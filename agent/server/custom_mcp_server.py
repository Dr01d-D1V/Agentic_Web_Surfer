import os
import re
import sys
import asyncio
from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from mcp.server.fastmcp import FastMCP
from playwright.async_api import Playwright, async_playwright
from steel import AsyncSteel

load_dotenv(find_dotenv())

STEEL_API_KEY = os.getenv("STEEL_API_KEY", "")
if not STEEL_API_KEY:
    sys.exit("Set STEEL_API_KEY (https://app.steel.dev/settings/api-keys)")

STEEL_BASE_URL = os.getenv("STEEL_BASE_URL", "https://api.steel.dev")
steel = AsyncSteel(steel_api_key=STEEL_API_KEY, base_url=STEEL_BASE_URL)

playwright: Playwright | None = None

_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _resolve_session_id(value: str) -> str:
    """steel_session_create (steel-mcp-server's own tool) returns a sess_...
    handle that only works with ITS tools. Our tools call Steel's raw API
    directly, which needs the real UUID instead, the same UUID already
    present in that same result's dashboard URL. Accept a bare UUID, a
    dashboard URL, or any text containing one, and pull the UUID out."""
    match = _UUID_RE.search(value)
    if not match:
        raise ValueError(
            f"Could not find a Steel session UUID in {value!r}. "
            "steel_session_create's session_id (the sess_... handle) will not "
            "work here, pass the dashboard URL or UUID from that same result instead."
        )
    return match.group(0)


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    global playwright
    async with async_playwright() as p:
        playwright = p
        yield


mcp = FastMCP("steel", lifespan=server_lifespan)


@mcp.tool()
async def upload_file(session_id: str, selector: str, file_path: str) -> dict:
    """Upload a local file into a page's file input on an EXISTING Steel session.
    session_id must be the dashboard URL or UUID from that session's
    steel_session_create result, not its sess_... handle."""
    if playwright is None:
        raise RuntimeError("Playwright instance has not been initialized.")

    real_id = _resolve_session_id(session_id)
    session = await steel.sessions.retrieve(real_id)

    ws_url = session.websocket_url
    delimiter = "&" if "?" in ws_url else "?"
    cdp_url = f"{ws_url}{delimiter}apiKey={STEEL_API_KEY}"

    browser = await playwright.chromium.connect_over_cdp(cdp_url)
    try:
        if not browser.contexts or not browser.contexts[0].pages:
            raise RuntimeError("No active pages found in the connected session.")
        page = browser.contexts[0].pages[0]
        await page.locator(selector).set_input_files(file_path)
        return {"status": "uploaded", "session_id": real_id}
    finally:
        await browser.close()


@mcp.tool()
async def get_live_debug_url(session_id: str) -> dict:
    """Return the correct, directly-embeddable debug_url for a session, the
    one that does NOT require the viewer to be logged into a Steel account.
    session_id must be the dashboard URL or UUID from that session's
    steel_session_create result, not its sess_... handle."""
    real_id = _resolve_session_id(session_id)
    session = await steel.sessions.retrieve(real_id)
    return {"debug_url": session.debug_url}


@mcp.tool()
async def create_profile_session() -> dict:
    """Create a new Steel session that will persist its browser profile on
    release. Navigate and log in manually via the returned debug_url, then
    call release_profile_session when done. The real profile_id only becomes
    available AFTER release, not at creation time. Session lifetime is fixed
    by your Steel plan and cannot be set here."""
    session = await steel.sessions.create(persist_profile=True)
    # profile_id = session.profile_id
    return {
        "session_id": session.id,
        "debug_url": session.debug_url,
        # "profile_id": session.profile_id,
        "note": "profile_id is only available after you call release_profile_session",
    }


@mcp.tool()
async def release_profile_session(session_id: str) -> dict:
    """Release a session, returning its real profile_id if it was created
    with persist_profile. session_id must be the dashboard URL or UUID from
    that session's steel_session_create (or create_profile_session) result,
    not its sess_... handle."""
    real_id = _resolve_session_id(session_id)
    await steel.sessions.release(real_id)
    await asyncio.sleep(3)
    session = await steel.sessions.retrieve(real_id)
    return {"profile_id": session.profile_id}


if __name__ == "__main__":
    try:
        mcp.run()
    except Exception as exc:
        print(f"MCP server execution failed: {exc}")