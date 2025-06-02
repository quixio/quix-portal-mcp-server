"""Quix Topics MCP tools."""

from typing import Any, Optional, Dict, List, Union
from enum import Enum
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

# Define clean-up policy enum to match the TopicCleanupPolicy in the schema
class TopicCleanupPolicy(str, Enum):
    DELETE = "Delete"
    COMPACT = "Compact"
    DELETE_AND_COMPACT = "DeleteAndCompact"

async def get_topics(ctx: Context) -> str:
    """List all topics in your workspace.
    """
    try:
        topics = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/topics"
        )
        
        if not topics:
            return "No topics found in this workspace."
        
        result = "Topics:\n\n"
        for topic in topics:
            result += f"Name: {topic.get('name')}\n"
            result += f"ID: {topic.get('id')}\n"
            
            # Add status information
            status = topic.get('status')
            if status:
                result += f"Status: {status}\n"
                
            # Include error information if present
            error_status = topic.get('errorStatus')
            if error_status:
                result += f"Error Status: {error_status}\n"
                last_error = topic.get('lastError')
                if last_error:
                    result += f"Last Error: {last_error}\n"
                    
            # Add timestamps
            created_at = topic.get('createdAt')
            if created_at:
                result += f"Created At: {created_at}\n"
                
            updated_at = topic.get('updatedAt')
            if updated_at:
                result += f"Updated At: {updated_at}\n"
                
            # Add persistence info if present
            persisted = topic.get('persisted')
            if persisted is not None:
                result += f"Persisted: {persisted}\n"
                
            persisted_status = topic.get('persistedStatus')
            if persisted_status:
                result += f"Persisted Status: {persisted_status}\n"
                
            # Add other flags
            external = topic.get('external')
            if external:
                result += f"External: {external}\n"
                
            unmanaged = topic.get('unmanaged')
            if unmanaged:
                result += f"Unmanaged: {unmanaged}\n"
                
            sdk_topic = topic.get('sdkTopic')
            if sdk_topic:
                result += f"SDK Topic: {sdk_topic}\n"
                
            # Add external sources/destinations if present
            external_source = topic.get('externalSourceName')
            if external_source:
                result += f"External Source: {external_source}\n"
                
            external_destination = topic.get('externalDestinationName')
            if external_destination:
                result += f"External Destination: {external_destination}\n"
                
            # Add configuration if present
            config = topic.get('configuration')
            if config:
                result += "\nConfiguration:\n"
                
                partitions = config.get('partitions')
                if partitions is not None:
                    result += f"  Partitions: {partitions}\n"
                    
                replication = config.get('replicationFactor')
                if replication is not None:
                    result += f"  Replication Factor: {replication}\n"
                    
                retention_mins = config.get('retentionInMinutes')
                if retention_mins is not None:
                    result += f"  Retention (minutes): {retention_mins}\n"
                    
                retention_bytes = config.get('retentionInBytes')
                if retention_bytes is not None:
                    result += f"  Retention (bytes): {retention_bytes}\n"
                    
                cleanup_policy = config.get('cleanupPolicy')
                if cleanup_policy:
                    result += f"  Cleanup Policy: {cleanup_policy}\n"
            
            # Add linked topic info if present
            linked_info = topic.get('linkedTopicInfo')
            if linked_info:
                result += "\nLinked Topic Info:\n"
                
                is_linked = linked_info.get('isLinked')
                if is_linked:
                    result += f"  Is Linked: {is_linked}\n"
                    
                is_locked = linked_info.get('isLocked')
                if is_locked:
                    result += f"  Is Locked: {is_locked}\n"
                    
                is_scratchpad = linked_info.get('isScratchpad')
                if is_scratchpad:
                    result += f"  Is Scratchpad: {is_scratchpad}\n"
                    
                repository_name = linked_info.get('repositoryName')
                if repository_name:
                    result += f"  Repository: {repository_name}\n"
                    
                environment_name = linked_info.get('environmentName')
                if environment_name:
                    result += f"  Environment: {environment_name}\n"
                
            # Add linked topic destination info if present
            linked_destinations = topic.get('linkedTopicDestinationInfo')
            if linked_destinations and len(linked_destinations) > 0:
                result += "\nLinked Topic Destinations:\n"
                
                for dest in linked_destinations:
                    dest_workspace = dest.get('workspaceId')
                    if dest_workspace:
                        result += f"  Workspace ID: {dest_workspace}\n"
                        
                    dest_topic = dest.get('topicName')
                    if dest_topic:
                        result += f"  Topic Name: {dest_topic}\n"
                        
                    dest_repo = dest.get('repositoryName')
                    if dest_repo:
                        result += f"  Repository: {dest_repo}\n"
                        
                    dest_env = dest.get('environmentName')
                    if dest_env:
                        result += f"  Environment: {dest_env}\n"
                        
                    result += "  ---\n"
            
            result += "-" * 40 + "\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

