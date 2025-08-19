#!/usr/bin/env python3
"""
User notification service for background job updates
"""

from datetime import datetime, timezone
from typing import List, Dict
from db_service import UserNotification, User_Auth_Table, ChatBots, BatchSummarizationJob

class NotificationService:
    """Service for managing user notifications"""
    
    @staticmethod
    async def create_enhancement_notification(
        user: User_Auth_Table,
        chatbot: ChatBots,
        batch_job: BatchSummarizationJob,
        notification_type: str,
        custom_message: str = None
    ) -> UserNotification:
        """Create a new user notification"""
        
        messages = {
            'enhancement_started': f"Enhancement started for '{chatbot.name}'. We'll notify you when complete!",
            'enhancement_completed': f"🎉 Enhancement complete for '{chatbot.name}'! Your agent now has AI-powered summaries.",
            'enhancement_failed': f"Enhancement failed for '{chatbot.name}'. Please try again or contact support."
        }
        
        notification = UserNotification(
            user=user,
            chatbot=chatbot,
            batch_job=batch_job,
            notification_type=notification_type,
            title=f"Agent Enhancement Update",
            message=custom_message or messages.get(notification_type, "Enhancement update available"),
            created_at=datetime.now(timezone.utc)
        )
        notification.save()
        return notification
    
    @staticmethod
    def get_user_notifications(user: User_Auth_Table, unread_only: bool = False) -> List[UserNotification]:
        """Get notifications for a user"""
        query = UserNotification.objects(user=user)
        if unread_only:
            query = query.filter(is_read=False)
        return query.order_by('-created_at')