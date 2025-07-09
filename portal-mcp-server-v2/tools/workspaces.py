"""
Quix Workspaces and Git Workflow MCP tools.

This module provides high-level, workflow-oriented tools for managing Quix workspaces
and promoting changes between environments.
"""

import os
from typing import Any, Optional, Dict, List
from enum import Enum
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

# Enum for the `manage_workspace` tool's action parameter
class WorkspaceAction(str, Enum):
    enable = "enable"
    disable = "disable"
    delete = "delete"
    rename = "rename"

# --- Internal Helper Functions (Direct API Wrappers) ---

async def _list_workspaces(ctx: Context) -> List[Dict[str, Any]]:
    """Internal helper to fetch all workspaces."""
    return await make_quix_request(ctx, "GET", "workspaces")

async def _get_workspace(ctx: Context, workspace_id: str) -> Dict[str, Any]:
    """Internal helper to fetch details for a single workspace."""
    return await make_quix_request(ctx, "GET", f"workspaces/{workspace_id}")

async def _enable_workspace(ctx: Context, workspace_id: str):
    """Internal helper to enable a workspace."""
    return await make_quix_request(ctx, "POST", f"workspaces/{workspace_id}/enable")

async def _disable_workspace(ctx: Context, workspace_id: str):
    """Internal helper to disable a workspace."""
    return await make_quix_request(ctx, "POST", f"workspaces/{workspace_id}/disable")

async def _delete_workspace(ctx: Context, workspace_id: str):
    """Internal helper to delete a workspace."""
    return await make_quix_request(ctx, "DELETE", f"workspaces/{workspace_id}")

async def _rename_workspace(ctx: Context, workspace_id: str, new_name: str):
    """Internal helper to rename a workspace."""
    return await make_quix_request(ctx, "PATCH", f"workspaces/{workspace_id}/rename/{new_name}")

async def _create_pull_request(ctx: Context, target_workspace_id: str, source_branch: str, title: str, body: Optional[str]) -> str:
    """Internal helper to create a pull request."""
    payload = {
        "sourceBranch": source_branch,
        "title": title,
        "body": body
    }
    return await make_quix_request(ctx, "POST", f"workspaces/{target_workspace_id}/pullrequests", json=payload)

# --- New High-Level MCP Tools ---

async def find_workspaces(ctx: Context) -> str:
    """
    <usecase>
    Finds and lists all workspaces (environments) for your organization. Use this to get an overview and find the ID for a specific workspace.
    </usecase>
    <instructions>
    This tool lists all workspaces you have access to. The 'Workspace ID' is required for most other workspace management tools.
    </instructions>
    """
    try:
        workspaces = await _list_workspaces(ctx)
        if not workspaces:
            return "No workspaces found in this organization. You may need to create a project first."
        
        result = "Found the following workspaces (environments):\n\n"
        for ws in workspaces:
            result += f"- Name: {ws.get('name')} (Branch: {ws.get('branch')})\n"
            result += f"  ID: {ws.get('workspaceId')}\n"
            result += f"  Status: {ws.get('status')}\n\n"
        
        result += "To see more details about a specific workspace, use `get_workspace_details(workspace_id='...')`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error finding workspaces. This could be due to an authentication or network issue. Please verify your QUIX_TOKEN and QUIX_BASE_URL environment variables are correct. Original error: {str(e)}"

async def get_workspace_details(ctx: Context) -> str:
    """
    <usecase>
    Retrieves detailed information about the current workspace, including its status, associated Git branch, and broker type.
    </usecase>
    <instructions>
    This tool operates on the current workspace configured for the server. The workspace ID is automatically retrieved from the environment variables.
    </instructions>
    """
    try:
        workspace_id = os.environ.get("QUIX_WORKSPACE")
        if not workspace_id:
            return "Error: The current QUIX_WORKSPACE environment variable is not set. Unable to identify the current workspace."
            
        workspace = await _get_workspace(ctx, workspace_id)
        if not workspace:
            return f"Could not retrieve details for workspace ID '{workspace_id}'."

        result = f"Details for Workspace '{workspace.get('name')}':\n\n"
        result += f"ID: {workspace.get('workspaceId')}\n"
        result += f"Environment Name: {workspace.get('environmentName')}\n"
        result += f"Git Branch: {workspace.get('branch')}\n"
        result += f"Branch Protected: {workspace.get('branchProtected')}\n"
        result += f"Status: {workspace.get('status')}\n"
        result += f"Broker Type: {workspace.get('brokerType')}\n"
        
        broker_details = workspace.get('broker')
        if broker_details:
            result += f"Broker Address: {broker_details.get('address')}\n"
        
        result += "\nNext steps you might consider:"
        result += "\n- List applications with `find_applications()`"
        result += "\n- List deployments with `find_deployments()`"
        result += "\n- List topics with `find_topics()`"
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        workspace_id = os.environ.get("QUIX_WORKSPACE", "unknown")
        return f"Error getting details for workspace '{workspace_id}'. The ID might be incorrect or you may lack permissions. You can list all accessible workspaces with `find_workspaces()` to verify the correct ID. Original error: {str(e)}"

