import logging
from contextlib import asynccontextmanager

import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Security, UploadFile
from fastapi.security import APIKeyHeader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama
from pydantic import BaseModel

import config
from ingest import (
    LOADERS, add_incidents, build_index, get_store, index_file, list_incidents, seed_incidents,
)

logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("assistant")

# L'assistant EXPLIQUE, il n'agit pas : il ne doit pas être confondu avec le
# moteur de remédiation (cf. sujet §3.3).
PROMPT = ChatPromptTemplate.from_template(
    "Tu es un assistant pour les opérateurs d'une plateforme de paiement en incident.\n"
    "Réponds UNIQUEMENT à partir du contexte ci-dessous. Si l'information n'y est pas, "
    "dis-le clairement et ne l'invente pas.\n"
    "Tu n'exécutes AUCUNE action : tu expliques et tu renvoies vers les procédures.\n\n"
    "Contexte:\n{context}\n\n"
    "Question: {question}\n\n"
    "Réponse (en français) :"
)

LOG_PROMPT = ChatPromptTemplate.from_template(
    "Tu es un assistant pour les opérateurs d'une plateforme de paiement en incident.\n"
    "On te transmet des logs d'erreur ou de warning. Appuie-toi en priorité sur les "
    "incidents connus et les procédures ci-dessous. Si rien ne correspond, dis-le "
    "clairement et donne seulement des pistes de diagnostic, sans inventer de procédure.\n"
    "Tu n'exécutes AUCUNE action : tu proposes, l'opérateur décide.\n\n"
    "Incidents connus :\n{incidents}\n\n"
    "Procédures :\n{docs}\n\n"
    "Service concerné : {service}\n"
    "Logs :\n{logs}\n\n"
    "Réponds en français, de façon concise, avec exactement ces rubriques :\n"
    "**Diagnostic** : ce qui se passe, en une ou deux phrases.\n"
    "**Cause probable** : la cause la plus vraisemblable.\n"
    "**Actions recommandées** : étapes numérotées, la plus sûre d'abord.\n"
    "**Gravité** : faible, moyenne ou critique, avec la raison.\n"
)


def _format_docs(docs) -> str:
    return "\n\n".join(d.page_content for d in docs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tente de construire l'index au démarrage. Si Ollama/les modèles ne sont pas
    # encore prêts, on log et on continue : /reindex et /chat réessaieront.
    try:
        build_index()
        seed_incidents()
    except Exception:
        logger.exception("indexation au démarrage impossible (Ollama/Qdrant pas prêts ?)")
    yield


app = FastAPI(title="Assistant opérateur (RAG)", lifespan=lifespan)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Security(_api_key_header)) -> None:
    if not config.ASSISTANT_API_KEY:
        raise HTTPException(status_code=503, detail="ASSISTANT_API_KEY non configurée")
    if not key or not secrets.compare_digest(key, config.ASSISTANT_API_KEY):
        raise HTTPException(status_code=401, detail="clé API invalide ou absente")


protected = [Depends(require_api_key)]


def _llm() -> ChatOllama:
    if not config.LLM_MODEL:
        raise HTTPException(
            status_code=503,
            detail="LLM_MODEL non défini : choisissez un modèle (benchmark) puis "
            "renseignez la variable d'env LLM_MODEL et faites `ollama pull <modèle>`.",
        )
    return ChatOllama(
        base_url=config.OLLAMA_BASE_URL,
        model=config.LLM_MODEL,
        temperature=config.LLM_TEMPERATURE,
        # Désactive le mode "thinking" (actif par défaut sur gemma4) : sur CPU il
        # multiplie le temps de réponse par ~10 sans gain utile pour du RAG.
        reasoning=False,
    )


def _build_chain():
    llm = _llm()
    retriever = get_store().as_retriever(search_kwargs={"k": config.RETRIEVER_K})
    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | PROMPT | llm | StrOutputParser()
    )
    return retriever, chain


class Query(BaseModel):
    question: str


class LogBatch(BaseModel):
    logs: str
    service: str | None = None


class Incident(BaseModel):
    title: str
    service: str | None = None
    symptoms: str  # extrait de logs / message d'erreur caractéristique
    cause: str
    solution: str


@app.get("/health")
def health():
    return {"status": "ok", "llm_model": config.LLM_MODEL or None, "embed_model": config.EMBED_MODEL}


@app.post("/reindex", dependencies=protected)
def reindex():
    """Reconstruit l'index RAG depuis zéro (après mise à jour des docs)."""
    try:
        count = build_index(force=True)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"indexation impossible : {exc}") from exc
    return {"indexed_chunks": count}


@app.post("/chat", dependencies=protected)
def chat(query: Query):
    retriever, chain = _build_chain()
    try:
        answer = chain.invoke(query.question)
        sources = sorted({d.metadata.get("source") for d in retriever.invoke(query.question)})
    except Exception as exc:
        logger.exception("échec de la requête au LLM")
        raise HTTPException(status_code=503, detail=f"LLM indisponible : {exc}") from exc
    return {"answer": answer, "sources": sources}


@app.post("/analyze", dependencies=protected)
def analyze(batch: LogBatch):
    """Reçoit des logs d'erreur/warning et propose un diagnostic et des actions."""
    llm = _llm()
    logs = batch.logs.strip()[-config.MAX_LOG_CHARS:]
    if not logs:
        raise HTTPException(status_code=422, detail="logs vides")
    try:
        incidents = get_store(config.INCIDENTS_COLLECTION).similarity_search_with_score(
            logs, k=config.INCIDENTS_K
        )
        docs = get_store().similarity_search(logs, k=config.RETRIEVER_K)
        chain = LOG_PROMPT | llm | StrOutputParser()
        analysis = chain.invoke({
            "incidents": _format_docs(d for d, _ in incidents) or "(aucun)",
            "docs": _format_docs(docs) or "(aucune)",
            "service": batch.service or "inconnu",
            "logs": logs,
        })
    except Exception as exc:
        logger.exception("échec de l'analyse des logs")
        raise HTTPException(status_code=503, detail=f"analyse impossible : {exc}") from exc
    return {
        "analysis": analysis,
        "matched_incidents": [
            {"title": d.metadata.get("title"), "score": round(score, 3)} for d, score in incidents
        ],
        "sources": sorted({d.metadata.get("source") for d in docs}),
    }


@app.post("/incidents", status_code=201, dependencies=protected)
def add_incident(incident: Incident):
    """Enregistre un incident résolu : il servira aux prochaines analyses."""
    try:
        add_incidents([incident.model_dump()])
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"enregistrement impossible : {exc}") from exc
    return {"status": "created", "title": incident.title}


@app.get("/incidents", dependencies=protected)
def get_incidents():
    """Liste les incidents connus de la base."""
    return list_incidents()


@app.post("/documents", status_code=201, dependencies=protected)
async def upload_document(file: UploadFile):
    """Ajoute (ou remplace) un document .md / .txt / .pdf et l'indexe aussitôt."""
    name = os.path.basename(file.filename or "")
    if os.path.splitext(name)[1].lower() not in LOADERS:
        raise HTTPException(status_code=422, detail="formats acceptés : .md, .txt, .pdf")
    upload_dir = os.path.join(config.DOCS_PATH, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, name)
    with open(path, "wb") as f:
        f.write(await file.read())
    try:
        chunks = index_file(path)
    except Exception as exc:
        logger.exception("indexation de %s impossible", path)
        raise HTTPException(status_code=503, detail=f"indexation impossible : {exc}") from exc
    return {"document": name, "indexed_chunks": chunks}
