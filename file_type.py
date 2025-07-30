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


# add mb size
