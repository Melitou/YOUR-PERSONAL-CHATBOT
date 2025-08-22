import { useState, useEffect, useRef } from 'react';
import MarkdownRenderer from './MarkdownRenderer';

interface TypewriterMarkdownProps {
    text: string;
    isStreaming: boolean;
    speed?: number;
    onComplete?: () => void;
}

const TypewriterMarkdown = ({ text, isStreaming, speed = 25, onComplete }: TypewriterMarkdownProps) => {
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
        return <MarkdownRenderer content={text} />;
    }

    return (
        <div className="relative">
            <MarkdownRenderer content={displayedText} />
            {isStreaming && currentIndex < text.length && (
                <span className="animate-pulse text-gray-400 ml-1 absolute">|</span>
            )}
        </div>
    );
};

export default TypewriterMarkdown;
