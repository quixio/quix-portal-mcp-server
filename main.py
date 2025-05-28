import os
import asyncio
import logging
import httpx
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Dict, List

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

from config import load_config


# Initialize FastMCP server for Quix Applications
mcp = FastMCP("quix")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Quix API constants
DEFAULT_API_VERSION_HEADER = "2.0"

# Define enums to match the schemas in the Swagger definition
class TopicCleanupPolicy(str, Enum):
    DELETE = "Delete"
    COMPACT = "Compact"
    DELETE_AND_COMPACT = "DeleteAndCompact"

class DeploymentType(str, Enum):
    SERVICE = "Service"
    JOB = "Job"

class DeploymentGitReferenceType(str, Enum):
    COMMIT = "Commit"
    TAG = "Tag"
    ANY = "Any"

class DeploymentStatus(str, Enum):
    QUEUED_FOR_BUILD = "QueuedForBuild"
    BUILDING = "Building"
    DELETING = "Deleting"
    BUILD_FAILED = "BuildFailed"
    BUILD_SUCCESSFUL = "BuildSuccessful"
    QUEUED_FOR_DEPLOYMENT = "QueuedForDeployment"
    DEPLOYING = "Deploying"
    STARTING = "Starting"
    DEPLOYMENT_FAILED = "DeploymentFailed"
    RUNNING = "Running"
    STOPPING = "Stopping"
    RUNTIME_ERROR = "RuntimeError"
    COMPLETED = "Completed"
    STOPPED = "Stopped"

class DeploymentUpdateStatus(str, Enum):
    NONE = "None"
    QUEUED_FOR_BUILD = "QueuedForBuild"
    BUILDING = "Building"
    BUILD_FAILED = "BuildFailed"
    BUILD_SUCCESSFUL = "BuildSuccessful"
    QUEUED_FOR_DEPLOYMENT = "QueuedForDeployment"
    DEPLOYING = "Deploying"
    DEPLOYMENT_FAILED = "DeploymentFailed"

class VariableInputType(str, Enum):
    TOPIC = "Topic"
    FREE_TEXT = "FreeText"
    HIDDEN_TEXT = "HiddenText"
    INPUT_TOPIC = "InputTopic"
    OUTPUT_TOPIC = "OutputTopic"
    SECRET = "Secret"

class LogDirection(str, Enum):
    FORWARD = "Forward"
    BACKWARD = "Backward"

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


# =========================================
# Deployment Tools
# =========================================

@mcp.tool()
async def get_deployments(ctx: Context, application_id: Optional[str] = None) -> str:
    """Get all deployments in the workspace, optionally filtered by application ID.
    
    Args:
        application_id: Optional application ID to filter deployments by
    """
    try:
        # Build query parameters if needed
        params = {}
        if application_id:
            params["applicationId"] = application_id
            
        deployments = await make_quix_request(
            ctx, 
            "GET", 
            "workspaces/{workspaceId}/deployments",
            params=params
        )
        
        if not deployments or len(deployments) == 0:
            return "No deployments found in the workspace."
        
        result = "Deployments:\n\n"
        for deployment in deployments:
            result += f"ID: {deployment.get('deploymentId')}\n"
            result += f"Name: {deployment.get('name')}\n"
            
            # Add application info if present
            app_id = deployment.get('applicationId')
            if app_id:
                result += f"Application ID: {app_id}\n"
                
            app_name = deployment.get('applicationName')
            if app_name:
                result += f"Application Name: {app_name}\n"
                
            # Add status information
            status = deployment.get('status')
            if status:
                result += f"Status: {status}\n"
                
            status_reason = deployment.get('statusReason')
            if status_reason:
                result += f"Status Reason: {status_reason}\n"
                
            # Add deployment type
            deployment_type = deployment.get('deploymentType')
            if deployment_type:
                result += f"Type: {deployment_type}\n"
                
            # Add resource info
            replicas = deployment.get('replicas')
            if replicas is not None:
                result += f"Replicas: {replicas}\n"
                
            cpu = deployment.get('cpuMillicores')
            if cpu is not None:
                result += f"CPU Millicores: {cpu}\n"
                
            memory = deployment.get('memoryInMb')
            if memory is not None:
                result += f"Memory (MB): {memory}\n"
                
            # Add state information if present
            state_enabled = deployment.get('stateEnabled')
            if state_enabled is not None:
                result += f"State Enabled: {state_enabled}\n"
                
            state_size = deployment.get('stateSize')
            if state_size is not None:
                result += f"State Size (GB): {state_size}\n"
                
            # Add public access info if present
            public_access = deployment.get('publicAccess')
            if public_access is not None:
                result += f"Public Access: {public_access}\n"
                
            url_prefix = deployment.get('urlPrefix')
            if url_prefix:
                result += f"URL Prefix: {url_prefix}\n"
                
            # Add git info if present
            git_ref = deployment.get('gitReference')
            if git_ref:
                result += f"Git Reference: {git_ref}\n"
                
            git_ref_type = deployment.get('gitReferenceType')
            if git_ref_type:
                result += f"Git Reference Type: {git_ref_type}\n"
                
            # Add timestamp info
            created_at = deployment.get('createdAt')
            if created_at:
                result += f"Created At: {created_at}\n"
                
            updated_at = deployment.get('updatedAt')
            if updated_at:
                result += f"Updated At: {updated_at}\n"
                
            # Add restart info
            restart_count = deployment.get('restartCount')
            if restart_count is not None:
                result += f"Restart Count: {restart_count}\n"
                
            time_of_deployment = deployment.get('timeOfDeployment')
            if time_of_deployment:
                result += f"Time of Deployment: {time_of_deployment}\n"
                
            started_at = deployment.get('startedAt')
            if started_at:
                result += f"Started At: {started_at}\n"
                
            # Add version tracking info
            use_latest = deployment.get('useLatest')
            if use_latest is not None:
                result += f"Use Latest Version: {use_latest}\n"
                
            latest_version = deployment.get('latestVersion')
            if latest_version:
                result += f"Latest Version: {latest_version}\n"
                
            latest_out_of_sync = deployment.get('latestOutOfSync')
            if latest_out_of_sync is not None:
                result += f"Latest Out of Sync: {latest_out_of_sync}\n"
                
            application_is_missing = deployment.get('applicationIsMissing')
            if application_is_missing is not None:
                result += f"Application Is Missing: {application_is_missing}\n"
                
            # Add image info if present
            image_uri = deployment.get('imageUri')
            if image_uri:
                result += f"Image URI: {image_uri}\n"
                
            # Add network info if present
            network = deployment.get('network')
            if network:
                service_name = network.get('serviceName')
                if service_name:
                    result += f"Network Service Name: {service_name}\n"
                    
                ports = network.get('ports')
                if ports and len(ports) > 0:
                    result += "Port Mappings:\n"
                    for port in ports:
                        port_num = port.get('port')
                        target_port = port.get('targetPort', port_num)
                        result += f"  {port_num} -> {target_port}\n"
                    
            result += "-" * 40 + "\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_deployment(ctx: Context, deployment_id: str) -> str:
    """Get details of a specific deployment.
    
    Args:
        deployment_id: The ID of the deployment to retrieve
    """
    try:
        deployment = await make_quix_request(
            ctx, 
            "GET", 
            f"deployments/{deployment_id}"
        )
        
        if not deployment:
            return f"No deployment found with ID {deployment_id}."
        
        result = "Deployment Details:\n\n"
        result += f"ID: {deployment.get('deploymentId')}\n"
        result += f"Name: {deployment.get('name')}\n"
        result += f"Workspace ID: {deployment.get('workspaceId')}\n"
        
        # Add application info if present
        app_id = deployment.get('applicationId')
        if app_id:
            result += f"Application ID: {app_id}\n"
            
        app_name = deployment.get('applicationName')
        if app_name:
            result += f"Application Name: {app_name}\n"
            
        # Add status information
        status = deployment.get('status')
        if status:
            result += f"Status: {status}\n"
            
        status_reason = deployment.get('statusReason')
        if status_reason:
            result += f"Status Reason: {status_reason}\n"
            
        # Add update status if present
        update_status = deployment.get('updateStatus')
        if update_status:
            result += f"Update Status: {update_status}\n"
            
        # Add deployment type
        deployment_type = deployment.get('deploymentType')
        if deployment_type:
            result += f"Type: {deployment_type}\n"
            
        # Add resource info
        replicas = deployment.get('replicas')
        if replicas is not None:
            result += f"Replicas: {replicas}\n"
            
        cpu = deployment.get('cpuMillicores')
        if cpu is not None:
            result += f"CPU Millicores: {cpu}\n"
            
        memory = deployment.get('memoryInMb')
        if memory is not None:
            result += f"Memory (MB): {memory}\n"
            
        # Add state information if present
        state_enabled = deployment.get('stateEnabled')
        if state_enabled is not None:
            result += f"State Enabled: {state_enabled}\n"
            
        state_size = deployment.get('stateSize')
        if state_size is not None:
            result += f"State Size (GB): {state_size}\n"
            
        # Add public access info if present
        public_access = deployment.get('publicAccess')
        if public_access is not None:
            result += f"Public Access: {public_access}\n"
            
        url_prefix = deployment.get('urlPrefix')
        if url_prefix:
            result += f"URL Prefix: {url_prefix}\n"
            
        # Add git info if present
        git_ref = deployment.get('gitReference')
        if git_ref:
            result += f"Git Reference: {git_ref}\n"
            
        git_ref_type = deployment.get('gitReferenceType')
        if git_ref_type:
            result += f"Git Reference Type: {git_ref_type}\n"
            
        # Add build info if present
        build_id = deployment.get('buildId')
        if build_id:
            result += f"Build ID: {build_id}\n"
            
        update_build_id = deployment.get('updateBuildId')
        if update_build_id:
            result += f"Update Build ID: {update_build_id}\n"
            
        # Add library info if present
        library_item_id = deployment.get('libraryItemId')
        if library_item_id:
            result += f"Library Item ID: {library_item_id}\n"
            
        library_item_commit_ref = deployment.get('libraryItemCommitReference')
        if library_item_commit_ref:
            result += f"Library Item Commit Reference: {library_item_commit_ref}\n"
            
        using_library_item_build = deployment.get('usingLibraryItemBuild')
        if using_library_item_build is not None:
            result += f"Using Library Item Build: {using_library_item_build}\n"
            
        # Add timestamp info
        created_at = deployment.get('createdAt')
        if created_at:
            result += f"Created At: {created_at}\n"
            
        updated_at = deployment.get('updatedAt')
        if updated_at:
            result += f"Updated At: {updated_at}\n"
            
        # Add restart info
        restart_count = deployment.get('restartCount')
        if restart_count is not None:
            result += f"Restart Count: {restart_count}\n"
            
        time_of_deployment = deployment.get('timeOfDeployment')
        if time_of_deployment:
            result += f"Time of Deployment: {time_of_deployment}\n"
            
        started_at = deployment.get('startedAt')
        if started_at:
            result += f"Started At: {started_at}\n"
            
        # Add version tracking info
        use_latest = deployment.get('useLatest')
        if use_latest is not None:
            result += f"Use Latest Version: {use_latest}\n"
            
        latest_version = deployment.get('latestVersion')
        if latest_version:
            result += f"Latest Version: {latest_version}\n"
            
        latest_out_of_sync = deployment.get('latestOutOfSync')
        if latest_out_of_sync is not None:
            result += f"Latest Out of Sync: {latest_out_of_sync}\n"
            
        application_is_missing = deployment.get('applicationIsMissing')
        if application_is_missing is not None:
            result += f"Application Is Missing: {application_is_missing}\n"
            
        # Add image info if present
        image_uri = deployment.get('imageUri')
        if image_uri:
            result += f"Image URI: {image_uri}\n"
            
        # Add network info if present
        network = deployment.get('network')
        if network:
            service_name = network.get('serviceName')
            if service_name:
                result += f"Network Service Name: {service_name}\n"
                
            ports = network.get('ports')
            if ports and len(ports) > 0:
                result += "Port Mappings:\n"
                for port in ports:
                    port_num = port.get('port')
                    target_port = port.get('targetPort', port_num)
                    result += f"  {port_num} -> {target_port}\n"
                
        # Add variables if present
        variables = deployment.get('variables')
        if variables and len(variables) > 0:
            result += "\nEnvironment Variables:\n"
            for var_name, var_info in variables.items():
                result += f"• {var_name} ({var_info.get('inputType')})\n"
                
                description = var_info.get('description')
                if description:
                    result += f"  Description: {description}\n"
                    
                value = var_info.get('value')
                if value:
                    # Don't show actual value for secrets
                    if var_info.get('inputType') == "Secret":
                        result += f"  Value: [HIDDEN]\n"
                    else:
                        result += f"  Value: {value}\n"
                    
                required = var_info.get('required')
                if required is not None:
                    result += f"  Required: {required}\n"
                    
                multiline = var_info.get('multiline')
                if multiline is not None:
                    result += f"  Multiline: {multiline}\n"
                    
        # Add creation info if present
        created_by = deployment.get('createdBy')
        if created_by:
            result += "\nCreated By:\n"
            result += f"  User ID: {created_by.get('userId')}\n"
            result += f"  Email: {created_by.get('email')}\n"
            result += f"  Name: {created_by.get('firstName')} {created_by.get('lastName')}\n"
            result += f"  Date: {created_by.get('dateTime')}\n"
            
        updated_by = deployment.get('updatedBy')
        if updated_by:
            result += "\nUpdated By:\n"
            result += f"  User ID: {updated_by.get('userId')}\n"
            result += f"  Email: {updated_by.get('email')}\n"
            result += f"  Name: {updated_by.get('firstName')} {updated_by.get('lastName')}\n"
            result += f"  Date: {updated_by.get('dateTime')}\n"
            
        # Add scratchpad info if present
        scratchpad_info = deployment.get('scratchpadInfo')
        if scratchpad_info:
            is_locked = scratchpad_info.get('isLocked')
            if is_locked is not None:
                result += f"\nScratchpad Locked: {is_locked}\n"
                
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def create_deployment(
    ctx: Context,
    name: str,
    application_id: str,
    replicas: int = 1,
    cpu_millicores: int = 1000,
    memory_in_mb: int = 1024,
    deployment_type: str = "Service",
    git_reference: Optional[str] = None,
    git_reference_type: str = "Commit",
    auto_start: bool = True,
    use_latest: bool = False,
    image_uri: Optional[str] = None,
    public_access: bool = False,
    url_prefix: Optional[str] = None,
    state_enabled: bool = False,
    state_size: int = 1,
    variables: Optional[Dict[str, Dict[str, Any]]] = None,
    ports: Optional[List[Dict[str, int]]] = None,
    service_name: Optional[str] = None
) -> str:
    """Create a new deployment. Only use this tool when you are explicitly asked to create a deployment. In all other cases. only use this tool after confirming with the user first.
    
    Args:
        name: User defined deployment name
        application_id: ID of the application to deploy
        replicas: Number of pods in parallel (default: 1)
        cpu_millicores: Maximum CPU millicores reserved (default: 1000)
        memory_in_mb: Maximum memory reserved in MB (default: 1024)
        deployment_type: Type of deployment (Service or Job, default: Service)
        git_reference: The git reference to deploy (commit or tag)
        git_reference_type: Type of git reference (Commit, Tag, or Any, default: Commit)
        auto_start: Whether to start the deployment automatically (default: True)
        use_latest: Whether to use the latest version for the deployment (default: False)
        image_uri: Image URI when deploying directly an image
        public_access: Whether the service has public URL access (default: False)
        url_prefix: Prefix of the public URL (required if public_access is True)
        state_enabled: Whether the service has state feature enabled (default: False)
        state_size: State size in GB (default: 1)
        variables: Dictionary of deployment variables {name: {inputType, description, required, value, multiline}}
        ports: List of port mappings [{port, targetPort}]
        service_name: Network service name
    """
    try:
        # Validate input
        if deployment_type not in [t.value for t in DeploymentType]:
            return f"Error: Invalid deployment type. Must be one of: {', '.join([t.value for t in DeploymentType])}"
            
        if git_reference_type not in [t.value for t in DeploymentGitReferenceType]:
            return f"Error: Invalid git reference type. Must be one of: {', '.join([t.value for t in DeploymentGitReferenceType])}"
            
        if public_access and not url_prefix:
            return "Error: url_prefix is required when public_access is True."
            
        # Build the request payload according to the DeploymentCreateRequestV2 schema
        payload = {
            "workspaceId": os.environ.get("QUIX_WORKSPACE"),
            "applicationId": application_id,
            "name": name,
            "replicas": replicas,
            "cpuMillicores": cpu_millicores,
            "memoryInMb": memory_in_mb,
            "publicAccess": public_access,
            "stateEnabled": state_enabled,
            "stateSize": state_size,
            "deploymentType": deployment_type,
            "gitReferenceType": git_reference_type,
            "autoStart": auto_start,
            "useLatest": use_latest
        }
        
        # Add optional parameters if provided
        if git_reference:
            payload["gitReference"] = git_reference
            
        if url_prefix:
            payload["urlPrefix"] = url_prefix
            
        if image_uri:
            payload["imageUri"] = image_uri
            
        if variables:
            payload["variables"] = variables
            
        # Add network configuration if specified
        if ports or service_name:
            network = {}
            
            if service_name:
                network["serviceName"] = service_name
                
            if ports:
                network["ports"] = ports
                
            payload["network"] = network
            
        deployment = await make_quix_request(
            ctx,
            "POST",
            "deployments",
            json=payload
        )
        
        if not deployment:
            return f"Failed to create deployment '{name}'."
            
        result = f"Successfully created deployment '{name}'.\n\n"
        result += f"Deployment ID: {deployment.get('deploymentId')}\n"
        result += f"Status: {deployment.get('status')}\n"
        
        if deployment.get('statusReason'):
            result += f"Status Reason: {deployment.get('statusReason')}\n"
            
        # Show git info
        git_ref = deployment.get('gitReference')
        if git_ref:
            result += f"Git Reference: {git_ref}\n"
            
        # Show URL if public
        is_public = deployment.get('publicAccess')
        url_prefix = deployment.get('urlPrefix')
        if is_public and url_prefix:
            result += f"URL Prefix: {url_prefix}\n"
            
        return result
    except QuixApiError as e:
        return f"Error creating deployment: {str(e)}"

