import os
import json
import httpx
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import Message, UserMessage
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from the .env file
load_dotenv()

# --- Configuration ---

class QuixSettings(BaseSettings):
    """Loads configuration from environment variables."""
    model_config = SettingsConfigDict(env_prefix="QUIX_")
    pat_token: str = Field(..., description="Quix Personal Access Token.")

# --- MCP Server Setup ---

settings = QuixSettings()
mcp = FastMCP(
    name="Quix Topic Schema Inferer",
    instructions=(
        "This server provides a tool to analyze the data structure of a Kafka topic hosted on the Quix platform. "
        "When a user asks to understand, define, or infer the schema of a topic, you should use the 'infer_topic_schema' tool. "
        "You will need to ask the user for their Workspace ID and Topic ID if they are not provided."
    ),
    host="0.0.0.0",
    port=80
)

# --- Tool Definition ---

@mcp.tool(
    name="infer_topic_schema",
    title="Infer Quix Topic Schema"
)
async def infer_topic_schema(
    workspace_id: str = Field(
        ...,
        description="The unique identifier for the Quix workspace. It typically follows the format 'organization-project-environment'.",
        examples=["acme-corp-iot-prod"],
        # Corrected from 'regex' to 'pattern'
        pattern=r"^[a-z0-9-]+$"
    ),
    topic_id: str = Field(
        ...,
        description="The unique identifier for the Quix topic within the workspace. It typically includes the workspace ID as a prefix.",
        examples=["acme-corp-iot-prod-sensor-data"],
        # Corrected from 'regex' to 'pattern'
        pattern=r"^[a-z0-9-]+$"
    )
) -> List[Message]:
    """
    Use this tool to infer the JSON schema of a Quix topic by analyzing its 100 
    most recent messages. You must provide the workspace_id and topic_id. 
    The tool will return the message sample to you, which you should then use 
    to generate the schema.
    """
    api_url = f'https://reader-{workspace_id}.demo.quix.io/query-messages'
    headers = {
        'accept': 'application/json',
        'Authorization': f'bearer {settings.pat_token}',
        'Content-Type': 'application/json'
    }
    params = {'initialTimeoutInSeconds': 30}
    payload = {
        "topicId": topic_id,
        "partition": 0,
        "offset": "Newest",
        "maxResults": 100
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, headers=headers, params=params, json=payload, timeout=45)
            response.raise_for_status()
            messages_data = response.json()

    except httpx.HTTPStatusError as e:
        error_details = e.response.text
        return [UserMessage(f"API Error: Failed to fetch data from Quix. Status: {e.response.status_code}. Details: {error_details}")]
    except Exception as e:
        return [UserMessage(f"An unexpected error occurred: {str(e)}")]

    system_prompt = (
        "The following data is a sample of 100 most recent messages from a Kafka topic, "
        "can you use this sample to infer the overall schema of the topic while noting any exceptions? "
        "Note that later, we'll be using this schema definition to write the data into an external destination, "
        "so it needs to be precise. Please return the result in JSON schema format, and ask the user to confirm "
        "that it looks correct."
    )

    data_sample_str = json.dumps(messages_data, indent=2, ensure_ascii=False)

    return [
        UserMessage(system_prompt),
        UserMessage(f"Here is the data sample:\n\n```json\n{data_sample_str}\n```")
    ]

# --- Server Execution ---

if __name__ == "__main__":
    mcp.run(transport="streamable-http")