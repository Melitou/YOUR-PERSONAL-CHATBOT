import csv
import tempfile
from file_type import doc_type_check

file_bytes = open(
    "./Files/ObesityDataSet_raw_and_data_sinthetic.csv", "rb").read()


def csv_to_md(file_bytes: bytes, delimiter: str = ",") -> str:
    """
    Extract entire CSV as markdown using csv text extraction.

    This function parses the complete CSV document into markdown format,
    preserving structure like headers, tables, lists, and references.

    Args:
        file_bytes: bytes

        delimiter: str = ","

    Returns:
        str: markdown_content
    """
    markdown_content = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_file.flush()

        with open(tmp_file.name, newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            for row in reader:
                markdown_content += "| " + " | ".join(row) + " |\n"
        return markdown_content
    except Exception as e:
        print(f"Error with csv extraction: {e}")
        return None


type_doc = doc_type_check(file_bytes)
print(type_doc)

if type_doc == "The document provided is a CSV file":
    md = csv_to_md(file_bytes)
    print(md[:100])
else:
    print("Unsupported document type for this script.")
