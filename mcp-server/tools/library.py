"""Quix Library MCP tools."""

import os
from typing import Any, Optional, Dict, List
from mcp.server.fastmcp import Context
from .base import make_quix_request, QuixApiError

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
    try:
        # Build the request payload according to the LibraryListViewRequest schema
        payload = {}
        
        if languages:
            payload["languages"] = languages
            
        if tags:
            payload["tags"] = tags
            
        if page_index is not None and page_length is not None:
            payload["pageIndex"] = page_index
            payload["pageLength"] = page_length
            
        if connectors is not None:
            payload["connectors"] = connectors
            
        if auxiliary_services is not None:
            payload["auxiliaryServices"] = auxiliary_services
        
        # Make the request to the library query endpoint
        items = await make_quix_request(
            ctx,
            "POST",
            "library/query",
            json=payload
        )
        
        if not items:
            return "No library items found matching the criteria."
        
        result = "Library Items:\n\n"
        for item in items:
            result += f"ID: {item.get('itemId')}\n"
            result += f"Name: {item.get('name')}\n"
            
            # Add language if present
            language = item.get('language')
            if language:
                result += f"Language: {language}\n"
                
            # Add tags if present
            tags = item.get('tags')
            if tags and len(tags) > 0:
                result += f"Tags: {', '.join(tags)}\n"
                
            # Add description if present
            description = item.get('shortDescription')
            if description:
                # Truncate long descriptions
                if len(description) > 100:
                    description = description[:97] + "..."
                result += f"Description: {description}\n"
                
            # Add highlighted status if true
            is_highlighted = item.get('isHighlighted')
            if is_highlighted:
                result += f"Highlighted: {is_highlighted}\n"
                
            # Add connector/service status if present
            is_connector = item.get('isConnector')
            if is_connector:
                result += f"Connector: Yes\n"
                
            is_auxiliary_service = item.get('isAuxiliaryService')
            if is_auxiliary_service:
                result += f"Auxiliary Service: Yes\n"
                
            # Add deploy readiness if present
            deployable = item.get('deployable')
            if deployable:
                result += f"Deployable: Yes\n"
                
            deploy_ready = item.get('deployReady')
            if deploy_ready:
                result += f"Deploy Ready: Yes\n"
                
            result += "-" * 40 + "\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

async def get_library_item_details(ctx: Context, item_id: str) -> str:
    """Get detailed information about a specific library item.
    
    Args:
        item_id: The ID of the library item to retrieve details for
    """
    try:
        details = await make_quix_request(
            ctx,
            "GET",
            f"library/{item_id}/details"
        )
        
        if not details:
            return f"No library item found with ID {item_id}."
        
        result = "Library Item Details:\n\n"
        result += f"ID: {details.get('itemId')}\n"
        result += f"Name: {details.get('name')}\n"
        
        # Add language if present
        language = details.get('language')
        if language:
            result += f"Language: {language}\n"
            
        # Add tags if present
        tags = details.get('tags')
        if tags and len(tags) > 0:
            result += f"Tags: {', '.join(tags)}\n"
            
        # Add highlighted status if true
        is_highlighted = details.get('isHighlighted')
        if is_highlighted:
            result += f"Highlighted: {is_highlighted}\n"
            
        # Add display order if present
        display_order = details.get('displayOrder')
        if display_order is not None:
            result += f"Display Order: {display_order}\n"
            
        # Add descriptions if present
        short_description = details.get('shortDescription')
        if short_description:
            result += f"Short Description: {short_description}\n"
            
        long_description = details.get('longDescription')
        if long_description:
            result += f"Long Description: {long_description}\n"
            
        # Add URL if present
        url = details.get('url')
        if url:
            result += f"URL: {url}\n"
            
        # Add connector/service status if present
        is_connector = details.get('isConnector')
        if is_connector:
            result += f"Connector: Yes\n"
            
        is_auxiliary_service = details.get('isAuxiliaryService')
        if is_auxiliary_service:
            result += f"Auxiliary Service: Yes\n"
            
        # Add deploy info if present
        deployable = details.get('deployable')
        if deployable:
            result += f"Deployable: Yes\n"
            
        deploy_ready = details.get('deployReady')
        if deploy_ready:
            result += f"Deploy Ready: Yes\n"
            
        # Add entry points if present
        entry_point = details.get('entryPoint')
        if entry_point:
            result += f"Entry Point: {entry_point}\n"
            
        run_entry_point = details.get('runEntryPoint')
        if run_entry_point:
            result += f"Run Entry Point: {run_entry_point}\n"
            
        default_file = details.get('defaultFile')
        if default_file:
            result += f"Default File: {default_file}\n"
            
        # Add timestamps
        created_at = details.get('createdAt')
        if created_at:
            result += f"Created At: {created_at}\n"
            
        updated_at = details.get('updatedAt')
        if updated_at:
            result += f"Updated At: {updated_at}\n"
            
        # Add files if present
        files = details.get('files')
        if files and len(files) > 0:
            result += "\nFiles:\n"
            for file in files:
                result += f"- {file}\n"
                
        # Add variables if present
        variables = details.get('variables')
        if variables and len(variables) > 0:
            result += "\nVariables:\n"
            for var in variables:
                result += f"• {var.get('name')} ({var.get('inputType')})\n"
                
                description = var.get('description')
                if description:
                    result += f"  Description: {description}\n"
                    
                default_value = var.get('defaultValue')
                if default_value:
                    result += f"  Default Value: {default_value}\n"
                    
                required = var.get('required')
                result += f"  Required: {required}\n"
                
                multiline = var.get('multiline')
                if multiline:
                    result += f"  Multiline: {multiline}\n"
                    
                result += "\n"
                
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

