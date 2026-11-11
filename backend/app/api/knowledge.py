import asyncio
from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from app.services import rag_service

router = APIRouter()


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    collection: str = Query(default="default"),
):
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty or unreadable file")

    metadata = {"source": file.filename or "unknown", "content_type": file.content_type or ""}

    chunk_count = await asyncio.to_thread(
        rag_service.ingest_document, text, metadata, collection
    )

    return {
        "status": "completed",
        "filename": file.filename,
        "chunks": chunk_count,
        "collection": collection,
    }


@router.get("/search")
async def search_knowledge(
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    collection: str = Query(default="default"),
):
    results = await asyncio.to_thread(
        rag_service.search, query, top_k, collection
    )
    return {"results": results, "query": query}


@router.get("/collections")
async def list_collections():
    collections = await asyncio.to_thread(rag_service.list_collections)
    return {"collections": collections}


@router.delete("/collections/{name}")
async def delete_collection(name: str):
    success = await asyncio.to_thread(rag_service.delete_collection, name)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"status": "deleted", "name": name}
