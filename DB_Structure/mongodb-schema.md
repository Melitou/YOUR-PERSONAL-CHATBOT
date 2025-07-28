# RAG Chatbot Builder - Enhanced MongoDB Schema (with GridFS)

## 🎯 **Enhanced Flow (Scalable MVP)**
1. User uploads PDFs.
2. Backend stores raw files in **MongoDB GridFS**.
3. A record for each file is created in the **`documents`** collection, linking to GridFS.
4. Files are processed: text is extracted and split into chunks.
5. Each chunk is saved as a separate document in the **`chunks`** collection.
6. Chunks are embedded and upserted to **Pinecone**, using the `_id` from the `chunks` collection as the vector ID.
7. Chatbot is ready, querying Pinecone with the user's namespace.

**✅ Schema Verified - Scalable & Production Ready**

---

## MongoDB Collections

### 1. User Authentication (`users`)
```javascript
// Collection: users
{
  "_id": ObjectId(),
  "username": "john_doe",
  "password": "hashed_password",
  "first_name": "John",
  "last_name": "Doe", 
  "email": "john@example.com",
  "created_at": ISODate()
}
```

### 2. Documents (`documents`)
*This table holds metadata for each uploaded file. The raw file itself is in GridFS.*
```javascript
// Collection: documents
{
  "_id": ObjectId(),
  "user_id": ObjectId("..."), // Links to the `users` collection
  "namespace": "user123_support_bot", // User-defined namespace
  "file_name": "manual.pdf",
  "file_type": "pdf",
  "gridfs_file_id": ObjectId("..."), // CRITICAL: Links to the file in GridFS's `fs.files`
  "full_hash": "sha256_hash_of_file",
  "created_at": ISODate()
}
```

### 3. Text Chunks (`chunks`)
*This collection stores the actual text chunks extracted from documents, ready for embedding. Each chunk is its own document.*
```javascript
// Collection: chunks
{
  "_id": ObjectId(), // This ID will be used as the Pinecone vector ID
  "document_id": ObjectId("..."), // Foreign key to the `documents` collection
  "user_id": ObjectId("..."),
  "namespace": "user123_support_bot",
  "chunk_index": 0, // The sequential order of the chunk within the document
  "content": "This is the first paragraph of text extracted from the PDF...",
  "summary":"the chunk summary from AI",
  "vector_id": "pinecone_vector_id_for_this_chunk", // Initially null, populated after embedding
  "created_at": ISODate()
}
```

### 4. GridFS Collections (Managed by MongoDB Driver)
*You don't typically interact with these directly. They are used by the driver to store and retrieve large files.*
- **`fs.files`**: Contains file metadata (filename, size, etc.). The `_id` here is what you store in `documents.gridfs_file_id`.
- **`fs.chunks`**: Contains the binary chunks of the files.

---

## Pinecone Vector Structure
```javascript
// In Pinecone Index: "chatbot-vectors"  
// Namespace: "user123_support_bot"
{
  // The `id` is the string representation of the `_id` from the `chunks` collection
  "id": "60d5ecf1a9b2f7a1e4b8f8b1", 
  "values": [0.1, 0.2, 0.3, ...], // Embeddings from the chunk content
  "metadata": {
    "user_id": "60d5ecf1a9b2f7a1e4b8f8a0",
    "document_id": "60d5ecf1a9b2f7a1e4b8f8a5",
    "chunk_index": 0,
    "file_name": "manual.pdf"
  }
}
```

---

## 🔄 **Exact Processing Flow (Enhanced)**

### Step 1: File Upload
- User uploads `manual.pdf`.
- Backend streams the file content into **GridFS**.
- GridFS returns a `file_id`.

### Step 2: Create Document Record
- A new document is created in the **`documents`** collection.
```javascript
{
  "user_id": "...",
  "namespace": "user123_support_bot",
  "file_name": "manual.pdf",
  "gridfs_file_id": "gridfs_file_id_from_step_1",
  "status": "pending"
}
```

### Step 3: Background Processing (FastAPI Background Tasks)
- A background worker picks up the new document.
- It retrieves the raw file from GridFS using the `gridfs_file_id`.
- It extracts the text and splits it into chunks.

### Step 4: Create Chunk Documents
- For each text chunk, create a new document in the **`chunks`** collection with the `vector_id` field set to `null`.
```javascript
// Loop over chunks and insert them
{
  "document_id": "document_id_from_step_2",
  "user_id": "...",
  "namespace": "user123_support_bot",
  "chunk_index": 0,
  "content": "Text of the first chunk...",
  "vector_id": null
}
```

### Step 5: Pinecone Embedding & Update
- For each newly created chunk document (where `vector_id` is `null`):
  - Generate an embedding from its `content` and `summary`
  - Upsert the vector to Pinecone, using the chunk's `_id` (as a string) as the `id` for the vector.
  - After a successful upsert, **update** the chunk document in MongoDB to set its `vector_id`.
