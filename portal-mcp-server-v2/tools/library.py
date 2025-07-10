"""Quix Library and Workflow MCP tools."""

import os
from typing import Any, Optional, Dict, List
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError
from . import applications, deployments

async def find_in_library(
    ctx: Context,
    workspace_id: str,
    search_term: str, 
    item_type: Optional[str] = None
) -> str:
    """
    <usecase>
    Searches the Quix Library for templates and connectors. Use this to discover pre-built components for your pipeline.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    - 'search_term' is the keyword to search for (e.g., "InfluxDB", "Starter").
    - 'item_type' can be "source", "transformation", or "destination" to filter results.
    </instructions>
    """
    try:
        payload = {"tags": [search_term]}
        if item_type:
            payload["tags"].append(item_type)
        
        items = await make_quix_request(ctx, "POST", "library/query", workspace_id=workspace_id, json=payload)
        
        if not items:
            return f"No library items found for search term '{search_term}'."
        
        result = "Found the following library items:\n\n"
        for item in items:
            result += f"- Name: {item.get('name')}\n  ID: {item.get('itemId')}\n  Description: {item.get('shortDescription')}\n"
        
        result += f"\nTo use a template, call `create_pipeline_from_template(workspace_id='{workspace_id}', template_id='...', ...)`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error searching library for '{search_term}' in workspace '{workspace_id}'. Please check your network connection and ensure the search term is correct. Try using broader search terms like 'starter', 'source', 'sink', or technology names like 'kafka', 'influxdb'. Original error: {str(e)}"

async def create_pipeline_from_template(
    ctx: Context,
    workspace_id: str,
    template_id: str, 
    application_name: str,
    deployment_name: str,
    input_topic: Optional[str] = None,
    output_topic: Optional[str] = None,
    environment_variables: Optional[Dict[str, str]] = None
) -> str:
    """
    <usecase>
    Creates and deploys a complete application from a library template. This is the fastest way to set up a new pipeline component like a data source or sink.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    - 'template_id' can be found using the 'find_in_library' tool.
    - 'application_name' and 'deployment_name' are required.
    - Provide 'input_topic' and 'output_topic' if the template requires them.
    - 'environment_variables' can be used to set any required credentials or configurations for the template.
    </instructions>
    """
    try:
        await ctx.info(f"Creating application '{application_name}' from template '{template_id}' in workspace '{workspace_id}'...")
        
        # The original create_application_from_library tool is now a helper
        create_app_payload = {
            "workspaceId": workspace_id,
            "libraryItemId": template_id,
            "applicationName": application_name,
            "environmentVariables": environment_variables
        }
        app = await make_quix_request(ctx, "POST", "library/application", workspace_id=workspace_id, json=create_app_payload)
        
        app_id = app.get('applicationId')
        if not app_id:
            raise QuixApiError("Failed to get new application ID after creation.")
        
        await ctx.info(f"Application '{application_name}' created with ID '{app_id}'.")

        # Configure topics if provided
        if input_topic or output_topic:
            await ctx.info("Configuring topics...")
            await applications.set_application_topics(ctx, workspace_id, app_id, input_topic, output_topic)
        
        await ctx.info(f"Deploying application as '{deployment_name}'...")
        
        # The original create_deployment is now a helper called by manage_deployment
        deploy_result_str = await deployments.manage_deployment(
            ctx,
            workspace_id=workspace_id,
            action=deployments.DeploymentAction.create,
            application_id=app_id,
            name=deployment_name
        )

        return f"Successfully initiated pipeline creation from template '{template_id}'.\n{deploy_result_str}"

    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error creating pipeline from template '{template_id}' in workspace '{workspace_id}'. Please ensure the template ID is correct and the application name is unique. You can find valid template IDs with `find_in_library(workspace_id='{workspace_id}', ...)`. If topics are specified, ensure they exist with `find_topics(workspace_id='{workspace_id}')`. Original error: {str(e)}"