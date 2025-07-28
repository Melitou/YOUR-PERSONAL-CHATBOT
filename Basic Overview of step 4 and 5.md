<h1>Step 4: Choose embeddings model</h1>
This is a UI step functionality, because the user chooses what type of embedding the Agent must use, bellow we can see the provided models for the users to decide.

|         **Model Name**          | **Provider** |            **Description**            | **User Availability (User - U & Developer - D)** |
| :-----------------------------: | :----------: | :-----------------------------------: | :----------------------------------------------: |
|     text-embedding-ada-002      |    OpenAI    |              Older model              |                        D                         |
|     text-embedding-ada-002      |    OpenAI    |             Smaller model             |                      U - D                       |
|     text-embedding-3-large      |    OpenAI    |          Most capable model           |                        D                         |
|      gemini-embedding-001       |    Google    |          Good for most tasks          |                      U - D                       |
|       text-embedding-005        |    Google    | Specialized in English and code tasks |                        D                         |
| text-multilingual-embedding-002 |    Google    |   Specialized in multilingual tasks   |                        D                         |
	Note: The mode `text-embedding-005` and `text-multilingual-embedding-002` are both consolidated into `gemini-embedding-001`, as stated from Google.
	
Note: To view all the models of OpenAI: 

~~~
GET https://api.openai.com/v1/models
~~~

<h1>Step 5: Initialize the embedding and cache them</h1>
The user has selected the required params and also loaded the documents, in this part the embedding process starts.
<h3>get_embedding_model</h3>
~~~~
get_embedding_model(model_name: str)

Params:
	model_name: The model that will be used in the procces (ex. gemini-embedding-001, text-embedding-3-large etc.).

Return:
	EmbModel A callable function (or client object) that embeds input text.

Usage example:
	embed_fn = get_embedding_model("text-embedding-3-large")
~~~~

* How it will work:
	**Basic Overview**: It will return the appropriate embedding object depending on the user's selection (from the UI), also it abstracts provider differences. Because of the abstraction, here we can handle the exception (`try/except`) if something goes wrong with the initialization of the embedding model.
	
	**Exception handling**: We define a dict of fallback models and we "play" with each of them if one fails. This can be done with a while loop that we try at first the model the user requested and if it fails we use some other model.
	**If all models failed: Then raise an exception, cancel the whole operation and inform the user in the UI with an appropriate message, such as "Agent creation failed, cannot instantiated the embedding model, please try again."**

	The fallback list is:
```
		fallback_models = {
        "text-embedding-3-large": "text-embedding-005",
        "text-embedding-005": "text-embedding-ada-002",
        "text-embedding-ada-002": "gemini-embedding-001",
        "gemini-embedding-001": "text-multilingual-embedding-002",
        "text-multilingual-embedding-002": "text-embedding-ada-002"
    }
```

<h3>create_vectors_of_chunks</h3>

```
create_vectors_of_chunks(chunks: List[str], emb_mode: Callable, max_retries=3) -> List[List[float]]

Params:
	chucks: The chucks of a document, list of text strings.
	emb_mode: Callabale object, the embedding model the user choose.
	max_retries: How many time the system will try to handle an exception, default value 3.

Return: 
	The corresponding vectors of the file.
```

* How it will work:
	**Basic Overview**: Feeds each chunk into the embedding model and returns the corresponding vector.
	
	**Exception Handling**: We define a variable number, called max_tries and we count the number of times the function failed to complete with success. If the function totally fails (3 out of 3) then the function will

**return an empty List**. The caller must handle it appropriately: Maybe skipping the particular chunk file or cancel the whole execution.

<h3>create_chunk_hash</h3>

```
create_chunk_hash(chunks: List[str]) -> Optional[str]

Params:
	chunks: List of text strings

Return:
	The created hash for the particular file chunk.
```

* How it will work:
	**Basic Overview**: Takes a file chunk and create the corresponding hash, using `SHA256`.
	**Exception Handing**: If an error occurred (`try/except`) return None, caller must handle the next steps accordingly.
	
<h3>check_embedding_cache</h3>

```
check_embedding_hash_cache(create_hash: str) -> bool

Params:
	create_hash: The hash of the chunks of a file

Return:
	Boolean value, if True the hagh already exists else (False) the hash does not exists.
```

* How it will work:
	**Basic Overview**: Takes the newly generate hash of a chunk of file data and iterates through the Hash DB to see if the hash is already created. The database can be TinyDB, Redis, Supabase or whatever.
	**Exception Handling**: If the function (`try/except`) fails, return False, so the caller can procced with the creation and storing of the embeddings. This approach is better than returning True because if the process fails and we return True then the system will think that the Vector DB already has the vector of the particular file and procced with the next steps, but when we reach the final steps and the agent is created there is a possibility that the Vector of that file **never existed** and that would be catastrophic. So it is better to return False, in order for the system to create and store  the embeddings even if we result in duplicate vector data. That way, we ensure the service will work for the user. Later we can write a procedure to check for any duplicate vectors in the Vector DB.

<h1>6. Store the chunks in a vector store</h1>

In this part the embeddings have been created with success and we procced with the storing of each of them in the Vector DB.

<h3>generate_summary</h3>

```
generate_summary(contents: str, summary_model: "gpt-4o", max_fallbacks=3) -> str

Params:
	chunks: A list with chunks of a document.
	summary_model: The model the system will use to create the summary
Return:
	The summary itself in string format.
```

* How it works:
	**Basic Overview**: It will use a model that is good at summarizing and it will create a summary based on the contents of the file (not the chunks).
	
	**Exception Handling**: We define a dict of fallback models and we "play" with each of them if one fails. In this function the idea is to is to **automatically switch to a backup model** if the primary model fails.

Note that here we fallback to cheaper models.

```
	fallback_chains = {
        "gpt-4o": ["gpt-4-turbo-preview", "gpt-3.5-turbo-0125"],
        "gpt-4-turbo-preview": ["gpt-3.5-turbo-0125", "text-davinci-003"],
        "gemini-1.5-pro": ["gemini-1.0-pro", "text-bison-001"],
    }
```

<h3>store_vector_in_db</h3>

```
store_vector_in_db(prefered_db: str, summary: str, vector_list: ...) -> bool

Params:
	prefered_db: Possble values {'Pipecone', 'ChromaDB', 'FAISS'}
	summary: The summary of the document
	vector_list: The vector that the system will store in the prefered DB\
Return:
	True if everything works correct or False if not
```

* How it works:
	**Basic Overview**: This function, based on the user preferred DB (local or cloud) will run the necessary procedures to store the data. Note that this function can also be split into multiple functions for each storing process each DB provider has (ex. one for Pipecone, one for ChromaDB etc.).
	
	**Exception Handling**: If the procedure fails when storing in a local DB we can keep trying with other types of local DB's. If the procedure fails when storing to cloud (Pipecone) we can store the data locally (ex. ChromaDB) and create a queue of failed storing attempts  to run them again after a period of time, using for example a timer (ex. after 1 min). 

*Bellow you can see the logic-flow between the above functions in pseudocode*

```
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
			success = store_vector_in_db(prefered_db, summary, vector_list)
			if success is True:
				return SuccessResponse
			else
				return FailResponse
		else
			...handle error...
```
