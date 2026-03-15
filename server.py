from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mcp_client import list_accessible_customers

app = FastAPI()


class EmptyRequest(BaseModel):
    pass


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/list-accessible-customers")
async def list_customers(_: EmptyRequest):
    try:
        result = await list_accessible_customers()
        return {
            "assistant_message": "Accessible Google Ads customers loaded successfully.",
            "tools_executed": [
                {
                    "tool_name": "list_accessible_customers",
                    "status": "success",
                    "output": result,
                }
            ],
            "metadata": {
                "customers": result,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
