/**
 * AI Chatbot Widget for PI-LMS
 * Provides real-time chat functionality for lesson pages
 */

class ChatbotWidget {
    constructor(lessonId, userId = null) {
        this.lessonId = lessonId;
        this.userId = userId;
        this.sessionId = null;
        this.websocket = null;
        this.isConnected = false;
        this.isExpanded = false;
        this.isTyping = false;
        this.messages = [];
        this.currentMode = 'default';
        
        // Get the current hostname and protocol
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = window.location.port ? `:${window.location.port}` : '';
        const baseUrl = `${protocol}//${host}${port}`;
        
        // Determine AI HTTP API base
        const aiBaseUrl = window.API_BASE_URL || 'http://localhost:8000';

        // Derive sensible WebSocket base URL
        let websocketBase;
        if (window.WEBSOCKET_URL) {
            // Explicitly provided at runtime (preferred)
            websocketBase = window.WEBSOCKET_URL;
        } else if (/^https?:\/\//.test(aiBaseUrl)) {
            // Convert the http(s) scheme of the AI base URL to ws(s)
            websocketBase = aiBaseUrl.replace(/^http/, 'ws');
        } else {
            // Fallback to same host but default WS port 8000
            websocketBase = `${protocol}//${host}:8000`;
        }

        // Configuration
        this.config = {
            aiServerUrl: aiBaseUrl,
            websocketUrl: websocketBase,
            reconnectInterval: 5000,
            maxReconnectAttempts: 5,
            typingTimeout: 3000
        };
        
        this.reconnectAttempts = 0;
        this.typingTimer = null;
        
        this.init();
    }
    
    async init() {
        await this.createChatWidget();
        await this.initializeChat();
        this.attachEventListeners();
        console.log('Chatbot widget initialized for lesson:', this.lessonId);
    }
    
