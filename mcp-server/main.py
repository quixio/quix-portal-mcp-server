"""Unified Quix Portal MCP Server."""

import os
import asyncio
import logging
from pathlib import Path
from typing import Any, Optional, Dict, List

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
import dotenv

# Import all tool modules
from tools import applications
from tools import deployments  
from tools import library
from tools import topics
from tools import workspaces

# Initialize FastMCP server
mcp = FastMCP("quix_portal")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add predefined var for workspace
# os.environ['QUIX_WORKSPACE'] = os.environ.get('Quix__Workspace__Id')

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
    return await applications.list_applications(ctx, search, include_updated_at)

@mcp.tool()
async def get_application(ctx: Context, application_id: str, reference: Optional[str] = None, include_updated_at: bool = False) -> str:
    """Get details of a specific application.
    
    Args:
        application_id: The ID of the application to retrieve
        reference: Optional commit reference
        include_updated_at: True to include the updated at timestamp (default: False)
    """
    return await applications.get_application(ctx, application_id, reference, include_updated_at)

@mcp.tool()
async def create_application(ctx: Context, application_name: str, path: Optional[str] = None, language: Optional[str] = None) -> str:
    """Create a new application in the workspace.
    
    Args:
        application_name: Name of the application
        path: Optional directory path where the application should be created
        language: Optional programming language for the application
    """
    return await applications.create_application(ctx, application_name, path, language)

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
    return await applications.update_application(
        ctx, application_id, application_name, application_path, language,
        dockerfile, run_entry_point, default_file, variables, included_folders
    )

@mcp.tool()
async def delete_application(ctx: Context, application_id: str, delete_files: bool = True) -> str:
    """Delete an application.
    
    Args:
        application_id: The ID of the application to delete
        delete_files: Whether to delete the application files (default: True)
    """
    return await applications.delete_application(ctx, application_id, delete_files)

@mcp.tool()
async def list_application_files(ctx: Context, application_id: str, reference: Optional[str] = None) -> str:
    """List files in an application.
    
    Args:
        application_id: The ID of the application
        reference: Optional commit reference
    """
    return await applications.list_application_files(ctx, application_id, reference)

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
    return await applications.duplicate_application(ctx, application_id, new_name, new_path)

@mcp.tool()
async def set_application_topics(
    ctx: Context,
    application_id: str,
    input_topic: Optional[str] = None,
    output_topic: Optional[str] = None
) -> str:
    """Set input and/or output topics for an application.
    This is a simplified helper function specifically for setting topic connections.
    
    Args:
        application_id: The ID of the application to update
        input_topic: Name of the input topic (for transformation/sink apps)
        output_topic: Name of the output topic (for source/transformation apps)
    """
    return await applications.set_application_topics(ctx, application_id, input_topic, output_topic)

# =========================================
# Deployment Tools
# =========================================

@mcp.tool()
async def get_deployments(ctx: Context, application_id: Optional[str] = None) -> str:
    """Get all deployments in the workspace, optionally filtered by application ID.
    
    Args:
        application_id: Optional application ID to filter deployments by
    """
    return await deployments.get_deployments(ctx, application_id)

@mcp.tool()
async def get_deployment(ctx: Context, deployment_id: str) -> str:
    """Get details of a specific deployment.
    
    Args:
        deployment_id: The ID of the deployment to retrieve
    """
    return await deployments.get_deployment(ctx, deployment_id)

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
    return await deployments.create_deployment(
        ctx, name, application_id, replicas, cpu_millicores, memory_in_mb, deployment_type,
        git_reference, git_reference_type, auto_start, use_latest, image_uri, public_access,
        url_prefix, state_enabled, state_size, variables, ports, service_name
    )

@mcp.tool()
async def start_deployment(ctx: Context, deployment_id: str, bypass_descriptor: bool = False) -> str:
    """Start a deployment.
    
    Args:
        deployment_id: The ID of the deployment to start
        bypass_descriptor: Whether to bypass descriptor checks (default: False)
    """
    return await deployments.start_deployment(ctx, deployment_id, bypass_descriptor)

@mcp.tool()
async def stop_deployment(ctx: Context, deployment_id: str, bypass_descriptor: bool = False) -> str:
    """Stop a deployment.
    
    Args:
        deployment_id: The ID of the deployment to stop
        bypass_descriptor: Whether to bypass descriptor checks (default: False)
    """
    return await deployments.stop_deployment(ctx, deployment_id, bypass_descriptor)

@mcp.tool()
async def delete_deployment(ctx: Context, deployment_id: str) -> str:
    """Delete a deployment.
    
    Args:
        deployment_id: The ID of the deployment to delete
    """
    return await deployments.delete_deployment(ctx, deployment_id)

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
    return await library.query_library(ctx, languages, tags, page_index, page_length, connectors, auxiliary_services)

