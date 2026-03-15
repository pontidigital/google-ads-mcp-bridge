from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import json

app = FastAPI()

class QueryRequest(BaseModel):
    message: str

@app.post("/query")
async def query(req: QueryRequest):

    process = subprocess.Popen(
        ["google-ads-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    payload = json.dumps({
        "message": req.message
    })

    stdout, stderr = process.communicate(payload)

    if stderr:
        raise Exception(stderr)

    return json.loads(stdout)
