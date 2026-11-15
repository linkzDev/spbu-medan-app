/**
 * SPBU Medan - Real Geocoding & Crowd Detection Engine
 * Pure Vanilla JavaScript, Zero Slop
 */

const API_BASE_URL = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
  ? window.location.origin
  : "http://localhost:8000";

// State Global
let appState = {
  userLat: 3.5686725,
  userLng: 98.7086462,
  userCity: "Kota Medan",
  userDistrict: "Medan Area",
  userRoad: "Jl. Menteng Raya",
  selectedDistrict: "all",
  topDistricts: [],
  spbuData: [],
  currentSort: "distance", // "distance" | "score_asc" | "all"
  searchQuery: "",
  isRealGps: false
};

// DOM Elements
const elGpsStatus = document.getElementById("gps-status-text");
const elCityDistrict = document.getElementById("location-city-district");
const elLocationRoad = document.getElementById("location-road");
const elLocationCoords = document.getElementById("location-coords");
const elCurrentClock = document.getElementById("current-clock");
const elDistrictChips = document.getElementById("district-chips");
const elSpbuList = document.getElementById("spbu-list");
const elTotalCount = document.getElementById("total-spbu-count");
const elQuietCount = document.getElementById("quiet-spbu-count");
const elMediumCount = document.getElementById("medium-spbu-count");
const elBtnRefresh = document.getElementById("btn-refresh");
const elSearchInput = document.getElementById("search-input");

// Modal Elements
const elModalBackdrop = document.getElementById("modal-backdrop");
const elBtnCloseModal = document.getElementById("btn-close-modal");
const elModalSpbuName = document.getElementById("modal-spbu-name");
const elModalSpbuCode = document.getElementById("modal-spbu-code");
const elModalScore = document.getElementById("modal-score");
const elModalStatusBadge = document.getElementById("modal-status-badge");
const elModalWaitEstimate = document.getElementById("modal-wait-estimate");
const elModalRoadDist = document.getElementById("modal-road-dist");
const elBarTime = document.getElementById("bar-time");
const elDescTime = document.getElementById("desc-time");
const elBarTraffic = document.getElementById("bar-traffic");
const elDescTraffic = document.getElementById("desc-traffic");
const elBarPump = document.getElementById("bar-pump");
const elDescPump = document.getElementById("desc-pump");
const elBarFacility = document.getElementById("bar-facility");
const elDescFacility = document.getElementById("desc-facility");
const elModalFacilities = document.getElementById("modal-facilities");
const elModalFuels = document.getElementById("modal-fuels");
const elModalRouteBtn = document.getElementById("modal-route-btn");

document.addEventListener("DOMContentLoaded", () => {
  initClock();
  setupEventListeners();
  requestUserGPS();
});

function initClock() {
  function updateTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    elCurrentClock.textContent = `${hours}:${minutes} WIB`;
  }
  updateTime();
  setInterval(updateTime, 10000);
}

function setupEventListeners() {
  elBtnRefresh.addEventListener("click", () => {
    fetchSPBUData();
  });

  elSearchInput.addEventListener("input", (e) => {
    appState.searchQuery = e.target.value.toLowerCase().trim();
    renderSPBUCards();
  });

  // Sort Tabs
  document.getElementById("tab-nearest").addEventListener("click", (e) => {
    setActiveTab(e.target);
    appState.currentSort = "distance";
    fetchSPBUData();
  });

  document.getElementById("tab-quietest").addEventListener("click", (e) => {
    setActiveTab(e.target);
    appState.currentSort = "score_asc";
    fetchSPBUData();
  });

  document.getElementById("tab-all").addEventListener("click", (e) => {
    setActiveTab(e.target);
    appState.currentSort = "all";
    fetchSPBUData();
  });

  // Modal Close
  elBtnCloseModal.addEventListener("click", closeModal);
  elModalBackdrop.addEventListener("click", (e) => {
    if (e.target === elModalBackdrop) closeModal();
  });
}