@mcp.tool()
async def update_deployment(
    ctx: Context,
    deployment_id: str,
    name: Optional[str] = None,
    replicas: Optional[int] = None,
    cpu_millicores: Optional[int] = None,
    memory_in_mb: Optional[int] = None,
    deployment_type: Optional[str] = None,
    git_reference: Optional[str] = None,
    git_reference_type: Optional[str] = None,
    use_latest: Optional[bool] = None,
    image_uri: Optional[str] = None,
    public_access: Optional[bool] = None,
    url_prefix: Optional[str] = None,
    state_enabled: Optional[bool] = None,
    state_size: Optional[int] = None,
    variables: Optional[Dict[str, Dict[str, Any]]] = None,
    network: Optional[Dict[str, Any]] = None,
    disable_network: bool = False,
    disabled: Optional[bool] = None
) -> str:
    """Update an existing deployment.
    
    Args:
        deployment_id: The ID of the deployment to update
        name: Optional new name for the deployment
        replicas: Optional new number of pods to run in parallel
        cpu_millicores: Optional new maximum CPU millicores
        memory_in_mb: Optional new maximum memory in MB
        deployment_type: Optional new deployment type (Service or Job)
        git_reference: Optional new git reference to deploy
        git_reference_type: Optional new git reference type (Commit, Tag, or Any)
        use_latest: Optional flag to use latest version for the deployment
        image_uri: Optional new image URI
        public_access: Optional flag for public URL access
        url_prefix: Optional new prefix of the public URL
        state_enabled: Optional flag for state feature
        state_size: Optional new state size in GB
        variables: Optional new dictionary of variables
        network: Optional new network configuration
        disable_network: Whether to disable network access (default: False)
        disabled: Optional flag to indicate if deployment exists only in database
    """
    try:
        # Validate input if provided
        if deployment_type and deployment_type not in [t.value for t in DeploymentType]:
            return f"Error: Invalid deployment type. Must be one of: {', '.join([t.value for t in DeploymentType])}"
            
        if git_reference_type and git_reference_type not in [t.value for t in DeploymentGitReferenceType]:
            return f"Error: Invalid git reference type. Must be one of: {', '.join([t.value for t in DeploymentGitReferenceType])}"
            
        # Build the request payload according to the DeploymentPatchRequestV2 schema
        payload = {}
        
        # Add parameters if provided
        if name is not None:
            payload["name"] = name
            
        if replicas is not None:
            payload["replicas"] = replicas
            
        if cpu_millicores is not None:
            payload["cpuMillicores"] = cpu_millicores
            
        if memory_in_mb is not None:
            payload["memoryInMb"] = memory_in_mb
            
        if deployment_type is not None:
            payload["deploymentType"] = deployment_type
            
        if git_reference is not None:
            payload["gitReference"] = git_reference
            
        if git_reference_type is not None:
            payload["gitReferenceType"] = git_reference_type
            
        if use_latest is not None:
            payload["useLatest"] = use_latest
            
        if image_uri is not None:
            payload["imageUri"] = image_uri
            
        if public_access is not None:
            payload["publicAccess"] = public_access
            
        if url_prefix is not None:
            payload["urlPrefix"] = url_prefix
            
        if state_enabled is not None:
            payload["stateEnabled"] = state_enabled
            
        if state_size is not None:
            payload["stateSize"] = state_size
            
        if variables is not None:
            payload["variables"] = variables
            
        if network is not None:
            payload["network"] = network
            
        if disable_network:
            payload["disableNetwork"] = True
            
        if disabled is not None:
            payload["disabled"] = disabled
            
        deployment = await make_quix_request(
            ctx,
            "PATCH",
            f"deployments/{deployment_id}",
            json=payload
        )
        
        if not deployment:
            return f"Failed to update deployment with ID {deployment_id}."
            
        result = f"Successfully updated deployment.\n\n"
        result += f"Deployment ID: {deployment.get('deploymentId')}\n"
        result += f"Name: {deployment.get('name')}\n"
        result += f"Status: {deployment.get('status')}\n"
        
        if deployment.get('statusReason'):
            result += f"Status Reason: {deployment.get('statusReason')}\n"
            
        # Show update status
        update_status = deployment.get('updateStatus')
        if update_status:
            result += f"Update Status: {update_status}\n"
            
        # Show updated git info
        git_ref = deployment.get('gitReference')
        if git_ref:
            result += f"Git Reference: {git_ref}\n"
            
        # Show updated resources
        if replicas is not None:
            result += f"Replicas: {deployment.get('replicas')}\n"
            
        if cpu_millicores is not None:
            result += f"CPU Millicores: {deployment.get('cpuMillicores')}\n"
            
        if memory_in_mb is not None:
            result += f"Memory (MB): {deployment.get('memoryInMb')}\n"
            
        # Show updated URL if public
        if public_access is not None or url_prefix is not None:
            is_public = deployment.get('publicAccess')
            url_prefix = deployment.get('urlPrefix')
            result += f"Public Access: {is_public}\n"
            if is_public and url_prefix:
                result += f"URL Prefix: {url_prefix}\n"
                
        return result
    except QuixApiError as e:
        return f"Error updating deployment: {str(e)}"

