import { useEffect, useState } from "react";
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
                    className="w-2 h-2 bg-gray-600 rounded-full animate-pulse"
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
            className={`transform transition-all duration-500 ease-out ${
                isAnimated 
                    ? 'translate-x-0 opacity-100' 
                    : 'translate-x-4 opacity-0'
            }`}
        >
            <div className="flex items-start space-x-3 mb-4">
                <div className="flex-shrink-0 w-6 h-6 bg-gray-800 text-white rounded-full flex items-center justify-center text-xs font-bold">
                    {index + 1}
                </div>
                <div className="flex-1">
                    <div className="font-semibold text-gray-800 text-sm mb-1">
                        {step.step}
                    </div>
                    <div className="text-gray-600 text-sm">
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

    useEffect(() => {
        if (thoughtVisualizerData.steps.length > visibleSteps) {
            const timer = setTimeout(() => {
                setVisibleSteps(thoughtVisualizerData.steps.length);
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [thoughtVisualizerData.steps.length, visibleSteps]);

    return (
        <div className="h-1/2 bg-white text-black flex flex-col rounded-lg border border-gray-200">
            {/* Header */}
            <div className="bg-gray-50 border-b border-gray-200 p-4 flex-shrink-0 rounded-t-lg">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div>
                            <h2 className="text-lg font-bold text-black">AI Thought Process</h2>
                            <p className="text-gray-600 text-sm">
                                {thoughtVisualizerData.isActive ? 'Thinking in progress...' : 'Thought process complete'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content - Scrollable */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Start Message */}
                {thoughtVisualizerData.startMessage && (
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="flex items-center space-x-2 mb-2">
                            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                            <span className="font-semibold text-blue-800 text-sm">Starting Analysis</span>
                        </div>
                        <div className="text-gray-700 text-sm">
                            <TypewriterText text={thoughtVisualizerData.startMessage} speed={25} />
                        </div>
                    </div>
                )}

                {/* Thinking Steps */}
                {thoughtVisualizerData.steps.length > 0 && (
                    <div>
                        <div className="flex items-center space-x-2 mb-4">
                            <h3 className="text-lg font-semibold text-gray-800">Processing Steps</h3>
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
                    <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <div className="flex items-center space-x-2 mb-2">
                            <ThinkingDots />
                            <span className="font-semibold text-yellow-800 text-sm">Current Focus</span>
                        </div>
                        <div className="text-gray-700 text-sm">
                            <TypewriterText text={thoughtVisualizerData.currentMessage} speed={25} />
                        </div>
                    </div>
                )}

                {/* Completion Message */}
                {thoughtVisualizerData.completeMessage && !thoughtVisualizerData.isActive && (
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center space-x-2 mb-2">
                            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                            <span className="font-semibold text-green-800 text-sm">Analysis Complete</span>
                        </div>
                        <div className="text-gray-700 text-sm">
                            <TypewriterText text={thoughtVisualizerData.completeMessage} speed={25} />
                        </div>
                    </div>
                )}

                {/* Empty state */}
                {!thoughtVisualizerData.startMessage && 
                 thoughtVisualizerData.steps.length === 0 && 
                 !thoughtVisualizerData.completeMessage && (
                    <div className="text-center py-8">
                        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <ThinkingDots />
                        </div>
                        <p className="text-gray-600">Waiting for thought process to begin...</p>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="bg-gray-50 border-t border-gray-200 px-4 py-3 text-sm text-gray-600 flex-shrink-0 rounded-b-lg">
                <div className="flex justify-between items-center">
                    <span>
                        {thoughtVisualizerData.steps.length} step{thoughtVisualizerData.steps.length !== 1 ? 's' : ''} completed
                    </span>
                    {thoughtVisualizerData.startTime && (
                        <span>
                            Started {new Date(thoughtVisualizerData.startTime).toLocaleTimeString()}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ThoughtVisualizerComponent;