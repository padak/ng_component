/**
 * Driver Creator Agent - Frontend Application
 *
 * WebSocket client for real-time communication with Claude-powered
 * driver creation agent. Handles message streaming, tool execution
 * status, code preview, and validation results.
 */

// ================================
// State Management
// ================================

const state = {
    ws: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    currentAgentMessage: null,
    messageBuffer: '',
    conversationHistory: [],
    generatedCode: null,
    todoItems: [],
    validationResults: null,
    tokenUsage: {
        input: 0,
        output: 0,
        cacheRead: 0,
        total: 0
    }
};

// ================================
// DOM Elements
// ================================

const elements = {
    // Connection
    statusIndicator: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),

    // Chat
    chatMessages: document.getElementById('chat-messages'),
    messageInput: document.getElementById('message-input'),
    sendBtn: document.getElementById('send-btn'),
    clearBtn: document.getElementById('clear-btn'),

    // Tabs
    tabs: document.querySelectorAll('.tab'),
    tabPanels: document.querySelectorAll('.tab-panel'),

    // Code Preview
    codePreview: document.getElementById('code-preview'),
    downloadBtn: document.getElementById('download-btn'),

    // TODO List
    todoList: document.getElementById('todo-list'),
    todoProgress: document.getElementById('todo-progress'),

    // Validation
    validationResults: document.getElementById('validation-results'),
    validationStatus: document.getElementById('validation-status'),

    // Stats
    statInput: document.getElementById('stat-input'),
    statOutput: document.getElementById('stat-output'),
    statCache: document.getElementById('stat-cache'),
    statTotal: document.getElementById('stat-total')
};

// ================================
// WebSocket Connection
// ================================

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8081';
    const wsUrl = `${protocol}//${host}/ws`;

    console.log('Connecting to:', wsUrl);
    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);
        state.reconnectAttempts = 0;
    };

    state.ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);

        // Attempt reconnection
        if (state.reconnectAttempts < state.maxReconnectAttempts) {
            state.reconnectAttempts++;
            elements.statusText.textContent = `Reconnecting (${state.reconnectAttempts}/${state.maxReconnectAttempts})...`;
            setTimeout(connect, 2000);
        } else {
            elements.statusText.textContent = 'Connection failed';
        }
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    state.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleMessage(data);
        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    };
}

function updateConnectionStatus(connected) {
    if (connected) {
        elements.statusIndicator.classList.add('connected');
        elements.statusIndicator.classList.remove('disconnected');
        elements.statusText.textContent = 'Connected';
        elements.sendBtn.disabled = false;
    } else {
        elements.statusIndicator.classList.remove('connected');
        elements.statusIndicator.classList.add('disconnected');
        elements.statusText.textContent = 'Disconnected';
        elements.sendBtn.disabled = true;
    }
}

// ================================
// Message Handling
// ================================

function handleMessage(data) {
    console.log('Received message:', data.type, data);

    switch (data.type) {
        case 'agent_message':
            // Complete message (non-streaming fallback)
            finalizeAgentMessage();
            addAgentMessage(data.content);
            hideTypingIndicator();
            break;

        case 'agent_delta':
            // Streaming text chunk
            if (data.delta) {
                appendAgentDelta(data.delta);
            }
            break;

        case 'status':
            // Status update
            if (data.content) {
                console.log('Status:', data.content);
            }
            break;

        case 'tool':
            // Tool execution status
            addToolBadge(data.tool, data.status, data.input);
            break;

        case 'tool_result':
            // Tool execution result
            if (data.tool === 'generate_driver_scaffold' && data.success) {
                // Extract todos and file list from result
                if (data.result.todos) {
                    updateTodoList(data.result.todos);
                }
                if (data.result.file_list) {
                    updateCodePreview({
                        driver_name: data.result.driver_name,
                        output_path: data.result.output_path,
                        files: data.result.file_list
                    });
                }
            } else if (data.tool === 'validate_driver' && data.success) {
                updateValidationResults(data.result);
            }
            break;

        case 'error':
            // Error message
            addErrorMessage(data.error);
            finalizeAgentMessage();
            hideTypingIndicator();
            break;

        case 'usage':
            // Token usage statistics
            updateTokenUsage(data.usage);
            finalizeAgentMessage();
            hideTypingIndicator();
            break;

        case 'typing':
            // Typing indicator
            if (data.is_typing) {
                showTypingIndicator();
            } else {
                hideTypingIndicator();
            }
            break;

        case 'pong':
            // Keep-alive response
            break;

        default:
            console.log('Unknown message type:', data.type);
    }
}

// ================================
// Chat UI Functions
// ================================

