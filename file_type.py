import csv


def doc_type_check(file_bytes: bytes) -> str:
    """
    This function checks the type of the document and returns the type of the document
    """
    if file_bytes.startswith(b"%PDF"):
        return "The document provided is a PDF file"
    elif file_bytes.startswith(b"PK"):
        return "The document provided is a DOCX file"
    try:
        sample = file_bytes[:2048].decode("utf-8", errors="ignore")

        # Use CSV sniffer to detect structure
        sniffer = csv.Sniffer()
        try:
            if sniffer.has_header(sample):
                return "The document provided is a CSV file"
        except csv.Error:
            pass  # Not a CSV

    except Exception as e:
        print(f"Decoding or sniffing error: {e}")

    # Default to plain text
    return "The document provided is a TXT file"


<<<<<<< HEAD
# add mb size
=======


def get_file_type_and_size(file_name: str, file_bytes: bytes) -> list:
    """
    Extract file type and size from file name and bytes.
    
    Args:
        file_name (str): Full file name with extension
        file_bytes (bytes): File content as bytes
        
    Returns:
        list: [file_extension, size_in_mb]
    """
    # Extract file extension
    if '.' in file_name:
        file_type = file_name.split('.')[-1].lower()
    else:
        file_type = 'unknown'
        
        # Calculate file size in MB
    size_mb = round(len(file_bytes) / (1024 * 1024), 2)
        
    return [file_type, size_mb]

>>>>>>> 016b1b1b855b506b96a7ff4acea3c7e4f1513a4c
