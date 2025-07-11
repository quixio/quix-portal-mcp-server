"""
Unified Quix Portal MCP Server.

This server provides a high-level, workflow-oriented interface to the Quix Portal API,
designed for efficient and intuitive use by AI models.
"""

import os
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
from tools import applications, deployments, library, sessions, topics, workspaces

# Initialize FastMCP server
mcp = FastMCP("quix_portal_assistant")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================
# Application Management Tools
# =========================================

@mcp.tool()
async def find_applications(ctx: Context, workspace_id: str, search: Optional[str] = None) -> str:
    """
    <usecase>
    Finds and lists applications within a specific workspace. Use this to get an overview of available applications or to find a specific application_id.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    You can optionally provide a 'search' term to filter the results by name or path.
    </instructions>
    """
    return await applications.find_applications(ctx, workspace_id, search)

@mcp.tool()
async def get_application_details(ctx: Context, workspace_id: str, application_id: str) -> str:
    """
    <usecase>
    Retrieves detailed information about a specific application, including its configuration, variables, and status.
    </usecase>
    <instructions>
    You must provide both a valid 'workspace_id' and 'application_id'. If you don't know these IDs, use 'find_workspaces()' and 'find_applications()' first.
    </instructions>
    """
    return await applications.get_application_details(ctx, workspace_id, application_id)

@mcp.tool()
async def manage_application(
    ctx: Context,
    workspace_id: str,
    action: applications.ApplicationAction,
    application_id: Optional[str] = None,
    name: Optional[str] = None,
    path: Optional[str] = None,
    language: Optional[str] = None,
    delete_files: bool = True
) -> str:
    """
    <usecase>
    Manages applications in the workspace. Use this tool to create, update, duplicate, or delete applications.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    - To 'create', 'name' is required. 'path' and 'language' are optional.
    - To 'update', 'application_id' is required. Provide 'name', 'path', or 'language' to update them.
    - To 'duplicate', 'application_id' (the source) and 'name' (for the new app) are required.
    - To 'delete', 'application_id' is required. Confirm with the user as this is a destructive action.
    </instructions>
    """
    return await applications.manage_application(
        ctx, workspace_id, action, application_id, name, path, language, delete_files
    )

@mcp.tool()
async def set_application_topics(
    ctx: Context,
    workspace_id: str,
    application_id: str,
    input_topic: Optional[str] = None,
    output_topic: Optional[str] = None
) -> str:
    """
    <usecase>
    Configures the input and/or output topics for a given application. This is a crucial step to connect applications into a pipeline.
    </usecase>
    <instructions>
    You must provide valid 'workspace_id' and 'application_id'. If you don't know these IDs, use 'find_workspaces()' and 'find_applications()' first.
    - Provide at least one of 'input_topic' or 'output_topic'.
    - The topics must exist in the workspace. You can create them with 'manage_topic'.
    </instructions>
    """
    return await applications.set_application_topics(ctx, workspace_id, application_id, input_topic, output_topic)

@mcp.tool()
async def update_application_variables(
    ctx: Context, 
    workspace_id: str,
    application_id: str, 
    variables: List[Dict[str, Any]],
    append: bool = True
) -> str:
    """
    <usecase>
    Updates the environment variables for an application. This is crucial for configuring database connections, API keys, and other runtime settings.
    </usecase>
    <instructions>
    You must provide valid 'workspace_id' and 'application_id'. If you don't know these IDs, use 'find_workspaces()' and 'find_applications()' first.
    - 'variables': List of environment variables to set, following the ApplicationVariable schema.
        Each variable must include:
            - name: Name of the variable
            - inputType: One of "Topic", "FreeText", "HiddenText", "InputTopic", "OutputTopic", "Secret"
            - required: Whether the variable is mandatory (true/false)
        Optional fields:
            - multiline: Whether the variable value can be multiline (true/false)
            - description: Description of the variable
            - defaultValue: Default value for the variable (IMPORTANT: Use "defaultValue", NOT "value")
    - 'append': Whether to append these variables to existing ones (True) or replace them all (False).
        When append=True (default), existing variables are preserved and new ones are added.
        When append=False, only the provided variables will be kept (all others will be removed).
    </instructions>
    """
    return await applications.update_application_variables(ctx, workspace_id, application_id, variables, append)


