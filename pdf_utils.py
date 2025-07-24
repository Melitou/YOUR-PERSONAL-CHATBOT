"""
PDF utility functions for compliance agents
"""
import os
import pathlib
import tempfile
from typing import Optional, Tuple
from PyPDF2 import PdfReader, PdfWriter
from dotenv import load_dotenv
from llama_cloud_services import LlamaParse

# Load environment variables to access API keys
load_dotenv()

def extract_page_from_pdf(pdf_path: str, page_number: int) -> Tuple[str, str]:
    """
    Extract a specific page from a PDF file, save it as a separate PDF,
    and extract the text using LlamaParse with fallbacks.
    
    Args:
        pdf_path (str): Path to the source PDF file
        page_number (int): The page number to extract (1-based index)
        
    Returns:
        Tuple[str, str]: Path to the extracted page PDF file and the extracted text
    """
    # Validate inputs
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Convert to Path object for better path handling
    path = pathlib.Path(pdf_path)
    
    # Create output path for the extracted page
    output_dir = path.parent
    output_filename = f"{path.stem}_page_{page_number}.pdf"
    output_path = os.path.join(output_dir, output_filename)
    
    # Open the PDF file
    with open(pdf_path, 'rb') as file:
        pdf_reader = PdfReader(file)
        
        # Check if page number is valid
        if page_number < 1 or page_number > len(pdf_reader.pages):
            raise ValueError(f"Invalid page number: {page_number}. PDF has {len(pdf_reader.pages)} pages.")
        
        # Create a PDF writer
        pdf_writer = PdfWriter()
        
        # Add the specified page (0-based index in PyPDF2)
        pdf_writer.add_page(pdf_reader.pages[page_number - 1])
        
        # Write the extracted page to the output file
        with open(output_path, 'wb') as output_file:
            pdf_writer.write(output_file)
    
    # Extract text from the page using LlamaParse first, then fallbacks
    text = extract_text_from_pdf_page(output_path)
    
    print(f"Extracted page {page_number} to {output_path}")
    return output_path, text

