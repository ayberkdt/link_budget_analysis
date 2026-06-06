# UZB451 Uzay Aracı Haberleşmesi Dönem Projesi
### GEO Uydu Hat Bütçesi Analizi (GEO Satellite Link Budget Analyzer)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Standards](https://img.shields.io/badge/standards-ITU--R%20P.618%20%7C%20P.838%20%7C%20P.676-orange.svg)](https://www.itu.int/)
[![Academic Baseline](https://img.shields.io/badge/MATLAB-Comparable-green.svg)](https://www.mathworks.com/)

---

## 🇹🇷 Türkçe Proje Özeti
Bu proje, **UZB451 Uzay Aracı Haberleşmesi (Spacecraft Communications)** dersi dönem ödevi için geliştirilmiş bir uydu hat bütçesi (link budget) analiz kodudur. Odak noktası, geosenkron yörüngedeki (GEO) şeffaf aktarıcılı (bent-pipe) bir uydunun bağlantı analizini yapmaktır.

Hesaplamalar MATLAB'deki Link Budget Analyzer (P.618 kapalı hali) referans alınarak yapılmıştır. Dönem ödevinin temel isterleri olan statik hat bütçesi ve 2 boyutlu kontur grafikleri MATLAB ile birebir uyumludur. Ek olarak; girişim analizi (ASI/IMD), Monte-Carlo yağış analizi, ITU-R yayılım sönümlemeleri ve DVB-S2 ACM gibi ileri seviye haberleşme konseptleri opsiyonel ekstra modüller olarak kodlanmıştır.

---

## 🇬🇧 English Overview
This is a link budget analysis tool developed for the **UZB451 Spacecraft Communications** term project. It calculates the clear-sky static link budget for a geostationary bent-pipe satellite.

The core calculations match the **MATLAB "Static Link Budget Analyzer" (with P.618 losses disabled)**, which is the required academic baseline for the course. Several advanced engineering concepts such as adjacent satellite interference (ASI), Monte-Carlo rain outage simulation, ITU-R slant-path propagation, and DVB-S2 ACM have been added as optional extra modules.

---

## 🚀 Proje Modülleri ve Kapsamı

| Modül / Özellik | Konfigürasyon | Açıklama | Durum |
|---|---|---|---|
| **Açık Hava Statik Hat Bütçesi** | *Daima Aktif* | MATLAB ile uyumlu, yağış/atmosfer kaybı içermeyen temel hat bütçesi (yönelim, polarizasyon vb. dahil). | **Zorunlu İster** |
| **2B Kontur Grafikleri** | *Daima Aktif* | C/N, Eb/N0 ve marj değerlerini frekans, güç ve anten çapına göre inceleyen kontur grafikleri. | **Zorunlu İster** |
| **Girişim (Interference) Analizi** | `INTERFERENCE` | Komşu uydu girişimi (ASI) ve intermodülasyon bozulması (IMD) hesapları. | **[Ekstra]** |
| **Dijital Metrikler** | `DIGITAL` | Çeşitli modülasyonlar için BER eğrileri, Shannon-Hartley limiti ve kanal kodlama (FEC) kazancı. | **[Ekstra]** |
| **Dinamik GS2 Gürültüsü** | `DYNAMIC_NOISE` | Yükseklik açısı (elevation) ve yağış sönümlemesine bağlı yer alıcısı gürültü sıcaklığı ($T_{sys}$) hesabı. | **[Ekstra]** |
| **Yörünge Hareketi (Apparent Motion)**| `APPARENT_MOTION` | Uydunun istasyon tutma (station-keeping) toleranslarından kaynaklı yörünge salınımı simülasyonu. | **[Ekstra]** |
| **Monte-Carlo Yağış Analizi** | `RAIN_OUTAGE` | Rastgele hava durumu profilleri üreterek yıllık kesinti (outage) sürelerini hesaplayan simülasyon. | **[Ekstra]** |
| **ITU-R Yayılım Modelleri** | `ITU_PROPAGATION` | P.618/P.676/P.840 standartlarına göre detaylı yağış, gaz, bulut ve sintilasyon kayıpları. | **[Ekstra]** |
| **DVB-S2 ACM Seçimi** | `MODCOD` | ITU kayıpları altındaki anlık sinyal/gürültü oranına göre en verimli DVB-S2 modülasyonunun otomatik seçimi. | **[Ekstra]** |

---

## 📁 Dosya Yapısı

```text
├── src/                # Python kaynak kodları
│   ├── main.py         # Ana çalıştırıcı (girdileri okur, analizleri çalıştırır ve çıktıları kaydeder)
│   ├── calculations.py # RF geometri, hat bütçesi ve simülasyon hesaplamaları
│   ├── constants.py    # Fiziksel sabitler ve birim dönüştürücüler
│   ├── entities.py     # Veri yapıları (dataclass tanımları)
│   ├── itu_propagation.py # ITU-R P.838/839/618/676/840 yayılım sönümleme (attenuation) modelleri
│   ├── modcod.py       # DVB-S2 MODCOD tablosu ve adaptif modülasyon (ACM) seçimi
│   ├── plotting.py     # Rapor için grafik çizim rutinleri (Matplotlib)
│   └── scenario_inputs.py # Uydu, yer istasyonları ve link parametrelerinin girildiği ana konfigürasyon dosyası
├── LaTeX Rapor/        # Akademik rapor şablonu (LaTeX)
├── requirements.txt    # Gerekli Python kütüphaneleri (numpy, matplotlib)
└── README.md           # Proje açıklaması
```

---

## 🛠️ Kurulum ve Kullanım

Projeyi çalıştırmak için **Python 3.10+** ile birlikte `numpy` ve `matplotlib` kütüphanelerine ihtiyacınız vardır.

### 1. Kurulum
```bash
git clone https://github.com/ayberkdt/link_budget_analysis.git
cd link_budget_analysis
pip install -r requirements.txt
```

### 2. Çalıştırma Seçenekleri
Komut satırı argümanları ile projenin sadece belirli kısımlarını veya tamamını çalıştırabilirsiniz:

```bash
# Aktif edilmiş tüm analizleri ve grafikleri çalıştır
python src/main.py

# Grafik çizmeyi atla, sadece CSV çıktılarını üret (daha hızlı çalışır)
python src/main.py --skip-plots

# Sadece zorunlu olan MATLAB uyumlu açık hava statik hat bütçesini çalıştır
python src/main.py --static-only

# Statik hat bütçesini çalıştırıp sadece CSV olarak kaydet
python src/main.py --static-only --skip-plots
```

---

## 📝 Parametreleri Değiştirme
Projeye ait tüm girdiler `src/scenario_inputs.py` dosyasında yer alır. Koordinatları, frekansları, güçleri, anten çaplarını değiştirmek veya ekstra analizleri açıp kapatmak için bu dosyayı düzenleyebilirsiniz:

```python
# src/scenario_inputs.py örneği
GS1 = {
    "site_name": "GS1 Istanbul",
    "latitude_deg": 41.0082,
    "longitude_deg": 28.9784,
    "antenna_diameter_m": 2.4, # Yer anteni çapı (m)
    "tx_power_w": 20.0,        # HPA gönderim gücü (W)
    ...
}
```

---

## 📊 Çıktılar
Kod çalıştıktan sonra tüm tablosal veriler `outputs/` klasörüne CSV formatında kaydedilir. Çizdirilen grafikleri ise raporlarda kullanılabilmesi için `outputs/plots/` klasörüne hem yüksek çözünürlüklü **PNG** hem de vektörel **PDF** olarak çıkarılır.

### Temel Statik Çıktılar:
*   `outputs/geometry_static.csv` — Geometrik hesaplamalar (mesafe, yükseklik ve azimut açıları).
*   `outputs/link_budget_static.csv` — Uplink ve downlink açık hava hat bütçesi detayları.
*   `outputs/scenario_summary_static.csv` — Uçtan uca birleştirilmiş (end-to-end) hat bütçesi sonuçları.

### Çizdirilen Kontur Grafikleri (`outputs/plots/`):
*   **01_downlink_cn0_dish_vs_frequency** — Downlink $C/N_0$ vs GS2 anten çapı ve frekans.
*   **02_downlink_margin_eirp_vs_tsys** — Uydu EIRP ve yer istasyonu gürültü sıcaklığına bağlı sistem marjı.
*   **03_uplink_cn_power_vs_dish** — Uplink $C/N$ vs HPA gücü ve anten çapı.
*   **04_total_ebn0_bitrate_vs_bandwidth** — Uçtan uca $E_b/N_0$, bit hızı ve bant genişliği.
*   **05_gs2_elevation_latitude_vs_longitude** — GS2 konumlarına göre yükseklik (elevation) haritası.

---

## ⚠️ Akademik Not
*   Bu araç **UZB451 Spacecraft Communications** dersi için eğitim amaçlı geliştirilmiştir.
*   Hat tasarımı hesaplamaları **Pratt - Satellite Communications** kitabının Bölüm 4'ünde anlatılan metodolojiye dayanmaktadır.
*   `src/scenario_inputs.py` içerisindeki varsayılan parametreler örnektir, kendi analiziniz için gerçek değerlerle değiştirmeyi unutmayın.
