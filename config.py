import os
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Server configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8765"))

# Agent configuration
AGENT_NAME = os.getenv("AGENT_NAME", "Agent_Default")

# Azure OpenAI configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")

# Connection settings
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", f"http://{SERVER_HOST}:{SERVER_PORT}")

def validate_config():
    """Validate that all required configuration variables are set."""
    missing = []
    
    if not AZURE_OPENAI_API_KEY:
        missing.append("AZURE_OPENAI_API_KEY")
    
    if not AZURE_OPENAI_ENDPOINT:
        missing.append("AZURE_OPENAI_ENDPOINT")
    
    if not AZURE_OPENAI_DEPLOYMENT_NAME:
        missing.append("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    if missing:
        raise ValueError(f"Missing required configuration variables: {', '.join(missing)}") 