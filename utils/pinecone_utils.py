import os
from typing import List, Dict, Any, Optional
from pinecone import Pinecone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class PineconeManager:
    def __init__(self):
        """Initialize Pinecone with API key for both vector operations and reranking."""
        api_key = os.getenv('PINECONE_API_KEY')
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(os.getenv('PINECONE_INDEX_NAME'))

    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text string."""
        try:
            # Get index stats to determine vector dimension
            stats = self.index.describe_index_stats()
            dimension = stats['dimension']

            # Create embedding with correct dimension
            embeddings = self.pc.inference.embed(
                model="multilingual-e5-large",
                inputs=[text],
                parameters={"input_type": "passage", "truncate": "END"}
            )

            # Ensure embedding matches index dimension
            values = embeddings[0]['values']
            if len(values) != dimension:
                print(
                    f"Warning: Embedding dimension {len(values)} does not match index dimension {dimension}")
                # Pad or truncate to match dimension
                if len(values) < dimension:
                    values.extend([0] * (dimension - len(values)))
                else:
                    values = values[:dimension]

            return values

        except Exception as e:
            print(f"Error creating embedding: {str(e)}")
            # Return zero vector with correct dimension as fallback
            return [0] * dimension

    def upsert_vector(self,
                      vector_id: str,
                      vector_values: List[float],
                      metadata: Dict[str, Any],
                      namespace: str = "default") -> bool:
        """Upsert a single vector to Pinecone."""
        try:
            # Format records according to Pinecone documentation
            records = [{
                "id": vector_id,
                "values": vector_values,
                "metadata": metadata
            }]

            self.index.upsert(vectors=records, namespace=namespace)
            return True
        except Exception as e:
            print(f"Error upserting vector: {str(e)}")
            return False

    def query_vectors(self,
                      query_vector: List[float],
                      top_k: int = 25,
                      namespace: str = "default",
                      filter_dict: Dict = None) -> Optional[Dict]:
        """Query vectors from Pinecone."""
        try:
            return self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter_dict,
                include_metadata=True  # Always include metadata for search_documents
            )
        except Exception as e:
            print(f"Error querying vectors: {str(e)}")
            return None

    def get_all_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Get relevant documents from Pinecone index using semantic search.
        Returns list of documents with their summaries and cloudflare paths.
        """
        try:
            # Create query embedding
            query_embedding = self.create_embedding(query)
            if not query_embedding:
                print("Error: Could not create query embedding")
                return []

            # Query vectors with semantic search
            query_response = self.query_vectors(
                query_vector=query_embedding,
                top_k=50,  # Increased from default 25 to get more potential matches
                namespace="default"
            )

            if not query_response or not query_response.get('matches'):
                print("No matching documents found")
                return []

            # Extract document information from matches
            documents = []
            for match in query_response['matches']:
                metadata = match.get('metadata', {})
                summary = metadata.get('summary')
                cloudflare_path = metadata.get('cloudflare_path')
                if summary and cloudflare_path:
                    documents.append({
                        'summary': summary,
                        'cloudflare_path': cloudflare_path,
                        # Include similarity score for debugging
                        'score': match.get('score', 0)
                    })

            print(
                f"Retrieved {len(documents)} semantically relevant documents for screening")
            return documents

        except Exception as e:
            print(f"Error getting documents: {str(e)}")
            return []
