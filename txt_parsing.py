from file_type import doc_type_check

file_bytes = open("./Files/Σ21066.ΜΠΙΤΟΥ.txt", "rb").read()


def txt_to_md(file_bytes: bytes) -> str:
    """
    Extract entire TXT as markdown using text extraction.

    This function parses the complete TXT document into markdown format,
    preserving structure like headers, tables, lists, and references.

    Args:
        file_bytes: bytes

    Returns:
        str: markdown_content
    """
    markdown_content = ""
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
        markdown_content = f"```\n{text}\n```"
    except Exception as e:
        print(f"Error reading TXT: {e}")
        markdown_content = ""
    return markdown_content


type_doc = doc_type_check(file_bytes)
print(type_doc)

if type_doc == "The document provided is a TXT file":
    md = txt_to_md(file_bytes)
    print(md[:100])
else:
    print("Unsupported document type for this script.")
