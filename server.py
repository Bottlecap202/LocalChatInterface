import aiohttp
from aiohttp import web
import asyncio
import json
import os
import subprocess

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, 'tools')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# --- Route Handlers ---

async def index(request):
    """Serves the main index.html file."""
    return web.FileResponse(os.path.join(STATIC_DIR, 'index.html'))

async def get_tools(request):
    """Scans the tools directory for .py, .bat, and .ps1 files."""
    try:
        if not os.path.exists(TOOLS_DIR):
            return web.json_response([])
        
        compatible_extensions = ('.py', '.bat', '.ps1')
        tool_files = [f for f in os.listdir(TOOLS_DIR) if f.endswith(compatible_extensions)]
        return web.json_response(tool_files)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def get_tool_options(request):
    """Runs a tool with '--get-options' to fetch its pre-typed command list for the manual UI."""
    tool_name = request.query.get('tool')
    if not tool_name:
        return web.json_response({"error": "Tool name parameter is missing."}, status=400)

    script_path = os.path.join(TOOLS_DIR, tool_name)
    if not os.path.isfile(script_path):
        return web.json_response({"error": "Tool not found."}, status=404)

    try:
        command = ['python', script_path, '--get-options']
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return web.json_response([])

        # FIX: Decode with error handling to prevent crashes
        options = json.loads(stdout.decode('utf-8', errors='replace'))
        return web.json_response(options)
    except (json.JSONDecodeError, FileNotFoundError):
        return web.json_response([])
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def call_tool(request):
    """Handles the MANUAL execution of a tool, intelligently choosing the interpreter."""
    data = await request.json()
    tool_name = data.get('tool')
    args_string = data.get('args', '')

    if not tool_name:
        return web.json_response({"error": "Invalid tool name specified."}, status=400)

    script_path = os.path.join(TOOLS_DIR, tool_name)
    if not os.path.isfile(script_path):
        return web.json_response({"error": "Tool not found."}, status=404)

    try:
        args_list = args_string.split()
        file_ext = os.path.splitext(tool_name)[1].lower()
        
        command = []
        if file_ext == '.py':
            command = ['python', script_path] + args_list
        elif file_ext == '.bat':
            command = [script_path] + args_list
        elif file_ext == '.ps1':
            command = ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', script_path] + args_list
        else:
            return web.json_response({"error": f"Unsupported tool type: {file_ext}"}, status=400)

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=500)

        # FIX: Decode with error handling to prevent crashes
        stderr_decoded = stderr.decode('utf-8', errors='replace')
        stdout_decoded = stdout.decode('utf-8', errors='replace')

        if proc.returncode != 0:
            return web.json_response({"error": f"Tool execution failed:\n{stderr_decoded}"}, status=500)
        
        return web.json_response({"output": stdout_decoded})
    except asyncio.TimeoutError:
        return web.json_response({"error": "Tool execution timed out after 500 seconds."}, status=500)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def decide_and_run_tool(request):
    """Handles the AUTOMATIC 'Smart Action' by asking the AI to choose and run a tool."""
    data = await request.json()
    user_prompt = data.get('prompt')
    if not user_prompt:
        return web.json_response({"error": "Prompt is missing."}, status=400)

    tool_definitions = []
    for tool_file in os.listdir(TOOLS_DIR):
        if tool_file.endswith('.py'):
            script_path = os.path.join(TOOLS_DIR, tool_file)
            try:
                proc = await asyncio.create_subprocess_exec(
                    'python', script_path, '--get-definition',
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    # FIX: Decode with error handling
                    tool_definitions.append(json.loads(stdout.decode('utf-8', errors='replace')))
            except Exception:
                continue

    model_api_url = "http://192.168.1.163:5000/v1/chat/completions"
    system_prompt = "You are a financial market analysis assistant with access to real-time market data functions and mandatory web search capabilities. CRITICAL REQUIREMENT: You must ALWAYS use the websearch feature available through this API endpoint before analyzing any market data or providing financial insights. Your training data is outdated for financial markets, which change by the second, so web search is mandatory for accuracy. OPERATIONAL FLOW: 1. MANDATORY WEB SEARCH FIRST: Before calling any market data functions, you must search the web for current market conditions, breaking financial news, economic events, and relevant developments that could impact your analysis. Search for terms like current market news, breaking financial news, economic updates, Fed announcements, earnings reports, geopolitical events affecting markets. 2. FUNCTION CALLING SEQUENCE: After web search, call the provided market data functions in this logical order: get_market_indices first, then get_sector_performance, then get_economic_indicators, then calculate_market_sentiment with the market data, and finally generate_market_summary with all collected data. 3. CONTEXTUAL ANALYSIS: Combine the current web search results with the function data to provide comprehensive analysis. Reference specific news events, policy changes, earnings announcements, or economic developments found in your web search when interpreting the numerical data from functions. 4. CURRENT EVENT INTEGRATION: Your analysis must reflect real-time market drivers found through web search. If your web search reveals significant news like Federal Reserve decisions, major earnings beats or misses, geopolitical tensions, economic data releases, or corporate announcements, prominently feature these in your analysis and explain how they relate to the market data. 5. ACCURACY PRIORITY: If web search results contradict or provide additional context to the function data, prioritize the most recent and credible information. Always cite your web sources when referencing current events or recent developments. RESPONSE STRUCTURE: Begin with a brief mention of key current events from your web search, present the quantitative analysis from the functions, then synthesize both into actionable insights. Always acknowledge the time-sensitive nature of financial markets and that conditions can change rapidly. Remember: Financial markets are extremely time-sensitive. What happened even hours ago can be outdated. Web search is not optional - it is mandatory for providing accurate, current financial analysis."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"User Request: '{user_prompt}'\n\nAvailable Tools:\n{json.dumps(tool_definitions, indent=2)}"}]
    llm_payload = {"model": "koboldcpp", "messages": messages, "temperature": 0.0}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(model_api_url, json=llm_payload) as response:
                response.raise_for_status()
                llm_response = await response.json()
                decision = json.loads(llm_response['choices'][0]['message']['content'])
    except Exception as e:
        return web.json_response({"error": f"LLM decision failed: {str(e)}"}, status=500)

    tool_name = decision.get('tool')
    args_string = decision.get('args', '')
    script_path = os.path.join(TOOLS_DIR, tool_name)
    
    try:
        args_list = args_string.split()
        command = ['python', script_path] + args_list
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=500)
        
        # FIX: Decode with error handling
        stderr_decoded = stderr.decode('utf-8', errors='replace')
        stdout_decoded = stdout.decode('utf-8', errors='replace')

        if proc.returncode != 0:
            return web.json_response({"error": f"Tool execution failed:\n{stderr_decoded}"}, status=500)
        return web.json_response({"output": stdout_decoded, "tool_called": tool_name})
    except Exception as e:
        return web.json_response({"error": f"Tool execution failed after decision: {str(e)}"}, status=500)

async def stream(request):
    """Handles the original AI chat streaming functionality."""
    try:
        data = await request.json()
        model_api_url = "http://192.168.1.163:5000/v1/chat/completions"
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        await response.prepare(request)
        async with aiohttp.ClientSession() as session:
            async with session.post(model_api_url, json=data) as proxy_response:
                proxy_response.raise_for_status()
                async for chunk in proxy_response.content.iter_any():
                    if chunk:
                        await response.write(chunk)
        await response.write_eof()
        return response
    except aiohttp.ClientError as e:
        error_message = {"error": f"Failed to connect to the AI model API: {e}"}
        error_json = f"data: {json.dumps(error_message)}\n\ndata: [DONE]\n\n"
        return web.Response(text=error_json, content_type='text/event-stream')

# --- Application Setup ---
app = web.Application()
app.router.add_get('/', index)
app.router.add_get('/tools', get_tools)
app.router.add_get('/tool-options', get_tool_options)
app.router.add_post('/call-tool', call_tool)
app.router.add_post('/decide-and-run-tool', decide_and_run_tool)
app.router.add_post('/stream', stream)
app.router.add_static('/', path=STATIC_DIR, name='static')

if __name__ == '__main__':
    web.run_app(app, host='192.168.1.163', port=8282)