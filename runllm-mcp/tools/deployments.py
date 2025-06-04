"""Quix Deployments MCP tools."""

import os
from typing import Any, Optional, Dict, List, Union
from enum import Enum
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

# Define enums to match the schemas in the Swagger definition
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