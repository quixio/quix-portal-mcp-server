"""Quix Workspaces MCP tools."""

from typing import Any, Optional, Dict, List
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

async def list_workspaces(ctx: Context) -> str:
    """List all workspaces for the organization.
    
    Returns:
        A formatted string listing all workspaces with their details
    """
    try:
        workspaces = await make_quix_request(
            ctx,
            "GET",
            "workspaces"
        )
        
        if not workspaces:
            return "No workspaces found."
        
        result = "Workspaces:\n\n"
        for workspace in workspaces:
            result += f"ID: {workspace.get('workspaceId')}\n"
            result += f"Name: {workspace.get('name')}\n"
            result += f"Status: {workspace.get('status')}\n"
            result += f"Broker Type: {workspace.get('brokerType')}\n"
            result += f"Environment: {workspace.get('environmentName', 'N/A')}\n"
            result += f"Branch: {workspace.get('branch', 'N/A')}\n"
            result += f"Created: {workspace.get('createdAt', 'N/A')}\n"
            
            if workspace.get('lastError'):
                result += f"Last Error: {workspace.get('lastError')}\n"
            
            result += "\n"
        
        return result
        
    except QuixApiError as e:
        return f"Error retrieving workspaces: {str(e)}"

async def get_workspace(ctx: Context, workspace_id: str) -> str:
    """Get details of a specific workspace.
    
    Args:
        workspace_id: The ID of the workspace to retrieve
        
    Returns:
        A formatted string with workspace details
    """
    try:
        workspace = await make_quix_request(
            ctx,
            "GET", 
            f"workspaces/{workspace_id}"
        )
        
        if not workspace:
            return f"Workspace {workspace_id} not found."
        
        result = f"Workspace Details:\n\n"
        result += f"ID: {workspace.get('workspaceId')}\n"
        result += f"Name: {workspace.get('name')}\n"
        result += f"Status: {workspace.get('status')}\n"
        result += f"Broker Type: {workspace.get('brokerType')}\n"
        result += f"Environment: {workspace.get('environmentName', 'N/A')}\n"
        result += f"Branch: {workspace.get('branch', 'N/A')}\n"
        result += f"Branch Protected: {workspace.get('branchProtected', False)}\n"
        result += f"Created: {workspace.get('createdAt', 'N/A')}\n"
        result += f"Version: {workspace.get('version', 'N/A')}\n"
        
        if workspace.get('lastError'):
            result += f"Last Error: {workspace.get('lastError')}\n"
        
        # Broker details
        broker = workspace.get('broker', {})
        if broker:
            result += f"\nBroker Details:\n"
            result += f"Address: {broker.get('address', 'N/A')}\n"
            result += f"Security Mode: {broker.get('securityMode', 'N/A')}\n"
            result += f"SASL Mechanism: {broker.get('saslMechanism', 'N/A')}\n"
            result += f"Username: {broker.get('username', 'N/A')}\n"
            result += f"Has Certificate: {broker.get('hasCertificate', False)}\n"
        
        return result
        
    except QuixApiError as e:
        return f"Error retrieving workspace {workspace_id}: {str(e)}"

async def get_workspace_variables(ctx: Context, workspace_id: str) -> str:
    """Get workspace variables.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        A formatted string with workspace variables
    """
    try:
        variables = await make_quix_request(
            ctx,
            "GET",
            f"workspaces/{workspace_id}/variables"
        )
        
        if not variables:
            return f"No variables found for workspace {workspace_id}."
        
        result = f"Workspace Variables:\n\n"
        for key, value in variables.items():
            result += f"{key}: {value}\n"
        
        return result
        
    except QuixApiError as e:
        return f"Error retrieving variables for workspace {workspace_id}: {str(e)}"

async def set_workspace_variables(ctx: Context, workspace_id: str, variables: Dict[str, str]) -> str:
    """Set workspace variables.
    
    Args:
        workspace_id: The workspace ID
        variables: Dictionary of variable key-value pairs to set
        
    Returns:
        Success message or error
    """
    try:
        await make_quix_request(
            ctx,
            "PUT",
            f"workspaces/{workspace_id}/variables",
            json=variables
        )
        
        return f"Successfully updated variables for workspace {workspace_id}."
        
    except QuixApiError as e:
        return f"Error setting variables for workspace {workspace_id}: {str(e)}"

