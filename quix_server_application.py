import os
import asyncio
import logging
import httpx
from typing import Any, Optional, Dict, List
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
import dotenv

# Initialize FastMCP server for Quix Applications
mcp = FastMCP("quix_applications")

# Set up logging
logging.basicConfig(level=logging.INFO)
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
            
            return response.json()
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

# =========================================
# Application Tools
# =========================================

@mcp.tool()
async def list_applications(ctx: Context, search: Optional[str] = None, include_updated_at: bool = False) -> str:
    """List all applications in the workspace.
    
    Args:
        search: Optional filter string to search for specific applications
        include_updated_at: True to include the updated at timestamp (default: False)
    """
    try:
        params = {}
        if search:
            params["search"] = search
        if include_updated_at:
            params["includeUpdatedAt"] = "true"
            
        applications = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/applications",
            params=params
        )
        
        if not applications:
            return "No applications found in this workspace."
        
        result = "Applications:\n\n"
        for app in applications:
            result += f"ID: {app.get('applicationId')}\n"
            result += f"Name: {app.get('name')}\n"
            result += f"Path: {app.get('path')}\n"
            result += f"Language: {app.get('language') or 'Unknown'}\n"
            
            # Add status information
            status = app.get('status')
            if status:
                result += f"Status: {status}\n"
                
            # Include error information if present
            error_status = app.get('errorStatus')
            if error_status:
                result += f"Error Status: {error_status}\n"
                error_message = app.get('errorMessage')
                if error_message:
                    result += f"Error Message: {error_message}\n"
            
            # Add updated_at if included in response
            updated_at = app.get('updatedAt')
            if updated_at:
                result += f"Last Updated: {updated_at}\n"
                
            result += "-" * 40 + "\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_application(ctx: Context, application_id: str, reference: Optional[str] = None, include_updated_at: bool = False) -> str:
    """Get details of a specific application.
    
    Args:
        application_id: The ID of the application to retrieve
        reference: Optional commit reference
        include_updated_at: True to include the updated at timestamp (default: False)
    """
    try:
        params = {}
        if reference:
            params["reference"] = reference
        if include_updated_at:
            params["includeUpdatedAt"] = "true"
            
        application = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/applications/{applicationId}".replace("{applicationId}", application_id),
            params=params
        )
        
        if not application:
            return f"No application found with ID {application_id}."
        
        # Format the application details
        result = "Application Details:\n\n"
        result += f"ID: {application.get('applicationId')}\n"
        result += f"Name: {application.get('name')}\n"
        result += f"Path: {application.get('path')}\n"
        result += f"Workspace ID: {application.get('workspaceId')}\n"
        result += f"Language: {application.get('language') or 'Unknown'}\n"
        
        # Add docker information if present
        dockerfile = application.get('dockerfile')
        if dockerfile:
            result += f"Dockerfile: {dockerfile}\n"
            
        run_entry_point = application.get('runEntryPoint')
        if run_entry_point:
            result += f"Run Entry Point: {run_entry_point}\n"
            
        default_file = application.get('defaultFile')
        if default_file:
            result += f"Default File: {default_file}\n"
            
        # Add status information
        status = application.get('status')
        if status:
            result += f"Status: {status}\n"
            
        # Include error information if present
        error_status = application.get('errorStatus')
        if error_status:
            result += f"Error Status: {error_status}\n"
            error_message = application.get('errorMessage')
            if error_message:
                result += f"Error Message: {error_message}\n"
                
        # Include library item ID if present
        library_item_id = application.get('libraryItemId')
        if library_item_id:
            result += f"Library Item ID: {library_item_id}\n"
            
        # Include connector and auxiliary service flags if present
        is_connector = application.get('isConnector')
        if is_connector is not None:
            result += f"Is Connector: {is_connector}\n"
            
        is_auxiliary_service = application.get('isAuxiliaryService')
        if is_auxiliary_service is not None:
            result += f"Is Auxiliary Service: {is_auxiliary_service}\n"
            
        # Add included folders if present
        included_folders = application.get('includedFolders')
        if included_folders:
            result += "Included Folders:\n"
            for folder in included_folders:
                result += f"  - {folder}\n"
                
        # Add variables if present
        variables = application.get('variables')
        if variables:
            result += "\nVariables:\n"
            for var in variables:
                result += f"  Name: {var.get('name')}\n"
                result += f"  Type: {var.get('inputType')}\n"
                result += f"  Required: {var.get('required')}\n"
                
                description = var.get('description')
                if description:
                    result += f"  Description: {description}\n"
                    
                default_value = var.get('defaultValue')
                if default_value:
                    result += f"  Default Value: {default_value}\n"
                    
                result += "  ---\n"
                
        # Add updated_at if included in response
        updated_at = application.get('updatedAt')
        if updated_at:
            result += f"Last Updated: {updated_at}\n"
            
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def create_application(ctx: Context, application_name: str, path: Optional[str] = None, language: Optional[str] = None) -> str:
    """Create a new application in the workspace.
    
    Args:
        application_name: Name of the application
        path: Optional directory path where the application should be created
        language: Optional programming language for the application
    """
    try:
        payload = {
            "applicationName": application_name
        }
        
        if path:
            payload["path"] = path
            
        if language:
            payload["language"] = language
            
        application = await make_quix_request(
            ctx, 
            "POST", 
            "{workspaceId}/applications",
            json=payload
        )
        
        if not application:
            return "Failed to create application."
        
        application_id = application.get('applicationId')
        return f"Successfully created application '{application_name}' with ID: {application_id}"
    except QuixApiError as e:
        return f"Error creating application: {str(e)}"

