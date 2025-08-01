"""
Python code extracted from rag_pdf.ipynb
Generated by Project Publisher

Original notebook: 18 cells
Code cells: 18
"""

# Imports
from google.colab import userdata
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders.pdf import PyPDFDirectoryLoader
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone,ServerlessSpec
import os

# Main code
!pip install -qqq tiktoken
!pip install -qqq pinecone-client
!pip install -qqq pypdf
!pip install -qqq openai
!pip install -qU langchain-openai
OPENAI_API_KEY=userdata.get('openai-key')
PINECONE_API_KEY=userdata.get('pinecone-key')
!pip install -qqq langchain_community
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
os.environ['PINECONE_API_KEY'] = PINECONE_API_KEY
#reads each document page by page. total length of documents variable
#is sum of all page counts
def read_doc(directory: str) -> list[str]:
    #Function to read the PDFs from a directory.
    #Args:
        #directory (str): The path of the directory where the PDFs are stored.
    #Returns:
        #list[str]: A list of text in the PDFs.
    # Initialize a PyPDFDirectoryLoader object with the given directory
    file_loader = PyPDFDirectoryLoader(directory)
    # Load PDF documents from the directory
    documents = file_loader.load_and_split()
    # Extract only the page content from each document
    page_contents = [doc.page_content for doc in documents]
    return page_contents
# Call the function
full_document = read_doc("/content")
print(len(full_document))
embed_model = OpenAIEmbeddings(model="text-embedding-3-large")
def generate_embeddings(documents: list[any]) -> list[list[float]]:
    #Generate embeddings for a list of documents.
    #Args:
        #documents (list[any]): A list of document objects, each containing a 'page_content' attribute.
    #Returns:
        #list[list[float]]: A list containig a list of embeddings corresponding to the documents.
    embedded = [embed_model.embed_documents(doc) for doc in documents]
    return embedded
# Run the function
chunked_document_embeddings = generate_embeddings(documents=full_document)
# Let's see the dimension of our embedding model so we can set it up later in pinecone
print(len(chunked_document_embeddings))
# create unique IDs
ids = [str(x) for x in range(0,len(chunked_document_embeddings))]
def combine_vector_and_text(
    documents: list[any], doc_embeddings: list[list[float]]) -> list[dict[str, any]]:
    """
    Process a list of documents along with their embeddings.
    Args:
    - documents (List[Any]): A list of documents (strings or other types).
    - doc_embeddings (List[List[float]]): A list of embeddings corresponding to the documents.
    Returns:
    - data_with_metadata (List[Dict[str, Any]]): A list of dictionaries, each containing an ID, embedding values, and metadata.
    """
    data_with_metadata = []
    for id,doc_text, embedding in zip(ids,documents, doc_embeddings):
        # Convert doc_text to string if it's not already a string
        if not isinstance(doc_text, str):
            doc_text = str(doc_text)
        # Generate a unique ID based on the text content
        doc_id = id
        # Create a data item dictionary
        data_item = {
            "id": doc_id,
            "values": embedding[0],
            "metadata": {"text": doc_text},  # Include the text as metadata
        }
        # Append the data item to the list
        data_with_metadata.append(data_item)
    return data_with_metadata
# Call the function
all_meta_data = combine_vector_and_text(full_document, chunked_document_embeddings)
# Verify that all_meta_data is not empty
print(len(all_meta_data))
print(all_meta_data[0]) # Inspect the first item
pinecone = Pinecone()
INDEX_NAME="rag-pdf"
if INDEX_NAME in [index.name for index in pinecone.list_indexes()]:
  pinecone.delete_index(INDEX_NAME)
pinecone.create_index(name=INDEX_NAME, dimension=3072, metric='cosine',
  spec=ServerlessSpec(cloud='aws', region='us-east-1'))
index = pinecone.Index(INDEX_NAME)
print(index)
index.upsert(all_meta_data)
query_embeddings = embed_model.embed_query("what are some health benefits of youth sports?")
# query_embeddings
def query_pinecone_index(
    query_embeddings: list, top_k=3, include_metadata: bool = True
) -> dict[str, any]:
    """
    Query a Pinecone index.
    Args:
    - index (Any): The Pinecone index object to query.
    - vectors (List[List[float]]): List of query vectors.
    - top_k (int): Number of nearest neighbors to retrieve (default: 2).
    - include_metadata (bool): Whether to include metadata in the query response (default: True).
    Returns:
    - query_response (Dict[str, Any]): Query response containing nearest neighbors.
    """
    query_response = index.query(
        vector=query_embeddings, top_k=3, include_metadata=True
    )
    return query_response
# Call the function
answers = query_pinecone_index(query_embeddings=query_embeddings)
print(answers)
LLM = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
# Extract only the text from the dictionary before passing it to the LLM
text_answer = " ".join([doc['metadata']['text'] for doc in answers['matches']])
prompt = f"{text_answer} Using the provided information, give me a summarized answer"
def query_response(prompt: str) -> str:
    """This function returns a better response using LLM
    Args:
        prompt (str): The prompt template
    Returns:
        str: The actual response returned by the LLM
    """
    answer = LLM.invoke(prompt)
    return answer.content
# Call the function
final_answer = query_response(prompt=prompt)
print(final_answer)

if __name__ == "__main__":
    # Run the main functionality
    print("Notebook code extracted successfully")