@mcp.tool()
async def delete_deployment(ctx: Context, deployment_id: str) -> str:
    """Delete a deployment.
    
    Args:
        deployment_id: The ID of the deployment to delete
    """
    try:
        await make_quix_request(
            ctx,
            "DELETE",
            f"deployments/{deployment_id}"
        )
        
        return f"Successfully deleted deployment with ID {deployment_id}."
    except QuixApiError as e:
        return f"Error deleting deployment: {str(e)}"

@mcp.tool()
async def start_deployment(ctx: Context, deployment_id: str, bypass_descriptor: bool = False) -> str:
    """Start a deployment.
    
    Args:
        deployment_id: The ID of the deployment to start
        bypass_descriptor: Whether to bypass descriptor checks (default: False)
    """
    try:
        params = {}
        if bypass_descriptor:
            params["bypassDescriptor"] = "true"
            
        await make_quix_request(
            ctx,
            "PUT",
            f"deployments/{deployment_id}/start",
            params=params
        )
        
        return f"Successfully started deployment with ID {deployment_id}."
    except QuixApiError as e:
        return f"Error starting deployment: {str(e)}"

@mcp.tool()
async def stop_deployment(ctx: Context, deployment_id: str, bypass_descriptor: bool = False) -> str:
    """Stop a deployment.
    
    Args:
        deployment_id: The ID of the deployment to stop
        bypass_descriptor: Whether to bypass descriptor checks (default: False)
    """
    try:
        params = {}
        if bypass_descriptor:
            params["bypassDescriptor"] = "true"
            
        await make_quix_request(
            ctx,
            "PUT",
            f"deployments/{deployment_id}/stop",
            params=params
        )
        
        return f"Successfully stopped deployment with ID {deployment_id}."
    except QuixApiError as e:
        return f"Error stopping deployment: {str(e)}"

@mcp.tool()
async def cancel_deployment_update(ctx: Context, deployment_id: str) -> str:
    """Cancel a deployment update.
    
    Args:
        deployment_id: The ID of the deployment to cancel update for
    """
    try:
        await make_quix_request(
            ctx,
            "PUT",
            f"deployments/{deployment_id}/update/cancel"
        )
        
        return f"Successfully cancelled update for deployment with ID {deployment_id}."
    except QuixApiError as e:
        return f"Error cancelling deployment update: {str(e)}"

@mcp.tool()
async def retry_deployment_update(ctx: Context, deployment_id: str) -> str:
    """Retry a deployment update.
    
    Args:
        deployment_id: The ID of the deployment to retry update for
    """
    try:
        await make_quix_request(
            ctx,
            "PUT",
            f"deployments/{deployment_id}/update/retry"
        )
        
        return f"Successfully retried update for deployment with ID {deployment_id}."
    except QuixApiError as e:
        return f"Error retrying deployment update: {str(e)}"

@mcp.tool()
async def get_deployment_replicas(ctx: Context, deployment_id: str) -> str:
    """Get the replicas of a deployment.
    
    Args:
        deployment_id: The ID of the deployment
    """
    try:
        replicas = await make_quix_request(
            ctx,
            "GET",
            f"deployments/{deployment_id}/replicas"
        )
        
        if not replicas or len(replicas) == 0:
            return f"No replicas found for deployment with ID {deployment_id}."
            
        result = f"Replicas for deployment {deployment_id}:\n\n"
        for i, replica in enumerate(replicas):
            result += f"{i+1}. {replica}\n"
            
        return result
    except QuixApiError as e:
        return f"Error getting deployment replicas: {str(e)}"

@mcp.tool()
async def get_deployment_secret_keys(ctx: Context) -> str:
    """Get deployment secrets keys in the workspace.
    """
    try:
        workspace_id = os.environ.get("QUIX_WORKSPACE")
        if not workspace_id:
            return "Missing QUIX_WORKSPACE environment variable. Please set your Quix Workspace ID."
            
        secrets = await make_quix_request(
            ctx,
            "GET",
            f"workspaces/{workspace_id}/deployments/secrets"
        )
        
        if not secrets or len(secrets) == 0:
            return "No deployment secrets found in this workspace."
            
        result = "Deployment Secret Keys:\n\n"
        for category, keys in secrets.items():
            result += f"Category: {category}\n"
            for key in keys:
                result += f"- {key}\n"
            result += "\n"
            
        return result
    except QuixApiError as e:
        return f"Error getting deployment secret keys: {str(e)}"

@mcp.tool()
async def update_deployments(ctx: Context, deployment_ids: Optional[List[str]] = None) -> str:
    """Update deployments in the workspace.
    
    Args:
        deployment_ids: Optional list of deployment IDs to update (if not specified, all deployments in the workspace will be updated)
    """
    try:
        workspace_id = os.environ.get("QUIX_WORKSPACE")
        if not workspace_id:
            return "Missing QUIX_WORKSPACE environment variable. Please set your Quix Workspace ID."
            
        await make_quix_request(
            ctx,
            "POST",
            f"workspaces/{workspace_id}/deployments/update",
            json=deployment_ids if deployment_ids else []
        )
        
        if deployment_ids and len(deployment_ids) > 0:
            return f"Successfully initiated update for {len(deployment_ids)} deployment(s)."
        else:
            return "Successfully initiated update for all deployments in the workspace."
    except QuixApiError as e:
        return f"Error updating deployments: {str(e)}"

@mcp.tool()
async def get_deployment_logs(
    ctx: Context,
    deployment_id: str,
    replica_id: Optional[str] = None,
    log_type: str = "current"
) -> str:
    """Get logs for a deployment.
    
    Args:
        deployment_id: The ID of the deployment
        replica_id: Optional ID of a specific replica to get logs for
        log_type: Type of logs to retrieve (current, all, buildlogs) (default: current)
    """
    try:
        params = {}
        if replica_id:
            params["replicaId"] = replica_id
            
        # Map log_type to endpoint
        endpoint_map = {
            "current": f"deployments/{deployment_id}/logs/current",
            "all": f"deployments/{deployment_id}/logs/all",
            "buildlogs": f"deployments/{deployment_id}/buildlogs"
        }
        
        if log_type not in endpoint_map:
            return f"Invalid log type: {log_type}. Must be one of: current, all, buildlogs"
            
        logs = await make_quix_request(
            ctx,
            "GET",
            endpoint_map[log_type],
            params=params
        )
        
        if not logs:
            return f"No {log_type} logs found for deployment with ID {deployment_id}."
            
        return logs
    except QuixApiError as e:
        return f"Error getting deployment logs: {str(e)}"

@mcp.tool()
async def get_deployment_logs_by_page(
    ctx: Context,
    deployment_id: str,
    page_number: int = 0,
    lines_per_page: int = 100,
    replica_id: Optional[str] = None
) -> str:
    """Get logs for a deployment by page.
    
    Args:
        deployment_id: The ID of the deployment
        page_number: Page number (default: 0)
        lines_per_page: Lines per page (default: 100)
        replica_id: Optional ID of a specific replica to get logs for
    """
    try:
        params = {
            "pageNumber": page_number,
            "linesPerPage": lines_per_page
        }
        
        if replica_id:
            params["replicaId"] = replica_id
            
        logs = await make_quix_request(
            ctx,
            "GET",
            f"deployments/{deployment_id}/logs/page",
            params=params
        )
        
        if not logs:
            return f"No logs found for deployment with ID {deployment_id} on page {page_number}."
            
        return logs
    except QuixApiError as e:
        return f"Error getting deployment logs by page: {str(e)}"

@mcp.tool()
async def get_deployment_historical_logs(
    ctx: Context,
    deployment_id: str,
    instance_id: Optional[str] = None,
    replica_id: Optional[str] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
    direction: str = "Forward",
    limit: int = 1000
) -> str:
    """Get historical logs for a deployment by date range.
    
    Args:
        deployment_id: The ID of the deployment
        instance_id: Optional instance ID
        replica_id: Optional ID of a specific replica
        start: Optional start time in nanoseconds since epoch
        end: Optional end time in nanoseconds since epoch
        direction: Log direction (Forward or Backward) (default: Forward)
        limit: Maximum number of logs to return (default: 1000)
    """
    try:
        # Validate input
        if direction not in [d.value for d in LogDirection]:
            return f"Error: Invalid direction. Must be one of: {', '.join([d.value for d in LogDirection])}"
            
        params = {
            "limit": limit,
            "direction": direction
        }
        
        if instance_id:
            params["instanceId"] = instance_id
            
        if replica_id:
            params["replicaId"] = replica_id
            
        if start:
            params["start"] = start
            
        if end:
            params["end"] = end
            
        logs = await make_quix_request(
            ctx,
            "GET",
            f"deployments/{deployment_id}/logs/history/filter",
            params=params
        )
        
        if not logs or not logs.get('entries') or len(logs.get('entries')) == 0:
            return f"No historical logs found for deployment with ID {deployment_id} in the specified time range."
            
        instance_id = logs.get('instanceId')
        replica_id = logs.get('replicaId')
        entries = logs.get('entries', [])
        
        result = f"Historical Logs for Deployment {deployment_id}\n"
        if instance_id:
            result += f"Instance ID: {instance_id}\n"
            
        if replica_id:
            result += f"Replica ID: {replica_id}\n"
            
        result += f"Found {len(entries)} log entries\n\n"
        
        for entry in entries:
            timestamp = entry.get('timestamp')
            log = entry.get('log')
            
            # Convert nanoseconds to seconds for readability
            timestamp_sec = timestamp / 1_000_000_000 if timestamp else 0
            
            # Format timestamp as ISO string
            from datetime import datetime, timezone
            timestamp_str = datetime.fromtimestamp(timestamp_sec, tz=timezone.utc).isoformat()
            
            result += f"[{timestamp_str}] {log}\n"
            
        return result
    except QuixApiError as e:
        return f"Error getting historical logs: {str(e)}"