async def get_library_file_content(ctx: Context, item_id: str, file_path: str, placeholder_replacements: Optional[Dict[str, str]] = None) -> str:
    """Get the content of a specific file within a library item.
    
    Args:
        item_id: The ID of the library item
        file_path: The path of the file within the library item
        placeholder_replacements: Optional dictionary of placeholder replacements (e.g. {"PLACEHOLDER": "value"})
    """
    try:
        # Build the request payload according to the LibraryFileContentRequest schema
        payload = {
            "filePath": file_path
        }
        
        if os.environ.get("QUIX_WORKSPACE"):
            payload["workspaceId"] = os.environ.get("QUIX_WORKSPACE")
            
        if placeholder_replacements:
            payload["placeholderReplacements"] = placeholder_replacements
        
        content = await make_quix_request(
            ctx,
            "POST",
            f"library/{item_id}/files/content",
            json=payload
        )
        
        if not content:
            return f"No content found for file {file_path} in library item {item_id}."
        
        return f"File: {file_path}\n\n{content}"
    except QuixApiError as e:
        return f"Error: {str(e)}"

async def get_library_icon(ctx: Context, item_id: str) -> str:
    """Get the icon for a library item.
    
    Args:
        item_id: The ID of the library item
    """
    try:
        icon = await make_quix_request(
            ctx,
            "GET",
            f"library/{item_id}/icon"
        )
        
        if not icon:
            return f"No icon found for library item {item_id}."
        
        return f"Icon retrieved for library item {item_id}."
    except QuixApiError as e:
        return f"Error: {str(e)}"

async def get_library_configuration(ctx: Context, source: Optional[str] = None) -> str:
    """Get library configuration.
    
    Args:
        source: Optional source parameter
    """
    try:
        params = {}
        if source:
            params["source"] = source
            
        config = await make_quix_request(
            ctx,
            "GET",
            "library/configuration",
            params=params
        )
        
        if not config:
            return "No library configuration found."
        
        result = "Library Configuration:\n\n"
        
        git_url = config.get('gitUrl')
        if git_url:
            result += f"Git URL: {git_url}\n"
            
        branch = config.get('branch')
        if branch:
            result += f"Branch: {branch}\n"
            
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

async def get_library_languages(ctx: Context, connectors: Optional[bool] = None, auxiliary_services: Optional[bool] = None) -> str:
    """Get a list of available programming languages in the Quix library.
    
    Args:
        connectors: Optional boolean to filter for connector items only (True) or exclude connectors (False)
        auxiliary_services: Optional boolean to filter for auxiliary service items only (True) or exclude them (False)
    """
    try:
        params = {}
        if connectors is not None:
            params["connectors"] = str(connectors).lower()
            
        if auxiliary_services is not None:
            params["auxiliaryServices"] = str(auxiliary_services).lower()
            
        languages = await make_quix_request(
            ctx,
            "GET",
            "library/languages",
            params=params
        )
        
        if not languages or len(languages) == 0:
            return "No programming languages found in the library."
        
        result = "Available languages in the Quix library:\n\n"
        for lang in languages:
            result += f"- {lang}\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

