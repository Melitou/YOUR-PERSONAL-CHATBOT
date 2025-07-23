### Project: Personal Chatbot ###

### Starting Plan Backend


###### RAG SYSTEM ######

# 1. Loading the documents 📑

## a. User uploads the docs 📥
## b. For starters, we have 4 types of documents:
    (i) PDF files
    (ii) DOCX files
    (iii) CSV files
    (iv) TXT files
## c. We convert the docs to text
    (i) We can use the PDFReader from pypdf library 
    (ii) We can use the extract_raw_text function from mammoth library
    (iii) We can use the open and read functions 
    (iv) llama parse cloud
## d. We chunk the texts 
    (i) First we will use Recursive chunking 
    (ii) For more complex documents like medical articles we can use sliding window chunking
## e. Choose embeddings model
    (i) Gemini: - Newest: gemini-embedding-001
                - For multilingual purposes: text-multilingual-embedding-002

    (ii) OpenAI: - Newest: text-embedding-3-large, text-embedding-3-small

## f. Initialize the embeddings and cache them
## g. Store the chunks in a vector store
    (i) Store them globally: - Pinecone

    (ii) Store them locally: - ChromaDB
                             - FAISS



# 2. LLM

### GEMINI ###  
(a) We create a client from google.genai
(b) We create a tool for google search 
(c) 

### OpenAI ###
(a) We create the OpenAI model 
(b) We use the responses API function to generate a response
(c) We add the embedded documents into the input parameter 