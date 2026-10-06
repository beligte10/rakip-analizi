"""TÜİK SDMX istemcisi (2026-09-30).

Veri: TÜİK Veri Portalı SDMX REST servisi (nsiws.tuik.gov.tr), Bearer token
(giris.tuik.gov.tr, 300 sn ömürlü) ile. Anahtar: TUIK_API_KEY ortam değişkeni.

Çözümleme fonksiyonları (parse_*, search_dataflows, build_sdmx_key,
filter_rows, limit_rows, resolve_version …) github.com/orhoncan/tuik-mcp
(MIT Lisansı, © orhoncan) projesinin src/tuik_sdmx_mcp/sdmx.py dosyasından
DEĞİŞTİRİLMEDEN alınmıştır. HTTP katmanı (asenkron httpx + fastmcp yerine)
asistanın geri kalanı gibi eşzamanlı urllib ile yeniden yazıldı; anahtar
kaydetme aracı alınmadı (anahtar yalnız sunucu ortamından okunur).
Araç resmi değildir; TÜİK ile bağlantısı yoktur.
"""
from __future__ import annotations

import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import unicodedata
import urllib.parse
from typing import Dict, List, Optional

from .http import ExternalError, TTLCache, request_json

BASE_URL = 'https://nsiws.tuik.gov.tr/rest'
TOKEN_URL = 'https://giris.tuik.gov.tr/realms/web/protocol/openid-connect/token'
CLIENT_ID = 'nsi-ws-consumer'
AGENCY = 'TR'
SOURCE = 'TÜİK servisi'
MAX_KEY_LEN = 1500          # SDMX anahtarı bundan uzunsa istemci tarafı süzme
_REFRESH_MARGIN = 30.0


def api_key() -> str:
    return os.environ.get('TUIK_API_KEY', '').strip()


def enabled() -> bool:
    """2026-09-30: TÜİK beklemeye alındı (kullanıcı kararı) — servis isteklerin
    ~%20-30'unda bağlantıyı kabul edip yanıt vermiyor. Kod hazır; açmak için
    TUIK_API_KEY'e ek olarak TUIK_ETKIN=1 tanımlanmalı."""
    return bool(api_key()) and os.environ.get('TUIK_ETKIN', '').strip() == '1'


# ------------------------------------------------------------------
# tuik-mcp'den alınan çözümleme fonksiyonları (MIT) — değiştirilmedi
# ------------------------------------------------------------------
def is_production(df: dict) -> bool:
    """Check if a dataflow is production (not test)."""
    for ann in df.get("annotations", []):
        if ann.get("type") == "NonProductionDataflow" and ann.get("text") == "true":
            return False
    return True


def parse_dataflows(
    refs: dict, production_only: bool = True
) -> list[dict]:
    """Parse dataflow references into a clean list."""
    results = []
    for _urn, df in refs.items():
        if production_only and not is_production(df):
            continue
        results.append(
            {
                "id": df["id"],
                "name": df.get("name", ""),
                "description": df.get("description", ""),
                "version": df.get("version", ""),
            }
        )
    return results


