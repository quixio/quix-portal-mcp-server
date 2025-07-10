"""
Quix IDE Sessions MCP Tools.

This module provides high-level, workflow-oriented tools for managing Quix IDE sessions,
allowing an AI assistant to write, run, and debug code within a sandboxed environment.
"""

import os
from typing import Any, Optional, Dict, List
from enum import Enum
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

# Enums for the session management tools
class SessionAction(str, Enum):
    start = "start"
    stop = "stop"
    
class SessionUpdateAction(str, Enum):
    update_branch = "update_branch"
    update_variables = "update_variables"
    update_application = "update_application"

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
            
            if branch_name:
                payload["branchName"] = branch_name
            if public_access and url_prefix:
                payload["urlPrefix"] = url_prefix
            if environment_variables:
                payload["environmentVariables"] = environment_variables
            
            session = await _create_session(ctx, workspace_id, payload)
            new_session_id = session.get('sessionId')
            
            result = f"IDE session started successfully with ID: {new_session_id}\n"
            result += f"- Application: {application_id}\n"
            result += f"- Branch: {branch_name or 'default'}\n"
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
            
            payload = {"environmentVariables": environment_variables}
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