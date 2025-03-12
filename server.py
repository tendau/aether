import asyncio
import json
import logging
import time
from typing import Dict, List, Set

from aiohttp import web
from aiohttp.web import Request, Response, json_response

import config

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agent_server")

# In-memory message storage
# Maps agent_id to list of messages
message_queues: Dict[str, List[Dict]] = {}
# Maps agent_id to a set of response objects for SSE connections
sse_connections: Dict[str, Set[web.StreamResponse]] = {}
# Maps agent_id to last seen timestamp
agent_last_seen: Dict[str, float] = {}

async def register_agent(request: Request) -> Response:
    """Register an agent with the server."""
    try:
        data = await request.json()
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return json_response({'error': 'Missing agent_id'}, status=400)
        
        # Initialize message queue if needed
        if agent_id not in message_queues:
            message_queues[agent_id] = []
            sse_connections[agent_id] = set()
        
        agent_last_seen[agent_id] = time.time()
        logger.info(f"Agent {agent_id} registered")
        
        return json_response({'status': 'registered', 'agent_id': agent_id})
    
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        return json_response({'error': str(e)}, status=500)

async def send_message(request: Request) -> Response:
    """Send a message to all other agents (broadcast)."""
    try:
        data = await request.json()
        sender_id = data.get('sender_id')
        content = data.get('content')
        
        if not sender_id or not content:
            return json_response({'error': 'Missing sender_id or content'}, status=400)
        
        # Update last seen timestamp
        agent_last_seen[sender_id] = time.time()
        
        # Create message
        message = {
            'type': 'message',
            'from': sender_id,
            'content': content,
            'timestamp': time.time()
        }
        
        # Broadcast to all agents except sender
        for agent_id in message_queues.keys():
            if agent_id != sender_id:
                # Add to message queue
                message_queues[agent_id].append(message)
                
                # Send to all active SSE connections for this agent
                for connection in sse_connections.get(agent_id, set()):
                    try:
                        await connection.write(f"data: {json.dumps(message)}\n\n".encode('utf-8'))
                        await connection.drain()
                    except Exception as e:
                        logger.error(f"Error sending SSE message to {agent_id}: {e}")
        
        logger.info(f"Message from {sender_id} broadcast to {len(message_queues) - 1} agents")
        return json_response({'status': 'sent'})
    
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return json_response({'error': str(e)}, status=500)

async def events(request: Request) -> web.StreamResponse:
    """Subscribe to events using Server-Sent Events."""
    agent_id = request.query.get('agent_id')
    
    if not agent_id:
        return json_response({'error': 'Missing agent_id'}, status=400)
    
    # Initialize message queue if needed
    if agent_id not in message_queues:
        message_queues[agent_id] = []
        sse_connections[agent_id] = set()
    
    # Update last seen timestamp
    agent_last_seen[agent_id] = time.time()
    
    # Set up SSE response
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    await response.prepare(request)
    
    # Add to active connections
    sse_connections[agent_id].add(response)
    
    try:
        # Send any waiting messages
        for message in message_queues[agent_id]:
            await response.write(f"data: {json.dumps(message)}\n\n".encode('utf-8'))
            await response.drain()
        
        # Clear the message queue after sending
        message_queues[agent_id] = []
        
        # Keep connection alive
        while True:
            # Send a ping message every 30 seconds to keep the connection alive
            await response.write(b": ping\n\n")
            await response.drain()
            
            # Update last seen timestamp
            agent_last_seen[agent_id] = time.time()
            
            await asyncio.sleep(30)
    
    except ConnectionResetError:
        logger.info(f"SSE connection closed for {agent_id}")
    except asyncio.CancelledError:
        logger.info(f"SSE connection cancelled for {agent_id}")
    finally:
        # Remove from active connections
        if agent_id in sse_connections and response in sse_connections[agent_id]:
            sse_connections[agent_id].remove(response)
        
        return response

async def list_agents(request: Request) -> Response:
    """List all registered agents."""
    # Clean up inactive agents first
    cleanup_inactive_agents()
    
    agents = list(message_queues.keys())
    return json_response({'agents': agents})

def cleanup_inactive_agents(max_idle_time=300):  # 5 minutes
    """Clean up agents that haven't been seen for a while."""
    current_time = time.time()
    inactive_agents = [
        agent_id for agent_id, last_seen in agent_last_seen.items()
        if current_time - last_seen > max_idle_time
    ]
    
    for agent_id in inactive_agents:
        if agent_id in message_queues:
            del message_queues[agent_id]
        if agent_id in sse_connections:
            # Close all connections
            for connection in sse_connections[agent_id]:
                try:
                    connection.force_close()
                except Exception:
                    pass
            del sse_connections[agent_id]
        if agent_id in agent_last_seen:
            del agent_last_seen[agent_id]
        
        logger.info(f"Cleaned up inactive agent {agent_id}")

async def cleanup_task(app):
    """Task to periodically clean up inactive agents."""
    while True:
        try:
            cleanup_inactive_agents()
            await asyncio.sleep(60)  # Run once a minute
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)

async def on_startup(app):
    logger.info(f"Server starting on {config.SERVER_HOST}:{config.SERVER_PORT}")
    app['cleanup_task'] = asyncio.create_task(cleanup_task(app))

async def on_shutdown(app):
    logger.info("Server shutting down")
    
    # Cancel cleanup task
    if 'cleanup_task' in app:
        app['cleanup_task'].cancel()
        try:
            await app['cleanup_task']
        except asyncio.CancelledError:
            pass
    
    # Close all SSE connections
    for agent_id, connections in sse_connections.items():
        for connection in connections:
            try:
                connection.force_close()
            except Exception:
                pass

def main():
    app = web.Application()
    
    # Set up routes
    app.router.add_post('/register', register_agent)
    app.router.add_post('/send', send_message)
    app.router.add_get('/events', events)
    app.router.add_get('/agents', list_agents)
    
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    web.run_app(app, host=config.SERVER_HOST, port=config.SERVER_PORT)

if __name__ == '__main__':
    main() 