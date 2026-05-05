# industrial-data-pipeline-dashboard

🏭 Endüstriyel Veri Hattı & Analitik Dashboard
Bu proje, bir üretim tesisindeki (Smart Factory) yüksek hacimli üretim ve stok verilerini otomatik olarak çeken, temizleyen ve AWS Redshift’e aktaran bir ETL sistemi ile birlikte, teknik ekiplerin veriyi kolayca inceleyebileceği interaktif bir dashboard’dan oluşuyor.
Projenin Çözdüğü Sorunlar

Veriler farklı ağ klasörlerinde dağınık halde duran Excel ve CSV dosyaları tek bir yerde (Redshift) toplanıyordu.
Her saat başı verileri manuel olarak çekme, temizleme ve yükleme işi oldukça zaman alıyordu ve hata riski yüksekti.
Büyük dosyalar işlenirken RAM sorunu yaşıyorduk.
Hassas bilgiler (sunucu adresleri, şifreler vb.) kodun içinde kalıyordu.

Teknik Mimari
1. Otonom ETL Hattı (main.py)

APScheduler ile her saat başı otomatik çalışacak şekilde zamanladım.
Pandas ve regex kullanarak verileri temizliyor (hatalı karakterler, boş satırlar vs.).
Redshift’e yüklerken önce Temp Table’a atıp ardından UPSERT (Merge) işlemiyle tekrar eden kayıtları engelliyor.

2. İnteraktif Dashboard (dashboard.py)

Streamlit ile geliştirildi.
Üretim miktarı, hata oranları, parça bazlı özetler gibi KPI’ları gösteriyor.
Altair ile zaman bazlı trend grafikleri ve dağılım grafikleri var.
Üretim adımı, varyant ve tarih filtreleriyle veriyi rahatça inceleyebiliyorsunuz.

Kurulum ve Çalıştırma

Depoyu klonlayın:Bashgit clone https://github.com/ammarsonmez/industrial-data-pipeline.git
cd industrial-data-pipeline
Gereksinimleri yükleyin:Bashpip install -r requirements.txt
Dashboard’u çalıştırın:Bashstreamlit run dashboard.py
ETL servisini başlatın:Bashpython main.py

Güvenlik Notu
Kurumsal ağ yolları, sunucu adresleri ve bazı hassas bilgiler gizlilik nedeniyle anonimleştirilmiştir. Veritabanı bağlantıları .streamlit/secrets.toml dosyası üzerinden yönetiliyor.
Bu proje, Schaeffler stajı sırasında edindiğim tecrübelerle geliştirdiğim, gerçek üretim ortamı ihtiyaçlarına göre tasarlanmış bir sistem.
