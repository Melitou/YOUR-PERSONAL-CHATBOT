#!/usr/bin/env python3
"""
Quick script to inspect the current MongoDB database structure
"""

from db_service import *


def inspect_database():
    """Inspect the current database structure and content"""
    client, db, fs = initialize_db()

    if not client:
        print("Failed to connect to database")
        return

    print("=== DATABASE INSPECTION ===\n")

    # Check collections
    collections = db.list_collection_names()
    print(f"Available collections: {collections}\n")

    # Check users
    try:
        users = User_Auth_Table.objects()
        print(f"Number of users: {len(users)}")
        for user in users:
            print(
                f"  User: {user.user_name}, ID: {user.id}, Email: {user.email}")
        print()
    except Exception as e:
        print(f"Error reading users: {e}\n")

    # Check documents
    try:
        docs = Documents.objects()
        print(f"Number of documents: {len(docs)}")
        for doc in docs:
            print(f"  Doc: {doc.file_name}")
            print(f"    GridFS ID: {doc.gridfs_file_id}")
            print(f"    Hash: {doc.full_hash[:16]}...")
            print(f"    Status: {doc.status}")
            print(f"    Namespace: {doc.namespace}")
        print()
    except Exception as e:
        print(f"Error reading documents: {e}\n")

    # Check GridFS files
    try:
        print("GridFS files:")
        for file_doc in db.fs.files.find():
            print(f"  File: {file_doc['filename']}")
            print(f"    ID: {file_doc['_id']}")
            print(f"    Size: {file_doc['length']} bytes")
            print(f"    Upload Date: {file_doc.get('uploadDate', 'N/A')}")
        print()
    except Exception as e:
        print(f"Error reading GridFS files: {e}\n")

    # Check chunks
    try:
        chunks = Chunks.objects()
        print(f"Number of chunks: {len(chunks)}")
        if len(chunks) > 0:
            sample_chunk = chunks[0]
            print(f"  Sample chunk: {sample_chunk.content[:50]}...")
            print(f"    Document: {sample_chunk.document.file_name}")
            print(f"    User: {sample_chunk.user.user_name}")
        print()
    except Exception as e:
        print(f"Error reading chunks: {e}\n")

    client.close()
    print("=== INSPECTION COMPLETE ===")


if __name__ == "__main__":
    inspect_database()
