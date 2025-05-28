import os
import argparse
import dotenv
from typing import Dict, Any
from pathlib import Path

# Default configuration values
DEFAULT_CONFIG = {
    'host': '0.0.0.0',
    'port': 8000,
    'debug': False,
    'quix_token': None,
    'quix_base_url': 'https://portal.platform.quix.io',
    'quix_workspace': None
}

def load_config() -> Dict[str, Any]:
    """Load configuration with the following priority:
    1. Default values
    2. Environment variables
    3. .env file
    4. Command line arguments
    """
    # Start with default config
    config = DEFAULT_CONFIG.copy()
    
    # Load from .env file if it exists
    env_path = Path('.env')
    if env_path.exists():
        dotenv.load_dotenv(env_path)
    
    # Update from environment variables
    config['quix_token'] = os.environ.get('QUIX_TOKEN', config['quix_token'])
    config['quix_base_url'] = os.environ.get('QUIX_BASE_URL', config['quix_base_url'])
    config['quix_workspace'] = os.environ.get('QUIX_WORKSPACE', config['quix_workspace'])
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Quix Applications MCP Server')
    
    # Server configuration
    parser.add_argument('--host', type=str, help='Host to bind to')
    parser.add_argument('--port', type=int, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Quix configuration
    parser.add_argument('--quix-token', type=str, help='Quix Personal Access Token')
    parser.add_argument('--quix-base-url', type=str, help='Quix Portal Base URL')
    parser.add_argument('--quix-workspace', type=str, help='Quix Workspace ID')
    
    args = parser.parse_args()
    
    # Update config with command line arguments if provided
    if args.host is not None:
        config['host'] = args.host
    if args.port is not None:
        config['port'] = args.port
    if args.debug:
        config['debug'] = args.debug
    if args.quix_token is not None:
        config['quix_token'] = args.quix_token
    if args.quix_base_url is not None:
        config['quix_base_url'] = args.quix_base_url.rstrip('/')
    if args.quix_workspace is not None:
        config['quix_workspace'] = args.quix_workspace
    
    # Validate required configuration
    if not config['quix_token']:
        raise ValueError("QUIX_TOKEN must be provided via environment variable, .env file, or --quix-token argument")
    
    if not config['quix_workspace']:
        raise ValueError("QUIX_WORKSPACE must be provided via environment variable, .env file, or --quix-workspace argument")
    
    return config
