import asyncio
import json
import logging
import os
import random
import sys
from typing import Dict, List, Optional

import autogen
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json

from sse_client import SSEClient
import config

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("local_agent")

class RemoteAgentConnector:
    """Connects the local Autogen agent with remote agents via SSE."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.sse_client = SSEClient(agent_id, config.SERVER_ADDRESS)
        self.user_proxy: Optional[UserProxyAgent] = None
        self.assistant: Optional[AssistantAgent] = None
        self.message_queue = asyncio.Queue()
        self.running = False
    
    async def setup(self):
        """Set up the SSE connection and autogen agents."""
        # Register with the server
        registered = await self.sse_client.register()
        if not registered:
            logger.error("Failed to register with server")
            return False
        
        # Add message handler
        self.sse_client.add_message_handler(self.handle_incoming_message)
        
        # Start listening for messages
        await self.sse_client.start_listening()
        
        # Set up Autogen agents
        self.setup_agents()
        
        self.running = True
        return True
    
    def setup_agents(self):
        """Set up Autogen agents with Azure OpenAI."""
        # Configure Azure OpenAI
        config_list = [{
            "model": config.AZURE_OPENAI_DEPLOYMENT_NAME,
            "api_key": config.AZURE_OPENAI_API_KEY,
            "base_url": f"{config.AZURE_OPENAI_ENDPOINT}",
            "api_version": config.AZURE_OPENAI_API_VERSION,
            "api_type": "azure",
        }]
        
        llm_config = {
            "config_list": config_list,
        }
        
        # Create an assistant agent
        self.assistant = AssistantAgent(
            name=self.agent_id,
            llm_config=llm_config,
            system_message=f"""You are an AI assistant named {self.agent_id} that can communicate with other AI agents.
Your goal is to help your user by collaborating with other agents when necessary.
Keep responses helpful, concise, and relevant to the user's needs."""
        )
        
        # Create a user proxy agent
        self.user_proxy = UserProxyAgent(
            name="user",
            human_input_mode="ALWAYS",
            code_execution_config={"use_docker": False},
        )
    
    async def handle_incoming_message(self, data: Dict):
        """Handle incoming SSE messages."""
        if data.get('type') == 'message':
            sender_id = data.get('from')
            content = data.get('content')
            
            if not sender_id or not content:
                return
            
            # Add to message queue for processing
            await self.message_queue.put({
                'sender': sender_id,
                'content': content
            })
    
    async def process_messages(self):
        """Process incoming messages from the queue."""
        while self.running:
            try:
                message = await self.message_queue.get()
                
                sender = message['sender']
                content = message['content']
                
                # Display the message to the user
                print(f"\n=== Message from {sender} ===")
                print(content['message'])
                print("===========================\n")
                
                # Allow the user to respond
                response = input("Enter your response (or 'skip' to ignore): ")
                
                if response.lower() != 'skip':
                    # Send the response through the assistant
                    conversation = self.assistant.initiate_chat(
                        self.user_proxy,
                        message=f"A message was received from {sender}. The message is: '{content['message']}'. "
                               f"My user wants to respond with: '{response}'. "
                               f"Formulate a proper response to send back to {sender}."
                    )
                    
                    # Get the last message from the assistant
                    last_message = self.assistant.chat_messages[self.user_proxy][-1]["content"]
                    
                    # Send the response back
                    await self.send_message(last_message)
                
                self.message_queue.task_done()
            
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def send_message(self, message: str) -> bool:
        """Send a message to all other agents."""
        content = {
            'message': message
        }
        
        result = await self.sse_client.send_message(content)
        return result
    
    async def start_conversation(self):
        """Start a conversation by broadcasting a message to all other agents."""
        # Get message from user
        user_input = input("\nEnter your message to broadcast to all agents: ")
        
        # Process through assistant
        conversation = self.assistant.initiate_chat(
            self.user_proxy,
            message=f"My user wants to send a message to all other AI agents. "
                   f"The message is: '{user_input}'. Please formulate this into a proper message "
                   f"that can be broadcast to other agents."
        )
        
        # Get the last message from the assistant
        last_message = self.assistant.chat_messages[self.user_proxy][-1]["content"]
        
        # Send the message
        sent = await self.send_message(last_message)
        
        if sent:
            print("Message broadcast to all other agents")
        else:
            print("Failed to broadcast message")
    
    async def run(self):
        """Run the main application loop."""
        if not self.running:
            success = await self.setup()
            if not success:
                return
        
        # Start message processor
        message_processor = asyncio.create_task(self.process_messages())
        
        try:
            while True:
                print("\nOptions:")
                print("1. Start conversation (broadcast to all agents)")
                print("2. List connected agents")
                print("3. Exit")
                
                choice = await asyncio.to_thread(input, "\nEnter your choice (1-3): ")
                
                if choice == '1':
                    await self.start_conversation()
                
                elif choice == '2':
                    agents = await self.sse_client.list_agents()
                    print("\nConnected agents:")
                    for agent_id in agents:
                        if agent_id == self.agent_id:
                            print(f"* {agent_id} (You)")
                        else:
                            print(f"* {agent_id}")
                
                elif choice == '3':
                    break
                
                else:
                    print("Invalid choice. Please try again.")
        
        finally:
            # Clean up
            self.running = False
            message_processor.cancel()
            await self.sse_client.close()

async def main():
    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Create and run the connector

    #get random id for agent_id
    agent_id = random.randint(1000, 9999)
    connector = RemoteAgentConnector(str(agent_id))
    await connector.run()

if __name__ == "__main__":
    asyncio.run(main()) 