@mcp.tool()
async def update_application(
    ctx: Context,
    application_id: str,
    application_name: Optional[str] = None,
    application_path: Optional[str] = None,
    language: Optional[str] = None,
    dockerfile: Optional[str] = None,
    run_entry_point: Optional[str] = None,
    default_file: Optional[str] = None,
    variables: Optional[List[Dict[str, Any]]] = None,
    included_folders: Optional[List[str]] = None
) -> str:
    """Update an existing application.
    
    Args:
        application_id: The ID of the application to update
        application_name: Optional new name for the application
        application_path: Optional new path for the application
        language: Optional new language for the application
        dockerfile: Optional new Dockerfile for the application
        run_entry_point: Optional new run entry point for the application
        default_file: Optional new default file for the application
        variables: Optional list of application variables following the ApplicationVariable schema
        included_folders: Optional list of folders to include
    """
    try:
        payload = {}
        
        if application_name:
            payload["applicationName"] = application_name
            
        if application_path:
            payload["applicationPath"] = application_path
            
        if language:
            payload["language"] = language
            
        if dockerfile:
            payload["dockerfile"] = dockerfile
            
        if run_entry_point:
            payload["runEntryPoint"] = run_entry_point
            
        if default_file:
            payload["defaultFile"] = default_file
            
        if variables:
            payload["variables"] = variables
            
        if included_folders:
            payload["includedFolders"] = included_folders
            
        application = await make_quix_request(
            ctx, 
            "PATCH", 
            "{workspaceId}/applications/{applicationId}".replace("{applicationId}", application_id),
            json=payload
        )
        
        if not application:
            return f"Failed to update application {application_id}."
        
        return f"Successfully updated application '{application.get('name')}' (ID: {application_id})"
    except QuixApiError as e:
        return f"Error updating application: {str(e)}"

@mcp.tool()
async def delete_application(ctx: Context, application_id: str, delete_files: bool = True) -> str:
    """Delete an application.
    
    Args:
        application_id: The ID of the application to delete
        delete_files: Whether to delete the application files (default: True)
    """
    try:
        params = {"deleteFiles": str(delete_files).lower()}
        
        result = await make_quix_request(
            ctx, 
            "DELETE", 
            "{workspaceId}/applications/{applicationId}".replace("{applicationId}", application_id),
            params=params
        )
        
        return f"Successfully deleted application with ID: {application_id}"
    except QuixApiError as e:
        return f"Error deleting application: {str(e)}"

