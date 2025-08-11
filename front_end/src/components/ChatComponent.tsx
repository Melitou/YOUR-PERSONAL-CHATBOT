import { useState, useEffect, useRef } from 'react';
import LoadedChatbotStore from '../stores/LoadedChatbotStore';

// Typewriter component for smooth text animation
const TypewriterText = ({ text, isStreaming, speed = 25, onComplete }: { text: string, isStreaming: boolean, speed?: number, onComplete?: () => void }) => {
    const [displayedText, setDisplayedText] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);
    const previousTextRef = useRef('');
    const previousLengthRef = useRef(0);

    useEffect(() => {
        // If this is a completely new message (different text), reset everything
        if (text !== previousTextRef.current && !text.startsWith(previousTextRef.current)) {
            setCurrentIndex(0);
            setDisplayedText('');
            previousTextRef.current = text;
            previousLengthRef.current = 0;
        }
        // If text grew (streaming chunk added), continue from where we were
        else if (text.length > previousLengthRef.current) {
            previousTextRef.current = text;
            previousLengthRef.current = text.length;
        }
    }, [text]);

    useEffect(() => {
        if (isStreaming && currentIndex < text.length) {
            const timer = setTimeout(() => {
                setDisplayedText(text.slice(0, currentIndex + 1));
                setCurrentIndex(currentIndex + 1);
            }, speed);

            return () => clearTimeout(timer);
        } else if (!isStreaming) {
            // When streaming stops, show full text immediately
            setDisplayedText(text);
            setCurrentIndex(text.length);
        }
    }, [currentIndex, text, speed, isStreaming]);

    // Call onComplete when animation finishes
    useEffect(() => {
        if (!isStreaming && currentIndex >= text.length && onComplete) {
            // Small delay to ensure the final character is displayed
            const timer = setTimeout(() => {
                onComplete();
            }, 100);
            return () => clearTimeout(timer);
        }
    }, [isStreaming, currentIndex, text.length, onComplete]);

    // If not streaming, show full text immediately
    if (!isStreaming) {
        return <span>{text}</span>;
    }

    return (
        <span>
            {displayedText}
            {isStreaming && currentIndex < text.length && (
                <span className="animate-pulse text-gray-400 ml-1">|</span>
            )}
        </span>
    );
};

const ChatComponent = () => {
    
    const { isThinking, loadedChatbot, conversationMessages, sendMessage, markStreamingComplete } = LoadedChatbotStore((state: any) => state);
    
    const [inputMessage, setInputMessage] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);

    const adjustTextareaHeight = (element?: HTMLTextAreaElement) => {
        const textarea = element ?? textareaRef.current;
        if (!textarea) return;
        const computed = window.getComputedStyle(textarea);
        const lineHeight = parseFloat(computed.lineHeight || '20');
        const paddingTop = parseFloat(computed.paddingTop || '0');
        const paddingBottom = parseFloat(computed.paddingBottom || '0');
        const maxRows = 3;
        const maxHeight = lineHeight * maxRows + paddingTop + paddingBottom;
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, maxHeight);
        textarea.style.height = `${newHeight}px`;
        textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden';
    };

    useEffect(() => {
        adjustTextareaHeight();
    }, [inputMessage]);

    useEffect(() => {
        // Initialize height on mount
        adjustTextareaHeight();
    }, []);

    const handleSendMessage = () => {
        if (!inputMessage.trim()) return; // Don't send empty messages
        
        const success = sendMessage(inputMessage.trim());
        if (success) {
            setInputMessage(''); // Clear input after successful send
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
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
                {conversationMessages?.conversation_id ? (
                    <>
                        {/*Small Header that displays the conversation ID*/}
                        <div className="text-xs text-gray-500 text-center border-b border-gray-200 pb-2">
                            Loaded conversation ID: {conversationMessages.conversation_id}
                        </div>
                        {conversationMessages?.messages && conversationMessages.messages.length > 0 ? (
                            conversationMessages.messages.map((message: any, index: number) => (
                                <div
                                    key={index}
                                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg shadow-sm ${
                                            message.role === 'user'
                                                ? 'bg-[#f4f4f4] text-black rounded-bl-none'
                                                : 'bg-white text-gray-800 border border-gray-200 rounded-br-none'
                                        }`}
                                    >
                                        <p className="text-sm">
                                            <TypewriterText 
                                                text={message.message} 
                                                isStreaming={message.isStreaming || false}
                                                speed={30}
                                                onComplete={() => {
                                                    // Mark as complete when animation finishes
                                                    markStreamingComplete();
                                                }}
                                            />
                                        </p>
                                        {message.isStreaming && (
                                            <div className="flex items-center mt-2 p-2 bg-gray-100 rounded-md">
                                                <div className="flex space-x-1">
                                                    <div className="w-2 h-2 bg-black rounded-full animate-bounce"></div>
                                                    <div className="w-2 h-2 bg-black rounded-full animate-bounce" style={{ animationDelay: '0.3s', animationDuration: '1.5s' }}></div>
                                                    <div className="w-2 h-2 bg-black rounded-full animate-bounce" style={{ animationDelay: '0.6s', animationDuration: '1.5s' }}></div>
                                                </div>
                                                <span className="text-sm text-black ml-3 font-medium">Agent is thinking...</span>
                                            </div>
                                        )}
                                        <p className={`text-xs mt-1 text-gray-500 ${
                                            message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                                        }`}>
                                            {new Date(message.created_at).toLocaleTimeString([], { 
                                                hour: '2-digit', 
                                                minute: '2-digit'
                                            })}
                                        </p>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <>
                                <div className="flex justify-center items-center h-min">
                                    <p className="text-gray-500 text-sm">No messages yet</p>
                                </div>
                            </>
                        )}
                    </>
                ) : (
                    <div className="flex-1 flex items-center justify-center">
                        <div className="text-center text-gray-500">
                            <div className="text-6xl mb-4">💬</div>
                            <h3 className="text-lg font-medium mb-2">No conversation loaded</h3>
                            <p className="text-sm">Start a new conversation or select an existing one from the sidebar</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Message Input Bar */}
            {conversationMessages?.conversation_id && (
                <div className="border rounded-xl border-gray-200 bg-white p-3">
                    <div className="flex items-center space-x-3">
                        <div className="flex-1 relative">
                            <textarea
                                ref={textareaRef}
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onInput={(e) => adjustTextareaHeight(e.currentTarget)}
                                onKeyPress={handleKeyPress}
                                placeholder="Type your message here..."
                                className="w-full px-4 py-2 text-black border border-gray-300 rounded-lg resize-none outline-none border-transparent focus:border-transparent"
                                rows={1}
                                style={{ minHeight: '40px' }}
                                disabled={isThinking}
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
                                disabled={isThinking || !inputMessage.trim()}
                                className="justify-center p-3 items-center justify-center text-black rounded-lg hover:bg-[#f4f4f4] hover:bg-opacity-10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <span className="material-symbols-outlined text-black text-5xl">
                                    send
                                </span>
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ChatComponent;