def extract_text_from_pdf_page(pdf_path: str) -> str:
    """
    Extract text from a PDF page using LlamaParse with fallbacks to local methods.
    
    This function uses LlamaParse as the primary method for high-quality text extraction,
    with local methods (PyPDF2, PyMuPDF, OCR) as fallbacks.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    # First try LlamaParse for best quality
    try:
        # Set up LlamaParse with premium mode
        parser = LlamaParse(
            result_type="text", 
            #premium_mode=True,
            api_key=os.getenv("LLAMA_CLOUD_API_KEY")
        )
        
        # Parse the PDF
        print("Extracting text using LlamaParse...")
        result = parser.parse(pdf_path)
        
        # Process the result
        if result and isinstance(result, list) and len(result) > 0:
            # Collect all text from results
            all_content = []
            for item in result:
                if isinstance(item, dict) and 'text' in item:
                    all_content.append(item['text'])
                elif isinstance(item, str):
                    all_content.append(item)
            
            # Combine all content
            content = "\n\n".join(all_content)
            
            # If we got reasonable text, return it
            if content and len(content.strip()) > 50:
                print("Successfully extracted text using LlamaParse")
                return content
        
        print("LlamaParse returned insufficient content, trying fallbacks")
    except ImportError:
        print("LlamaParse not available, falling back to local methods")
    except Exception as e:
        print(f"Error with LlamaParse extraction: {e}")
    
    # Fallback to PyPDF2
    try:
        reader = PdfReader(pdf_path)
        page_text = reader.pages[0].extract_text()
        
        # If we got reasonable text, return it
        if page_text and len(page_text.strip()) > 50:
            print("Successfully extracted text using PyPDF2")
            return page_text
    except Exception as e:
        print(f"Error with PyPDF2 extraction: {e}")
    
    # Try PyMuPDF fallback
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        page = doc[0]  # First page (0-based index)
        
        # Get text with more detailed options
        text = page.get_text("text")
        doc.close()
        
        if text and len(text.strip()) > 50:
            print("Successfully extracted text using PyMuPDF")
            return text
    except ImportError:
        print("PyMuPDF not available, trying next method")
    except Exception as e:
        print(f"Error with PyMuPDF extraction: {e}")
    
    # Last resort: use OCR if available
    try:
        import pytesseract
        from PIL import Image
        
        # Convert PDF to image
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page = doc[0]
            pix = page.get_pixmap(dpi=300)
            
            # Save the pixmap to a temporary file
            tmp_img_path = tempfile.mktemp(suffix=".png")
            pix.save(tmp_img_path)
            
            # Use OCR to extract text
            text = pytesseract.image_to_string(Image.open(tmp_img_path))
            
            # Clean up
            os.remove(tmp_img_path)
            doc.close()
            
            if text and len(text.strip()) > 50:
                print("Successfully extracted text using OCR")
                return text
        except ImportError:
            print("PyMuPDF or Tesseract not available for OCR")
        except Exception as e:
            print(f"Error with OCR extraction: {e}")
    except ImportError:
        print("OCR libraries not available")
    
    # All methods failed
    print("All extraction methods failed")
    return "No text could be extracted from the PDF."

def extract_markdown_from_full_pdf(pdf_path: str) -> Tuple[str, str]:
    """
    Extract entire PDF as markdown using LlamaParse with fallback to text extraction.
    
    This function parses the complete PDF document into markdown format,
    preserving structure like headers, tables, lists, and references.
    Falls back to PyPDF2 text extraction if LlamaParse fails.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        Tuple[str, str]: (markdown_content, plain_text_content)
    """
    markdown_content = ""
    plain_text_content = ""
    
    # First try LlamaParse with markdown output
    try:
        from llama_parse import LlamaParse
        
        # Get API key and region from environment
        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        region = os.getenv("LLAMA_CLOUD_REGION", "NA").upper()  # Default to NA if not specified
        
        # Set base URL based on region
        if region == "EU":
            base_url = "https://api.cloud.eu.llamaindex.ai"
            print("Using EU region for LlamaParse")
        else:
            base_url = "https://api.cloud.llamaindex.ai"  # NA region (default)
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
        documents = parser.load_data(pdf_path)
        
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
            
            # Verify we got substantial content
            if markdown_content and len(markdown_content.strip()) > 50:
                # Note: Success logging is handled by the caller in api.py
                # Convert markdown to plain text
                plain_text_content = convert_markdown_to_plain_text(markdown_content)
                return markdown_content, plain_text_content
            else:
                print("LlamaParse returned insufficient content, trying fallback")
        else:
            print("LlamaParse returned no documents, trying fallback")
            
    except ImportError:
        print("LlamaParse not available (pip install llama-parse), falling back to PyPDF2")
    except Exception as e:
        print(f"Error with LlamaParse extraction: {e}")
        print("Falling back to PyPDF2")
    
    # Fallback to PyPDF2 for text extraction
    print("Using PyPDF2 fallback for text extraction")
    try:
        reader = PdfReader(pdf_path)
        pages_markdown = []
        pages_text = []
        
        # Extract text from all pages
        print(f"Extracting text from {len(reader.pages)} pages using PyPDF2")
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                # Create markdown-like structure
                pages_markdown.append(f"# Page {i + 1}\n\n{page_text}")
                pages_text.append(page_text)
        
        # Combine all pages
        if pages_markdown:
            markdown_content = "\n\n---\n\n".join(pages_markdown)
            plain_text_content = "\n\n".join(pages_text)
            print(f"Successfully extracted {len(plain_text_content)} characters from {len(reader.pages)} pages using PyPDF2")
            return markdown_content, plain_text_content
        else:
            print("PyPDF2 extracted no text from any pages")
    except Exception as e:
        print(f"Error with PyPDF2 extraction: {e}")
    
    # If all methods fail
    print("All extraction methods failed")
    error_msg = "Failed to extract content from PDF."
    return error_msg, error_msg

def convert_markdown_to_plain_text(markdown_text: str) -> str:
    """
    Convert markdown formatted text to plain text by removing markdown syntax.
    
    Args:
        markdown_text (str): The markdown formatted text
        
    Returns:
        str: Plain text with markdown syntax removed
    """
    import re
    
    # Remove markdown headers (# ## ### etc.)
    text = re.sub(r'^#+\s+', '', markdown_text, flags=re.MULTILINE)
    
    # Remove bold (**text** or __text__)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    
    # Remove italic (*text* or _text_)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    
    # Remove links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Remove images ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    
    # Remove code blocks ```code```
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    
    # Remove inline code `code`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove horizontal rules
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    
    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove list markers (- * + or numbers)
    text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove table formatting (basic)
    text = re.sub(r'\|', ' ', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    
    return text

def check_pdf_size(pdf_path: str) -> float:
    """
    Check if the PDF file exists and return its size in MB.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        float: Size of the PDF file in MB
        
    Raises:
        FileNotFoundError: If the PDF file does not exist
        ValueError: If the path does not point to a PDF file
    """
    # Convert to Path object for better path handling
    path = pathlib.Path(pdf_path)
    
    # Validate that the file exists
    if not path.exists():
        raise FileNotFoundError(f"The file {pdf_path} does not exist.")
    
    # Validate that it's a PDF file
    if path.suffix.lower() != '.pdf':
        raise ValueError(f"The file {pdf_path} is not a PDF file.")
    
    # Get the file size in bytes and convert to MB
    file_size_bytes = path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    print(f"PDF size: {file_size_mb:.2f} MB")
    
    return file_size_mb