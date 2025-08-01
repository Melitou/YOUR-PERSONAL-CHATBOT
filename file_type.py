import os
import csv


def doc_type_check(file_bytes: bytes) -> str:
    """
    This function checks the type of the document and returns the type of the document and the file size
    """

    # file_size = os.path.getsize(file_path)
    file_size = len(file_bytes)

    if file_bytes.startswith(b"%PDF"):
        return ("The document provided is a PDF file", file_size)
    elif file_bytes.startswith(b"PK"):
        return ("The document provided is a DOCX file", file_size)
    try:
        sample = file_bytes[:2048].decode("utf-8", errors="ignore")

        # Use CSV sniffer to detect structure
        sniffer = csv.Sniffer()
        try:
            if sniffer.has_header(sample):
                return ("The document provided is a CSV file", file_size)
        except csv.Error:
            pass  # Not a CSV

    except Exception as e:
        print(f"Decoding or sniffing error: {e}")

    # Default to plain text
    return ("The document provided is a TXT file", file_size)