@mcp.tool()
async def get_deployment_historical_log_stats(
    ctx: Context,
    deployment_id: str,
    streams: int = 10,
    start: Optional[int] = None,
    end: Optional[int] = None,
    replica_id: Optional[str] = None
) -> str:
    """Get historical log stats for a deployment.
    
    Args:
        deployment_id: The ID of the deployment
        streams: Number of log stream stats to return (default: 10)
        start: Optional start time in nanoseconds since epoch
        end: Optional end time in nanoseconds since epoch
        replica_id: Optional ID of a specific replica
    """
    try:
        params = {
            "streams": streams
        }
        
        if replica_id:
            params["replicaId"] = replica_id
            
        if start:
            params["start"] = start
            
        if end:
            params["end"] = end
            
        stats = await make_quix_request(
            ctx,
            "GET",
            f"deployments/{deployment_id}/logs/history/stats",
            params=params
        )
        
        if not stats or len(stats) == 0:
            return f"No historical log stats found for deployment with ID {deployment_id}."
            
        result = f"Historical Log Stats for Deployment {deployment_id}\n\n"
        
        for i, stream in enumerate(stats):
            instance_id = stream.get('instanceId')
            replica_id = stream.get('replicaId')
            first_timestamp = stream.get('firstTimestamp')
            last_timestamp = stream.get('lastTimestamp')
            
            result += f"Stream {i+1}:\n"
            if instance_id:
                result += f"  Instance ID: {instance_id}\n"
                
            if replica_id:
                result += f"  Replica ID: {replica_id}\n"
                
            # Convert nanoseconds to seconds for readability
            first_ts_sec = first_timestamp / 1_000_000_000 if first_timestamp else 0
            last_ts_sec = last_timestamp / 1_000_000_000 if last_timestamp else 0
            
            # Format timestamps as ISO strings
            from datetime import datetime, timezone
            first_ts_str = datetime.fromtimestamp(first_ts_sec, tz=timezone.utc).isoformat()
            last_ts_str = datetime.fromtimestamp(last_ts_sec, tz=timezone.utc).isoformat()
            
            result += f"  First Log: {first_ts_str}\n"
            result += f"  Last Log: {last_ts_str}\n"
            result += "\n"
            
        return result
    except QuixApiError as e:
        return f"Error getting historical log stats: {str(e)}"

@mcp.tool()
async def download_deployment_logs(
    ctx: Context,
    deployment_id: str,
    instance_id: Optional[str] = None,
    replica_id: Optional[str] = None,
    include_timestamp: bool = False,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    """Download logs for a deployment.
    
    Args:
        deployment_id: The ID of the deployment
        instance_id: Optional instance ID
        replica_id: Optional ID of a specific replica
        include_timestamp: Whether to include timestamp in logs (default: False)
        start_time: Optional start time in ISO format (e.g. "2023-01-01T00:00:00Z")
        end_time: Optional end time in ISO format (e.g. "2023-01-01T01:00:00Z")
    """
    try:
        params = {
            "includeTimestamp": str(include_timestamp).lower()
        }
        
        if instance_id:
            params["instanceId"] = instance_id
            
        if replica_id:
            params["replicaId"] = replica_id
            
        if start_time:
            params["startTime"] = start_time
            
        if end_time:
            params["endTime"] = end_time
            
        logs = await make_quix_request(
            ctx,
            "GET",
            f"deployments/{deployment_id}/logs/history/download",
            params=params
        )
        
        if not logs:
            return f"No logs found for deployment with ID {deployment_id} in the specified time range."
            
        # Format the logs with line numbers
        numbered_logs = ""
        for i, line in enumerate(logs.splitlines()):
            numbered_logs += f"{i+1}: {line}\n"
            
        return numbered_logs
    except QuixApiError as e:
        return f"Error downloading logs: {str(e)}"

@mcp.tool()
async def get_deployment_runs(ctx: Context, deployment_id: str) -> str:
    """Get historical runs for a deployment.
    
    Args:
        deployment_id: The ID of the deployment
    """
    try:
        runs = await make_quix_request(
            ctx,
            "GET",
            f"deployments/{deployment_id}/runs"
        )
        
        if not runs or len(runs) == 0:
            return f"No historical runs found for deployment with ID {deployment_id}."
            
        result = f"Historical Runs for Deployment {deployment_id}:\n\n"
        
        for run in runs:
            run_id = run.get('id')
            replica_id = run.get('replicaId')
            pod_name = run.get('podName')
            instance_id = run.get('instanceId')
            start_time = run.get('startTime')
            end_time = run.get('endTime')
            exit_code = run.get('exitCode')
            reason = run.get('reason')
            message = run.get('message')
            current_run = run.get('currentRun')
            logs_stored = run.get('logsStored')
            logs_download_url = run.get('logsDownloadUrl')
            
            result += f"Run ID: {run_id}\n"
            
            if replica_id:
                result += f"Replica ID: {replica_id}\n"
                
            if pod_name:
                result += f"Pod Name: {pod_name}\n"
                
            if instance_id:
                result += f"Instance ID: {instance_id}\n"
                
            if start_time:
                result += f"Start Time: {start_time}\n"
                
            if end_time:
                result += f"End Time: {end_time}\n"
                
            if exit_code is not None:
                result += f"Exit Code: {exit_code}\n"
                
            if reason:
                result += f"Reason: {reason}\n"
                
            if message:
                result += f"Message: {message}\n"
                
            if current_run is not None:
                result += f"Current Run: {current_run}\n"
                
            if logs_stored is not None:
                result += f"Logs Stored: {logs_stored}\n"
                
            if logs_download_url:
                result += f"Logs Download URL: {logs_download_url}\n"
                
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error getting deployment runs: {str(e)}"

@mcp.tool()
async def get_deployment_run_logs(ctx: Context, deployment_id: str, run_id: str) -> str:
    """Get logs for a specific deployment run.
    
    Args:
        deployment_id: The ID of the deployment
        run_id: The ID of the run
    """
    try:
        logs = await make_quix_request(
            ctx,
            "GET",
            f"deployments/{deployment_id}/runs/{run_id}/logs"
        )
        
        if not logs:
            return f"No logs found for run {run_id} of deployment {deployment_id}."
            
        return logs
    except QuixApiError as e:
        return f"Error getting run logs: {str(e)}"


# =========================================
# Library Tools
# =========================================

@mcp.tool()
async def query_library(
    ctx: Context, 
    languages: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    page_index: Optional[int] = None,
    page_length: Optional[int] = None,
    connectors: Optional[bool] = None,
    auxiliary_services: Optional[bool] = None
) -> str:
    """Query the Quix library for items using filters.
    
    Args:
        languages: Optional list of programming languages to filter by (e.g. ["python", "csharp"])
        tags: Optional list of tags to filter by (e.g. ["source", "sink"])
        page_index: Optional page index for paginated results (starts at 0)
        page_length: Optional number of items per page
        connectors: Optional boolean to filter for connector items only (True) or exclude connectors (False)
        auxiliary_services: Optional boolean to filter for auxiliary service items only (True) or exclude them (False)
    """
    try:
        # Build the request payload according to the LibraryListViewRequest schema
        payload = {}
        
        if languages:
            payload["languages"] = languages
            
        if tags:
            payload["tags"] = tags
            
        if page_index is not None and page_length is not None:
            payload["pageIndex"] = page_index
            payload["pageLength"] = page_length
            
        if connectors is not None:
            payload["connectors"] = connectors
            
        if auxiliary_services is not None:
            payload["auxiliaryServices"] = auxiliary_services
        
        # Make the request to the library query endpoint
        items = await make_quix_request(
            ctx,
            "POST",
            "library/query",
            json=payload
        )
        
        if not items:
            return "No library items found matching the criteria."
        
        result = "Library Items:\n\n"
        for item in items:
            result += f"ID: {item.get('itemId')}\n"
            result += f"Name: {item.get('name')}\n"
            
            # Add language if present
            language = item.get('language')
            if language:
                result += f"Language: {language}\n"
                
            # Add tags if present
            tags = item.get('tags')
            if tags and len(tags) > 0:
                result += f"Tags: {', '.join(tags)}\n"
                
            # Add description if present
            description = item.get('shortDescription')
            if description:
                # Truncate long descriptions
                if len(description) > 100:
                    description = description[:97] + "..."
                result += f"Description: {description}\n"
                
            # Add highlighted status if true
            is_highlighted = item.get('isHighlighted')
            if is_highlighted:
                result += f"Highlighted: {is_highlighted}\n"
                
            # Add connector/service status if present
            is_connector = item.get('isConnector')
            if is_connector:
                result += f"Connector: Yes\n"
                
            is_auxiliary_service = item.get('isAuxiliaryService')
            if is_auxiliary_service:
                result += f"Auxiliary Service: Yes\n"
                
            # Add deploy readiness if present
            deployable = item.get('deployable')
            if deployable:
                result += f"Deployable: Yes\n"
                
            deploy_ready = item.get('deployReady')
            if deploy_ready:
                result += f"Deploy Ready: Yes\n"
                
            result += "-" * 40 + "\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_library_item_details(ctx: Context, item_id: str) -> str:
    """Get detailed information about a specific library item.
    
    Args:
        item_id: The ID of the library item to retrieve details for
    """
    try:
        details = await make_quix_request(
            ctx,
            "GET",
            f"library/{item_id}/details"
        )
        
        if not details:
            return f"No library item found with ID {item_id}."
        
        result = "Library Item Details:\n\n"
        result += f"ID: {details.get('itemId')}\n"
        result += f"Name: {details.get('name')}\n"
        
        # Add language if present
        language = details.get('language')
        if language:
            result += f"Language: {language}\n"
            
        # Add tags if present
        tags = details.get('tags')
        if tags and len(tags) > 0:
            result += f"Tags: {', '.join(tags)}\n"
            
        # Add highlighted status if true
        is_highlighted = details.get('isHighlighted')
        if is_highlighted:
            result += f"Highlighted: {is_highlighted}\n"
            
        # Add display order if present
        display_order = details.get('displayOrder')
        if display_order is not None:
            result += f"Display Order: {display_order}\n"
            
        # Add descriptions if present
        short_description = details.get('shortDescription')
        if short_description:
            result += f"Short Description: {short_description}\n"
            
        long_description = details.get('longDescription')
        if long_description:
            result += f"Long Description: {long_description}\n"
            
        # Add URL if present
        url = details.get('url')
        if url:
            result += f"URL: {url}\n"
            
        # Add connector/service status if present
        is_connector = details.get('isConnector')
        if is_connector:
            result += f"Connector: Yes\n"
            
        is_auxiliary_service = details.get('isAuxiliaryService')
        if is_auxiliary_service:
            result += f"Auxiliary Service: Yes\n"
            
        # Add deploy info if present
        deployable = details.get('deployable')
        if deployable:
            result += f"Deployable: Yes\n"
            
        deploy_ready = details.get('deployReady')
        if deploy_ready:
            result += f"Deploy Ready: Yes\n"
            
        # Add entry points if present
        entry_point = details.get('entryPoint')
        if entry_point:
            result += f"Entry Point: {entry_point}\n"
            
        run_entry_point = details.get('runEntryPoint')
        if run_entry_point:
            result += f"Run Entry Point: {run_entry_point}\n"
            
        default_file = details.get('defaultFile')
        if default_file:
            result += f"Default File: {default_file}\n"
            
        # Add timestamps
        created_at = details.get('createdAt')
        if created_at:
            result += f"Created At: {created_at}\n"
            
        updated_at = details.get('updatedAt')
        if updated_at:
            result += f"Updated At: {updated_at}\n"
            
        # Add files if present
        files = details.get('files')
        if files and len(files) > 0:
            result += "\nFiles:\n"
            for file in files:
                result += f"- {file}\n"
                
        # Add variables if present
        variables = details.get('variables')
        if variables and len(variables) > 0:
            result += "\nVariables:\n"
            for var in variables:
                result += f"• {var.get('name')} ({var.get('inputType')})\n"
                
                description = var.get('description')
                if description:
                    result += f"  Description: {description}\n"
                    
                default_value = var.get('defaultValue')
                if default_value:
                    result += f"  Default Value: {default_value}\n"
                    
                required = var.get('required')
                result += f"  Required: {required}\n"
                
                multiline = var.get('multiline')
                if multiline:
                    result += f"  Multiline: {multiline}\n"
                    
                result += "\n"
                
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_library_file_content(ctx: Context, item_id: str, file_path: str, placeholder_replacements: Optional[Dict[str, str]] = None) -> str:
    """Get the content of a specific file within a library item.
    
    Args:
        item_id: The ID of the library item
        file_path: The path of the file within the library item
        placeholder_replacements: Optional dictionary of placeholder replacements (e.g. {"PLACEHOLDER": "value"})
    """
    try:
        # Build the request payload according to the LibraryFileContentRequest schema
        payload = {
            "filePath": file_path
        }
        
        if os.environ.get("QUIX_WORKSPACE"):
            payload["workspaceId"] = os.environ.get("QUIX_WORKSPACE")
            
        if placeholder_replacements:
            payload["placeholderReplacements"] = placeholder_replacements
        
        content = await make_quix_request(
            ctx,
            "POST",
            f"library/{item_id}/files/content",
            json=payload
        )
        
        if not content:
            return f"No content found for file {file_path} in library item {item_id}."
        
        return f"File: {file_path}\n\n{content}"
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_library_icon(ctx: Context, item_id: str) -> str:
    """Get the icon for a library item.
    
    Args:
        item_id: The ID of the library item
    """
    try:
        icon = await make_quix_request(
            ctx,
            "GET",
            f"library/{item_id}/icon"
        )
        
        if not icon:
            return f"No icon found for library item {item_id}."
        
        return f"Icon retrieved for library item {item_id}."
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_library_configuration(ctx: Context, source: Optional[str] = None) -> str:
    """Get library configuration.
    
    Args:
        source: Optional source parameter
    """
    try:
        params = {}
        if source:
            params["source"] = source
            
        config = await make_quix_request(
            ctx,
            "GET",
            "library/configuration",
            params=params
        )
        
        if not config:
            return "No library configuration found."
        
        result = "Library Configuration:\n\n"
        
        git_url = config.get('gitUrl')
        if git_url:
            result += f"Git URL: {git_url}\n"
            
        branch = config.get('branch')
        if branch:
            result += f"Branch: {branch}\n"
            
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_library_languages(ctx: Context, connectors: Optional[bool] = None, auxiliary_services: Optional[bool] = None) -> str:
    """Get a list of available programming languages in the Quix library.
    
    Args:
        connectors: Optional boolean to filter for connector items only (True) or exclude connectors (False)
        auxiliary_services: Optional boolean to filter for auxiliary service items only (True) or exclude them (False)
    """
    try:
        params = {}
        if connectors is not None:
            params["connectors"] = str(connectors).lower()
            
        if auxiliary_services is not None:
            params["auxiliaryServices"] = str(auxiliary_services).lower()
            
        languages = await make_quix_request(
            ctx,
            "GET",
            "library/languages",
            params=params
        )
        
        if not languages or len(languages) == 0:
            return "No programming languages found in the library."
        
        result = "Available languages in the Quix library:\n\n"
        for lang in languages:
            result += f"- {lang}\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_library_tags(ctx: Context, connectors: Optional[bool] = None, auxiliary_services: Optional[bool] = None) -> str:
    """Get information about available tags in the Quix library.
    
    Args:
        connectors: Optional boolean to filter for connector items only (True) or exclude connectors (False)
        auxiliary_services: Optional boolean to filter for auxiliary service items only (True) or exclude them (False)
    """
    try:
        params = {}
        if connectors is not None:
            params["connectors"] = str(connectors).lower()
            
        if auxiliary_services is not None:
            params["auxiliaryServices"] = str(auxiliary_services).lower()
            
        tag_groups = await make_quix_request(
            ctx,
            "GET",
            "library/tags",
            params=params
        )
        
        if not tag_groups or len(tag_groups) == 0:
            return "No tags found in the library."
        
        result = "Available tags in the Quix library:\n\n"
        for group in tag_groups:
            group_name = group.get('tagGroup')
            tags = group.get('tags', [])
            
            if group_name:
                result += f"Group: {group_name}\n"
                
            if tags and len(tags) > 0:
                for tag in tags:
                    result += f"- {tag}\n"
                
            result += "\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def create_application_from_library(
    ctx: Context,
    library_item_id: str,
    application_name: str,
    path: Optional[str] = None,
    placeholders: Optional[Dict[str, str]] = None,
    environment_variables: Optional[Dict[str, str]] = None
) -> str:
    """Create a new application from a library item.
    
    Args:
        library_item_id: The ID of the library item to create an application from
        application_name: The name for the new application
        path: Optional path for the new application
        placeholders: Optional dictionary of placeholder values (e.g. {"PLACEHOLDER": "value"})
        environment_variables: Optional dictionary of environment variables (e.g. {"ENV_VAR": "value"})
    """
    try:
        # Ensure workspace ID is available
        workspace_id = os.environ.get("QUIX_WORKSPACE")
        if not workspace_id:
            return "Missing QUIX_WORKSPACE environment variable. Please set your Quix Workspace ID."
            
        # Build the request payload according to the CreateApplicationFromLibraryRequest schema
        payload = {
            "workspaceId": workspace_id,
            "applicationName": application_name,
            "libraryItemId": library_item_id
        }
        
        if path:
            payload["path"] = path
            
        if placeholders:
            payload["placeholders"] = placeholders
            
        if environment_variables:
            payload["environmentVariables"] = environment_variables
        
        application = await make_quix_request(
            ctx,
            "POST",
            "library/application",
            json=payload
        )
        
        if not application:
            return "Failed to create application from library item."
        
        application_id = application.get('applicationId')
        name = application.get('name')
        return f"Successfully created application '{name}' with ID: {application_id} from library item {library_item_id}."
    except QuixApiError as e:
        return f"Error creating application: {str(e)}"

