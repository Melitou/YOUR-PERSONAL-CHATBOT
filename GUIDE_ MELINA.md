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
    (i) For PDF files we will use llama parse
    We will create a function that extracts text from uploaded pdf file that has one parameter: The pdf bytes: bytes. In this function:
    - We will create a variable named tmp_file that stores the uploaded document. To do that:
        - we will use the tempfile.NamedTemporaryFile() function from the tempfile library to create a temporary file path and store it to the temp_file object 
        - Into the variable we should make sure that the suffix parameter is se to .pdf, this will inform the object that the file ia a pdf, then
        - we will use the temp_file.write function to pass the content of the pdf document to the temp_file object and lastly
        - we will use the temo_file.flush function to enure that all bytes are written
    - We will initialize Llama parse and store it into a variable called parser
    - We will load the file into the parser using the parser.load_data function that takes as input the tmp_file.name and store it into a variable called docs
    - This variable is a llama_index.core.schema.Document so to get the text we will join the text of all the docs in the docs variable and store it into a variable called full text.
    
    - If llama parse fails then we will raise an error to let the user know and we will be trying fallbacks. For our fallback for pdfs will be using the pypdf.PDFReader function from pypdf library
    - First, we will read the pdf file using the PdfReader class that takes as input the temporary file path and store it in a variable called reader
    - To get the extracted text we will use a for loop. For every page in reader we will use the extracted_text() function and we will join the results in a variable named full_text
    
    The output will be a string that contains the full text of the document
    
    (ii) For DOCX files we will use llama parse cloud
    -- Consider not using llama parse
    - The llama parse proccess for docx files is exactly the same as the proccess llama parse proccess for pdf files. The only thing we should to change is suffix parameter in the tempfile.NamedTemporaryFile() function to .docx.
    - If llama parse fails then we will use the docx.Document from docx library
    - In particular, we will load the file through the Document class passing the temporary file path as input and store it into a variable called doc
    - With the doc.paragraph list we extract the text of each paragraph, so using a for loop we will append it to a variable called full_text
    
    The output will be a string that contains the full text of the document

    (iii) For CSV files we will use llama parse cloud. If llama parse cloud fails then we will use the csv.reader function from csv library for the parsing

    We will create a function that extracts text from uploaded csv files that has two input parameters: 1. csv_bytes: bytes and 2. demileter: str ",". In this function:
    - We will convert the bytes to a text stream so the csv.reader funtion can work and store them in a variable called text_stream
    - We will use the csv.reader function that takes as input two parameters: 1. text_stream and 2. delimiter and store it into a variable called reader 
    - For every row in reader we will join them into a one comma seperated string and store the result into a variable called lines
    - Finally, we will join the lines and store them into a variable called full text

    The output will be a string that contains the full text of the document

    (iv) For TXT files we do not need to extract text as it is already in text form
## d. We chunk the texts 
    (i) Preferred method: Fixed token chunking 
        We will make a function called token_chunk that has four input parameters: 1. Full text 2. Token count, 3. Overlap count and 4. Encoding name or Model name. Some of the paramaters will be already set to 2. token_count: int 7000, 3. overlap: int 300 and 4. encoding_name: str "cl100k_base"
        In the function:
        - If the overlap is equal or greater than the token count then we will raise a value error and inform the user that the overlap must be smaller than token count
        - In this function we will first encode the whole document 
        - We will store the length of the encoding text in a variable called total_tokens
        - We will create a for loop that will split the encoded document into smaller parts, the range of the loop will be from 0 to total_tokens with a step of token_count - overlap
        - Into the loop the encoded chunks will be from i to i + token_count of the encoded document
        - Then these chunks will be decoded into text so they can be comprehended by the user
        - Lastly, the decoded chunks will be appended into a list called chunks 
        The output will be a list of chunks
    (ii) Semantic chunking 
        We will make a function called semantic_chunk that has two input parameters: 1. Full text and 2. Embeddings model. The Embeddings model parameter will be already initialiazed to: "OpenAIEmbeddings"
### breakpoint_threshold_type
        In the function:
        - We will use the class SemanticChunker from the langchain_experimental.text_splitter library that takes as input the embeddings model
        - To split the document we will use the method create_documents of the SemanticChunker class and store it into a variable named docs
        - The docs variable is now a list of langchain Documents so to trasfmorm it into the text chunks we want we will use a for loop to get the content into a new variable called chunks
        The output will be a list of chunks
    (iii) Fixed line chunking
        We will create a function called line_chunk that has three input parameters: 1. Full text, 2. Line count and 3. Overlap count
        In the function:
        - We will split the document into lines using the document.splitlines() function and store them into a variable called lines
        - We will create a variable called total_lines which will indicate the total lines of the document, those will be counted using the len(lines) function
        - We will create a variable called step which will be the difference line_count - overlap. If this variable is equal or less than 0 then we will raise an error and let the user know that the overlap must be less than the line_count
        - We will create a for loop that will get the chunks, the range of the loop will be from 0 to total_lines with a step of step
        - Into the loop the chunks will be from i to i + line_count of the lines variable
        - Lastly, we will append each chunk into a list called chunks.
        The output will be a list of chunks
    (iv) Recursive chunking
        We will create a function called recursive_chunk that has three input variables: 1. Full text, 2. Chunk size and 3. Chunk overlap
        In the function:
        - We will use the class RecursiveCharacterTextSplitter from the langchain_text_splitters library, that takes as input the Chunk size and Chunk overlap parameters
        - To split the document we will use the method create_documents of the RecursiveCharacterTextSplitter class and store it into a variable named texts
        - The texts variable is now a list of langchain Documents so to trasfmorm it into the text chunks we want we will use a for loop to get the content into a new variable called chunks
        The output will be a list of chunks
## e. Choose embeddings model
    (i) Gemini: - Newest: gemini-embedding-001

                - For multilingual purposes: text-multilingual-embedding-002

    (ii) OpenAI: - text-embedding-3-large: Higher accuracy on complex queries and long-form content analysis

                 - text-embedding-3-small: Faster and has lower costs.  Suitable for everyday use.
## f. Initialize the embeddings and cache them
## g. Create a summary function
    To increase the accuracy of the vector store's retrieval proccess based on the user's query, we will add into the vector store the chunks' summary. 
    It will take as input: 1. The content of the document and 2. The content of the chunk.
    In particular:
        - First, we will create a client which will be an expert at summarizing
        - We will create two different prompts. One for the whole document which will just include the content of the document and one for the chunk which will include the content of the certain chunk and some additional information that can help the agent understand, like: "Given this chunk context and it's location within the overall document, give me a summary"
        - If we use Gemini as our client then we will generate the summary using client.models.generate content()
            - In the contents parameter we will insert the two prompts referred above as dictionaries with two keys: role and content. The first dictionary will have user as the role and the document's content as the content. The second dictionary will have user as the role and the chunk's content as the content. 
        - If we use OpenAI as our client then we will generate the summary using client.responses.create()
            - In the input parameter we will insert the two prompts referred above as dictionaries with two keys: role and content. The first dictionary will have user as the role and the document's content as the content. The second dictionary will have user as the role and the chunk's content as the content. 
        - The output will be a summary of the chunks based on the whole document
## h. Store the chunks in a vector store
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
