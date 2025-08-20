#!/usr/bin/env python3
"""
OpenAI Batch API Service for Background Summarization Enhancement
"""

import io
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from db_service import (
	Chunks, ChatBots, BatchSummarizationJob, UserNotification,
	User_Auth_Table
)
from notification_service import NotificationService

logger = logging.getLogger(__name__)

class BatchEnhancementService:
	"""Service for managing OpenAI Batch API enhancement jobs"""
	
	def __init__(self):
		self.openai_client = AsyncOpenAI()
		self.summary_model = "gpt-4.1-mini"
		self.max_tokens = 150
		self.temperature = 0.2
	
	async def start_enhancement_job(self, chatbot_id: str, user_id: str) -> str:
		"""Start a batch enhancement job for a chatbot's chunks"""

		# TODO: WRONG: We need to check in the Mapper
		# Based on the chatbot in the param, take the namespace of the "father" chatbot

		chatbot = ChatBots.objects(id=chatbot_id).first()
		user = User_Auth_Table.objects(id=user_id).first()
		if not chatbot or not user:
			raise ValueError("Invalid chatbot_id or user_id")
		
		# Target only basic summaries for enhancement
		chunks: List[Chunks] = list(Chunks.objects(
			namespace=chatbot.namespace,
            user=user_id,
			summary_type="basic"
		).order_by("chunk_index"))
		
		if not chunks:
			logger.info(f"No basic summaries found for chatbot {chatbot_id}")
			raise ValueError(f"No basic summaries available to enhance for the chatbot {chatbot_id} for the user {user_id} with namespace {chatbot.namespace}")
		
		# Build JSONL payload for OpenAI Batch
		jsonl_content: str = await self.create_batch_jsonl(chunks)
		jsonl_bytes = jsonl_content.encode("utf-8")
		
		# Create OpenAI File from in-memory bytes
		jsonl_buf = io.BytesIO(jsonl_bytes)
		jsonl_buf.name = "enhancement_requests.jsonl"  # OpenAI requires a name attr
		
		input_file = await self.openai_client.files.create(
			file=jsonl_buf,
			purpose="batch"
		)
		
		# Create Batch job (24h window)
		batch = await self.openai_client.batches.create(
			input_file_id=input_file.id,
			endpoint="/v1/chat/completions",
			completion_window="24h"
		)
		
		# Track job in DB
		job = BatchSummarizationJob(
			chatbot=chatbot,
			user=user,
			batch_id=batch.id,
			status="submitted",
			total_requests=len(chunks),
			request_counts_by_status={},
			created_at=datetime.now(timezone.utc),
			input_file_id=input_file.id
		)
		job.save()
		
		# Link chunks to job (so we can find them later if needed)
		for ch in chunks:
			ch.batch_job = job
			ch.save()
		
		# Notify user
		await NotificationService.create_enhancement_notification(
			user=user,
			chatbot=chatbot,
			batch_job=job,
			notification_type="enhancement_started"
		)
		
		logger.info(f"Started enhancement batch {batch.id} for chatbot {chatbot_id} with {len(chunks)} requests")
		return batch.id
	
	async def create_batch_jsonl(self, chunks: List[Chunks]) -> str:
		"""Create JSONL content for batch API"""
		lines: List[str] = []
		
		# Use a concise, standalone-summary prompt per chunk
		for ch in chunks:
			body = {
				"model": self.summary_model,
				"messages": [
					{
						"role": "system",
						"content": "You are an expert at summarizing text chunks for retrieval. Produce a concise, accurate, standalone summary."
					},
					{
						"role": "user",
						"content": f"Summarize the following text chunk, focusing on the key facts and entities.\n\nChunk:\n{ch.content}"
						# TODO: Add the full contents of the document
					}
				],
				"max_tokens": self.max_tokens,
				"temperature": self.temperature
			}
			line = {
				"custom_id": str(ch.id),
				"method": "POST",
				"url": "/v1/chat/completions",
				"body": body
			}
			lines.append(json.dumps(line, ensure_ascii=False))
		
		return "\n".join(lines)
	
	async def process_batch_completion(self, batch_id: str) -> Dict:
		"""Process completed batch and update chunks"""
		job: Optional[BatchSummarizationJob] = BatchSummarizationJob.objects(batch_id=batch_id).first()
		if not job:
			logger.warning(f"Batch job not found for id={batch_id}")
			return {"status": "error", "message": "job_not_found"}
		
		# Retrieve batch status and output file references
		batch = await self.openai_client.batches.retrieve(batch_id)
		status = getattr(batch, "status", None) or getattr(batch, "state", None)
		request_counts = getattr(batch, "request_counts", None) or getattr(batch, "request_counts_by_status", None) or {}
		output_file_id = getattr(batch, "output_file_id", None)
		error_file_id = getattr(batch, "error_file_id", None)
		
		# Update job fields from latest batch info
		job.status = status or job.status
		job.request_counts_by_status = dict(request_counts) if request_counts else job.request_counts_by_status
		if output_file_id:
			job.output_file_id = output_file_id
		if error_file_id:
			job.error_file_id = error_file_id
		
		updated = 0
		errors = 0
		
		try:
			if status == "completed" and output_file_id:
				# Download batch output JSONL
				file_resp = await self.openai_client.files.content(output_file_id)
				
				text_data: Optional[str] = None
				try:
					# Some SDK versions expose .text
					text_data = getattr(file_resp, "text", None)
				except Exception:
					text_data = None
				if not text_data:
					# Try reading bytes
					try:
						if hasattr(file_resp, "aread"):
							raw = await file_resp.aread()
							text_data = raw.decode("utf-8")
						elif hasattr(file_resp, "read"):
							raw = await file_resp.read()
							text_data = raw.decode("utf-8")
						else:
							if isinstance(file_resp, (bytes, bytearray)):
								text_data = file_resp.decode("utf-8")
							elif isinstance(file_resp, str):
								text_data = file_resp
					except Exception as e:
						logger.error(f"Failed to read batch output file {output_file_id}: {e}")
						raise
				
				if not text_data:
					raise RuntimeError("Empty batch output content")
				
				# Parse JSONL and update chunks
				for line in text_data.splitlines():
					if not line.strip():
						continue
					try:
						obj = json.loads(line)
						custom_id = obj.get("custom_id")
						response = obj.get("response", {})
						body = response.get("body", {})
						choices = body.get("choices", [])
						content = None
						if choices and "message" in choices[0]:
							content = choices[0]["message"].get("content")
						
						if custom_id and content:
							chunk = Chunks.objects(id=custom_id).first()
							if chunk:
								chunk.summary = content.strip() 
								chunk.summary_type = "ai_enhanced"
								chunk.enhanced_at = datetime.utcnow()
								chunk.batch_job = job
								chunk.save()
								updated += 1
					except Exception as e:
						errors += 1
						logger.exception(f"Error processing batch output line: {e}")
				
				job.status = "completed"
				job.completed_at = datetime.utcnow()
				
				# Notify user on completion
				await NotificationService.create_enhancement_notification(
					user=job.user,
					chatbot=job.chatbot,
					batch_job=job,
					notification_type="enhancement_completed"
				)
			
			elif status in {"failed", "expired", "cancelled"}:
				job.failed_at = datetime.utcnow()
				# If there is an error file
				await NotificationService.create_enhancement_notification(
					user=job.user,
					chatbot=job.chatbot,
					batch_job=job,
					notification_type="enhancement_failed"
				)
			else:
				# Not final yet
				job.save()
				return {"status": "pending", "batch_status": status}
		
		except Exception as e:
			job.status = "failed"
			job.failed_at = datetime.utcnow()
			job.error_message = str(e)[:1000]
			job.save()
			await NotificationService.create_enhancement_notification(
				user=job.user,
				chatbot=job.chatbot,
				batch_job=job,
				notification_type="enhancement_failed",
			)
			return {"status": "error", "message": "processing_failed"}
		
		job.save()
		return {"status": "processed", "updated_chunks": updated, "errors": errors, "batch_status": job.status}
	
	async def handle_batch_webhook(self, webhook_data: Dict) -> None:
		"""Handle incoming webhook from OpenAI"""
		event_type = webhook_data.get("type")
		data = webhook_data.get("data", {}) or {}
		
		if event_type == "batch.completed":
			batch_id = data.get("id")
			if batch_id:
				await self.process_batch_completion(batch_id)
			return
		
		# Update job status for other terminal events
		if event_type in {"batch.failed", "batch.expired", "batch.cancelled"}:
			batch_id = data.get("id")
			job = BatchSummarizationJob.objects(batch_id=batch_id).first()
			if job:
				job.status = event_type.split(".")[1]  # failed/expired/cancelled
				job.failed_at = datetime.utcnow()
				job.save()
				await NotificationService.create_enhancement_notification(
					user=job.user,
					chatbot=job.chatbot,
					batch_job=job,
					notification_type="enhancement_failed"
				)