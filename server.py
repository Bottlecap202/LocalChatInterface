#!/usr/bin/env python3
"""
server.py  –  local LLM chat interface
OpenAI-compatible streaming endpoint expected at
http://192.168.1.163:5000/v1/chat/completions
"""

import json, pathlib, uuid, time, asyncio
from aiohttp import web, WSMsgType
import aiohttp_cors
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

import aiohttp  # kept for any future outbound use; not used in stream_llm anymore

# ---------- config -----------------------------------------------------------
ROOT_DIR       = pathlib.Path(__file__).parent
DATA_DIR       = ROOT_DIR / "data"
CHATS_FILE     = DATA_DIR / "chats.json"
SETTINGS_FILE  = DATA_DIR / "settings.json"
LLM_API_BASE   = "http://192.168.1.163:5000/v1/chat/completions"
DEFAULT_SET    = {"temp": 0.7, "max_tokens": 500, "top_p": 1.0, "dark": True}

DATA_DIR.mkdir(exist_ok=True)

# ---------- helpers ----------------------------------------------------------
def sanitize(text: str) -> str:
    return text.replace("<", "<").replace(">", ">")

def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def ensure_files():
    if not CHATS_FILE.exists():
        save_json(CHATS_FILE, {})
    if not SETTINGS_FILE.exists():
        save_json(SETTINGS_FILE, DEFAULT_SET)

# ---------- storage ----------------------------------------------------------
def load_chats():
    return load_json(CHATS_FILE, {})

def save_chats(chats):
    save_json(CHATS_FILE, chats)

def load_settings():
    return load_json(SETTINGS_FILE, DEFAULT_SET.copy())

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

# ---------- HTTP streaming endpoint ------------------------------------------
async def chat_stream(request):
    """HTTP streaming endpoint for chat using curl requests"""
    logger.info(f"HTTP chat stream request from {request.remote}")
    try:
        data = await request.json()
        user_msg = sanitize(data["message"])
        history = data.get("history", [])
        settings = load_settings()
        temp = float(data.get("temperature", settings["temp"]))
        max_tokens = int(data.get("max_tokens", settings["max_tokens"]))
        top_p = float(data.get("top_p", settings["top_p"]))
        
        logger.info(f"HTTP stream request: message='{user_msg[:50]}...', history_length={len(history)}")
        logger.debug(f"Full request data: {json.dumps(data, indent=2)}")
        
        # Set up streaming response
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'application/x-ndjson'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        await response.prepare(request)
        
        # Stream tokens using existing curl-based function
        token_count = 0
        async for token in stream_llm(user_msg, history, temp, max_tokens, top_p):
            token_count += 1
            if token_count <= 3:  # Log first few tokens
                logger.debug(f"Sending token {token_count}: {token}")
            
            # Send each token as a JSON line
            await response.write(json.dumps({"token": token}).encode() + b'\n')
        
        # Send completion signal
        await response.write(json.dumps({"done": True}).encode() + b'\n')
        logger.info(f"HTTP stream completed successfully, sent {token_count} tokens")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in HTTP chat stream: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)

# ---------- LLM proxy via curl -----------------------------------------------
async def stream_llm(prompt, history, temp, max_tokens, top_p):
    logger.info(f"stream_llm called with prompt: {prompt[:50]}..., history length: {len(history)}")
    logger.info(f"Settings: temp={temp}, max_tokens={max_tokens}, top_p={top_p}")
    logger.info(f"Target API: {LLM_API_BASE}")
    
    msgs = [{"role": "system", "content": "You are a helpful AI assistant."}] + history + [{"role": "user", "content": prompt}]
    payload = {
        "model": "local",
        "messages": msgs,
        "temperature": temp,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "stream": True
    }
    
    logger.debug(f"Full payload: {json.dumps(payload, indent=2)}")
    
    cmd = [
        "curl", "-s", "-N",
        "-X", "POST",
        LLM_API_BASE,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]
    
    logger.info(f"Curl command: {' '.join(cmd)}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE  # Capture stderr for debugging
        )
        
        logger.info("Subprocess created successfully")
        
        token_count = 0
        async for line in proc.stdout:
            line = line.decode().strip()
            logger.debug(f"Raw line from curl: {line}")
            
            if line.startswith("data: "):
                chunk = line[6:]
                if chunk == "[DONE]":
                    logger.info("Received [DONE] signal")
                    break
                try:
                    delta = json.loads(chunk)["choices"][0]["delta"]
                    if "content" in delta:
                        token = delta["content"]
                        token_count += 1
                        if token_count <= 3:  # Log first few tokens
                            logger.debug(f"Yielding token {token_count}: {token}")
                        yield token
                except Exception as e:
                    logger.warning(f"Failed to parse chunk: {chunk}, error: {e}")
                    continue
            else:
                logger.debug(f"Non-data line: {line}")
        
        # Check stderr for any errors
        stderr = await proc.stderr.read()
        if stderr:
            logger.error(f"Curl stderr: {stderr.decode()}")
        
        return_code = await proc.wait()
        logger.info(f"Subprocess completed with return code: {return_code}")
        
    except Exception as e:
        logger.error(f"Exception in stream_llm: {e}", exc_info=True)
        raise

