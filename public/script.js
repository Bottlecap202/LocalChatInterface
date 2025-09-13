// DOM Elements
const sidebar = document.getElementById('sidebar');
const chatHistory = document.getElementById('chat-history');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const newChatBtn = document.getElementById('new-chat-btn');
const settingsBtn = document.getElementById('settings-btn');
const themeToggle = document.getElementById('theme-toggle');
const modelSelector = document.getElementById('model-selector');
const chatTitle = document.getElementById('chat-title');

// Modal Elements
const settingsModal = document.getElementById('settings-modal');
const editMessageModal = document.getElementById('edit-message-modal');
const closeModalBtns = document.querySelectorAll('.close-modal');

// Settings Form Elements
const settingsForm = document.getElementById('settings-form');
const apiEndpointSelect = document.getElementById('api-endpoint');
const customApiEndpoint = document.getElementById('custom-api-endpoint');
const temperatureSlider = document.getElementById('temperature');
const temperatureValue = document.getElementById('temperature-value');
const maxTokensSlider = document.getElementById('max-tokens');
const maxTokensValue = document.getElementById('max-tokens-value');
const topPSlider = document.getElementById('top-p');
const topPValue = document.getElementById('top-p-value');
const exportSettingsBtn = document.getElementById('export-settings');
const importSettingsBtn = document.getElementById('import-settings');

// Edit Message Form Elements
const editMessageForm = document.getElementById('edit-message-form');
const editMessageContent = document.getElementById('edit-message-content');
const cancelEditBtn = document.getElementById('cancel-edit');

// State
let currentChatId = null;
let currentMessages = [];
let isSidebarCollapsed = false;
let currentTheme = 'dark';
let currentSettings = {
    apiEndpoint: 'http://localhost:1234/v1',
    model: 'gpt-3.5-turbo',
    temperature: 0.7,
    maxTokens: 2048,
    topP: 0.9
};

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    // Load settings
    await loadSettings();
    
    // Load chat history
    await loadChatHistory();
    
    // Set up event listeners
    setupEventListeners();
    
    // Create a new chat
    createNewChat();
});

// Set up event listeners
function setupEventListeners() {
    // Message input handling
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = (messageInput.scrollHeight) + 'px';
    });
    
    // Sidebar toggle
    toggleSidebarBtn.addEventListener('click', toggleSidebar);
    newChatBtn.addEventListener('click', createNewChat);
    
    // Settings modal
    settingsBtn.addEventListener('click', openSettingsModal);
    exportSettingsBtn.addEventListener('click', exportSettings);
    importSettingsBtn.addEventListener('click', importSettings);
    
    // Theme toggle
    themeToggle.addEventListener('click', toggleTheme);
    
    // Close modals
    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            settingsModal.classList.remove('active');
            editMessageModal.classList.remove('active');
        });
    });
    
    // Settings form
    settingsForm.addEventListener('submit', saveSettings);
    apiEndpointSelect.addEventListener('change', toggleCustomEndpoint);
    
    // Slider value updates
    temperatureSlider.addEventListener('input', () => {
        temperatureValue.textContent = temperatureSlider.value;
    });
    
    maxTokensSlider.addEventListener('input', () => {
        maxTokensValue.textContent = maxTokensSlider.value;
    });
    
    topPSlider.addEventListener('input', () => {
        topPValue.textContent = topPSlider.value;
    });
    
    // Edit message form
    editMessageForm.addEventListener('submit', saveEditedMessage);
    cancelEditBtn.addEventListener('click', () => {
        editMessageModal.classList.remove('active');
    });
    
    // Click outside modal to close
    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) {
            settingsModal.classList.remove('active');
        }
        if (e.target === editMessageModal) {
            editMessageModal.classList.remove('active');
        }
    });
}

