import asyncio
import json
import os
from typing import Any

from fastapi import FastAPI

app = FastAPI()


async def _run_mcp_method(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}

    process = await asyncio.create_subprocess_exec(
        "google-ads-mcp",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "google-ads-mcp-bridge",
                "version": "1.0.0",
            },
        },
    }

    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": method,
        "params": params,
    }

    payload = (
        json.dumps(initialize_request) + "\n" +
        json.dumps(request) + "\n"
    ).encode("utf-8")

    stdout, stderr = await process.communicate()

    stderr_text = stderr.decode("utf-8", errors="ignore").strip()
    stdout_text = stdout.decode("utf-8", errors="ignore").strip()

    if process.stdin:
        process.stdin.write(payload)
        await process.stdin.drain()
        process.stdin.close()

    stdout, stderr = await process.communicate()

    stderr_text = stderr.decode("utf-8", errors="ignore").strip()
    stdout_text = stdout.decode("utf-8", errors="ignore").strip()

    if process.returncode != 0:
        raise RuntimeError(f"google-ads-mcp failed: {stderr_text or 'unknown error'}")

    lines = [line for line in stdout_text.splitlines() if line.strip()]
    parsed: list[dict[str, Any]] = []

    for line in lines:
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not parsed:
        raise RuntimeError(f"No JSON response from MCP. STDOUT: {stdout_text} STDERR: {stderr_text}")

    response = next((item for item in parsed if item.get("id") == 2), None)
    if not response:
        raise RuntimeError(f"Response not found. Responses: {parsed}")

    if "error" in response:
        raise RuntimeError(json.dumps(response["error"]))

    return response.get("result", {})


async def _run_mcp_tool(tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _run_mcp_method(
        "tools/call",
        {
            "name": tool_name,
            "arguments": arguments or {},
        },
    )


async def list_tools() -> dict[str, Any]:
    return await _run_mcp_method("tools/list", {})


async def list_accessible_customers() -> dict[str, Any]:
    return await _run_mcp_tool("list_accessible_customers")


async def search_campaigns(customer_id: str, login_customer_id: str | None = None) -> dict[str, Any]:
    query = """
    SELECT
      campaign.id,
      campaign.name,
      campaign.status,
      campaign.advertising_channel_type
    FROM campaign
    ORDER BY campaign.name
    """

    args: dict[str, Any] = {
        "customer_id": customer_id,
        "query": query,
    }

    if login_customer_id:
        args["login_customer_id"] = login_customer_id

    return await _run_mcp_tool("search", args)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/tools")
async def tools():
    return await list_tools()


@app.get("/debug-auth-config")
async def debug_auth_config():
    return {
        "GOOGLE_ADS_DEVELOPER_TOKEN": bool(os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")),
        "GOOGLE_ADS_CLIENT_ID": bool(os.getenv("GOOGLE_ADS_CLIENT_ID")),
        "GOOGLE_ADS_CLIENT_SECRET": bool(os.getenv("GOOGLE_ADS_CLIENT_SECRET")),
        "GOOGLE_ADS_REFRESH_TOKEN": bool(os.getenv("GOOGLE_ADS_REFRESH_TOKEN")),
    }


@app.post("/list-accessible-customers")
async def http_list_accessible_customers():
    return await list_accessible_customers()


@app.post("/campaigns")
async def http_search_campaigns(body: dict[str, Any]):
    customer_id = body.get("customer_id")
    login_customer_id = body.get("login_customer_id")

    if not customer_id:
        return {"error": "customer_id is required"}

    return await search_campaigns(customer_id, login_customer_id)
