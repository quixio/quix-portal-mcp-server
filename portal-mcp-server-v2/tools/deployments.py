"""Quix Deployments MCP tools."""

import os
from typing import Any, Optional, Dict, List
from enum import Enum
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

# Enum for manage_deployment action
class DeploymentAction(str, Enum):
    create = "create"
    update = "update"
    start = "start"
    stop = "stop"
    delete = "delete"

# --- Internal Helper Functions ---

async def _get_deployments(ctx: Context, workspace_id: str, application_id: Optional[str]) -> List[Dict[str, Any]]:
    params = {}
    if application_id:
        params["applicationId"] = application_id
    return await make_quix_request(ctx, "GET", "workspaces/{workspaceId}/deployments", workspace_id=workspace_id, params=params)

async def _get_deployment(ctx: Context, workspace_id: str, deployment_id: str) -> Dict[str, Any]:
    return await make_quix_request(ctx, "GET", f"deployments/{deployment_id}", workspace_id=workspace_id)

async def _create_deployment(ctx: Context, workspace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await make_quix_request(ctx, "POST", "deployments", workspace_id=workspace_id, json=payload)

async def _start_deployment(ctx: Context, workspace_id: str, deployment_id: str):
    return await make_quix_request(ctx, "PUT", f"deployments/{deployment_id}/start", workspace_id=workspace_id)

async def _stop_deployment(ctx: Context, workspace_id: str, deployment_id: str):
    return await make_quix_request(ctx, "PUT", f"deployments/{deployment_id}/stop", workspace_id=workspace_id)

async def _delete_deployment(ctx: Context, workspace_id: str, deployment_id: str):
    return await make_quix_request(ctx, "DELETE", f"deployments/{deployment_id}", workspace_id=workspace_id)

# --- New High-Level MCP Tools ---

async def find_deployments(ctx: Context, workspace_id: str, application_name: Optional[str] = None, status: Optional[str] = None) -> str:
    """
    <usecase>
    Finds and lists deployments in a specific workspace. Use this to get an overview of running services or to find a specific deployment_id.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    You can optionally filter by 'application_name' or 'status'.
    </instructions>
    """
    try:
        # Note: The API doesn't directly support filtering by app name or status.
        # This implementation fetches all and filters locally.
        # For a production server, this might need optimization or an API change.
        all_deployments = await _get_deployments(ctx, workspace_id, None)

        if not all_deployments:
            return "No deployments found in this workspace. You can create one with `manage_deployment(action='create', ...)`."

        filtered_deployments = all_deployments
        if application_name:
            filtered_deployments = [d for d in filtered_deployments if d.get('applicationName') == application_name]
        if status:
            filtered_deployments = [d for d in filtered_deployments if d.get('status') == status]

        if not filtered_deployments:
            return "No deployments found matching your criteria."

        result = "Found the following deployments:\n\n"
        for d in filtered_deployments:
            result += f"- Name: {d.get('name')}\n  ID: {d.get('deploymentId')}\n  Status: {d.get('status')}\n  App: {d.get('applicationName')}\n"
        
        result += f"\nTo get more details, use `get_deployment_details(workspace_id='{workspace_id}', deployment_id='...')`."
        result += f"\nTo manage a deployment, use `manage_deployment(workspace_id='{workspace_id}', deployment_id='...', action='...')`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error finding deployments in workspace '{workspace_id}'. Please check your workspace credentials and network connection. If no deployments exist, you can create one with `manage_deployment(workspace_id='{workspace_id}', action='create', application_id='...', name='...')`. Original error: {str(e)}"

async def get_deployment_details(ctx: Context, workspace_id: str, deployment_id: str) -> str:
    """
    <usecase>
    Retrieves detailed information about a specific deployment including its status, configuration, and resource usage.
    </usecase>
    <instructions>
    You must provide both a valid 'workspace_id' and 'deployment_id'. If you don't know these IDs, use 'find_workspaces()' and 'find_deployments()' first.
    </instructions>
    """
    try:
        deployment = await _get_deployment(ctx, workspace_id, deployment_id)
        if not deployment:
            return f"Deployment with ID '{deployment_id}' not found."

        result = f"Details for Deployment '{deployment.get('name')}':\n"
        result += f"ID: {deployment['deploymentId']}\n"
        result += f"Status: {deployment.get('status', 'N/A')}\n"
        if deployment.get('statusReason'):
            result += f"Status Reason: {deployment.get('statusReason')}\n"
        result += f"Application: {deployment.get('applicationName', 'N/A')} (ID: {deployment.get('applicationId')})\n"
        result += f"Resources: {deployment.get('cpuMillicores')}m CPU, {deployment.get('memoryInMb')}MB RAM, {deployment.get('replicas')} replica(s)\n"
        
        variables = deployment.get('variables')
        if variables:
            result += "\nVariables:\n"
            for name, var_info in variables.items():
                val = var_info.get('value', '[Not Set]')
                if var_info.get('inputType') == 'Secret':
                    val = '[SECRET]'
                result += f"  - {name}: {val}\n"
        
        result += f"\nTo see logs, use `get_deployment_logs(workspace_id='{workspace_id}', deployment_id='{deployment_id}')`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error getting details for deployment '{deployment_id}' in workspace '{workspace_id}'. The IDs might be incorrect or the deployment may not exist. Try using `find_deployments(workspace_id='{workspace_id}')` to get a list of valid deployment IDs. Original error: {str(e)}"

async def manage_deployment(
    ctx: Context,
    workspace_id: str,
    action: DeploymentAction,
    deployment_id: Optional[str] = None,
    application_id: Optional[str] = None,
    name: Optional[str] = None,
    replicas: int = 1,
    cpu_millicores: int = 1000,
    memory_in_mb: int = 1024
) -> str:
    """
    <usecase>
    Manages deployment lifecycle operations including creating, starting, stopping, and deleting deployments.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    </instructions>
    """
    try:
        if action == DeploymentAction.create:
            if not application_id or not name:
                return "Error: 'application_id' and 'name' are required to create a deployment."
            payload = {
                "workspaceId": workspace_id,
                "applicationId": application_id,
                "name": name,
                "replicas": replicas,
                "cpuMillicores": cpu_millicores,
                "memoryInMb": memory_in_mb,
            }
            deployment = await _create_deployment(ctx, workspace_id, payload)
            new_id = deployment.get('deploymentId')
            return f"Deployment '{name}' is being created with ID '{new_id}' in workspace '{workspace_id}'. Its status is '{deployment.get('status')}'. Check its progress with `get_deployment_details(workspace_id='{workspace_id}', deployment_id='{new_id}')`."

        if not deployment_id:
            return f"Error: 'deployment_id' is required for '{action.value}' action."

        if action == DeploymentAction.start:
            await _start_deployment(ctx, workspace_id, deployment_id)
            return f"Deployment '{deployment_id}' has been started. Use `get_deployment_details(workspace_id='{workspace_id}', deployment_id='{deployment_id}')` to check its status."
        
        if action == DeploymentAction.stop:
            await _stop_deployment(ctx, workspace_id, deployment_id)
            return f"Deployment '{deployment_id}' has been stopped. Use `get_deployment_details(workspace_id='{workspace_id}', deployment_id='{deployment_id}')` to check its status."

        if action == DeploymentAction.delete:
            await _delete_deployment(ctx, workspace_id, deployment_id)
            return f"Deployment '{deployment_id}' has been deleted successfully."
        
        if action == DeploymentAction.update:
             return "Update action is not yet fully implemented in this simplified tool. Please use the Portal UI for now."

    except QuixApiError as e:
        # --- Guided Error Handling ---
        if action == DeploymentAction.create:
            return f"Error creating deployment. Please ensure the application ID is correct and the name is unique. You can verify the application ID with `find_applications()`. The name might already exist in this workspace. Original error: {str(e)}"
        elif action in [DeploymentAction.start, DeploymentAction.stop, DeploymentAction.delete]:
            return f"Error performing '{action.value}' on deployment '{deployment_id}'. Please ensure the deployment ID is correct and the deployment is in a valid state for this action. You can verify the ID and status with `find_deployments()`. Original error: {str(e)}"
        else:
            return f"Error managing deployment: {str(e)}"

async def create_deployment_from_template(
    ctx: Context,
    workspace_id: str,
    library_item_id: str,
    deployment_name: Optional[str] = None,
    create_application: bool = True,
    environment_variables: Optional[Dict[str, str]] = None
) -> str:
    """
    <usecase>
    Creates a deployment directly from a library item using the POST /library/deployment endpoint. This can optionally create an application too.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    - 'library_item_id' can be found using the 'find_in_library' tool.
    - 'deployment_name' is optional - if not provided, it will auto-generate a name based on the library item.
    - 'create_application' defaults to True - set to False if you want to deploy without creating an application.
    - 'environment_variables' can be used to set any required credentials or configurations for the template.
    </instructions>
    """
    try:
        await ctx.info(f"Creating deployment from library item '{library_item_id}' in workspace '{workspace_id}'...")
        
        # Create deployment from library item using the correct API endpoint
        payload = {
            "workspaceId": workspace_id,
            "libraryItemId": library_item_id,
            "createApplication": create_application
        }
        
        if deployment_name:
            payload["deploymentName"] = deployment_name
        if environment_variables:
            payload["environmentVariables"] = environment_variables
        
        deployment = await make_quix_request(ctx, "POST", "library/deployment", workspace_id=workspace_id, json=payload)
        
        deployment_id = deployment.get('deploymentId')
        deployment_name_result = deployment.get('name')
        app_id = deployment.get('applicationId')
        app_name = deployment.get('applicationName')
        
        if not deployment_id:
            raise QuixApiError("Failed to get new deployment ID after creation.")
        
        await ctx.info(f"Deployment '{deployment_name_result}' created with ID '{deployment_id}'.")
        
        result = f"Deployment '{deployment_name_result}' created successfully with ID '{deployment_id}' from library item '{library_item_id}' in workspace '{workspace_id}'.\n"
        result += f"- Status: {deployment.get('status')}\n"
        result += f"- Deployment Type: {deployment.get('deploymentType', 'Service')}\n"
        result += f"- Resources: {deployment.get('cpuMillicores', 'N/A')}m CPU, {deployment.get('memoryInMb', 'N/A')}MB RAM, {deployment.get('replicas', 'N/A')} replica(s)\n"
        
        if create_application and app_id:
            result += f"- Application Created: '{app_name}' (ID: {app_id})\n"
        elif app_id:
            result += f"- Using Existing Application: '{app_name}' (ID: {app_id})\n"
        
        if deployment.get('publicAccess'):
            result += f"- Public Access: {deployment.get('urlPrefix', 'N/A')}\n"
        
        variables = deployment.get('variables', {})
        if variables:
            result += f"- Variables: {len(variables)} configured\n"
        
        result += f"\nYou can check its progress with `get_deployment_details(workspace_id='{workspace_id}', deployment_id='{deployment_id}')` or view logs with `get_deployment_logs(deployment_id='{deployment_id}')`."
        
        return result

    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error creating deployment from library item '{library_item_id}' in workspace '{workspace_id}'. Please ensure the library item ID is correct and the deployment name (if provided) is unique. You can find valid library item IDs with `find_in_library(workspace_id='{workspace_id}', ...)`. Original error: {str(e)}"

async def get_deployment_logs(ctx: Context, deployment_id: str, replica_id: Optional[str] = None, log_type: str = "current") -> str:
    try:
        params = {}
        if replica_id:
            params["replicaId"] = replica_id
            
        endpoint = f"deployments/{deployment_id}/logs/current"
        
        logs = await make_quix_request(ctx, "GET", endpoint, params=params)
        
        if not logs:
            return f"No {log_type} logs found for deployment with ID {deployment_id}."
            
        return f"Logs for deployment {deployment_id}:\n\n{logs}"
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error getting logs for deployment '{deployment_id}'. Please ensure the deployment ID is correct and the deployment exists. You can verify the ID with `find_deployments()`. If the deployment is very new, logs might not be available yet. Original error: {str(e)}"