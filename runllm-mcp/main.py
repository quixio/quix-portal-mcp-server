import os
import json
import requests
from typing import Any
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server for RunLLM tools (SSE)
mcp = FastMCP("RunLLM")

@mcp.tool()
async def ask_runllm(message: str) -> str:
    """Ask RunLLM a question about Quix and get an AI-powered response.
    
    This tool connects to the RunLLM API, which is designed to answer questions
    about Quix products and services. Response time is typically 1-5 seconds but can be up to 30 seconds.
    
    Args:
        message: The question or query to ask RunLLM about Quix
    """
    # Get environment variables
    api_key = os.getenv("RUNLLM_API_KEY")
    pipeline_id = os.getenv("RUNLLM_PIPELINE_ID", "111")
    
    if not api_key:
        return "Error: RUNLLM_API_KEY environment variable is required"
    
    url = f"https://api.runllm.com/api/pipeline/{pipeline_id}/chat"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {"message": message}
    
    try:
        with requests.post(url, headers=headers, json=payload, stream=True) as r:
            r.raise_for_status()
            parts = []
            for line in r.iter_lines(decode_unicode=True):
                if line.startswith("data:"):
                    data = json.loads(line[5:])
                    if data.get("chunk_type") == "generation_in_progress":
                        parts.append(data["content"])
            
            return "".join(parts)
    
    except requests.exceptions.RequestException as e:
        return f"Error communicating with RunLLM API: {str(e)}"
    except json.JSONDecodeError as e:
        return f"Error parsing RunLLM response: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server  # noqa: WPS437

    import argparse
    
    parser = argparse.ArgumentParser(description='Run RunLLM MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=80, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    print(f"Starting RunLLM MCP server on {args.host}:{args.port}")
    print("Required environment variables:")
    print("  RUNLLM_API_KEY: Your RunLLM API token")
    print("  RUNLLM_PIPELINE_ID: Pipeline ID (defaults to '111')")
    
    uvicorn.run(starlette_app, host=args.host, port=args.port)