@mcp.tool()
async def list_application_files(ctx: Context, application_id: str, reference: Optional[str] = None) -> str:
    """List files in an application.
    
    Args:
        application_id: The ID of the application
        reference: Optional commit reference
    """
    try:
        params = {}
        if reference:
            params["reference"] = reference
            
        files = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/applications/{applicationId}/files".replace("{applicationId}", application_id),
            params=params
        )
        
        if not files:
            return f"No files found in application {application_id}."
        
        result = f"Files in application {application_id}:\n\n"
        for file in files:
            result += f"- {file}\n"
            
        return result
    except QuixApiError as e:
        return f"Error listing application files: {str(e)}"

@mcp.tool()
async def duplicate_application(
    ctx: Context, 
    application_id: str, 
    new_name: str, 
    new_path: Optional[str] = None
) -> str:
    """Duplicate an existing application.
    
    Args:
        application_id: The ID of the application to duplicate
        new_name: Name for the new application
        new_path: Optional path for the new application
    """
    try:
        payload = {
            "name": new_name
        }
        
        if new_path:
            payload["path"] = new_path
            
        application = await make_quix_request(
            ctx, 
            "POST", 
            "{workspaceId}/applications/{applicationId}/duplicate".replace("{applicationId}", application_id),
            json=payload
        )
        
        if not application:
            return f"Failed to duplicate application {application_id}."
        
        new_application_id = application.get('applicationId')
        return f"Successfully duplicated application to '{new_name}' with ID: {new_application_id}"
    except QuixApiError as e:
        return f"Error duplicating application: {str(e)}"

@mcp.tool()
async def get_application_commits(
    ctx: Context, 
    application_id: str, 
    git_reference: Optional[str] = None, 
    limit: Optional[int] = None
) -> str:
    """Get commit history for an application.
    
    Args:
        application_id: The ID of the application
        git_reference: Optional git reference to start from
        limit: Optional maximum number of commits to retrieve
    """
    try:
        params = {}
        if git_reference:
            params["gitReference"] = git_reference
            
        if limit:
            params["limit"] = limit
            
        commits = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/applications/{applicationId}/commits".replace("{applicationId}", application_id),
            params=params
        )
        
        if not commits:
            return f"No commit history found for application {application_id}."
        
        result = f"Commit history for application {application_id}:\n\n"
        for commit in commits:
            result += f"Reference: {commit.get('reference')}\n"
            result += f"Message: {commit.get('message')}\n"
            result += f"Created: {commit.get('createdAt')}\n"
            
            author_name = commit.get('authorName')
            if author_name:
                result += f"Author: {author_name}"
                
                author_email = commit.get('authorEmail')
                if author_email:
                    result += f" <{author_email}>"
                    
                result += "\n"
                
            committer_name = commit.get('committerName')
            if committer_name and committer_name != author_name:
                result += f"Committer: {committer_name}\n"
                
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving commit history: {str(e)}"

@mcp.tool()
async def get_application_last_commit(ctx: Context, application_id: str) -> str:
    """Get the last commit that affected an application.
    
    Args:
        application_id: The ID of the application
    """
    try:
        commit = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/applications/{applicationId}/commits/last".replace("{applicationId}", application_id)
        )
        
        if not commit:
            return f"No commit found for application {application_id}."
        
        result = f"Last commit for application {application_id}:\n\n"
        result += f"Reference: {commit.get('reference')}\n"
        result += f"Message: {commit.get('message')}\n"
        result += f"Created: {commit.get('createdAt')}\n"
        
        author_name = commit.get('authorName')
        if author_name:
            result += f"Author: {author_name}"
            
            author_email = commit.get('authorEmail')
            if author_email:
                result += f" <{author_email}>"
                
            result += "\n"
            
        committer_name = commit.get('committerName')
        if committer_name and committer_name != author_name:
            result += f"Committer: {committer_name}\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving last commit: {str(e)}"