async def get_workspace_yaml(ctx: Context, workspace_id: str, reference: Optional[str] = None) -> str:
    """Get the workspace YAML descriptor.
    
    Args:
        workspace_id: The workspace ID
        reference: Optional git reference (defaults to HEAD)
        
    Returns:
        The YAML content as a string
    """
    try:
        params = {}
        if reference:
            params["reference"] = reference
            
        yaml_content = await make_quix_request(
            ctx,
            "GET",
            f"workspaces/{workspace_id}/yaml",
            params=params
        )
        
        if not yaml_content:
            return f"No YAML found for workspace {workspace_id}."
        
        return f"Workspace YAML:\n\n{yaml_content}"
        
    except QuixApiError as e:
        return f"Error retrieving YAML for workspace {workspace_id}: {str(e)}"

async def update_workspace_yaml(ctx: Context, workspace_id: str, yaml_content: str, commit_message: Optional[str] = None) -> str:
    """Update the workspace YAML descriptor.
    
    Args:
        workspace_id: The workspace ID
        yaml_content: The new YAML content
        commit_message: Optional commit message
        
    Returns:
        Success message or error
    """
    try:
        params = {}
        if commit_message:
            params["commitMessage"] = commit_message
            
        await make_quix_request(
            ctx,
            "PUT",
            f"workspaces/{workspace_id}/yaml",
            json=yaml_content,
            params=params,
            headers={"Content-Type": "text/plain"}
        )
        
        return f"Successfully updated YAML for workspace {workspace_id}."
        
    except QuixApiError as e:
        return f"Error updating YAML for workspace {workspace_id}: {str(e)}"

async def get_workspace_sync_status(ctx: Context, workspace_id: str) -> str:
    """Get workspace sync status.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        A formatted string with sync status details
    """
    try:
        sync_status = await make_quix_request(
            ctx,
            "GET",
            f"workspaces/{workspace_id}/sync/status"
        )
        
        if not sync_status:
            return f"No sync status found for workspace {workspace_id}."
        
        result = f"Workspace Sync Status:\n\n"
        result += f"Status: {sync_status.get('status', 'Unknown')}\n"
        result += f"YAML Out of Sync: {sync_status.get('yamlOutOfSync', False)}\n"
        result += f"Variables Out of Sync: {sync_status.get('variablesOutOfSync', False)}\n"
        result += f"Deployments Out of Sync: {sync_status.get('deploymentsVersionsOutOfSync', False)}\n"
        result += f"Last Repo Commit: {sync_status.get('lastRepoCommitReference', 'N/A')}\n"
        result += f"Synced Commit: {sync_status.get('syncedCommitReference', 'N/A')}\n"
        result += f"Commits Behind: {sync_status.get('commitsBehind', 0)}\n"
        
        error = sync_status.get('error')
        if error:
            result += f"Error: {error.get('error', 'N/A')}\n"
            result += f"Error Commit: {error.get('commitReference', 'N/A')}\n"
        
        return result
        
    except QuixApiError as e:
        return f"Error retrieving sync status for workspace {workspace_id}: {str(e)}"

