"""
Pinecone Index Information Script
This script connects to a Pinecone index and displays basic information about it.
"""

import os
from pinecone import Pinecone


def get_pinecone_info():
    """
    Connect to Pinecone and retrieve index information
    """
    try:
        # Initialize Pinecone client with your API key
        # You can set your API key as an environment variable or replace with your actual key
        api_key = os.getenv('PINECONE_API_KEY')

        if not api_key:
            print("⚠️  PINECONE_API_KEY environment variable not found.")
            print("Please set your API key using one of these methods:")
            print("1. Set environment variable: $env:PINECONE_API_KEY='your_api_key'")
            print(
                "2. Or edit this script and replace 'YOUR_API_KEY_HERE' with your actual key")
            print("\nFor now, please enter your Pinecone API key:")
            api_key = input("API Key: ").strip()

            if not api_key:
                print("❌ No API key provided. Exiting.")
                return

        pc = Pinecone(api_key=api_key)

        # Your index name
        index_name = "chatbot-vectors-google"

        # Check if the index exists
        if not pc.has_index(index_name):
            print(f"❌ Index '{index_name}' does not exist.")
            print("Available indexes:")
            indexes = pc.list_indexes()
            for idx in indexes:
                print(f"  - {idx['name']}")
            return

        # Target the index
        index = pc.Index(index_name)

        # Get index statistics
        print(f"📊 Index Information for '{index_name}':")
        print("=" * 50)

        # Get index description to verify host
        index_description = pc.describe_index(index_name)
        print(f"🌍 Host: {index_description.host}")

        stats = index.describe_index_stats()

        # Display dimension
        print(f"🔢 Dimension: {stats.get('dimension', 'N/A')}")

        # Display total vector count
        print(f"📈 Total Vector Count: {stats.get('total_vector_count', 0)}")

        # Display index fullness
        index_fullness = stats.get('index_fullness', 0)
        print(f"📏 Index Fullness: {index_fullness:.2%}")

        # Display metric
        print(f"📐 Distance Metric: {stats.get('metric', 'N/A')}")

        # Display vector type
        print(f"🏷️  Vector Type: {stats.get('vector_type', 'N/A')}")

        # Display namespaces
        namespaces = stats.get('namespaces', {})
        print(f"\n📁 Available Namespaces ({len(namespaces)}):")

        if namespaces:
            for namespace, info in namespaces.items():
                vector_count = info.get('vector_count', 0)
                namespace_display = namespace if namespace else "[default namespace]"
                print(f"  • {namespace_display}: {vector_count} vectors")
        else:
            print("  No namespaces found or index is empty")

        print("\n✅ Successfully retrieved index information!")

    except Exception as e:
        print(f"❌ Error connecting to Pinecone: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Check that your API key is correct")
        print("2. Verify that the index name 'chatbot-vectors-google' exists")
        print("3. Ensure you have proper permissions to access the index")


if __name__ == "__main__":
    print("🚀 Connecting to Pinecone...")
    get_pinecone_info()