def parse_sdmx_data(
    json_data: dict,
    keep_dimensions: set[str] | None = None,
) -> list[dict]:
    """Parse SDMX JSON response into a list of flat dicts.

    ``keep_dimensions`` prevents selected series dimensions from being removed
    as constants. The long-URL client-side fallback needs those columns for
    filtering even when the selected response contains only one value.

    Automatically removes columns where all rows share a single value
    (e.g. "Not Applicable", or a lone indicator name).
    """
    struct = json_data["structure"]
    ds = json_data["dataSets"][0]

    dim_info: dict[str, dict] = {}
    for dtype in ("series", "observation"):
        for dim in struct.get("dimensions", {}).get(dtype, []):
            dim_id = dim["id"]
            pos = dim.get("keyPosition", dim.get("position", 0))
            values = {i: v["name"] for i, v in enumerate(dim.get("values", []))}
            dim_info[dim_id] = {
                "id": dim_id, "position": pos, "values": values, "type": dtype
            }

    # Observation boyutları, gözlem anahtarındaki (ör. "0:1") konum sırasına
    # göre çözülür; tek observation boyutunda anahtar "0" gibi tek parçalıdır.
    obs_dims_sorted = sorted(
        (info for info in dim_info.values() if info["type"] == "observation"),
        key=lambda i: i["position"],
    )
    obs_ids = {
        dim_id for dim_id, info in dim_info.items() if info["type"] == "observation"
    }

    rows: list[dict] = []
    for series_key, series_val in ds.get("series", {}).items():
        key_parts = series_key.split(":")
        series_dims: dict[str, str] = {}
        for dim_id, info in dim_info.items():
            if info["type"] == "series":
                pos = info["position"]
                if pos < len(key_parts):
                    idx = int(key_parts[pos])
                    series_dims[dim_id] = info["values"].get(idx, f"?{idx}")

        for obs_key, obs_val in series_val.get("observations", {}).items():
            obs_parts = obs_key.split(":")
            obs_dims: dict[str, str] = {}
            for i, info in enumerate(obs_dims_sorted):
                if i < len(obs_parts) and obs_parts[i].isdigit():
                    idx = int(obs_parts[i])
                    obs_dims[info["id"]] = info["values"].get(idx, f"?{idx}")

            value = obs_val[0] if obs_val else None
            row = {**series_dims, **obs_dims, "DEGER": value}
            rows.append(row)

    if rows:
        # Sabit sütunları temizle - ama observation boyutlarını (ör. TIME_PERIOD)
        # asla düşürme: tek dönemlik çekimde tarih kaybolmasın.
        kept_ids = keep_dimensions or set()
        all_keys = [k for k in rows[0] if k != "DEGER"]
        drop_keys = []
        for k in all_keys:
            if k in obs_ids or k in kept_ids:
                continue
            unique = set(r.get(k) for r in rows)
            if len(unique) <= 1:
                drop_keys.append(k)
        if drop_keys:
            rows = [{k: v for k, v in r.items() if k not in drop_keys} for r in rows]

    return rows


# Dataflow adları İngilizce; Türkçe sorguların da eşleşmesi için sık kullanılan
# TÜİK konularının İngilizce karşılıkları. Her terim aranırken kendisi VE varsa
# çevirileri OR mantığıyla denenir; terimler arası AND korunur.
_TR_EN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "işsizlik": ("unemployment",),
    "istihdam": ("employment",),
    "işgücü": ("labour", "labor"),
    "nüfus": ("population",),
    "enflasyon": ("inflation", "price"),
    "fiyat": ("price",),
    "ticaret": ("trade",),
    "ihracat": ("export",),
    "ithalat": ("import",),
    "üretim": ("production",),
    "sanayi": ("industry", "industrial"),
    "konut": ("housing", "dwelling"),
    "turizm": ("tourism",),
    "eğitim": ("education",),
    "sağlık": ("health",),
    "gelir": ("income",),
    "yoksulluk": ("poverty",),
    "ücret": ("wage",),
    "tarım": ("agriculture", "agricultural"),
}


def _search_normalize(text: str) -> str:
    """Türkçe ve İngilizce metni ortak, aksansız arama biçimine çevirir.

    Katalog İngilizce olduğu için ``I`` harfini Türkçe kuralla ``ı`` yapmak
    ``Import`` gibi sözcükleri bozuyordu. Unicode ayrıştırma ve casefold ile
    hem ``Import/import`` hem de ``İşsizlik/işsizlik`` aynı biçime gelir.
    """
    decomposed = unicodedata.normalize("NFKD", text).casefold().replace("ı", "i")
    return "".join(char for char in decomposed if not unicodedata.combining(char))


_NORMALIZED_SYNONYMS: dict[str, tuple[str, ...]] = {
    _search_normalize(term): tuple(_search_normalize(value) for value in values)
    for term, values in _TR_EN_SYNONYMS.items()
}


def search_dataflows(
    dataflows: list[dict], query: str
) -> list[dict]:
    """Search dataflows by keyword(s).

    Each term matches if the term itself or any of its known Turkish->English
    synonyms appears in the dataflow text, so Turkish queries reach the
    English-only catalog. Terms are ANDed, ancak hiçbir dataflow'da geçmeyen
    terimler (ör. 'oranı' gibi ek/dolgu kelimeler) sorguyu boşa düşürmesin
    diye yok sayılır; tüm terimler eşleşmesizse boş liste döner.
    """
    terms = _search_normalize(query).split()
    if not terms:
        return []

    texts = [
        (df, _search_normalize(f"{df['name']} {df['description']} {df['id']}"))
        for df in dataflows
    ]

    def variants(term: str) -> tuple[str, ...]:
        return (term, *_NORMALIZED_SYNONYMS.get(term, ()))

    # Katalogda hiçbir yerde geçmeyen terimleri AND'den düşür.
    effective = [
        t for t in terms
        if any(any(v in text for v in variants(t)) for _df, text in texts)
    ]
    if not effective:
        return []

    return [
        df for df, text in texts
        if all(any(v in text for v in variants(t)) for t in effective)
    ]


