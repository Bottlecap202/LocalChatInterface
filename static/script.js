// --- RETAINED: Your original DOM element constants ---
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");

// --- ADDITION: New DOM element constants for the tool UI ---
const toolSelect = document.getElementById("tool-select");
const toolArgsSelect = document.getElementById("tool-args-select");
const useToolBtn = document.getElementById("use-tool-btn");
const reEnableBtn = document.getElementById("re-enable-tools-btn");
const smartActionBtn = document.getElementById("smart-action-btn"); // Added for Smart Action

// --- ADDITION: State management for used tools ---
const usedTools = new Set();


// --- RETAINED: Your original appendMessage function, completely untouched ---
function appendMessage(content, sender) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender);
    const senderDiv = document.createElement("div");
    senderDiv.classList.add("sender");
    senderDiv.textContent = sender === 'user' ? 'User' : (sender === 'system' ? 'System' : 'Cortex');
    const contentDiv = document.createElement("div");
    contentDiv.classList.add("content");
    contentDiv.textContent = content;
    msgDiv.appendChild(senderDiv);
    msgDiv.appendChild(contentDiv);
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// --- ADDITION START: The new functions required for tool calling ---

function updateToolDropdownState() {
    for (const option of toolSelect.options) {
        if (option.value && usedTools.has(option.value)) {
            option.disabled = true;
        } else {
            option.disabled = false;
        }
    }
}

async function loadTools() {
    try {
        const response = await fetch('/tools');
        if (!response.ok) throw new Error('Failed to fetch tools');
        const tools = await response.json();
        toolSelect.innerHTML = '<option value="">Select a tool</option>';
        tools.forEach(tool => {
            const option = document.createElement('option');
            option.value = tool;
            option.textContent = tool;
            toolSelect.appendChild(option);
        });
    } catch (error) {
        console.error("Error loading tools:", error);
        appendMessage("Could not load tools from the server.", "system");
    }
}

async function loadToolOptions(toolName) {
    if (!toolName) {
        toolArgsSelect.style.display = 'none';
        return;
    }
    try {
        const response = await fetch(`/tool-options?tool=${toolName}`);
        const options = await response.json();
        if (options && options.length > 0) {
            toolArgsSelect.innerHTML = '<option value="" disabled selected>Select an action</option>';
            options.forEach(opt => {
                const optionEl = document.createElement('option');
                optionEl.value = opt.args;
                optionEl.textContent = opt.name;
                toolArgsSelect.appendChild(optionEl);
            });
            toolArgsSelect.style.display = 'block';
        } else {
            toolArgsSelect.style.display = 'none';
        }
    } catch (error) {
        console.error(`Error loading options for ${toolName}:`, error);
        toolArgsSelect.style.display = 'none';
    }
}