async def sync_workspace(ctx: Context, workspace_id: str, reference: Optional[str] = None, dry_run: bool = False, create_deployments_stopped: bool = False) -> str:
    """Sync workspace with repository.
    
    Args:
        workspace_id: The workspace ID
        reference: Optional git reference (defaults to HEAD)
        dry_run: If True, performs a dry run sync (default: False)
        create_deployments_stopped: If True, creates deployments as stopped (default: False)
        
    Returns:
        A formatted string with sync results
    """
    try:
        params = {}
        if reference:
            params["reference"] = reference
        if create_deployments_stopped:
            params["createDeploymentsAsStopped"] = "true"
            
        method = "GET" if dry_run else "POST"
        
        sync_result = await make_quix_request(
            ctx,
            method,
            f"workspaces/{workspace_id}/sync",
            params=params
        )
        
        if not sync_result:
            return f"No sync result for workspace {workspace_id}."
        
        result = f"Workspace Sync {'Preview' if dry_run else 'Result'}:\n\n"
        
        # Applications changes
        app_results = sync_result.get('applicationsSyncResults', [])
        if app_results:
            result += "Application Changes:\n"
            for app_result in app_results:
                change = app_result.get('changeDetails', {})
                action = change.get('action', 'Unknown')
                target_key = change.get('targetKey', 'Unknown')
                operation_result = app_result.get('result', 'Unknown')
                result += f"  - {action} {target_key}: {operation_result}\n"
                if app_result.get('error'):
                    result += f"    Error: {app_result.get('error')}\n"
            result += "\n"
        
        # Deployment changes
        deploy_results = sync_result.get('deploymentsSyncResults', [])
        if deploy_results:
            result += "Deployment Changes:\n"
            for deploy_result in deploy_results:
                change = deploy_result.get('changeDetails', {})
                action = change.get('action', 'Unknown')
                target_key = change.get('targetKey', 'Unknown')
                operation_result = deploy_result.get('result', 'Unknown')
                result += f"  - {action} {target_key}: {operation_result}\n"
                if deploy_result.get('error'):
                    result += f"    Error: {deploy_result.get('error')}\n"
            result += "\n"
        
        # Topic changes
        topic_results = sync_result.get('topicsSyncResults', [])
        if topic_results:
            result += "Topic Changes:\n"
            for topic_result in topic_results:
                change = topic_result.get('changeDetails', {})
                action = change.get('action', 'Unknown')
                target_key = change.get('targetKey', 'Unknown')
                operation_result = topic_result.get('result', 'Unknown')
                result += f"  - {action} {target_key}: {operation_result}\n"
                if topic_result.get('error'):
                    result += f"    Error: {topic_result.get('error')}\n"
            result += "\n"
        
        if not app_results and not deploy_results and not topic_results:
            result += "No changes detected.\n"
        
        return result
        
    except QuixApiError as e:
        return f"Error syncing workspace {workspace_id}: {str(e)}"

async def create_workspace_branch(ctx: Context, workspace_id: str, branch_name: str) -> str:
    """Create a new branch in the workspace.
    
    Args:
        workspace_id: The workspace ID
        branch_name: Name of the branch to create
        
    Returns:
        Success message or error
    """
    try:
        await make_quix_request(
            ctx,
            "POST",
            f"workspaces/{workspace_id}/branch/{branch_name}"
        )
        
        return f"Successfully created branch '{branch_name}' in workspace {workspace_id}."
        
    except QuixApiError as e:
        return f"Error creating branch '{branch_name}' in workspace {workspace_id}: {str(e)}"

async def switch_workspace_branch(ctx: Context, workspace_id: str, branch_name: str, protected: bool = False) -> str:
    """Switch to a different branch in the workspace.
    
    Args:
        workspace_id: The workspace ID
        branch_name: Name of the branch to switch to
        protected: Whether the branch is protected (default: False)
        
    Returns:
        Success message or error with commit details
    """
    try:
        params = {}
        if protected:
            params["branchProtected"] = "true"
            
        commit = await make_quix_request(
            ctx,
            "PATCH",
            f"workspaces/{workspace_id}/branch/{branch_name}",
            params=params
        )
        
        result = f"Successfully switched to branch '{branch_name}' in workspace {workspace_id}."
        
        if commit:
            result += f"\nCurrent commit: {commit.get('reference', 'N/A')}"
            result += f"\nCommit message: {commit.get('message', 'N/A')}"
            result += f"\nAuthor: {commit.get('authorName', 'N/A')}"
        
        return result
        
    except QuixApiError as e:
        return f"Error switching to branch '{branch_name}' in workspace {workspace_id}: {str(e)}"

async def create_workspace_tag(ctx: Context, workspace_id: str, tag_name: str, reference: Optional[str] = None) -> str:
    """Create a new tag in the workspace.
    
    Args:
        workspace_id: The workspace ID
        tag_name: Name of the tag to create
        reference: Optional git reference to tag (defaults to HEAD)
        
    Returns:
        Success message or error
    """
    try:
        tag_request = {
            "tagName": tag_name
        }
        if reference:
            tag_request["reference"] = reference
            
        await make_quix_request(
            ctx,
            "POST",
            f"workspaces/{workspace_id}/tags",
            json=tag_request
        )
        
        return f"Successfully created tag '{tag_name}' in workspace {workspace_id}."
        
    except QuixApiError as e:
        return f"Error creating tag '{tag_name}' in workspace {workspace_id}: {str(e)}"