def parse_structure(json_data: dict) -> list[dict]:
    """Parse dimension structure from a nodata response.

    Returns dimensions ordered by position. Each dimension has:
    - id, name, position, values (list of {id, name}), value_count
    Single-valued dimensions are marked with single_value=True.
    """
    dimensions: list[dict] = []
    for dtype in ("series", "observation"):
        for dim in (
            json_data.get("structure", {})
            .get("dimensions", {})
            .get(dtype, [])
        ):
            values = [
                {"id": v["id"], "name": v.get("name", v["id"])}
                for v in dim.get("values", [])
            ]
            dimensions.append(
                {
                    "id": dim["id"],
                    "name": dim.get("name", ""),
                    "position": dim.get("keyPosition", dim.get("position", 0)),
                    "type": dtype,
                    "values": values,
                    "value_count": len(values),
                    "single_value": len(values) <= 1,
                }
            )
    dimensions.sort(key=lambda d: d["position"])
    return dimensions


def build_sdmx_key(
    dimensions: list[dict],
    boyut_filtre: dict[str, list[str]] | None,
) -> str:
    """Build an SDMX REST data-query key from a dimension-value filter.

    The key lists value codes for every series dimension (ordered by
    keyPosition), joining multiple codes in one position with '+' and positions
    with '.'. TÜİK's SDMX endpoint rejects wildcard/partial keys (empty
    positions -> 404), so once any dimension is filtered the key must be fully
    specified: filtered dimensions get the selected codes, and every other
    dimension is filled with *all* of its codes. This pushes filtering to the
    server instead of downloading everything and trimming client-side.

    Args:
        dimensions: Output of parse_structure (each has id, type, position,
            values[{id, name}]).
        boyut_filtre: {dimension_id: [value_name_or_id, ...]}. Values are
            matched against each dimension's value name first, then its id.
            Observation dimensions (e.g. TIME_PERIOD) are ignored here; use
            start/endPeriod for those.

    Returns:
        The key string, or "" when nothing is filtered (fetch all).

    Raises:
        ValueError: if a requested value matches no name/id in its dimension.
    """
    if not boyut_filtre:
        return ""

    # Bilinmeyen filtre anahtarını (ör. typo) sessizce yok sayma: yok sayılırsa
    # anahtar boş kalıp tüm veri çekilir (kapsam taşması). Hiçbir boyutla
    # eşleşmeyen anahtar varsa net bir hata yükselt.
    known_ids = {d["id"] for d in dimensions}
    unknown = [k for k in boyut_filtre if k not in known_ids]
    if unknown:
        valid = ", ".join(sorted(known_ids))
        raise ValueError(
            f"Bilinmeyen boyut(lar): {', '.join(unknown)}. "
            f"Geçerli boyutlar: {valid}"
        )

    # Boş seçim listesi belirsizdir: "hepsi" mi "hiçbiri" mi? Sessizce tüm
    # veriyi çekmek yerine net hata ver (boyutu filtrelememek için anahtarı
    # sözlükten tamamen çıkarmak yeterli).
    empty = [k for k, v in boyut_filtre.items() if not v]
    if empty:
        raise ValueError(
            f"Boş değer listesi: {', '.join(empty)}. Bir boyutu filtrelemek "
            "istemiyorsanız onu boyut_filtre'den tamamen çıkarın."
        )

    # Observation boyutları (ör. TIME_PERIOD) seri anahtarına giremez; sessizce
    # yok saymak filtresiz veriyi filtrelenmiş gibi döndürür. Net hata ver ve
    # dönem filtresi için baslangic/bitis parametrelerine yönlendir.
    obs_ids = {d["id"] for d in dimensions if d.get("type") == "observation"}
    obs_filtered = [k for k in boyut_filtre if k in obs_ids]
    if obs_filtered:
        raise ValueError(
            f"{', '.join(obs_filtered)} bir gözlem boyutudur ve boyut_filtre "
            "ile filtrelenemez. Dönem filtresi için baslangic/bitis "
            "parametrelerini kullanın."
        )

    series_dims = sorted(
        (d for d in dimensions if d.get("type") == "series"),
        key=lambda d: d["position"],
    )

    parts: list[str] = []
    for dim in series_dims:
        wanted = boyut_filtre.get(dim["id"])
        if not wanted:
            # Filtrelenmeyen boyut: TÜİK boş konum kabul etmediği için tüm
            # kodlarını doldur.
            parts.append("+".join(v["id"] for v in dim["values"]))
            continue
        by_name = {v["name"]: v["id"] for v in dim["values"]}
        by_id = {v["id"]: v["id"] for v in dim["values"]}
        codes: list[str] = []
        for w in wanted:
            code = by_name.get(w) or by_id.get(w)
            if code is None:
                valid = ", ".join(v["name"] for v in dim["values"])
                raise ValueError(
                    f"'{dim['id']}' boyutunda geçersiz değer: '{w}'. "
                    f"Geçerli değerler: {valid}"
                )
            codes.append(code)
        parts.append("+".join(codes))

    return ".".join(parts)


