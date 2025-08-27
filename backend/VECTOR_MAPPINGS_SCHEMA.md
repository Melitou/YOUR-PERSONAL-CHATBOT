# ChunkVectorMappings Schema Design

## 🎯 Purpose
This collection creates a many-to-many relationship between chunks and chatbots, allowing:
- Same chunk content to have different vector embeddings for different chatbots
- Different embedding models (OpenAI vs Gemini) for the same content
- Independent chatbot operations and deletions

## 📊 Schema Definition

```python
class ChunkVectorMappings(Document):
    """
    Maps chunks to their vector representations in different chatbots.
    Each mapping represents one embedding of a chunk for a specific chatbot.
    """
    
    # Core Relationships
    chunk = ReferenceField(Chunks, required=True)
    chatbot = ReferenceField(ChatBots, required=True) 
    user = ReferenceField(User_Auth_Table, required=True)  # For security isolation
    
    # Embedding Details
    embedding_model = StringField(required=True)  # e.g., "text-embedding-3-small"
    pinecone_index = StringField(required=True)   # e.g., "chatbot-vectors-openai-1536"
    vector_id = StringField(required=True)        # e.g., "chunk123_abc_def456"
    
    # Metadata
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField()  # For re-embedding tracking
    
    meta = {
        'collection': 'chunk_vector_mappings',
        'indexes': [
            # PRIMARY: Unique mapping per chunk+chatbot
            {'fields': [('chunk', 1), ('chatbot', 1)], 'unique': True},
            
            # PERFORMANCE: Fast chatbot lookups
            {'fields': ['chatbot']},
            
            # PERFORMANCE: Fast chunk lookups (find all chatbots using this chunk)
            {'fields': ['chunk']},
            
            # PERFORMANCE: User isolation
            {'fields': ['user']},
            
            # PERFORMANCE: Model-specific queries
            {'fields': ['embedding_model']},
            
            # OPERATIONS: Pinecone vector management
            {'fields': ['vector_id']},
            {'fields': ['pinecone_index']},
            
            # CLEANUP: Find mappings by creation date
            {'fields': ['created_at']},
            
            # COMPOSITE: Fast user+chatbot queries
            {'fields': [('user', 1), ('chatbot', 1)]},
            
            # COMPOSITE: Find all vectors for user+model combination
            {'fields': [('user', 1), ('embedding_model', 1)]}
        ]
    }
```

## 🔍 Query Patterns

### Most Common Queries:
1. **RAG Lookup**: "Find vector_id for chunk X in chatbot Y"
   ```python
   mapping = ChunkVectorMappings.objects(chunk=chunk_id, chatbot=chatbot_id).first()
   vector_id = mapping.vector_id if mapping else None
   ```

2. **Chatbot Vectors**: "Get all vectors for chatbot deletion"
   ```python
   mappings = ChunkVectorMappings.objects(chatbot=chatbot_id)
   ```

3. **Chunk Sharing**: "Which chatbots use this chunk?"
   ```python
   mappings = ChunkVectorMappings.objects(chunk=chunk_id)
   ```

## 🔄 Data Flow Examples

### Scenario: Same Document, Different Models

**Document**: `AIBYDNA.pdf` 
**Chunk**: `ObjectId("chunk123")` - "We empower organizations..."

**ChatbotA (OpenAI)**:
```json
{
  "_id": ObjectId("mapping_001"),
  "chunk": ObjectId("chunk123"),
  "chatbot": ObjectId("chatbot_A"),
  "user": ObjectId("user_ayush"),
  "embedding_model": "text-embedding-3-small",
  "pinecone_index": "chatbot-vectors-openai-1536", 
  "vector_id": "chunk123_abc123_chatbotA",
  "created_at": "2025-01-15T10:00:00Z"
}
```

**ChatbotB (Gemini)**:
```json
{
  "_id": ObjectId("mapping_002"),
  "chunk": ObjectId("chunk123"),
  "chatbot": ObjectId("chatbot_B"), 
  "user": ObjectId("user_ayush"),
  "embedding_model": "gemini-embedding-001",
  "pinecone_index": "chatbot-vectors-google-3072",
  "vector_id": "chunk123_def456_chatbotB", 
  "created_at": "2025-01-15T11:00:00Z"
}
```

## 🛡️ Data Integrity Features

1. **Unique Constraint**: Prevents duplicate mappings for same chunk+chatbot
2. **Required Fields**: Ensures all critical data is present
3. **User Isolation**: Each user's data is properly isolated
4. **Audit Trail**: Created/updated timestamps for debugging

## 🗑️ Deletion Behavior

**Delete Chatbot**: Remove only mappings for that chatbot
```python
ChunkVectorMappings.objects(chatbot=chatbot_id).delete()
```

**Delete Document**: Remove mappings for all chunks of that document
```python
chunk_ids = [chunk.id for chunk in Chunks.objects(document=document_id)]
ChunkVectorMappings.objects(chunk__in=chunk_ids).delete()
```

**Delete User**: Remove all mappings for that user
```python
ChunkVectorMappings.objects(user=user_id).delete()
```

## 📈 Performance Characteristics

- **Write Performance**: Excellent (simple inserts)
- **Read Performance**: Excellent (indexed lookups)
- **Storage Overhead**: ~100 bytes per mapping
- **Scalability**: Linear with number of chunk+chatbot combinations

## 🔄 Migration Strategy

1. Create new collection with schema
2. Migrate existing `chunks.vector_id` data to mappings
3. Update application code to use mappings
4. Remove `vector_id` field from chunks collection
5. Verify data integrity and performance
