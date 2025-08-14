# Embedding Pipeline Integration Plan

## Overview
This plan outlines the integration of an embedding pipeline that will process chunks stored in MongoDB, generate embeddings using OpenAI or Gemini models, store them in Pinecone, and update the MongoDB chunks collection with the Pinecone vector IDs.

## Current Architecture Analysis

### Existing Components
1. **Master Pipeline** (`master_pipeline.py`): Orchestrates document upload and processing
2. **Document Processor** (`document_processor.py`): Handles parsing, chunking, and AI summarization  
3. **Embeddings Service** (`embeddings.py`): Contains embedding model initialization and creation logic
4. **Database Service** (`db_service.py`): MongoDB models and operations using MongoEngine
5. **Existing Pinecone Integration**: Found in `split_and_upload_md.py` and `LLM/scaling_up_demo_tool.py`

### Current Data Flow
```
Local Files → GridFS Storage → Document Processing → Chunking → MongoDB Chunks Collection
```

### MongoDB Chunks Schema
```python
class Chunks(Document):
    document = ReferenceField(Documents, required=True)
    user = ReferenceField(User_Auth_Table, required=True) 
    namespace = StringField(required=True)
    file_name = StringField(required=True)  # Denormalized for performance
    chunk_index = IntField(required=True)
    content = StringField(required=True)
    summary = StringField(required=True)
    chunking_method = StringField(choices=['token', 'semantic', 'line', 'recursive'])
    vector_id = StringField(required=False)  # Initially None, populated by embedding pipeline
    created_at = DateTimeField(required=True)
```

## Proposed New Architecture

### Extended Data Flow
```
Local Files → GridFS Storage → Document Processing → Chunking → MongoDB Chunks Collection → **Embedding Pipeline** → Pinecone Vector Store
```

## Implementation Plan

### Phase 1: Enhance Embeddings Service (`embeddings.py`)

#### 1.1 Add Database Query Methods
- **Function**: `get_unembedded_chunks(namespace: Optional[str] = None, limit: Optional[int] = None) -> List[Chunks]`
  - Query chunks where `vector_id` is None or empty
  - Optional filtering by namespace
  - Optional limit for batch processing
  - Use MongoEngine ORM: `Chunks.objects(vector_id__in=[None, ""]).limit(limit)`

- **Function**: `get_chunks_by_namespace(namespace: str) -> List[Chunks]`
  - Retrieve all chunks for a specific namespace
  - For re-embedding or migration scenarios

#### 1.2 Add Pinecone Integration
- **Add Dependencies**: Update `requirements.txt` to include `pinecone-client`
- **Pinecone Configuration**: Environment variables for API key, index name, and settings
- **Initialize Pinecone Client**: Similar pattern to existing OpenAI/Gemini initialization

#### 1.3 Add Vector Operations
- **Function**: `prepare_embedding_text(content: str, summary: str) -> str`
  - Concatenate content and summary in consistent format
  - Format: `"Summary: {summary}\n\nContent: {content}"`

- **Function**: `create_embeddings_for_chunks(chunks: List[Chunks], model_name: str) -> List[Dict]`
  - Batch process chunks for embedding generation
  - Reuse existing `_create_embeddings_batch` method
  - Return list of dicts: `{"chunk_id": str, "embedding": List[float], "text": str}`

- **Function**: `upsert_to_pinecone(embeddings_data: List[Dict], namespace: str, index_name: str) -> List[str]`
  - Upload embeddings to Pinecone with metadata
  - Use chunk MongoDB `_id` as Pinecone vector ID
  - Include metadata: `user_id`, `document_id`, `chunk_index`, `file_name`
  - Return list of successfully uploaded vector IDs

#### 1.4 Add Database Update Methods
- **Function**: `update_chunk_vector_ids(chunk_vector_mappings: List[Dict]) -> int`
  - Update MongoDB chunks with Pinecone vector IDs
  - Input: `[{"chunk_id": ObjectId, "vector_id": str}]`
  - Use bulk update operations for efficiency
  - Return count of successfully updated chunks

### Phase 2: Create Embedding Pipeline Class

#### 2.1 Main Pipeline Class (`EmbeddingPipeline`)
```python
class EmbeddingPipeline:
    def __init__(self, 
                 embedding_model: str = "text-embedding-3-large",
                 pinecone_index: str = "chatbot-vectors", 
                 batch_size: int = 100,
                 max_workers: int = 4):
```

#### 2.2 Core Methods
- **`process_namespace_embeddings(namespace: str, use_parallel: bool = True) -> Dict`**
  - Main workflow method for processing a complete namespace
  - Get unembedded chunks → Create embeddings → Upload to Pinecone → Update MongoDB
  - Return comprehensive statistics

- **`process_chunks_batch(chunks: List[Chunks], namespace: str) -> Dict`**
  - Process a specific batch of chunks
  - Handle rate limiting and error recovery
  - Return batch processing results

- **`reprocess_namespace(namespace: str, force_update: bool = False) -> Dict`**
  - Re-embed all chunks in a namespace (for model updates)
  - Option to force update existing embeddings

### Phase 3: Integration with Master Pipeline

#### 3.1 Add Embedding Phase to Master Pipeline
- **New Method**: `process_directory_with_embeddings()`
  - Extend existing workflow: Upload → Process → Chunk → **Embed** → Complete
  - Optional embedding step controlled by user parameter

