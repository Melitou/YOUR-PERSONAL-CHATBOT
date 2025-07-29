<h1>Step 4: Choose embeddings model</h1>
This is a UI step functionality, because the user chooses what type of embedding the Agent must use, bellow we can see the provided models for the users to decide.

|         **Model Name**          | **Provider** |            **Description**            | **User Availability (User - U & Developer - D)** |
|:-------------------------------:|:------------:|:-------------------------------------:| :----------------------------------------------: |
|             REMOVE              |    OpenAI    |              Older model              |                        D                         |
|     text-embedding-3-small      |    OpenAI    |             Smaller model             |                      U - D                       |
|     text-embedding-3-large      |    OpenAI    |          Most capable model           |                        D                         |
|      gemini-embedding-001       |    Google    |          Good for most tasks          |                      U - D                       |
|       text-embedding-005        |    Google    | Specialized in English and code tasks |                        D                         |
| text-multilingual-embedding-002 |    Google    |   Specialized in multilingual tasks   |                        D                         |'
|  multilingual-e5-large          |   Pipecone   |                   -                   |                      U - D                       |
	Note: The mode `text-embedding-005` and `text-multilingual-embedding-002` are both consolidated into `gemini-embedding-001`, as stated from Google.
Note: To view all the models of OpenAI: 

<pre>
GET https://api.openai.com/v1/models
</pre>

# Step 5: Initialize the embedding and cache them
The user has selected the required params and also created the chunks, in this part the embedding process starts.
### get_embedding_model
<pre>
get_embedding_model(model_name: str, max_fallbacks: int = 3) -> str
Params:
	model_name: The model that will be used in the process (ex. gemini-embedding-001, text-embedding-3-large etc.).
	max_fallbacks: Maximum number of fallback attempts (default: 3).

Return:
	The embedding model name for later use, or None if all attempts fail
</pre>

* How it will work:
	**Basic Overview**: It will return embedding model in string type, depending on the user's selection (from the UI), also it abstracts provider differences. Because of the abstraction, here we can handle the exception (`try/except`) if something goes wrong with the initialization of the embedding model.
* 
	**Exception handling**: We define a dict of fallback models and we "play" with each of them if one fails. This can be done with a while loop, and also we have a counter to count the numnber of times we will try to initialize the mode if it keeps failing. If the model is initialized successfully, we return the model name, else we will try to initialize the next model in the fallback list.
*
	The fallback list is:

<pre>
fallback_models = {
            "text-embedding-3-large": "text-embedding-3-small",
            "text-embedding-3-small": "text-embedding-005",
            "text-embedding-005": "text-embedding-ada-002",
            "text-embedding-ada-002": "gemini-embedding-001",
            "gemini-embedding-001": "text-multilingual-embedding-002",
            "text-multilingual-embedding-002": "text-embedding-ada-002"
}
</pre>

### create_vectors_of_chunks

<pre>
create_vectors_of_chunks(chunks: List[str], model_name: str,  max_tries: int = 3, use_fallbacks: bool = True) -> List[List[float]]

Params:
	chucks: The chucks of a document, list of text strings.
	model_name: The model that will be used to create the vectors.
	max_tries: Maximum number of attempts to create vectors (default: 3).
	use_fallbacks: Whether to use fallback models if the primary fails (default: True).

Return: 
	The corresponding vectors of the file.
</pre>

* How it will work:
	**Basic Overview**: Feeds each chunk into the embedding model and returns the corresponding vector.
* 
	**Exception Handling**: We define a variable number, called max_tries, and we count the number of times the function failed to complete with success. If the function totally fails (3 out of 3) then the function will **return an empty List**. The caller must handle it appropriately: Maybe skipping the particular chunk file or cancel the whole execution.
* Also, like in the previous function, we define the same dict of fallback models, and we try each of them if the preferred fails.

### create_chunk_hash

<pre>
create_chunk_hash(chunks: List[str]) -> Optional[str]

Params:
	chunks: List of chunks strings

Return:
	The created hash for the particular file chunk.
</pre>

* How it will work:
	**Basic Overview**: Takes a file chunk and create the corresponding hash, using `SHA256`.
