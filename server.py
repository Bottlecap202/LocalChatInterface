import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional

import aiohttp
import aiofiles
from aiohttp import web, WSMsgType

# Define paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CHATS_DIR = DATA_DIR / "chats"
SETTINGS_FILE = DATA_DIR / "settings.json"
CONFIG_DIR = BASE_DIR / "config"
DEFAULT_CONFIG_FILE = CONFIG_DIR / "default.json"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CHATS_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

# Default settings
DEFAULT_SETTINGS = {
    "apiEndpoint": "http://localhost:1234/v1",
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "maxTokens": 2048,
    "topP": 0.9
}

# Default config
DEFAULT_CONFIG = {
    "availableEndpoints": {
        "Local OpenAI-compatible": "http://localhost:1234/v1",
        "Ollama": "http://localhost:11434/api",
        "LocalAI": "http://localhost:8080"
    },
    "defaultModels": [
        "gpt-3.5-turbo",
        "gpt-4",
        "llama2",
        "mistral"
    ]
}

async def load_settings() -> Dict[str, Any]:
    """Load settings from file or create default if not exists."""
    try:
        async with aiofiles.open(SETTINGS_FILE, 'r') as f:
            content = await f.read()
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        await save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

async def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to file."""
    async with aiofiles.open(SETTINGS_FILE, 'w') as f:
        await f.write(json.dumps(settings, indent=2))

async def load_chat_history() -> List[Dict[str, Any]]:
    """Load all chat histories."""
    chats = []
    for chat_file in CHATS_DIR.glob("*.json"):
        try:
            async with aiofiles.open(chat_file, 'r') as f:
                content = await f.read()
                chat_data = json.loads(content)
                chats.append(chat_data)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return sorted(chats, key=lambda x: x.get("timestamp", ""), reverse=True)

async def save_chat(chat_data: Dict[str, Any]) -> None:
    """Save a chat to file."""
    chat_id = chat_data.get("id", str(uuid.uuid4()))
    chat_file = CHATS_DIR / f"{chat_id}.json"
    
    # Add timestamp if not present
    if "timestamp" not in chat_data:
        chat_data["timestamp"] = asyncio.get_event_loop().time()
    
    async with aiofiles.open(chat_file, 'w') as f:
        await f.write(json.dumps(chat_data, indent=2))

async def delete_chat(chat_id: str) -> bool:
    """Delete a chat by ID."""
    chat_file = CHATS_DIR / f"{chat_id}.json"
    try:
        if chat_file.exists():
            chat_file.unlink()
            return True
        return False
    except Exception:
        return False

async def get_available_models(api_endpoint: str) -> List[str]:
    """Get available models from the LLM backend."""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if "ollama" in api_endpoint.lower():
                # Ollama API
                url = f"{api_endpoint}/tags"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["name"] for model in data.get("models", [])]
            else:
                # OpenAI-compatible API
                url = f"{api_endpoint}/models"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["id"] for model in data.get("data", [])]
    except Exception as e:
        print(f"Error fetching models: {e}")
    
    # Return default models if unable to fetch
    return DEFAULT_CONFIG["defaultModels"]

async def stream_llm_response(websocket: web.WebSocketResponse, messages: List[Dict[str, Any]], settings: Dict[str, Any]) -> None:
    """Stream LLM response to the client via WebSocket."""
    api_endpoint = settings.get("apiEndpoint", "http://localhost:1234/v1")
    model = settings.get("model", "gpt-3.5-turbo")
    temperature = settings.get("temperature", 0.7)
    max_tokens = settings.get("maxTokens", 2048)
    top_p = settings.get("topP", 0.9)
    
    try:
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if "ollama" in api_endpoint.lower():
                # Ollama API
                payload = {
                    "model": model,
                    "prompt": messages[-1]["content"],
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "num_predict": max_tokens
                    }
                }
                url = f"{api_endpoint}/generate"
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        await websocket.send_json({"type": "error", "message": f"API Error: {error_text}"})
                        return
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    await websocket.send_json({
                                        "type": "message",
                                        "content": data["response"]
                                    })
                                if data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                # OpenAI-compatible API
                payload = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p
                }
                url = f"{api_endpoint}/chat/completions"
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        await websocket.send_json({"type": "error", "message": f"API Error: {error_text}"})
                        return
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        await websocket.send_json({
                                            "type": "message",
                                            "content": delta["content"]
                                        })
                            except json.JSONDecodeError:
                                continue
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Connection Error: {str(e)}"})

# API Handlers
async def get_models(request: web.Request) -> web.Response:
    """Get available models from the LLM backend."""
    settings = await load_settings()
    api_endpoint = settings.get("apiEndpoint", "http://localhost:1234/v1")
    models = await get_available_models(api_endpoint)
    return web.json_response({"models": models})

async def post_chat(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connection for streaming chat responses."""
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)
    
    try:
        # Wait for the initial message with chat data
        msg = await websocket.receive()
        if msg.type != WSMsgType.TEXT:
            await websocket.close()
            return websocket
        
        data = json.loads(msg.data)
        messages = data.get("messages", [])
        settings = data.get("settings", {})
        
        # Stream the LLM response
        await stream_llm_response(websocket, messages, settings)
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Error: {str(e)}"})
    finally:
        await websocket.close()
    
    return websocket