@mcp.tool()
async def create_deployment_from_library(
    ctx: Context,
    library_item_id: str,
    deployment_name: str,
    create_application: bool = False,
    environment_variables: Optional[Dict[str, str]] = None
) -> str:
    """Create a new deployment from a library item.
    
    Args:
        library_item_id: The ID of the library item to create a deployment from
        deployment_name: The name for the new deployment
        create_application: Whether to also create an application from the deployment (default: False)
        environment_variables: Optional dictionary of environment variables (e.g. {"ENV_VAR": "value"})
    """
    try:
        # Ensure workspace ID is available
        workspace_id = os.environ.get("QUIX_WORKSPACE")
        if not workspace_id:
            return "Missing QUIX_WORKSPACE environment variable. Please set your Quix Workspace ID."
            
        # Build the request payload according to the CreateDeploymentFromLibraryRequest schema
        payload = {
            "workspaceId": workspace_id,
            "deploymentName": deployment_name,
            "libraryItemId": library_item_id,
            "createApplication": create_application
        }
        
        if environment_variables:
            payload["environmentVariables"] = environment_variables
        
        deployment = await make_quix_request(
            ctx,
            "POST",
            "library/deployment",
            json=payload
        )
        
        if not deployment:
            return "Failed to create deployment from library item."
        
        deployment_id = deployment.get('deploymentId')
        return f"Successfully created deployment '{deployment_name}' with ID: {deployment_id} from library item {library_item_id}."
    except QuixApiError as e:
        return f"Error creating deployment: {str(e)}"

@mcp.tool()
async def get_library_zip(
    ctx: Context,
    item_id: str,
    placeholder_replacements: Optional[Dict[str, str]] = None
) -> str:
    """Download a library item as a ZIP file.
    
    Args:
        item_id: The ID of the library item to download
        placeholder_replacements: Optional dictionary of placeholder replacements (e.g. {"PLACEHOLDER": "value"})
    """
    try:
        # Build the request payload according to the LibraryZipContentRequest schema
        payload = {}
        
        if os.environ.get("QUIX_WORKSPACE"):
            payload["workspaceId"] = os.environ.get("QUIX_WORKSPACE")
            
        if placeholder_replacements:
            payload["placeholderReplacements"] = placeholder_replacements
        
        zip_content = await make_quix_request(
            ctx,
            "POST",
            f"library/{item_id}/zip",
            json=payload
        )
        
        if not zip_content:
            return f"Failed to download ZIP for library item {item_id}."
        
        return f"Successfully downloaded ZIP for library item {item_id}."
    except QuixApiError as e:
        return f"Error downloading ZIP: {str(e)}"


# =========================================
# Topic Tools
# =========================================

