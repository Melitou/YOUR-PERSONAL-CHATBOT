import { useEffect, useState, useRef } from "react";
import ViewStore, { type ThinkingStep } from "../stores/ViewStore";

// Typewriter animation for smooth text reveal
const TypewriterText: React.FC<{ text: string; speed?: number; onComplete?: () => void }> = ({
    text,
    speed = 30,
    onComplete
}) => {
    const [displayedText, setDisplayedText] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        setDisplayedText('');
        setCurrentIndex(0);
    }, [text]);

    useEffect(() => {
        if (currentIndex < text.length) {
            const timer = setTimeout(() => {
                setDisplayedText(text.slice(0, currentIndex + 1));
                setCurrentIndex(currentIndex + 1);
            }, speed);
            return () => clearTimeout(timer);
        } else if (onComplete && currentIndex === text.length && text.length > 0) {
            onComplete();
        }
    }, [currentIndex, text, speed, onComplete]);

    return <span>{displayedText}</span>;
};

// Animated thinking dots
const ThinkingDots: React.FC = () => {
    return (
        <div className="flex space-x-1">
            {[0, 1, 2].map((index) => (
                <div
                    key={index}
                    className="w-2 h-2 bg-white bg-opacity-60 rounded-full animate-pulse"
                    style={{
                        animationDelay: `${index * 0.2}s`,
                        animationDuration: '1s'
                    }}
                />
            ))}
        </div>
    );
};

// Individual step component with animation
const ThinkingStepComponent: React.FC<{
    step: ThinkingStep;
    index: number;
    isVisible: boolean;
}> = ({ step, index, isVisible }) => {
    const [isAnimated, setIsAnimated] = useState(false);

    useEffect(() => {
        if (isVisible) {
            const timer = setTimeout(() => setIsAnimated(true), index * 200);
            return () => clearTimeout(timer);
        }
    }, [isVisible, index]);

    return (
        <div
            className={`transform transition-all duration-500 ease-out ${isAnimated
                ? 'translate-x-0 opacity-100'
                : 'translate-x-4 opacity-0'
                }`}
        >
            <div className="flex items-start space-x-3 mb-4">
                <div className="flex-shrink-0 w-6 h-6 bg-white bg-opacity-80 text-black rounded-full flex items-center justify-center text-xs font-bold">
                    {index + 1}
                </div>
                <div className="flex-1">
                    <div className="font-semibold glass-text text-sm mb-1">
                        {step.step}
                    </div>
                    <div className="glass-text text-sm opacity-80">
                        <TypewriterText text={step.message} speed={20} />
                    </div>
                </div>
            </div>
        </div>
    );
};