    async createChatWidget() {
        // Create chat widget HTML structure
        const widgetHTML = `
            <div id="chatbot-widget" class="chatbot-widget collapsed">
                <!-- Floating Chat Button -->
                <div id="chat-toggle-btn" class="chat-toggle-btn">
                    <div class="chat-icon">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a8.013 8.013 0 01-5.314-2.017L3 21l2.983-4.686A8.014 8.014 0 013 12c0-4.418 3.582-8 8-8s8 3.582 8 8z"/>
                        </svg>
                    </div>
                    <div class="notification-badge" id="chat-notification" style="display: none;">
                        <span id="notification-count">1</span>
                    </div>
                </div>
                
                <!-- Chat Window -->
                <div id="chat-window" class="chat-window">
                    <!-- Chat Header -->
                    <div class="chat-header">
                        <div class="chat-title">
                            <div class="ai-avatar">🤖</div>
                            <div class="chat-info">
                                <h4>AI Learning Assistant</h4>
                                <div class="connection-status" id="connection-status">
                                    <span class="status-indicator connecting"></span>
                                    <span class="status-text">Connecting...</span>
                                </div>
                            </div>
                        </div>
                        <div class="chat-controls">
                            <button id="chat-mode-btn" class="mode-btn" title="Switch chat mode">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                            </button>
                            <button id="chat-minimize-btn" class="minimize-btn" title="Minimize chat">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Chat Mode Selector -->
                    <div id="chat-mode-selector" class="chat-mode-selector" style="display: none;">
                        <div class="mode-option" data-mode="default">
                            <span class="mode-icon">💬</span>
                            <div class="mode-info">
                                <span class="mode-name">General Chat</span>
                                <span class="mode-desc">Ask questions about the lesson</span>
                            </div>
                        </div>
                        <div class="mode-option" data-mode="quiz_mode">
                            <span class="mode-icon">🧠</span>
                            <div class="mode-info">
                                <span class="mode-name">Quiz Mode</span>
                                <span class="mode-desc">Practice questions and assessments</span>
                            </div>
                        </div>
                        <div class="mode-option" data-mode="explanation">
                            <span class="mode-icon">📚</span>
                            <div class="mode-info">
                                <span class="mode-name">Explanation</span>
                                <span class="mode-desc">Detailed concept explanations</span>
                            </div>
                        </div>
                        <div class="mode-option" data-mode="study_guide">
                            <span class="mode-icon">📝</span>
                            <div class="mode-info">
                                <span class="mode-name">Study Guide</span>
                                <span class="mode-desc">Study plans and summaries</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Chat Messages -->
                    <div id="chat-messages" class="chat-messages">
                        <div class="welcome-message">
                            <div class="ai-avatar">🤖</div>
                            <div class="message-content">
                                <p>Hello! I'm your AI learning assistant. I can help you understand this lesson, answer questions, and create practice exercises. What would you like to explore?</p>
                                <div class="quick-actions">
                                    <button class="quick-action-btn" data-action="summarize">📄 Summarize lesson</button>
                                    <button class="quick-action-btn" data-action="quiz">🧠 Create quiz</button>
                                    <button class="quick-action-btn" data-action="explain">💡 Explain concepts</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Typing Indicator -->
                    <div id="typing-indicator" class="typing-indicator" style="display: none;">
                        <div class="ai-avatar">🤖</div>
                        <div class="typing-animation">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                    
                    <!-- Smart Suggestions -->
                    <div id="smart-suggestions" class="smart-suggestions" style="display: none;">
                        <div class="suggestions-header">Suggested questions:</div>
                        <div class="suggestions-list"></div>
                    </div>
                    
                    <!-- Related Lessons -->
                    <div id="related-lessons" class="related-lessons" style="display: none;">
                        <div class="related-header">Related lessons:</div>
                        <div class="related-list"></div>
                    </div>
                    
                    <!-- Chat Input -->
                    <div class="chat-input-area">
                        <div class="input-container">
                            <textarea 
                                id="chat-input" 
                                class="chat-input" 
                                placeholder="Ask me anything about this lesson..."
                                rows="1"
                                maxlength="1000"
                            ></textarea>
                            <button id="chat-send-btn" class="send-btn" disabled>
                                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                                </svg>
                            </button>
                        </div>
                        <div class="input-footer">
                            <span class="char-count">0/1000</span>
                            <span class="current-mode">Mode: <span id="current-mode-text">General Chat</span></span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add widget to page
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
    }
    
    async initializeChat() {
        try {
            // Create session
            this.sessionId = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            // Get lesson context
            await this.loadLessonContext();
            
            // Initialize WebSocket connection
            await this.connectWebSocket();
            
        } catch (error) {
            console.error('Failed to initialize chat:', error);
            this.showConnectionError();
        }
    }
    
    async loadLessonContext() {
        try {
            // Get auth token from the frontend
            const authToken = await this.getAuthToken();
            const headers = {
                'Content-Type': 'application/json'
            };
            
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }
            
            const response = await fetch(`${this.config.aiServerUrl}/api/chat/context/${this.lessonId}`, {
                headers: headers
            });
            
            if (response.ok) {
                this.lessonContext = await response.json();
                console.log('Lesson context loaded:', this.lessonContext);
            }
        } catch (error) {
            console.warn('Failed to load lesson context:', error);
        }
    }
    
    async getAuthToken() {
        try {
            // Try to get auth token from the frontend API
            const response = await fetch('/api/token');
            if (response.ok) {
                const data = await response.json();
                return data.token;
            }
        } catch (error) {
            console.warn('Failed to get auth token:', error);
        }
        return null;
    }
    
    async connectWebSocket() {
        try {
            // Get auth token for WebSocket connection
            const authToken = await this.getAuthToken();
            const wsUrl = authToken
                ? `${this.config.websocketUrl}/ws/chat/${this.sessionId}?token=${encodeURIComponent(authToken)}`
                : `${this.config.websocketUrl}/ws/chat/${this.sessionId}`;
            
            console.log('Connecting WebSocket with auth token:', authToken ? 'Yes' : 'No');
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected', 'Connected');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus('disconnected', 'Disconnected');
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('error', 'Connection error');
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.showConnectionError();
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'token':
                this.handleStreamingToken(data);
                break;
            case 'complete':
                this.handleCompleteResponse(data);
                break;
            case 'response':
                this.handleNonStreamingResponse(data);
                break;
            case 'typing':
                this.showTypingIndicator();
                break;
            case 'error':
                this.handleErrorResponse(data);
                break;
            case 'pong':
                // Handle ping response
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
    
    handleStreamingToken(data) {
        if (!this.currentStreamingMessage) {
            this.currentStreamingMessage = this.addMessage('assistant', '', data.timestamp);
        }
        
        const messageElement = this.currentStreamingMessage.querySelector('.message-text');
        messageElement.textContent += data.content;
        this.scrollToBottom();
    }
    
    handleCompleteResponse(data) {
        this.hideTypingIndicator();
        
        if (this.currentStreamingMessage) {
            // Update final message content
            const messageElement = this.currentStreamingMessage.querySelector('.message-text');
            messageElement.textContent = data.content;
            this.currentStreamingMessage = null;
        } else {
            // Add complete message
            this.addMessage('assistant', data.content, data.timestamp);
        }
        
        // Show related lessons and suggestions
        this.showRelatedLessons(data.related_lessons || []);
        this.showSmartSuggestions(data.suggestions || []);
        
        this.scrollToBottom();
    }
    
    handleNonStreamingResponse(data) {
        this.hideTypingIndicator();
        this.addMessage('assistant', data.content, data.timestamp);
        this.showRelatedLessons(data.related_lessons || []);
        this.showSmartSuggestions(data.suggestions || []);
        this.scrollToBottom();
    }
    
    handleErrorResponse(data) {
        this.hideTypingIndicator();
        this.addMessage('assistant', data.content || 'Sorry, I encountered an error. Please try again.', data.timestamp, 'error');
        this.scrollToBottom();
    }
    
    addMessage(role, content, timestamp = null, type = 'normal') {
        const messagesContainer = document.getElementById('chat-messages');
        const messageTime = timestamp ? new Date(timestamp) : new Date();
        
        const messageHTML = `
            <div class="chat-message ${role}-message ${type}">
                <div class="message-avatar">
                    ${role === 'user' ? '👤' : '🤖'}
                </div>
                <div class="message-content">
                    <div class="message-text">${this.formatMessage(content)}</div>
                    <div class="message-time">${this.formatTime(messageTime)}</div>
                </div>
            </div>
        `;
        
        messagesContainer.insertAdjacentHTML('beforeend', messageHTML);
        const messageElement = messagesContainer.lastElementChild;
        
        // Add to messages array
        this.messages.push({
            role,
            content,
            timestamp: messageTime,
            type
        });
        
        return messageElement;
    }
    
    formatMessage(content) {
        // Basic message formatting
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }
    
    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    showTypingIndicator() {
        document.getElementById('typing-indicator').style.display = 'flex';
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        document.getElementById('typing-indicator').style.display = 'none';
    }
    
    showSmartSuggestions(suggestions) {
        const suggestionsContainer = document.getElementById('smart-suggestions');
        const suggestionsList = suggestionsContainer.querySelector('.suggestions-list');
        
        if (suggestions.length > 0) {
            suggestionsList.innerHTML = suggestions.map(suggestion => 
                `<button class="suggestion-btn" data-suggestion="${suggestion}">${suggestion}</button>`
            ).join('');
            suggestionsContainer.style.display = 'block';
        } else {
            suggestionsContainer.style.display = 'none';
        }
    }
    
    showRelatedLessons(lessons) {
        const relatedContainer = document.getElementById('related-lessons');
        const relatedList = relatedContainer.querySelector('.related-list');
        
        if (lessons.length > 0) {
            relatedList.innerHTML = lessons.map(lesson => 
                `<a href="/lessons/${lesson.id}" class="related-lesson-link" target="_blank">
                    <span class="lesson-icon">📚</span>
                    <span class="lesson-title">${lesson.title}</span>
                </a>`
            ).join('');
            relatedContainer.style.display = 'block';
        } else {
            relatedContainer.style.display = 'none';
        }
    }
    
    attachEventListeners() {
        // Toggle chat widget
        document.getElementById('chat-toggle-btn').addEventListener('click', () => {
            this.toggleChat();
        });
        
        // Minimize chat
        document.getElementById('chat-minimize-btn').addEventListener('click', () => {
            this.minimizeChat();
        });
        
        // Mode selector
        document.getElementById('chat-mode-btn').addEventListener('click', () => {
            this.toggleModeSelector();
        });
        
        // Mode selection
        document.querySelectorAll('.mode-option').forEach(option => {
            option.addEventListener('click', () => {
                this.selectMode(option.dataset.mode);
            });
        });
        
        // Chat input
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');
        
        chatInput.addEventListener('input', () => {
            this.handleInputChange();
        });
        
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        sendBtn.addEventListener('click', () => {
            this.sendMessage();
        });
        
        // Quick actions
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-action-btn')) {
                this.handleQuickAction(e.target.dataset.action);
            }
            
            if (e.target.classList.contains('suggestion-btn')) {
                this.sendSuggestion(e.target.dataset.suggestion);
            }
        });
        
        // Auto-resize textarea
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        });
    }
    
    toggleChat() {
        const widget = document.getElementById('chatbot-widget');
        const isCollapsed = widget.classList.contains('collapsed');
        
        if (isCollapsed) {
            this.expandChat();
        } else {
            this.minimizeChat();
        }
    }
    
    expandChat() {
        const widget = document.getElementById('chatbot-widget');
        widget.classList.remove('collapsed');
        this.isExpanded = true;
        
        // Hide notification badge
        document.getElementById('chat-notification').style.display = 'none';
        
        // Focus input
        setTimeout(() => {
            document.getElementById('chat-input').focus();
        }, 300);
    }
    
    minimizeChat() {
        const widget = document.getElementById('chatbot-widget');
        widget.classList.add('collapsed');
        this.isExpanded = false;
        
        // Hide mode selector
        document.getElementById('chat-mode-selector').style.display = 'none';
    }
    
    toggleModeSelector() {
        const selector = document.getElementById('chat-mode-selector');
        selector.style.display = selector.style.display === 'none' ? 'block' : 'none';
    }
    
    selectMode(mode) {
        this.currentMode = mode;
        document.getElementById('current-mode-text').textContent = this.getModeDisplayName(mode);
        document.getElementById('chat-mode-selector').style.display = 'none';
        
        // Add mode change message
        this.addMessage('system', `Switched to ${this.getModeDisplayName(mode)} mode`, null, 'system');
        this.scrollToBottom();
    }
    
    getModeDisplayName(mode) {
        const modeNames = {
            'default': 'General Chat',
            'quiz_mode': 'Quiz Mode',
            'explanation': 'Explanation',
            'study_guide': 'Study Guide',
            'discussion': 'Discussion'
        };
        return modeNames[mode] || 'General Chat';
    }
    
    handleInputChange() {
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');
        const charCount = document.querySelector('.char-count');
        
        const length = input.value.length;
        charCount.textContent = `${length}/1000`;
        
        sendBtn.disabled = length === 0 || !this.isConnected;
        
        // Auto-resize
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }
    
    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (!message || !this.isConnected) return;
        
        // Add user message
        this.addMessage('user', message);
        input.value = '';
        this.handleInputChange();
        
        // Hide suggestions and related lessons
        document.getElementById('smart-suggestions').style.display = 'none';
        document.getElementById('related-lessons').style.display = 'none';
        
        // Get the current lesson context
        const lessonContext = this.lessonContext || {};
        
        // Send via WebSocket
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'message',
                content: message,
                lesson_id: this.lessonId,
                mode: this.currentMode,
                context: {
                    lesson_title: lessonContext.lesson?.title || '',
                    lesson_content: lessonContext.text_content || '',
                    lesson_objectives: lessonContext.lesson?.objectives || []
                }
            }));
        }
        
        this.scrollToBottom();
    }
    
    sendSuggestion(suggestion) {
        document.getElementById('chat-input').value = suggestion;
        this.handleInputChange();
        this.sendMessage();
    }
    
    handleQuickAction(action) {
        const actions = {
            'summarize': 'Can you provide a summary of this lesson?',
            'quiz': 'Create some practice questions for this lesson.',
            'explain': 'Explain the main concepts in this lesson.'
        };
        
        if (actions[action]) {
            document.getElementById('chat-input').value = actions[action];
            this.handleInputChange();
            this.sendMessage();
        }
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    updateConnectionStatus(status, text) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        
        statusIndicator.className = `status-indicator ${status}`;
        statusText.textContent = text;
        
        // Update send button state
        const sendBtn = document.getElementById('chat-send-btn');
        sendBtn.disabled = status !== 'connected' || document.getElementById('chat-input').value.length === 0;
    }
    
    showConnectionError() {
        this.addMessage('system', 'Connection to AI service failed. Some features may not work properly.', null, 'error');
        this.updateConnectionStatus('error', 'Connection failed');
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.updateConnectionStatus('connecting', `Reconnecting... (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, this.config.reconnectInterval);
        } else {
            this.updateConnectionStatus('error', 'Connection failed');
            this.addMessage('system', 'Unable to connect to AI service. Please refresh the page to try again.', null, 'error');
        }
    }
    
    // Cleanup method
    destroy() {
        if (this.websocket) {
            this.websocket.close();
        }
        
        const widget = document.getElementById('chatbot-widget');
        if (widget) {
            widget.remove();
        }
    }
}

// Global instance
window.ChatbotWidget = ChatbotWidget;