# Python 3.10 slim tabanlı bir imaj kullan
FROM python:3.10-slim

# Ortam değişkenleri (log formatı ve cache için)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Çalışma dizini oluştur
WORKDIR /app

# Gerekli dosyaları kopyala
COPY requirements.txt .

# Gereksinimleri yükle
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Uygulama 5000 portunu kullanıyor
EXPOSE 5000

# Flask uygulamasını başlat
CMD ["python", "app.py"]
