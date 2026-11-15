# Aplikasi Pantau Keramaian SPBU Kota Medan (Mobile Web App)

Aplikasi web mobile Android-friendly bertema **serba putih (clean minimalist)** dengan arsitektur **Frontend & Backend terpisah** untuk mendeteksi SPBU terdekat berbasis GPS pengguna dan menghitung skor keramaian secara real-time.

---

## 📁 Struktur Direktori

```
Scraping Spbu/
├── backend/
│   ├── server.py        # REST API HTTP Server & Static File Server
│   ├── spbu_data.py     # Database SPBU Pertamina terverifikasi di Kota Medan
│   └── scoring.py       # Algoritma multi-indikator objektif (tanpa AI-slop)
│
├── frontend/
│   ├── index.html       # Antarmuka web mobile Android (HTML5 semantik)
│   ├── style.css        # Tema serba putih (pure white, border halus, crisp typography)
│   └── app.js           # Geolocation HTML5, filter, kalkulasi, & dynamic rendering
│
└── spbu_scraper.py      # Script scraper Google Maps live traffic & data SPBU
```

---

## 🧮 Algoritma Perhitungan Skor Keramaian (0 - 100)

Skor dihitung dari 4 variabel objektif:

$$\text{Skor} = (0.35 \times S_{\text{komuter}}) + (0.30 \times S_{\text{koridor}}) + (0.20 \times S_{\text{kapasitas}}) + (0.15 \times S_{\text{dwell}})$$

1. **Waktu Komuter ($S_{\text{komuter}}$, Bobot 35%):**
   * Puncak Pagi (06.45 – 08.45 WIB): Berangkat kerja/sekolah.
   * Puncak Siang (11.45 – 13.45 WIB): Istirahat & mobilitas ojol.
   * Puncak Sore (16.30 – 19.30 WIB): Arus kepulangan komuter.
   * Dini Hari (22.00 – 05.30 WIB): Arus lengang.
2. **Beban Koridor Jalan ($S_{\text{koridor}}$, Bobot 30%):**
   * Mengukur beban jalan (Arteri Primer vs Kolektor vs Sekunder) di depan SPBU.
3. **Kapasitas Pompa & Nozzle ($S_{\text{kapasitas}}$, Bobot 20%):**
   * Rasio jumlah dispenser kendaraan roda 2 dan roda 4. SPBU dengan pompa terbatas di jalur padat memiliki penalti antrean lebih tinggi.
4. **Fasilitas Tenant & Dwell Time ($S_{\text{dwell}}$, Bobot 15%):**
   * Keberadaan minimarket (Indomaret/Alfamart), cafe, dan ATM center yang memperpanjang waktu singgah/parkir kendaraan.

### Kategori Status:
* **0 – 35 (Hijau):** **Sepi / Lancar** (Antrean 0–2 kendaraan, waktu tunggu < 3 menit).
* **36 – 70 (Kuning/Oranye):** **Sedang / Normal** (Antrean 3–6 kendaraan, waktu tunggu 4–8 menit).
* **71 – 100 (Merah):** **Ramai / Padat** (Antrean > 7 kendaraan, waktu tunggu 10–20 menit).

---

## 🚀 Cara Menjalankan Aplikasi

### 1. Jalankan Backend
Buka terminal PowerShell di folder ini, lalu jalankan:
```bash
python backend/server.py
```
Backend akan aktif di `http://localhost:8000` dengan endpoint:
* `GET /api/spbu/nearby?lat=...&lng=...&sort=distance`
* `GET /api/spbu/detail?id=14.201.1151`
* `GET /api/health`

### 2. Buka Aplikasi di Browser / HP Android
* **Di Komputer / Laptop:** Buka browser dan akses [http://localhost:8000](http://localhost:8000).
* **Di HP Android (Jaringan Wi-Fi yang sama):**
  1. Cek alamat IP lokal komputer Anda (misal `192.168.1.x` via perintah `ipconfig`).
  2. Buka Chrome di Android dan akses `http://192.168.1.x:8000`.
  3. Izinkan akses lokasi (GPS) saat diminta browser.
  4. Anda bisa memilih opsi **"Tambahkan ke Layar Utama" (Add to Home screen)** di Chrome Android agar aplikasi berjalan seperti aplikasi native Android.