// Toggle sidebar visibility
function toggleSidebar() {
    isSidebarCollapsed = !isSidebarCollapsed;
    sidebar.classList.toggle('collapsed', isSidebarCollapsed);
    toggleSidebarBtn.innerHTML = isSidebarCollapsed ? 
        '<i class="fas fa-bars"></i>' : 
        '<i class="fas fa-times"></i>';
}

// Create a new chat
function createNewChat() {
    currentChatId = 'chat-' + Date.now();
    currentMessages = [];
    chatTitle.textContent = 'New Chat';
    chatMessages.innerHTML = '';
    
    // Add initial assistant message
    addMessageToChat('assistant', 'Hello! I\'m your local AI assistant. How can I help you today?');
    
    // Update UI
    toggleSidebar();
    messageInput.focus();
}

// Send message to the LLM
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    // Show typing indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = `
        <span></span>
        <span></span>
        <span></span>
    `;
    chatMessages.appendChild(typingIndicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Simulate API call to backend
    try {
        // In a real implementation, this would connect to your local LLM
        // For now, we'll simulate a response
        setTimeout(() => {
            chatMessages.removeChild(typingIndicator);
            addMessageToChat('assistant', 'This is a simulated response from your local LLM. In a real implementation, this would connect to your local AI model like Ollama, LocalAI, or any OpenAI-compatible endpoint.');
            saveCurrentChat();
        }, 1000);
    } catch (error) {
        chatMessages.removeChild(typingIndicator);
        addMessageToChat('assistant', 'Sorry, I encountered an error. Please try again.');
        console.error('Error sending message:', error);
    }
}

// Add message to chat display
function addMessageToChat(role, content, messageId = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    if (messageId) messageDiv.dataset.id = messageId;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Render markdown content
    contentDiv.innerHTML = marked.parse(content);
    
    // Add message actions
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    
    if (role === 'user') {
        const editBtn = document.createElement('button');
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.title = 'Edit message';
        editBtn.addEventListener('click', () => editMessage(messageDiv));
        actionsDiv.appendChild(editBtn);
    } else {
        const regenerateBtn = document.createElement('button');
        regenerateBtn.innerHTML = '<i class="fas fa-redo"></i>';
        regenerateBtn.title = 'Regenerate response';
        regenerateBtn.addEventListener('click', () => regenerateResponse(messageDiv));
        actionsDiv.appendChild(regenerateBtn);
    }
    
    const copyBtn = document.createElement('button');
    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
    copyBtn.title = 'Copy message';
    copyBtn.addEventListener('click', () => copyMessage(content));
    actionsDiv.appendChild(copyBtn);
    
    contentDiv.appendChild(actionsDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Add to current messages array
    const msgObj = {
        id: messageId || 'msg-' + Date.now(),
        role,
        content,
        timestamp: new Date().toISOString()
    };
    
    currentMessages.push(msgObj);
}

// Edit a message
function editMessage(messageElement) {
    const messageId = messageElement.dataset.id;
    const message = currentMessages.find(msg => msg.id === messageId);
    
    if (message) {
        editMessageContent.value = message.content;
        editMessageContent.dataset.messageId = messageId;
        editMessageModal.classList.add('active');
    }
}

// Save edited message
function saveEditedMessage(e) {
    e.preventDefault();
    
    const messageId = editMessageContent.dataset.messageId;
    const newContent = editMessageContent.value;
    
    // Update message in array
    const messageIndex = currentMessages.findIndex(msg => msg.id === messageId);
    if (messageIndex !== -1) {
        currentMessages[messageIndex].content = newContent;
    }
    
    // Update message in UI
    const messageElement = document.querySelector(`[data-id="${messageId}"] .message-content`);
    if (messageElement) {
        messageElement.innerHTML = marked.parse(newContent);
        
        // Re-add actions
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        const editBtn = document.createElement('button');
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.title = 'Edit message';
        editBtn.addEventListener('click', () => editMessage(messageElement.parentElement.parentElement));
        actionsDiv.appendChild(editBtn);
        
        const copyBtn = document.createElement('button');
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy message';
        copyBtn.addEventListener('click', () => copyMessage(newContent));
        actionsDiv.appendChild(copyBtn);
        
        messageElement.appendChild(actionsDiv);
    }
    
    editMessageModal.classList.remove('active');
    saveCurrentChat();
}

// Regenerate response
function regenerateResponse(messageElement) {
    // In a real implementation, this would send the conversation history
    // up to this point to the LLM to generate a new response
    const newResponse = "This is a regenerated response. In a real implementation, this would connect to your local LLM to generate a new response based on the conversation history.";
    
    // Update message content
    const contentDiv = messageElement.querySelector('.message-content');
    contentDiv.innerHTML = marked.parse(newResponse);
    
    // Re-add actions
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    
    const regenerateBtn = document.createElement('button');
    regenerateBtn.innerHTML = '<i class="fas fa-redo"></i>';
    regenerateBtn.title = 'Regenerate response';
    regenerateBtn.addEventListener('click', () => regenerateResponse(messageElement));
    actionsDiv.appendChild(regenerateBtn);
    
    const copyBtn = document.createElement('button');
    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
    copyBtn.title = 'Copy message';
    copyBtn.addEventListener('click', () => copyMessage(newResponse));
    actionsDiv.appendChild(copyBtn);
    
    contentDiv.appendChild(actionsDiv);
    
    // Update in messages array
    const messageId = messageElement.dataset.id;
    const messageIndex = currentMessages.findIndex(msg => msg.id === messageId);
    if (messageIndex !== -1) {
        currentMessages[messageIndex].content = newResponse;
    }
    
    saveCurrentChat();
}

// Copy message to clipboard
function copyMessage(content) {
    navigator.clipboard.writeText(content).then(() => {
        // Show a temporary "Copied!" message
        const originalText = themeToggle.innerHTML;
        themeToggle.innerHTML = '<i class="fas fa-check"></i> Copied!';
        setTimeout(() => {
            themeToggle.innerHTML = originalText;
        }, 2000);
    });
}

// Save current chat
async function saveCurrentChat() {
    if (!currentChatId || currentMessages.length === 0) return;
    
    const chatData = {
        id: currentChatId,
        title: chatTitle.textContent || 'New Chat',
        messages: currentMessages
    };
    
    try {
        const response = await fetch('/api/chats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(chatData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to save chat');
        }
        
        // Reload chat history
        await loadChatHistory();
    } catch (error) {
        console.error('Error saving chat:', error);
    }
}

// Load chat history
async function loadChatHistory() {
    try {
        const response = await fetch('/api/chats');
        if (!response.ok) {
            throw new Error('Failed to load chat history');
        }
        
        const chats = await response.json();
        renderChatHistory(chats);
    } catch (error) {
        console.error('Error loading chat history:', error);
        chatHistory.innerHTML = '<p class="error">Failed to load chat history</p>';
    }
}

// Render chat history in sidebar
function renderChatHistory(chats) {
    chatHistory.innerHTML = '';
    
    if (chats.length === 0) {
        chatHistory.innerHTML = '<p class="empty">No chat history yet</p>';
        return;
    }
    
    chats.forEach(chat => {
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-history-item';
        chatItem.dataset.id = chat.id;
        
        const title = document.createElement('span');
        title.textContent = chat.title;
        title.className = 'chat-title';
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteChat(chat.id);
        });
        
        chatItem.appendChild(title);
        chatItem.appendChild(deleteBtn);
        
        chatItem.addEventListener('click', () => loadChat(chat.id));
        
        chatHistory.appendChild(chatItem);
    });
}

// Load a specific chat
async function loadChat(chatId) {
    try {
        // In a real implementation, you would fetch the chat from the server
        // For now, we'll simulate loading a chat
        currentChatId = chatId;
        chatTitle.textContent = 'Loaded Chat';
        
        // Clear current messages
        chatMessages.innerHTML = '';
        currentMessages = [];
        
        // Add sample messages
        addMessageToChat('user', 'Hello, can you help me with something?');
        addMessageToChat('assistant', 'Of course! I\'m here to help. What do you need assistance with?');
        
        // Update UI
        toggleSidebar();
        messageInput.focus();
    } catch (error) {
        console.error('Error loading chat:', error);
    }
}

// Delete a chat
async function deleteChat(chatId) {
    if (!confirm('Are you sure you want to delete this chat?')) return;
    
    try {
        const response = await fetch(`/api/chats/${chatId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete chat');
        }
        
        // Reload chat history
        await loadChatHistory();
        
        // If we deleted the current chat, create a new one
        if (currentChatId === chatId) {
            createNewChat();
        }
    } catch (error) {
        console.error('Error deleting chat:', error);
        alert('Failed to delete chat');
    }
}