function addUserMessage(content) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper user';

    const message = document.createElement('div');
    message.className = 'message user';
    message.textContent = content;

    wrapper.appendChild(message);
    elements.chatMessages.appendChild(wrapper);
    scrollToBottom();

    // Store in history
    state.conversationHistory.push({ role: 'user', content });
}

function addAgentMessage(content) {
    hideTypingIndicator();
    finalizeAgentMessage();

    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper agent';

    const message = document.createElement('div');
    message.className = 'message agent';

    // Render markdown
    message.innerHTML = marked.parse(content);

    // Highlight code blocks
    message.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });

    wrapper.appendChild(message);
    elements.chatMessages.appendChild(wrapper);
    scrollToBottom();

    // Store in history
    state.conversationHistory.push({ role: 'agent', content });
}

function appendAgentDelta(delta) {
    if (!state.currentAgentMessage) {
        hideTypingIndicator();

        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper agent streaming';

        const message = document.createElement('div');
        message.className = 'message agent';

        wrapper.appendChild(message);
        elements.chatMessages.appendChild(wrapper);

        state.currentAgentMessage = message;
        state.messageBuffer = '';
    }

    state.messageBuffer += delta;

    // Render markdown incrementally
    state.currentAgentMessage.innerHTML = marked.parse(state.messageBuffer);

    // Highlight code blocks
    state.currentAgentMessage.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });

    scrollToBottom();
}

function finalizeAgentMessage() {
    if (state.currentAgentMessage) {
        // Final render
        state.currentAgentMessage.innerHTML = marked.parse(state.messageBuffer);

        // Highlight code blocks
        state.currentAgentMessage.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });

        // Remove streaming class
        const wrapper = state.currentAgentMessage.closest('.streaming');
        if (wrapper) {
            wrapper.classList.remove('streaming');
        }

        // Store in history
        state.conversationHistory.push({ role: 'agent', content: state.messageBuffer });

        // Reset state
        state.currentAgentMessage = null;
        state.messageBuffer = '';
    }
}

function showTypingIndicator() {
    // Remove existing typing indicator
    hideTypingIndicator();

    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper agent typing-wrapper';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    wrapper.appendChild(indicator);
    elements.chatMessages.appendChild(wrapper);
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = elements.chatMessages.querySelector('.typing-wrapper');
    if (indicator) {
        indicator.remove();
    }
}

function addToolBadge(toolName, status, input) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper agent';

    const badge = document.createElement('div');
    badge.className = `tool-badge ${status}`;

    const icon = status === 'running' ? '⚙️' :
                 status === 'completed' ? '✅' :
                 status === 'failed' ? '❌' : '🔧';

    const statusText = status.charAt(0).toUpperCase() + status.slice(1);

    let displayText = `${icon} ${toolName} - ${statusText}`;

    // Add input preview for some tools
    if (input && status === 'running') {
        const inputPreview = typeof input === 'string' ? input : JSON.stringify(input);
        if (inputPreview.length > 50) {
            displayText += `: ${inputPreview.substring(0, 50)}...`;
        } else {
            displayText += `: ${inputPreview}`;
        }
    }

    badge.textContent = displayText;

    wrapper.appendChild(badge);
    elements.chatMessages.appendChild(wrapper);
    scrollToBottom();
}

function addErrorMessage(error) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper agent';

    const message = document.createElement('div');
    message.className = 'message agent';
    message.style.borderLeft = '4px solid var(--accent-red)';
    message.innerHTML = `<strong style="color: var(--accent-red);">Error:</strong> ${escapeHtml(error)}`;

    wrapper.appendChild(message);
    elements.chatMessages.appendChild(wrapper);
    scrollToBottom();
}

