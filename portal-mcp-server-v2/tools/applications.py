"""Quix Applications MCP tools."""

from typing import Any, Optional, Dict, List
from enum import Enum
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

# Enum for manage_application action
class ApplicationAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    duplicate = "duplicate"

# --- Internal Helper Functions (original functions, now private) ---

async def _list_applications(ctx: Context, search: Optional[str] = None) -> List[Dict[str, Any]]:
    params = {}
    if search:
        params["search"] = search
    return await make_quix_request(ctx, "GET", "{workspaceId}/applications", params=params)

async def _get_application(ctx: Context, application_id: str) -> Dict[str, Any]:
    return await make_quix_request(ctx, "GET", f"{{workspaceId}}/applications/{application_id}")

async def _create_application(ctx: Context, name: str, path: Optional[str], language: Optional[str]) -> Dict[str, Any]:
    payload = {"applicationName": name, "path": path, "language": language}
    return await make_quix_request(ctx, "POST", "{workspaceId}/applications", json=payload)

async def _update_application(ctx: Context, application_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await make_quix_request(ctx, "PATCH", f"{{workspaceId}}/applications/{application_id}", json=payload)

async def _delete_application(ctx: Context, application_id: str, delete_files: bool):
    params = {"deleteFiles": str(delete_files).lower()}
    return await make_quix_request(ctx, "DELETE", f"{{workspaceId}}/applications/{application_id}", params=params)

async def _duplicate_application(ctx: Context, application_id: str, new_name: str, new_path: Optional[str]) -> Dict[str, Any]:
    payload = {"name": new_name, "path": new_path}
    return await make_quix_request(ctx, "POST", f"{{workspaceId}}/applications/{application_id}/duplicate", json=payload)

# --- New High-Level MCP Tools ---

async def find_applications(ctx: Context, search: Optional[str] = None) -> str:
    try:
        applications = await _list_applications(ctx, search)
        if not applications:
            return "No applications found. You can create one with `manage_application(action='create', ...)`."
        
        result = "Found the following applications:\n\n"
        for app in applications:
            result += f"- Name: {app.get('name')}\n  ID: {app.get('applicationId')}\n  Path: {app.get('path')}\n  Status: {app.get('status', 'N/A')}\n"
        
        result += "\nTo see more details, use `get_application_details(application_id='...')`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error finding applications. Please check your workspace credentials and network connection. If the workspace is empty, you can create your first application with `manage_application(action='create', name='my-app')`. Original error: {str(e)}"

async def get_application_details(ctx: Context, application_id: str) -> str:
    try:
        app = await _get_application(ctx, application_id)
        if not app:
            return f"Application with ID '{application_id}' not found."

        result = f"Details for Application '{app.get('name')}':\n"
        result += f"ID: {app.get('applicationId')}\n"
        result += f"Path: {app.get('path')}\n"
        result += f"Language: {app.get('language', 'N/A')}\n"
        result += f"Status: {app.get('status', 'N/A')}\n"
        if app.get('errorMessage'):
            result += f"Error Message: {app.get('errorMessage')}\n"
        
        variables = app.get('variables')
        if variables:
            result += "\nVariables:\n"
            for var in variables:
                result += f"  - {var.get('name')}: (Type: {var.get('inputType')}, Default: {var.get('defaultValue', 'None')})\n"
        
        result += "\nTo modify this application, use `manage_application(action='update', ...)`."
        result += "\nTo deploy this application, use `manage_deployment(action='create', application_id='...', ...)`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error getting details for application '{application_id}'. The ID might be incorrect or the application may not exist. Try using `find_applications()` to get a list of valid application IDs. Original error: {str(e)}"

async def manage_application(
    ctx: Context, 
    action: ApplicationAction,
    application_id: Optional[str] = None,
    name: Optional[str] = None,
    path: Optional[str] = None,
    language: Optional[str] = None,
    delete_files: bool = True
) -> str:
    try:
        if action == ApplicationAction.create:
            if not name:
                return "Error: 'name' is required to create an application."
            app = await _create_application(ctx, name, path, language)
            return f"Application '{app.get('name')}' created successfully with ID '{app.get('applicationId')}'. You can now deploy it using `manage_deployment`."
        
        if not application_id:
            return f"Error: 'application_id' is required for '{action.value}' action."

        if action == ApplicationAction.update:
            payload = {k: v for k, v in {"applicationName": name, "applicationPath": path, "language": language}.items() if v is not None}
            if not payload:
                return "Error: At least one field (name, path, or language) must be provided for an update."
            app = await _update_application(ctx, application_id, payload)
            return f"Application '{app.get('name')}' updated successfully."

        if action == ApplicationAction.duplicate:
            if not name:
                return "Error: A 'name' for the new duplicated application is required."
            app = await _duplicate_application(ctx, application_id, name, path)
            return f"Application duplicated to '{app.get('name')}' with new ID '{app.get('applicationId')}'."

        if action == ApplicationAction.delete:
            await _delete_application(ctx, application_id, delete_files)
            return f"Application '{application_id}' deleted successfully."
            
    except QuixApiError as e:
        # --- Guided Error Handling ---
        if action == ApplicationAction.create:
            return f"Error creating application. Please ensure the name is unique and all parameters are correct. The name might already exist in this workspace. Original error: {str(e)}"
        elif action in [ApplicationAction.update, ApplicationAction.duplicate, ApplicationAction.delete]:
            return f"Error performing '{action.value}' on application '{application_id}'. Please ensure the ID is correct and you have the necessary permissions. You can verify the ID with `find_applications()`. Original error: {str(e)}"
        else:
            return f"Error managing application: {str(e)}"

async def set_application_topics(
    ctx: Context,
    application_id: str,
    input_topic: Optional[str] = None,
    output_topic: Optional[str] = None
) -> str:
    try:
        current_app = await _get_application(ctx, application_id)
        existing_variables = current_app.get('variables', [])
        
        # Create a dictionary for easy update
        vars_dict = {var['name']: var for var in existing_variables}
        
        if input_topic:
            vars_dict['input'] = {
                "name": "input", "inputType": "InputTopic", "defaultValue": input_topic
            }
        if output_topic:
            vars_dict['output'] = {
                "name": "output", "inputType": "OutputTopic", "defaultValue": output_topic
            }
        
        updated_vars = list(vars_dict.values())
        
        await _update_application(ctx, application_id, {"variables": updated_vars})
        
        response = f"Topics for application '{current_app.get('name')}' configured.\n"
        if input_topic:
            response += f"Input topic set to: '{input_topic}'\n"
        if output_topic:
            response += f"Output topic set to: '{output_topic}'\n"
        response += "You can now deploy this application using `manage_deployment`."
        return response
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error setting topics for application '{application_id}'. Please ensure the application ID is correct and the topic names are valid. You can list applications with `find_applications()` and topics with `find_topics()`. Original error: {str(e)}"