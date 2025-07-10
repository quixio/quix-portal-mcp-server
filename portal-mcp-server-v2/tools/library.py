"""Quix Library and Workflow MCP tools."""

import os
from typing import Any, Optional, Dict, List
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

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
    - 'item_type' can be "Source", "Transformation", or "Destination" to filter results by tag (casing in important for this search).
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
        
        result += f"\nTo use a library item:\n- Create an application: `create_app_from_template(workspace_id='{workspace_id}', library_item_id='...', ...)`\n- Create a deployment: `create_deployment_from_template(workspace_id='{workspace_id}', library_item_id='...', ...)`"
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error searching library for '{search_term}' in workspace '{workspace_id}'. Please check your network connection and ensure the search term is correct. Try using broader search terms like 'starter', 'source', 'sink', or technology names like 'kafka', 'influxdb'. Original error: {str(e)}"

