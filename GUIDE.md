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
    (i) For PDF files we will use llama parse cloud. If llama parse cloud fails then we will use the PDFReader function from pypdf library 
    (ii) For DOCX files we will use llama parse cloud. If llama parse cloud fails then we will use the Document function from docx library
    (iii) For CSV files we will use llama parse cloud. If llama parse cloud fails then we will use the reader function from csv library
    (iv) For TXT files we will use llama parse cloud. If llama parse cloud fails then we will open the file and use the read function
## d. We chunk the texts 
    (i) Preferred method: Fixed token chunking [There are two input parameters: 1. Token count and 2. Overlap count].
        The output will be chunks that have the same number of tokens.
    (ii) Semantic chunking [There is one input parameter: Embeddings model]. this method splits the text into sentences,
        embeds them and groups them based on their embedding similarity. 
        The output will be chunks that have the maximum embedding similarity within. 
    (iii) Fixed line chunking [There are two input parameters: 1. Line count and 2. Overlap count].
        The output will be chunks that have the same number of lines.
    (iv) Recursive chunking [There are two input parameters: 1. Chunk size and 2. Chunk overlap].
        The output will be chunks that have the same size.
## e. Choose embeddings model
    (i) Gemini: - Newest: gemini-embedding-001

                - For multilingual purposes: text-multilingual-embedding-002

    (ii) OpenAI: - text-embedding-3-large: Higher accuracy on complex queries and long-form content analysis

                 - text-embedding-3-small: Faster and has lower costs.  Suitable for everyday use.
## f. Initialize the embeddings and cache them
## g. Store the chunks in a vector store
    To increase the accuracy of the vector store's retrieval proccess based on the user's query, we will add into the vector store the chunks' summary. In particular:
        - We will create an agent which will be an expert at summarizing
        - It will take as input the whole document and the each of the chunks
        - The output will be a summary of the chunks based on the whole document

    Then the user will choose how to store them:
    (i) Store them globally: - Pinecone

    (ii) Store them locally: - ChromaDB
                             - FAISS

    If the user wants to store them to Pinecone:
    - First, we intialize the client
    - We create or connect to an index
    - We embed and upsert vectors
    - Search for the right index based on the user's query
    *  There are 3 ways of searching: 1. Semantic [similar meaning or context to the query]
    *                                 2. Lexical [matching words or phrases of the query]
    *                                 3. Hybrid [a combination of Semantic and Lexical]
    - Extract the text
    - Insert it into the LLM

    If the user wants to store them on ChromaDB or FAISS:
    - We will intialize the client
    - We will create a collection
    - We add the embeddings 
    - We make the vector store persistent
    - We make a function for searching the vector store
        * It takes as input 1. The user's query and 2. The number of the documents that it will retrieve.
        * It will search the vector store based on the similarity
        * The output will be the retrieved documents 
        **If the function is unable to retrieve the documents, we will desplay an error**
    - Extract the text
    - Insert it into the LLM


# 3. Chat History 

## Add memory to the agent

    We will create two functions:
    (i) Load the previous chat history
    (ii) Save the current chat history


# 2. LLM

## GEMINI 
    (i) We create a client from google.genai
    (ii) We create a tool for google search 
    (iii) We create a function for RAG
    (iv) We insert the functions into the google client through config parameter
    (v) We add the chat history through the contents parameter
    (vi) We generate the answer

## OpenAI 
    (i) We create the OpenAI model 
    (ii) We use the responses API function to generate a response
    (iii) We add web_search_preview into the tools parameter 
    (iv) We create a function for RAG 
    (v) We insert the function into the tools parameter 
    (vi) We generate the answer
