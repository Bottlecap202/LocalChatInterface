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
      res.write('data: [DONE]\n\n');
      res.end();
    }
  }, 30);
});

app.get('/api/chats', (req, res) => {
  fs.readdir(chatsDir, (err, files) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to read chats directory' });
    }
    
    const chats = files
      .filter(file => file.endsWith('.json'))
      .map(file => {
        const chatId = path.basename(file, '.json');
        const chatData = JSON.parse(fs.readFileSync(path.join(chatsDir, file), 'utf8'));
        return {
          id: chatId,
          title: chatData.title || 'Untitled Chat',
          timestamp: chatData.timestamp
        };
      })
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    res.json(chats);
  });
});

app.post('/api/chats', (req, res) => {
  const { id, title, messages } = req.body;
  
  if (!id || !title || !messages) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  
  const chatData = {
    id,
    title,
    timestamp: new Date().toISOString(),
    messages
  };
  
  fs.writeFile(
    path.join(chatsDir, `${id}.json`),
    JSON.stringify(chatData, null, 2),
    (err) => {
      if (err) {
        return res.status(500).json({ error: 'Failed to save chat' });
      }
      res.json({ success: true, id });
    }
  );
});

app.delete('/api/chats/:id', (req, res) => {
  const { id } = req.params;
  
  fs.unlink(path.join(chatsDir, `${id}.json`), (err) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to delete chat' });
    }
    res.json({ success: true });
  });
});

app.get('/api/settings', (req, res) => {
  fs.readFile(settingsPath, 'utf8', (err, data) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to read settings' });
    }
    res.json(JSON.parse(data));
  });
});

app.post('/api/settings', (req, res) => {
  const settings = req.body;
  
  fs.writeFile(settingsPath, JSON.stringify(settings, null, 2), (err) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to save settings' });
    }
    res.json({ success: true });
  });
});

// WebSocket for real-time communication
wss.on('connection', (ws) => {
  ws.on('message', (message) => {
    // Echo the message back (in a real app, this would be the LLM response)
    ws.send(`Echo: ${message}`);
  });
});

// Start server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