// --- THIS IS THE MODIFIED FUNCTION ---
async function callTool() {
    const selectedTool = toolSelect.value;
    const selectedArgs = toolArgsSelect.value; // This gets the '--mode ...' part
    const chatInputValue = chatInput.value.trim(); // This gets the user input

    // --- Step 1: Validate all required inputs from the user ---
    if (!selectedTool) {
        appendMessage("Please select a tool from the dropdown first.", "system");
        return;
    }
    // The 'stock-stats-tool' requires a mode to be selected.
    if (!selectedArgs) {
        appendMessage("Please select an action (like 'Research Specific Stock') from the second dropdown.", "system");
        return;
    }
    // The tool also requires a ticker symbol.
    if (!chatInputValue) {
        appendMessage("Please enter a stock ticker in the input box before using the tool.", "system");
        return;
    }

    // --- Step 2: Build the final, complete argument string ---
    // This is the crucial fix. We combine the mode and the ticker arguments.
    // Example result: "--mode get-performance-summary --ticker GOOGL"
    let finalArgs;
    let userMessage;
    
    // Handle argument construction based on tool type
    if (selectedTool === "web-search-tool.py") {
        // Web search tool expects positional arguments after mode flags
        finalArgs = `${selectedArgs} ${chatInputValue}`;
        const modeName = toolArgsSelect.options[toolArgsSelect.selectedIndex].text;
        userMessage = `Request: ${modeName} - ${chatInputValue.substring(0, 80)}${chatInputValue.length > 80 ? '...' : ''}`;
    } else {
        // Stock and other tools use --ticker parameter
        finalArgs = `${selectedArgs} --ticker ${chatInputValue}`;
        const modeName = toolArgsSelect.options[toolArgsSelect.selectedIndex].text;
        userMessage = `Request: ${modeName} for ${chatInputValue}`;
    }

    // --- Step 3: Display user feedback and call the tool ---
    appendMessage(userMessage, "user");
    appendMessage(`Calling tool: ${selectedTool}...`, "system");
    chatInput.value = ""; // Clear the input box after use

    try {
        const response = await fetch('/call-tool', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // Send the correctly combined argument string to the backend
            body: JSON.stringify({ tool: selectedTool, args: finalArgs }),
        });
        const result = await response.json();
        if (response.ok) {
            appendMessage(result.output, "system");
        } else {
            appendMessage(`Error: ${result.error}`, "system");
        }
    } catch (error) {
        console.error("Error calling tool:", error);
        appendMessage("An unexpected error occurred while calling the tool.", "system");
    } finally {
        // This part for disabling used tools can remain the same.
        usedTools.add(selectedTool);
        updateToolDropdownState();
        toolSelect.value = "";
        loadToolOptions("");
    }
}
// --- END MODIFICATION ---

// --- RETAINED & CORRECTED: Your original streamChatCompletion function ---
async function streamChatCompletion(userMessage) {
    try {
        appendMessage(userMessage, "user");
        const payload = {
            model: "koboldcpp",
            messages: [
                { role: "system", content: "You are a helpful AI assistant." },
                { role: "user", content: userMessage }
            ],
            temperature: 0.1,
            stream: true
        };
        const assistantMsgDiv = document.createElement("div");
        assistantMsgDiv.className = "message assistant";
        const senderDiv = document.createElement("div");
        senderDiv.className = "sender";
        senderDiv.textContent = "Cortex";
        const contentDiv = document.createElement("div");
        contentDiv.className = "content";
        contentDiv.textContent = "…";
        assistantMsgDiv.appendChild(senderDiv);
        assistantMsgDiv.appendChild(contentDiv);
        chatMessages.appendChild(assistantMsgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        const response = await fetch('/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullResponse = '';
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') { return; }
                    try {
                        const parsed = JSON.parse(data);
                        const delta = parsed.choices[0]?.delta?.content;
                        if (delta) {
                            if (contentDiv.textContent === "…") { contentDiv.textContent = ""; }
                            fullResponse += delta;
                            contentDiv.textContent = fullResponse;
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    } catch (err) { console.warn("Failed to parse SSE chunk:", err); }
                }
            }
        }
    } catch (err) {
        console.error("SSE connection error:", err);
        const errorDiv = chatMessages.querySelector(".assistant .content");
        if (errorDiv) { errorDiv.textContent = "Connection failed - check console"; }
    }
}

// --- ADDITION: Event listeners for the new tool UI ---
document.addEventListener('DOMContentLoaded', loadTools);
useToolBtn.addEventListener('click', callTool);
toolSelect.addEventListener('change', () => loadToolOptions(toolSelect.value));
reEnableBtn.addEventListener('click', () => {
    usedTools.clear();
    updateToolDropdownState();
    appendMessage("All tools have been re-enabled.", "system");
});

// --- RETAINED: Your original event listeners, completely untouched ---
chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (msg === "") return;
    // Check if a tool is selected. If so, don't submit as a chat message.
    if (toolSelect.value && toolArgsSelect.value) {
        appendMessage("Please use the 'Use Tool' button to run a tool with the provided ticker.", "system");
        return;
    }
    chatInput.value = "";
    streamChatCompletion(msg);
});

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});