async def get_topic(ctx: Context, topic_name: str) -> str:
    """Get details of a specific topic.
    
    Args:
        topic_name: The name of the topic to retrieve
    """
    try:
        topic = await make_quix_request(
            ctx, 
            "GET", 
            "{workspaceId}/topics/{topicName}".replace("{topicName}", topic_name)
        )
        
        if not topic:
            return f"No topic found with name {topic_name}."
        
        # Format the topic details
        result = "Topic Details:\n\n"
        result += f"Name: {topic.get('name')}\n"
        result += f"ID: {topic.get('id')}\n"
        result += f"Workspace ID: {topic.get('workspaceId')}\n"
        
        # Add status information
        status = topic.get('status')
        if status:
            result += f"Status: {status}\n"
            
        # Include error information if present
        error_status = topic.get('errorStatus')
        if error_status:
            result += f"Error Status: {error_status}\n"
            last_error = topic.get('lastError')
            if last_error:
                result += f"Last Error: {last_error}\n"
                
        # Add timestamps
        created_at = topic.get('createdAt')
        if created_at:
            result += f"Created At: {created_at}\n"
            
        updated_at = topic.get('updatedAt')
        if updated_at:
            result += f"Updated At: {updated_at}\n"
            
        # Add persistence info if present
        persisted = topic.get('persisted')
        if persisted is not None:
            result += f"Persisted: {persisted}\n"
            
        persisted_status = topic.get('persistedStatus')
        if persisted_status:
            result += f"Persisted Status: {persisted_status}\n"
            
        # Add other flags
        external = topic.get('external')
        if external:
            result += f"External: {external}\n"
            
        unmanaged = topic.get('unmanaged')
        if unmanaged:
            result += f"Unmanaged: {unmanaged}\n"
            
        sdk_topic = topic.get('sdkTopic')
        if sdk_topic:
            result += f"SDK Topic: {sdk_topic}\n"
            
        # Add data tier info if present
        data_tier = topic.get('dataTier')
        if data_tier:
            result += f"Data Tier: {data_tier}\n"
            
        # Add external sources/destinations if present
        external_source = topic.get('externalSourceName')
        if external_source:
            result += f"External Source: {external_source}\n"
            
        external_destination = topic.get('externalDestinationName')
        if external_destination:
            result += f"External Destination: {external_destination}\n"
            
        # Add configuration if present
        config = topic.get('configuration')
        if config:
            result += "\nConfiguration:\n"
            
            partitions = config.get('partitions')
            if partitions is not None:
                result += f"  Partitions: {partitions}\n"
                
            replication = config.get('replicationFactor')
            if replication is not None:
                result += f"  Replication Factor: {replication}\n"
                
            retention_mins = config.get('retentionInMinutes')
            if retention_mins is not None:
                result += f"  Retention (minutes): {retention_mins}\n"
                
            retention_bytes = config.get('retentionInBytes')
            if retention_bytes is not None:
                result += f"  Retention (bytes): {retention_bytes}\n"
                
            cleanup_policy = config.get('cleanupPolicy')
            if cleanup_policy:
                result += f"  Cleanup Policy: {cleanup_policy}\n"
        
        # Add linked topic info if present
        linked_info = topic.get('linkedTopicInfo')
        if linked_info:
            result += "\nLinked Topic Info:\n"
            
            is_linked = linked_info.get('isLinked')
            if is_linked:
                result += f"  Is Linked: {is_linked}\n"
                
            is_locked = linked_info.get('isLocked')
            if is_locked:
                result += f"  Is Locked: {is_locked}\n"
                
            is_scratchpad = linked_info.get('isScratchpad')
            if is_scratchpad:
                result += f"  Is Scratchpad: {is_scratchpad}\n"
                
            has_repo_access = linked_info.get('hasRepositoryAccess')
            if has_repo_access is not None:
                result += f"  Has Repository Access: {has_repo_access}\n"
                
            has_workspace_access = linked_info.get('hasWorkspaceAccess')
            if has_workspace_access is not None:
                result += f"  Has Workspace Access: {has_workspace_access}\n"
                
            repository_name = linked_info.get('repositoryName')
            if repository_name:
                result += f"  Repository: {repository_name}\n"
                
            environment_name = linked_info.get('environmentName')
            if environment_name:
                result += f"  Environment: {environment_name}\n"
            
        # Add linked topic destination info if present
        linked_destinations = topic.get('linkedTopicDestinationInfo')
        if linked_destinations and len(linked_destinations) > 0:
            result += "\nLinked Topic Destinations:\n"
            
            for dest in linked_destinations:
                dest_workspace = dest.get('workspaceId')
                if dest_workspace:
                    result += f"  Workspace ID: {dest_workspace}\n"
                    
                dest_topic = dest.get('topicName')
                if dest_topic:
                    result += f"  Topic Name: {dest_topic}\n"
                    
                dest_repo = dest.get('repositoryName')
                if dest_repo:
                    result += f"  Repository: {dest_repo}\n"
                    
                dest_env = dest.get('environmentName')
                if dest_env:
                    result += f"  Environment: {dest_env}\n"
                    
                result += "  ---\n"
                
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

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
    try:
        # Build the topic create request according to the TopicCreateRequest schema
        payload = {
            "name": name,
            "unmanaged": unmanaged
        }
        
        # Add configuration if any related parameters are provided
        if any([partitions, replication_factor, retention_in_minutes, retention_in_bytes, cleanup_policy]):
            config = {}
            
            if partitions is not None:
                config["partitions"] = partitions
                
            if replication_factor is not None:
                config["replicationFactor"] = replication_factor
                
            if retention_in_minutes is not None:
                config["retentionInMinutes"] = retention_in_minutes
                
            if retention_in_bytes is not None:
                config["retentionInBytes"] = retention_in_bytes
                
            if cleanup_policy:
                # Validate cleanup policy
                valid_policies = [p.value for p in TopicCleanupPolicy]
                if cleanup_policy not in valid_policies:
                    return f"Error: Invalid cleanup policy. Must be one of: {', '.join(valid_policies)}"
                config["cleanupPolicy"] = cleanup_policy
                
            payload["configuration"] = config
        
        # Add optional parameters if provided
        if data_tier_name:
            payload["dataTierName"] = data_tier_name
            
        if external_source_name:
            payload["externalSourceName"] = external_source_name
            
        if external_destination_name:
            payload["externalDestinationName"] = external_destination_name
            
        # Add linked topic info if both required parameters are provided
        if linked_topic_workspace_id and linked_topic_name:
            payload["linkedTopic"] = {
                "workspaceId": linked_topic_workspace_id,
                "topicName": linked_topic_name
            }
        elif linked_topic_workspace_id or linked_topic_name:
            # Both parameters are required for linking
            return "Error: Both linked_topic_workspace_id and linked_topic_name must be provided together to link a topic."
            
        topic = await make_quix_request(
            ctx,
            "POST",
            "{workspaceId}/topics",
            json=payload
        )
        
        if not topic:
            return f"Failed to create topic '{name}'."
            
        result = f"Successfully created topic '{name}'.\n\n"
        result += f"Topic ID: {topic.get('id')}\n"
        result += f"Status: {topic.get('status')}\n"
        
        # Show configuration if present
        config = topic.get('configuration')
        if config:
            result += "\nConfiguration:\n"
            
            partitions = config.get('partitions')
            if partitions is not None:
                result += f"  Partitions: {partitions}\n"
                
            replication = config.get('replicationFactor')
            if replication is not None:
                result += f"  Replication Factor: {replication}\n"
                
            retention_mins = config.get('retentionInMinutes')
            if retention_mins is not None:
                result += f"  Retention (minutes): {retention_mins}\n"
                
            retention_bytes = config.get('retentionInBytes')
            if retention_bytes is not None:
                result += f"  Retention (bytes): {retention_bytes}\n"
                
            cleanup_policy = config.get('cleanupPolicy')
            if cleanup_policy:
                result += f"  Cleanup Policy: {cleanup_policy}\n"
                
        # Show linking info if present
        linked_info = topic.get('linkedTopicInfo')
        if linked_info and linked_info.get('isLinked'):
            result += "\nLinked Topic Info:\n"
            result += f"  Is Linked: {linked_info.get('isLinked')}\n"
            
            repository_name = linked_info.get('repositoryName')
            if repository_name:
                result += f"  Repository: {repository_name}\n"
                
            environment_name = linked_info.get('environmentName')
            if environment_name:
                result += f"  Environment: {environment_name}\n"
                
        return result
    except QuixApiError as e:
        return f"Error creating topic: {str(e)}"