# ---------- routes -----------------------------------------------------------
async def index(_):
    return web.FileResponse(ROOT_DIR / "public" / "index.html")

async def history_list(_):
    chats = load_chats()
    return web.json_response(list(chats.values()))

async def history_get(request):
    cid = request.match_info["id"]
    chats = load_chats()
    return web.json_response(chats[cid]) if cid in chats else web.json_response({"error": "not found"}, status=404)

async def history_delete(request):
    cid = request.match_info["id"]
    chats = load_chats()
    chats.pop(cid, None)
    save_chats(chats)
    return web.json_response({"ok": True})

async def history_rename(request):
    cid = request.match_info["id"]
    body = await request.json()
    new_name = sanitize(body["name"])
    chats = load_chats()
    if cid in chats:
        chats[cid]["name"] = new_name
        save_chats(chats)
    return web.json_response({"ok": True})

async def export_all(_):
    return web.json_response({"chats": load_chats(), "settings": load_settings()})

async def import_all(request):
    body = await request.json()
    if "chats" in body:
        save_chats(body["chats"])
    if "settings" in body:
        save_settings(body["settings"])
    return web.json_response({"ok": True})

async def get_settings(_):
    return web.json_response(load_settings())

async def post_settings(request):
    save_settings(await request.json())
    return web.json_response({"ok": True})

# ---------- websocket --------------------------------------------------------
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            data = json.loads(msg.data)
            if data.get("action") == "stream":
                user_msg = sanitize(data["message"])
                history = data.get("history", [])
                settings = load_settings()
                temp = float(data.get("temperature", settings["temp"]))
                max_tokens = int(data.get("max_tokens", settings["max_tokens"]))
                top_p = float(data.get("top_p", settings["top_p"]))
                logger.info(f"WebSocket stream request: message='{user_msg[:50]}...', history_length={len(history)}")
                logger.debug(f"Full message data: {json.dumps(data, indent=2)}")
                try:
                    async for token in stream_llm(user_msg, history, temp, max_tokens, top_p):
                        await ws.send_str(json.dumps({"token": token}))
                    await ws.send_str(json.dumps({"done": True}))
                    logger.info("WebSocket stream completed successfully")
                except Exception as e:
                    logger.error(f"Error in WebSocket stream: {e}", exc_info=True)
                    await ws.send_str(json.dumps({"error": str(e)}))
        elif msg.type == WSMsgType.ERROR:
            logger.error(f"WebSocket error: {ws.exception()}")
    return ws

# ---------- app --------------------------------------------------------------
def build_app():
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={"*": aiohttp_cors.ResourceOptions(
        allow_credentials=True, expose_headers="*", allow_headers="*", allow_methods="*")})
    app.router.add_get("/", index)
    app.router.add_get("/api/history", history_list)
    app.router.add_get("/api/history/{id}", history_get)
    app.router.add_delete("/api/history/{id}", history_delete)
    app.router.add_patch("/api/history/{id}", history_rename)
    app.router.add_get("/api/export", export_all)
    app.router.add_post("/api/import", import_all)
    app.router.add_get("/api/settings", get_settings)
    app.router.add_post("/api/settings", post_settings)
    app.router.add_post("/api/chat", chat_stream)
    app.router.add_get("/api/stream", websocket_handler)
    app.router.add_static("/", path=ROOT_DIR / "public", name="static")
    for r in list(app.router.routes()):
        cors.add(r)
    return app

if __name__ == "__main__":
    ensure_files()
    logger.info("Starting server on 192.168.1.163:8282")
    web.run_app(build_app(), host="192.168.1.163", port=8282)