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
    (i) For PDF files we will use llama parse cloud. If llama parse cloud fails then we will use the PDFReader from pypdf library 
    (iv) For DOCX files we will use llama parse cloud. If llama parse cloud fails then we will use Document from docx library
## d. We chunk the texts 
    (i) Fixed token chunking [There are two input parameters: 1. Token count and 2. Overlap count] 
    (ii) Semantic chunking [Tere is one input parameter: Embeddings model]
    (iii) Fixed line chunking [There are two input parameters: 1. Line count and 2. Overlap count]
    (iv) Recursive chunking [There are two input parameters: 1. Chunk size and 2. Chunk overlap]
## e. Choose embeddings model
    (i) Gemini: - Newest: gemini-embedding-001
                - For multilingual purposes: text-multilingual-embedding-002

    (ii) OpenAI: - Newest: text-embedding-3-large, text-embedding-3-small
## f. Initialize the embeddings and cache them
## g. Store the chunks in a vector store
    (i) Store them globally: - Pinecone

    (ii) Store them locally: - ChromaDB
                             - FAISS


#### function to search the right oinecone index


# 3. Chat History 

## Add memory to the agent

We will create two functions:
(a) Load the previous chat history
(b) Save the current chat history


# 2. LLM

### GEMINI ###  
(a) We create a client from google.genai
(b) We create a tool for google search 
(c) We create a function for RAG
(d) We insert the functions into the google client through config parameter
(e) We add the chat history through the contents parameter
(f) We generate the answer

### OpenAI ###
(a) We create the OpenAI model 
(b) We use the responses API function to generate a response
(c) We add web_search_preview into the tools parameter 
(d) We create a function for RAG 
(e) We insert the function into the tools parameter 
(f) We generate the answer


Tell the agent to save the mermaid file