async def update_topic(
    ctx: Context,
    topic_name: str,
    partitions: Optional[int] = None,
    retention_in_minutes: Optional[int] = None,
    retention_in_bytes: Optional[int] = None,
    cleanup_policy: Optional[str] = None,
    data_tier_name: Optional[str] = None,
    unset_data_tier: bool = False,
    external_source_name: Optional[str] = None,
    external_destination_name: Optional[str] = None,
    unlink_topic: bool = False,
    linked_topic_workspace_id: Optional[str] = None,
    linked_topic_name: Optional[str] = None
) -> str:
    """Update a topic's configuration.
    
    Args:
        topic_name: The name of the topic to update
        partitions: Optional number of partitions (must be greater than current value)
        retention_in_minutes: Optional retention time in minutes
        retention_in_bytes: Optional retention size in bytes
        cleanup_policy: Optional cleanup policy (one of: Delete, Compact, DeleteAndCompact)
        data_tier_name: Optional data tier name
        unset_data_tier: Whether to unset the data tier (default: False)
        external_source_name: Optional external source name
        external_destination_name: Optional external destination name
        unlink_topic: Whether to unlink the topic (default: False)
        linked_topic_workspace_id: Optional workspace ID for a linked topic
        linked_topic_name: Optional topic name for a linked topic
    """
    try:
        # Build the topic patch request according to the TopicPatchRequest schema
        payload = {}
        
        # Add partitions if provided
        if partitions is not None:
            payload["partitions"] = partitions
            
        # Add retention values if provided
        if retention_in_minutes is not None:
            payload["retentionInMinutes"] = retention_in_minutes
            
        if retention_in_bytes is not None:
            payload["retentionInBytes"] = retention_in_bytes
            
        # Add cleanup policy if provided
        if cleanup_policy:
            # Validate cleanup policy
            valid_policies = [p.value for p in TopicCleanupPolicy]
            if cleanup_policy not in valid_policies:
                return f"Error: Invalid cleanup policy. Must be one of: {', '.join(valid_policies)}"
            payload["cleanupPolicy"] = cleanup_policy
            
        # Add data tier info if provided
        if data_tier_name:
            payload["dataTierName"] = data_tier_name
            
        if unset_data_tier:
            payload["unsetDataTier"] = True
            
        # Add external source/destination if provided
        if external_source_name:
            payload["externalSourceName"] = external_source_name
            
        if external_destination_name:
            payload["externalDestinationName"] = external_destination_name
            
        # Add unlinking if requested
        if unlink_topic:
            payload["unlinkTopic"] = True
            
        # Add linked topic info if both required parameters are provided
        if linked_topic_workspace_id and linked_topic_name:
            payload["linkedTopic"] = {
                "workspaceId": linked_topic_workspace_id,
                "topicName": linked_topic_name
            }
        elif linked_topic_workspace_id or linked_topic_name:
            # Both parameters are required for linking
            return "Error: Both linked_topic_workspace_id and linked_topic_name must be provided together to link a topic."
            
        topic = await make_quix_request(
            ctx,
            "PATCH",
            "{workspaceId}/topics/{topicName}".replace("{topicName}", topic_name),
            json=payload
        )
        
        if not topic:
            return f"Failed to update topic '{topic_name}'."
            
        result = f"Successfully updated topic '{topic_name}'.\n\n"
        result += f"Topic ID: {topic.get('id')}\n"
        result += f"Status: {topic.get('status')}\n"
        
        # Show updated configuration
        config = topic.get('configuration')
        if config:
            result += "\nUpdated Configuration:\n"
            
            config_partitions = config.get('partitions')
            if config_partitions is not None:
                result += f"  Partitions: {config_partitions}\n"
                
            replication = config.get('replicationFactor')
            if replication is not None:
                result += f"  Replication Factor: {replication}\n"
                
            retention_mins = config.get('retentionInMinutes')
            if retention_mins is not None:
                result += f"  Retention (minutes): {retention_mins}\n"
                
            retention_bytes = config.get('retentionInBytes')
            if retention_bytes is not None:
                result += f"  Retention (bytes): {retention_bytes}\n"
                
            config_cleanup_policy = config.get('cleanupPolicy')
            if config_cleanup_policy:
                result += f"  Cleanup Policy: {config_cleanup_policy}\n"
                
        # Show data tier if present
        data_tier = topic.get('dataTier')
        if data_tier:
            result += f"\nData Tier: {data_tier}\n"
            
        # Show external info if present
        external_source = topic.get('externalSourceName')
        if external_source:
            result += f"External Source: {external_source}\n"
            
        external_destination = topic.get('externalDestinationName')
        if external_destination:
            result += f"External Destination: {external_destination}\n"
            
        # Show linking info if present
        linked_info = topic.get('linkedTopicInfo')
        if linked_info:
            is_linked = linked_info.get('isLinked')
            result += f"\nIs Linked: {is_linked}\n"
            
            if is_linked:
                repository_name = linked_info.get('repositoryName')
                if repository_name:
                    result += f"Repository: {repository_name}\n"
                    
                environment_name = linked_info.get('environmentName')
                if environment_name:
                    result += f"Environment: {environment_name}\n"
                
        return result
    except QuixApiError as e:
        return f"Error updating topic: {str(e)}"

