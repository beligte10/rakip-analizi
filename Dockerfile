# KT Stratejik Kokpit — Docker imajı
#
# Tamamen yerelde çalışır, harici bir servise (Hugging Face vb.) bağımlılığı yok.
#
# Build & çalıştır (KT_USERNAME/KT_PASSWORD ZORUNLU — image'da varsayılan
# YOK, bkz. aşağıdaki not):
#   docker build -t kt-cockpit .
#   docker run -p 7860:7860 -e KT_USERNAME=... -e KT_PASSWORD=... kt-cockpit
#   → http://localhost:7860
#
# Veriyi konteyner dışında kalıcı tutmak isterseniz volume mount edin:
#   docker run -p 7860:7860 -v "$(pwd)/data:/app/data" -e KT_USERNAME=... -e KT_PASSWORD=... kt-cockpit

FROM python:3.11-slim

# Sistem bağımlılıkları (pandas/pyarrow için minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Önce requirements'ı kopyala — Docker layer cache için
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kalan dosyaları kopyala
COPY app.py .
COPY users.py .
COPY pipeline/ pipeline/
COPY frontend/ frontend/
COPY scripts/ scripts/

# NOT (2026-08-15): `data/` KASITLI OLARAK image'a kopyalanmıyor.
# - Deploy'da data/ kalıcı bir volume'dan bağlanır (bind-mount image içeriğini
#   zaten tamamen gölgeler → COPY işe yaramazdı).
# - COPY data/ image'ı onlarca MB şişirir ve eski bir veri snapshot'ı taşırdı.
# - Sırlar (users.json, .session_secret) .dockerignore'da; onlar hiç girmiyor.
# İlk kurulumda data/ içeriği (catalog.json, veriler.parquet, computed.json,
# users.json, .session_secret ...) sunucudaki volume'a rsync/scp ile taşınır.

EXPOSE 7860

# KT_USERNAME/KT_PASSWORD burada KASITLI OLARAK set edilmiyor — image'a
# gömülen bir varsayılan şifre, `docker run` sırasında unutulsa bile herkese
# açık kalır (bkz. app.py'nin kendi 'faruk'/'faruk123' fallback'i — o da
# aynı nedenle sadece yerel geliştirme içindir, deploy'da MUTLAKA -e ile
# override edilmeli). PORT dışında sır olmayan tek env burada kalıyor.
ENV PORT=7860

# Uvicorn ile çalıştır
CMD ["python", "app.py"]