* 
	**Exception Handing**: If an error occurred (`try/except`) return None, caller must handle the next steps accordingly. 
if None returned, that means the creation or the storing of the hash failed.

### store_chunk_hash

<pre>
store_chunk_hash(hash_value: str, db_path: str, max_tries: int = 3, retry_delay: float = 1.0) -> Optional[str]

Params:
	hash_value: str the hash to store
	db_path: str the path to the database file (default: "hash_db.json")
	max_tries: int maximum number of retry attempts (default: 3)
	retry_delay: float delay in seconds between retries (default: 1.0)
Return:
	The created hash for the particular file chunk.
</pre>

* How it will work:
	**Basic Overview**: Takes a hash value and stores it in a local database (like TinyDB, SQLite, etc.).
*
	**Exception Handing**: The function will retry storing the hash if it fails, up to a maximum number of attempts (`max_tries`).

### check_embedding_cache

<pre>
check_embedding_hash_cache(create_hash: str) -> bool

Params:
	create_hash: The hash of the chunks of a file

Return:
	Boolean value, if True the high already exists else (False) the hash does not exists.
</pre>

* How it will work:
	**Basic Overview**: Takes the newly generate hash of a chunk of file data and iterates through the Hash DB to see if the hash is already created. The database can be TinyDB, Redis, Supabase or whatever.
* 
	**Exception Handling**: If the function (`try/except`) fails, return False, so the caller can proceed with the creation and storing of the embeddings. This approach is better than returning True because if the process fails and we return True then the system will think that the Vector DB already has the vector of the particular file and proceed with the next steps, but when we reach the final steps and the agent is created there is a possibility that the Vector of that file **never existed** and that would be catastrophic. So it is better to return False, in order for the system to create and store  the embeddings even if we result in duplicate vector data. That way, we ensure the service will work for the user. Later we can write a procedure to check for any duplicate vectors in the Vector DB.

# 6. Store the chunks in a vector store
In this part the embeddings have been created with success and we procced with the storing of each of them in the Vector DB.

<pre>
	fallback_chains = {
            "gpt-4o": ["gpt-4-turbo-preview", "gpt-3.5-turbo-0125"],
            "gpt-4-turbo-preview": ["gpt-3.5-turbo-0125", "text-davinci-003"],
            "gpt-4o-mini": ["gpt-3.5-turbo-0125"],
            "gemini-1.5-pro": ["gemini-1.0-pro", "text-bison-001"],
        }
</pre>

### store_vector_in_db

<pre>
store_vector_in_db(preferred_db: str, hash: str, summary: str, vector_list: ...) -> bool

Params:
	preferred_db: str the DB to store the vector in
	hash: str the hash of the chunks
	summary: str the summary of the chunks
	vector_list: List[List[float]] the vector of the chunks
Return:
	True if everything works correct or False if not
</pre>

* How it works:
	**Basic Overview**: This function, based on the user preferred DB (local or cloud) will run the necessary procedures to store the data. Note that this function can also be split into multiple functions for each storing process each DB provider has (ex. one for Pipecone, one for ChromaDB etc.).
* 
	**Exception Handling**: If the procedure fails when storing in a local DB we can keep trying with other types of local DB's. If the procedure fails when storing to cloud (Pipecone) we can store the data locally (ex. ChromaDB) and create a queue of failed storing attempts  to run them again after a period of time, using for example a timer (ex. after 1 min). 

*Bellow you can see the logic-flow between the above functions in pseudocode*

<pre>
# model_name is defined from the frontend (str)
emb_model = get_embedding_model(model_name)

# FilesInfo is returned from the previous steps 
## (List[Tuple[str, List[str],str]]) a list of Tuples with the name of the file, ## the chunks and the file text contents
For each name, chunk, contents in FilesInfo:
	hash = create_chunk_hash(chunk)
	if hash and (check_embedding_cache(hash) is False):
		vector_list = create_vectors_of_chunks(chunk, emb_model)
		
		if vectors_list is not empty:
			summary = generate_summary(contents)
			success = store_vector_in_db(preferred_db, summary, vector_list)
			if success is True:
				return SuccessResponse
			else
				return FailResponse
		else
			...handle error...
</pre>
