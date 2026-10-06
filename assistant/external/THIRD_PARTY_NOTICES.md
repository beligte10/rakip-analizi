# Üçüncü taraf kod bildirimleri

## tuik-mcp

`assistant/external/tuik.py` içindeki SDMX çözümleme fonksiyonları
(`parse_dataflows`, `parse_sdmx_data`, `search_dataflows`, `parse_structure`,
`build_sdmx_key`, `filtre_to_names`, `filter_rows`, `validate_fetch_params`,
`limit_rows`, `resolve_version` ve yardımcıları) aşağıdaki projeden
değiştirilmeden alınmıştır:

- Proje: https://github.com/orhoncan/tuik-mcp (`src/tuik_sdmx_mcp/sdmx.py`)
- Yazar: orhoncan
- Lisans: MIT (projenin README'sinde belirtildiği şekilde)

MIT Lisansı özeti: Yazılım "OLDUĞU GİBİ", hiçbir garanti olmaksızın sağlanır;
telif bildirimi ve bu izin bildirimi yazılımın tüm kopyalarında korunmalıdır.

Proje, TÜİK ile bağlantısı olmayan kişisel bir çalışmadır; çıktıların resmi
bültenlerle doğrulanması önerilir.
