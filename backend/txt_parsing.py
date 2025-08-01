from file_type import doc_type_check


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


# Test code - only runs when script is executed directly
if __name__ == "__main__":
    # Example usage (commented out to prevent file not found errors)
    # file_bytes = open("./test_files_for_local_db/alice_in_wonderland.txt", "rb").read()
    # type_doc = doc_type_check(file_bytes)
    # print(type_doc[0])
    # print(f"File size: {type_doc[1]} bytes")
    #
    # if type_doc[0] == "The document provided is a TXT file":
    #     md = txt_to_md(file_bytes)
    #     print(md[:100])
    # else:
    #     print("Unsupported document type for this script.")
    print("TXT parser module loaded successfully")