async def delete_topic(ctx: Context, topic_name: str) -> str:
    """Delete a topic from your workspace.
    
    Args:
        topic_name: The name of the topic to delete
    """
    try:
        result = await make_quix_request(
            ctx,
            "DELETE",
            "{workspaceId}/topics/{topicName}".replace("{topicName}", topic_name)
        )
        
        return f"Successfully deleted topic '{topic_name}'."
    except QuixApiError as e:
        return f"Error deleting topic: {str(e)}"

async def clean_topic(ctx: Context, topic_name: str) -> str:
    """Clean the contents of a topic (removes all messages).
    
    Args:
        topic_name: The name of the topic to clean
    """
    try:
        result = await make_quix_request(
            ctx,
            "POST",
            "{workspaceId}/topics/{topicName}/clean".replace("{topicName}", topic_name)
        )
        
        return f"Successfully cleaned topic '{topic_name}'."
    except QuixApiError as e:
        return f"Error cleaning topic: {str(e)}"

async def clear_topic_error(ctx: Context, topic_name: str) -> str:
    """Clear the error state of a topic.
    
    Args:
        topic_name: The name of the topic to clear error state for
    """
    try:
        result = await make_quix_request(
            ctx,
            "POST",
            "{workspaceId}/topics/{topicName}/clear-error".replace("{topicName}", topic_name)
        )
        
        return f"Successfully cleared error state for topic '{topic_name}'."
    except QuixApiError as e:
        return f"Error clearing topic error: {str(e)}"

