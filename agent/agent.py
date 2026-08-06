import os
from dotenv import load_dotenv
from mcp import StdioServerParameters

from agno.agent import Agent
from agno.tools.mcp import MCPTools

load_dotenv()

# Cloud or local model — swap the import/id as you like:
from agno.models.openai import OpenAIChat
# from agno.models.anthropic import Claude
from agno.models.google import Gemini
# from agno.models.ollama import Ollama   # local, e.g. qwen2.5-vl for screenshots

steel_mcp = StdioServerParameters(
    command="npx",
    args=["-y", "@steel-dev/steel-mcp-server"],
    env={
        "STEEL_LOCAL": "true",
        "STEEL_BASE_URL": os.getenv("STEEL_BASE_URL", "http://localhost:3000"),
        "STEEL_API_KEY": os.getenv("STEEL_API_KEY", ""),
    },
)

agent = Agent(
    name="Steel Surfer",
    model=Gemini(id="gemini-2.0-flash"),          # use a vision-capable model for screenshots
    tools=[MCPTools(servers=[steel_mcp])],
    instructions=[
        "You are a web-browsing agent driving a real browser via Steel.",
        "Use the Steel MCP tools to navigate, click, type, and take screenshots.",
        "When you need to understand a page, take a screenshot and read it.",
    ],
    show_tool_calls=True,
    markdown=True,
)