import { useState } from 'react';
import LoadedChatbotStore from '../stores/LoadedChatbotStore';

interface Message {
    id: number;
    text: string;
    sender: 'user' | 'agent';
    timestamp: Date;
}

const ChatComponent = () => {
    
    const { isThinking, setIsThinking, loadedChatbot } = LoadedChatbotStore((state: any) => state);

    const [messages] = useState<Message[]>([
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

    const handleSendMessage = () => {
        setIsThinking(true);
        setTimeout(() => {
            setIsThinking(false);
        }, 5000);
    };  

    return (
        <div className="flex flex-col flex-1 h-full w-full max-w-5xl mx-auto">
            {/* Chatbot Header */}
            <div className="bg-white border-b border-gray-200 px-4 py-4">
                <div className="flex items-center space-x-3 min-w-0">
                    <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center">
                        <span className="material-symbols-outlined text-white text-xl">
                            smart_toy
                        </span>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-semibold text-gray-900 truncate">
                            {loadedChatbot?.name || 'AI Assistant'}
                        </h2>
                        {loadedChatbot?.description && (
                            <p className="text-sm text-gray-500 truncate">
                                {loadedChatbot.description}
                            </p>
                        )}
                    </div>
                    <div className="flex items-center space-x-2 flex-shrink-0">
                        <div className={`w-3 h-3 rounded-full ${loadedChatbot?.isActive ? 'bg-green-400' : 'bg-gray-300'}`}></div>
                        <span className="text-sm text-gray-500 whitespace-nowrap">
                            {loadedChatbot?.isActive ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Chat Messages Container */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
            <div className="border rounded-xl border-gray-200 bg-white p-3">
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
