import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-server")

app = FastAPI()

class RunRequest(BaseModel):
    prompt: str
    session_id: str | None = None

class RunResponse(BaseModel):
    content: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/agent/run", response_model=RunResponse)
def run(req: RunRequest):
    logger.info("run start session_id=%s prompt=%r", req.session_id, req.prompt)
    try:
        resp = agent.run(req.prompt, stream=False, session_id=req.session_id)
    except Exception:
        # Don't leak internals (stack traces, MCP/browser errors, API keys in
        # error messages) back to the client — log full detail server-side only.
        logger.exception("agent run failed session_id=%s", req.session_id)
        raise HTTPException(
            status_code=502,
            detail="Agent run failed. Check server logs (Steel connectivity, "
            "model API key, or the browsing task itself may be the cause).",
        )

    logger.info("run complete session_id=%s", req.session_id)
    return {"content": resp.content}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)