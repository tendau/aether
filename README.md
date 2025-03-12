# AI Agent Communication System

This system allows AI agents to communicate with each other over the Internet, facilitating a turn-based conversation between users through AI intermediaries.

## Components

- **Server**: HTTP server that broadcasts messages between agents using Server-Sent Events (SSE)
- **Local Agent**: Runs locally on a user's machine and interacts with both the user and remote agents through Azure OpenAI

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure the application:
   - Copy `.env.example` to `.env` and modify as needed
   - Set your Azure OpenAI API key and endpoint in the `.env` file
   - Set the server address in the config file

3. Start the server:
   ```
   python run_server.py
   ```

4. Start the local agent on each machine:
   ```
   python run_agent.py
   ```

## Usage

1. A user instructs their local agent
2. The agent processes the input using Azure OpenAI
3. The agent broadcasts the message to all other connected agents
4. Other agents receive the message and display it to their local users
5. Users can respond, continuing the conversation

## Architecture

- The system uses Autogen with Azure OpenAI for AI agent functionality
- Communication between agents is handled via Server-Sent Events (SSE)
- Messages are broadcast to all connected agents except the sender

## Azure Deployment

### Server Deployment

The server can be deployed to Azure App Service:

1. Create an Azure App Service with Python runtime
2. Set the following environment variables in the App Service configuration:
   - SERVER_HOST
   - SERVER_PORT
3. Deploy the code to the App Service
4. Update the `SERVER_ADDRESS` in the local `.env` files to point to your deployed App Service URL

### Local Agent Configuration

For the local agents, configure:

1. Azure OpenAI resource settings:
   - `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
   - `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
   - `AZURE_OPENAI_DEPLOYMENT_NAME`: The name of your deployed model in Azure OpenAI
2. `AGENT_NAME`: Unique identifier for each agent
3. `SERVER_ADDRESS`: The URL of the deployed server 