@mcp.tool()
async def get_application_tags(ctx: Context, application_id: str) -> str:
    """Get tags for an application.
    
    Args:
        application_id: The ID of the application
    """
    try:
        tags = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/applications/{applicationId}/tags".replace("{applicationId}", application_id)
        )
        
        if not tags:
            return f"No tags found for application {application_id}."
        
        result = f"Tags for application {application_id}:\n\n"
        for tag in tags:
            result += f"Name: {tag.get('name')}\n"
            result += f"Reference: {tag.get('reference')}\n"
            result += f"Message: {tag.get('message')}\n"
            result += f"Created: {tag.get('createdAt')}\n"
            
            author_name = tag.get('authorName')
            if author_name:
                result += f"Author: {author_name}"
                
                author_email = tag.get('authorEmail')
                if author_email:
                    result += f" <{author_email}>"
                    
                result += "\n"
                
            committer_name = tag.get('committerName')
            if committer_name and committer_name != author_name:
                result += f"Committer: {committer_name}\n"
                
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving tags: {str(e)}"

@mcp.tool()
async def add_application_variable(
    ctx: Context,
    application_id: str,
    name: str,
    input_type: str,
    required: bool = False,
    multiline: Optional[bool] = None,
    description: Optional[str] = None,
    default_value: Optional[str] = None
) -> str:
    """Add a single environment variable to an application while preserving existing variables.
    
    Args:
        application_id: The ID of the application to update
        name: Name of the variable
        input_type: Type of the variable input. Must be one of: "Topic", "FreeText", "HiddenText", "InputTopic", "OutputTopic", "Secret"
        required: Whether the variable is mandatory (default: False)
        multiline: Whether the variable value can be multiline (optional)
        description: Description of the variable (optional)
        default_value: Default value for the variable (optional)
    
    Note: This is a high-level helper that combines create_application_variable and update_application_variables.
    It will first fetch existing variables, then append the new one, preserving all existing variables.
    """
    try:
        # Create the new variable
        valid_input_types = ["Topic", "FreeText", "HiddenText", "InputTopic", "OutputTopic", "Secret"]
        
        if input_type not in valid_input_types:
            return f"Error: Invalid input_type '{input_type}'. Must be one of: {', '.join(valid_input_types)}"
        
        new_variable = {
            "name": name,
            "inputType": input_type,
            "required": required
        }
        
        if multiline is not None:
            new_variable["multiline"] = multiline
            
        if description is not None:
            new_variable["description"] = description
            
        if default_value is not None:
            new_variable["defaultValue"] = default_value
        
        # Get the current application details
        current_app = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/applications/{applicationId}".replace("{applicationId}", application_id)
        )
        
        if not current_app:
            return f"No application found with ID {application_id}."
        
        # Get existing variables
        existing_variables = current_app.get('variables', [])
        
        # Check if a variable with this name already exists
        for var in existing_variables:
            if var.get('name') == name:
                return f"Error: A variable with name '{name}' already exists in application {application_id}. Use update_application_variables to modify it."
        
        # Create the final list of variables (existing + new)
        final_variables = existing_variables + [new_variable]
        
        # Update the application
        payload = {
            "variables": final_variables
        }
        
        application = await make_quix_request(
            ctx, 
            "PATCH", 
            "{workspaceId}/applications/{applicationId}".replace("{applicationId}", application_id),
            json=payload
        )
        
        if not application:
            return f"Failed to update variables for application {application_id}."
        
        # Format the response
        result = f"Successfully added environment variable '{name}' to application '{application.get('name')}' (ID: {application_id}):\n\n"
        
        result += f"• {name} ({input_type})\n"
        
        if description:
            result += f"  Description: {description}\n"
            
        if default_value:
            result += f"  Default Value: {default_value}\n"
            
        result += f"  Required: {required}\n"
        
        if multiline:
            result += f"  Multiline: {multiline}\n"
        
        result += f"\nTotal environment variables: {len(final_variables)}"
        
        return result
    except QuixApiError as e:
        return f"Error adding application variable: {str(e)}"

