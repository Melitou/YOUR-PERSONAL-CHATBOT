# Chat Client Integration Example

This document shows how the frontend should integrate with the new chat API.

## 1. Create a Chat Session

```javascript
// User selects a chatbot from the UI
const chatbotId = "selected_chatbot_id";

// Create chat session (requires JWT token in Authorization header)
const sessionResponse = await fetch(`/chatbot/${chatbotId}/session`, {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${userJwtToken}`,
        'Content-Type': 'application/json'
    }
});

const sessionData = await sessionResponse.json();
console.log(sessionData);
// {
//   "session_id": "uuid-here",
//   "conversation_id": "conversation-id",
//   "chatbot_id": "chatbot-id",
//   "chatbot_name": "My Assistant",
//   "previous_messages": [...]
// }
```

## 2. Connect to WebSocket

```javascript
// Connect to WebSocket with session ID and JWT token
const wsUrl = `ws://localhost:8000/ws/chat/${sessionData.session_id}?token=${userJwtToken}`;
const socket = new WebSocket(wsUrl);

socket.onopen = () => {
    console.log('Connected to chat');
};

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'session_info':
            console.log('Session info:', data);
            displayMessage('system', data.message);
            break;
            
        case 'message_received':
            console.log('Message acknowledged:', data.message_id);
            break;
            
        case 'response_start':
            console.log('Assistant is responding...');
            createNewAssistantMessage(); // Create empty message bubble
            break;
            
        case 'response_chunk':
            appendToAssistantMessage(data.chunk); // Append chunk to current message
            break;
            
        case 'response_complete':
            console.log('Response complete:', data.message_id);
            finalizeAssistantMessage(data.full_response);
            break;
            
        case 'error':
            console.error('Chat error:', data.message);
            displayError(data.message);
            break;
    }
};

socket.onerror = (error) => {
    console.error('WebSocket error:', error);
};

socket.onclose = () => {
    console.log('WebSocket closed');
};
```

## 3. Send Messages

```javascript
function sendMessage(messageText) {
    if (socket.readyState === WebSocket.OPEN) {
        const messageData = {
            message: messageText,
            message_type: "text"
        };
        
        socket.send(JSON.stringify(messageData));
        
        // Display user message immediately
        displayMessage('user', messageText);
    }
}

// Example usage
sendMessage("Hello, can you help me with my project?");
```

## 4. Handle Previous Messages

```javascript
// Display previous messages from the session
function displayPreviousMessages(messages) {
    messages.forEach(msg => {
        displayMessage(msg.role, msg.message, msg.created_at);
    });
}

// Call this after creating session
displayPreviousMessages(sessionData.previous_messages);
```

## 5. Close Session (Optional)

```javascript
// Gracefully close session when user navigates away
function closeSession() {
    if (sessionData?.session_id) {
        fetch(`/chatbot/session/${sessionData.session_id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${userJwtToken}`
            }
        });
    }
    
    if (socket) {
        socket.close();
    }
}

// Call on page unload
window.addEventListener('beforeunload', closeSession);
```

## WebSocket Message Types

### Client → Server
```json
{
    "message": "User's message text",
    "message_type": "text"
}
```

### Server → Client

**Session Info:**
```json
{
    "type": "session_info",
    "session_id": "uuid",
    "chatbot_name": "Assistant Name",
    "message": "Connected to Assistant. You can start chatting!"
}
```

**Message Received:**
```json
{
    "type": "message_received",
    "message_id": "msg_id",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response Streaming:**
```json
{
    "type": "response_start",
    "message": "Assistant is thinking..."
}

{
    "type": "response_chunk",
    "chunk": "Hello! I'd be happy to help"
}

{
    "type": "response_complete",
    "message_id": "msg_id",
    "timestamp": "2024-01-15T10:30:05Z",
    "full_response": "Complete response text"
}
```

**Error:**
```json
{
    "type": "error",
    "message": "Error description"
}
```

## Features Implemented

✅ **Session Management**: One active session per user  
✅ **JWT Authentication**: Both REST and WebSocket  
✅ **Message Persistence**: All messages saved to MongoDB  
✅ **Streaming Responses**: Real-time response chunks  
✅ **Conversation History**: Previous messages loaded on session creation  
✅ **RAG Integration**: Context-aware responses using uploaded documents  
✅ **Session Cleanup**: Automatic cleanup of inactive sessions  
✅ **Error Handling**: Comprehensive error handling and logging

## Security Notes

- JWT token required for all chat operations
- Sessions are user-specific (can't access other users' sessions)
- WebSocket authentication via query parameter
- Sessions automatically closed on disconnect
- Rate limiting should be implemented at the WebSocket level