@mcp.tool()
async def get_topics(ctx: Context) -> str:
    """List all topics in your workspace.
    """
    try:
        topics = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/topics"
        )
        
        if not topics:
            return "No topics found in this workspace."
        
        result = "Topics:\n\n"
        for topic in topics:
            result += f"Name: {topic.get('name')}\n"
            result += f"ID: {topic.get('id')}\n"
            
            # Add status information
            status = topic.get('status')
            if status:
                result += f"Status: {status}\n"
                
            # Include error information if present
            error_status = topic.get('errorStatus')
            if error_status:
                result += f"Error Status: {error_status}\n"
                last_error = topic.get('lastError')
                if last_error:
                    result += f"Last Error: {last_error}\n"
                    
            # Add timestamps
            created_at = topic.get('createdAt')
            if created_at:
                result += f"Created At: {created_at}\n"
                
            updated_at = topic.get('updatedAt')
            if updated_at:
                result += f"Updated At: {updated_at}\n"
                
            # Add persistence info if present
            persisted = topic.get('persisted')
            if persisted is not None:
                result += f"Persisted: {persisted}\n"
                
            persisted_status = topic.get('persistedStatus')
            if persisted_status:
                result += f"Persisted Status: {persisted_status}\n"
                
            # Add other flags
            external = topic.get('external')
            if external:
                result += f"External: {external}\n"
                
            unmanaged = topic.get('unmanaged')
            if unmanaged:
                result += f"Unmanaged: {unmanaged}\n"
                
            sdk_topic = topic.get('sdkTopic')
            if sdk_topic:
                result += f"SDK Topic: {sdk_topic}\n"
                
            # Add external sources/destinations if present
            external_source = topic.get('externalSourceName')
            if external_source:
                result += f"External Source: {external_source}\n"
                
            external_destination = topic.get('externalDestinationName')
            if external_destination:
                result += f"External Destination: {external_destination}\n"
                
            # Add configuration if present
            config = topic.get('configuration')
            if config:
                result += "\nConfiguration:\n"
                
                partitions = config.get('partitions')
                if partitions is not None:
                    result += f"  Partitions: {partitions}\n"
                    
                replication = config.get('replicationFactor')
                if replication is not None:
                    result += f"  Replication Factor: {replication}\n"
                    
                retention_mins = config.get('retentionInMinutes')
                if retention_mins is not None:
                    result += f"  Retention (minutes): {retention_mins}\n"
                    
                retention_bytes = config.get('retentionInBytes')
                if retention_bytes is not None:
                    result += f"  Retention (bytes): {retention_bytes}\n"
                    
                cleanup_policy = config.get('cleanupPolicy')
                if cleanup_policy:
                    result += f"  Cleanup Policy: {cleanup_policy}\n"
            
            # Add linked topic info if present
            linked_info = topic.get('linkedTopicInfo')
            if linked_info:
                result += "\nLinked Topic Info:\n"
                
                is_linked = linked_info.get('isLinked')
                if is_linked:
                    result += f"  Is Linked: {is_linked}\n"
                    
                is_locked = linked_info.get('isLocked')
                if is_locked:
                    result += f"  Is Locked: {is_locked}\n"
                    
                is_scratchpad = linked_info.get('isScratchpad')
                if is_scratchpad:
                    result += f"  Is Scratchpad: {is_scratchpad}\n"
                    
                repository_name = linked_info.get('repositoryName')
                if repository_name:
                    result += f"  Repository: {repository_name}\n"
                    
                environment_name = linked_info.get('environmentName')
                if environment_name:
                    result += f"  Environment: {environment_name}\n"
                
            # Add linked topic destination info if present
            linked_destinations = topic.get('linkedTopicDestinationInfo')
            if linked_destinations and len(linked_destinations) > 0:
                result += "\nLinked Topic Destinations:\n"
                
                for dest in linked_destinations:
                    dest_workspace = dest.get('workspaceId')
                    if dest_workspace:
                        result += f"  Workspace ID: {dest_workspace}\n"
                        
                    dest_topic = dest.get('topicName')
                    if dest_topic:
                        result += f"  Topic Name: {dest_topic}\n"
                        
                    dest_repo = dest.get('repositoryName')
                    if dest_repo:
                        result += f"  Repository: {dest_repo}\n"
                        
                    dest_env = dest.get('environmentName')
                    if dest_env:
                        result += f"  Environment: {dest_env}\n"
                        
                    result += "  ---\n"
            
            result += "-" * 40 + "\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_topic(ctx: Context, topic_name: str) -> str:
    """Get details of a specific topic.
    
    Args:
        topic_name: The name of the topic to retrieve
    """
    try:
        topic = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/topics/{topicName}".replace("{topicName}", topic_name)
        )
        
        if not topic:
            return f"No topic found with name {topic_name}."
        
        # Format the topic details
        result = "Topic Details:\n\n"
        result += f"Name: {topic.get('name')}\n"
        result += f"ID: {topic.get('id')}\n"
        result += f"Workspace ID: {topic.get('workspaceId')}\n"
        
        # Add status information
        status = topic.get('status')
        if status:
            result += f"Status: {status}\n"
            
        # Include error information if present
        error_status = topic.get('errorStatus')
        if error_status:
            result += f"Error Status: {error_status}\n"
            last_error = topic.get('lastError')
            if last_error:
                result += f"Last Error: {last_error}\n"
                
        # Add timestamps
        created_at = topic.get('createdAt')
        if created_at:
            result += f"Created At: {created_at}\n"
            
        updated_at = topic.get('updatedAt')
        if updated_at:
            result += f"Updated At: {updated_at}\n"
            
        # Add persistence info if present
        persisted = topic.get('persisted')
        if persisted is not None:
            result += f"Persisted: {persisted}\n"
            
        persisted_status = topic.get('persistedStatus')
        if persisted_status:
            result += f"Persisted Status: {persisted_status}\n"
            
        # Add other flags
        external = topic.get('external')
        if external:
            result += f"External: {external}\n"
            
        unmanaged = topic.get('unmanaged')
        if unmanaged:
            result += f"Unmanaged: {unmanaged}\n"
            
        sdk_topic = topic.get('sdkTopic')
        if sdk_topic:
            result += f"SDK Topic: {sdk_topic}\n"
            
        # Add data tier info if present
        data_tier = topic.get('dataTier')
        if data_tier:
            result += f"Data Tier: {data_tier}\n"
            
        # Add external sources/destinations if present
        external_source = topic.get('externalSourceName')
        if external_source:
            result += f"External Source: {external_source}\n"
            
        external_destination = topic.get('externalDestinationName')
        if external_destination:
            result += f"External Destination: {external_destination}\n"
            
        # Add configuration if present
        config = topic.get('configuration')
        if config:
            result += "\nConfiguration:\n"
            
            partitions = config.get('partitions')
            if partitions is not None:
                result += f"  Partitions: {partitions}\n"
                
            replication = config.get('replicationFactor')
            if replication is not None:
                result += f"  Replication Factor: {replication}\n"
                
            retention_mins = config.get('retentionInMinutes')
            if retention_mins is not None:
                result += f"  Retention (minutes): {retention_mins}\n"
                
            retention_bytes = config.get('retentionInBytes')
            if retention_bytes is not None:
                result += f"  Retention (bytes): {retention_bytes}\n"
                
            cleanup_policy = config.get('cleanupPolicy')
            if cleanup_policy:
                result += f"  Cleanup Policy: {cleanup_policy}\n"
        
        # Add linked topic info if present
        linked_info = topic.get('linkedTopicInfo')
        if linked_info:
            result += "\nLinked Topic Info:\n"
            
            is_linked = linked_info.get('isLinked')
            if is_linked:
                result += f"  Is Linked: {is_linked}\n"
                
            is_locked = linked_info.get('isLocked')
            if is_locked:
                result += f"  Is Locked: {is_locked}\n"
                
            is_scratchpad = linked_info.get('isScratchpad')
            if is_scratchpad:
                result += f"  Is Scratchpad: {is_scratchpad}\n"
                
            has_repo_access = linked_info.get('hasRepositoryAccess')
            if has_repo_access is not None:
                result += f"  Has Repository Access: {has_repo_access}\n"
                
            has_workspace_access = linked_info.get('hasWorkspaceAccess')
            if has_workspace_access is not None:
                result += f"  Has Workspace Access: {has_workspace_access}\n"
                
            repository_name = linked_info.get('repositoryName')
            if repository_name:
                result += f"  Repository: {repository_name}\n"
                
            environment_name = linked_info.get('environmentName')
            if environment_name:
                result += f"  Environment: {environment_name}\n"
            
        # Add linked topic destination info if present
        linked_destinations = topic.get('linkedTopicDestinationInfo')
        if linked_destinations and len(linked_destinations) > 0:
            result += "\nLinked Topic Destinations:\n"
            
            for dest in linked_destinations:
                dest_workspace = dest.get('workspaceId')
                if dest_workspace:
                    result += f"  Workspace ID: {dest_workspace}\n"
                    
                dest_topic = dest.get('topicName')
                if dest_topic:
                    result += f"  Topic Name: {dest_topic}\n"
                    
                dest_repo = dest.get('repositoryName')
                if dest_repo:
                    result += f"  Repository: {dest_repo}\n"
                    
                dest_env = dest.get('environmentName')
                if dest_env:
                    result += f"  Environment: {dest_env}\n"
                    
                result += "  ---\n"
                
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def create_topic(
    ctx: Context,
    name: str,
    partitions: Optional[int] = None,
    replication_factor: Optional[int] = None,
    retention_in_minutes: Optional[int] = None,
    retention_in_bytes: Optional[int] = None,
    cleanup_policy: Optional[str] = None,
    data_tier_name: Optional[str] = None,
    external_source_name: Optional[str] = None,
    external_destination_name: Optional[str] = None,
    unmanaged: bool = False,
    linked_topic_workspace_id: Optional[str] = None,
    linked_topic_name: Optional[str] = None
) -> str:
    """Create a new Kafka topic in your workspace.
    
    Args:
        name: The name of the topic to create
        partitions: Optional number of partitions (default depends on Quix configuration)
        replication_factor: Optional replication factor (default depends on Quix configuration)
        retention_in_minutes: Optional retention time in minutes
        retention_in_bytes: Optional retention size in bytes
        cleanup_policy: Optional cleanup policy (one of: Delete, Compact, DeleteAndCompact)
        data_tier_name: Optional data tier name
        external_source_name: Optional external source name
        external_destination_name: Optional external destination name
        unmanaged: Whether the topic is managed by Quix (default: False)
        linked_topic_workspace_id: Optional workspace ID for a linked topic
        linked_topic_name: Optional topic name for a linked topic
    """
    try:
        # Build the topic create request according to the TopicCreateRequest schema
        payload = {
            "name": name,
            "unmanaged": unmanaged
        }
        
        # Add configuration if any related parameters are provided
        if any([partitions, replication_factor, retention_in_minutes, retention_in_bytes, cleanup_policy]):
            config = {}
            
            if partitions is not None:
                config["partitions"] = partitions
                
            if replication_factor is not None:
                config["replicationFactor"] = replication_factor
                
            if retention_in_minutes is not None:
                config["retentionInMinutes"] = retention_in_minutes
                
            if retention_in_bytes is not None:
                config["retentionInBytes"] = retention_in_bytes
                
            if cleanup_policy:
                # Validate cleanup policy
                valid_policies = [p.value for p in TopicCleanupPolicy]
                if cleanup_policy not in valid_policies:
                    return f"Error: Invalid cleanup policy. Must be one of: {', '.join(valid_policies)}"
                config["cleanupPolicy"] = cleanup_policy
                
            payload["configuration"] = config
        
        # Add optional parameters if provided
        if data_tier_name:
            payload["dataTierName"] = data_tier_name
            
        if external_source_name:
            payload["externalSourceName"] = external_source_name
            
        if external_destination_name:
            payload["externalDestinationName"] = external_destination_name
            
        # Add linked topic info if both required parameters are provided
        if linked_topic_workspace_id and linked_topic_name:
            payload["linkedTopic"] = {
                "workspaceId": linked_topic_workspace_id,
                "topicName": linked_topic_name
            }
        elif linked_topic_workspace_id or linked_topic_name:
            # Both parameters are required for linking
            return "Error: Both linked_topic_workspace_id and linked_topic_name must be provided together to link a topic."
            
        topic = await make_quix_request(
            ctx,
            "POST",
            "{workspaceId}/topics",
            json=payload
        )
        
        if not topic:
            return f"Failed to create topic '{name}'."
            
        result = f"Successfully created topic '{name}'.\n\n"
        result += f"Topic ID: {topic.get('id')}\n"
        result += f"Status: {topic.get('status')}\n"
        
        # Show configuration if present
        config = topic.get('configuration')
        if config:
            result += "\nConfiguration:\n"
            
            partitions = config.get('partitions')
            if partitions is not None:
                result += f"  Partitions: {partitions}\n"
                
            replication = config.get('replicationFactor')
            if replication is not None:
                result += f"  Replication Factor: {replication}\n"
                
            retention_mins = config.get('retentionInMinutes')
            if retention_mins is not None:
                result += f"  Retention (minutes): {retention_mins}\n"
                
            retention_bytes = config.get('retentionInBytes')
            if retention_bytes is not None:
                result += f"  Retention (bytes): {retention_bytes}\n"
                
            cleanup_policy = config.get('cleanupPolicy')
            if cleanup_policy:
                result += f"  Cleanup Policy: {cleanup_policy}\n"
                
        # Show linking info if present
        linked_info = topic.get('linkedTopicInfo')
        if linked_info and linked_info.get('isLinked'):
            result += "\nLinked Topic Info:\n"
            result += f"  Is Linked: {linked_info.get('isLinked')}\n"
            
            repository_name = linked_info.get('repositoryName')
            if repository_name:
                result += f"  Repository: {repository_name}\n"
                
            environment_name = linked_info.get('environmentName')
            if environment_name:
                result += f"  Environment: {environment_name}\n"
                
        return result
    except QuixApiError as e:
        return f"Error creating topic: {str(e)}"

