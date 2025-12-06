# admin_backend/bot/rag.py
import os
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = "chroma_db"
KNOWLEDGE_DIR = "knowledge"
COLLECTION_NAME = "hotel_knowledge"

_client = None
_collection = None
_model = None


def get_chroma_collection():
    global _client, _collection, _model
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _collection, _model


def split_into_chunks(text: str, min_length=30) -> list[str]:
    return [line.strip() for line in text.split("\n") if len(line.strip()) >= min_length]


def load_all_knowledge():
    collection, model = get_chroma_collection()

    # Очистка
    try:
        collection.delete(where={})
    except:
        pass

    if not os.path.exists(KNOWLEDGE_DIR):
        print("❌ Папка knowledge/ не найдена")
        return

    files = [f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith(".txt")]
    if not files:
        print("❌ Нет .txt файлов в knowledge/")
        return

    total = 0
    for filename in files:
        hotel_name = filename.replace(".txt", "")
        with open(os.path.join(KNOWLEDGE_DIR, filename), "r", encoding="utf-8") as f:
            text = f.read().strip()

        chunks = split_into_chunks(text)
        embeddings = model.encode(chunks).tolist()
        ids = [f"{hotel_name}_{i}" for i in range(len(chunks))]
        metadatas = [{"hotel": hotel_name} for _ in chunks]

        # ⚠️ ОБЯЗАТЕЛЬНО передавать metadatas!
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas  # ← ЭТО КРИТИЧНО!
        )
        total += len(chunks)
        print(f"✅ Загружено {len(chunks)} чанков для {hotel_name}")

    print(f"🧮 Всего фрагментов: {total}")


def knowledge_query(query: str, filter: dict = None) -> str:
    collection, model = get_chroma_collection()
    query_emb = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_emb,
        n_results=3,
        where=filter  # ← фильтр будет работать ТОЛЬКО если metadatas были сохранены
    )

    docs = results.get("documents", [])
    return "\n".join(docs[0]) if docs and docs[0] else ""


if __name__ == "__main__":
    load_all_knowledge()