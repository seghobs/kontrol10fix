#!/bin/bash

# Kontrol Project Auto Setup - Tek Komutla Kurulum
# Kullanim: bash -c "$(curl -sL https://raw.githubusercontent.com/seghobs/kontrol-v12-no-error/main/setup.sh)"

echo "========================================="
echo "Kontrol Projesi Otomatik Kuruluyor..."
echo "========================================="

# Mevcut mysite klasorunu temizle ve yedekle
if [ -d "mysite" ]; then
    echo "Mysite klasoru temizleniyor ve yedekleniyor..."
    mv mysite mysite_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null
fi

# Projeyi GitHub'dan indir
echo "Proje indiriliyor..."
rm -rf mysite 2>/dev/null
git clone https://github.com/seghobs/kontrol-v12-no-error.git mysite

if [ ! -d "mysite" ]; then
    echo "HATA: Proje indirilemedi!"
    exit 1
fi

cd mysite

# PythonAnywhere veya Linux sistemi kontrolü
if command -v pip3 &> /dev/null; then
    echo "Pip bulundu, paketler yukleniyor..."
    pip3 install -r requirements.txt 2>/dev/null || pip install -r requirements.txt 2>/dev/null
fi

# Dosya izinleri
echo "Izinler ayarlaniyor..."
chmod -R 755 .
chmod -R 777 data/ logs/ 2>/dev/null
chmod 777 *.json 2>/dev/null
chmod 777 *.db 2>/dev/null

# .env dosyasi kontrolu
if [ ! -f ".env" ]; then
    echo ".env dosyasi olusturuluyor..."
    echo "SECRET_KEY=kontrol_secret_key_$(date +%s)" > .env
fi

# Veritabani klasoru kontrolu
mkdir -p data logs

echo ""
echo "========================================="
echo "Kurulum TAMAMLANDI!"
echo "========================================="
echo ""
echo "Projeyi baslatmak icin:"
echo "  cd mysite"
echo "  python flask_app.py"
echo ""
echo "Veya tek komutla:"
echo "  cd mysite && python flask_app.py"
echo ""