@mcp.tool()
async def create_application_variable(
    ctx: Context,
    name: str,
    input_type: str,
    required: bool = False,
    multiline: Optional[bool] = None,
    description: Optional[str] = None,
    default_value: Optional[str] = None
) -> Dict[str, Any]:
    """Create an application variable object following the ApplicationVariable schema.
    This is a helper function to create properly formatted variable objects for use with
    update_application and update_application_variables.
    
    Args:
        name: Name of the variable
        input_type: Type of the variable input. Must be one of: "Topic", "FreeText", "HiddenText", "InputTopic", "OutputTopic", "Secret"
        required: Whether the variable is mandatory (default: False)
        multiline: Whether the variable value can be multiline (optional)
        description: Description of the variable (optional)
        default_value: Default value for the variable (optional)
        
    Returns:
        A properly formatted ApplicationVariable object
    """
    valid_input_types = ["Topic", "FreeText", "HiddenText", "InputTopic", "OutputTopic", "Secret"]
    
    if input_type not in valid_input_types:
        raise ValueError(f"Invalid input_type '{input_type}'. Must be one of: {', '.join(valid_input_types)}")
    
    variable = {
        "name": name,
        "inputType": input_type,
        "required": required
    }
    
    if multiline is not None:
        variable["multiline"] = multiline
        
    if description is not None:
        variable["description"] = description
        
    if default_value is not None:
        variable["defaultValue"] = default_value
        
    return variable

