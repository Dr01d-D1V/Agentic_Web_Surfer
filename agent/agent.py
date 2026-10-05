import os
from dotenv import load_dotenv
from mcp import StdioServerParameters

from agno.agent import Agent
from agno.tools.mcp import MCPTools
from agno.db.redis import RedisDb

load_dotenv()

# Cloud or local model — swap the import/id as you like:
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.models.google import Gemini
from agno.models.deepseek import DeepSeek
from agno.models.ollama import Ollama   # local, e.g. qwen2.5-vl for screenshots

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "").lower()

def build_model():
    if MODEL_PROVIDER == "openai":
        return OpenAIChat(id=os.getenv("MODEL_ID", "gpt-4o"))
    elif MODEL_PROVIDER == "anthropic":
        return Claude(id=os.getenv("MODEL_ID", ""))
    elif MODEL_PROVIDER == "google":
        return Gemini(id=os.getenv("MODEL_ID", "gemini-2.5-flash"))
    else:
        return Ollama(id=os.getenv("OLLAMA_MODEL", "gemma4:e4b"))

# Now a real toggle read from .env instead of a hardcoded literal, so switching
# between self-hosted and Steel Cloud is a config change, not a code edit.
STEEL_LOCAL = os.getenv("STEEL_LOCAL_STATUS", "true").strip().lower() == "true"

custom_steel_mcp = StdioServerParameters(
    command="python",
    args=["server/custom_mcp_server.py"],
    env={
        "STEEL_BASE_URL": os.getenv(
            "STEEL_BASE_URL",
            "http://localhost:3000" if STEEL_LOCAL else "https://api.steel.dev",
        ),
    #     # "STEEL_API_KEY": os.getenv("STEEL_API_KEY", ""),
    },
)

steel_mcp = StdioServerParameters(
    command="node",
    args=[os.getenv("STEEL_MCP_SERVER_PATH", "../steel-mcp-server/dist/stdio.js")],
    env={
        "STEEL_LOCAL": "true" if STEEL_LOCAL else "false",
        "STEEL_BASE_URL": os.getenv(
            "STEEL_BASE_URL",
            "http://localhost:3000" if STEEL_LOCAL else "https://api.steel.dev",
        ),
        "STEEL_API_KEY": os.getenv("STEEL_API_KEY", ""),
    },
)

agent_db = RedisDb(db_url="redis://localhost:6379")

custom_steel_tools = MCPTools(
    server_params=custom_steel_mcp,
    timeout_seconds=60
)

steel_tools = MCPTools(
    server_params=steel_mcp, 
    timeout_seconds=60, 
    exclude_tools=["steel_session_create", "steel_session_release"] if STEEL_LOCAL else [],
    )


deployment_instructions = ""
if STEEL_LOCAL:
    deployment_instructions = [
        "This deployment is self-hosted, not Steel Cloud. Do not attempt goal='account', persist_profile, use_proxy, or solve_captcha, these will always fail here. For login walls, create a plain session with no special parameters and rely on the viewer_url handoff instead.",
    ]
else:
    deployment_instructions = [
        "This deployment is Steel Cloud, but steel_session_options is not available to you in this configuration. Never invent a profile_id, namespace, or credential value, these do not exist unless a real one was explicitly given to you. Always create a plain steel_session_create call with no profile_id, namespace, or persist_profile, and rely on the viewer_url handoff for any login wall.",
    ]

agent = Agent(
    name="Steel Surfer",
    model=build_model(),          # use a vision-capable model for screenshots
    # tools=[MCPTools(servers=[steel_mcp])],
    tools=[
        steel_tools, 
        custom_steel_tools
    ], 
    instructions=[
        deployment_instructions,
        # "I have currently set the deployment to Steel Cloud so you can make use of all the cloud tools available to you for a certain task."
        # "If deployment is set to self-hosted do not attempt goal='account', persist_profile, use_proxy, or solve_captcha — these will always fail here."
        "When initializing a browser context using the browser workspace creation tools, the tool payload returns an infrastructural parameter named 'sessionViewerUrl'.",
        "CRITICAL INFRASTRUCTURE RULE: Under no circumstances should you confuse 'sessionViewerUrl' with the address bar URL of the pages you navigate to (like LinkedIn or Google).",
        "If you encounter a login wall or captcha checkpoint and are instructed to halt for human takeover, you MUST explicitly grab the 'sessionViewerUrl' provided during session setup and print it cleanly to the user.",
        "When handing off a session for manual login, always call get_live_debug_url with the session_id first, and report that debug_url to the user, not the viewer_url printed by steel_session_create, which requires a Steel account login and will not work for them.",
        "Do not grab the URL string from the page redirect wall (e.g. do not print '://linkedin.com'). Only report the Steel-hosted dashboard viewer web address."
        "For login walls, create a plain session and rely on the viewer_url handoff instead.",
        "Whenever a user makes a request for you to go to a website, before you create the session, if the site looks like it requires the person to log in or they say you should log in, you should make use of the create_profile_session tool and when you are to end or release the session you should use the release_profile_session tool.",
        "steel_session_create's session_id (the sess_... string) only works with steel-mcp-server's own tools: steel_navigate, steel_act, steel_session_release, and similar. For upload_file, get_live_debug_url, and release_profile_session, use the dashboard URL or UUID from that same steel_session_create result instead (the 'Watch or take control in the live browser: ...' line), not the sess_... handle.",
        "To reuse an already-set-up profile for routine work, use plain steel_session_create with profile_id set to the real profile_id, this loads the identity safely without overwriting it. Only use create_profile_session when you specifically need to create a NEW profile or intentionally re-save changes to an existing one.",
        "Steel sessions expire based on timeout_ms set at creation and cannot be extended afterward."
        "On Steel Cloud, this account's plan caps session length at 900000ms (15 minutes). Always use timeout_ms=900000 when creating a session, do not request more.",
        # "Always set timeout_ms to at least 1800000 (30 minutes) when creating a session, especially for any task that might need a login or manual step."
        "TOOL USAGE RULES:",
        "- `steel_scrape` is a standalone tool. Do NOT create a browser session or call `steel_navigate` before calling `steel_scrape`. Just pass the `url` directly to it.",
        "- If you choose to use a browser session (via `steel_session_create`), you must use `steel_navigate` with the resulting `session_id` to go to a page, and then use `steel_snapshot` or `steel_screenshot` to read the page content. Do NOT mix `steel_scrape` with an active browser session ID.",
        "You have NO knowledge of any webpage's current content until you retrieve it "
        "yourself via a tool call. Never describe visiting, opening, or reading a page "
        "unless you have just made a real tool call and received its result.",
        "If you're asked to browse or check something, your first action must be an "
        "actual tool call not a description of what you're about to do.",
        "You are a web-browsing agent driving a real browser via Steel.",
        "Use the Steel MCP tools to navigate, click, type, and take screenshots.",
        "When you need to understand a page, take a screenshot and read it.",
        "Only ever visit and interact with pages relevant to the user's request.",
        "If a task requires submitting a form, making a purchase, or any other irreversible action, describe what you are about to do and stop to ask for confirmation before doing it.",
    ],
    db=agent_db,
    add_history_to_context=True,
    num_history_runs=5,
    tool_call_limit=int(os.getenv("TOOL_CALL_LIMIT", "25")),
    # show_tool_calls=True,
    debug_mode=True,
    markdown=True,
)