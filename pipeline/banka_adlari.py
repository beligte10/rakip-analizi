"""
pipeline.banka_adlari
=====================
Banka adı eşlemesi (2026-10-02): platformda gösterilen (kanonik) banka adı ile
BDDK dosya/klasör adları farklı olabilir. Örn. ham dosyalar 'QNB Finansbank -
30.06.2026.xlsx' adıyla gelir ama platformun her yerinde 'QNB' yazılır.

Kanonik ad catalog.seed.json'daki `banka_adi`dır; eski adlar yalnız giriş
noktalarında (dosya adı, ZIP klasörü, eski parquet/katalog) bu tabloyla
çevrilir. Yeni bir yeniden adlandırmada buraya satır eklemek yeterli.
"""
from __future__ import annotations

from typing import Dict

BANKA_AD_ESLEME: Dict[str, str] = {
    'QNB Finansbank': 'QNB',
}


def kanonik(ad: str) -> str:
    """Eski/dosya adını platformdaki kanonik banka adına çevirir."""
    if ad is None:
        return ad
    return BANKA_AD_ESLEME.get(str(ad).strip(), str(ad).strip())
