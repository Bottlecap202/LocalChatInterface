# Local LLM Chat Application - User Guide

## Overview
The Local LLM Chat Application is a web-based interface that allows you to interact with local language models. It provides a clean, modern interface similar to popular chat applications, but designed to work entirely offline with your own local models.

## Getting Started

### Main Interface
The application consists of two main areas:
1. **Sidebar**: Contains your chat history and settings
2. **Main Chat Area**: Where you interact with the AI

### Starting a New Chat
1. Click the "New Chat" button in the sidebar
2. A new conversation will begin with a greeting from the AI
3. Type your message in the input field at the bottom and press Enter or click the Send button

### Navigating Chat History
1. Your previous conversations are listed in the sidebar
2. Click on any conversation to load it
3. To delete a conversation, hover over it and click the trash icon

## Features

### Message Interaction
- **Copy Message**: Hover over any message and click the copy icon to copy its content
- **Edit User Messages**: Hover over your messages and click the edit icon to modify them
- **Regenerate Responses**: Hover over AI responses and click the regenerate icon to get a new response

### Markdown and Code
- The application supports Markdown formatting in messages
- Code blocks are automatically highlighted with syntax highlighting
- You can use backticks (`) for inline code and triple backticks (```) for code blocks

### Settings
Click the "Settings" button in the sidebar to configure:

#### API Endpoint
- **Local OpenAI-compatible**: For APIs like LM Studio, text-generation-webui, etc.
- **Ollama**: For the Ollama local LLM runner
- **LocalAI**: For the LocalAI self-hosted solution
- **Custom**: For any other OpenAI-compatible API

#### Model Selection
- Choose which model to use for conversations
- The available models depend on your backend configuration

#### Parameters
- **Temperature**: Controls randomness (0 = deterministic, 1 = creative)
- **Max Tokens**: Maximum length of the response
- **Top-P**: Nucleus sampling parameter

### Theme
- Toggle between dark and light themes using the theme button in the sidebar
- Your preference is saved and will be applied on future visits

### Data Management
- **Export Settings**: Save your current settings to a JSON file
- **Import Settings**: Load settings from a previously exported file
- **Chat History**: All conversations are automatically saved and can be accessed from the sidebar

## Keyboard Shortcuts
- **Enter**: Send message
- **Shift+Enter**: Add a new line in the message input
- **Ctrl+/**: Toggle sidebar (when focused on chat input)

## Tips for Better Conversations

### Effective Prompting
- Be specific and clear in your requests
- Provide context when needed
- For complex tasks, break them down into smaller steps

### Working with Code
- Use triple backticks with language specification for syntax highlighting:
  ```
  ```python
  def hello_world():
      print("Hello, World!")
  ```
  ```
- The AI can help with code generation, debugging, and explanation

### Managing Long Conversations
- For very long conversations, consider starting a new chat to maintain context
- You can always refer back to previous conversations in the history

## Troubleshooting Common Issues

### Slow Response Times
- Check that your local LLM backend is running properly
- Consider reducing the Max Tokens setting for shorter responses
- Make sure your system has sufficient resources (RAM, CPU/GPU)

### Error Messages
- "Connection Error": Check that your LLM backend is running and the API endpoint is correct
- "API Error": Verify that the selected model is available in your backend
- "Failed to save/load": Check that the application has write permissions to the data directory

### Model Not Available
- Make sure the model is properly installed in your backend
- Try refreshing the model list by changing the API endpoint and then changing it back
- Check your backend's documentation for model installation instructions

## Privacy and Data
- All conversations are stored locally on your machine
- No data is sent to external servers
- Your chat history is never shared or used for training

## Support
For additional support or to report issues, please refer to the project documentation or create an issue in the project repository.