async def delete_workspace_tag(ctx: Context, workspace_id: str, tag_name: str) -> str:
    """Delete a tag from the workspace.
    
    Args:
        workspace_id: The workspace ID
        tag_name: Name of the tag to delete
        
    Returns:
        Success message or error
    """
    try:
        await make_quix_request(
            ctx,
            "DELETE",
            f"workspaces/{workspace_id}/tags/{tag_name}"
        )
        
        return f"Successfully deleted tag '{tag_name}' from workspace {workspace_id}."
        
    except QuixApiError as e:
        return f"Error deleting tag '{tag_name}' from workspace {workspace_id}: {str(e)}"

async def get_workspace_commits(ctx: Context, workspace_id: str, reference: Optional[str] = None, limit: Optional[int] = None) -> str:
    """Get commits for the workspace.
    
    Args:
        workspace_id: The workspace ID
        reference: Optional git reference (defaults to HEAD)
        limit: Optional limit on number of commits to retrieve
        
    Returns:
        A formatted string with commit history
    """
    try:
        params = {}
        if reference:
            params["reference"] = reference
        if limit:
            params["limit"] = str(limit)
            
        commits = await make_quix_request(
            ctx,
            "GET",
            f"workspaces/{workspace_id}/yaml/commits",
            params=params
        )
        
        if not commits:
            return f"No commits found for workspace {workspace_id}."
        
        result = f"Workspace Commits:\n\n"
        for commit in commits:
            result += f"Reference: {commit.get('reference', 'N/A')}\n"
            result += f"Message: {commit.get('message', 'N/A')}\n"
            result += f"Author: {commit.get('authorName', 'N/A')} <{commit.get('authorEmail', 'N/A')}>\n"
            result += f"Created: {commit.get('createdAt', 'N/A')}\n"
            result += "\n"
        
        return result
        
    except QuixApiError as e:
        return f"Error retrieving commits for workspace {workspace_id}: {str(e)}"

async def enable_workspace(ctx: Context, workspace_id: str) -> str:
    """Enable a workspace.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        Success message or error
    """
    try:
        await make_quix_request(
            ctx,
            "POST",
            f"workspaces/{workspace_id}/enable"
        )
        
        return f"Successfully enabled workspace {workspace_id}."
        
    except QuixApiError as e:
        return f"Error enabling workspace {workspace_id}: {str(e)}"

async def disable_workspace(ctx: Context, workspace_id: str) -> str:
    """Disable a workspace.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        Success message or error
    """
    try:
        await make_quix_request(
            ctx,
            "POST",
            f"workspaces/{workspace_id}/disable"
        )
        
        return f"Successfully disabled workspace {workspace_id}."
        
    except QuixApiError as e:
        return f"Error disabling workspace {workspace_id}: {str(e)}"

async def delete_workspace(ctx: Context, workspace_id: str) -> str:
    """Delete a workspace.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        Success message or error
    """
    try:
        await make_quix_request(
            ctx,
            "DELETE",
            f"workspaces/{workspace_id}"
        )
        
        return f"Successfully deleted workspace {workspace_id}."
        
    except QuixApiError as e:
        return f"Error deleting workspace {workspace_id}: {str(e)}"

async def rename_workspace(ctx: Context, workspace_id: str, new_name: str) -> str:
    """Rename a workspace.
    
    Args:
        workspace_id: The workspace ID
        new_name: The new name for the workspace
        
    Returns:
        Success message or error
    """
    try:
        await make_quix_request(
            ctx,
            "PATCH",
            f"workspaces/{workspace_id}/rename/{new_name}"
        )
        
        return f"Successfully renamed workspace {workspace_id} to '{new_name}'."
        
    except QuixApiError as e:
        return f"Error renaming workspace {workspace_id}: {str(e)}"