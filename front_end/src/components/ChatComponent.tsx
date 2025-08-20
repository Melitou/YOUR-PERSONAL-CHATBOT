import { useState, useEffect, useRef } from 'react';
import LoadedChatbotStore from '../stores/LoadedChatbotStore';
import { InlineThinkingComponent } from './ThoughtVisualizerComponent';

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
        <div className="w-full h-full max-w-4xl mx-auto glass-card shadow-2xl rounded-lg overflow-hidden flex flex-col border border-white/20 backdrop-blur-xl">
            {/* Chatbot Header - Fixed */}
            <div className="glass-dark px-6 py-4 border-b border-white/10 flex-shrink-0">
                <div className="flex items-center space-x-3 min-w-0">
                    <div className="w-12 h-12 glass-dark rounded-full flex items-center justify-center">
                        <span className="material-symbols-outlined glass-text text-2xl">
                            smart_toy
                        </span>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-base sm:text-lg font-medium glass-text truncate">
                            {loadedChatbot?.name || 'AI Assistant'}
                        </h2>
                        {loadedChatbot?.description && (
                            <p className="text-xs sm:text-sm glass-text opacity-70 truncate">
                                {loadedChatbot.description}
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Chat Messages Container - Scrollable Area */}
            <div className="flex-1 min-h-0 overflow-y-auto px-4 py-2 space-y-2 min-h-0">
                {conversationMessages?.conversation_id ? (
                    <>
                        {conversationMessages?.messages && conversationMessages.messages.length > 0 ? (
                            <>
                                {conversationMessages.messages.map((message: any, index: number) => (
                                    <div key={index}>
                                        <div
                                            className={`chat-message-container ${message.role === 'user' ? 'user-message-container' : 'bot-message-container'}`}
                                        >
                                            <div
                                                className={`chat-message-bubble px-5 py-3 ${message.role === 'user'
                                                    ? 'glass-card user-message-bubble'
                                                    : 'glass bot-message-bubble'
                                                    }`}
                                            >
                                                <p className="text-xs sm:text-sm glass-text">
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
                                                    <div className="flex items-center mt-3 p-3 glass-dark rounded-lg">
                                                <div className="flex space-x-1">
                                                    <div className="w-2 h-2 bg-white/70 rounded-full animate-bounce"></div>
                                                    <div className="w-2 h-2 bg-white/70 rounded-full animate-bounce" style={{ animationDelay: '0.3s', animationDuration: '1.5s' }}></div>
                                                    <div className="w-2 h-2 bg-white/70 rounded-full animate-bounce" style={{ animationDelay: '0.6s', animationDuration: '1.5s' }}></div>
                                                </div>
                                                <span className="text-xs sm:text-sm glass-text ml-3 font-medium">Agent is thinking...</span>
                                            </div>
                                        )}
                                        <p className="text-xs sm:text-sm mt-2 glass-text opacity-60">
                                            {new Date(message.created_at).toLocaleTimeString([], {
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            })}
                                        </p>
                                    </div>
                                </div>
                                
                            </div>
                        ))}
                        
                        {/* Show inline thinking component on small screens at the end */}
                        <div className="lg:hidden">
                            <InlineThinkingComponent />
                        </div>
                    </>
                        ) : (
                            <>
                                <div className="flex justify-center items-center py-8">
                                    <p className="glass-text opacity-70 text-xs sm:text-sm">No messages yet</p>
                                </div>
                            </>
                        )}
                    </>
                ) : (
                    <div className="flex items-center justify-center h-full">
                        <div className="text-center glass p-6">
                            <div className="w-12 h-12 mx-auto mb-3 glass-dark rounded-full flex items-center justify-center">
                                <span className="material-symbols-outlined text-2xl glass-text">
                                    chat
                                </span>
                            </div>
                            <h3 className="text-base font-medium mb-2 glass-text">No conversation loaded</h3>
                            <p className="text-xs sm:text-xs glass-text opacity-70">Start a new conversation or select one from the sidebar</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Message Input Bar - Fixed Footer */}
            {conversationMessages?.conversation_id && (
                <div className="glass-dark px-4 py-3 border-t border-white/10 flex-shrink-0">
                    <div className="flex items-center space-x-4">
                        <div className="flex-1 relative">
                            <textarea
                                ref={textareaRef}
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onInput={(e) => adjustTextareaHeight(e.currentTarget)}
                                onKeyPress={handleKeyPress}
                                placeholder="Type your message here..."
                                className="glass-input w-full px-4 py-3 glass-text placeholder-white/80 text-white resize-none"
                                rows={1}
                                style={{ minHeight: '48px' }}
                                disabled={isThinking}
                            />
                        </div>
                        {isThinking ? (
                            <div className="flex justify-center p-2 items-center glass rounded-lg">
                                <div className="flex space-x-1">
                                    <div className="w-1.5 h-1.5 bg-white/70 rounded-full animate-pulse"></div>
                                    <div className="w-1.5 h-1.5 bg-white/70 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                                    <div className="w-1.5 h-1.5 bg-white/70 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                                </div>
                            </div>
                        ) : (
                            <button
                                onClick={handleSendMessage}
                                disabled={isThinking || !inputMessage.trim()}
                                className="glass-button p-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <span className="material-symbols-outlined glass-text text-lg">
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
