import asyncio
import json
from typing import Any


async def _run_mcp_tool(tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments or {}

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

    tool_call_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    payload = (
        json.dumps(initialize_request) + "\n" +
        json.dumps(tool_call_request) + "\n"
    ).encode("utf-8")

    stdout, stderr = await process.communicate(payload)

    stderr_text = stderr.decode("utf-8", errors="ignore").strip()
    stdout_text = stdout.decode("utf-8", errors="ignore").strip()

    if process.returncode != 0:
        raise RuntimeError(f"google-ads-mcp failed: {stderr_text or 'unknown error'}")

    lines = [line for line in stdout_text.splitlines() if line.strip()]
    parsed = []
    for line in lines:
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not parsed:
        raise RuntimeError(f"No JSON response from MCP. STDOUT: {stdout_text} STDERR: {stderr_text}")

    tool_response = next((item for item in parsed if item.get("id") == 2), None)
    if not tool_response:
        raise RuntimeError(f"Tool response not found. Responses: {parsed}")

    if "error" in tool_response:
        raise RuntimeError(json.dumps(tool_response["error"]))

    return tool_response.get("result", {})


async def list_accessible_customers() -> dict[str, Any]:
    return await _run_mcp_tool("list_accessible_customers")
