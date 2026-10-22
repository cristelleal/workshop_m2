import os

# --- Ollama ---------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

# Modèle de génération : laissé VIDE volontairement. On le fixe après le
# benchmark, via la variable d'env LLM_MODEL (aucun modèle codé en dur).
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

# Modèle d'embeddings : stable (sert à construire l'index RAG, hors benchmark).
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text").strip()

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# --- Base vectorielle (Qdrant) ---------------------------------------------
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
# Procédures / docs de l'équipe : reconstruite depuis DOCS_PATH à chaque /reindex.
DOCS_COLLECTION = os.getenv("DOCS_COLLECTION", "docs")
# Incidents connus (symptôme -> cause -> solution) : alimentée au fil de l'eau
# via POST /incidents, jamais effacée par /reindex.
INCIDENTS_COLLECTION = os.getenv("INCIDENTS_COLLECTION", "incidents")
INCIDENTS_SEED = os.getenv("INCIDENTS_SEED", "/app/knowledge/incidents.json")

# --- RAG ------------------------------------------------------------------
DOCS_PATH = os.getenv("DOCS_PATH", "/docs")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "4"))
INCIDENTS_K = int(os.getenv("INCIDENTS_K", "3"))

# Sur CPU, le temps de réponse est dominé par la lecture du prompt (~18 tok/s) :
# on borne la taille des logs envoyés au LLM (on garde la fin, la plus récente).
MAX_LOG_CHARS = int(os.getenv("MAX_LOG_CHARS", "3000"))

# --- Accès -------------------------------------------------------------------
# L'assistant est joignable via Tailscale : toutes les routes sauf /health
# exigent l'en-tête X-API-Key.
ASSISTANT_API_KEY = os.getenv("ASSISTANT_API_KEY", "").strip()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
