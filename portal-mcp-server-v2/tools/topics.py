"""Quix Topics MCP tools."""

from typing import Any, Optional, Dict
from enum import Enum
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

class TopicAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    clean = "clean"

# --- Internal Helper Functions ---

async def _get_topics(ctx: Context, workspace_id: str):
    return await make_quix_request(ctx, "GET", "{workspaceId}/topics", workspace_id=workspace_id)

async def _get_topic(ctx: Context, workspace_id: str, topic_name: str):
    return await make_quix_request(ctx, "GET", f"{{workspaceId}}/topics/{topic_name}", workspace_id=workspace_id)

async def _create_topic(ctx: Context, workspace_id: str, payload: Dict[str, Any]):
    return await make_quix_request(ctx, "POST", "{workspaceId}/topics", workspace_id=workspace_id, json=payload)

async def _update_topic(ctx: Context, workspace_id: str, topic_name: str, payload: Dict[str, Any]):
    return await make_quix_request(ctx, "PATCH", f"{{workspaceId}}/topics/{topic_name}", workspace_id=workspace_id, json=payload)

async def _delete_topic(ctx: Context, workspace_id: str, topic_name: str):
    return await make_quix_request(ctx, "DELETE", f"{{workspaceId}}/topics/{topic_name}", workspace_id=workspace_id)

async def _clean_topic(ctx: Context, workspace_id: str, topic_name: str):
    return await make_quix_request(ctx, "POST", f"{{workspaceId}}/topics/{topic_name}/clean", workspace_id=workspace_id)


# --- New High-Level MCP Tools ---

async def find_topics(ctx: Context, workspace_id: str) -> str:
    """
    <usecase>
    Finds and lists all Kafka topics in a specific workspace.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    </instructions>
    """
    try:
        topics = await _get_topics(ctx, workspace_id)
        if not topics:
            return f"No topics found in workspace '{workspace_id}'. You can create one with `manage_topic(workspace_id='{workspace_id}', action='create', name='...')`."

        result = f"Found the following topics in workspace '{workspace_id}':\n\n"
        for topic in topics:
            result += f"- Name: {topic.get('name')}\n  ID: {topic.get('id')}\n  Status: {topic.get('status')}\n"
        
        result += f"\nTo get more details, use `get_topic_details(workspace_id='{workspace_id}', topic_name='...')`."
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error finding topics in workspace '{workspace_id}'. Please check your workspace credentials and network connection. If no topics exist, you can create one with `manage_topic(workspace_id='{workspace_id}', action='create', name='my-topic')`. Original error: {str(e)}"

async def get_topic_details(ctx: Context, workspace_id: str, topic_name: str) -> str:
    """
    <usecase>
    Retrieves detailed information about a specific Kafka topic including its configuration and status.
    </usecase>
    <instructions>
    You must provide both a valid 'workspace_id' and 'topic_name'. If you don't know these, use 'find_workspaces()' and 'find_topics()' first.
    </instructions>
    """
    try:
        topic = await _get_topic(ctx, workspace_id, topic_name)
        if not topic:
            return f"Topic '{topic_name}' not found."

        result = f"Details for Topic '{topic.get('name')}':\n"
        # ... (add detailed formatting as in the original `get_topic`) ...
        config = topic.get('configuration')
        if config:
            result += f"Partitions: {config.get('partitions')}\n"
            result += f"Retention (minutes): {config.get('retentionInMinutes')}\n"
        
        return result
    except QuixApiError as e:
        # --- Guided Error Handling ---
        return f"Error getting details for topic '{topic_name}' in workspace '{workspace_id}'. The names might be incorrect or the topic may not exist. Try using `find_topics(workspace_id='{workspace_id}')` to get a list of valid topic names. Original error: {str(e)}"

async def manage_topic(
    ctx: Context,
    workspace_id: str,
    action: TopicAction,
    name: str,
    partitions: Optional[int] = None,
    retention_in_minutes: Optional[int] = None
) -> str:
    """
    <usecase>
    Manages Kafka topic lifecycle operations including creating, updating, deleting, and cleaning topics.
    </usecase>
    <instructions>
    You must provide a valid 'workspace_id'. If you don't know the workspace ID, use 'find_workspaces()' first to list all available workspaces and their IDs.
    </instructions>
    """
    try:
        if action == TopicAction.create:
            payload = {"name": name}
            config = {}
            if partitions: config["partitions"] = partitions
            if retention_in_minutes: config["retentionInMinutes"] = retention_in_minutes
            if config: payload["configuration"] = config
            
            topic = await _create_topic(ctx, workspace_id, payload)
            return f"Topic '{topic.get('name')}' created successfully with ID '{topic.get('id')}' in workspace '{workspace_id}'. You can now use it as an input or output for an application."

        if action == TopicAction.update:
            payload = {}
            if partitions: payload["partitions"] = partitions
            if retention_in_minutes: payload["retentionInMinutes"] = retention_in_minutes
            if not payload:
                return "Error: At least one field (partitions or retention_in_minutes) must be provided for an update."
            await _update_topic(ctx, workspace_id, name, payload)
            return f"Topic '{name}' updated successfully."

        if action == TopicAction.clean:
            await _clean_topic(ctx, workspace_id, name)
            return f"All messages in topic '{name}' have been cleared."

        if action == TopicAction.delete:
            await _delete_topic(ctx, workspace_id, name)
            return f"Topic '{name}' has been deleted successfully."

    except QuixApiError as e:
        # --- Guided Error Handling ---
        if action == TopicAction.create:
            return f"Error creating topic '{name}'. The name might already exist in this workspace or contain invalid characters. Try a different name or check the existing topics with `find_topics()`. Original error: {str(e)}"
        elif action == TopicAction.update:
            return f"Error updating topic '{name}'. Please ensure the topic name is correct and you have the necessary permissions. You can verify the name with `find_topics()`. Original error: {str(e)}"
        elif action in [TopicAction.delete, TopicAction.clean]:
            return f"Error performing '{action.value}' on topic '{name}'. Please ensure the topic name is correct and the topic exists. You can verify the name with `find_topics()`. Note: Topics in use by applications cannot be deleted. Original error: {str(e)}"
        else:
            return f"Error managing topic: {str(e)}"