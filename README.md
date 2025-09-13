# Local LLM Chat Application

A modern, offline-first chat interface for interacting with local language models. This application provides a ChatGPT-like experience but runs entirely on your local machine, connecting to local LLM backends such as Ollama, LocalAI, or any OpenAI-compatible API.

## Features

- **Modern UI**: Clean, responsive interface with dark and light themes
- **Real-time Streaming**: Responses are streamed token by token for a natural conversation flow
- **Chat History**: Automatically save and load previous conversations
- **Message Management**: Edit your messages and regenerate AI responses
- **Markdown Support**: Render Markdown with syntax highlighting for code blocks
- **Multiple Backends**: Support for Ollama, LocalAI, and OpenAI-compatible APIs
- **Customizable**: Adjust temperature, max tokens, and other LLM parameters
- **Data Portability**: Export/import settings and chat history

## Technology Stack

### Backend
- Python with aiohttp for asynchronous web serving
- WebSocket support for real-time streaming
- JSON file storage for settings and chat history

### Frontend
- Vanilla JavaScript (ES6+)
- HTML5 and CSS3
- Marked.js for Markdown rendering
- Highlight.js for syntax highlighting

## Quick Start

1. **Clone or download this repository**
2. **Install dependencies**:
   ```bash
   cd C:\Users\sirbo\Desktop\AI-INTERFACE\
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Start the application**:
   ```bash
   python server.py
   ```
4. **Open your browser** and navigate to `http://localhost:8080`

## Configuration

The application supports multiple local LLM backends:

### Ollama
- Default endpoint: `http://localhost:11434/api`
- Make sure Ollama is installed and running
- Pull models using `ollama pull <model_name>`

### LocalAI
- Default endpoint: `http://localhost:8080`
- Make sure LocalAI is installed and running
- Configure models according to LocalAI documentation

### OpenAI-Compatible APIs
- Default endpoint: `http://localhost:1234/v1`
- Works with LM Studio, text-generation-webui, and other compatible backends
- Use the "Custom" option for non-default endpoints

## Project Structure