# =========================================
# Deployment Management Tools
# =========================================

@mcp.tool()
async def find_deployments(ctx: Context, application_name: Optional[str] = None, status: Optional[str] = None) -> str:
    """
    <usecase>
    Finds deployments in the current workspace. Use this to get an overview of running services or to find a specific deployment_id.
    </usecase>
    <instructions>
    - You can filter by 'application_name' to see all deployments for a specific app.
    - You can filter by 'status' (e.g., "Running", "Stopped", "Error") to see deployments in a certain state.
    </instructions>
    """
    return await deployments.find_deployments(ctx, application_name, status)

@mcp.tool()
async def get_deployment_details(ctx: Context, deployment_id: str) -> str:
    """
    <usecase>
    Retrieves detailed information about a specific deployment, including its status, resource usage, and configuration.
    </usecase>
    <instructions>
    You must provide a valid 'deployment_id', which can be found using the 'find_deployments' tool.
    </instructions>
    """
    return await deployments.get_deployment_details(ctx, deployment_id)

@mcp.tool()
async def manage_deployment(
    ctx: Context,
    action: deployments.DeploymentAction,
    deployment_id: Optional[str] = None,
    application_id: Optional[str] = None,
    name: Optional[str] = None,
    replicas: int = 1,
    cpu_millicores: int = 1000,
    memory_in_mb: int = 1024
) -> str:
    """
    <usecase>
    Manages the lifecycle of a deployment. Use this to create, start, stop, or delete a deployment. This is the primary tool for controlling services in the pipeline.
    </usecase>
    <instructions>
    - To 'create', 'application_id' and 'name' are required. Resource settings are optional.
    - To 'start', 'stop', or 'delete', 'deployment_id' is required.
    - Always confirm with the user before using the 'delete' action.
    </instructions>
    """
    return await deployments.manage_deployment(
        ctx, action, deployment_id, application_id, name, replicas, cpu_millicores, memory_in_mb
    )

@mcp.tool()
async def get_deployment_logs(ctx: Context, deployment_id: str, replica_id: Optional[str] = None) -> str:
    """
    <usecase>
    Retrieves the most recent logs for a running or stopped deployment. This is essential for debugging and monitoring.
    </usecase>
    <instructions>
    - 'deployment_id' is required.
    - If a deployment has multiple replicas, you can specify a 'replica_id' to get logs from a specific instance.
    </instructions>
    """
    return await deployments.get_deployment_logs(ctx, deployment_id, replica_id, "current")

# =========================================
# Library & Workflow Tools
# =========================================

@mcp.tool()
async def find_in_library(ctx: Context, workspace_id: str, search_term: str, item_type: Optional[str] = None) -> str:
    """
    <usecase>
    Searches the Quix Library for templates and connectors. Use this to discover pre-built components for your pipeline.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    - 'search_term' is the keyword to search for (e.g., "InfluxDB", "Starter").
    - 'item_type' can be "Source", "Transformation", or "Destination" to filter results by tag (casing in important for this search).
    </instructions>
    """
    return await library.find_in_library(ctx, workspace_id, search_term, item_type)

@mcp.tool()
async def create_app_from_template(
    ctx: Context,
    workspace_id: str,
    library_item_id: str, 
    application_name: Optional[str] = None,
    path: Optional[str] = None,
    placeholders: Optional[Dict[str, str]] = None,
    environment_variables: Optional[Dict[str, str]] = None
) -> str:
    """
    <usecase>
    Creates an application from a library item using the POST /library/application endpoint. Use this to create an application based on a pre-built template from the Quix Library.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    - 'library_item_id' can be found using the 'find_in_library' tool.
    - 'application_name' is optional - if not provided, it will auto-generate a name based on the library item.
    - 'path' is optional - specify a custom path for the application.
    - 'placeholders' can be used for template placeholders (key-value pairs).
    - 'environment_variables' can be used to set any required credentials or configurations for the template.
    </instructions>
    """
    return await applications.create_app_from_template(
        ctx, workspace_id, library_item_id, application_name, path, placeholders, environment_variables
    )

@mcp.tool()
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
    return await deployments.create_deployment_from_template(
        ctx, workspace_id, library_item_id, deployment_name, create_application, environment_variables
    )

# =========================================
# Topic Management Tools
# =========================================

