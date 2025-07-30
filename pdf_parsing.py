import tempfile
from llama_parse import LlamaParse
import os
from dotenv import load_dotenv
from file_type import doc_type_check
load_dotenv()


def pdf_to_md(file_bytes: bytes) -> str:
    """
    Extract entire PDF as markdown using LlamaParse with fallback to text extraction.

    This function parses the complete PDF document into markdown format,
    preserving structure like headers, tables, lists, and references.
    Falls back to pypdf text extraction if LlamaParse fails.

    Args:
        file_bytes: bytes: 

    Returns:
        str: markdown_content
    """
    markdown_content = ""

    # First try LlamaParse with markdown output
    try:
        from llama_parse import LlamaParse

        # Get API key and region from environment
        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        # Default to NA if not specified
        region = os.getenv("LLAMA_CLOUD_REGION", "NA").upper()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_file.flush()

        # Set base URL based on region
        if region == "EU":
            base_url = "https://api.cloud.eu.llamaindex.ai"
            print("Using EU region for LlamaParse")
        else:
            # NA region (default)
            base_url = "https://api.cloud.llamaindex.ai"
            print("Using NA region for LlamaParse")

        # Set up LlamaParse with markdown output
        parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",  # Get structured markdown output
            verbose=False,  # Show progress
            base_url=base_url,  # Specify the region-specific base URL
            num_workers=4,  # Parallel processing for speed
            # partition_pages=100,  # Split large documents if needed
            invalidate_cache=False,  # Force fresh parsing
            split_by_page=True,  # Ensure each page is parsed separately
        )

        # Parse the entire PDF document
        # Note: Logging is handled by the caller in api.py

        # Method 1: Direct parse - returns list of documents
        documents = parser.load_data(tmp_file.name)

        # Combine all documents/pages into one markdown file with page numbers
        if documents and len(documents) > 0:
            # Extract text from all document objects with page numbering
            all_pages_markdown = []

            # Check if LlamaParse returns one document or multiple
            if len(documents) == 1:
                # Single document returned - check if it contains page info
                doc_text = ""
                if hasattr(documents[0], 'text'):
                    doc_text = documents[0].text
                elif isinstance(documents[0], dict) and 'text' in documents[0]:
                    doc_text = documents[0]['text']
                elif isinstance(documents[0], str):
                    doc_text = documents[0]

                # If no page markers exist, add them (for single page PDFs)
                if "Page " not in doc_text[:100]:
                    markdown_content = f"# Page 1\n\n{doc_text}"
                else:
                    markdown_content = doc_text
            else:
                # Multiple documents - one per page
                for page_num, doc in enumerate(documents, 1):
                    doc_text = ""
                    if hasattr(doc, 'text'):
                        doc_text = doc.text
                    elif isinstance(doc, dict) and 'text' in doc:
                        doc_text = doc['text']
                    elif isinstance(doc, str):
                        doc_text = doc

                    # Add page header and content
                    page_markdown = f"# Page {page_num}\n\n{doc_text}"
                    all_pages_markdown.append(page_markdown)

                # Join all pages with clear separation
                markdown_content = "\n\n---\n\n".join(all_pages_markdown)
                return markdown_content
    except ImportError:
        print(
            "LlamaParse not available (pip install llama-parse), falling back to PyPDF2")
    except Exception as e:
        print(f"Error with LlamaParse extraction: {e}")
        print("Falling back to pypdf")

    print("Using pypdf fallback for text extraction")
    try:
        from pypdf import PdfReader
        reader = PdfReader(tmp_file.name)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()
        return full_text
    except ImportError:
        print(
            "pypdf not available (pip install pypdf), there was an error with pypdf extraction")
        return None
    except Exception as e:
        print(f"Error with pypdf extraction: {e}")
        print("There was an error with pypdf extraction")
        return None


# Test code - only runs when script is executed directly
if __name__ == "__main__":
    # Example usage (commented out to prevent file not found errors)
    # file_bytes = open("example.pdf", "rb").read()
    # type_doc = doc_type_check(file_bytes)
    # print(type_doc[0])
    # print(f"File size: {type_doc[1]} bytes")
    #
    # if type_doc[0] == "The document provided is a PDF file":
    #     md = pdf_to_md(file_bytes)
    #     print(md[:100])
    # else:
    #     print("Unsupported document type for this script.")
    print("PDF parser module loaded successfully")