const ThoughtVisualizerComponent: React.FC = () => {
    const thoughtVisualizerData = ViewStore((state) => state.thoughtVisualizerData);

    const [visibleSteps, setVisibleSteps] = useState(0);
    const scrollContainerRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (thoughtVisualizerData.steps.length > visibleSteps) {
            const timer = setTimeout(() => {
                setVisibleSteps(thoughtVisualizerData.steps.length);
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [thoughtVisualizerData.steps.length, visibleSteps]);

    const scrollToBottom = () => {
        if (scrollContainerRef.current) {
            requestAnimationFrame(() => {
                scrollContainerRef.current?.scrollTo({
                    top: scrollContainerRef.current.scrollHeight,
                    behavior: 'smooth'
                });
            });
        }
    };

    useEffect(() => {
        // Auto-scroll to bottom ONLY when actively thinking and new content is added
        if (thoughtVisualizerData.isActive) {
            scrollToBottom();
        }
    }, [thoughtVisualizerData.steps, thoughtVisualizerData.currentMessage, thoughtVisualizerData.isActive]);

    return (
        <div className="h-full w-full glass-card flex flex-col">
            {/* Header */}
            <div className="glass border-b border-white border-opacity-20 p-4 flex-shrink-0 rounded-t-3xl">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div>
                            <h2 className="text-lg font-bold glass-text">AI Thought Process</h2>
                            <p className="glass-text text-sm opacity-75">
                                {thoughtVisualizerData.isActive ? 'Thinking in progress...' : 'Thought process complete'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content - Scrollable */}
            <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Start Message */}
                {thoughtVisualizerData.startMessage && (
                    <div className="p-4 glass-light rounded-2xl">
                        <div className="flex items-center space-x-2 mb-2">
                            <div className="w-3 h-3 bg-white bg-opacity-80 rounded-full"></div>
                            <span className="font-semibold glass-text text-sm">Starting Analysis</span>
                        </div>
                        <div className="glass-text text-sm opacity-90">
                            <TypewriterText text={thoughtVisualizerData.startMessage} speed={25} />
                        </div>
                    </div>
                )}

                {/* Thinking Steps */}
                {thoughtVisualizerData.steps.length > 0 && (
                    <div>
                        <div className="flex items-center space-x-2 mb-4">
                            <h3 className="text-lg font-semibold glass-text">Processing Steps</h3>
                            {thoughtVisualizerData.isActive && (
                                <ThinkingDots />
                            )}
                        </div>
                        <div className="space-y-2">
                            {thoughtVisualizerData.steps.map((step: ThinkingStep, index: number) => (
                                <ThinkingStepComponent
                                    key={step.id}
                                    step={step}
                                    index={index}
                                    isVisible={index < visibleSteps}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {/* Current Message (if actively thinking) */}
                {thoughtVisualizerData.isActive && thoughtVisualizerData.currentMessage && (
                    <div className="p-4 glass rounded-2xl border border-white border-opacity-30">
                        <div className="flex items-center space-x-2 mb-2">
                            <ThinkingDots />
                            <span className="font-semibold glass-text text-sm">Current Focus</span>
                        </div>
                        <div className="glass-text text-sm opacity-90">
                            <TypewriterText text={thoughtVisualizerData.currentMessage} speed={25} />
                        </div>
                    </div>
                )}

                {/* Completion Message */}
                {thoughtVisualizerData.completeMessage && !thoughtVisualizerData.isActive && (
                    <div className="p-4 glass-light rounded-2xl border border-white border-opacity-40">
                        <div className="flex items-center space-x-2 mb-2">
                            <div className="w-3 h-3 bg-white bg-opacity-90 rounded-full"></div>
                            <span className="font-semibold glass-text text-sm">Analysis Complete</span>
                        </div>
                        <div className="glass-text text-sm opacity-90">
                            <TypewriterText text={thoughtVisualizerData.completeMessage} speed={25} />
                        </div>
                    </div>
                )}

                {/* Empty state */}
                {!thoughtVisualizerData.startMessage &&
                    thoughtVisualizerData.steps.length === 0 &&
                    !thoughtVisualizerData.completeMessage && (
                        <div className="text-center py-8">
                            <div className="w-16 h-16 glass rounded-full flex items-center justify-center mx-auto mb-4">
                                <ThinkingDots />
                            </div>
                            <p className="glass-text opacity-75">Waiting for thought process to begin...</p>
                        </div>
                    )}
            </div>

            {/* Footer */}
            <div className="glass border-t border-white border-opacity-20 px-4 py-3 text-sm flex-shrink-0 rounded-b-3xl">
                <div className="flex justify-between items-center">
                    <span className="glass-text opacity-75">
                        {thoughtVisualizerData.steps.length} step{thoughtVisualizerData.steps.length !== 1 ? 's' : ''} completed
                    </span>
                    {thoughtVisualizerData.startTime && (
                        <span className="glass-text opacity-75">
                            Started {new Date(thoughtVisualizerData.startTime).toLocaleTimeString()}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
};

// Inline thinking component for mobile displays
export const InlineThinkingComponent: React.FC = () => {
    const thoughtVisualizerData = ViewStore((state) => state.thoughtVisualizerData);

    // Get the current step to display (latest one)
    const getCurrentDisplayText = () => {
        if (thoughtVisualizerData.completeMessage && !thoughtVisualizerData.isActive) {
            return {
                text: thoughtVisualizerData.completeMessage,
                isComplete: true
            };
        }

        if (thoughtVisualizerData.isActive && thoughtVisualizerData.currentMessage) {
            return {
                text: thoughtVisualizerData.currentMessage,
                isComplete: false
            };
        }

        if (thoughtVisualizerData.steps.length > 0) {
            const latestStep = thoughtVisualizerData.steps[thoughtVisualizerData.steps.length - 1];
            return {
                text: latestStep.message,
                isComplete: false
            };
        }

        if (thoughtVisualizerData.startMessage) {
            return {
                text: thoughtVisualizerData.startMessage,
                isComplete: false
            };
        }

        return null;
    };

    const currentDisplay = getCurrentDisplayText();

    // Don't render if no thinking data
    if (!currentDisplay) {
        return null;
    }

    return (
        <div className="w-full mb-3">
            <div className="chat-message-container bot-message-container">
                <div className="chat-message-bubble glass bot-message-bubble px-4 py-2 border border-white border-opacity-20">
                    <div className="flex items-center space-x-2">
                        {currentDisplay.isComplete ? (
                            <div className="w-2 h-2 bg-white bg-opacity-60 rounded-full"></div>
                        ) : (
                            <ThinkingDots />
                        )}
                        <div className="glass-text text-xs opacity-60 font-light italic">
                            <TypewriterText
                                text={currentDisplay.text}
                                speed={15}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ThoughtVisualizerComponent;