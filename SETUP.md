# Local LLM Chat Application - Setup Guide

## Prerequisites
- Python 3.8 or higher
- Windows operating system
- A local LLM backend (Ollama, LocalAI, or any OpenAI-compatible API)

## Step-by-Step Setup Instructions

1. **Open Command Prompt**
   ```
   cd C:\Users\sirbo\Desktop\AI-INTERFACE\
   ```

2. **Create a Virtual Environment**
   ```
   python -m venv venv
   ```

3. **Activate the Virtual Environment**
   ```
   .\venv\Scripts\activate
   ```

4. **Install Required Dependencies**
   ```
   pip install -r requirements.txt
   ```

5. **Start the Application**
   ```
   python server.py
   ```

6. **Access the Application**
   - Open your web browser and navigate to `http://localhost:8080`
   - The application should now be running and ready to use

## Backend Configuration

### Connecting to Ollama
1. Make sure Ollama is installed and running on your system
2. In the application settings, select "Ollama" from the API Endpoint dropdown
3. The default endpoint is `http://localhost:11434/api`
4. Select a model from the dropdown (e.g., "llama2", "mistral")

### Connecting to LocalAI
1. Make sure LocalAI is installed and running on your system
2. In the application settings, select "LocalAI" from the API Endpoint dropdown
3. The default endpoint is `http://localhost:8080`
4. Select a model from the dropdown

### Connecting to a Custom OpenAI-Compatible API
1. In the application settings, select "Custom" from the API Endpoint dropdown
2. Enter your custom API endpoint in the text field that appears
3. Select a model from the dropdown or enter a custom model name

## Troubleshooting

### Application Won't Start
- Make sure Python 3.8 or higher is installed
- Check that all dependencies were installed correctly
- Verify that port 8080 is not already in use

### Can't Connect to LLM Backend
- Verify that your LLM backend is running and accessible
- Check the API endpoint URL in the settings
- Make sure the model name is correct

### Chat History Not Saving
- Check that the `data` directory exists and is writable
- Verify that the `chats` subdirectory exists within `data`

### Settings Not Persisting
- Check that the `data` directory exists and is writable
- Verify that the `settings.json` file exists within `data`

## Advanced Configuration

### Environment Variables
You can configure the application using environment variables:

- `LLM_CHAT_HOST`: Host to bind to (default: 0.0.0.0)
- `LLM_CHAT_PORT`: Port to bind to (default: 8080)
- `LLM_CHAT_DATA_DIR`: Data directory path (default: ./data)

### Running on a Different Port