@mcp.tool()
async def update_topic(
    ctx: Context,
    topic_name: str,
    partitions: Optional[int] = None,
    retention_in_minutes: Optional[int] = None,
    retention_in_bytes: Optional[int] = None,
    cleanup_policy: Optional[str] = None,
    data_tier_name: Optional[str] = None,
    unset_data_tier: bool = False,
    external_source_name: Optional[str] = None,
    external_destination_name: Optional[str] = None,
    unlink_topic: bool = False,
    linked_topic_workspace_id: Optional[str] = None,
    linked_topic_name: Optional[str] = None
) -> str:
    """Update a topic's configuration.
    
    Args:
        topic_name: The name of the topic to update
        partitions: Optional number of partitions (must be greater than current value)
        retention_in_minutes: Optional retention time in minutes
        retention_in_bytes: Optional retention size in bytes
        cleanup_policy: Optional cleanup policy (one of: Delete, Compact, DeleteAndCompact)
        data_tier_name: Optional data tier name
        unset_data_tier: Whether to unset the data tier (default: False)
        external_source_name: Optional external source name
        external_destination_name: Optional external destination name
        unlink_topic: Whether to unlink the topic (default: False)
        linked_topic_workspace_id: Optional workspace ID for a linked topic
        linked_topic_name: Optional topic name for a linked topic
    """
    try:
        # Build the topic patch request according to the TopicPatchRequest schema
        payload = {}
        
        # Add partitions if provided
        if partitions is not None:
            payload["partitions"] = partitions
            
        # Add retention values if provided
        if retention_in_minutes is not None:
            payload["retentionInMinutes"] = retention_in_minutes
            
        if retention_in_bytes is not None:
            payload["retentionInBytes"] = retention_in_bytes
            
        # Add cleanup policy if provided
        if cleanup_policy:
            # Validate cleanup policy
            valid_policies = [p.value for p in TopicCleanupPolicy]
            if cleanup_policy not in valid_policies:
                return f"Error: Invalid cleanup policy. Must be one of: {', '.join(valid_policies)}"
            payload["cleanupPolicy"] = cleanup_policy
            
        # Add data tier info if provided
        if data_tier_name:
            payload["dataTierName"] = data_tier_name
            
        if unset_data_tier:
            payload["unsetDataTier"] = True
            
        # Add external source/destination if provided
        if external_source_name:
            payload["externalSourceName"] = external_source_name
            
        if external_destination_name:
            payload["externalDestinationName"] = external_destination_name
            
        # Add unlinking if requested
        if unlink_topic:
            payload["unlinkTopic"] = True
            
        # Add linked topic info if both required parameters are provided
        if linked_topic_workspace_id and linked_topic_name:
            payload["linkedTopic"] = {
                "workspaceId": linked_topic_workspace_id,
                "topicName": linked_topic_name
            }
        elif linked_topic_workspace_id or linked_topic_name:
            # Both parameters are required for linking
            return "Error: Both linked_topic_workspace_id and linked_topic_name must be provided together to link a topic."
            
        topic = await make_quix_request(
            ctx,
            "PATCH",
            "{workspaceId}/topics/{topicName}".replace("{topicName}", topic_name),
            json=payload
        )
        
        if not topic:
            return f"Failed to update topic '{topic_name}'."
            
        result = f"Successfully updated topic '{topic_name}'.\n\n"
        result += f"Topic ID: {topic.get('id')}\n"
        result += f"Status: {topic.get('status')}\n"
        
        # Show updated configuration
        config = topic.get('configuration')
        if config:
            result += "\nUpdated Configuration:\n"
            
            config_partitions = config.get('partitions')
            if config_partitions is not None:
                result += f"  Partitions: {config_partitions}\n"
                
            replication = config.get('replicationFactor')
            if replication is not None:
                result += f"  Replication Factor: {replication}\n"
                
            retention_mins = config.get('retentionInMinutes')
            if retention_mins is not None:
                result += f"  Retention (minutes): {retention_mins}\n"
                
            retention_bytes = config.get('retentionInBytes')
            if retention_bytes is not None:
                result += f"  Retention (bytes): {retention_bytes}\n"
                
            config_cleanup_policy = config.get('cleanupPolicy')
            if config_cleanup_policy:
                result += f"  Cleanup Policy: {config_cleanup_policy}\n"
                
        # Show data tier if present
        data_tier = topic.get('dataTier')
        if data_tier:
            result += f"\nData Tier: {data_tier}\n"
            
        # Show external info if present
        external_source = topic.get('externalSourceName')
        if external_source:
            result += f"External Source: {external_source}\n"
            
        external_destination = topic.get('externalDestinationName')
        if external_destination:
            result += f"External Destination: {external_destination}\n"
            
        # Show linking info if present
        linked_info = topic.get('linkedTopicInfo')
        if linked_info:
            is_linked = linked_info.get('isLinked')
            result += f"\nIs Linked: {is_linked}\n"
            
            if is_linked:
                repository_name = linked_info.get('repositoryName')
                if repository_name:
                    result += f"Repository: {repository_name}\n"
                    
                environment_name = linked_info.get('environmentName')
                if environment_name:
                    result += f"Environment: {environment_name}\n"
                
        return result
    except QuixApiError as e:
        return f"Error updating topic: {str(e)}"

@mcp.tool()
async def delete_topic(ctx: Context, topic_name: str) -> str:
    """Delete a topic from your workspace.
    
    Args:
        topic_name: The name of the topic to delete
    """
    try:
        result = await make_quix_request(
            ctx,
            "DELETE",
            "{workspaceId}/topics/{topicName}".replace("{topicName}", topic_name)
        )
        
        return f"Successfully deleted topic '{topic_name}'."
    except QuixApiError as e:
        return f"Error deleting topic: {str(e)}"

@mcp.tool()
async def clean_topic(ctx: Context, topic_name: str) -> str:
    """Clean the contents of a topic (removes all messages).
    
    Args:
        topic_name: The name of the topic to clean
    """
    try:
        result = await make_quix_request(
            ctx,
            "POST",
            "{workspaceId}/topics/{topicName}/clean".replace("{topicName}", topic_name)
        )
        
        return f"Successfully cleaned topic '{topic_name}'."
    except QuixApiError as e:
        return f"Error cleaning topic: {str(e)}"

@mcp.tool()
async def clear_topic_error(ctx: Context, topic_name: str) -> str:
    """Clear the error state of a topic.
    
    Args:
        topic_name: The name of the topic to clear error state for
    """
    try:
        result = await make_quix_request(
            ctx,
            "POST",
            "{workspaceId}/topics/{topicName}/clear-error".replace("{topicName}", topic_name)
        )
        
        return f"Successfully cleared error state for topic '{topic_name}'."
    except QuixApiError as e:
        return f"Error clearing topic error: {str(e)}"

@mcp.tool()
async def get_default_topic_config(ctx: Context) -> str:
    """Get the default topic configuration for your workspace.
    """
    try:
        config = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/config/default"
        )
        
        if not config:
            return "No default topic configuration found."
            
        result = "Default Topic Configuration:\n\n"
        
        partitions = config.get('partitions')
        if partitions is not None:
            result += f"Partitions: {partitions}\n"
            
        replication = config.get('replicationFactor')
        if replication is not None:
            result += f"Replication Factor: {replication}\n"
            
        retention_mins = config.get('retentionInMinutes')
        if retention_mins is not None:
            result += f"Retention (minutes): {retention_mins}\n"
            
        retention_bytes = config.get('retentionInBytes')
        if retention_bytes is not None:
            result += f"Retention (bytes): {retention_bytes}\n"
            
        cleanup_policy = config.get('cleanupPolicy')
        if cleanup_policy:
            result += f"Cleanup Policy: {cleanup_policy}\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving default topic configuration: {str(e)}"