function scrollToBottom() {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

// ================================
// Code Preview
// ================================

function updateCodePreview(data) {
    if (!data) return;

    state.generatedCode = data;

    elements.codePreview.innerHTML = '';

    // Show driver info
    if (data.driver_name) {
        const info = document.createElement('div');
        info.style.marginBottom = '20px';
        info.innerHTML = `
            <h3>✅ Driver Generated: ${data.driver_name}</h3>
            <p><strong>Output Path:</strong> <code>${data.output_path}</code></p>
        `;
        elements.codePreview.appendChild(info);
    }

    // Show file list
    if (data.files && data.files.length > 0) {
        const fileList = document.createElement('div');
        fileList.innerHTML = '<h4>Generated Files:</h4>';
        const ul = document.createElement('ul');
        ul.style.listStyle = 'none';
        ul.style.padding = '0';

        data.files.forEach(file => {
            const li = document.createElement('li');
            li.style.padding = '5px 0';
            li.innerHTML = `📄 ${file}`;
            ul.appendChild(li);
        });

        fileList.appendChild(ul);
        elements.codePreview.appendChild(fileList);
    } else {
        // Fallback to JSON display
        const pre = document.createElement('pre');
        const codeElement = document.createElement('code');
        codeElement.className = 'language-python';
        codeElement.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
        pre.appendChild(codeElement);
        elements.codePreview.appendChild(pre);

        // Highlight syntax
        hljs.highlightElement(codeElement);
    }

    // Enable download button
    elements.downloadBtn.disabled = false;
}

// ================================
// TODO List
// ================================

function updateTodoList(todos) {
    if (!todos || todos.length === 0) {
        elements.todoList.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M2.5 1a1 1 0 0 0-1 1v1a1 1 0 0 0 1 1H3v9a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V4h.5a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H10a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1H2.5zm3 4a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-1 0v-7a.5.5 0 0 1 .5-.5zM8 5a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-1 0v-7A.5.5 0 0 1 8 5zm3 .5v7a.5.5 0 0 1-1 0v-7a.5.5 0 0 1 1 0z"/>
                </svg>
                <p>No TODO items yet</p>
            </div>
        `;
        return;
    }

    state.todoItems = todos;

    elements.todoList.innerHTML = '';

    todos.forEach((item, index) => {
        const todoItem = document.createElement('div');
        todoItem.className = `todo-item ${item.completed ? 'completed' : ''}`;

        const checkbox = document.createElement('div');
        checkbox.className = `todo-checkbox ${item.completed ? 'checked' : ''}`;
        checkbox.onclick = () => toggleTodo(index);

        const content = document.createElement('div');
        content.className = 'todo-content';
        content.style.flex = '1';

        // Extract TODO text from various formats
        const todoText = item.description || item.text || item.content || item;

        // If we have file/line info, show it
        if (item.file || item.line) {
            const location = document.createElement('div');
            location.style.fontSize = '0.85em';
            location.style.color = '#888';
            location.style.marginBottom = '4px';
            location.textContent = `${item.file || ''}${item.line ? ':' + item.line : ''}`;
            content.appendChild(location);
        }

        const text = document.createElement('div');
        text.className = 'todo-text';
        text.textContent = todoText;
        content.appendChild(text);

        todoItem.appendChild(checkbox);
        todoItem.appendChild(content);
        elements.todoList.appendChild(todoItem);
    });

    // Update progress
    const completed = todos.filter(t => t.completed).length;
    elements.todoProgress.textContent = `${completed}/${todos.length}`;
}

function toggleTodo(index) {
    if (state.todoItems[index]) {
        state.todoItems[index].completed = !state.todoItems[index].completed;
        updateTodoList(state.todoItems);
    }
}

// ================================
// Validation Results
// ================================

function updateValidationResults(results) {
    if (!results) return;

    state.validationResults = results;

    elements.validationResults.innerHTML = '';

    const checks = results.checks || results.results || [];
    const passed = checks.filter(c => c.passed || c.status === 'pass').length;
    const total = checks.length;

    // Update status
    const allPassed = passed === total;
    elements.validationStatus.textContent = allPassed ? `✅ ${passed}/${total} Passed` : `❌ ${passed}/${total} Passed`;
    elements.validationStatus.className = `validation-status ${allPassed ? 'pass' : 'fail'}`;

    // Render checks
    checks.forEach(check => {
        const isPassed = check.passed || check.status === 'pass';

        const item = document.createElement('div');
        item.className = 'validation-item';

        const icon = document.createElement('div');
        icon.className = `validation-icon ${isPassed ? 'pass' : 'fail'}`;
        icon.textContent = isPassed ? '✅' : '❌';

        const content = document.createElement('div');
        content.className = 'validation-content';

        const label = document.createElement('div');
        label.className = 'validation-label';
        label.textContent = check.name || check.label || 'Check';

        const description = document.createElement('div');
        description.className = 'validation-description';
        description.textContent = check.message || check.description || (isPassed ? 'Passed' : 'Failed');

        content.appendChild(label);
        content.appendChild(description);

        item.appendChild(icon);
        item.appendChild(content);

        elements.validationResults.appendChild(item);
    });
}

// ================================
// Token Usage
// ================================

function updateTokenUsage(usage) {
    if (!usage) return;

    state.tokenUsage = {
        input: usage.total_input_tokens || usage.input_tokens || 0,
        output: usage.total_output_tokens || usage.output_tokens || 0,
        cacheRead: usage.total_cache_read_tokens || usage.cache_read_tokens || 0,
        total: (usage.total_input_tokens || 0) + (usage.total_output_tokens || 0)
    };

    elements.statInput.textContent = formatNumber(state.tokenUsage.input);
    elements.statOutput.textContent = formatNumber(state.tokenUsage.output);
    elements.statCache.textContent = formatNumber(state.tokenUsage.cacheRead);
    elements.statTotal.textContent = formatNumber(state.tokenUsage.total);
}

// ================================
// User Actions
// ================================

function sendMessage() {
    const content = elements.messageInput.value.trim();
    if (!content || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;

    // Add user message to UI
    addUserMessage(content);

    // Show typing indicator
    showTypingIndicator();

    // Send to server
    state.ws.send(JSON.stringify({
        type: 'message',
        content: content
    }));

    // Clear input
    elements.messageInput.value = '';
    autoResizeTextarea();
    elements.messageInput.focus();
}

function clearConversation() {
    if (!confirm('Clear the entire conversation?')) return;

    // Keep welcome message, remove everything else
    const messages = elements.chatMessages.querySelectorAll('.message-wrapper:not(.welcome-message)');
    messages.forEach(msg => msg.remove());

    // Reset state
    state.conversationHistory = [];
    state.currentAgentMessage = null;
    state.messageBuffer = '';
    state.generatedCode = null;
    state.todoItems = [];
    state.validationResults = null;

    // Reset UI
    elements.codePreview.innerHTML = `
        <div class="empty-state">
            <svg width="48" height="48" fill="currentColor" viewBox="0 0 16 16">
                <path d="M10.478 1.647a.5.5 0 1 0-.956-.294l-4 13a.5.5 0 0 0 .956.294l4-13zM4.854 4.146a.5.5 0 0 1 0 .708L1.707 8l3.147 3.146a.5.5 0 0 1-.708.708l-3.5-3.5a.5.5 0 0 1 0-.708l3.5-3.5a.5.5 0 0 1 .708 0zm6.292 0a.5.5 0 0 0 0 .708L14.293 8l-3.147 3.146a.5.5 0 0 0 .708.708l3.5-3.5a.5.5 0 0 0 0-.708l-3.5-3.5a.5.5 0 0 0-.708 0z"/>
            </svg>
            <p>No driver code generated yet</p>
        </div>
    `;
    elements.downloadBtn.disabled = true;

    updateTodoList([]);
    elements.validationResults.innerHTML = `
        <div class="empty-state">
            <svg width="48" height="48" fill="currentColor" viewBox="0 0 16 16">
                <path d="M10.067.87a2.89 2.89 0 0 0-4.134 0l-.622.638-.89-.011a2.89 2.89 0 0 0-2.924 2.924l.01.89-.636.622a2.89 2.89 0 0 0 0 4.134l.637.622-.011.89a2.89 2.89 0 0 0 2.924 2.924l.89-.01.622.636a2.89 2.89 0 0 0 4.134 0l.622-.637.89.011a2.89 2.89 0 0 0 2.924-2.924l-.01-.89.636-.622a2.89 2.89 0 0 0 0-4.134l-.637-.622.011-.89a2.89 2.89 0 0 0-2.924-2.924l-.89.01-.622-.636zm.287 5.984-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7 8.793l2.646-2.647a.5.5 0 0 1 .708.708z"/>
            </svg>
            <p>No validation results yet</p>
        </div>
    `;
    elements.validationStatus.textContent = '';
}

function downloadDriver() {
    if (!state.generatedCode) return;

    const code = typeof state.generatedCode === 'string'
        ? state.generatedCode
        : JSON.stringify(state.generatedCode, null, 2);

    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'driver.py';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ================================
// UI Helpers
// ================================

function switchTab(tabName) {
    // Update tabs
    elements.tabs.forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    // Update panels
    elements.tabPanels.forEach(panel => {
        if (panel.id === `${tabName}-tab`) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });
}

function autoResizeTextarea() {
    const textarea = elements.messageInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

function formatNumber(num) {
    return num.toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ================================
// Event Listeners
// ================================

// Send message
elements.sendBtn.addEventListener('click', sendMessage);
elements.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Auto-resize textarea
elements.messageInput.addEventListener('input', autoResizeTextarea);

// Clear conversation
elements.clearBtn.addEventListener('click', clearConversation);

// Tab switching
elements.tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        switchTab(tab.dataset.tab);
    });
});

// Download driver
elements.downloadBtn.addEventListener('click', downloadDriver);

// Welcome message quick actions
elements.chatMessages.addEventListener('click', (e) => {
    const listItem = e.target.closest('.message.welcome li');
    if (listItem) {
        elements.messageInput.value = listItem.textContent;
        elements.messageInput.focus();
        autoResizeTextarea();
    }
});

// ================================
// Initialize
// ================================

function initialize() {
    console.log('Initializing Driver Creator Agent...');

    // Connect WebSocket
    connect();

    // Focus input
    elements.messageInput.focus();

    // Setup keep-alive ping
    setInterval(() => {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000); // 30 seconds
}

// Start the application
initialize();
