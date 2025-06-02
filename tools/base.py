"""Base utilities for Quix MCP tools."""

import os
import logging
import httpx
from typing import Any, Optional, Dict

from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)

# Quix API constants
DEFAULT_API_VERSION_HEADER = "2.0"

class QuixApiError(Exception):
    """Exception raised for errors in the Quix API."""
    pass

async def make_quix_request(
    ctx: Context,
    method: str,
    path: str,
    json: Dict[str, Any] = None,
    params: Dict[str, Any] = None,
    headers: Dict[str, Any] = None,
) -> Any:
    """Make a request to the Quix Portal API with proper error handling."""
    # Get environment variables
    token = os.environ.get("QUIX_TOKEN")
    base_url = os.environ.get("QUIX_BASE_URL")
    workspace_id = os.environ.get("QUIX_WORKSPACE")
    
    if not token:
        raise QuixApiError("Missing QUIX_TOKEN environment variable. Please set your Quix Personal Access Token.")
    
    if not base_url:
        raise QuixApiError("Missing QUIX_BASE_URL environment variable. Please set your Quix Base URL (e.g. https://portal-myenv.platform.quix.io/).")
    
    if not workspace_id and "{workspaceId}" in path:
        raise QuixApiError("Missing QUIX_WORKSPACE environment variable. Please set your Quix Workspace ID.")
    
    # Replace workspace_id in path if present
    if workspace_id and "{workspaceId}" in path:
        path = path.replace("{workspaceId}", workspace_id)
    
    # Replace workspace_id in any placeholders if present in JSON
    if workspace_id and json and "{workspaceId}" in str(json):
        import json as json_lib
        json_str = json_lib.dumps(json)
        json_str = json_str.replace('"{workspaceId}"', f'"{workspace_id}"')
        json = json_lib.loads(json_str)
    
    # Ensure base URL ends with a slash
    if not base_url.endswith('/'):
        base_url = f"{base_url}/"
    
    # Set default headers
    request_headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "X-Version": DEFAULT_API_VERSION_HEADER
    }
    
    # Add any additional headers
    if headers:
        request_headers.update(headers)
    
    # Log the request details (omitting sensitive headers)
    safe_headers = {k: v for k, v in request_headers.items() if k != "Authorization"}
    logger.info(f"API Request: {method} {base_url}{path}")
    logger.debug(f"Headers: {safe_headers}")
    logger.debug(f"Params: {params}")
    
    url = f"{base_url}{path}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=json,
                params=params,
                headers=request_headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            
            # Handle empty responses
            if not response.content:
                return None
            
            # Handle text responses or JSON responses
            content_type = response.headers.get("content-type", "")
            if content_type and "text/plain" in content_type and not "application/json" in content_type:
                return response.text
            else:
                try:
                    return response.json()
                except ValueError:
                    # Return raw content if not JSON
                    return response.text
    except httpx.HTTPStatusError as e:
        error_info = f"HTTP error {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_info = f"{error_info}: {error_detail}"
        except Exception:
            # If we can't parse JSON, use the text content
            if e.response.text:
                error_info = f"{error_info}: {e.response.text}"
        
        logger.error(f"API Error: {error_info}")
        raise QuixApiError(f"Error calling Quix API: {error_info}")
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise QuixApiError(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise QuixApiError(f"Unexpected error: {str(e)}")