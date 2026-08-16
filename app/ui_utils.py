def format_bank_name(bank_name: str) -> str:
    """Banka adını grafiklerde göstermek için standartlaştırır."""
    if not bank_name:
        return "Belirtilmemiş"

# Öncelikli sözlük eşleştirmesi (Modül seviyesi sabit)
BANK_DICT = {
    "T.O.M. Katılım Bankası A.Ş.": "TOM Katılım",
    "Kuveyt Türk Katılım Bankası A.Ş.": "Kuveyt Türk",
    "Albaraka Türk Katılım Bankası A.Ş.": "Albaraka Türk",
    "Türkiye Finans Katılım Bankası A.Ş.": "Türkiye Finans",
    "Ziraat Katılım Bankası A.Ş.": "Ziraat Katılım",
    "Vakıf Katılım Bankası A.Ş.": "Vakıf Katılım",
    "Emlak Katılım Bankası A.Ş.": "Emlak Katılım",
    "Hayat Finans Katılım Bankası A.Ş.": "Hayat Finans",
    "Dünya Katılım Bankası A.Ş.": "Dünya Katılım"
}

def format_bank_name(bank_name: str) -> str:
    """Banka adını grafiklerde göstermek için standartlaştırır."""
    if not bank_name:
        return "Belirtilmemiş"

    # Güvenlik: Boşlukları temizle
    clean_input = bank_name.strip()

    if clean_input in BANK_DICT:
        return BANK_DICT[clean_input]

    # Sözlükte yoksa fallback olarak agresif temizlik yap
    cleaned = (
        clean_input.replace(" Katılım Bankası A.Ş.", "")
        .replace(" Bankası A.Ş.", "")
        .replace(" Katılım A.Ş.", "")
        .replace(" A.Ş.", "")
        .replace(" Anonim Şirketi", "")
        .strip()
    )

    if len(cleaned) > 15:
        return cleaned[:15] + "..."
    
    return cleaned
