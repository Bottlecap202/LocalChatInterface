const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const http = require('http');
const WebSocket = require('ws');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Ensure data directories exist
const dataDir = path.join(__dirname, 'data');
const chatsDir = path.join(dataDir, 'chats');
const configDir = path.join(__dirname, 'config');

if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

if (!fs.existsSync(chatsDir)) {
  fs.mkdirSync(chatsDir, { recursive: true });
}

if (!fs.existsSync(configDir)) {
  fs.mkdirSync(configDir, { recursive: true });
}

// Default settings
const defaultSettings = {
  apiEndpoint: 'http://localhost:1234/v1',
  model: 'gpt-3.5-turbo',
  temperature: 0.7,
  maxTokens: 2048,
  topP: 0.9
};

// Default config
const defaultConfig = {
  "apiEndpoints": {
    "Local OpenAI-compatible": "http://localhost:1234/v1",
    "Ollama": "http://localhost:11434/api",
    "LocalAI": "http://localhost:8080"
  }
};

// Initialize settings file if it doesn't exist
const settingsPath = path.join(dataDir, 'settings.json');
if (!fs.existsSync(settingsPath)) {
  fs.writeFileSync(settingsPath, JSON.stringify(defaultSettings, null, 2));
}

// Initialize config file if it doesn't exist
const configPath = path.join(configDir, 'default.json');
if (!fs.existsSync(configPath)) {
  fs.writeFileSync(configPath, JSON.stringify(defaultConfig, null, 2));
}

// API Routes
app.get('/api/models', (req, res) => {
  // In a real implementation, this would fetch from the LLM backend
  // For now, we'll return some sample models
  res.json({
    models: [
      'gpt-3.5-turbo',
      'gpt-4',
      'llama2',
      'mistral'
    ]
  });
});

app.post('/api/chat', (req, res) => {
  const { messages, settings } = req.body;
  
  // In a real implementation, this would connect to the LLM backend
  // For now, we'll simulate a response
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });
  
  // Simulate streaming response
  const response = "This is a simulated response from your local LLM. In a real implementation, this would connect to your local AI model like Ollama, LocalAI, or any OpenAI-compatible endpoint.";
  let index = 0;
  
  const interval = setInterval(() => {
    if (index < response.length) {
      res.write(`data: ${JSON.stringify({ content: response[index] })}\n\n`);
      index++;
    } else {
      clearInterval(interval);
      res.write('data