# Advanced GEO Satellite Link Budget Analyzer (V5)
### UZB451 Spacecraft Communications Term Project

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Standards](https://img.shields.io/badge/standards-ITU--R%20P.618%20%7C%20P.838%20%7C%20P.676-orange.svg)](https://www.itu.int/)
[![Academic Baseline](https://img.shields.io/badge/MATLAB-Comparable-green.svg)](https://www.mathworks.com/)

---

## 🇹🇷 Türkçe Proje Özeti
Bu proje, **UZB451 Uzay Aracı Haberleşmesi (Spacecraft Communications)** dersi dönem ödevi kapsamında geliştirilmiş, geosenkron yörüngedeki (GEO) şeffaf aktarıcılı (bent-pipe) bir haberleşme uydusunun hat bütçesini (link budget) analiz eden profesyonel bir Python paketidir. 

Ödevin zorunlu isterleri olan **Açık Hava Statik Hat Bütçesi** ve **2 Boyutlu Kontur Grafikleri** MATLAB entegrasyonuyla birebir uyumlu çalışırken; projenin akademik derinliğini artırmak adına **Girişim Analizi (ASI/IMD)**, **Dinamik Gürültü Sıcaklığı**, **Yörünge Hareketi Simülasyonu (GEO Motion)**, **Monte-Carlo Yağış Analizi**, **ITU-R Yayılım Sönümlemeleri (P.618/P.676/P.840)** ve **DVB-S2 Adaptif Kodlama/Modülasyon (ACM)** gibi birçok ileri düzey mühendislik modülü **[EXTRA]** olarak projeye dahil edilmiştir.

---

## 🇬🇧 English Overview
This repository provides a transparent, standards-compliant Python workflow for the **UZB451 Spacecraft Communications** term project. It computes a clear-sky static link budget for a geostationary bent-pipe link and incorporates advanced engineering layers (interference, digital metrics, dynamic noise, apparent satellite motion, Monte-Carlo rain outages, ITU-R slant-path propagation availability, and DVB-S2 adaptive coding and modulation).

The core static budget is mathematically matched to the **MATLAB "Static Link Budget Analyzer" with P.618 losses disabled**, serving as the exact academic baseline.

---

## 🚀 Key Features & Analysis Layers

| Module / Layer | Mode Flag | Description / TR Karşılığı | Status |
|---|---|---|---|
| **Clear-Sky Static Link Budget** | *Always On* | MATLAB karşılaştırılabilir açık hava statik hat bütçesi (yönelim, polarizasyon, sabit atmosfer kayıpları). | **Compulsory / Zorunlu** |
| **2D Contour Plots** | *Always On* | C/N, Eb/N0, marj gibi değerleri frekans, güç ve anten çapına göre analiz eden 6 adet 2B kontur grafiği. | **Compulsory / Zorunlu** |
| **Interference Analysis** | `INTERFERENCE` | Komşu uydu girişimi (ASI - Adjacent Satellite Interference) ve intermodülasyon bozulması (IMD). | **[EXTRA] Optional** |
| **Digital Layer Metrics** | `DIGITAL` | Modülasyona göre BER (bit hata oranı) eğrileri, Shannon-Hartley kanal kapasitesi limiti ve kodlama kazancı (FEC). | **[EXTRA] Optional** |
| **Dynamic GS2 Noise** | `DYNAMIC_NOISE` | Yükseklik açısı (elevation) ve yağış sönümlemesine bağlı yer alıcısı gürültü sıcaklığı ($T_{sys}$) modeli. | **[EXTRA] Optional** |
| **Apparent GEO Motion** | `APPARENT_MOTION` | Uydunun yörüngede istasyon tutma (station-keeping) salınımlarını simüle eden zamana bağlı konum analizi. | **[EXTRA] Optional** |
| **Monte-Carlo Rain Outage** | `RAIN_OUTAGE` | Rastgele hava durumu üreterek yıllık kesinti sürelerini simüle eden stochastic weather generator. | **[EXTRA] Optional** |
| **ITU-R Slant-Path Propagation** | `ITU_PROPAGATION` | ITU-R P.618/P.676/P.840 standartlarına göre yağış, gaz, bulut ve sintilasyon sönümlemeleri. | **[EXTRA] Optional** |
| **DVB-S2 ACM Selection** | `MODCOD` | ITU sönümlemesi altındaki aşağı hatta en uygun DVB-S2 modülasyonunun (MODCOD) dinamik seçimi. | **[EXTRA] Optional** |

---

## 📁 File Structure & Project Architecture

```text
├── scenario_inputs.py  # Düzenlenebilir yer istasyonları (GS1/GS2), uydu, frekans ve kayıp girdileri
├── constants.py        # Fiziksel sabitler, birim dönüştürücüler ve ortak mühendislik sabitleri (DRY)
├── entities.py         # Konum, anten, bağlantı ve sonuçlar için kullanılan Python dataclass yapıları
├── calculations.py     # Geometri, RF bütçesi, girişim, dijital kapasite ve simülasyon hesaplamaları
├── itu_propagation.py  # ITU-R P.838 / P.839 / P.618 / P.676 / P.840 slant-path sönümleme modelleri
├── modcod.py           # DVB-S2 MODCOD tablosu ve adaptif kodlama/modülasyon (ACM) mekanizması
├── plotting.py         # Yüksek çözünürlüklü 2D kontur çizimleri ve ileri seviye simülasyon grafikleri
├── main.py             # Giriş noktası (Girdileri doğrular, modülleri çalıştırır, CSV ve grafikleri kaydeder)
├── requirements.txt    # Gerekli kütüphaneler (numpy, matplotlib)
└── .gitignore          # Derlenmiş dosyaları ve çıktıları (results/) git dışı tutan ayarlar
```

---

## 🛠️ Installation & Usage

This project requires **Python 3.10+** and two standard libraries: `numpy` and `matplotlib`.

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/ayberkdt/link_budget_analysis.git
cd link_budget_analysis
pip install -r requirements.txt
```

### 2. Run the Analyzer
You can run the full suite or restrict execution using command-line arguments:

```bash
# Run all enabled advanced analyses and generate all plots
python main.py

# Write CSV outputs only, skipping plot generation (quicker execution)
python main.py --skip-plots

# Run ONLY the clear-sky static baseline (MATLAB-comparable, P.618 losses off)
python main.py --static-only

# Clear-sky static baseline with CSV output only
python main.py --static-only --skip-plots
```

---

## 📝 Where to Edit Scenario Inputs
All project inputs are centralized inside [scenario_inputs.py](file:///c:/Users/ayber/Desktop/Spacecraft%20Communication%20Proje/V5/scenario_inputs.py). You can update coordinates, frequencies, transmitter power, dish diameters, and enable/disable advanced features:

```python
# scenario_inputs.py (Example)
GS1 = {
    "site_name": "GS1 Istanbul",
    "latitude_deg": 41.0082,
    "longitude_deg": 28.9784,
    "antenna_diameter_m": 2.4, # Yer anteni çapı
    "tx_power_w": 20.0,         # Gönderim gücü (Watts)
    ...
}
```

---

## 📊 Outputs & Reports
After execution, all data tables are written to `results/` as CSV files, and all figures are saved in `results/plots/` as high-resolution **PNG** (for quick preview) and **PDF** (for LaTeX/Word report insertion):

### Core Static Baseline Files:
*   `geometry_static.csv` — Slant range, elevation, azimuth, and central angles.
*   `link_budget_static.csv` — Complete uplink and downlink clear-sky metrics.
*   `scenario_summary_static.csv` — Combined end-to-end link budget.

### Generated Contour Plots (Always produced):
*   **01_downlink_cn0_dish_vs_frequency** — Downlink $C/N_0$ vs GS2 dish diameter and frequency.
*   **02_downlink_margin_eirp_vs_tsys** — Margin map showing the $0$ dB closure line.
*   **03_uplink_cn_power_vs_dish** — Uplink $C/N$ vs HPA power and dish size.
*   **04_total_ebn0_bitrate_vs_bandwidth** — End-to-end $E_b/N_0$ with required thresholds.
*   **05_gs2_elevation_latitude_vs_longitude** — GS2 elevation map with low-elevation constraints.

---

## ⚠️ Academic Integrity & Disclaimer
*   This tool is developed for educational purposes in the **UZB451 Spacecraft Communications** course.
*   It is structured based on the Link Design Procedure in **Chapter 4 of Pratt's *Satellite Communications*** textbook.
*   Default parameters in `scenario_inputs.py` are illustrative examples. Users should replace them with real datasheet values and cite their sources accordingly in their final reports.
