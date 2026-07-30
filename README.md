# Kontrol V10 FIX (Premium Coffee Automation & Analysis)

Kontrol V10 FIX, yepyeni **Coffee / Espresso** tasarım diliyle (Karamel, Mocha ve Cream vurguları) yeniden inşa edilmiş, üst düzey bir Instagram Otomasyon, Yorum/Beğeni Kontrol, Token Yönetimi ve Zamanlanmış Arka Plan Otomasyon platformudur. Orijinal Instagram mobil uygulamasının (Android) API başlıklarını, cihaz kimliklerini ve session yönetimini birebir taklit ederek çalışan, son derece kararlı, güvenli ve sinematik estetiğe sahip bir sistemdir.

## 🚀 Proje Ne İşe Yarıyor?
Bu proje, **Instagram yardımlaşma ve etkileşim gruplarını** profesyonel, güvenli ve otomatik bir düzeyde yönetmek için tasarlanmıştır. Üyelerin görevlerini (beğeni/yorum) yapıp yapmadıklarını saniyeler içinde tespit eder ve raporlar.

---

## ✨ Tüm Özellikler (v10 FIX)

### 📊 Ana Denetim Özellikleri
*   **Toplu Beğeni ve Yorum Denetimi:** Birden fazla gönderiyi aynı anda tarar, kimin eksik olduğunu detaylı raporlar.
*   **Kopya Yorum Tespiti:** "Toplu Kontrol" modunda, kullanıcıların farklı postlara aynı (kopyala-yapıştır) yorumu atıp atmadığını otomatik belirler ve uyarır.
*   **DM Grubu Entegrasyonu:** Bağlı hesapların bulunduğu grupları otomatik tespit eder, üye listelerini ve paylaşılan postları anında çeker.
*   **Favori Gruplar:** Sık kullandığınız Instagram gruplarını favoriye ekleyerek listenin en üstünde tutabilirsiniz.
*   **Gelişmiş Muafiyet Yönetimi:** 
    *   **Post Bazlı Muafiyet:** Belirli gönderilerde bazı üyeleri geçici olarak denetim dışı bırakabilirsiniz.
    *   **Global Muafiyet:** Yönetici, moderatör veya VIP üyeleri kalıcı muafiyet listesine ekleyerek tüm kontrollerden muaf tutabilirsiniz.

### 🤖 Gelişmiş Arka Plan Otomasyonu (Auto-Pilot)
*   **Zamanlanmış Otomatik Kontroller:** Günün belirlenen saatlerinde (örneğin 23:59) otomatik olarak dünün paylaşımlarını denetler.
*   **Otomatik Grup Bildirimi:** Eksik listesini ve önceden hazırlanan etiket şablonunu otomatik olarak DM grubuna gönderir.
*   **Eksiklere Bireysel DM:** Görevini yapmayan kullanıcılara otomatik olarak tek tek uyarı DM'si gönderir.
*   **Yönetici Raporu:** İşlem tamamlandığında yönetici hesabına detaylı başarı/eksik durum raporunu otomatik olarak iletir.
*   **Canlı Test Modu (Live Test):** Mesaj göndermeksizin otomasyonun nasıl çalışacağını test etmek için canlı simülasyon başlatabilirsiniz.

### 🔑 Token ve Cihaz Yönetimi
*   **Çoklu Hesap Desteği (Token Pool):** Sisteme birden fazla Instagram hesabı ekleyebilir ve bunları havuz olarak kullanabilirsiniz.
*   **Akıllı Yeniden Giriş (Auto-Relogin):** Oturumu düşen veya şifresiyle yeniden girilmesi gereken hesapları tek tıkla admin panelinden güncelleyebilirsiniz.
*   **Toplu İçe/Dışa Aktarma:** Hesaplarınızı JSON veya CSV formatında toplu olarak sisteme yükleyebilir ya da yedekleyebilirsiniz.
*   **Cihaz Simülasyonu:** Her hesap için benzersiz Android Cihaz Kimliği (Android ID), Device ID ve User Agent tanımlayarak Instagram radarına takılmayı önler.

### 🛡️ Güvenlik ve Kararlılık
*   **Doğrulama Destekli Failover Mekanizması:** Sorgular sırasında `403` veya `401` hatası alındığında, token'ın gerçekten ölü olup olmadığını test eder. Gerçekten ölü değilse (özel post/geçici limit durumu) hesabı kapatmaz ve diğer yedek hesaba geçerek sorguyu tamamlar.
*   **Geri Alma (Unsend) Desteği:** Botun DM grubuna attığı eksik listesi mesajlarını tek tıklamayla Instagram sunucularından geri alabilir/silebilirsiniz.
*   **İşlem Günlüğü (Audit Logs):** Sistemde manuel veya otomatik yapılan tüm kontrolleri, relogin işlemlerini saniye saniye takip edebilirsiniz.

### 🎨 Premium UI/UX (Coffee Theme)
*   **Coffee / Espresso Design:** Saf, şık kahve tonları (`--accent-caramel`, `--accent-mocha`) kullanılarak baştan aşağı yenilenen lüks bir deneyim.
*   **Sinematik Animasyonlar:** Sayfalar arası geçişlerde ve "Kontrol Et" bekleme anlarında devreye giren 1.5 saniyelik harika bulanıklık (blur) ve fade-in efektleriyle gerçek bir SPA hissi.
*   **Zarif Etkileşimler:** Grup ve paylaşım seçimi yapıldığında ekranda oluşan göz yormayan, kısa süreli bulanıklık efektleri.
*   **Tasarım Ayarları:** Sıvı cam (Liquid Glass) efekti ve Swipe Navigasyonu gibi özellikleri admin panelinden açıp kapatabilirsiniz.

---

## 🛠️ Kurulum

### Tek Komutla Kurulum (Linux/Bash/PythonAnywhere)
```bash
bash -c "$(curl -sL https://raw.githubusercontent.com/seghobs/kontrolv10-fix/main/setup.sh)"
```

### Manuel Kurulum
```bash
git clone https://github.com/seghobs/kontrolv10-fix.git kontrol
cd kontrol
pip install -r requirements.txt
python flask_app.py
```

---

## 💻 Kullanım
Sunucu veya lokal makinede projeyi başlattıktan sonra:

**Ana Kontrol Paneli:**
```text
http://localhost:5000
```

**Admin Paneli (Token, Otomasyon & Muafiyetler):**
```text
http://localhost:5000/admin
```

---

## 📁 Proje Yapısı
-   `flask_app.py`: Uygulamanın giriş noktası.
-   `log_in.py`: Instagram Bloks giriş taklit motoru.
-   `app_core/`: Sistemin mantıksal çekirdeği (Routes, API, Storage, Automation).
-   `static/css/`: Coffee/Karamel tabanlı modernize edilmiş UI stil dosyaları.
-   `static/js/`: Dinamik arama, sinematik geçişler, sürükle-bırak ve favorileme mantığı.
-   `templates/`: Animasyonla yüklenen, akıcı Jinja2 HTML şablonları.

---

## 🔒 Güvenlik Notu
Bu proje eğitim ve analiz amaçlıdır. Instagram kullanım koşullarına uygun şekilde kullanılması kullanıcının sorumluluğundadır. Verileriniz yerel bir SQLite veritabanında (`app.db`) güvenli şekilde saklanır.
