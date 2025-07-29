from file_type import doc_type_check
import os
from dotenv import load_dotenv
import tempfile
from docx import Document
load_dotenv()

file_bytes = open("./Files/Θέματα Επιστήμης Δεδομένων.docx", "rb").read()


def docx_to_md(file_bytes: bytes) -> str:
    """
    Extract entire DOCX as markdown using docx text extraction.

    This function parses the complete DOCX document into markdown format,
    preserving structure like headers, tables, lists, and references.

    Args:
        file_bytes: bytes: 

    Returns:
        str: markdown_content
    """
    markdown_content = ""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_file.flush()
    # First try LlamaParse with markdown output
    # try:
    #     from llama_parse import LlamaParse

    #     # Get API key and region from environment
    #     api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    #     # Default to NA if not specified
    #     region = os.getenv("LLAMA_CLOUD_REGION", "NA").upper()

    #     # Set base URL based on region
    #     if region == "EU":
    #         base_url = "https://api.cloud.eu.llamaindex.ai"
    #         print("Using EU region for LlamaParse")
    #     else:
    #         # NA region (default)
    #         base_url = "https://api.cloud.llamaindex.ai"
    #         print("Using NA region for LlamaParse")

    #     # Set up LlamaParse with markdown output
    #     parser = LlamaParse(
    #         api_key=api_key,
    #         result_type="markdown",  # Get structured markdown output
    #         verbose=False,  # Show progress
    #         base_url=base_url,  # Specify the region-specific base URL
    #         num_workers=4,  # Parallel processing for speed
    #         # partition_pages=100,  # Split large documents if needed
    #         invalidate_cache=False,  # Force fresh parsing
    #         split_by_page=True,  # Ensure each page is parsed separately
    #     )

    #     # Parse the entire PDF document
    #     # Note: Logging is handled by the caller in api.py

    #     # Method 1: Direct parse - returns list of documents
    #     documents = parser.load_data(tmp_file.name)

    #     # Combine all documents/pages into one markdown file with page numbers
    #     if documents and len(documents) > 0:
    #         # Extract text from all document objects with page numbering
    #         all_pages_markdown = []

    #         # Check if LlamaParse returns one document or multiple
    #         if len(documents) == 1:
    #             # Single document returned - check if it contains page info
    #             doc_text = ""
    #             if hasattr(documents[0], 'text'):
    #                 doc_text = documents[0].text
    #             elif isinstance(documents[0], dict) and 'text' in documents[0]:
    #                 doc_text = documents[0]['text']
    #             elif isinstance(documents[0], str):
    #                 doc_text = documents[0]

    #             # If no page markers exist, add them (for single page PDFs)
    #             if "Page " not in doc_text[:100]:
    #                 markdown_content = f"# Page 1\n\n{doc_text}"
    #             else:
    #                 markdown_content = doc_text
    #         else:
    #             # Multiple documents - one per page
    #             for page_num, doc in enumerate(documents, 1):
    #                 doc_text = ""
    #                 if hasattr(doc, 'text'):
    #                     doc_text = doc.text
    #                 elif isinstance(doc, dict) and 'text' in doc:
    #                     doc_text = doc['text']
    #                 elif isinstance(doc, str):
    #                     doc_text = doc

    #                 # Add page header and content
    #                 page_markdown = f"# Page {page_num}\n\n{doc_text}"
    #                 all_pages_markdown.append(page_markdown)

    #             # Join all pages with clear separation
    #             markdown_content = "\n\n---\n\n".join(all_pages_markdown)
    #             return markdown_content
    # except ImportError:
    #     print(
    #         "LlamaParse not available (pip install llama-parse), falling back to docx")
    # except Exception as e:
    #     print(f"Error with LlamaParse extraction: {e}")
    #     print("Falling back to docx")

    # print("Using docx fallback for text extraction")
    try:
        doc = Document(tmp_file.name)
        for paragraph in doc.paragraphs:
            markdown_content += paragraph.text + "\n"
        return markdown_content
    except ImportError:
        print(
            "docx not available (pip install python-docx), falling back to text extraction")
        return None
    except Exception as e:
        print(f"Error with docx extraction: {e}")
        return None


type_doc = doc_type_check(file_bytes)
print(type_doc)

if type_doc == "The document provided is a DOCX file":
    md = docx_to_md(file_bytes)
    print(md[:100])
else:
    print("Unsupported document type for this script.")