def filtre_to_names(
    dimensions: list[dict],
    boyut_filtre: dict[str, list[str]],
) -> dict[str, list[str]]:
    """boyut_filtre değerlerini (ad veya kod id) satırlardaki adlara çözer.

    Client tarafı süzme (filter_rows) satırlardaki insan-okur adlarla eşleşir;
    kullanıcı id verdiyse ada çevrilmesi gerekir. build_sdmx_key ile aynı
    ad-önce çözümleme kuralı uygulanır.
    """
    by_dim = {d["id"]: d for d in dimensions}
    resolved: dict[str, list[str]] = {}
    for dim_id, wanted in boyut_filtre.items():
        dim = by_dim.get(dim_id)
        if dim is None:
            resolved[dim_id] = list(wanted)
            continue
        # parse_sdmx_data sabit seri boyutlarını çıktıda düşürür. Tek değerli
        # bir boyut build_sdmx_key tarafından zaten doğrulandığı ve veriyi daha
        # fazla daraltamayacağı için client filtresine eklenmemelidir; aksi halde
        # eksik sütun fail-closed kontrolünde geçerli sonuçların tamamı elenir.
        if dim.get("single_value"):
            continue
        names = {v["name"] for v in dim["values"]}
        by_id = {v["id"]: v["name"] for v in dim["values"]}
        resolved[dim_id] = [
            w if w in names else by_id.get(w, w) for w in wanted
        ]
    return resolved


def filter_rows(
    rows: list[dict],
    boyut_filtre: dict[str, list[str]],
) -> list[dict]:
    """Filter parsed rows by dimension code IDs.

    Args:
        rows: Flat observation dicts from parse_sdmx_data.
        boyut_filtre: {dimension_id: [allowed_code_name, ...]}
            Values are matched against the human-readable names in rows.
    """
    if not boyut_filtre:
        return rows
    filtered = []
    for row in rows:
        match = True
        for dim_id, allowed in boyut_filtre.items():
            # Eksik boyutu eşleşme sayma: API beklenmedik bir yapı döndürürse
            # filtrelenmemiş/alakasız satırlar filtreyi geçmiş gibi görünmesin.
            if dim_id not in row or row[dim_id] not in allowed:
                match = False
                break
        if not match:
            continue
        filtered.append(row)
    return filtered


def _version_key(version: str) -> tuple:
    """Numeric sort key for a dotted version string ("10.0" > "9.0").

    Non-numeric segments fall back to (0, segment) so mixed versions still
    order deterministically instead of raising.
    """
    parts = []
    for seg in str(version).split("."):
        if seg.isdigit():
            parts.append((1, int(seg), ""))
        else:
            parts.append((0, 0, seg))
    return tuple(parts)


