from fastapi import FastAPI
from pydantic import BaseModel
from agent import agent

app = FastAPI()

class RunRequest(BaseModel):
    prompt: str
    session_id: str | None = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/agent/run")
def run(req: RunRequest):
    resp = agent.run(req.prompt, stream=False, session_id=req.session_id)
    return {"content": resp.content}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)