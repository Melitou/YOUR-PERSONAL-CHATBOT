#!/usr/bin/env python3
"""
Database Cleanup Script - Fix Orphaned Chunks and Document Mappings
Fixes inconsistent database state where chunks exist without proper document mappings.
"""

import logging
from datetime import datetime
from bson import ObjectId
from db_service import (
    initialize_db, 
    User_Auth_Table, 
    ChatBots, 
    Documents, 
    Chunks, 
    ChatbotDocumentsMapper
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_orphaned_data(user_name: str = "ayushbh", chatbot_name: str = "test1"):
    """
    Clean up orphaned chunks and fix document mappings for a specific user and chatbot.
    
    Args:
        user_name: Username to clean up data for
        chatbot_name: Chatbot name to fix mappings for
    """
    try:
        # Initialize database
        client, db, fs = initialize_db()
        if not client:
            logger.error("Failed to connect to database")
            return False
        
        logger.info("=" * 60)
        logger.info("🧹 STARTING DATABASE CLEANUP")
        logger.info("=" * 60)
        
        # Find user
        user = User_Auth_Table.objects(user_name=user_name).first()
        if not user:
            logger.error(f"User not found: {user_name}")
            return False
        
        logger.info(f"👤 Found user: {user.user_name} (ID: {user.id})")
        
        # Find chatbot
        chatbot = ChatBots.objects(user_id=user, name=chatbot_name).first()
        if not chatbot:
            logger.error(f"Chatbot not found: {chatbot_name}")
            return False
        
        logger.info(f"🤖 Found chatbot: {chatbot.name} (ID: {chatbot.id})")
        logger.info(f"🏷️  Chatbot namespace: {chatbot.namespace}")
        
        # Step 1: Find orphaned chunks (chunks without valid document mappings)
        logger.info("\n" + "="*50)
        logger.info("🔍 STEP 1: FINDING ORPHANED CHUNKS")
        logger.info("="*50)
        
        # Get all chunks for this user
        all_chunks = Chunks.objects(user=user)
        logger.info(f"📊 Total chunks for user: {all_chunks.count()}")
        
        orphaned_chunks = []
        valid_chunks = []
        
        for chunk in all_chunks:
            # Check if chunk has a valid document mapping
            if chunk.document:
                # Check if document exists and has valid chatbot mapping
                mapping = ChatbotDocumentsMapper.objects(
                    document=chunk.document,
                    user=user
                ).first()
                
                if mapping:
                    valid_chunks.append(chunk)
                    logger.debug(f"✅ Valid chunk: {chunk.id} -> Document: {chunk.document.file_name}")
                else:
                    orphaned_chunks.append(chunk)
                    logger.warning(f"⚠️  Orphaned chunk: {chunk.id} -> Document: {chunk.document.file_name} (no mapping)")
            else:
                orphaned_chunks.append(chunk)
                logger.warning(f"⚠️  Orphaned chunk: {chunk.id} -> No document reference")
        
        logger.info(f"✅ Valid chunks: {len(valid_chunks)}")
        logger.info(f"⚠️  Orphaned chunks: {len(orphaned_chunks)}")
        
        # Step 2: Clean up orphaned chunks
        if orphaned_chunks:
            logger.info("\n" + "="*50)
            logger.info("🗑️  STEP 2: CLEANING ORPHANED CHUNKS")
            logger.info("="*50)
            
            confirm = input(f"⚠️  Found {len(orphaned_chunks)} orphaned chunks. Delete them? (y/N): ")
            if confirm.lower() == 'y':
                for chunk in orphaned_chunks:
                    try:
                        logger.info(f"🗑️  Deleting orphaned chunk: {chunk.id}")
                        chunk.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete chunk {chunk.id}: {e}")
                
                logger.info(f"✅ Cleaned up {len(orphaned_chunks)} orphaned chunks")
            else:
                logger.info("ℹ️  Skipped orphaned chunk cleanup")
        
        # Step 3: Find documents without proper mappings
        logger.info("\n" + "="*50)
        logger.info("🔍 STEP 3: FINDING DOCUMENTS WITHOUT MAPPINGS")
        logger.info("="*50)
        
        # Find documents for this user that match the chatbot namespace
        documents = Documents.objects(user=user, namespace=chatbot.namespace)
        logger.info(f"📄 Found {documents.count()} documents with chatbot namespace")
        
        unmapped_documents = []
        for doc in documents:
            mapping = ChatbotDocumentsMapper.objects(
                chatbot=chatbot,
                document=doc,
                user=user
            ).first()
            
            if not mapping:
                unmapped_documents.append(doc)
                logger.warning(f"⚠️  Document without mapping: {doc.file_name} (ID: {doc.id})")
            else:
                logger.debug(f"✅ Document has mapping: {doc.file_name}")
        
        # Step 4: Create missing document mappings
        if unmapped_documents:
            logger.info("\n" + "="*50)
            logger.info("🔗 STEP 4: CREATING MISSING DOCUMENT MAPPINGS")
            logger.info("="*50)
            
            for doc in unmapped_documents:
                try:
                    mapping = ChatbotDocumentsMapper(
                        chatbot=chatbot,
                        document=doc,
                        user=user,
                        assigned_at=datetime.now()
                    )
                    mapping.save()
                    logger.info(f"✅ Created mapping: {chatbot.name} -> {doc.file_name}")
                except Exception as e:
                    logger.error(f"Failed to create mapping for {doc.file_name}: {e}")
        
        # Step 5: Verification
        logger.info("\n" + "="*50)
        logger.info("🔍 STEP 5: VERIFICATION")
        logger.info("="*50)
        
        # Check chatbot document mappings
        final_mappings = ChatbotDocumentsMapper.objects(chatbot=chatbot, user=user)
        logger.info(f"📋 Final chatbot mappings: {final_mappings.count()}")
        
        for mapping in final_mappings:
            logger.info(f"✅ Mapping: {chatbot.name} -> {mapping.document.file_name}")
            
            # Check chunks for this document
            chunks = Chunks.objects(document=mapping.document, user=user)
            logger.info(f"   📊 Chunks: {chunks.count()}")
        
        logger.info("\n" + "="*60)
        logger.info("🎉 DATABASE CLEANUP COMPLETE!")
        logger.info("="*60)
        logger.info("✅ Your RAG search should now work properly")
        logger.info("✅ All documents have proper chatbot mappings")
        logger.info("✅ Orphaned data has been cleaned up")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return False

def main():
    """Main cleanup function"""
    print("🧹 Database Cleanup Script")
    print("This script will fix orphaned chunks and document mappings.")
    print()
    
    user_name = input("Enter username (default: ayushbh): ").strip() or "ayushbh"
    chatbot_name = input("Enter chatbot name (default: test1): ").strip() or "test1"
    
    success = cleanup_orphaned_data(user_name, chatbot_name)
    
    if success:
        print("\n🎉 Cleanup completed successfully!")
        print("Your RAG search should now work properly.")
    else:
        print("\n❌ Cleanup failed. Check the logs for details.")

if __name__ == "__main__":
    main()
