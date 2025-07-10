# MCP Server for Quix Topic Schema Inference

This MCP server provides a tool that allows an AI client to infer the JSON schema of a Kafka topic hosted on the Quix platform. It fetches a sample of the 100 most recent messages from a specified topic and presents them to the AI with a prompt to generate a schema.

## Features

- **Dynamic Schema Inference**: Connects to any Quix workspace and topic specified by the client.
- **Secure Authentication**: Uses a Personal Access Token (PAT) from environment variables to authenticate with the Quix API.
- **Modern Transport**: Uses the Streamable HTTP transport, with SSE support for older clients.
- **Containerized**: Includes a Dockerfile for easy cloud deployment.

## Prerequisites

- Docker installed on your machine.
- A Quix account with a Personal Access Token (PAT).
- A Quix workspace and topic you want to analyze.

## Setup

1.  **Clone the repository** (if you haven't already).

2.  **Create a `.env` file**:
    Rename the `.env.example` file to `.env` and add your Quix Personal Access Token:

    ```
    QUIX_PAT_TOKEN="p_your_token_from_quix_portal"
    ```

## Building the Docker Image

From the root directory of this server, run the following command to build the Docker image:

```bash
docker build -t quix-schema-inferer .