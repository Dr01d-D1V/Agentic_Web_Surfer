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
        return Gemini(id=os.getenv("MODEL_ID", "gemini-2.0-flash"))
    else:
        return Ollama(id=os.getenv("OLLAMA_MODEL", "gemma4:e4b"))


steel_mcp = StdioServerParameters(
    command="npx",
    args=["-y", "@steel-dev/steel-mcp-server"],
    env={
        "STEEL_LOCAL": "true",
        "STEEL_BASE_URL": os.getenv("STEEL_BASE_URL", "http://localhost:3000"),
        "STEEL_API_KEY": os.getenv("STEEL_API_KEY", ""),
    },
)

agent_db = RedisDb(db_url="redis://localhost:6379")

agent = Agent(
    name="Steel Surfer",
    model=build_model(),          # use a vision-capable model for screenshots
    # tools=[MCPTools(servers=[steel_mcp])],
    tools=[MCPTools(server_params=steel_mcp)],
    instructions=[
        "You have NO knowledge of any webpage's current content until you retrieve it "
        "yourself via a tool call. Never describe visiting, opening, or reading a page "
        "unless you have just made a real tool call and received its result.",
        "If you're asked to browse or check something, your first action must be an "
        "actual tool call — not a description of what you're about to do.",
        "You are a web-browsing agent driving a real browser via Steel.",
        "Use the Steel MCP tools to navigate, click, type, and take screenshots.",
        "When you need to understand a page, take a screenshot and read it.",
        "Only ever visit and interact with pages relevant to the user's request.",
        "If a task requires submitting a form, making a purchase, or any other "
        "irreversible action, describe what you are about to do and stop to ask "
        "for confirmation before doing it.",
    ],
    db=agent_db,
    add_history_to_context=True,
    num_history_runs=5,
    tool_call_limit=int(os.getenv("TOOL_CALL_LIMIT", "25")),
    # show_tool_calls=True,
    debug_mode=True,
    markdown=True,
)