// Load settings
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (!response.ok) {
            throw new Error('Failed to load settings');
        }
        
        currentSettings = await response.json();
        applySettingsToForm();
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

// Apply settings to form
function applySettingsToForm() {
    // Set API endpoint
    if (Object.values({
        "Local OpenAI-compatible": "http://localhost:1234/v1",
        "Ollama": "http://localhost:11434/api",
        "LocalAI": "http://localhost:8080"
    }).includes(currentSettings.apiEndpoint)) {
        apiEndpointSelect.value = currentSettings.apiEndpoint;
        customApiEndpoint.style.display = 'none';
    } else {
        apiEndpointSelect.value = '';
        customApiEndpoint.style.display = 'block';
        customApiEndpoint.value = currentSettings.apiEndpoint;
    }
    
    // Set model
    modelSelector.value = currentSettings.model;
    
    // Set sliders
    temperatureSlider.value = currentSettings.temperature;
    temperatureValue.textContent = currentSettings.temperature;
    
    maxTokensSlider.value = currentSettings.maxTokens;
    maxTokensValue.textContent = currentSettings.maxTokens;
    
    topPSlider.value = currentSettings.topP;
    topPValue.textContent = currentSettings.topP;
}

// Save settings
async function saveSettings(e) {
    e.preventDefault();
    
    // Get values from form
    const settings = {
        apiEndpoint: apiEndpointSelect.value || customApiEndpoint.value,
        model: modelSelector.value,
        temperature: parseFloat(temperatureSlider.value),
        maxTokens: parseInt(maxTokensSlider.value),
        topP: parseFloat(topPSlider.value)
    };
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            throw new Error('Failed to save settings');
        }
        
        currentSettings = settings;
        settingsModal.classList.remove('active');
        alert('Settings saved successfully!');
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Failed to save settings');
    }
}

// Toggle custom API endpoint field
function toggleCustomEndpoint() {
    if (apiEndpointSelect.value === '') {
        customApiEndpoint.style.display = 'block';
    } else {
        customApiEndpoint.style.display = 'none';
    }
}

// Export settings
function exportSettings() {
    const dataStr = JSON.stringify(currentSettings, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = 'llm-chat-settings.json';
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}

// Import settings
function importSettings() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = e => {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.readAsText(file, 'UTF-8');
        
        reader.onload = readerEvent => {
            try {
                const content = readerEvent.target.result;
                const settings = JSON.parse(content);
                currentSettings = settings;
                applySettingsToForm();
                alert('Settings imported successfully!');
            } catch (error) {
                console.error('Error importing settings:', error);
                alert('Failed to import settings. Invalid file format.');
            }
        };
    };
    
    input.click();
}

// Toggle theme
function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.classList.toggle('light-theme', currentTheme === 'light');
    themeToggle.innerHTML = currentTheme === 'dark' ? 
        '<i class="fas fa-moon"></i> Dark Mode' : 
        '<i class="fas fa-sun"></i> Light Mode';
}