@mcp.tool()
async def find_topics(ctx: Context, workspace_id: str) -> str:
    """
    <usecase>
    Finds and lists all Kafka topics in a specific workspace.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    This tool lists all topics and their status. Use the topic names as input for other tools.
    </instructions>
    """
    return await topics.find_topics(ctx, workspace_id)

@mcp.tool()
async def get_topic_details(ctx: Context, workspace_id: str, topic_name: str) -> str:
    """
    <usecase>
    Retrieves detailed configuration and status information for a specific topic.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id' and 'topic_name'. If you don't know these, use 'find_workspaces()' and 'find_topics()' first.
    </instructions>
    """
    return await topics.get_topic_details(ctx, workspace_id, topic_name)

@mcp.tool()
async def manage_topic(
    ctx: Context,
    workspace_id: str,
    action: topics.TopicAction,
    name: str,
    partitions: Optional[int] = None,
    retention_in_minutes: Optional[int] = None
) -> str:
    """
    <usecase>
    Manages Kafka topics. Use this to create, update, clean (delete messages), or delete a topic.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    - For 'create', 'name' is required. 'partitions' and 'retention_in_minutes' are optional.
    - For 'update', 'name' is required. Provide 'partitions' or 'retention_in_minutes' to update them.
    - For 'clean' or 'delete', 'name' is required. Confirm with the user before using 'delete' or 'clean'.
    </instructions>
    """
    return await topics.manage_topic(ctx, workspace_id, action, name, partitions, retention_in_minutes)


# =========================================
# Workspace & Git Tools
# =========================================

@mcp.tool()
async def find_workspaces(ctx: Context) -> str:
    """
    <usecase>
    Finds and lists all workspaces (environments) for your organization. Use this to get an overview and find the workspace ID for other operations.
    </usecase>
    <instructions>
    This tool lists all workspaces you have access to. The 'workspace_id' from the results is required for most other workspace and resource management tools.
    </instructions>
    """
    return await workspaces.find_workspaces(ctx)

@mcp.tool()
async def get_workspace_details(ctx: Context, workspace_id: str) -> str:
    """
    <usecase>
    Retrieves details about a specific workspace, including its status, branch, and broker type.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    </instructions>
    """
    return await workspaces.get_workspace_details(ctx, workspace_id)

@mcp.tool()
async def promote_environment(ctx: Context, source_branch: str, target_branch: str, title: str, body: Optional[str] = None) -> str:
    """
    <usecase>
    Promotes changes from one environment (branch) to another by creating a pull request. This is the standard way to move tested changes to production.
    </usecase>
    <instructions>
    - 'source_branch' is the branch with the changes (e.g., 'develop').
    - 'target_branch' is the destination branch (e.g., 'main').
    - 'title' is a short description of the changes for the pull request.
    - 'body' is an optional longer description.
    </instructions>
    """
    return await workspaces.promote_environment(ctx, source_branch, target_branch, title, body)


# =========================================
# IDE Session Tools
# =========================================

@mcp.tool()
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
    return await sessions.find_sessions(ctx, workspace_id)

@mcp.tool()
async def get_session_details(ctx: Context, workspace_id: str, session_id: str) -> str:
    """
    <usecase>
    Retrieves detailed information about a specific IDE session, including its configuration, status, and resource usage.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    </instructions>
    """
    return await sessions.get_session_details(ctx, workspace_id, session_id)