function setActiveTab(clickedBtn) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  clickedBtn.classList.add("active");
}

// Minta Izin GPS HP Android
function requestUserGPS() {
  elGpsStatus.textContent = "Mendeteksi Posisi Riil GPS...";

  if ("geolocation" in navigator) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        appState.userLat = position.coords.latitude;
        appState.userLng = position.coords.longitude;
        appState.isRealGps = true;
        elGpsStatus.textContent = "GPS Aktif & Terkunci";
        fetchSPBUData();
      },
      (error) => {
        console.warn("GPS ditolak atau gagal:", error.message);
        elGpsStatus.textContent = "GPS Tidak Diizinkan (Gunakan Preset)";
        fetchSPBUData();
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
    );
  } else {
    elGpsStatus.textContent = "GPS tidak didukung perangkat";
    fetchSPBUData();
  }
}

// Fetch Data SPBU Riil & Resolusi Wilayah Administratif
async function fetchSPBUData() {
  elSpbuList.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Mengambil data administratif riil & kalkulasi jarak rute jalan...</p>
    </div>
  `;

  try {
    let sortParam = "distance";
    if (appState.currentSort === "score_asc") sortParam = "score_asc";

    const districtParam = appState.selectedDistrict !== "all" ? `&district=${encodeURIComponent(appState.selectedDistrict)}` : "";
    const url = `${API_BASE_URL}/api/spbu/nearby?lat=${appState.userLat}&lng=${appState.userLng}&sort=${sortParam}${districtParam}`;
    
    const resp = await fetch(url);
    const data = await resp.json();

    if (data.success) {
      // 1. Update info lokasi administratif riil
      const loc = data.user_location;
      appState.userCity = loc.city || "Kota Medan";
      appState.userDistrict = loc.district || "Medan Area";
      appState.userRoad = loc.road || "Jalan Utama";

      elCityDistrict.textContent = `${appState.userCity} • ${appState.userDistrict}`;
      elLocationRoad.textContent = `📍 Berada di sekitar: ${appState.userRoad}`;
      elLocationCoords.textContent = `Lat: ${loc.latitude.toFixed(5)}, Lng: ${loc.longitude.toFixed(5)}`;

      // 2. Render Top Kecamatan Terdekat
      if (Array.isArray(data.top_nearby_districts)) {
        appState.topDistricts = data.top_nearby_districts;
        renderDistrictChips();
      }

      // 3. Render List SPBU
      appState.spbuData = data.spbu_list || [];
      updateMetrics(appState.spbuData);
      renderSPBUCards();
    } else {
      showError("Gagal memuat data dari server.");
    }
  } catch (err) {
    console.error("API Error:", err);
    showError("Gagal terhubung ke Backend. Pastikan 'python backend/server.py' aktif.");
  }
}

// Render Top Kecamatan Terdekat (Slider Horizontal Geser Kiri-Kanan)
function renderDistrictChips() {
  const allActive = appState.selectedDistrict === "all" ? "active" : "";
  let html = `
    <button class="dist-chip ${allActive}" onclick="selectDistrict('all', this)">
      <span>Semua Kecamatan</span>
      <span class="dist-chip-dist">${appState.spbuData.length || 11}</span>
    </button>
  `;

  appState.topDistricts.forEach((dist) => {
    const isCurrent = dist.is_current;
    const isActive = appState.selectedDistrict.toLowerCase() === dist.name.toLowerCase() ? "active" : "";
    const icon = isCurrent ? "📍 " : "";
    const distText = dist.distance_km < 0.2 ? "Di sini" : `${dist.distance_km} km`;
    const countBadge = dist.spbu_count > 0 ? `• ${dist.spbu_count} SPBU` : "";

    html += `
      <button class="dist-chip ${isActive}" onclick="selectDistrict('${dist.name}', this)">
        <span>${icon}Kec. ${dist.name}</span>
        <span class="dist-chip-dist">${distText} ${countBadge}</span>
      </button>
    `;
  });

  elDistrictChips.innerHTML = html;
}

window.selectDistrict = function(districtName, element) {
  appState.selectedDistrict = districtName;
  if (element && element.scrollIntoView) {
    element.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  }
  renderDistrictChips();
  fetchSPBUData();
};

function updateMetrics(list) {
  elTotalCount.textContent = list.length;
  const quiet = list.filter(item => item.crowd.status === "Sepi").length;
  const medium = list.filter(item => item.crowd.status === "Sedang").length;
  elQuietCount.textContent = quiet;
  elMediumCount.textContent = medium;
}

// Render Kartu-Kartu SPBU
function renderSPBUCards() {
  let filtered = [...appState.spbuData];

  if (appState.searchQuery) {
    filtered = filtered.filter(item => 
      item.name.toLowerCase().includes(appState.searchQuery) ||
      item.address.toLowerCase().includes(appState.searchQuery) ||
      item.district.toLowerCase().includes(appState.searchQuery) ||
      item.id.toLowerCase().includes(appState.searchQuery) ||
      item.fuel_types.some(f => f.toLowerCase().includes(appState.searchQuery))
    );
  }

  if (filtered.length === 0) {
    elSpbuList.innerHTML = `
      <div class="empty-state">
        <p>Tidak ditemukan SPBU di kecamatan atau kriteria pencarian ini.</p>
        <button class="btn-secondary" onclick="selectDistrict('all')" style="margin: 12px auto; display: inline-flex;">Lihat Semua SPBU Medan</button>
      </div>
    `;
    return;
  }

  elSpbuList.innerHTML = filtered.map(spbu => {
    const crowd = spbu.crowd;
    const statusClass = crowd.status.toLowerCase();
    
    // Gunakan rute jalan riil jika tersedia
    let distanceLabel = `${crowd.distance_km} km`;
    let durationLabel = "";
    if (crowd.route_real) {
      distanceLabel = `${crowd.route_real.road_distance_km} km`;
      durationLabel = `~${crowd.route_real.driving_duration_min} mnt jalan`;
    }

    return `
      <article class="spbu-card">
        <div class="card-top">
          <div>
            <div class="card-meta-row">
              <span class="card-district-tag">Kec. ${spbu.district}</span>
              <span class="card-brand-badge">${spbu.brand}</span>
            </div>
            <h2 class="card-title">${spbu.name}</h2>
            <p class="card-address">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              ${spbu.address}
            </p>
          </div>
          <div class="card-distance-badge">
            <span>${distanceLabel}</span>
            ${durationLabel ? `<span class="card-duration-text">${durationLabel}</span>` : ""}
          </div>
        </div>

        <!-- Score & Status Box -->
        <div class="card-score-container">
          <div class="score-row">
            <span class="status-chip ${statusClass}">
              <span style="width: 6px; height: 6px; border-radius: 50%; background: currentColor;"></span>
              ${crowd.status}
            </span>
            <span class="score-value">Skor Keramaian: ${crowd.score} / 100</span>
          </div>

          <div class="score-progress-bar">
            <div class="progress-fill" style="width: ${crowd.score}%; background-color: ${crowd.status_color};"></div>
          </div>

          <div class="wait-time-row">
            <span class="wait-label">${crowd.status_description}</span>
            <span class="wait-val">⏱ Tunggu: ${crowd.estimated_wait_time}</span>
          </div>
        </div>

        <!-- Tags BBM & Fasilitas Utama -->
        <div class="card-tags">
          <span class="tag-item">⛽ ${spbu.pump_capacity.motorcycle_nozzles + spbu.pump_capacity.car_nozzles} Nozzle Pompa</span>
          <span class="tag-item">🛣 ${spbu.road_class}</span>
          ${spbu.has_convenience_store ? '<span class="tag-item">🏪 Minimarket Aktif</span>' : ''}
          <span class="tag-item">🕒 ${spbu.operating_hours}</span>
        </div>

        <!-- Actions -->
        <div class="card-actions">
          <button class="btn-secondary" onclick="openDetailModal('${spbu.id}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            Analisis Detail
          </button>
          <a href="${spbu.google_maps_url}" target="_blank" rel="noopener noreferrer" class="btn-primary-route">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
            </svg>
            Petunjuk Arah
          </a>
        </div>
      </article>
    `;
  }).join("");
}

// Buka Modal Detail
window.openDetailModal = function(spbuId) {
  const spbu = appState.spbuData.find(s => s.id === spbuId);
  if (!spbu) return;

  const crowd = spbu.crowd;
  const bd = crowd.breakdown;

  elModalSpbuName.textContent = spbu.name;
  elModalSpbuCode.textContent = `Kode: ${spbu.id} • Kec. ${spbu.district} • ${spbu.road_name}`;
  elModalScore.textContent = crowd.score;

  elModalStatusBadge.textContent = crowd.status;
  elModalStatusBadge.className = `modal-badge ${crowd.status.toLowerCase()}`;
  elModalStatusBadge.style.backgroundColor = crowd.status === "Sepi" ? "#ecfdf5" : (crowd.status === "Sedang" ? "#fffbeb" : "#fef2f2");
  elModalStatusBadge.style.color = crowd.status_color;

  elModalWaitEstimate.textContent = `Estimasi antre: ${crowd.estimated_wait_time} (${crowd.estimated_vehicles_in_queue} kendaraan)`;

  // Info Rute Riil
  if (crowd.route_real) {
    elModalRoadDist.textContent = `Jarak jalan: ${crowd.route_real.road_distance_km} km • Waktu tempuh berkendara: ~${crowd.route_real.driving_duration_min} menit (Jaringan Jalan Riil)`;
  } else {
    elModalRoadDist.textContent = `Jarak garis lurus: ${crowd.distance_km} km`;
  }

  // 1. Waktu Komuter
  elBarTime.style.width = `${bd.time_commuter.score}%`;
  elDescTime.textContent = `${bd.time_commuter.label} (Indeks: ${bd.time_commuter.score}/100)`;

  // 2. Koridor Arus Lalin
  elBarTraffic.style.width = `${bd.traffic_corridor.score}%`;
  elDescTraffic.textContent = `${bd.traffic_corridor.road_class} • Status: ${bd.traffic_corridor.status} (${crowd.traffic_condition ? crowd.traffic_condition.detail : 'Normal'})`;

  // 3. Kapasitas Pompa
  elBarPump.style.width = `${bd.pump_capacity.score}%`;
  elDescPump.textContent = `${bd.pump_capacity.total_nozzles} Nozzle Pompa Aktif (Indeks Penetrasi Antrean: ${bd.pump_capacity.score}/100)`;

  // 4. Tenant & Dwell Time
  elBarFacility.style.width = `${bd.facilities_dwell.score}%`;
  elDescFacility.textContent = bd.facilities_dwell.has_convenience_store 
    ? "Terdapat Minimarket & Tenant Dwell Aktif (Menambah Waktu Parkir Kendaraan)" 
    : "Tanpa Minimarket Besar (Durasi Singgah Kendaraan Lebih Singkat)";

  // Render Tags
  elModalFacilities.innerHTML = spbu.facilities.map(f => `<span class="chip-tag">${f}</span>`).join("");
  elModalFuels.innerHTML = spbu.fuel_types.map(f => `<span class="chip-tag">${f}</span>`).join("");

  elModalRouteBtn.href = spbu.google_maps_url;
  elModalBackdrop.classList.remove("hidden");
};

function closeModal() {
  elModalBackdrop.classList.add("hidden");
}

function showError(msg) {
  elSpbuList.innerHTML = `
    <div class="empty-state">
      <p style="color: #ef4444; font-weight: 600;">${msg}</p>
      <button onclick="fetchSPBUData()" class="btn-secondary" style="margin: 12px auto; display: inline-flex;">Coba Lagi</button>
    </div>
  `;
}

// Register Service Worker untuk Standar Aplikasi Android PWA
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.warn("SW registration skipped:", err);
    });
  });
}
