import chromadb
import argparse
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from pprint import pprint
from app.config.settings import settings


def get_vectorstore():
    """Initializes and returns the Chroma vector store client."""
    embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
    client = chromadb.HttpClient(host=settings.CHROMADB_HOST, port=settings.CHROMADB_PORT)
    vectorstore = Chroma(
        client=client,
        collection_name="adr_collection",
        embedding_function=embeddings,
    )
    return vectorstore


def main():
    parser = argparse.ArgumentParser(
        description="Query your ChromaDB collections from the terminal."
    )
    parser.add_argument(
        "collection_name",
        type=str,
        help="The name of the collection to query (e.g., 'adr_collection').",
    )
    parser.add_argument(
        "--query", "-q", type=str, help="A text query for a semantic search."
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=5,
        help="Limit the number of results to display.",
    )

    args = parser.parse_args()

    try:
        vectorstore = get_vectorstore()
        count = vectorstore._collection.count()
        print(f"Total documents in '{args.collection_name}': {count}")

        if args.query:
            print(f"\n--- Running semantic search for query: '{args.query}' ---")
            results = vectorstore.similarity_search_with_score(args.query, k=args.limit)

            # Format and print the results
            formatted_results = [
                {
                    "score": score,
                    "metadata": doc.metadata,
                    "content": doc.page_content[:200] + "...",
                }
                for doc, score in results
            ]
            pprint(formatted_results)
        else:
            # If no query, just show a sample of documents
            print(
                f"\n--- Retrieving first {args.limit} documents from '{args.collection_name}' ---"
            )
            results = vectorstore._collection.peek(limit=args.limit)
            pprint(results)

    except Exception as e:
        print(f"An error occurred: {e}.")
        print(
            "Make sure your Docker services are running and the collection name is correct."
        )


if __name__ == "__main__":
    main()
