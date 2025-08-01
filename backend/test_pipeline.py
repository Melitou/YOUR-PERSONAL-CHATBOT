#!/usr/bin/env python3
"""
Test script for the document upload pipeline
"""

from document_pipeline import DocumentPipeline
import os


def test_upload_folder():
    """Test the pipeline with the Upload folder"""
    try:
        print("Testing Document Upload Pipeline...")

        # Initialize pipeline
        pipeline = DocumentPipeline()

        # Test with Upload folder
        upload_folder = "./Upload"
        namespace = "examples"

        # Process the directory
        results = pipeline.process_directory(upload_folder, namespace)

        # Close pipeline
        pipeline.close()

        print(f"\nTest completed successfully!")
        return results

    except Exception as e:
        print(f"Test failed with error: {e}")
        return None


if __name__ == "__main__":
    test_upload_folder()
