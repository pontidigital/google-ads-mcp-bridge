from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import json
import traceback

app = FastAPI()

class QueryRequest(BaseModel):
    message: str

@app.post("/query")
async def query(req: QueryRequest):
    try:
        print(f"Received message: {req.message}")

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

        print(f"Process return code: {process.returncode}")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")

        if process.returncode != 0:
            raise Exception(f"google-ads-mcp failed: {stderr}")

        return json.loads(stdout)

    except Exception as e:
        print("TRACEBACK START")
        traceback.print_exc()
        print("TRACEBACK END")
        raise HTTPException(status_code=500, detail=str(e))
