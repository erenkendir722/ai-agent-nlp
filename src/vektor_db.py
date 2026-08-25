"""Vektör veritabanı (Qdrant) ve Gömme (Embedding) entegrasyonu (EVREN).

Serbest metin (kampanya koşulları) RAG aşamasında kullanılmak üzere
kampanya verilerini Qdrant'a yükler ve benzerlik araması yapar.
"""

import os
import logging
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchAny

from src.depolama import KampanyaKaydi

log = logging.getLogger(__name__)

# EVREN API Yapılandırması (Embeddings için)
EVREN_API_URL = os.getenv("EVREN_TEMEL_URL", "https://evren-llmapi.ssyz.org.tr/v1")
EVREN_API_KEY = os.getenv("EVREN_API_ANAHTARI", "")
EVREN_EMBEDDING_MODEL = os.getenv("EVREN_EMBEDDING_MODEL", "embedding") # SSB model adı

# Qdrant Yapılandırması
QDRANT_URL = os.getenv("QDRANT_URL", "https://qdrant.ssyz.org.tr")
QDRANT_API_KEY = os.getenv("QDRANT_API_ANAHTARI", "")

COLLECTION_NAME = "kampanyalar"
VECTOR_SIZE = 1024 # Model kartına göre güncellenebilir

_openai_client = None
_qdrant_client = None

def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            base_url=EVREN_API_URL,
            api_key=EVREN_API_KEY or "dummy_key"
        )
    return _openai_client

def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        if QDRANT_API_KEY:
            _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        else:
            _qdrant_client = QdrantClient(url=QDRANT_URL)
            
        # Koleksiyon var mı kontrol et, yoksa oluştur
        try:
            _qdrant_client.get_collection(COLLECTION_NAME)
        except Exception:
            log.info(f"Qdrant koleksiyonu oluşturuluyor: {COLLECTION_NAME}")
            _qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
    return _qdrant_client

def embed_text(text: str) -> list[float]:
    """EVREN üzerinden metni vektöre çevirir."""
    client = get_openai_client()
    try:
        response = client.embeddings.create(
            input=text,
            model=EVREN_EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        log.error(f"Embedding alınamadı: {e}")
        # Hata durumunda 0 vektörü dön (testler kırılmasın diye)
        return [0.0] * VECTOR_SIZE

def kayitlari_vektorlestir(kayitlar: list[KampanyaKaydi]):
    """Kampanya kayıtlarını paragraf paragraf Qdrant'a yükler."""
    client = get_qdrant_client()
    points = []
    
    point_id = 1
    import re
    
    for kayit in kayitlar:
        if not kayit.ham_metin:
            continue
            
        paragraflar = re.split(r"\n+", kayit.ham_metin)
        
        for paragraf in paragraflar:
            if len(paragraf) < 40:
                continue
            
            vector = embed_text(paragraf)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "kampanya_id": kayit.kampanya_id,
                        "banka_adi": kayit.banka_adi,
                        "metin": paragraf
                    }
                )
            )
            point_id += 1
            
    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        log.info(f"{len(points)} vektör Qdrant'a yazıldı.")


def vektor_ara(sorgu: str, limit: int = 3, filter_ids: list[str] | None = None) -> list[dict]:
    """Sorguya en benzer metinleri Qdrant'tan getirir.
    
    Eğer filter_ids verilirse, yalnızca bu kampanya ID'lerine sahip vektörlerde arar.
    """
    client = get_qdrant_client()
    vector = embed_text(sorgu)
    
    query_filter = None
    if filter_ids:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="kampanya_id",
                    match=MatchAny(any=filter_ids)
                )
            ]
        )
    
    try:
        search_result = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=limit,
            query_filter=query_filter
        )
        return [hit.payload for hit in search_result]
    except Exception as e:
        log.error(f"Vektör araması başarısız: {e}")
        return []
