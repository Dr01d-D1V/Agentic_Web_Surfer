import os
import sys
from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from mcp.server.fastmcp import FastMCP
from playwright.async_api import Playwright, async_playwright
from steel import AsyncSteel

# Load environment variables
load_dotenv(find_dotenv())

STEEL_API_KEY = os.getenv("STEEL_API_KEY", "")
if not STEEL_API_KEY:
    sys.exit("Set STEEL_API_KEY (https://app.steel.dev/settings/api-keys)")

steel = AsyncSteel(steel_api_key=STEEL_API_KEY)

# Global holder for Playwright
playwright: Playwright | None = None


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage the lifecycle of the Playwright async engine."""
    global playwright
    async with async_playwright() as p:
        playwright = p
        yield


mcp = FastMCP("steel", lifespan=server_lifespan)


@mcp.tool()
async def upload_file(session_id: str, selector: str, file_path: str) -> dict:
    """Upload a local file into a page's file input on an EXISTING Steel session."""
    if playwright is None:
        raise RuntimeError("Playwright instance has not been initialized.")

    # Retrieve Steel session connection info
    session = await steel.sessions.retrieve(session_id)

    # Safely append apiKey depending on existing query parameters
    ws_url = session.websocket_url
    delimiter = "&" if "?" in ws_url else "?"
    cdp_url = f"{ws_url}{delimiter}apiKey={STEEL_API_KEY}"

    # Connect to the remote session over CDP
    browser = await playwright.chromium.connect_over_cdp(cdp_url)

    try:
        if not browser.contexts or not browser.contexts[0].pages:
            raise RuntimeError("No active pages found in the connected session.")

        page = browser.contexts[0].pages[0]

        # Locator-based set_input_files is the current recommended API;
        # page.set_input_files(selector, ...) still works but is discouraged.
        await page.locator(selector).set_input_files(file_path)
        return {"status": "uploaded", "session_id": session_id}

    finally:
        # Guarantee CDP connection detachment without closing the Steel cloud session
        await browser.close()


@mcp.tool()
async def get_live_debug_url(session_id: str) -> dict:
    """Return the correct, directly-embeddable debug_url for a session, the
    one that does NOT require the viewer to be logged into a Steel account.
    steel-mcp-server's own steel_session_create result only surfaces
    session_viewer_url, a Steel dashboard page that requires account login,
    the wrong link to hand to an end user for manual login."""
    session = await steel.sessions.retrieve(session_id)
    return {"debug_url": session.debug_url}


if __name__ == "__main__":
    try:
        mcp.run()
    except Exception as exc:
        print(f"MCP server execution failed: {exc}")

        