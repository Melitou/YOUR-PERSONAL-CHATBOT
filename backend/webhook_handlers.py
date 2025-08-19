#!/usr/bin/env python3
"""
Webhook handlers for OpenAI Batch API events
"""

import hmac
import hashlib
import json
import logging
from typing import Dict
from fastapi import HTTPException, Request
from batch_enhancement_service import BatchEnhancementService

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Handle OpenAI webhook events"""
    
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
        self.batch_service = BatchEnhancementService()
    
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify OpenAI webhook signature"""
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    async def handle_batch_event(self, event_data: Dict) -> Dict:
        """Handle batch-related webhook events"""
        event_type = event_data.get("type")
        batch_data = event_data.get("data", {})
        
        if event_type == "batch.completed":
            return await self.batch_service.process_batch_completion(batch_data.get("id"))
        elif event_type == "batch.failed":
            return await self.handle_batch_failure(batch_data)
        elif event_type == "batch.expired":
            return await self.handle_batch_expiry(batch_data)
        
        return {"status": "ignored", "event_type": event_type}

    async def handle_batch_failure(self, batch_data: Dict) -> Dict:
        """Handle failed batch event: persist status and notify user via service"""
        batch_id = batch_data.get("id")
        if not batch_id:
            logger.warning("batch.failed webhook missing batch id")
            return {"status": "error", "message": "missing_batch_id"}

        await self.batch_service.handle_batch_webhook({
            "type": "batch.failed",
            "data": batch_data,
        })

        return {"status": "handled", "event_type": "batch.failed", "batch_id": batch_id}

    async def handle_batch_expiry(self, batch_data: Dict) -> Dict:
        """Handle expired batch event: persist status and notify user via service"""
        batch_id = batch_data.get("id")
        if not batch_id:
            logger.warning("batch.expired webhook missing batch id")
            return {"status": "error", "message": "missing_batch_id"}

        await self.batch_service.handle_batch_webhook({
            "type": "batch.expired",
            "data": batch_data,
        })

        return {"status": "handled", "event_type": "batch.expired", "batch_id": batch_id}