@mcp.tool()
async def search_topics(
    ctx: Context,
    data_tier: Optional[str] = None,
    workspace_id: Optional[str] = None,
    repository_id: Optional[str] = None,
    linkable: Optional[bool] = None,
    linked: Optional[bool] = None,
    locked: Optional[bool] = None,
    is_sdk: Optional[bool] = None,
    page_number: Optional[int] = None,
    page_size: Optional[int] = None
) -> str:
    """Search for topics across workspaces with various filters.
    
    Args:
        data_tier: Optional data tier filter
        workspace_id: Optional workspace ID filter (if not provided, uses the current workspace)
        repository_id: Optional repository ID filter
        linkable: Optional filter for linkable topics (True/False)
        linked: Optional filter for linked topics (True/False)
        locked: Optional filter for locked topics (True/False)
        is_sdk: Optional filter for SDK topics (True/False)
        page_number: Optional page number for pagination
        page_size: Optional page size for pagination
    """
    try:
        params = {}
        
        # Add filters if provided
        if data_tier:
            params["DataTier"] = data_tier
            
        if workspace_id:
            params["WorkspaceId"] = workspace_id
            
        if repository_id:
            params["RepositoryId"] = repository_id
            
        if linkable is not None:
            params["Linkable"] = str(linkable).lower()
            
        if linked is not None:
            params["Linked"] = str(linked).lower()
            
        if locked is not None:
            params["Locked"] = str(locked).lower()
            
        if is_sdk is not None:
            params["IsSdk"] = str(is_sdk).lower()
            
        # Add pagination if provided
        if page_number is not None:
            params["PageNumber"] = page_number
            
        if page_size is not None:
            params["PageSize"] = page_size
            
        topics = await make_quix_request(
            ctx,
            "GET",
            "topics",
            params=params
        )
        
        if not topics:
            return "No topics found matching the search criteria."
            
        result = "Topics found:\n\n"
        for topic in topics:
            result += f"Name: {topic.get('name')}\n"
            result += f"ID: {topic.get('id')}\n"
            result += f"Workspace ID: {topic.get('workspaceId')}\n"
            
            # Add status information
            status = topic.get('status')
            if status:
                result += f"Status: {status}\n"
                
            # Add data tier if present
            data_tier = topic.get('dataTier')
            if data_tier:
                result += f"Data Tier: {data_tier}\n"
                
            # Add linked topic info if present
            linked_info = topic.get('linkedTopicInfo')
            if linked_info:
                is_linked = linked_info.get('isLinked')
                if is_linked:
                    result += f"Is Linked: {is_linked}\n"
                    
                is_locked = linked_info.get('isLocked')
                if is_locked:
                    result += f"Is Locked: {is_locked}\n"
                    
                is_scratchpad = linked_info.get('isScratchpad')
                if is_scratchpad:
                    result += f"Is Scratchpad: {is_scratchpad}\n"
                    
                repository_name = linked_info.get('repositoryName')
                if repository_name:
                    result += f"Repository: {repository_name}\n"
                    
                environment_name = linked_info.get('environmentName')
                if environment_name:
                    result += f"Environment: {environment_name}\n"
                    
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error searching topics: {str(e)}"

@mcp.tool()
async def get_linkable_topics(ctx: Context) -> str:
    """Get all linkable topics from your workspace.
    """
    try:
        topics = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/all-linkable"
        )
        
        if not topics:
            return "No linkable topics found in this workspace."
            
        result = "Linkable Topics:\n\n"
        for topic in topics:
            result += f"Name: {topic.get('name')}\n"
            result += f"ID: {topic.get('id')}\n"
            
            # Add status information
            status = topic.get('status')
            if status:
                result += f"Status: {status}\n"
                
            # Add linked topic info if present
            linked_info = topic.get('linkedTopicInfo')
            if linked_info:
                is_linked = linked_info.get('isLinked')
                if is_linked:
                    result += f"Is Linked: {is_linked}\n"
                    
                is_locked = linked_info.get('isLocked')
                if is_locked:
                    result += f"Is Locked: {is_locked}\n"
                    
                repository_name = linked_info.get('repositoryName')
                if repository_name:
                    result += f"Repository: {repository_name}\n"
                    
                environment_name = linked_info.get('environmentName')
                if environment_name:
                    result += f"Environment: {environment_name}\n"
                    
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving linkable topics: {str(e)}"

@mcp.tool()
async def get_external_topics(ctx: Context) -> str:
    """Get all available external topics that can be imported.
    """
    try:
        result = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/external/import"
        )
        
        if not result:
            return "No external topics available for import."
            
        return f"External topics available for import: {result}"
    except QuixApiError as e:
        return f"Error retrieving external topics: {str(e)}"

@mcp.tool()
async def check_imported_topics_refresh(ctx: Context) -> str:
    """Check what would happen if you refresh imported topics (dry run).
    """
    try:
        result = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/external/import/refresh"
        )
        
        if not result:
            return "No changes would occur from refreshing imported topics."
            
        output = "Potential changes from refreshing imported topics:\n\n"
        
        # Handle changed topics
        changed_topics = result.get('changedTopics', [])
        if changed_topics and len(changed_topics) > 0:
            output += "Topics that would be changed:\n"
            
            for topic in changed_topics:
                name = topic.get('name')
                output += f"- {name}\n"
                
                current_config = topic.get('currentConfig')
                target_config = topic.get('targetConfig')
                
                if current_config and target_config:
                    output += "  Changes:\n"
                    
                    # Compare partitions
                    current_partitions = current_config.get('partitions')
                    target_partitions = target_config.get('partitions')
                    if current_partitions != target_partitions:
                        output += f"    Partitions: {current_partitions} -> {target_partitions}\n"
                        
                    # Compare replication factor
                    current_replication = current_config.get('replicationFactor')
                    target_replication = target_config.get('replicationFactor')
                    if current_replication != target_replication:
                        output += f"    Replication Factor: {current_replication} -> {target_replication}\n"
                        
                    # Compare retention in minutes
                    current_retention_mins = current_config.get('retentionInMinutes')
                    target_retention_mins = target_config.get('retentionInMinutes')
                    if current_retention_mins != target_retention_mins:
                        output += f"    Retention (minutes): {current_retention_mins} -> {target_retention_mins}\n"
                        
                    # Compare retention in bytes
                    current_retention_bytes = current_config.get('retentionInBytes')
                    target_retention_bytes = target_config.get('retentionInBytes')
                    if current_retention_bytes != target_retention_bytes:
                        output += f"    Retention (bytes): {current_retention_bytes} -> {target_retention_bytes}\n"
                        
                    # Compare cleanup policy
                    current_cleanup = current_config.get('cleanupPolicy')
                    target_cleanup = target_config.get('cleanupPolicy')
                    if current_cleanup != target_cleanup:
                        output += f"    Cleanup Policy: {current_cleanup} -> {target_cleanup}\n"
                        
            output += "\n"
            
        # Handle deleted topics
        deleted_topics = result.get('deletedTopics', [])
        if deleted_topics and len(deleted_topics) > 0:
            output += "Topics that would be deleted:\n"
            
            for topic in deleted_topics:
                name = topic.get('name')
                output += f"- {name}\n"
                
            output += "\n"
            
        return output
    except QuixApiError as e:
        return f"Error checking imported topics refresh: {str(e)}"

@mcp.tool()
async def refresh_imported_topics(ctx: Context) -> str:
    """Refresh imported topics to sync with external changes.
    """
    try:
        result = await make_quix_request(
            ctx,
            "POST",
            "{workspaceId}/topics/external/import/refresh"
        )
        
        if not result:
            return "No changes occurred from refreshing imported topics."
            
        output = "Changes from refreshing imported topics:\n\n"
        
        # Handle changed topics
        changed_topics = result.get('changedTopics', [])
        if changed_topics and len(changed_topics) > 0:
            output += "Topics that were changed:\n"
            
            for topic in changed_topics:
                name = topic.get('name')
                output += f"- {name}\n"
                
                current_config = topic.get('currentConfig')
                target_config = topic.get('targetConfig')
                
                if current_config and target_config:
                    output += "  Changes:\n"
                    
                    # Compare partitions
                    current_partitions = current_config.get('partitions')
                    target_partitions = target_config.get('partitions')
                    if current_partitions != target_partitions:
                        output += f"    Partitions: {current_partitions} -> {target_partitions}\n"
                        
                    # Compare replication factor
                    current_replication = current_config.get('replicationFactor')
                    target_replication = target_config.get('replicationFactor')
                    if current_replication != target_replication:
                        output += f"    Replication Factor: {current_replication} -> {target_replication}\n"
                        
                    # Compare retention in minutes
                    current_retention_mins = current_config.get('retentionInMinutes')
                    target_retention_mins = target_config.get('retentionInMinutes')
                    if current_retention_mins != target_retention_mins:
                        output += f"    Retention (minutes): {current_retention_mins} -> {target_retention_mins}\n"
                        
                    # Compare retention in bytes
                    current_retention_bytes = current_config.get('retentionInBytes')
                    target_retention_bytes = target_config.get('retentionInBytes')
                    if current_retention_bytes != target_retention_bytes:
                        output += f"    Retention (bytes): {current_retention_bytes} -> {target_retention_bytes}\n"
                        
                    # Compare cleanup policy
                    current_cleanup = current_config.get('cleanupPolicy')
                    target_cleanup = target_config.get('cleanupPolicy')
                    if current_cleanup != target_cleanup:
                        output += f"    Cleanup Policy: {current_cleanup} -> {target_cleanup}\n"
                        
            output += "\n"
            
        # Handle deleted topics
        deleted_topics = result.get('deletedTopics', [])
        if deleted_topics and len(deleted_topics) > 0:
            output += "Topics that were deleted:\n"
            
            for topic in deleted_topics:
                name = topic.get('name')
                output += f"- {name}\n"
                
            output += "\n"
            
        return output
    except QuixApiError as e:
        return f"Error refreshing imported topics: {str(e)}"

@mcp.tool()
async def get_topic_metrics(ctx: Context) -> str:
    """Get metrics for all topics in your workspace.
    """
    try:
        metrics = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/metrics/all"
        )
        
        if not metrics:
            return "No topic metrics available."
            
        result = "Topic Metrics:\n\n"
        for metric in metrics:
            topic_id = metric.get('topicId')
            if topic_id:
                result += f"Topic ID: {topic_id}\n"
                
            # Core metrics
            bytes_in = metric.get('bytesInPerSecond')
            if bytes_in is not None:
                result += f"Bytes In/sec: {bytes_in}\n"
                
            bytes_out = metric.get('bytesOutPerSecond')
            if bytes_out is not None:
                result += f"Bytes Out/sec: {bytes_out}\n"
                
            values_persisted = metric.get('valuesPersistedPerSecond')
            if values_persisted is not None:
                result += f"Values Persisted/sec: {values_persisted}\n"
                
            # Streams metrics
            streams_persisted = metric.get('streamsPersisted')
            if streams_persisted and len(streams_persisted) > 0:
                result += "Streams Persisted:\n"
                for stream_id, values in streams_persisted.items():
                    result += f"  {stream_id}: {values} values/sec\n"
                    
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving topic metrics: {str(e)}"


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
    # Load configuration
    config = load_config()
    
    # Set environment variables for backward compatibility
    if config['quix_token']:
        os.environ['QUIX_TOKEN'] = config['quix_token']
    if config['quix_base_url']:
        os.environ['QUIX_BASE_URL'] = config['quix_base_url']
    if config['quix_workspace']:
        os.environ['QUIX_WORKSPACE'] = config['quix_workspace']
    
    # Initialize and start the server
    mcp_server = mcp._mcp_server
    starlette_app = create_starlette_app(mcp_server, debug=config['debug'])
    
    logger.info(f"Starting Quix Applications MCP server on {config['host']}:{config['port']}")
    logger.info(f"Using Quix Portal at {config['quix_base_url']}")
    logger.info(f"Using Quix Workspace {config['quix_workspace']}")
    
    uvicorn.run(starlette_app, host=config['host'], port=config['port'])