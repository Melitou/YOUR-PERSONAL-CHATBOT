import React, { useState } from 'react';
import LoadedChatbotStore from '../stores/LoadedChatbotStore';

interface Message {
    id: number;
    text: string;
    sender: 'user' | 'agent';
    timestamp: Date;
}

const ChatComponent = () => {
    
    const { isThinking, setIsThinking } = LoadedChatbotStore();

    const [messages, setMessages] = useState<Message[]>([
        {
            id: 1,
            text: "Hello! I'm your AI assistant. How can I help you today?",
            sender: 'agent',
            timestamp: new Date()
        },
        {
            id: 2,
            text: "Hi there! Can you help me with some questions?",
            sender: 'user',
            timestamp: new Date()
        },
        {
            id: 3,
            text: "Of course! I'd be happy to help you with any questions you have. What would you like to know?",
            sender: 'agent',
            timestamp: new Date()
        }
    ]);
    
    const [inputMessage, setInputMessage] = useState('');

    // Dummy agent responses for demonstration
    const dummyResponses = [
        "That's an interesting question! Let me think about that...",
        "I understand what you're asking. Here's what I think...",
        "Great point! From my perspective...",
        "That's a common question. The answer is...",
        "I'm glad you asked! Here's my response...",
        "Absolutely! I can help you with that...",
        "That's a fascinating topic. Let me explain...",
        "I see what you mean. My suggestion would be..."
    ];

    // const handleSendMessage = () => {
    //     if (inputMessage.trim() === '') return;

    //     // Add user message
    //     const userMessage: Message = {
    //         id: messages.length + 1,
    //         text: inputMessage,
    //         sender: 'user',
    //         timestamp: new Date()
    //     };

    //     setMessages(prev => [...prev, userMessage]);
    //     setInputMessage('');

    //     // Simulate agent response after a short delay
    //     setTimeout(() => {
    //         const randomResponse = dummyResponses[Math.floor(Math.random() * dummyResponses.length)];
    //         const agentMessage: Message = {
    //             id: messages.length + 2,
    //             text: randomResponse,
    //             sender: 'agent',
    //             timestamp: new Date()
    //         };
    //         setMessages(prev => [...prev, agentMessage]);
    //     }, 1000);
    // };

    const handleSendMessage = () => {
        setIsThinking(true);
        setTimeout(() => {
            setIsThinking(false);
        }, 5000);
    };  

    return (
        <div className="flex flex-col flex-1 min-h-0 w-full sm:w-2/3">
            {/* Chat Messages Container */}
            <div className="flex-1 overflow-y-auto p-10 space-y-4 w-full">
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg shadow-sm ${
                                message.sender === 'user'
                                    ? 'bg-[#f4f4f4] text-black rounded-bl-none'
                                    : 'bg-white text-gray-800 border border-gray-200 rounded-br-none'
                            }`}
                        >
                            <p className="text-sm">{message.text}</p>
                            <p className={`text-xs mt-1 text-gray-500 ${
                                message.sender === 'user' ? 'text-blue-100' : 'text-gray-500'
                            }`}>
                                {message.timestamp.toLocaleTimeString([], { 
                                    hour: '2-digit', 
                                    minute: '2-digit' 
                                })}
                            </p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Message Input Bar */}
            <div className="border rounded-xl border-gray-200 bg-white p-3 w-full">
                <div className="flex items-center space-x-3">
                    <div className="flex-1 relative">
                        <textarea
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            placeholder="Type your message here..."
                            className="w-full px-4 py-2 text-black border border-gray-300 rounded-lg resize-none outline-none border-transparent focus:border-transparent"
                            rows={1}
                            style={{ minHeight: '40px', maxHeight: '120px' }}
                        />
                    </div>
                    {isThinking ? (
                        <div className="justify-center p-3 items-center text-black rounded-lg hover:bg-opacity-10 transition-colors">
                            <div className="flex space-x-1">
                                <div className="w-2 h-2 bg-black rounded-full animate-pulse"></div>
                                <div className="w-2 h-2 bg-black rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                                <div className="w-2 h-2 bg-black rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                            </div>
                        </div>
                    ) : (
                        <button
                            onClick={handleSendMessage}
                            className="justify-center p-3 items-center justify-center text-black rounded-lg hover:bg-[#f4f4f4] hover:bg-opacity-10 transition-colors"
                        >
                            <span className="material-symbols-outlined text-black text-5xl">
                                send
                            </span>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ChatComponent;
