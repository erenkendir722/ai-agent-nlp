"""Ajan katmanı — hiyerarşik ajan mimarisi (v3).

Buradaki ajanların çoğu YENİ KOD DEĞİL; sistemde zaten çalışan parçaların
ajan sözleşmesine bağlanmış hâli. Eşleme:

    toplayici    <- src/collector/toplayici.py
    cikarim      <- src/extraction/llm.py
    elestirmen   <- src/extraction/llm.py içindeki kanıt reddi (buraya taşındı)
    muhakeme     <- YENİ, tek gerçek yeni ajan
    orkestrator  <- src/rag/chatbot.py: niyet_belirle()

Karşılaştırma motoru (`src/comparison/`) bilinçli olarak ajan DEĞİLDİR:
taksit hesabı, sıralama ve aritmetik saf koddur. LLM'e aritmetik yaptırmak,
halüsinasyon savunmasıyla kazanılan güveni tek hamlede kaybettirir.
"""

from src.ajanlar.temel import Ajan, AjanIzi, IzDefteri, iz_tut

__all__ = ["Ajan", "AjanIzi", "IzDefteri", "iz_tut"]