@mcp.tool()
async def update_application_variables(
    ctx: Context, 
    application_id: str, 
    variables: List[Dict[str, Any]],
    append: bool = True
) -> str:
    """Update the environment variables for an application.
    
    Args:
        application_id: The ID of the application to update
        variables: List of environment variables to set, following the ApplicationVariable schema.
            Each variable must include the following fields:
                - name: Name of the variable
                - inputType: One of "Topic", "FreeText", "HiddenText", "InputTopic", "OutputTopic", "Secret"
                - required: Whether the variable is mandatory (true/false)
            Optional fields:
                - multiline: Whether the variable value can be multiline (true/false)
                - description: Description of the variable
                - defaultValue: Default value for the variable
        append: Whether to append these variables to existing ones (True) or replace them all (False).
            IMPORTANT: Due to API constraints, PATCH operations completely overwrite arrays.
            When append=True (default), we'll first fetch existing variables and combine them with new ones.
            When append=False, only the provided variables will be kept (all others will be removed).
            
    Example:
        [
            {
                "name": "input-topic",
                "inputType": "Topic",
                "multiline": true,
                "description": "The input topic",
                "defaultValue": "input-data",
                "required": true
            },
            {
                "name": "api-key",
                "inputType": "Secret",
                "description": "API Key for external service",
                "required": true
            }
        ]
        
    Note: You can use the create_application_variable tool to create properly formatted variable objects.
    """
    try:
        # Validate the input variables
        valid_input_types = ["Topic", "FreeText", "HiddenText", "InputTopic", "OutputTopic", "Secret"]
        
        for var in variables:
            # Check for required fields
            if "name" not in var:
                return f"Error: Missing 'name' field in variable {var}"
                
            if "inputType" not in var:
                return f"Error: Missing 'inputType' field in variable '{var.get('name')}'"
                
            if var.get("inputType") not in valid_input_types:
                return f"Error: Invalid 'inputType' value '{var.get('inputType')}' for variable '{var.get('name')}'. Must be one of: {', '.join(valid_input_types)}"
                
            if "required" not in var:
                return f"Error: Missing 'required' field in variable '{var.get('name')}'"
        
        # Get the current application details
        current_app = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/applications/{applicationId}".replace("{applicationId}", application_id)
        )
        
        if not current_app:
            return f"No application found with ID {application_id}."
        
        # Determine the final set of variables to apply
        final_variables = []
        
        if append:
            # Get existing variables
            existing_variables = current_app.get('variables', [])
            
            # Create a lookup of new variable names for quick checking
            new_variable_names = {var.get('name'): var for var in variables}
            
            # Start with existing variables that aren't being updated
            for var in existing_variables:
                var_name = var.get('name')
                if var_name not in new_variable_names:
                    final_variables.append(var)
                
            # Add all new variables
            final_variables.extend(variables)
            
            operation_description = "updated/added"
        else:
            # Complete replacement
            final_variables = variables
            operation_description = "replaced all with new"
        
        # Prepare the update payload with the final variables
        payload = {
            "variables": final_variables
        }
        
        # Update the application
        application = await make_quix_request(
            ctx, 
            "PATCH", 
            "{workspaceId}/applications/{applicationId}".replace("{applicationId}", application_id),
            json=payload
        )
        
        if not application:
            return f"Failed to update variables for application {application_id}."
        
        # Format the response with the updated variables
        result = f"Successfully {operation_description} environment variables for application '{application.get('name')}' (ID: {application_id}):\n\n"
        
        # First show the variables that were just modified/added
        result += "Modified/Added Variables:\n"
        for var in variables:
            result += f"• {var.get('name')} ({var.get('inputType')})\n"
            
            if var.get('description'):
                result += f"  Description: {var.get('description')}\n"
                
            if var.get('defaultValue'):
                result += f"  Default Value: {var.get('defaultValue')}\n"
                
            result += f"  Required: {var.get('required')}\n"
            
            if var.get('multiline'):
                result += f"  Multiline: {var.get('multiline')}\n"
                
            result += "\n"
        
        # If there are other variables, list them too
        other_vars = [var for var in final_variables if var.get('name') not in [v.get('name') for v in variables]]
        if other_vars and append:
            result += "Other Existing Variables:\n"
            for var in other_vars:
                result += f"• {var.get('name')} ({var.get('inputType')})\n"
            result += "\n"
        
        # Show total count
        result += f"Total environment variables: {len(final_variables)}"
        
        return result
    except QuixApiError as e:
        return f"Error updating application variables: {str(e)}"

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
    import argparse
    
    # Load environment variables from .env file if it exists
    env_path = Path('.env')
    if env_path.exists():
        dotenv.load_dotenv(env_path)
        logger.info("Loaded environment variables from .env file")
    
    parser = argparse.ArgumentParser(description='Run Quix Applications MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--quix-token', help='Quix Personal Access Token (PAT)')
    parser.add_argument('--quix-base-url', help='Quix Portal Base URL (e.g., https://portal-myenv.platform.quix.io/)')
    parser.add_argument('--quix-workspace', help='Quix Workspace ID')
    parser.add_argument('--env-file', help='Path to .env file (default: .env in current directory)')
    args = parser.parse_args()
    
    # Load from specific env file if provided
    if args.env_file:
        env_path = Path(args.env_file)
        if env_path.exists():
            dotenv.load_dotenv(env_path)
            logger.info(f"Loaded environment variables from {args.env_file}")
        else:
            logger.warning(f"Environment file {args.env_file} not found")
    
    # Set environment variables if provided via arguments (overrides .env)
    if args.quix_token:
        os.environ['QUIX_TOKEN'] = args.quix_token
    
    if args.quix_base_url:
        os.environ['QUIX_BASE_URL'] = args.quix_base_url
        
    if args.quix_workspace:
        os.environ['QUIX_WORKSPACE'] = args.quix_workspace
    
    # Check if required environment variables are set
    if not os.environ.get('QUIX_TOKEN'):
        logger.error("QUIX_TOKEN environment variable is required. Please set it with --quix-token or in your .env file")
        exit(1)
    
    if not os.environ.get('QUIX_BASE_URL'):
        logger.error("QUIX_BASE_URL environment variable is required. Please set it with --quix-base-url or in your .env file")
        exit(1)
        
    if not os.environ.get('QUIX_WORKSPACE'):
        logger.error("QUIX_WORKSPACE environment variable is required. Please set it with --quix-workspace or in your .env file")
        exit(1)
    
    # Bind SSE request handling to MCP server
    mcp_server = mcp._mcp_server
    starlette_app = create_starlette_app(mcp_server, debug=True)
    
    logger.info(f"Starting Quix Applications MCP server on {args.host}:{args.port}")
    logger.info(f"Using Quix Portal at {os.environ.get('QUIX_BASE_URL')}")
    logger.info(f"Using Quix Workspace {os.environ.get('QUIX_WORKSPACE')}")
    
    uvicorn.run(starlette_app, host=args.host, port=args.port)