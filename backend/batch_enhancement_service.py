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
	User_Auth_Table, ChatbotClientMapper, ChunkVectorMappings
)
from embeddings import EmbeddingService
from notification_service import NotificationService
import time

logger = logging.getLogger(__name__)

class BatchEnhancementService:
	"""Service for managing OpenAI Batch API enhancement jobs"""
	
	def __init__(self):
		self.openai_client = AsyncOpenAI()
		self.summary_model = "gpt-4.1-mini"
		self.max_tokens = 150
		self.temperature = 0.2
	
	async def start_enhancement_job(self, chatbot: ChatBots, user: User_Auth_Table, namespaces: List[str]) -> List[str]:
		"""Start a batch enhancement job for a chatbot's chunks"""
		logger.info(f"Starting enhancement job for chatbot {chatbot.name} with {len(namespaces)} namespaces.")

		try:
			if not chatbot or not user:
				raise ValueError("Invalid chatbot or user")

			chatbot_id = str(chatbot.id)
			user_id = str(user.id)

			if len(namespaces) == 0:
				logger.info(f"No namespaces found for chatbot {chatbot_id}, job not started.")
				return []
			
			# Check if the chatbot has a batch job already running
			batch_job = BatchSummarizationJob.objects(chatbot=chatbot, status="submitted").first()
			if batch_job:
				logger.info(f"Chatbot {chatbot_id} already has a batch job running, job not started.")
				return []

			logger.info(f"Starting enhancement job for chatbot {chatbot_id} with {len(namespaces)} namespaces.")

			batch_ids = []
			for namespace in namespaces:
				try:
					# We need to take the chunks ids that have as namespace the namespace of the initial chatbot
					# but also are only included in the chatbot that reuse them (if it does)
					chunks_ids = []
					chunk_vector_mappings = ChunkVectorMappings.objects(
						user=user,
						chatbot=chatbot # original
					)

					# Get the chunks from the chunk_vector_mappings
					chunks = []
					for mapping in chunk_vector_mappings:
						chunks.append(mapping.chunk)

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
					
					# Extract chunk IDs for metadata
					chunk_ids = "_".join([str(chunk.id) for chunk in chunks])
					
					# Create Batch job (24h window)
					batch = await self.openai_client.batches.create(
						input_file_id=input_file.id,
						endpoint="/v1/chat/completions",
						completion_window="24h",
						metadata={
							"chatbot_id": chatbot_id, 
							"user_id": user_id,
							"namespace": namespace,
							# "chunk_ids": chunk_ids
						}
					)
					
					batch_ids.append(batch.id)
					
					# Track job in DB
					job = BatchSummarizationJob(
						chatbot=chatbot,
						user=user,
						batch_id=batch.id,
						status="submitted",
						total_requests=len(chunks),
						request_counts_by_status={},
						created_at=datetime.utcnow(),
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
						namespace=namespace,
						chatbot=chatbot,
						batch_job=job,
						notification_type="enhancement_started"
					)
					
					logger.info(f"Started enhancement batch {batch.id} for chatbot {chatbot_id} with {len(chunks)} requests for namespace {namespace}.")
					# Wait a bit of time before returning the batch id
					time.sleep(5)
				except Exception as e:
					logger.error(f"Error starting enhancement job: {e}")
					continue # Continue with the next namespace

			logger.info(f"Started {len(batch_ids)} enhancement jobs for chatbot {chatbot_id} with {len(namespaces)} namespaces.")
			return batch_ids
		except Exception as e:
			logger.error(f"Error starting enhancement job: {e}")
			return []
	
	async def create_batch_jsonl(self, chunks: List[Chunks]) -> str:
		"""Create JSONL content for batch API"""
		lines: List[str] = []

		full_content = self._construct_full_content(chunks)
		
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
						"content": f"Summarize the following text chunk, focusing on the key facts and entities.\n\nChunk:\n{ch.content}\n\nFull content of the document:\n{full_content}"
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
	
	def _construct_full_content(self, chunks: List[Chunks]) -> str:
		"""Construct the full content of the document from the chunks"""
		full_content = ""
		for ch in chunks:
			full_content += ch.content
		return full_content
	
	async def process_batch_completion(self, batch_id: str) -> Dict:
		"""Process completed batch and update chunks"""
		logger.info(f"Processing batch completion for batch id={batch_id}")

		job: Optional[BatchSummarizationJob] = BatchSummarizationJob.objects(batch_id=batch_id).first()
		if not job:
			logger.warning(f"Batch job not found for id={batch_id}")
			return {"status": "error", "message": "job_not_found"}
		
		# if job is completed, return
		if job.status == "completed":
			logger.info(f"Batch job {batch_id} is already completed, returning")
			return {"status": "processed", "updated_chunks": 0, "errors": 0, "batch_status": job.status}
		
		# Retrieve batch status and output file references
		batch = await self.openai_client.batches.retrieve(batch_id) # GET https://api.openai.com/v1/batches
		status = getattr(batch, "status", None) or getattr(batch, "state", None)
		request_counts = getattr(batch, "request_counts", None) or getattr(batch, "request_counts_by_status", None) or {}
		output_file_id = getattr(batch, "output_file_id", None)
		error_file_id = getattr(batch, "error_file_id", None)
		metadata = getattr(batch, "metadata", {})
		namespace = metadata.get("namespace", "unknown")
		
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

								logger.info(f"Updated chunk {chunk.id} with AI-enhanced summary with chunk summary length {len(chunk.summary)}")

								# Now, update redo the embedding of the chunks, also update the embeddings in Pinecone
								# Start with deleting the vector from Pinecone for this specific chatbot
								embedding_service = EmbeddingService()
								
								# Get the vector ID for this chunk in this chatbot's namespace
								vector_id = embedding_service.get_vector_id_for_chunk(
									chunk_id=str(chunk.id),
									chatbot=chatbot
								)
								
								if vector_id:
									embedding_service.delete_vector_from_pinecone(vector_id)
									logger.info(f"Deleted old vector {vector_id} for chunk {chunk.id}")
								else:
									logger.warning(f"No vector mapping found for chunk {chunk.id} in chatbot {chatbot.name}")

								# Now, redo the embedding
								# Get the chatbot and document info for re-embedding
								chatbot = job.chatbot  # The chatbot from the batch job
								document_id = str(chunk.document.id)  # The document ID from the chunk
								embedding_model = chatbot.embedding_model  # The embedding model used by this chatbot

								# Re-embed the document for this specific chatbot
								re_embed_result = embedding_service.embed_document_for_chatbot(
									document_id=document_id,
									chatbot=chatbot,
									embedding_model=embedding_model,
									batch_size=50
								)

								if re_embed_result["success"]:
									logger.info(f"Successfully re-embedded chunk {chunk.id} for chatbot {chatbot.name}\n")
									# The chunk's vector_id will be updated by the embed_document_for_chatbot function
								else:
									logger.error(f"Failed to re-embed chunk {chunk.id}: {re_embed_result['errors']}\n")

					except Exception as e:
						errors += 1
						logger.exception(f"Error processing batch output line: {e}")
				
				job.status = "completed"
				job.completed_at = datetime.utcnow()
				
				# Notify user on completion
				await NotificationService.create_enhancement_notification(
					user=job.user,
					namespace=namespace,
					chatbot=job.chatbot,
					batch_job=job,
					notification_type="enhancement_completed"
				)
			
			elif status in {"failed", "expired", "cancelled"}:
				job.failed_at = datetime.utcnow()
				# If there is an error file
				await NotificationService.create_enhancement_notification(
					user=job.user,
					namespace=namespace,
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
			
			# Get namespace from batch metadata for notification
			try:
				batch = await self.openai_client.batches.retrieve(batch_id)
				metadata = getattr(batch, "metadata", {})
				notification_namespace = metadata.get("namespace", "unknown")
			except Exception:
				notification_namespace = "unknown"
			
			await NotificationService.create_enhancement_notification(
				user=job.user,
				namespace=notification_namespace,
				chatbot=job.chatbot,
				batch_job=job,
				notification_type="enhancement_failed",
			)
			return {"status": "error", "message": "processing_failed"}
		
		job.save()
		return {"status": "processed", "updated_chunks": updated, "errors": errors, "batch_status": job.status}
	
	async def handle_batch_webhook(self, webhook_data: Dict) -> None:
		"""Handle incoming webhook from OpenAI"""
		logger.info(f"Handling batch webhook for batch id={webhook_data.get('id')}")
		
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

			# if job is already completed, return
			if job.status == "completed":
				logger.info(f"Batch job {batch_id} is already completed, returning")
				return {"status": "processed", "updated_chunks": 0, "errors": 0, "batch_status": job.status}

			if job:
				# Get namespace from batch metadata
				try:
					batch = await self.openai_client.batches.retrieve(batch_id)
					metadata = getattr(batch, "metadata", {})
					namespace = metadata.get("namespace", "unknown")
				except Exception as e:
					logger.warning(f"Could not retrieve batch metadata for namespace: {e}")
					namespace = "unknown"
				
				job.status = event_type.split(".")[1]  # failed/expired/cancelled
				job.failed_at = datetime.utcnow()
				job.save()
				await NotificationService.create_enhancement_notification(
					user=job.user,
					namespace=namespace,
					chatbot=job.chatbot,
					batch_job=job,
					notification_type="enhancement_failed"
				)