async def get_default_topic_config(ctx: Context) -> str:
    """Get the default topic configuration for your workspace.
    """
    try:
        config = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/config/default"
        )
        
        if not config:
            return "No default topic configuration found."
            
        result = "Default Topic Configuration:\n\n"
        
        partitions = config.get('partitions')
        if partitions is not None:
            result += f"Partitions: {partitions}\n"
            
        replication = config.get('replicationFactor')
        if replication is not None:
            result += f"Replication Factor: {replication}\n"
            
        retention_mins = config.get('retentionInMinutes')
        if retention_mins is not None:
            result += f"Retention (minutes): {retention_mins}\n"
            
        retention_bytes = config.get('retentionInBytes')
        if retention_bytes is not None:
            result += f"Retention (bytes): {retention_bytes}\n"
            
        cleanup_policy = config.get('cleanupPolicy')
        if cleanup_policy:
            result += f"Cleanup Policy: {cleanup_policy}\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving default topic configuration: {str(e)}"

async def search_topics(
    ctx: Context,
    data_tier: Optional[str] = None,
    workspace_id: Optional[str] = None,
    repository_id: Optional[str] = None,
    linkable: Optional[bool] = None,
    linked: Optional[bool] = None,
    locked: Optional[bool] = None,
    is_sdk: Optional[bool] = None,
    page_number: Optional[int] = None,
    page_size: Optional[int] = None
) -> str:
    """Search for topics across workspaces with various filters.
    
    Args:
        data_tier: Optional data tier filter
        workspace_id: Optional workspace ID filter (if not provided, uses the current workspace)
        repository_id: Optional repository ID filter
        linkable: Optional filter for linkable topics (True/False)
        linked: Optional filter for linked topics (True/False)
        locked: Optional filter for locked topics (True/False)
        is_sdk: Optional filter for SDK topics (True/False)
        page_number: Optional page number for pagination
        page_size: Optional page size for pagination
    """
    try:
        params = {}
        
        # Add filters if provided
        if data_tier:
            params["DataTier"] = data_tier
            
        if workspace_id:
            params["WorkspaceId"] = workspace_id
            
        if repository_id:
            params["RepositoryId"] = repository_id
            
        if linkable is not None:
            params["Linkable"] = str(linkable).lower()
            
        if linked is not None:
            params["Linked"] = str(linked).lower()
            
        if locked is not None:
            params["Locked"] = str(locked).lower()
            
        if is_sdk is not None:
            params["IsSdk"] = str(is_sdk).lower()
            
        # Add pagination if provided
        if page_number is not None:
            params["PageNumber"] = page_number
            
        if page_size is not None:
            params["PageSize"] = page_size
            
        topics = await make_quix_request(
            ctx,
            "GET",
            "topics",
            params=params
        )
        
        if not topics:
            return "No topics found matching the search criteria."
            
        result = "Topics found:\n\n"
        for topic in topics:
            result += f"Name: {topic.get('name')}\n"
            result += f"ID: {topic.get('id')}\n"
            result += f"Workspace ID: {topic.get('workspaceId')}\n"
            
            # Add status information
            status = topic.get('status')
            if status:
                result += f"Status: {status}\n"
                
            # Add data tier if present
            data_tier = topic.get('dataTier')
            if data_tier:
                result += f"Data Tier: {data_tier}\n"
                
            # Add linked topic info if present
            linked_info = topic.get('linkedTopicInfo')
            if linked_info:
                is_linked = linked_info.get('isLinked')
                if is_linked:
                    result += f"Is Linked: {is_linked}\n"
                    
                is_locked = linked_info.get('isLocked')
                if is_locked:
                    result += f"Is Locked: {is_locked}\n"
                    
                is_scratchpad = linked_info.get('isScratchpad')
                if is_scratchpad:
                    result += f"Is Scratchpad: {is_scratchpad}\n"
                    
                repository_name = linked_info.get('repositoryName')
                if repository_name:
                    result += f"Repository: {repository_name}\n"
                    
                environment_name = linked_info.get('environmentName')
                if environment_name:
                    result += f"Environment: {environment_name}\n"
                    
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error searching topics: {str(e)}"

