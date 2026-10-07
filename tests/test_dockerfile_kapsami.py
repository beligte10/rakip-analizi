"""Dockerfile, app.py'nin import ettiği tüm yerel modülleri imaja kopyalıyor mu?

2026-10-07: app.py'ye `import security` eklendi ama Dockerfile'a
`COPY security.py .` eklenmedi — yeni konteyner açılışta
ModuleNotFoundError ile çöktü, Coolify eski sürümde kaldı ve canlı site
güncellenmedi. Bu test aynı hatayı push'tan önce yakalar.
"""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _yerel_moduller():
    """Kök dizindeki .py dosyaları ve paket klasörleri."""
    adlar = {p.stem for p in ROOT.glob('*.py')}
    adlar |= {p.parent.name for p in ROOT.glob('*/__init__.py')}
    return adlar


def _app_importlari():
    agac = ast.parse((ROOT / 'app.py').read_text(encoding='utf-8'))
    adlar = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Import):
            adlar |= {a.name.split('.')[0] for a in dugum.names}
        elif isinstance(dugum, ast.ImportFrom) and dugum.module and dugum.level == 0:
            adlar.add(dugum.module.split('.')[0])
    return adlar


def _dockerfile_kopyalari():
    metin = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
    kopyalar = set()
    for kaynak in re.findall(r'^COPY\s+(\S+)\s+\S+', metin, flags=re.M):
        kopyalar.add(kaynak.rstrip('/').removesuffix('.py'))
    return kopyalar


def test_app_yerel_importlari_imaja_kopyalaniyor():
    gereken = _app_importlari() & _yerel_moduller()
    eksik = sorted(gereken - _dockerfile_kopyalari())
    assert not eksik, f"Dockerfile'da COPY eksik: {eksik}"