async def manage_workspace(
    ctx: Context,
    action: WorkspaceAction,
    workspace_id: str,
    new_name: Optional[str] = None
) -> str:
    """
    <usecase>
    Manages a workspace's lifecycle. Use this to enable, disable, rename, or delete a workspace.
    </usecase>
    <instructions>
    - 'action' specifies the operation: 'enable', 'disable', 'rename', or 'delete'.
    - 'workspace_id' is required for all actions.
    - For 'rename', the 'new_name' argument is required.
    - Always confirm with the user before performing 'delete' or 'disable' actions as they can be disruptive.
    </instructions>
    """
    try:
        if action == WorkspaceAction.enable:
            await _enable_workspace(ctx, workspace_id)
            return f"Workspace '{workspace_id}' has been enabled."
        
        if action == WorkspaceAction.disable:
            await _disable_workspace(ctx, workspace_id)
            return f"Workspace '{workspace_id}' has been disabled."
            
        if action == WorkspaceAction.rename:
            if not new_name:
                return "Error: 'new_name' is required for the rename action."
            await _rename_workspace(ctx, workspace_id, new_name)
            return f"Workspace '{workspace_id}' has been renamed to '{new_name}'."
            
        if action == WorkspaceAction.delete:
            await _delete_workspace(ctx, workspace_id)
            return f"Workspace '{workspace_id}' has been deleted successfully."
            
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error performing '{action.value}' on workspace '{workspace_id}'. Please ensure the workspace ID is correct and that you have the necessary permissions for this action. You can list available workspaces with `find_workspaces()` to verify the ID. Original error: {str(e)}"

async def promote_environment(
    ctx: Context, 
    source_branch: str, 
    target_branch: str, 
    title: str, 
    body: Optional[str] = None
) -> str:
    """
    <usecase>
    Promotes changes from one environment (branch) to another by creating a pull request. This is the standard and recommended way to move tested changes from a development environment to production.
    </usecase>
    <instructions>
    - 'source_branch' is the branch containing the changes you want to merge (e.g., 'develop').
    - 'target_branch' is the destination branch for the changes (e.g., 'main').
    - 'title' is a short, descriptive summary for the pull request.
    - 'body' is an optional longer description of the changes.
    </instructions>
    """
    try:
        await ctx.info(f"Finding target workspace for branch '{target_branch}'...")
        all_workspaces = await _list_workspaces(ctx)
        target_workspace = next((ws for ws in all_workspaces if ws.get('branch') == target_branch), None)

        if not target_workspace:
            return f"Error: Could not find a workspace associated with the target branch '{target_branch}'. Please ensure a workspace for this branch exists."

        target_workspace_id = target_workspace['workspaceId']
        await ctx.info(f"Target workspace found: '{target_workspace['name']}' ({target_workspace_id}). Creating pull request...")

        pr_url = await _create_pull_request(ctx, target_workspace_id, source_branch, title, body)
        
        if not pr_url:
            raise QuixApiError("Pull request creation did not return a URL.")
            
        return f"Pull request created successfully to promote '{source_branch}' to '{target_branch}'.\nPlease review and merge it here: {pr_url}"
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error promoting environment from '{source_branch}' to '{target_branch}'. Please ensure both branches exist and that you have permissions to create pull requests. You can list all workspaces and their branches with `find_workspaces()` to verify the branch names. Original error: {str(e)}"