async def get_linkable_topics(ctx: Context) -> str:
    """Get all linkable topics from your workspace.
    """
    try:
        topics = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/all-linkable"
        )
        
        if not topics:
            return "No linkable topics found in this workspace."
            
        result = "Linkable Topics:\n\n"
        for topic in topics:
            result += f"Name: {topic.get('name')}\n"
            result += f"ID: {topic.get('id')}\n"
            
            # Add status information
            status = topic.get('status')
            if status:
                result += f"Status: {status}\n"
                
            # Add linked topic info if present
            linked_info = topic.get('linkedTopicInfo')
            if linked_info:
                is_linked = linked_info.get('isLinked')
                if is_linked:
                    result += f"Is Linked: {is_linked}\n"
                    
                is_locked = linked_info.get('isLocked')
                if is_locked:
                    result += f"Is Locked: {is_locked}\n"
                    
                repository_name = linked_info.get('repositoryName')
                if repository_name:
                    result += f"Repository: {repository_name}\n"
                    
                environment_name = linked_info.get('environmentName')
                if environment_name:
                    result += f"Environment: {environment_name}\n"
                    
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving linkable topics: {str(e)}"

async def get_external_topics(ctx: Context) -> str:
    """Get all available external topics that can be imported.
    """
    try:
        result = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/external/import"
        )
        
        if not result:
            return "No external topics available for import."
            
        return f"External topics available for import: {result}"
    except QuixApiError as e:
        return f"Error retrieving external topics: {str(e)}"

