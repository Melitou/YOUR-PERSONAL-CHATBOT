# YOUR-PERSONAL-CHATBOT

YOUR-PERSONAL-CHATBOT is an AI-powered chatbot that helps users search their own documentation using natural language. This project provides a complete pipeline for processing documents, creating embeddings, and interacting with a RAG-based chatbot.

## Features

- **Document Processing:** Upload and process documents from a local directory.
- **Supported File Types:** PDF, DOCX, TXT, and CSV.
- **Chunking Methods:** Choose from various chunking strategies:
    - `token`: Splits text by token count.
    - `line`: Splits text by line count.
    - `recursive`: Splits text recursively by characters.
- **Embedding Models:**
    - **OpenAI:** `text-embedding-3-small`
    - **Gemini:** `gemini-embedding-001`
- **Chatbot Models:**
    - **OpenAI:** `gpt-4.1`, `gpt-4o`, `gpt-4o-mini`, `gpt-o3`
    - **Gemini:** `gemini-2.5-pro`, `gemini-2.5-flash`, and more.
- **Vector Database:** Uses Pinecone for efficient vector storage and retrieval.
- **Database:** MongoDB with GridFS for file storage.
- **CLI Interface:** An interactive command-line interface to manage the entire workflow.

## How It Works

The project follows a master pipeline that orchestrates the entire workflow from document processing to chatbot interaction.

<p align="center">
  <img src="Mermaid_graph.png" width="400" alt="RAG Flowchart">
</p>




## Getting Started

### Prerequisites

- Python 3.8 or higher
- Pip for package management
- Access to a MongoDB database
- API keys for OpenAI, Gemini, and Pinecone

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Melitou/YOUR-PERSONAL-CHATBOT.git
    cd YOUR-PERSONAL-CHATBOT
    ```

2.  **Create a virtual environment and activate it:**
    ```bash
    python -m venv .venv
    # On Windows
    .venv\Scripts\activate
    # On macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The main entry point for the application is `master_pipeline.py`. You can run it directly from the command line.

```bash
python master_pipeline.py
```

The script will guide you through the following steps:

1.  **Enter the folder path containing your documents.**
2.  **Enter a namespace** for your chatbot (e.g., `my_project_docs`).
3.  **Select an embedding provider** (OpenAI or Gemini).
4.  **Select a chatbot model.**
5.  **Select a chunking strategy.**

The pipeline will then process your documents, create embeddings, and start an interactive chat session.

### Example

```
$ python master_pipeline.py
================================================================================
🚀 COMPLETE RAG CHATBOT PIPELINE
================================================================================
Complete workflow: Documents → Processing → Embeddings → Chat
• 📤 Upload and process your documents
• 🧠 Create embeddings and store in vector database
• 🤖 Start chatting with your personal document assistant
================================================================================

📁 Enter folder path containing documents: /path/to/your/documents
✅ Found 5 supported files in /path/to/your/documents
🏷️  Enter namespace (e.g., 'my_documents', 'company_data'): project_docs
✅ Namespace 'project_docs' is valid.

🤖 Select embedding provider:
1. OpenAI (text-embedding-3-small)
2. Gemini (gemini-embedding-001)
Choose provider (1 or 2): 1
✅ Selected: OpenAI

... and so on.
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

1.  Fork the repository
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request
