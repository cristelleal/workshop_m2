import json
import logging
import os

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models

import config

logger = logging.getLogger("assistant.ingest")


def _embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(base_url=config.OLLAMA_BASE_URL, model=config.EMBED_MODEL)


def _client() -> QdrantClient:
    return QdrantClient(url=config.QDRANT_URL)


def _has_points(collection: str) -> bool:
    client = _client()
    return client.collection_exists(collection) and client.count(collection).count > 0


LOADERS = {".md": TextLoader, ".txt": TextLoader, ".pdf": PyPDFLoader}


def _splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )


def _load_documents() -> list:
    """Charge les .md / .txt / .pdf produits par l'équipe (procédures, archi…)."""
    docs = []
    for glob, loader_cls, kwargs in (
        ("**/*.md", TextLoader, {"encoding": "utf-8"}),
        ("**/*.txt", TextLoader, {"encoding": "utf-8"}),
        ("**/*.pdf", PyPDFLoader, {}),
    ):
        loader = DirectoryLoader(
            config.DOCS_PATH, glob=glob, loader_cls=loader_cls,
            loader_kwargs=kwargs, silent_errors=True,
        )
        docs.extend(loader.load())
    return docs


def get_store(collection: str = config.DOCS_COLLECTION) -> QdrantVectorStore:
    """Retourne le vector store d'une collection existante. N'indexe rien."""
    return QdrantVectorStore.from_existing_collection(
        collection_name=collection, embedding=_embeddings(), url=config.QDRANT_URL,
    )


def build_index(force: bool = False) -> int:
    """Indexe DOCS_PATH si la collection est vide (ou si force=True). Retourne le nb de chunks."""
    if _has_points(config.DOCS_COLLECTION) and not force:
        logger.info("collection %s déjà remplie, ingestion ignorée", config.DOCS_COLLECTION)
        return 0

    documents = _load_documents()
    if not documents:
        logger.warning("aucun document trouvé dans %s", config.DOCS_PATH)
        return 0

    chunks = _splitter().split_documents(documents)

    # force_recreate : repart d'une collection propre (docs supprimés/renommés)
    QdrantVectorStore.from_documents(
        chunks, _embeddings(), url=config.QDRANT_URL,
        collection_name=config.DOCS_COLLECTION, force_recreate=True,
    )
    logger.info("index construit : %s documents -> %s chunks", len(documents), len(chunks))
    return len(chunks)


def index_file(path: str) -> int:
    """Indexe un seul fichier de DOCS_PATH, en remplaçant sa version précédente."""
    ext = os.path.splitext(path)[1].lower()
    loader_cls = LOADERS[ext]
    loader = loader_cls(path, encoding="utf-8") if loader_cls is TextLoader else loader_cls(path)
    chunks = _splitter().split_documents(loader.load())

    client = _client()
    if client.collection_exists(config.DOCS_COLLECTION):
        client.delete(
            config.DOCS_COLLECTION,
            points_selector=models.Filter(must=[
                models.FieldCondition(key="metadata.source", match=models.MatchValue(value=path))
            ]),
        )
    QdrantVectorStore.from_documents(
        chunks, _embeddings(), url=config.QDRANT_URL, collection_name=config.DOCS_COLLECTION,
    )
    logger.info("document indexé : %s -> %s chunks", path, len(chunks))
    return len(chunks)


def list_incidents() -> list[dict]:
    client = _client()
    if not client.collection_exists(config.INCIDENTS_COLLECTION):
        return []
    points, _ = client.scroll(config.INCIDENTS_COLLECTION, limit=1000, with_payload=True)
    return [
        {k: v for k, v in p.payload["metadata"].items() if k != "source"} for p in points
    ]


def incident_document(incident: dict) -> Document:
    """Un incident = un point. On vectorise le symptôme (ce qui ressemble aux logs reçus)."""
    text = (
        f"Incident : {incident['title']}\n"
        f"Service : {incident.get('service') or 'n/a'}\n"
        f"Symptômes / logs : {incident['symptoms']}\n"
        f"Cause : {incident['cause']}\n"
        f"Solution : {incident['solution']}"
    )
    return Document(page_content=text, metadata={**incident, "source": "incidents"})


def add_incidents(incidents: list[dict]) -> int:
    docs = [incident_document(i) for i in incidents]
    QdrantVectorStore.from_documents(
        docs, _embeddings(), url=config.QDRANT_URL, collection_name=config.INCIDENTS_COLLECTION,
    )
    return len(docs)


def seed_incidents() -> int:
    """Charge les incidents de référence uniquement si la collection est vide."""
    if _has_points(config.INCIDENTS_COLLECTION):
        return 0
    if not os.path.exists(config.INCIDENTS_SEED):
        logger.warning("fichier d'incidents de référence absent : %s", config.INCIDENTS_SEED)
        return 0
    with open(config.INCIDENTS_SEED, encoding="utf-8") as f:
        count = add_incidents(json.load(f))
    logger.info("base d'incidents initialisée : %s incidents", count)
    return count
