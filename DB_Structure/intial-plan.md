**TABLES**

## User_auth_table :
### Columns:
1) Usename 
2) Password
3) first name
4) last name
5) Email id
6) User_id   **MAIN CONNECTOR**

## documents :
### columns:
1) user_id
2) file_name
3) file_type
4) gridfs_file_id  **(links to the raw file in GridFS)**
5) status **(e.g., 'pending', 'processed', 'failed')**
6) full_hash **SHA256**
7) namespace
8) created_at

## chunks :
### columns :
1) _id
2) document_id **(links to the documents table)**
3) user_id
4) namespace
5) chunk_index
6) content
7) vector_id **(the ID used in Pinecone)**
8) created_at

## GridFS Storage (Internal MongoDB collections):
### fs.files (metadata):
1) _id
2) filename
3) contentType
4) length
5) uploadDate

### fs.chunks (file content):
1) files_id **(links to fs.files)**
2) n (chunk sequence number)
3) data (binary chunk)

## Pinecone Vector Structure:
### Columns (in Pinecone):
1) id **(e.g., the _id from the chunks collection)**
2) values (embeddings)
3) metadata (user_id, document_id, chunk_index)
