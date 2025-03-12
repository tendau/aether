#!/usr/bin/env python3
"""
Run script for the Server-Sent Events based agent communication server.
This server can be deployed to Azure App Service.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("run_server")

def main():
    # Check if .env file exists (for local development)
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            logger.warning("No .env file found. Copying from .env.example...")
            
            # Copy .env.example to .env
            with open('.env.example', 'r') as example_file:
                example_content = example_file.read()
            
            with open('.env', 'w') as env_file:
                env_file.write(example_content)
            
            logger.info("Created .env file from example. Please edit it with your configuration.")
        else:
            logger.warning("No .env or .env.example file found. Will try to use environment variables directly.")
    
    # Check for Azure environment variables
    if 'APPSETTING_WEBSITE_SITE_NAME' in os.environ:
        logger.info("Running in Azure App Service")
        # When running in Azure App Service, the app service settings will be loaded
        # as environment variables automatically
    
    # Run the server
    logger.info("Starting the SSE server...")
    
    try:
        from server import main as server_main
        server_main()
    except ImportError as e:
        logger.error(f"Failed to import the server module: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running the server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 