async def check_imported_topics_refresh(ctx: Context) -> str:
    """Check what would happen if you refresh imported topics (dry run).
    """
    try:
        result = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/external/import/refresh"
        )
        
        if not result:
            return "No changes would occur from refreshing imported topics."
            
        output = "Potential changes from refreshing imported topics:\n\n"
        
        # Handle changed topics
        changed_topics = result.get('changedTopics', [])
        if changed_topics and len(changed_topics) > 0:
            output += "Topics that would be changed:\n"
            
            for topic in changed_topics:
                name = topic.get('name')
                output += f"- {name}\n"
                
                current_config = topic.get('currentConfig')
                target_config = topic.get('targetConfig')
                
                if current_config and target_config:
                    output += "  Changes:\n"
                    
                    # Compare partitions
                    current_partitions = current_config.get('partitions')
                    target_partitions = target_config.get('partitions')
                    if current_partitions != target_partitions:
                        output += f"    Partitions: {current_partitions} -> {target_partitions}\n"
                        
                    # Compare replication factor
                    current_replication = current_config.get('replicationFactor')
                    target_replication = target_config.get('replicationFactor')
                    if current_replication != target_replication:
                        output += f"    Replication Factor: {current_replication} -> {target_replication}\n"
                        
                    # Compare retention in minutes
                    current_retention_mins = current_config.get('retentionInMinutes')
                    target_retention_mins = target_config.get('retentionInMinutes')
                    if current_retention_mins != target_retention_mins:
                        output += f"    Retention (minutes): {current_retention_mins} -> {target_retention_mins}\n"
                        
                    # Compare retention in bytes
                    current_retention_bytes = current_config.get('retentionInBytes')
                    target_retention_bytes = target_config.get('retentionInBytes')
                    if current_retention_bytes != target_retention_bytes:
                        output += f"    Retention (bytes): {current_retention_bytes} -> {target_retention_bytes}\n"
                        
                    # Compare cleanup policy
                    current_cleanup = current_config.get('cleanupPolicy')
                    target_cleanup = target_config.get('cleanupPolicy')
                    if current_cleanup != target_cleanup:
                        output += f"    Cleanup Policy: {current_cleanup} -> {target_cleanup}\n"
                        
            output += "\n"
            
        # Handle deleted topics
        deleted_topics = result.get('deletedTopics', [])
        if deleted_topics and len(deleted_topics) > 0:
            output += "Topics that would be deleted:\n"
            
            for topic in deleted_topics:
                name = topic.get('name')
                output += f"- {name}\n"
                
            output += "\n"
            
        return output
    except QuixApiError as e:
        return f"Error checking imported topics refresh: {str(e)}"

