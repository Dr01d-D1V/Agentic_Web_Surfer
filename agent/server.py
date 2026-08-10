import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import agent
from agno.run.base import RunStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-server")

app = FastAPI()


class RunRequest(BaseModel):
    prompt: str
    session_id: str | None = None


class RunResponse(BaseModel):
    content: str
    warning: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/agent/run", response_model=RunResponse)
async def run(req: RunRequest):
    logger.info("run start session_id=%s prompt=%r", req.session_id, req.prompt)
    try:
        resp = await agent.arun(req.prompt, stream=False, session_id=req.session_id)
    except Exception:
        # Don't leak internals (stack traces, MCP/browser errors, API keys in
        # error messages) back to the client — log full detail server-side only.
        logger.exception("agent run failed session_id=%s", req.session_id)
        raise HTTPException(
            status_code=502,
            detail="Agent run failed. Check server logs (Steel connectivity, "
            "model API key, or the browsing task itself may be the cause).",
        )

    logger.info("run complete session_id=%s status=%s", req.session_id, resp.status)

    if resp.status == RunStatus.error:
        # Agno itself doesn't raise on model/provider failures (rate limits,
        # outages, etc.) — it stores the error message as `resp.content` and
        # returns normally. Without this check that error text would be
        # returned to the client as if it were a real agent answer.
        logger.error("agent run ended in error status session_id=%s: %s", req.session_id, resp.content)
        raise HTTPException(status_code=502, detail=str(resp.content))

    warning = None
    tool_calls = resp.tools or []
    steel_calls = [t for t in tool_calls if t.tool_name]

    if not steel_calls:
        # Small/local models sometimes narrate browsing actions ("I've opened
        # Wikipedia...") without ever invoking a tool, producing a confident
        # but fully hallucinated answer. RunOutput.tools is empty whenever no
        # tool actually ran, which is the reliable way to catch this — much
        # more reliable than trying to detect it from the text itself.
        warning = (
            "No browser tool was called during this run. The response below "
            "may be hallucinated rather than based on an actual page visit."
        )
        logger.warning("run had zero tool calls session_id=%s", req.session_id)
    else:
        logger.info(
            "run used %d tool call(s): %s",
            len(steel_calls),
            [t.tool_name for t in steel_calls],
        )

    return {"content": resp.content, "warning": warning}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)