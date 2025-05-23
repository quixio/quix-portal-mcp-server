# Quix Portal MCP Server

This is an MCP (Model Context Protocol) server that provides access to the Quix Platform API. The server supports interaction with various Quix Platform features, including Deployments, Topics, and Library operations.

## Overview

This MCP server allows AI agents and applications to interact with the Quix Platform through natural language. It exposes a set of tools for managing deployments, topics, and working with the Quix library of sample applications.

The server communicates using the Server-Sent Events (SSE) protocol, making it compatible with MCP clients like Claude Desktop, MCP Inspector, or any other MCP-compatible client.

## Requirements

- Python 3.9+
- MCP Python SDK
- httpx
- uvicorn
- starlette
- python-dotenv

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The MCP server requires these environment variables:

- `QUIX_TOKEN`: Your Quix Personal Access Token (PAT)
- `QUIX_BASE_URL`: The base URL of your Quix Portal (e.g., `https://portal-myenv.platform.quix.io/`)
- `QUIX_WORKSPACE`: Your Quix Workspace ID (required for topics and deployments)

You can set these environment variables in your shell:

```bash
export QUIX_TOKEN=your_quix_token
export QUIX_BASE_URL=https://portal-myenv.platform.quix.io/
export QUIX_WORKSPACE=your_workspace_id
```

Or you can create a `.env` file in the root directory with these variables:

```
QUIX_TOKEN=your_quix_token
QUIX_BASE_URL=https://portal-myenv.platform.quix.io/
QUIX_WORKSPACE=your_workspace_id
```

You can also pass them as command-line arguments when starting the server.

## Usage

### Starting the server

Specify a particular server to run:

```bash
python quix_server_application.py
python quix_server_deployments.py
python quix_server_library.py
python quix_server_topics.py
```

If you haven't set the environment variables, you can pass them as arguments:

```bash
python quix_server_application.py --quix-token your_quix_token --quix-base-url https://portal-myenv.platform.quix.io/ --quix-workspace your_workspace_id
```

By default, the servers run on:
- Library server: `0.0.0.0:8080`
- Topics server: `0.0.0.0:8081`
- Deployments server: `0.0.0.0:8082`

You can change the base port using the `--port` argument:

```bash
python quix_server_application.py --port 9000
```

### Connecting with an MCP client

You can connect to any of the servers using an MCP client that supports SSE, such as:

1. **MCP Inspector**:
   ```bash
   # For library server:
   mcp connect sse http://localhost:8080/sse
   # For topics server:
   mcp connect sse http://localhost:8081/sse
   # For deployments server:
   mcp connect sse http://localhost:8082/sse
   ```

2. **Claude Desktop**: Create a custom server connection to the appropriate endpoint:
   - Library server: `http://localhost:8080/sse`
   - Topics server: `http://localhost:8081/sse`
   - Deployments server: `http://localhost:8082/sse`

3. **Programmatically**: Use the MCP Python SDK's client functionality to connect to the SSE endpoint

## Available Tools

### Deployment Tools

- `get_deployments`: Get all deployments in the workspace
- `get_deployment`: Get details of a specific deployment
- `create_deployment`: Create a new deployment
- `update_deployment`: Update an existing deployment
- `delete_deployment`: Delete a deployment
- `start_deployment`: Start a deployment
- `stop_deployment`: Stop a deployment
- `cancel_deployment_update`: Cancel a deployment update
- `retry_deployment_update`: Retry a deployment update
- `get_deployment_replicas`: Get the replicas of a deployment
- `get_deployment_secret_keys`: Get deployment secrets keys
- `update_deployments`: Update deployments in the workspace
- `get_deployment_logs`: Get logs for a deployment
- `get_deployment_logs_by_page`: Get logs for a deployment by page
- `get_deployment_historical_logs`: Get historical logs for a deployment
- `get_deployment_historical_log_stats`: Get historical log stats for a deployment
- `download_deployment_logs`: Download logs for a deployment
- `get_deployment_runs`: Get historical runs for a deployment
- `get_deployment_run_logs`: Get logs for a specific deployment run

### Topic Tools

- `get_topics`: List all topics in your workspace
- `get_topic`: Get details of a specific topic
- `create_topic`: Create a new Kafka topic
- `update_topic`: Update a topic's configuration
- `delete_topic`: Delete a topic
- `clean_topic`: Clean the contents of a topic
- `clear_topic_error`: Clear the error state of a topic
- `get_default_topic_config`: Get the default topic configuration
- `search_topics`: Search for topics across workspaces
- `get_linkable_topics`: Get all linkable topics
- `get_external_topics`: Get all available external topics
- `check_imported_topics_refresh`: Check what would happen if you refresh imported topics
- `refresh_imported_topics`: Refresh imported topics to sync with external changes
- `get_topic_metrics`: Get metrics for all topics

### Library Tools

- `query_library`: Query the Quix library for items using filters
- `get_library_item_details`: Get detailed information about a library item
- `get_library_file_content`: Get the content of a file within a library item
- `get_library_icon`: Get the icon for a library item
- `get_library_configuration`: Get library configuration
- `get_library_languages`: Get a list of available programming languages in the Quix library
- `get_library_tags`: Get information about available tags in the Quix library
- `create_application_from_library`: Create a new application from a library item
- `create_deployment_from_library`: Create a new deployment from a library item
- `get_library_zip`: Download a library item as a ZIP file

## Example Conversations

Here are some example conversations you might have with the Quix Portal MCP servers:

**Working with deployments:**
```
> List all deployments in my workspace
> Show me details for deployment with ID "my-deployment-123"
> Start the deployment with ID "my-deployment-123"
> Show me the logs for deployment "my-deployment-123"
> Create a new deployment called "my-service" from application "my-app-id" with 2 replicas
```

**Working with topics:**
```
> List all topics in my workspace
> Show me details for topic "my-data-stream"
> Create a new topic called "sensor-readings" with 3 partitions
> Clean the topic "test-topic"
```

**Working with the library:**
```
> Show me Python library items with the "source" tag
> Get details for library item "12345"
> Show me the code for the main.py file in library item "12345"
> Create a deployment from library item "12345" called "my-connector"
```

## Error Handling

The server provides detailed error messages when API calls fail, including HTTP status codes and error descriptions. Authentication errors, invalid parameters, and other API errors are handled gracefully and reported back to the client.

## Security Considerations

- The server requires a Quix Personal Access Token (PAT) for authentication.
- Sensitive information in API responses is redacted (e.g., secret environment variables).
- The server doesn't expose token values in logs or error messages.

## References

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Quix Platform Documentation](https://docs.quix.io/)