async def refresh_imported_topics(ctx: Context) -> str:
    """Refresh imported topics to sync with external changes.
    """
    try:
        result = await make_quix_request(
            ctx,
            "POST",
            "{workspaceId}/topics/external/import/refresh"
        )
        
        if not result:
            return "No changes occurred from refreshing imported topics."
            
        output = "Changes from refreshing imported topics:\n\n"
        
        # Handle changed topics
        changed_topics = result.get('changedTopics', [])
        if changed_topics and len(changed_topics) > 0:
            output += "Topics that were changed:\n"
            
            for topic in changed_topics:
                name = topic.get('name')
                output += f"- {name}\n"
                
                current_config = topic.get('currentConfig')
                target_config = topic.get('targetConfig')
                
                if current_config and target_config:
                    output += "  Changes:\n"
                    
                    # Compare partitions
                    current_partitions = current_config.get('partitions')
                    target_partitions = target_config.get('partitions')
                    if current_partitions != target_partitions:
                        output += f"    Partitions: {current_partitions} -> {target_partitions}\n"
                        
                    # Compare replication factor
                    current_replication = current_config.get('replicationFactor')
                    target_replication = target_config.get('replicationFactor')
                    if current_replication != target_replication:
                        output += f"    Replication Factor: {current_replication} -> {target_replication}\n"
                        
                    # Compare retention in minutes
                    current_retention_mins = current_config.get('retentionInMinutes')
                    target_retention_mins = target_config.get('retentionInMinutes')
                    if current_retention_mins != target_retention_mins:
                        output += f"    Retention (minutes): {current_retention_mins} -> {target_retention_mins}\n"
                        
                    # Compare retention in bytes
                    current_retention_bytes = current_config.get('retentionInBytes')
                    target_retention_bytes = target_config.get('retentionInBytes')
                    if current_retention_bytes != target_retention_bytes:
                        output += f"    Retention (bytes): {current_retention_bytes} -> {target_retention_bytes}\n"
                        
                    # Compare cleanup policy
                    current_cleanup = current_config.get('cleanupPolicy')
                    target_cleanup = target_config.get('cleanupPolicy')
                    if current_cleanup != target_cleanup:
                        output += f"    Cleanup Policy: {current_cleanup} -> {target_cleanup}\n"
                        
            output += "\n"
            
        # Handle deleted topics
        deleted_topics = result.get('deletedTopics', [])
        if deleted_topics and len(deleted_topics) > 0:
            output += "Topics that were deleted:\n"
            
            for topic in deleted_topics:
                name = topic.get('name')
                output += f"- {name}\n"
                
            output += "\n"
            
        return output
    except QuixApiError as e:
        return f"Error refreshing imported topics: {str(e)}"

async def get_topic_metrics(ctx: Context) -> str:
    """Get metrics for all topics in your workspace.
    """
    try:
        metrics = await make_quix_request(
            ctx,
            "GET",
            "{workspaceId}/topics/metrics/all"
        )
        
        if not metrics:
            return "No topic metrics available."
            
        result = "Topic Metrics:\n\n"
        for metric in metrics:
            topic_id = metric.get('topicId')
            if topic_id:
                result += f"Topic ID: {topic_id}\n"
                
            # Core metrics
            bytes_in = metric.get('bytesInPerSecond')
            if bytes_in is not None:
                result += f"Bytes In/sec: {bytes_in}\n"
                
            bytes_out = metric.get('bytesOutPerSecond')
            if bytes_out is not None:
                result += f"Bytes Out/sec: {bytes_out}\n"
                
            values_persisted = metric.get('valuesPersistedPerSecond')
            if values_persisted is not None:
                result += f"Values Persisted/sec: {values_persisted}\n"
                
            # Streams metrics
            streams_persisted = metric.get('streamsPersisted')
            if streams_persisted and len(streams_persisted) > 0:
                result += "Streams Persisted:\n"
                for stream_id, values in streams_persisted.items():
                    result += f"  {stream_id}: {values} values/sec\n"
                    
            result += "-" * 40 + "\n"
            
        return result
    except QuixApiError as e:
        return f"Error retrieving topic metrics: {str(e)}"