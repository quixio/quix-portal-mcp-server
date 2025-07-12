"""
Quix IDE Sessions MCP Tools.

This module provides high-level, workflow-oriented tools for managing Quix IDE sessions,
allowing an AI assistant to write, run, and debug code within a sandboxed environment.
"""

import os
import base64
from typing import Any, Optional, Dict, List
from enum import Enum
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError
from . import applications

# Enums for the session management tools
class SessionAction(str, Enum):
    start = "start"
    stop = "stop"
    
class SessionUpdateAction(str, Enum):
    update_branch = "update_branch"
    update_variables = "update_variables"
    update_application = "update_application"
    sync_application_variables = "sync_application_variables"

# --- Internal Helper Functions (Direct API Wrappers) ---

async def _create_session(ctx: Context, workspace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Internal helper to create a new IDE session."""
    return await make_quix_request(ctx, "POST", "sessions", workspace_id=workspace_id, json=payload)

async def _get_session(ctx: Context, workspace_id: str, session_id: str) -> Dict[str, Any]:
    """Internal helper to get details of a specific session."""
    return await make_quix_request(ctx, "GET", f"sessions/{session_id}", workspace_id=workspace_id)

async def _list_sessions(ctx: Context, workspace_id: str) -> List[Dict[str, Any]]:
    """Internal helper to list all active sessions for the user."""
    return await make_quix_request(ctx, "GET", "sessions", workspace_id=workspace_id)

async def _delete_session(ctx: Context, workspace_id: str, session_id: str):
    """Internal helper to terminate an IDE session."""
    return await make_quix_request(ctx, "DELETE", f"sessions/{session_id}", workspace_id=workspace_id)

async def _update_session(ctx: Context, workspace_id: str, session_id: str, payload: Dict[str, Any]):
    """Internal helper to update session configuration."""
    return await make_quix_request(ctx, "PATCH", f"sessions/{session_id}", workspace_id=workspace_id, json=payload)

async def _run_in_session(ctx: Context, workspace_id: str, session_id: str, file_to_run: Optional[str] = None):
    """Internal helper to run code in a session."""
    payload = {}
    if file_to_run:
        payload["file"] = file_to_run
    return await make_quix_request(ctx, "POST", f"sessions/{session_id}/run", workspace_id=workspace_id, json=payload)

async def _setup_session(ctx: Context, workspace_id: str, session_id: str, force: bool = False):
    """Internal helper to re-run setup for a session."""
    params = {"force": str(force).lower()}
    return await make_quix_request(ctx, "POST", f"sessions/{session_id}/setup", workspace_id=workspace_id, params=params)

async def _heartbeat_session(ctx: Context, workspace_id: str, session_id: str):
    """Internal helper to send heartbeat to keep session alive."""
    return await make_quix_request(ctx, "PUT", f"sessions/{session_id}/heartbeat", workspace_id=workspace_id)

async def _get_session_application(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None) -> Dict[str, Any]:
    """Internal helper to get application details from session."""
    params = {}
    if reference:
        params["reference"] = reference
    return await make_quix_request(ctx, "GET", f"sessions/{session_id}/application", workspace_id=workspace_id, params=params)

async def _update_session_application(ctx: Context, workspace_id: str, session_id: str, payload: Dict[str, Any]):
    """Internal helper to update application configuration in session."""
    return await make_quix_request(ctx, "PATCH", f"sessions/{session_id}/application", workspace_id=workspace_id, json=payload)

async def _get_session_zip(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None):
    """Internal helper to download session application as zip."""
    params = {}
    if reference:
        params["reference"] = reference
    return await make_quix_request(ctx, "GET", f"sessions/{session_id}/zip", workspace_id=workspace_id, params=params)

async def _get_git_errors(ctx: Context, workspace_id: str, session_id: str) -> List[Dict[str, Any]]:
    """Internal helper to get git errors for a session."""
    return await make_quix_request(ctx, "GET", f"sessions/{session_id}/git/errors", workspace_id=workspace_id)

async def _clean_git_errors(ctx: Context, workspace_id: str, session_id: str):
    """Internal helper to clean git errors for a session."""
    return await make_quix_request(ctx, "POST", f"sessions/{session_id}/git/errors/clean", workspace_id=workspace_id)

async def _commit_session_files(ctx: Context, workspace_id: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Internal helper to commit file changes to a session."""
    return await make_quix_request(ctx, "POST", f"sessions/{session_id}/commit", workspace_id=workspace_id, json=payload)

async def _get_session_files(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None) -> List[str]:
    """Internal helper to get list of files in a session."""
    params = {}
    if reference:
        params["reference"] = reference
    return await make_quix_request(ctx, "GET", f"sessions/{session_id}/files", workspace_id=workspace_id, params=params)

async def _get_session_folders(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None, hide_application_folders: bool = False, hide_existing_included_folders: bool = False) -> List[str]:
    """Internal helper to get list of folders in a session."""
    params = {}
    if reference:
        params["reference"] = reference
    if hide_application_folders:
        params["hideApplicationFolders"] = "true"
    if hide_existing_included_folders:
        params["hideExistingIncludedFolders"] = "true"
    return await make_quix_request(ctx, "GET", f"sessions/{session_id}/folders", workspace_id=workspace_id, params=params)

async def _get_session_files_with_metadata(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None) -> List[Dict[str, Any]]:
    """Internal helper to get files with metadata in a session."""
    params = {}
    if reference:
        params["reference"] = reference
    return await make_quix_request(ctx, "GET", f"sessions/{session_id}/files-with-metadata", workspace_id=workspace_id, params=params)

async def _get_session_file_content(ctx: Context, workspace_id: str, session_id: str, file_path: str, reference: Optional[str] = None) -> str:
    """Internal helper to get content of a specific file in a session."""
    params = {}
    if reference:
        params["reference"] = reference
    return await make_quix_request(ctx, "GET", f"sessions/{session_id}/files/{file_path}", workspace_id=workspace_id, params=params)

async def _update_session_file(ctx: Context, workspace_id: str, session_id: str, file_path: str, content: str) -> Dict[str, Any]:
    """Internal helper to update or create a file in a session."""
    return await make_quix_request(ctx, "POST", f"sessions/{session_id}/files/{file_path}", workspace_id=workspace_id, data=content, headers={"Content-Type": "text/plain"})

async def _delete_session_file(ctx: Context, workspace_id: str, session_id: str, file_path: str) -> Dict[str, Any]:
    """Internal helper to delete a file from a session."""
    return await make_quix_request(ctx, "DELETE", f"sessions/{session_id}/files/{file_path}", workspace_id=workspace_id)

# --- High-Level MCP Tools ---

async def find_sessions(ctx: Context, workspace_id: str) -> str:
    """
    <usecase>
    Finds and lists all active IDE sessions for a specific workspace. Use this to check if a session is already running or to get a session_id for other tools.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    This tool lists all active sessions in the specified workspace. Sessions show their application, branch, and resource allocation.
    </instructions>
    """
    try:
        sessions = await _list_sessions(ctx, workspace_id)
        if not sessions:
            return "No active IDE sessions found. You can start one with `manage_session(action='start', application_id='...')`."
        
        result = "Found the following active IDE sessions:\n\n"
        for s in sessions:
            result += f"- Session ID: {s.get('sessionId')}\n"
            result += f"  Application ID: {s.get('applicationId')}\n"
            result += f"  Branch: {s.get('branchName', 'default')}\n"
            result += f"  Status: {'Idle' if s.get('isIdle') else 'Active'}\n"
            result += f"  Resources: {s.get('cpuMillicores', 'N/A')}m CPU, {s.get('memoryInMb', 'N/A')}MB RAM\n"
            result += f"  Created: {s.get('createdAt', 'N/A')}\n"
            if s.get('publicAccess'):
                result += f"  Public URL: {s.get('urlPrefix', 'N/A')}\n"
            result += "\n"
        
        result += "To manage a session, use `manage_session(session_id='...', action='...')` or get details with `get_session_details(session_id='...')`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error finding sessions. Please check your workspace credentials and network connection. If you haven't created any sessions yet, you can start one with `manage_session(action='start', application_id='...')`. Original error: {str(e)}"

async def get_session_details(ctx: Context, workspace_id: str, session_id: str) -> str:
    """
    <usecase>
    Retrieves detailed information about a specific IDE session, including its configuration, status, and resource usage.
    </usecase>
    <instructions>
    You must provide a valid 'session_id', which can be found using the 'find_sessions' tool.
    </instructions>
    """
    try:
        session = await _get_session(ctx, workspace_id, session_id)
        if not session:
            return f"Session '{session_id}' not found."

        result = f"Details for IDE Session '{session_id}':\n\n"
        result += f"Application ID: {session.get('applicationId')}\n"
        result += f"Branch: {session.get('branchName', 'default')}\n"
        result += f"Status: {'Idle' if session.get('isIdle') else 'Active'}\n"
        result += f"Resources: {session.get('cpuMillicores', 'N/A')}m CPU, {session.get('memoryInMb', 'N/A')}MB RAM\n"
        result += f"Created: {session.get('createdAt', 'N/A')}\n"
        result += f"Updated: {session.get('updatedAt', 'N/A')}\n"
        
        if session.get('publicAccess'):
            result += f"Public Access: Yes (URL: {session.get('urlPrefix', 'N/A')})\n"
        else:
            result += f"Public Access: No\n"
            
        env_vars = session.get('environmentVariables', {})
        if env_vars:
            result += f"\nEnvironment Variables:\n"
            for key, value in env_vars.items():
                result += f"  - {key}: {value}\n"
        
        result += "\nNext steps you might consider:"
        result += "\n- Run code with `run_code_in_session(session_id='...', file_to_run='...')`"
        result += "\n- Update configuration with `update_session_config(...)`"
        result += "\n- Get application details with `get_session_application_details(...)`"
        result += "\n- Check for git errors with `check_session_git_status(...)`"
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error getting details for session '{session_id}'. The session ID might be incorrect or the session may have expired. Try using `find_sessions()` to get a list of valid session IDs. Original error: {str(e)}"

async def manage_session(
    ctx: Context,
    workspace_id: str,
    action: SessionAction,
    application_id: Optional[str] = None,
    session_id: Optional[str] = None,
    branch_name: Optional[str] = None,
    cpu_millicores: int = 1000,
    memory_in_mb: int = 1024,
    public_access: bool = False,
    url_prefix: Optional[str] = None,
    environment_variables: Optional[Dict[str, str]] = None
) -> str:
    """
    <usecase>
    Manages an IDE session. Use this to start a new session for an application or to stop an existing one.
    </usecase>
    <instructions>
    - To 'start' a session, the 'application_id' is required. You can optionally specify resource allocation, branch, and environment variables.
    - To 'stop' a session, the 'session_id' is required.
    - For public access, provide 'url_prefix' when setting 'public_access' to True.
    </instructions>
    """
    try:
        if action == SessionAction.start:
            if not application_id:
                return "Error: 'application_id' is required to start a session."
            
            payload = {
                "workspaceId": workspace_id,
                "applicationId": application_id,
                "cpuMillicores": cpu_millicores,
                "memoryInMb": memory_in_mb,
                "publicAccess": public_access
            }
            
            # Default to "main" branch if not specified
            payload["branchName"] = branch_name or "main"
            if public_access and url_prefix:
                payload["urlPrefix"] = url_prefix
            if environment_variables:
                # Validate environment variables against application variable definitions
                from .applications import _get_application
                app_details = await _get_application(ctx, workspace_id, application_id)
                app_variables = app_details.get('variables', []) if app_details else []
                
                # Create lookup of application variables by name with their types
                app_var_types = {var.get('name'): var.get('inputType') for var in app_variables}
                
                # Check that all required application variables are provided  
                required_vars = [var.get('name') for var in app_variables if var.get('required')]
                missing_required = [var for var in required_vars if var not in environment_variables]
                if missing_required:
                    return f"Error: Missing required variables: {', '.join(missing_required)}. These variables are required by the application."
                
                # Separate regular environment variables from secrets
                regular_env_vars = {}
                secret_keys = {}
                
                # Validate that session variables match application variable types
                for var_name, var_value in environment_variables.items():
                    if var_name in app_var_types:
                        expected_type = app_var_types[var_name]
                        
                        # If this is a secret variable, put it in secretKeys field
                        if expected_type == 'Secret':
                            secret_keys[var_name] = var_value
                        else:
                            regular_env_vars[var_name] = var_value
                    else:
                        # Variables not defined in application go to regular env vars
                        regular_env_vars[var_name] = var_value
                
                # Set both fields in payload
                if regular_env_vars:
                    payload["environmentVariables"] = regular_env_vars
                if secret_keys:
                    payload["secretKeys"] = secret_keys
            
            session = await _create_session(ctx, workspace_id, payload)
            new_session_id = session.get('sessionId')
            
            result = f"IDE session started successfully with ID: {new_session_id}\n"
            result += f"- Application: {application_id}\n"
            result += f"- Branch: {branch_name or 'main'}\n"
            result += f"- Resources: {cpu_millicores}m CPU, {memory_in_mb}MB RAM\n"
            if public_access:
                result += f"- Public URL: {session.get('urlPrefix', 'N/A')}\n"
            result += f"\nYou can now run code with `run_code_in_session(session_id='{new_session_id}', ...)` or get application details with `get_session_application_details(session_id='{new_session_id}')`."
            return result

        if action == SessionAction.stop:
            if not session_id:
                return "Error: 'session_id' is required to stop a session."
            
            await _delete_session(ctx, workspace_id, session_id)
            return f"Session '{session_id}' has been stopped successfully and resources have been released."
            
    except QuixApiError as e:
        # --- Guided Error Handling ---
        if action == SessionAction.start:
            return f"Error starting session for application '{application_id}'. Please ensure the application ID is correct and you have the necessary permissions. You can verify the application ID with `find_applications()`. Original error: {str(e)}"
        elif action == SessionAction.stop:
            return f"Error stopping session '{session_id}'. Please ensure the session ID is correct and the session exists. You can verify the session ID with `find_sessions()`. Original error: {str(e)}"
        else:
            return f"Error managing session: {str(e)}"

async def run_code_in_session(
    ctx: Context,
    workspace_id: str,
    session_id: str,
    file_to_run: Optional[str] = None,
    force_setup: bool = False
) -> str:
    """
    <usecase>
    Executes code within a sandboxed IDE session and returns the execution status. Use this for testing and debugging code changes.
    </usecase>
    <instructions>
    - 'session_id' must be an active session ID.
    - 'file_to_run' is optional - if not provided, runs the default application entry point.
    - 'force_setup' can be used to force re-setup before running if there are environment issues.
    </instructions>
    """
    try:
        # Force setup if requested
        if force_setup:
            await _setup_session(ctx, workspace_id, session_id, force=True)
            await ctx.info(f"Forced setup completed for session '{session_id}'.")
        
        # Run the code
        result = await _run_in_session(ctx, workspace_id, session_id, file_to_run)
        
        response = f"Code execution initiated in session '{session_id}'"
        if file_to_run:
            response += f" for file '{file_to_run}'"
        response += ".\n\n"
        
        if result:
            response += f"Execution result:\n{result}"
        else:
            response += "Execution completed. Check the session logs or application output for results."
        
        response += f"\n\nYou can get more details with `get_session_details(session_id='{session_id}')` or check for git errors with `check_session_git_status(session_id='{session_id}')`."
        return response
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error running code in session '{session_id}'. Please ensure the session ID is correct and the session is active. You can verify the session with `find_sessions()`. If there are setup issues, try using `force_setup=True`. Original error: {str(e)}"

async def update_session_config(
    ctx: Context,
    workspace_id: str,
    session_id: str,
    action: SessionUpdateAction,
    branch_name: Optional[str] = None,
    git_reference: Optional[str] = None,
    environment_variables: Optional[Dict[str, str]] = None,
    dockerfile: Optional[str] = None,
    run_entry_point: Optional[str] = None,
    variables: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    <usecase>
    Updates session configuration such as git branch, environment variables, or application settings.
    </usecase>
    <instructions>
    - 'session_id' must be an active session ID.
    - For 'update_branch', provide 'branch_name' or 'git_reference'.
    - For 'update_variables', provide 'environment_variables' dictionary.
    - For 'update_application', provide 'dockerfile', 'run_entry_point', or 'variables'.
    - For 'sync_application_variables', no additional parameters needed - automatically syncs session with current application variable configuration including proper Secret type handling.
    </instructions>
    """
    try:
        if action == SessionUpdateAction.update_branch:
            if not branch_name and not git_reference:
                return "Error: Either 'branch_name' or 'git_reference' is required for branch update."
            
            payload = {}
            if branch_name:
                payload["branchName"] = branch_name
            if git_reference:
                payload["gitReference"] = git_reference
                
            await _update_session(ctx, workspace_id, session_id, payload)
            return f"Session '{session_id}' branch updated successfully. You may need to run setup again with `run_code_in_session(session_id='{session_id}', force_setup=True)`."
        
        elif action == SessionUpdateAction.update_variables:
            if not environment_variables:
                return "Error: 'environment_variables' is required for variable update."
            
            # Initialize variables for secret separation
            regular_env_vars = {}
            secret_keys = {}
            
            # Get session details to find the application ID for validation
            session_details = await _get_session(ctx, workspace_id, session_id)
            application_id = session_details.get('applicationId')
            
            if application_id:
                # Get application variable definitions
                from .applications import _get_application
                app_details = await _get_application(ctx, workspace_id, application_id)
                app_variables = app_details.get('variables', []) if app_details else []
                
                # Create lookup of application variables by name with their types
                app_var_types = {var.get('name'): var.get('inputType') for var in app_variables}
                
                # Check that all required application variables are provided
                required_vars = [var.get('name') for var in app_variables if var.get('required')]
                missing_required = [var for var in required_vars if var not in environment_variables]
                if missing_required:
                    return f"Error: Missing required variables: {', '.join(missing_required)}. These variables are required by the application."
                
                # Validate that session variables match application variable types
                for var_name, var_value in environment_variables.items():
                    if var_name in app_var_types:
                        expected_type = app_var_types[var_name]
                        
                        # If this is a secret variable, put it in secretKeys field
                        if expected_type == 'Secret':
                            secret_keys[var_name] = var_value
                        else:
                            regular_env_vars[var_name] = var_value
                    else:
                        # Variables not defined in application go to regular env vars
                        regular_env_vars[var_name] = var_value
            else:
                # If no application context, treat all variables as regular env vars
                # (though this should be rare for IDE sessions)
                regular_env_vars = environment_variables.copy()
            
            # Create payload with proper field separation
            payload = {}
            if regular_env_vars:
                payload["environmentVariables"] = regular_env_vars
            if secret_keys:
                payload["secretKeys"] = secret_keys
            await _update_session(ctx, workspace_id, session_id, payload)
            return f"Session '{session_id}' environment variables updated successfully."
        
        elif action == SessionUpdateAction.update_application:
            payload = {}
            if dockerfile:
                payload["dockerfile"] = dockerfile
            if run_entry_point:
                payload["runEntryPoint"] = run_entry_point
            if variables:
                payload["variables"] = variables
            
            if not payload:
                return "Error: At least one application parameter (dockerfile, run_entry_point, or variables) must be provided."
            
            await _update_session_application(ctx, workspace_id, session_id, payload)
            return f"Session '{session_id}' application configuration updated successfully."
        
        elif action == SessionUpdateAction.sync_application_variables:
            # Get session details to find the application ID
            session_details = await _get_session(ctx, workspace_id, session_id)
            application_id = session_details.get('applicationId')
            
            if not application_id:
                return f"Error: Could not determine application ID for session '{session_id}'."
            
            # Get the current application configuration with variables
            app_details = await applications._get_application(ctx, workspace_id, application_id)
            app_variables = app_details.get('variables', [])
            
            if not app_variables:
                return f"No variables found in application '{application_id}' to sync."
            
            # Update session application with the current application variables
            payload = {"variables": app_variables}
            await _update_session_application(ctx, workspace_id, session_id, payload)
            
            # Format response showing synced variables
            result = f"Session '{session_id}' successfully synced with application '{application_id}' variables:\n\n"
            for var in app_variables:
                result += f"• {var.get('name')} ({var.get('inputType')})"
                if var.get('defaultValue'):
                    if var.get('inputType') == 'Secret':
                        result += f" = [Secret: {var.get('defaultValue')}]"
                    else:
                        result += f" = {var.get('defaultValue')}"
                result += "\n"
            
            result += f"\nThis ensures proper secret resolution and variable type handling. You can now run code with `run_code_in_session(session_id='{session_id}', ...)`."
            return result
        
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error updating session '{session_id}' configuration. Please ensure the session ID is correct and you have the necessary permissions. You can verify the session with `find_sessions()`. Original error: {str(e)}"

async def get_session_application_details(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None) -> str:
    """
    <usecase>
    Retrieves detailed application information from an IDE session, including configuration and file structure.
    </usecase>
    <instructions>
    - 'session_id' must be an active session ID.
    - 'reference' is optional - specify a git reference to view application at that point.
    </instructions>
    """
    try:
        app_details = await _get_session_application(ctx, workspace_id, session_id, reference)
        
        result = f"Application Details for Session '{session_id}':\n\n"
        result += f"Name: {app_details.get('name', 'N/A')}\n"
        result += f"ID: {app_details.get('applicationId', 'N/A')}\n"
        result += f"Path: {app_details.get('path', 'N/A')}\n"
        result += f"Language: {app_details.get('language', 'N/A')}\n"
        result += f"Status: {app_details.get('status', 'N/A')}\n"
        
        if app_details.get('dockerfile'):
            result += f"Dockerfile: Present\n"
        if app_details.get('runEntryPoint'):
            result += f"Run Entry Point: {app_details.get('runEntryPoint')}\n"
            
        variables = app_details.get('variables', [])
        if variables:
            result += f"\nApplication Variables:\n"
            for var in variables:
                result += f"  - {var.get('name', 'N/A')}: {var.get('inputType', 'N/A')} (Default: {var.get('defaultValue', 'None')})\n"
        
        result += f"\nYou can run this application with `run_code_in_session(session_id='{session_id}')` or download the code with `download_session_code(session_id='{session_id}')`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error getting application details for session '{session_id}'. Please ensure the session ID is correct and the session is active. You can verify the session with `find_sessions()`. Original error: {str(e)}"

async def check_session_git_status(ctx: Context, workspace_id: str, session_id: str, clean_errors: bool = False) -> str:
    """
    <usecase>
    Checks the git status of a session and optionally cleans any git errors. Useful for debugging git-related issues.
    </usecase>
    <instructions>
    - 'session_id' must be an active session ID.
    - 'clean_errors' set to True will attempt to clean any git errors found.
    </instructions>
    """
    try:
        git_errors = await _get_git_errors(ctx, workspace_id, session_id)
        
        if not git_errors:
            return f"Session '{session_id}' has no git errors. Git status is clean."
        
        result = f"Git Status for Session '{session_id}':\n\n"
        result += f"Found {len(git_errors)} git error(s):\n"
        
        for i, error in enumerate(git_errors, 1):
            result += f"{i}. Type: {error.get('type', 'Unknown')}\n"
            result += f"   Message: {error.get('message', 'No message')}\n"
            if error.get('file'):
                result += f"   File: {error.get('file')}\n"
            result += "\n"
        
        if clean_errors:
            await _clean_git_errors(ctx, workspace_id, session_id)
            result += "Git errors have been cleaned. You can now proceed with your session operations."
        else:
            result += "To clean these errors, run this command again with `clean_errors=True`."
        
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error checking git status for session '{session_id}'. Please ensure the session ID is correct and the session is active. You can verify the session with `find_sessions()`. Original error: {str(e)}"

async def keep_session_alive(ctx: Context, workspace_id: str, session_id: str) -> str:
    """
    <usecase>
    Sends a heartbeat to keep an IDE session alive and prevent it from timing out. Useful for long-running development sessions.
    </usecase>
    <instructions>
    - 'session_id' must be an active session ID.
    - Use this periodically during long development sessions to prevent automatic session termination.
    </instructions>
    """
    try:
        await _heartbeat_session(ctx, workspace_id, session_id)
        return f"Heartbeat sent to session '{session_id}'. Session will remain active for the extended timeout period."
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error sending heartbeat to session '{session_id}'. The session ID might be incorrect or the session may have already expired. Try using `find_sessions()` to get a list of valid session IDs. Original error: {str(e)}"

async def download_session_code(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None) -> str:
    """
    <usecase>
    Downloads the complete application code from an IDE session as a zip file. Useful for backing up or sharing code.
    </usecase>
    <instructions>
    - 'session_id' must be an active session ID.
    - 'reference' is optional - specify a git reference to download code at that point.
    - This returns information about the download, not the actual file content.
    </instructions>
    """
    try:
        zip_result = await _get_session_zip(ctx, workspace_id, session_id, reference)
        
        if zip_result:
            return f"Application code from session '{session_id}' is ready for download. The zip file contains all application files and can be used for backup or sharing purposes."
        else:
            return f"No application code found in session '{session_id}' or the session is empty."
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error downloading code from session '{session_id}'. Please ensure the session ID is correct and the session is active. You can verify the session with `find_sessions()`. Original error: {str(e)}"

async def commit_session_files(
    ctx: Context,
    workspace_id: str,
    session_id: str,
    file_path: str,
    content: str,
    commit_message: Optional[str] = None,
    action: str = "Update"
) -> str:
    """
    <usecase>
    Updates the content of a file in an IDE session, or creates one if it doesn't already exist. This allows you to modify code files within the session.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    - 'file_path' is the path to the file within the session (e.g., 'main.py', 'src/utils.py')
    - 'content' is the new file content as a string
    - 'commit_message' is optional - describes what changes were made
    - 'action' can be 'Create' for new files or 'Update' for existing files (default: 'Update')
    </instructions>
    """
    try:
        # Encode content as base64
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        # Prepare the commit payload
        payload = {
            "actions": [
                {
                    "action": action,
                    "filePath": file_path,
                    "content": content_base64
                }
            ],
            "commitMessage": commit_message or f"{action} {file_path}"
        }
        
        result = await _commit_session_files(ctx, workspace_id, session_id, payload)
        
        response = f"Successfully {action.lower()}d file '{file_path}' in session '{session_id}'"
        if result and result.get('reference'):
            response += f"\n- Commit reference: {result.get('reference')}"
        if result and result.get('message'):
            response += f"\n- Commit message: {result.get('message')}"
        if result and result.get('createdAt'):
            response += f"\n- Created at: {result.get('createdAt')}"
        
        response += f"\n\nYou can now run the updated code with `run_code_in_session(session_id='{session_id}', file_to_run='{file_path}')` or run the default application."
        return response
        
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error committing file '{file_path}' to session '{session_id}'. Please ensure the session ID is correct and the session is active. You can verify the session with `find_sessions()`. Original error: {str(e)}"

async def explore_session_codebase(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None) -> str:
    """
    <usecase>
    Explores the complete codebase structure of an IDE session. Use this when you need to understand the project layout, find specific files, or get an overview of the application architecture.
    </usecase>
    <instructions>
    You must provide valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    - 'reference' is optional - specify a git reference to explore code from that point.
    - Returns organized file structure with key files highlighted and next actions suggested.
    </instructions>
    """
    try:
        # Get both files and folders to provide complete picture
        files = await _get_session_files(ctx, workspace_id, session_id, reference)
        folders = await _get_session_folders(ctx, workspace_id, session_id, reference, hide_application_folders=False, hide_existing_included_folders=False)
        files_with_metadata = await _get_session_files_with_metadata(ctx, workspace_id, session_id, reference)
        
        if not files and not folders:
            return f"Session '{session_id}' appears to be empty or not properly initialized. Try running `run_code_in_session(session_id='{session_id}', force_setup=True)` to initialize the session."
        
        result = f"Codebase Overview for Session '{session_id}'"
        if reference:
            result += f" (reference: {reference})"
        result += ":\n\n"
        
        # Organize files by type and importance
        code_files = []
        config_files = []
        data_files = []
        other_files = []
        main_app_files = []
        
        # Create metadata lookup
        metadata_lookup = {f.get('path', ''): f for f in files_with_metadata} if files_with_metadata else {}
        
        for file_path in sorted(files):
            file_meta = metadata_lookup.get(file_path, {})
            if file_meta.get('isMainApp', False):
                main_app_files.append(file_path)
            elif file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php')):
                code_files.append(file_path)
            elif file_path.endswith(('.json', '.yml', '.yaml', '.xml', '.toml', '.ini', '.cfg', '.conf', 'Dockerfile', 'requirements.txt', 'package.json')):
                config_files.append(file_path)
            elif file_path.endswith(('.csv', '.txt', '.md', '.log')):
                data_files.append(file_path)
            else:
                other_files.append(file_path)
        
        # Display organized structure
        if main_app_files:
            result += "🎯 **Main Application Files:**\n"
            for file_path in main_app_files:
                size = metadata_lookup.get(file_path, {}).get('byteSize', 0)
                result += f"  • {file_path} ({size} bytes)\n"
            result += "\n"
        
        if folders:
            result += "📁 **Directory Structure:**\n"
            for folder in sorted(folders)[:10]:  # Show first 10 folders
                result += f"  • {folder}/\n"
            if len(folders) > 10:
                result += f"  ... and {len(folders) - 10} more folders\n"
            result += "\n"
        
        if code_files:
            result += "💻 **Code Files:**\n"
            for file_path in code_files[:8]:  # Show first 8 code files
                size = metadata_lookup.get(file_path, {}).get('byteSize', 0)
                result += f"  • {file_path} ({size} bytes)\n"
            if len(code_files) > 8:
                result += f"  ... and {len(code_files) - 8} more code files\n"
            result += "\n"
        
        if config_files:
            result += "⚙️ **Configuration Files:**\n"
            for file_path in config_files[:5]:
                size = metadata_lookup.get(file_path, {}).get('byteSize', 0)
                result += f"  • {file_path} ({size} bytes)\n"
            if len(config_files) > 5:
                result += f"  ... and {len(config_files) - 5} more config files\n"
            result += "\n"
        
        # Summary and next actions
        result += f"**Summary:** {len(files)} files in {len(folders)} folders\n\n"
        
        result += "**Next Actions:**\n"
        if main_app_files:
            result += f"• To examine the main application: `read_session_file(session_id='{session_id}', file_path='{main_app_files[0]}')`\n"
        if code_files:
            result += f"• To view any code file: `read_session_file(session_id='{session_id}', file_path='...')`\n"
        if config_files:
            result += f"• To check configuration: `read_session_file(session_id='{session_id}', file_path='{config_files[0]}')`\n"
        result += f"• To run the application: `run_code_in_session(session_id='{session_id}')`\n"
        result += f"• To work with specific files: `work_with_session_files(session_id='{session_id}', action='...')`\n"
        
        return result
    except QuixApiError as e:
        return f"Error exploring codebase in session '{session_id}'. Please ensure the session ID is correct and active. You can verify with `find_sessions()`. Original error: {str(e)}"

async def read_session_file(ctx: Context, workspace_id: str, session_id: str, file_path: str, reference: Optional[str] = None) -> str:
    """
    <usecase>
    Reads and displays the content of a specific file in an IDE session. Use this to examine code, configuration, or any text-based files when you need to understand or debug the application.
    </usecase>
    <instructions>
    You must provide valid 'workspace_id', 'session_id', and 'file_path'. Use 'find_workspaces()', 'find_sessions()', and 'explore_session_codebase()' to get these details.
    - 'reference' is optional - specify a git reference to read from that point.
    - Returns formatted content with syntax highlighting and editing suggestions.
    </instructions>
    """
    try:
        # Get file content and metadata
        content = await _get_session_file_content(ctx, workspace_id, session_id, file_path, reference)
        files_with_metadata = await _get_session_files_with_metadata(ctx, workspace_id, session_id, reference)
        
        if not content:
            return f"File '{file_path}' in session '{session_id}' is empty or not found. Use `explore_session_codebase(session_id='{session_id}')` to see available files."
        
        # Get file metadata
        file_meta = next((f for f in files_with_metadata if f.get('path') == file_path), {}) if files_with_metadata else {}
        
        result = f"📄 **File: {file_path}**"
        if reference:
            result += f" (reference: {reference})"
        result += "\n\n"
        
        # Add metadata if available
        if file_meta:
            size = file_meta.get('byteSize', 0)
            mime_type = file_meta.get('mimeType', 'Unknown')
            is_binary = file_meta.get('isBinary', False)
            is_main_app = file_meta.get('isMainApp', False)
            
            result += f"**File Info:** {size} bytes | {mime_type}"
            if is_main_app:
                result += " | 🎯 Main Application File"
            if is_binary:
                result += " | ⚠️ Binary File"
            result += "\n\n"
            
            if is_binary:
                result += "**Note:** This is a binary file. Content display may not be meaningful.\n\n"
        
        # Display content with syntax highlighting
        result += "**Content:**\n"
        result += "```\n"
        result += content
        result += "\n```\n\n"
        
        # Suggest next actions based on file type
        result += "**Next Actions:**\n"
        result += f"• To modify this file: `work_with_session_files(session_id='{session_id}', action='update', file_path='{file_path}', content='...')`\n"
        if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php')):
            result += f"• To run this file: `run_code_in_session(session_id='{session_id}', file_to_run='{file_path}')`\n"
        result += f"• To explore more files: `explore_session_codebase(session_id='{session_id}')`\n"
        result += f"• To commit changes: `commit_session_files(session_id='{session_id}', file_path='{file_path}', ...)`\n"
        
        return result
    except QuixApiError as e:
        return f"Error reading file '{file_path}' in session '{session_id}'. Please ensure the session ID and file path are correct. You can explore available files with `explore_session_codebase()`. Original error: {str(e)}"

async def work_with_session_files(ctx: Context, workspace_id: str, session_id: str, action: str, file_path: str, content: Optional[str] = None) -> str:
    """
    <usecase>
    Performs file operations in an IDE session - create, update, or delete files. Use this when you need to modify code, add new files, or remove unwanted files as part of development workflow.
    </usecase>
    <instructions>
    You must provide valid 'workspace_id', 'session_id', 'action', and 'file_path'. Use 'find_workspaces()' and 'find_sessions()' to get IDs.
    - 'action' must be one of: 'create', 'update', 'delete'
    - 'content' is required for 'create' and 'update' actions
    - 'file_path' is the path to the file within the session (e.g., 'main.py', 'src/utils.py')
    - For safety, delete operations will ask for confirmation in error handling
    </instructions>
    """
    try:
        if action.lower() in ['create', 'update']:
            if not content:
                return f"Error: 'content' is required for '{action}' action. Please provide the file content as a string."
            
            # Use the direct file update API for immediate changes
            result = await _update_session_file(ctx, workspace_id, session_id, file_path, content)
            
            action_word = "created" if action.lower() == 'create' else "updated"
            response = f"✅ Successfully {action_word} file '{file_path}' in session '{session_id}'"
            
            if result:
                if result.get('reference'):
                    response += f"\n📝 Commit reference: {result.get('reference')}"
                if result.get('message'):
                    response += f"\n💬 Commit message: {result.get('message')}"
                if result.get('createdAt'):
                    response += f"\n🕐 Created at: {result.get('createdAt')}"
            
            response += f"\n\n**Next Actions:**\n"
            response += f"• To view the {action_word} file: `read_session_file(session_id='{session_id}', file_path='{file_path}')`\n"
            if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php')):
                response += f"• To run this file: `run_code_in_session(session_id='{session_id}', file_to_run='{file_path}')`\n"
            response += f"• To run the application: `run_code_in_session(session_id='{session_id}')`\n"
            response += f"• To explore the codebase: `explore_session_codebase(session_id='{session_id}')`\n"
            
            return response
            
        elif action.lower() == 'delete':
            result = await _delete_session_file(ctx, workspace_id, session_id, file_path)
            
            response = f"🗑️ Successfully deleted file '{file_path}' from session '{session_id}'"
            
            if result:
                if result.get('reference'):
                    response += f"\n📝 Commit reference: {result.get('reference')}"
                if result.get('message'):
                    response += f"\n💬 Commit message: {result.get('message')}"
                if result.get('createdAt'):
                    response += f"\n🕐 Created at: {result.get('createdAt')}"
            
            response += f"\n\n⚠️ **Warning:** This action cannot be undone. The file has been permanently removed from the session."
            response += f"\n\n**Next Actions:**\n"
            response += f"• To see remaining files: `explore_session_codebase(session_id='{session_id}')`\n"
            response += f"• To run the application: `run_code_in_session(session_id='{session_id}')`\n"
            
            return response
            
        else:
            return f"Error: Invalid action '{action}'. Valid actions are: 'create', 'update', 'delete'. Use 'create' for new files, 'update' for existing files, or 'delete' to remove files."
            
    except QuixApiError as e:
        if action.lower() == 'delete':
            return f"Error deleting file '{file_path}' from session '{session_id}'. Please ensure the session ID and file path are correct. **Safety Note:** Delete operations are permanent and cannot be undone. You can verify files with `explore_session_codebase()`. Original error: {str(e)}"
        else:
            return f"Error {action}ing file '{file_path}' in session '{session_id}'. Please ensure the session ID is correct and the session is active. You can verify with `find_sessions()`. Original error: {str(e)}"