#### 3.2 CLI Interface Updates
- **New Options**:
  - Embedding model selection (OpenAI vs Gemini)
  - Pinecone index name configuration
  - Option to run embedding immediately or separately
  - Batch size for embedding processing

### Phase 4: Standalone Embedding CLI

#### 4.1 New CLI Script (`embedding_pipeline.py`)
```python
def main():
    # CLI for standalone embedding processing
    # Options: namespace, embedding model, batch size, parallel processing
    # Support for processing existing chunks without re-upload
```

#### 4.2 CLI Features
- **Process by Namespace**: Embed all unembedded chunks in a namespace
- **Model Selection**: Choose between available embedding models
- **Batch Processing**: Configure batch sizes for rate limiting
- **Progress Tracking**: Real-time progress and statistics
- **Resume Capability**: Handle interruptions and resume processing

### Phase 5: Error Handling and Monitoring

#### 5.1 Robust Error Handling
- **Embedding Failures**: Fallback to alternative models
- **Pinecone Failures**: Retry logic with exponential backoff
- **MongoDB Failures**: Transaction rollback for consistency
- **Partial Failures**: Continue processing other chunks

#### 5.2 Logging and Monitoring
- **Structured Logging**: Consistent with existing pipeline logging
- **Progress Tracking**: Chunks processed, embeddings created, errors
- **Performance Metrics**: Throughput, error rates, processing times

### Phase 6: Configuration and Environment

#### 6.1 Environment Variables
```bash
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=chatbot-vectors
PINECONE_ENVIRONMENT=us-east-1

# Embedding Configuration  
DEFAULT_EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_BATCH_SIZE=100
MAX_EMBEDDING_WORKERS=4
```

#### 6.2 Configuration Validation
- **Startup Checks**: Verify all required environment variables
- **Model Availability**: Test embedding model access before processing
- **Pinecone Connectivity**: Verify index exists or can be created

## Implementation Sequence

### Step 1: Database Query Enhancement
1. Add MongoDB query methods to `embeddings.py`
2. Test chunk retrieval and filtering
3. Add unit tests for database operations

### Step 2: Pinecone Integration  
1. Add Pinecone client initialization
2. Implement vector upsert operations
3. Test with small batch of chunks

### Step 3: Embedding Processing
1. Implement text preparation and embedding generation
2. Add batch processing capabilities
3. Test end-to-end embedding workflow

### Step 4: Database Updates
1. Implement vector ID update operations
2. Add error handling and rollback logic
3. Test data consistency

### Step 5: Pipeline Integration
1. Create standalone embedding pipeline class
2. Add CLI interface for standalone operation
3. Integrate with master pipeline

### Step 6: Testing and Validation
1. Test with existing sample data
2. Validate Pinecone storage and retrieval
3. Performance testing with larger datasets

## Key Design Decisions

### 1. Pinecone Vector ID Strategy
- **Use MongoDB chunk `_id` as Pinecone vector ID**
- Ensures 1:1 mapping between MongoDB chunks and Pinecone vectors
- Enables efficient cross-referencing

### 2. Text Preparation Format
```
Summary: {chunk.summary}

Content: {chunk.content}
```
- Consistent format for all embeddings
- Preserves both summary and content information
- Compatible with existing embedding models

### 3. Namespace Organization
- **Use existing MongoDB namespace for Pinecone namespace**
- Maintains consistent data organization
- Enables namespace-based access control

### 4. Batch Processing Strategy
- **Default batch size: 100 chunks**
- Rate limiting to respect API limits
- Parallel processing with configurable workers

### 5. Error Recovery
- **Continue processing on individual chunk failures**
- Track failed chunks for separate retry processing
- Maintain data consistency between MongoDB and Pinecone

## Dependencies Required

### New Python Packages
```txt
pinecone-client>=3.0.0
```

### Environment Variables
```bash
PINECONE_API_KEY=your_api_key
PINECONE_INDEX_NAME=chatbot-vectors
PINECONE_ENVIRONMENT=us-east-1
```

## Testing Strategy

### Unit Tests
- Database query operations
- Embedding text preparation
- Pinecone client operations
- Vector ID updates

### Integration Tests
- End-to-end embedding pipeline
- Master pipeline integration
- Error handling scenarios

### Performance Tests
- Large batch processing
- Concurrent embedding generation
- Memory usage optimization

## Success Criteria

1. **Successful Embedding Generation**: All chunks can be embedded using selected models
2. **Pinecone Storage**: Embeddings are correctly stored in Pinecone with proper metadata
3. **Database Consistency**: MongoDB chunks are updated with correct Pinecone vector IDs
4. **Performance**: Process 1000+ chunks efficiently with rate limiting
5. **Error Resilience**: Handle API failures and partial processing gracefully
6. **User Experience**: Clear CLI interface with progress tracking and configuration options

## Future Enhancements

### 1. Multi-Index Support
- Support for multiple Pinecone indexes
- Index selection based on embedding model or use case

### 2. Embedding Model Comparison
- A/B testing framework for different embedding models
- Performance metrics comparison

### 3. Incremental Updates
- Detect content changes in chunks
- Selective re-embedding for updated content

### 4. Vector Search Integration
- Direct integration with retrieval systems
- Semantic search capabilities within the pipeline

This plan provides a comprehensive roadmap for integrating embeddings into the existing RAG chatbot pipeline while maintaining consistency with current architecture patterns and ensuring robust error handling and performance.