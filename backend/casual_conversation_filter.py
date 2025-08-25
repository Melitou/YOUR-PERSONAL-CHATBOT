"""
Casual Conversation Filter for Fast Response Pre-filtering
Detects simple conversational messages that don't require document search
"""
import re
import logging
import random
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CasualConversationFilter:
    """Handles detection and response for casual conversations"""

    # Regex patterns for different types of casual conversations
    CASUAL_PATTERNS = {
        'greetings': [
            r'^(hi|hello|hey|good morning|good afternoon|good evening|greetings?)[\s!.]*$',
            r'^(hi there|hey there)[\s!.]*$',
            r'^(what\'s up|how\'s it going|howdy)[\s!.?]*$'
        ],
        'thanks': [
            r'^(thank you|thanks|thank u|thx|appreciate it|much appreciated)[\s!.]*$',
            r'^(thanks a lot|thank you so much|thanks very much)[\s!.]*$',
            r'^thank you .{0,30} (help|assistance|time)[\s!.]*$'
        ],
        'farewells': [
            r'^(bye|goodbye|farewell|see ya|ttyl|cya)[\s!.]*$',
            r'^(see you|see you later|talk to you later)[\s!.]*$',
            r'^(good night|good day|have a good day|take care)[\s!.]*$'
        ],
        'acknowledgments': [
            r'^(ok|okay|alright|sure|got it|understood|yes|no|yep|nope|yeah|nah)[\s!.]*$',
            r'^(sounds good|sounds great|perfect|awesome|great)[\s!.]*$'
        ],
        'capability_questions': [
            r'^(what can you do|how can you help|what do you do)[\s!.?]*$',
            r'^(what are your capabilities|tell me about yourself|who are you)[\s!.?]*$'
        ],
        'casual_chat': [
            r'^(how are you|how\'re you doing|how have you been)[\s!.?]*$',
            r'^(nice to meet you|pleasure to meet you|good to see you)[\s!.]*$'
        ]
    }

    # Predefined responses for each category
    CASUAL_RESPONSES = {
        'greetings': [
            "Hello! I'm your personal document assistant. How can I help you with your documents today?",
            "Hi there! I'm ready to help you find information in your uploaded documents. What would you like to know?",
            "Good to see you! I can help you search through your documents or answer questions about their content. What can I do for you?"
        ],
        'thanks': [
            "You're very welcome! I'm here whenever you need help with your documents.",
            "My pleasure! Feel free to ask me anything about your uploaded files.",
            "Happy to help! I'm always ready to assist with your document questions."
        ],
        'farewells': [
            "Goodbye! Feel free to return anytime you need help with your documents.",
            "See you later! I'll be here whenever you need document assistance.",
            "Take care! Come back anytime you have questions about your files."
        ],
        'acknowledgments': [
            "Great! Is there anything specific you'd like to know about your documents?",
            "Perfect! How else can I help you with your uploaded files?",
            "Sounds good! What would you like to explore in your documents?"
        ],
        'capability_questions': [
            "I'm your personal document assistant! I can search through your uploaded documents, answer questions about their content, extract specific information, summarize sections, and help you find exactly what you're looking for. What would you like to know about your documents?",
            "I specialize in helping you work with your uploaded documents. I can find specific information, answer questions about the content, provide summaries, and extract data from your files. How can I assist you today?",
            "I'm here to make your documents more accessible! I can search, analyze, and answer questions about any files you've uploaded. Whether you need specific facts, summaries, or detailed analysis - just ask!"
        ],
        'casual_chat': [
            "I'm doing well and ready to help! How can I assist you with your documents today?",
            "Great, thanks for asking! I'm here and ready to help you with any questions about your uploaded documents.",
            "I'm doing wonderfully! Looking forward to helping you find the information you need in your documents."
        ]
    }

    def __init__(self, enable_filtering: bool = True):
        """
        Initialize the casual conversation filter

        Args:
            enable_filtering: Whether to enable casual conversation filtering
        """
        self.enable_filtering = enable_filtering
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for better performance"""
        self.compiled_patterns = {}
        for category, patterns in self.CASUAL_PATTERNS.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def is_casual_conversation(self, message: str) -> Optional[str]:
        """
        Check if a message is a casual conversation

        Args:
            message: User message to analyze

        Returns:
            Category name if casual conversation detected, None otherwise
        """
        if not self.enable_filtering:
            return None

        if not message or not isinstance(message, str):
            return None

        # Clean and normalize the message
        cleaned_message = message.strip()
        if not cleaned_message:
            return None

        # Check against each category
        for category, compiled_patterns in self.compiled_patterns.items():
            for pattern in compiled_patterns:
                if pattern.match(cleaned_message):
                    logger.info(
                        f"Detected casual conversation: '{cleaned_message}' -> category: {category}")
                    return category

        return None

    def get_casual_response(self, category: str, chatbot_description: Optional[str] = None) -> str:
        """
        Get an appropriate response for a casual conversation category

        Args:
            category: The category of casual conversation
            chatbot_description: Optional chatbot description for personalization

        Returns:
            Appropriate response string
        """
        if category not in self.CASUAL_RESPONSES:
            logger.warning(f"Unknown casual conversation category: {category}")
            category = 'greetings'  # Fallback to greetings

        responses = self.CASUAL_RESPONSES[category]
        # Randomly select a response for variety
        base_response = random.choice(responses)

        # Optionally personalize based on chatbot description (only for capability questions)
        if chatbot_description and category == 'capability_questions':
            base_response = f"I'm your specialized assistant for {chatbot_description.lower()}! I can search through your uploaded documents, answer questions about their content, and help you find exactly what you're looking for in this domain. How can I assist you today?"

        return base_response

    def get_filter_stats(self) -> Dict[str, Any]:
        """
        Get statistics about filter usage (for monitoring)

        Returns:
            Dictionary with filter statistics
        """
        return {
            'enabled': self.enable_filtering,
            'categories_count': len(self.CASUAL_PATTERNS),
            'total_patterns': sum(len(patterns) for patterns in self.CASUAL_PATTERNS.values()),
            'last_checked': datetime.now().isoformat()
        }


# Global instance for use throughout the application
casual_filter = CasualConversationFilter(enable_filtering=True)


def is_casual_message(message: str) -> Optional[str]:
    """
    Convenience function to check if a message is casual

    Args:
        message: User message to check

    Returns:
        Category if casual, None otherwise
    """
    return casual_filter.is_casual_conversation(message)


def get_casual_response(category: str, chatbot_description: Optional[str] = None) -> str:
    """
    Convenience function to get casual response

    Args:
        category: Casual conversation category
        chatbot_description: Optional chatbot description

    Returns:
        Appropriate response
    """
    return casual_filter.get_casual_response(category, chatbot_description)
