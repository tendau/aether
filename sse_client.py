import asyncio
import json
import logging
import time
from typing import Callable, Dict, List, Optional
import aiohttp

import config

logger = logging.getLogger("sse_client")

class SSEClient:
    """Client for Server-Sent Events communication with the server."""
    
    def __init__(self, agent_id: str, server_address: str):
        self.agent_id = agent_id
        self.server_address = server_address
        self.base_url = server_address.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_registered = False
        self.is_listening = False
        self.message_handlers: List[Callable] = []
        self.sse_task = None
    
    async def register(self) -> bool:
        """Register the agent with the server."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"{self.base_url}/register"
            async with self.session.post(url, json={'agent_id': self.agent_id}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'registered':
                        logger.info(f"Successfully registered as {self.agent_id}")
                        self.is_registered = True
                        return True
                    else:
                        logger.error(f"Registration response: {data}")
                        return False
                else:
                    logger.error(f"Registration failed with status {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False
    
    async def send_message(self, content: Dict) -> bool:
        """Send a message to be broadcast to all other agents."""
        if not self.is_registered:
            logger.error("Cannot send message: not registered")
            return False
        
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"{self.base_url}/send"
            async with self.session.post(url, json={
                'sender_id': self.agent_id,
                'content': content
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'sent':
                        return True
                    else:
                        logger.error(f"Send message response: {data}")
                        return False
                else:
                    logger.error(f"Send message failed with status {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return False
    
    async def list_agents(self) -> List[str]:
        """Get a list of all connected agents."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"{self.base_url}/agents"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('agents', [])
                else:
                    logger.error(f"List agents failed with status {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"List agents error: {e}")
            return []
    
    def add_message_handler(self, handler: Callable):
        """Add a handler function for incoming messages."""
        self.message_handlers.append(handler)
    
    async def _process_sse_event(self, event: str):
        """Process an SSE event."""
        if not event or not event.strip():
            return
        
        try:
            # Parse the event data
            data = json.loads(event)
            
            # Call all registered handlers
            for handler in self.message_handlers:
                await handler(data)
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in SSE event: {event}")
        except Exception as e:
            logger.error(f"Error processing SSE event: {e}")
    
    async def _listen_for_events(self):
        """Listen for SSE events from the server."""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/events?agent_id={self.agent_id}"
            
            # Track reconnection attempts
            reconnect_delay = 1
            max_reconnect_delay = 60  # Max 1 minute
            
            while True:
                try:
                    self.is_listening = True
                    
                    async with self.session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"SSE connection failed with status {response.status}")
                            await asyncio.sleep(reconnect_delay)
                            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                            continue
                        
                        # Reset reconnect delay on successful connection
                        reconnect_delay = 1
                        
                        # Process the events
                        buffer = ""
                        async for line in response.content:
                            line = line.decode('utf-8')
                            
                            # Check for ping
                            if line.startswith(': ping'):
                                continue
                            
                            # Line that starts with 'data: ' contains the event data
                            if line.startswith('data: '):
                                data = line[6:].strip()
                                await self._process_sse_event(data)
                            
                except asyncio.CancelledError:
                    logger.info("SSE listening task cancelled")
                    break
                except Exception as e:
                    logger.error(f"SSE connection error: {e}")
                    
                    # Wait before reconnecting
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                
                finally:
                    self.is_listening = False
        except Exception as e:
            logger.error(f"Error in SSE listening loop: {e}")
    
    async def start_listening(self):
        """Start listening for SSE events."""
        if self.sse_task is None or self.sse_task.done():
            self.sse_task = asyncio.create_task(self._listen_for_events())
            await asyncio.sleep(1)
    
    async def stop_listening(self):
        """Stop listening for SSE events."""
        if self.sse_task is not None and not self.sse_task.done():
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass
    
    async def close(self):
        """Close the client."""
        await self.stop_listening()
        
        if self.session is not None:
            await self.session.close()
            self.session = None
        
        self.is_registered = False
        logger.info("SSE client closed") 