async def get_library_tags(ctx: Context, connectors: Optional[bool] = None, auxiliary_services: Optional[bool] = None) -> str:
    """Get information about available tags in the Quix library.
    
    Args:
        connectors: Optional boolean to filter for connector items only (True) or exclude connectors (False)
        auxiliary_services: Optional boolean to filter for auxiliary service items only (True) or exclude them (False)
    """
    try:
        params = {}
        if connectors is not None:
            params["connectors"] = str(connectors).lower()
            
        if auxiliary_services is not None:
            params["auxiliaryServices"] = str(auxiliary_services).lower()
            
        tag_groups = await make_quix_request(
            ctx,
            "GET",
            "library/tags",
            params=params
        )
        
        if not tag_groups or len(tag_groups) == 0:
            return "No tags found in the library."
        
        result = "Available tags in the Quix library:\n\n"
        for group in tag_groups:
            group_name = group.get('tagGroup')
            tags = group.get('tags', [])
            
            if group_name:
                result += f"Group: {group_name}\n"
                
            if tags and len(tags) > 0:
                for tag in tags:
                    result += f"- {tag}\n"
                
            result += "\n"
        
        return result
    except QuixApiError as e:
        return f"Error: {str(e)}"

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
    try:
        # Ensure workspace ID is available
        workspace_id = os.environ.get("QUIX_WORKSPACE")
        if not workspace_id:
            return "Missing QUIX_WORKSPACE environment variable. Please set your Quix Workspace ID."
            
        # Build the request payload according to the CreateApplicationFromLibraryRequest schema
        payload = {
            "workspaceId": workspace_id,
            "applicationName": application_name,
            "libraryItemId": library_item_id
        }
        
        if path:
            payload["path"] = path
            
        if placeholders:
            payload["placeholders"] = placeholders
            
        if environment_variables:
            payload["environmentVariables"] = environment_variables
        
        application = await make_quix_request(
            ctx,
            "POST",
            "library/application",
            json=payload
        )
        
        if not application:
            return "Failed to create application from library item."
        
        application_id = application.get('applicationId')
        name = application.get('name')
        return f"Successfully created application '{name}' with ID: {application_id} from library item {library_item_id}."
    except QuixApiError as e:
        return f"Error creating application: {str(e)}"

async def create_deployment_from_library(
    ctx: Context,
    library_item_id: str,
    deployment_name: str,
    create_application: bool = False,
    environment_variables: Optional[Dict[str, str]] = None
) -> str:
    """Create a new deployment from a library item.
    
    Args:
        library_item_id: The ID of the library item to create a deployment from
        deployment_name: The name for the new deployment
        create_application: Whether to also create an application from the deployment (default: False)
        environment_variables: Optional dictionary of environment variables (e.g. {"ENV_VAR": "value"})
    """
    try:
        # Ensure workspace ID is available
        workspace_id = os.environ.get("QUIX_WORKSPACE")
        if not workspace_id:
            return "Missing QUIX_WORKSPACE environment variable. Please set your Quix Workspace ID."
            
        # Build the request payload according to the CreateDeploymentFromLibraryRequest schema
        payload = {
            "workspaceId": workspace_id,
            "deploymentName": deployment_name,
            "libraryItemId": library_item_id,
            "createApplication": create_application
        }
        
        if environment_variables:
            payload["environmentVariables"] = environment_variables
        
        deployment = await make_quix_request(
            ctx,
            "POST",
            "library/deployment",
            json=payload
        )
        
        if not deployment:
            return "Failed to create deployment from library item."
        
        deployment_id = deployment.get('deploymentId')
        return f"Successfully created deployment '{deployment_name}' with ID: {deployment_id} from library item {library_item_id}."
    except QuixApiError as e:
        return f"Error creating deployment: {str(e)}"

async def get_library_zip(
    ctx: Context,
    item_id: str,
    placeholder_replacements: Optional[Dict[str, str]] = None
) -> str:
    """Download a library item as a ZIP file.
    
    Args:
        item_id: The ID of the library item to download
        placeholder_replacements: Optional dictionary of placeholder replacements (e.g. {"PLACEHOLDER": "value"})
    """
    try:
        # Build the request payload according to the LibraryZipContentRequest schema
        payload = {}
        
        if os.environ.get("QUIX_WORKSPACE"):
            payload["workspaceId"] = os.environ.get("QUIX_WORKSPACE")
            
        if placeholder_replacements:
            payload["placeholderReplacements"] = placeholder_replacements
        
        zip_content = await make_quix_request(
            ctx,
            "POST",
            f"library/{item_id}/zip",
            json=payload
        )
        
        if not zip_content:
            return f"Failed to download ZIP for library item {item_id}."
        
        return f"Successfully downloaded ZIP for library item {item_id}."
    except QuixApiError as e:
        return f"Error downloading ZIP: {str(e)}"