async def get_chats(request: web.Request) -> web.Response:
    """Get all chat histories."""
    chats = await load_chat_history()
    return web.json_response({"chats": chats})

async def post_chats(request: web.Request) -> web.Response:
    """Save a new chat."""
    try:
        chat_data = await request.json()
        await save_chat(chat_data)
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def delete_chat_handler(request: web.Request) -> web.Response:
    """Delete a chat by ID."""
    chat_id = request.match_info.get('id')
    if not chat_id:
        return web.json_response({"status": "error", "message": "Missing chat ID"}, status=400)
    
    success = await delete_chat(chat_id)
    if success:
        return web.json_response({"status": "success"})
    else:
        return web.json_response({"status": "error", "message": "Chat not found"}, status=404)

async def get_settings(request: web.Request) -> web.Response:
    """Get current settings."""
    settings = await load_settings()
    return web.json_response(settings)

async def post_settings(request: web.Request) -> web.Response:
    """Update settings."""
    try:
        new_settings = await request.json()
        await save_settings(new_settings)
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def index(request: web.Request) -> web.Response:
    """Serve the main HTML file."""
    return web.FileResponse(BASE_DIR / "public" / "index.html")

async def static_handler(request: web.Request) -> web.Response:
    """Serve static files."""
    file_path = BASE_DIR / "public" / request.match_info.get('filename', '')
    if file_path.exists() and file_path.is_file():
        return web.FileResponse(file_path)
    return web.Response(status=404)

# Initialize default config and settings if they don't exist
async def init_default_files():
    """Initialize default configuration and settings files."""
    # Create default config if not exists
    if not DEFAULT_CONFIG_FILE.exists():
        async with aiofiles.open(DEFAULT_CONFIG_FILE, 'w') as f:
            await f.write(json.dumps(DEFAULT_CONFIG, indent=2))
    
    # Create default settings if not exists
    if not SETTINGS_FILE.exists():
        await save_settings(DEFAULT_SETTINGS)

# Create and configure the application
async def create_app():
    """Create and configure the aiohttp application."""
    app = web.Application()
    
    # Initialize default files
    await init_default_files()
    
    # Add routes
    app.router.add_get('/', index)
    app.router.add_get('/static/{filename}', static_handler)
    
    # API routes
    app.router.add_get('/api/models', get_models)
    app.router.add_get('/api/chats', get_chats)
    app.router.add_post('/api/chats', post_chats)
    app.router.add_delete('/api/chats/{id}', delete_chat_handler)
    app.router.add_get('/api/settings', get_settings)
    app.router.add_post('/api/settings', post_settings)
    app.router.add_get('/api/chat', post_chat)  # WebSocket endpoint
    
    return app

if __name__ == '__main__':
    print("Starting LLM Chat Server...")
    app = asyncio.run(create_app())
    web.run_app(app, host='0.0.0.0', port=8080)
