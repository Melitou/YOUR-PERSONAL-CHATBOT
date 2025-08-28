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
- **Structured Responses:** AI responses are formatted with markdown for better readability (headers, lists, code blocks, etc.)
- **CLI Interface:** An interactive command-line interface to manage the entire workflow.

## How It Works

The project follows a master pipeline that orchestrates the entire workflow from document processing to chatbot interaction.

<p align="center">
  <img src="Detailed Technical Flow.png" width="1100" alt="RAG Flowchart">
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
Before we start we should download MongoDB locally from https://www.mongodb.com/try/download/community. You choose your version (we recommend 8.0.13 or higher) and platform. When the installation is complete we continue.

The main entry point for the application is `main.py`. You can run it directly from the command line.

```bash
cd backend
python main.py
```

Now we open another terminal and run the code shown below so that we can initialize the front end:
```bash
cd front_end
npm install  
npm run dev
```
When the app is ready you will be able to sign up as a user.

As a user you will have the following options:
- Create a chatbot
- Load a chatbot
- Delete a chatbot
- Asssign a chatbot to clients by email 
- Edit and delete conversations


As a client you will have the option to:
- Select the chatbot you want to use (if more than one are assigned to you)
- Edit and delete conversations

After logging in you should create a conversation and that is it! Now you can chat with the chatbot and show the thinking proccess!


## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
