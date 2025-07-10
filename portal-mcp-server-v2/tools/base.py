"""Base utilities for Quix MCP tools."""

import os
import logging
import httpx
from typing import Any, Optional, Dict, List

from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)

# Quix API constants
DEFAULT_API_VERSION_HEADER = "2.0"

class QuixApiError(Exception):
    """Exception raised for errors in the Quix API."""
    def __init__(self, message: str, error_type: str = "api_error", status_code: Optional[int] = None):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code
        
def create_guided_error_message(error_type: str, status_code: Optional[int], original_message: str, context: str = "") -> str:
    """Create guided error messages based on error type and status code."""
    base_message = f"[{error_type.upper()}]"
    
    if status_code == 401:
        return f"{base_message} Authentication failed. Please verify your QUIX_TOKEN is valid and hasn't expired. You can generate a new token from the Quix Portal settings."
    elif status_code == 403:
        return f"{base_message} Permission denied. Your account may not have access to this {context}. Contact your workspace administrator or check if you're using the correct workspace ID."
    elif status_code == 404:
        return f"{base_message} Resource not found. The {context} ID might be incorrect or the resource may have been deleted. Try listing available resources first to verify the correct ID."
    elif status_code == 409:
        return f"{base_message} Resource conflict. The {context} name might already exist or be in use. Try a different name or check existing resources."
    elif status_code == 422:
        return f"{base_message} Invalid request data. Please check that all required parameters are provided and correctly formatted."
    elif status_code and status_code >= 500:
        return f"{base_message} Server error. The Quix Portal may be experiencing issues. Please try again in a few moments or check the Quix status page."
    elif error_type == "timeout":
        return f"{base_message} Request timed out. The operation may be taking longer than expected. For large operations, try breaking them into smaller chunks."
    elif error_type == "network":
        return f"{base_message} Network connectivity issue. Please check your internet connection and verify the QUIX_BASE_URL is correct."
    else:
        return f"{base_message} {original_message}"

def replace_workspace_id_in_json(json_data: Dict[str, Any], workspace_id: str) -> Dict[str, Any]:
    """
    Safely replace {workspaceId} placeholders in JSON data using proper traversal.
    
    Args:
        json_data: The JSON data structure to process
        workspace_id: The workspace ID to substitute
        
    Returns:
        The JSON data with placeholders replaced
    """
    if isinstance(json_data, dict):
        return {key: replace_workspace_id_in_json(value, workspace_id) for key, value in json_data.items()}
    elif isinstance(json_data, list):
        return [replace_workspace_id_in_json(item, workspace_id) for item in json_data]
    elif isinstance(json_data, str) and json_data == "{workspaceId}":
        return workspace_id
    else:
        return json_data

def validate_required_params(params: Dict[str, Any], required_fields: List[str], context: str = "operation") -> Optional[str]:
    """
    Validate that required parameters are provided and not empty.
    
    Args:
        params: Dictionary of parameters to validate
        required_fields: List of required field names
        context: Context for the error message (e.g., "create application")
        
    Returns:
        Error message if validation fails, None if all required fields are present
    """
    missing_fields = []
    empty_fields = []
    
    for field in required_fields:
        if field not in params:
            missing_fields.append(field)
        elif params[field] is None or (isinstance(params[field], str) and params[field].strip() == ""):
            empty_fields.append(field)
    
    if missing_fields or empty_fields:
        error_parts = []
        if missing_fields:
            error_parts.append(f"Missing required parameters: {', '.join(missing_fields)}")
        if empty_fields:
            error_parts.append(f"Empty required parameters: {', '.join(empty_fields)}")
        
        return f"Error in {context}: {' and '.join(error_parts)}. Please provide all required parameters."
    
    return None

async def make_quix_request(
    ctx: Context,
    method: str,
    path: str,
    workspace_id: Optional[str] = None,
    json: Dict[str, Any] = None,
    params: Dict[str, Any] = None,
    headers: Dict[str, Any] = None,
) -> Any:
    """Make a request to the Quix Portal API with proper error handling."""
    # Get environment variables
    token = os.environ.get("QUIX_TOKEN")
    base_url = os.environ.get("QUIX_BASE_URL")
    
    if not token:
        raise QuixApiError("Missing QUIX_TOKEN environment variable. Please set your Quix Personal Access Token.")
    
    if not base_url:
        raise QuixApiError("Missing QUIX_BASE_URL environment variable. Please set your Quix Base URL (e.g. https://portal-myenv.platform.quix.io/).")
    
    if not workspace_id and "{workspaceId}" in path:
        raise QuixApiError("Missing workspace_id parameter. Please provide a workspace_id for this operation. If you don't know your workspace ID, use the 'list_workspaces' tool to find available workspaces.")
    
    # Replace workspace_id in path if present
    if workspace_id and "{workspaceId}" in path:
        path = path.replace("{workspaceId}", workspace_id)
    
    # Replace workspace_id in any placeholders if present in JSON
    if workspace_id and json:
        json = replace_workspace_id_in_json(json, workspace_id)
    
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
        status_code = e.response.status_code
        error_info = f"HTTP error {status_code}"
        
        try:
            error_detail = e.response.json()
            if isinstance(error_detail, dict) and 'message' in error_detail:
                error_info = f"{error_info}: {error_detail['message']}"
            else:
                error_info = f"{error_info}: {error_detail}"
        except Exception:
            # If we can't parse JSON, use the text content
            if e.response.text:
                error_info = f"{error_info}: {e.response.text}"
        
        logger.error(f"API Error: {error_info}")
        
        # Extract context from path for better error messages
        context = "resource"
        if "/applications/" in path:
            context = "application"
        elif "/deployments/" in path:
            context = "deployment"
        elif "/topics/" in path:
            context = "topic"
        elif "/workspaces/" in path:
            context = "workspace"
        elif "/library/" in path:
            context = "library item"
            
        guided_message = create_guided_error_message("http", status_code, error_info, context)
        raise QuixApiError(guided_message, "http_error", status_code)
    except httpx.TimeoutException as e:
        logger.error(f"Request timeout: {str(e)}")
        guided_message = create_guided_error_message("timeout", None, str(e))
        raise QuixApiError(guided_message, "timeout_error")
    except httpx.ConnectError as e:
        logger.error(f"Connection error: {str(e)}")
        guided_message = create_guided_error_message("network", None, f"Cannot connect to Quix Portal. Please verify your QUIX_BASE_URL ({base_url}) is correct and accessible.")
        raise QuixApiError(guided_message, "network_error")
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        guided_message = create_guided_error_message("network", None, str(e))
        raise QuixApiError(guided_message, "request_error")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise QuixApiError(f"Unexpected error: {str(e)}")