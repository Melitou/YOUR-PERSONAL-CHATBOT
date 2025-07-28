# How to Use GridFS to Store and Retrieve Large Files

This guide provides a simple, practical example of how to use GridFS with Python and the `pymongo` library to store and retrieve large files, such as PDFs or DOCX, in your MongoDB database.

### Prerequisites

You need to have `pymongo` installed. If you don't have it, install it via pip:

```bash
pip install pymongo
```

### The Code: A Simple Example

Here is a Python script that demonstrates the two main operations:
1.  **`upload_file`**: Takes a file path and stores the file in GridFS.
2.  **`retrieve_file`**: Takes a `file_id` (the unique ID from GridFS) and saves the file back to your local disk.

```python
from pymongo import MongoClient
import gridfs

# --- 1. Connect to MongoDB ---
# Replace with your MongoDB connection string
client = MongoClient('mongodb://localhost:27017/') 
db = client['your_database_name']  # Your database name, e.g., 'chatbot_db'

# Initialize GridFS
fs = gridfs.GridFS(db)

def upload_file(file_path, file_name):
    """
    Uploads a file to MongoDB GridFS.

    Args:
        file_path (str): The local path to the file you want to upload.
        file_name (str): The name you want the file to have in the database.

    Returns:
        ObjectId: The unique ID of the stored file in GridFS.
    """
    try:
        with open(file_path, 'rb') as f:
            # The put method stores the file and returns its unique _id
            file_id = fs.put(f, filename=file_name)
            print(f"Successfully uploaded '{file_name}' to GridFS.")
            print(f"GridFS File ID: {file_id}")
            return file_id
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None

def retrieve_file(file_id, output_path):
    """
    Retrieves a file from GridFS and saves it locally.

    Args:
        file_id (ObjectId): The GridFS ID of the file to retrieve.
        output_path (str): The local path where you want to save the retrieved file.
    """
    try:
        # The get method retrieves the file object
        gridfs_file = fs.get(file_id)
        with open(output_path, 'wb') as f:
            f.write(gridfs_file.read())
        print(f"Successfully retrieved file and saved it to '{output_path}'.")
    except gridfs.errors.NoFile:
        print(f"Error: No file with ID {file_id} was found in GridFS.")

# --- 2. How to Use the Functions ---
if __name__ == '__main__':
    # --- Upload Example ---
    # Imagine you have a PDF file named 'my_manual.pdf' in the same directory
    local_file_to_upload = 'my_manual.pdf'
    
    # This is the ID you would store in your `documents` collection
    stored_file_id = upload_file(local_file_to_upload, 'manual_for_user_123.pdf')

    # --- Retrieve Example ---
    if stored_file_id:
        # Now, use the stored ID to retrieve the file
        local_file_to_save = 'retrieved_manual.pdf'
        retrieve_file(stored_file_id, local_file_to_save)
```

### How This Fits Your Plan

1.  A user uploads a PDF to your application.
2.  Your backend saves the PDF to a temporary location.
3.  You call the `upload_file()` function, passing the path to the temporary file.
4.  You take the `stored_file_id` that is returned and save it in the `gridfs_file_id` field of your `documents` collection in MongoDB.
5.  Later, when a background worker needs to process the file, it will query the `documents` collection, get the `gridfs_file_id`, and use the `retrieve_file()` logic to access the file's content. 