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
import os
from openai import OpenAI
from batch_enhancement_service import BatchEnhancementService

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Handle OpenAI webhook events"""
    
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
        self.batch_service = BatchEnhancementService()
    
    # def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
    #     """Verify OpenAI webhook signature"""
    #     expected_signature = hmac.new(
    #         self.webhook_secret.encode(),
    #         body,
    #         hashlib.sha256
    #     ).hexdigest()
    #     return hmac.compare_digest(f"sha256={expected_signature}", signature)

    def verify_webhook_signature(self, body: bytes, signature: str) -> tuple[bool, dict]:
        """Verify OpenAI webhook signature and return parsed event data"""
        try:
            client = OpenAI()
            # Use the webhook_secret from constructor instead of fetching again
            event = client.webhooks.unwrap(body, signature, secret=self.webhook_secret)
            return True, event
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False, {}
    
    async def handle_batch_event(self, event) -> Dict:
        """Handle batch-related webhook events"""
        # Access event properties using dot notation since it's a structured object
        logger.info(f"Processing webhook event: {type(event).__name__}")
        event_type = event.type
        batch_data = event.data
        
        logger.info(f"Event type: {event_type}, Batch ID: {getattr(batch_data, 'id', 'unknown')}")
        
        if event_type == "batch.completed":
            return await self.batch_service.process_batch_completion(batch_data.id)
        elif event_type == "batch.failed":
            return await self.handle_batch_failure(batch_data)
        elif event_type == "batch.expired":
            return await self.handle_batch_expiry(batch_data)
        
        return {"status": "ignored", "event_type": event_type}

    async def handle_batch_failure(self, batch_data) -> Dict:
        """Handle failed batch event: persist status and notify user via service"""
        batch_id = batch_data.id if hasattr(batch_data, 'id') else None
        if not batch_id:
            logger.warning("batch.failed webhook missing batch id")
            return {"status": "error", "message": "missing_batch_id"}

        # Convert batch_data object to dict for the service
        batch_dict = {
            "id": batch_data.id,
            "status": getattr(batch_data, 'status', None),
            "errors": getattr(batch_data, 'errors', None),
        }

        await self.batch_service.handle_batch_webhook({
            "type": "batch.failed",
            "data": batch_dict,
        })

        return {"status": "handled", "event_type": "batch.failed", "batch_id": batch_id}

    async def handle_batch_expiry(self, batch_data) -> Dict:
        """Handle expired batch event: persist status and notify user via service"""
        batch_id = batch_data.id if hasattr(batch_data, 'id') else None
        if not batch_id:
            logger.warning("batch.expired webhook missing batch id")
            return {"status": "error", "message": "missing_batch_id"}

        # Convert batch_data object to dict for the service
        batch_dict = {
            "id": batch_data.id,
            "status": getattr(batch_data, 'status', None),
            "errors": getattr(batch_data, 'errors', None),
        }

        await self.batch_service.handle_batch_webhook({
            "type": "batch.expired",
            "data": batch_dict,
        })

        return {"status": "handled", "event_type": "batch.expired", "batch_id": batch_id}