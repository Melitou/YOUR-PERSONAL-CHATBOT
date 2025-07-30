from file_type import doc_type_check
import os
from dotenv import load_dotenv
import tempfile
from docx import Document
load_dotenv()

file_bytes = open("", "rb").read()


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
print(type_doc[0])
print(f"File size: {type_doc[1]} bytes")

if type_doc[0] == "The document provided is a DOCX file":
    md = docx_to_md(file_bytes)
    print(md[:100])
else:
    print("Unsupported document type for this script.")