@mcp.tool()
async def get_library_item_details(ctx: Context, item_id: str) -> str:
    """Get detailed information about a specific library item.
    
    Args:
        item_id: The ID of the library item to retrieve details for
    """
    return await library.get_library_item_details(ctx, item_id)

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
    return await library.create_application_from_library(
        ctx, library_item_id, application_name, path, placeholders, environment_variables
    )

# =========================================
# Topic Tools
# =========================================

@mcp.tool()
async def get_topics(ctx: Context) -> str:
    """List all topics in your workspace.
    """
    return await topics.get_topics(ctx)

@mcp.tool()
async def get_topic(ctx: Context, topic_name: str) -> str:
    """Get details of a specific topic.
    
    Args:
        topic_name: The name of the topic to retrieve
    """
    return await topics.get_topic(ctx, topic_name)

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
    return await topics.create_topic(
        ctx, name, partitions, replication_factor, retention_in_minutes, retention_in_bytes,
        cleanup_policy, data_tier_name, external_source_name, external_destination_name,
        unmanaged, linked_topic_workspace_id, linked_topic_name
    )

@mcp.tool()
async def delete_topic(ctx: Context, topic_name: str) -> str:
    """Delete a topic from your workspace.
    
    Args:
        topic_name: The name of the topic to delete
    """
    return await topics.delete_topic(ctx, topic_name)

# =========================================
# Workspace Tools
# =========================================

@mcp.tool()
async def list_workspaces(ctx: Context) -> str:
    """List all workspaces for the organization."""
    return await workspaces.list_workspaces(ctx)

@mcp.tool()
async def get_workspace(ctx: Context, workspace_id: str) -> str:
    """Get details of a specific workspace.
    
    Args:
        workspace_id: The ID of the workspace to retrieve
    """
    return await workspaces.get_workspace(ctx, workspace_id)

@mcp.tool()
async def get_workspace_variables(ctx: Context, workspace_id: str) -> str:
    """Get workspace variables.
    
    Args:
        workspace_id: The workspace ID
    """
    return await workspaces.get_workspace_variables(ctx, workspace_id)

@mcp.tool()
async def set_workspace_variables(ctx: Context, workspace_id: str, variables: Dict[str, str]) -> str:
    """Set workspace variables.
    
    Args:
        workspace_id: The workspace ID
        variables: Dictionary of variable key-value pairs to set
    """
    return await workspaces.set_workspace_variables(ctx, workspace_id, variables)

@mcp.tool()
async def get_workspace_yaml(ctx: Context, workspace_id: str, reference: Optional[str] = None) -> str:
    """Get the workspace YAML descriptor.
    
    Args:
        workspace_id: The workspace ID
        reference: Optional git reference (defaults to HEAD)
    """
    return await workspaces.get_workspace_yaml(ctx, workspace_id, reference)

@mcp.tool()
async def update_workspace_yaml(ctx: Context, workspace_id: str, yaml_content: str, commit_message: Optional[str] = None) -> str:
    """Update the workspace YAML descriptor.
    
    Args:
        workspace_id: The workspace ID
        yaml_content: The new YAML content
        commit_message: Optional commit message
    """
    return await workspaces.update_workspace_yaml(ctx, workspace_id, yaml_content, commit_message)

@mcp.tool()
async def get_workspace_sync_status(ctx: Context, workspace_id: str) -> str:
    """Get workspace sync status.
    
    Args:
        workspace_id: The workspace ID
    """
    return await workspaces.get_workspace_sync_status(ctx, workspace_id)

@mcp.tool()
async def sync_workspace(ctx: Context, workspace_id: str, reference: Optional[str] = None, dry_run: bool = False, create_deployments_stopped: bool = False) -> str:
    """Sync workspace with repository.
    
    Args:
        workspace_id: The workspace ID
        reference: Optional git reference (defaults to HEAD)
        dry_run: If True, performs a dry run sync (default: False)
        create_deployments_stopped: If True, creates deployments as stopped (default: False)
    """
    return await workspaces.sync_workspace(ctx, workspace_id, reference, dry_run, create_deployments_stopped)

@mcp.tool()
async def create_workspace_branch(ctx: Context, workspace_id: str, branch_name: str) -> str:
    """Create a new branch in the workspace.
    
    Args:
        workspace_id: The workspace ID
        branch_name: Name of the branch to create
    """
    return await workspaces.create_workspace_branch(ctx, workspace_id, branch_name)

@mcp.tool()
async def switch_workspace_branch(ctx: Context, workspace_id: str, branch_name: str, protected: bool = False) -> str:
    """Switch to a different branch in the workspace.
    
    Args:
        workspace_id: The workspace ID
        branch_name: Name of the branch to switch to
        protected: Whether the branch is protected (default: False)
    """
    return await workspaces.switch_workspace_branch(ctx, workspace_id, branch_name, protected)