def _period_bounds(period: str) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Bir SDMX dönemini (başlangıç_ayı, bitiş_ayı) aralığına çevirir.

    "2024" -> (2024,1)..(2024,12); "2024-03" -> (2024,3)..(2024,3);
    "2024-Q2" -> (2024,4)..(2024,6). Tanınmayan biçimde None döner (doğrulama
    atlanır, karar sunucuya bırakılır).
    """
    parts = period.strip().split("-", 1)
    if not parts[0].isdigit():
        return None
    year = int(parts[0])
    if len(parts) == 1:
        return (year, 1), (year, 12)
    sub = parts[1].upper()
    if sub.isdigit() and 1 <= int(sub) <= 12:
        month = int(sub)
        return (year, month), (year, month)
    if sub.startswith("Q") and sub[1:].isdigit() and 1 <= int(sub[1:]) <= 4:
        q = int(sub[1:])
        return (year, 3 * q - 2), (year, 3 * q)
    return None


def validate_fetch_params(
    son_gozlem: int, limit: int, baslangic: str, bitis: str
) -> None:
    """tuik_cek girdilerini erken doğrula; anlamsız değerlerde net hata ver.

    Dönem karşılaştırması takvimseldir, leksik değildir: bitis="2024" yıl sonu
    demektir, dolayısıyla baslangic="2024-01" geçerli bir aralıktır.

    Raises:
        ValueError: negatif son_gozlem/limit ya da baslangic bitis'ten sonra
            başlıyorsa.
    """
    if son_gozlem < 0:
        raise ValueError("son_gozlem negatif olamaz (0 = kapalı).")
    if limit < 0:
        raise ValueError("limit negatif olamaz (0 = sınırsız).")
    if baslangic and bitis:
        start = _period_bounds(baslangic)
        end = _period_bounds(bitis)
        # Biri tanınmıyorsa karar sunucuya bırakılır.
        if start and end and start[0] > end[1]:
            raise ValueError(
                f"baslangic ({baslangic}) bitis'ten ({bitis}) sonra olamaz."
            )


def limit_rows(
    rows: list[dict], limit: int
) -> tuple[list[dict], bool, int]:
    """Cap the number of returned rows so a large fetch can't flood context.

    Args:
        rows: Parsed observation rows.
        limit: Max rows to return; 0 or negative means no cap.

    Returns:
        (kept_rows, truncated, total_row_count).
    """
    total = len(rows)
    if limit and limit > 0 and total > limit:
        return rows[:limit], True, total
    return rows, False, total


def resolve_version(
    dataflows: list[dict],
    dataflow_id: str,
    requested_version: str = "",
) -> str:
    """Validate a dataflow ID and honor a version or select the latest one.

    TÜİK kataloğu eski ama hâlâ erişilebilir sürümlerin tamamını listelemek
    zorunda değildir. Açık sürümün varlığı veri yapısı isteğiyle doğrulanır.
    """
    versions = [df["version"] for df in dataflows if df["id"] == dataflow_id]
    if not versions:
        raise ValueError(f"Dataflow bulunamadı: {dataflow_id}")
    if requested_version:
        return requested_version
    return max(versions, key=_version_key)


# ------------------------------------------------------------------
# HTTP katmanı (eşzamanlı)
# ------------------------------------------------------------------
class _Token:
    def __init__(self):
        self._token = ''
        self._expires = 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if self._token and time.monotonic() < self._expires:
                return self._token
            try:
                payload = request_json(TOKEN_URL, data={'grant_type': 'password', 'client_id': CLIENT_ID,
                                                        'api_key': api_key()}, source='TÜİK giriş servisi')
            except ExternalError as e:
                raise ExternalError('TÜİK anahtarı doğrulanamadı ya da giriş servisi yanıt vermedi '
                                    f'({e})') from None
            token = payload.get('access_token') if isinstance(payload, dict) else None
            if not token:
                raise ExternalError('TÜİK giriş servisi token döndürmedi')
            self._token = token
            self._expires = time.monotonic() + max(0.0, float(payload.get('expires_in', 300)) - _REFRESH_MARGIN)
            return self._token

    def reset(self) -> None:
        with self._lock:
            self._token = ''
            self._expires = 0.0


_token = _Token()
_catalog = TTLCache(ttl=24 * 3600)
_structures = TTLCache(ttl=24 * 3600)


_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix='tuik')
HEDGE_AT = (5.0, 12.0)   # ilk istek dönmezse bu saniyelerde paralel yeni istekler
MAX_WAIT = 35.0          # toplam bekleme üst sınırı


def _get_once(url: str, timeout: float):
    for attempt in (1, 2):
        headers = {'Authorization': 'Bearer ' + _token.get(), 'Accept': 'application/json'}
        try:
            return request_json(url, headers=headers, timeout=timeout, source=SOURCE)
        except ExternalError as e:
            if e.status in (401, 403) and attempt == 1:
                _token.reset()      # token erken geçersizleştiyse bir kez yenile
                continue
            raise


def _get(path: str, params: Optional[dict] = None, timeout: float = MAX_WAIT):
    """Kimlikli GET, "hedge" ile. TÜİK servisi isteklerin bir kısmında
    bağlantıyı kabul edip hiç yanıt vermiyor (2026-09-30 ölçümü: bağlantı ve
    TLS <0,2 sn, aynı URL bir denemede 1 sn'de, diğerinde 20 sn'de bile
    yanıtsız; ~%20-30). İlk istek HEDGE_AT saniyelerinde dönmemişse paralel
    yeni istekler açılır (eşdeğer URL varyantlarıyla); önce başarıyla dönen
    alınır, toplam bekleme en fazla `timeout` sn. Kesin yanıtlar (404/400 …)
    hemen hata olarak döner."""
    params = dict(params or {})
    q = urllib.parse.urlencode
    base = f'{BASE_URL}/{path}'
    urls = [base + (('?' + q(params)) if params else ''),
            base + '?' + q({**params, 'dimensionAtObservation': 'TIME_PERIOD'}),
            base + '?' + q({**params, 'includeHistory': 'false'})]
    start = time.monotonic()
    deadline = start + timeout
    futures = [_pool.submit(_get_once, urls[0], timeout)]
    launched = 1
    last_err: Optional[ExternalError] = None
    while futures or launched <= len(HEDGE_AT):
        now = time.monotonic()
        if now >= deadline:
            break
        next_at = start + HEDGE_AT[launched - 1] if launched <= len(HEDGE_AT) else deadline
        if futures:
            done, _ = wait(futures, timeout=max(0.0, min(next_at, deadline) - now), return_when=FIRST_COMPLETED)
        else:
            done = set()
            time.sleep(max(0.0, min(next_at, deadline) - now))
        for f in done:
            futures.remove(f)
            try:
                return f.result()
            except ExternalError as e:
                if e.status is not None:
                    raise           # kesin yanıt: tekrar denenmez
                last_err = e
        if launched <= len(HEDGE_AT) and time.monotonic() >= next_at:
            futures.append(_pool.submit(_get_once, urls[launched], max(1.0, deadline - time.monotonic())))
            launched += 1
    raise last_err or ExternalError(f'{SOURCE} {int(timeout)} sn içinde yanıt vermedi; biraz sonra tekrar deneyin')


def dataflows() -> List[dict]:
    """Üretim (test olmayan) veri setleri; 24 saat önbellekte."""
    def load():
        refs = (_get('dataflow/TR/all', timeout=40.0) or {}).get('references', {})
        flows = parse_dataflows(refs, production_only=True)
        if not flows:
            raise ExternalError('TÜİK veri seti listesi boş döndü')
        return flows
    return _catalog.get('dataflows', load)


def dimensions(dataflow_id: str, version: str) -> List[dict]:
    def load():
        dims = parse_structure(_get(f'data/{AGENCY},{dataflow_id},{version}/', {'detail': 'nodata'}, 30.0))
        if not dims:
            raise ExternalError(f'{dataflow_id} için boyut yapısı alınamadı')
        return dims
    return _structures.get((dataflow_id, version), load)


def fetch(dataflow_id: str, version: str, key: str = '', baslangic: str = '',
          bitis: str = '') -> Optional[dict]:
    """Ham SDMX-JSON; seçilen dilimde veri yoksa (404) None. (lastNObservations
    bilerek kullanılmıyor — servis bu parametrede takılıyor; son N dönem
    istemci tarafında seçilir, bkz. tools._son_gozlem.)"""
    params: Dict[str, str] = {}
    if baslangic:
        params['startPeriod'] = baslangic
    if bitis:
        params['endPeriod'] = bitis
    try:
        return _get(f'data/{AGENCY},{dataflow_id},{version}/{key}', params or None)
    except ExternalError as e:
        if e.status == 404:
            return None
        raise
