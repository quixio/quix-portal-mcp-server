# Quix Portal MCP Server

A Model Context Protocol (MCP) server that provides access to Quix Portal API operations for managing workspaces, applications, deployments, library items, and Kafka topics.

## Architecture

This project uses a modular architecture inspired by the MCP server for Shortcut. The server is organized into separate tool modules that are imported by a unified main server.

### Directory Structure

```
quix-portal-mcp/
├── server.py                    # Main unified MCP server
├── tools/                       # Modular tool implementations
│   ├── __init__.py              # Tools package
│   ├── base.py                  # Shared utilities and API client
│   ├── applications.py          # Application management tools
│   ├── deployments.py           # Deployment management tools
│   ├── library.py               # Library item tools
│   ├── topics.py                # Kafka topic management tools
│   └── workspaces.py            # Workspace management tools
├── test_imports.py              # Import validation test
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

### Legacy Structure (Deprecated)

The following files are the original individual MCP servers and are now deprecated in favor of the unified server:

- `quix_server_application.py` (replaced by `tools/applications.py`)
- `quix_server_deployments.py` (replaced by `tools/deployments.py`)
- `quix_server_library.py` (replaced by `tools/library.py`)
- `quix_server_topics.py` (replaced by `tools/topics.py`)
- `main.py` (replaced by `server.py`)

## Setup

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
QUIX_TOKEN=your_personal_access_token
QUIX_BASE_URL=https://portal-myenv.platform.quix.io/
QUIX_WORKSPACE=your_workspace_id
```

Alternatively, you can pass these as command-line arguments when starting the server.

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables (see above)

3. Test the installation:
```bash
python3 test_imports.py
```

## Usage

### Starting the Server

Run the unified MCP server:

```bash
python3 server.py
```

Or with custom configuration:

```bash
python3 server.py --host 0.0.0.0 --port 8080 --quix-token YOUR_TOKEN --quix-base-url YOUR_URL --quix-workspace YOUR_WORKSPACE
```

### Command Line Arguments

- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to listen on (default: 8080)
- `--quix-token`: Quix Personal Access Token (overrides env var)
- `--quix-base-url`: Quix Portal Base URL (overrides env var)
- `--quix-workspace`: Quix Workspace ID (overrides env var)
- `--env-file`: Path to custom .env file

## Available Tools

### Workspace Management

- `list_workspaces` - List all workspaces for the organization
- `get_workspace` - Get details of a specific workspace
- `create_workspace` - Create a new workspace V2
- `get_workspace_variables` - Get workspace environment variables
- `set_workspace_variables` - Set workspace environment variables
- `get_workspace_yaml` - Get the workspace descriptor YAML
- `update_workspace_yaml` - Update the workspace descriptor YAML
- `get_workspace_sync_status` - Check workspace sync status with repository
- `sync_workspace` - Sync workspace with repository (supports dry-run)
- `create_workspace_branch` - Create a new git branch in the workspace
- `switch_workspace_branch` - Switch to a different git branch
- `create_workspace_tag` - Create a new git tag
- `delete_workspace_tag` - Delete a git tag
- `get_workspace_commits` - Get commit history for the workspace
- `get_workspace_commit` - Get details of a specific git commit by reference
- `pull_workspace` - Pull latest changes from remote repository
- `push_workspace` - Push latest changes to remote repository
- `enable_workspace` - Enable a workspace
- `disable_workspace` - Disable a workspace
- `delete_workspace` - Delete a workspace
- `rename_workspace` - Rename a workspace

### Application Management

- `list_applications` - List all applications in the workspace
- `get_application` - Get details of a specific application
- `create_application` - Create a new application
- `update_application` - Update an existing application
- `delete_application` - Delete an application
- `list_application_files` - List files in an application
- `duplicate_application` - Duplicate an existing application

### Deployment Management

- `get_deployments` - List deployments in the workspace
- `get_deployment` - Get details of a specific deployment
- `create_deployment` - Create a new deployment
- `start_deployment` - Start a deployment
- `stop_deployment` - Stop a deployment
- `delete_deployment` - Delete a deployment

### Library Management

- `query_library` - Search library items with filters
- `get_library_item_details` - Get detailed information about a library item
- `create_application_from_library` - Create application from library item

### Topic Management

- `get_topics` - List all topics in the workspace
- `get_topic` - Get details of a specific topic
- `create_topic` - Create a new Kafka topic
- `delete_topic` - Delete a topic

## Development

### Adding New Tools

1. Add your tool function to the appropriate module in `tools/`
2. Import and register the tool in `server.py` with the `@mcp.tool()` decorator
3. Update this README with the new tool documentation

### Testing

Run the import tests to verify the modular structure:

```bash
python3 test_imports.py
```

### Module Structure

Each tool module (`applications.py`, `deployments.py`, etc.) contains:

- Pure async functions without MCP decorators
- Import from `tools.base` for shared utilities
- Consistent error handling using `QuixApiError`
- Comprehensive type hints and documentation

The main `server.py` file:

- Imports all tool modules
- Applies `@mcp.tool()` decorators to expose functions as MCP tools
- Handles server configuration and startup
- Provides the SSE endpoint for MCP communication

## Configuration

### Quix Portal Setup

1. Get your Personal Access Token from the Quix Portal
2. Note your Portal URL (e.g., `https://portal-myenv.platform.quix.io/`)
3. Get your Workspace ID from the Portal

### MCP Client Configuration

Configure your MCP client to connect to this server at the specified host and port (default: `http://localhost:8080/sse`).

## Error Handling

All tools use consistent error handling:

- API errors are caught and returned as formatted error messages
- Missing environment variables are validated at startup
- Network timeouts are handled gracefully
- All errors include helpful context for debugging

## Contributing

When contributing to this project:

1. Follow the modular architecture pattern
2. Add new tools to appropriate modules in `tools/`
3. Register tools in `server.py`
4. Update documentation
5. Test your changes with `test_imports.py`