@mcp.tool()
async def create_workspace_tag(ctx: Context, workspace_id: str, tag_name: str, reference: Optional[str] = None) -> str:
    """Create a new tag in the workspace.
    
    Args:
        workspace_id: The workspace ID
        tag_name: Name of the tag to create
        reference: Optional git reference to tag (defaults to HEAD)
    """
    return await workspaces.create_workspace_tag(ctx, workspace_id, tag_name, reference)

@mcp.tool()
async def delete_workspace_tag(ctx: Context, workspace_id: str, tag_name: str) -> str:
    """Delete a tag from the workspace.
    
    Args:
        workspace_id: The workspace ID
        tag_name: Name of the tag to delete
    """
    return await workspaces.delete_workspace_tag(ctx, workspace_id, tag_name)

@mcp.tool()
async def get_workspace_commits(ctx: Context, workspace_id: str, reference: Optional[str] = None, limit: Optional[int] = None) -> str:
    """Get commits for the workspace.
    
    Args:
        workspace_id: The workspace ID
        reference: Optional git reference (defaults to HEAD)
        limit: Optional limit on number of commits to retrieve
    """
    return await workspaces.get_workspace_commits(ctx, workspace_id, reference, limit)

@mcp.tool()
async def enable_workspace(ctx: Context, workspace_id: str) -> str:
    """Enable a workspace.
    
    Args:
        workspace_id: The workspace ID
    """
    return await workspaces.enable_workspace(ctx, workspace_id)

@mcp.tool()
async def disable_workspace(ctx: Context, workspace_id: str) -> str:
    """Disable a workspace.
    
    Args:
        workspace_id: The workspace ID
    """
    return await workspaces.disable_workspace(ctx, workspace_id)

@mcp.tool()
async def delete_workspace(ctx: Context, workspace_id: str) -> str:
    """Delete a workspace.
    
    Args:
        workspace_id: The workspace ID
    """
    return await workspaces.delete_workspace(ctx, workspace_id)

@mcp.tool()
async def rename_workspace(ctx: Context, workspace_id: str, new_name: str) -> str:
    """Rename a workspace.
    
    Args:
        workspace_id: The workspace ID
        new_name: The new name for the workspace
    """
    return await workspaces.rename_workspace(ctx, workspace_id, new_name)

@mcp.tool()
async def create_workspace(ctx: Context, repository_id: str, environment_name: str, branch: str, 
                          workspace_class_id: Optional[str] = None, storage_class_id: Optional[str] = None,
                          broker_type: str = "SharedKafka", sync_topics: bool = True, 
                          branch_protected: bool = False, cluster_id: Optional[str] = None,
                          node_group_id: Optional[str] = None, broker_id: Optional[str] = None) -> str:
    """Create a new workspace V2.
    
    Args:
        repository_id: Repository ID for the workspace
        environment_name: Name of the environment
        branch: Git branch name for the workspace
        workspace_class_id: Optional workspace class ID
        storage_class_id: Optional storage class ID
        broker_type: Broker type (default: SharedKafka)
        sync_topics: Whether to sync existing topics in the broker (default: True)
        branch_protected: Whether the branch is protected (default: False)
        cluster_id: Optional cluster ID for deployments and IDEs
        node_group_id: Optional node group ID within the cluster
        broker_id: Optional broker configuration ID
    """
    return await workspaces.create_workspace(ctx, repository_id, environment_name, branch, 
                                            workspace_class_id, storage_class_id, broker_type, 
                                            sync_topics, branch_protected, cluster_id, 
                                            node_group_id, broker_id)

@mcp.tool()
async def get_workspace_commit(ctx: Context, workspace_id: str, reference: str) -> str:
    """Get the commit of a git reference.
    
    Args:
        workspace_id: The workspace ID
        reference: The git reference (commit hash, branch name, or tag)
    """
    return await workspaces.get_workspace_commit(ctx, workspace_id, reference)

@mcp.tool()
async def pull_workspace(ctx: Context, workspace_id: str) -> str:
    """Pull the latest changes from the remote repository.
    
    Args:
        workspace_id: The workspace ID
    """
    return await workspaces.pull_workspace(ctx, workspace_id)

@mcp.tool()
async def push_workspace(ctx: Context, workspace_id: str) -> str:
    """Push the latest changes to the remote repository.
    
    Args:
        workspace_id: The workspace ID
    """
    return await workspaces.push_workspace(ctx, workspace_id)

# =========================================
# Server Infrastructure
# =========================================

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
    
    parser = argparse.ArgumentParser(description='Run Quix Portal MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=80, help='Port to listen on')
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
    
    logger.info(f"Starting Quix Portal MCP server on {args.host}:{args.port}")
    logger.info(f"Using Quix Portal at {os.environ.get('QUIX_BASE_URL')}")
    logger.info(f"Using Quix Workspace {os.environ.get('QUIX_WORKSPACE')}")
    
    uvicorn.run(starlette_app, host=args.host, port=args.port)