@mcp.tool()
async def manage_session(
    ctx: Context,
    workspace_id: str,
    action: sessions.SessionAction,
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
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    - To 'start' a session, the 'application_id' is required. You can optionally specify resource allocation, branch, and environment variables.
    - To 'stop' a session, the 'session_id' is required.
    - For public access, provide 'url_prefix' when setting 'public_access' to True.
    </instructions>
    """
    return await sessions.manage_session(
        ctx, workspace_id, action, application_id, session_id, branch_name, cpu_millicores, memory_in_mb, public_access, url_prefix, environment_variables
    )

@mcp.tool()
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
    You must provide a valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    - 'file_to_run' is optional - if not provided, runs the default application entry point.
    - 'force_setup' can be used to force re-setup before running if there are environment issues.
    </instructions>
    """
    return await sessions.run_code_in_session(ctx, workspace_id, session_id, file_to_run, force_setup)

@mcp.tool()
async def update_session_config(
    ctx: Context,
    workspace_id: str,
    session_id: str,
    action: sessions.SessionUpdateAction,
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
    You must provide a valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    - For 'update_branch', provide 'branch_name' or 'git_reference'.
    - For 'update_variables', provide 'environment_variables' dictionary.
    - For 'update_application', provide 'dockerfile', 'run_entry_point', or 'variables'.
    </instructions>
    """
    return await sessions.update_session_config(
        ctx, workspace_id, session_id, action, branch_name, git_reference, environment_variables, dockerfile, run_entry_point, variables
    )

@mcp.tool()
async def get_session_application_details(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None) -> str:
    """
    <usecase>
    Retrieves detailed application information from an IDE session, including configuration and file structure.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    - 'reference' is optional - specify a git reference to view application at that point.
    </instructions>
    """
    return await sessions.get_session_application_details(ctx, workspace_id, session_id, reference)

@mcp.tool()
async def check_session_git_status(ctx: Context, workspace_id: str, session_id: str, clean_errors: bool = False) -> str:
    """
    <usecase>
    Checks the git status of a session and optionally cleans any git errors. Useful for debugging git-related issues.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    - 'clean_errors' set to True will attempt to clean any git errors found.
    </instructions>
    """
    return await sessions.check_session_git_status(ctx, workspace_id, session_id, clean_errors)

@mcp.tool()
async def keep_session_alive(ctx: Context, workspace_id: str, session_id: str) -> str:
    """
    <usecase>
    Sends a heartbeat to keep an IDE session alive and prevent it from timing out. Useful for long-running development sessions.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    - Use this periodically during long development sessions to prevent automatic session termination.
    </instructions>
    """
    return await sessions.keep_session_alive(ctx, workspace_id, session_id)

@mcp.tool()
async def download_session_code(ctx: Context, workspace_id: str, session_id: str, reference: Optional[str] = None) -> str:
    """
    <usecase>
    Downloads the complete application code from an IDE session as a zip file. Useful for backing up or sharing code.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id' and 'session_id'. Use 'find_workspaces()' and 'find_sessions()' to get these IDs.
    - 'reference' is optional - specify a git reference to download code at that point.
    - This returns information about the download, not the actual file content.
    </instructions>
    """
    return await sessions.download_session_code(ctx, workspace_id, session_id, reference)

@mcp.tool()
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
    return await sessions.commit_session_files(ctx, workspace_id, session_id, file_path, content, commit_message, action)

@mcp.tool()
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
    return await sessions.explore_session_codebase(ctx, workspace_id, session_id, reference)

@mcp.tool()
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
    return await sessions.read_session_file(ctx, workspace_id, session_id, file_path, reference)

@mcp.tool()
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
    return await sessions.work_with_session_files(ctx, workspace_id, session_id, action, file_path, content)

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
                request._send,
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
    # Note: quix-workspace argument removed - workspace_id is now passed as parameter to each tool
    parser.add_argument('--env-file', help='Path to .env file (default: .env in current directory)')
    args = parser.parse_args()
    
    if args.env_file:
        env_path = Path(args.env_file)
        if env_path.exists():
            dotenv.load_dotenv(env_path)
            logger.info(f"Loaded environment variables from {args.env_file}")
        else:
            logger.warning(f"Environment file {args.env_file} not found")
    
    if args.quix_token:
        os.environ['QUIX_TOKEN'] = args.quix_token
    
    if args.quix_base_url:
        os.environ['QUIX_BASE_URL'] = args.quix_base_url
        
    # Note: QUIX_WORKSPACE is no longer required as workspace_id is now passed as a parameter to each tool
    
    if not os.environ.get('QUIX_TOKEN') or not os.environ.get('QUIX_BASE_URL'):
        logger.error("QUIX_TOKEN and QUIX_BASE_URL are required. Set them via arguments or a .env file.")
        exit(1)
    
    mcp_server = mcp._mcp_server
    starlette_app = create_starlette_app(mcp_server, debug=True)
    
    logger.info(f"Starting Quix Portal MCP server on {args.host}:{args.port}")
    logger.info(f"Using Quix Portal at {os.environ.get('QUIX_BASE_URL')}")
    logger.info("Workspace ID will be provided as parameter for each tool call")
    
    uvicorn.run(starlette_app, host=args.host, port=args.port)