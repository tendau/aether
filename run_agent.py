#!/usr/bin/env python3
"""
Run script for the local AI agent component that uses Azure OpenAI.
"""

import os
import sys
import logging
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("run_agent")

async def main():
    # Check if .env file exists
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            logger.warning("No .env file found. Copying from .env.example...")
            
            # Copy .env.example to .env
            with open('.env.example', 'r') as example_file:
                example_content = example_file.read()
            
            with open('.env', 'w') as env_file:
                env_file.write(example_content)
            
            logger.info("Created .env file from example. Please edit it with your configuration.")
            logger.info("Please set your AZURE_OPENAI_API_KEY and other settings in the .env file.")
            
            # Prompt user to update the .env file
            user_input = input("Would you like to proceed with default settings? (y/n): ")
            if user_input.lower() != 'y':
                logger.info("Please update the .env file and run the script again.")
                sys.exit(0)
        else:
            logger.error("No .env or .env.example file found. Please create a .env file.")
            sys.exit(1)
    
    # Check for Azure OpenAI configuration
    from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME
    
    if not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_DEPLOYMENT_NAME:
        logger.error("Azure OpenAI configuration is incomplete. Please check your .env file.")
        logger.error("Make sure AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT_NAME are set.")
        sys.exit(1)
    
    # Run the local agent
    logger.info("Starting the local agent with Azure OpenAI...")
    
    try:
        from local_agent import main as agent_main
        await agent_main()
    except ImportError as e:
        logger.error(f"Failed to import the local_agent module: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running the local agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 