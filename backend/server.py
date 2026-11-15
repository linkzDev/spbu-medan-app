import os
import sys
import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from spbu_data import MEDAN_SPBU_DATABASE, MEDAN_DISTRICTS
from scoring import calculate_crowd_score
from geocoding import reverse_geocode, get_top_nearby_districts, haversine

PORT = int(os.environ.get("PORT", 8000))
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

class SPBUAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        # 1. API: List SPBU Terdekat dengan Reverse Geocoding & Top Kecamatan
        if path == "/api/spbu/nearby":
            self.handle_nearby_spbu(query_params)
            return

        # 2. API: Info Lokasi GPS & Top Kecamatan Terdekat
        if path == "/api/location/resolve":
            self.handle_resolve_location(query_params)
            return

        # 3. API: Detail Lengkap SPBU
        if path == "/api/spbu/detail":
            self.handle_detail_spbu(query_params)
            return

        # 4. API Health Check
        if path == "/api/health":
            self.send_json_response({
                "status": "healthy",
                "service": "SPBU Medan Real Location & Crowd Engine",
                "version": "2.0.0"
            })
            return

        # 5. Fallback melayani frontend static files
        if path == "/" or path == "":
            self.path = "/index.html"
            
        return super().do_GET()

    def handle_resolve_location(self, params):
        try:
            lat = float(params.get("lat", [3.5686])[0])
            lng = float(params.get("lng", [98.7086])[0])
        except (ValueError, TypeError):
            lat, lng = 3.5686, 98.7086

        geo_info = reverse_geocode(lat, lng)
        top_districts = get_top_nearby_districts(lat, lng, limit=6)

        self.send_json_response({
            "success": True,
            "coordinates": {"latitude": lat, "longitude": lng},
            "administrative_area": geo_info,
            "top_nearby_districts": top_districts
        })

    def handle_nearby_spbu(self, params):
        try:
            user_lat = float(params.get("lat", [3.5686725])[0])
            user_lng = float(params.get("lng", [98.7086462])[0])
        except (ValueError, TypeError):
            user_lat = 3.5686725
            user_lng = 98.7086462

        selected_district = params.get("district", ["all"])[0]
        sort_by = params.get("sort", ["distance"])[0]

        # 1. Reverse geocoding lokasi pengguna ke Kota & Kecamatan riil
        user_geo = reverse_geocode(user_lat, user_lng)
        top_districts = get_top_nearby_districts(user_lat, user_lng, limit=6)

        # 2. Proses tiap SPBU
        results = []
        for spbu in MEDAN_SPBU_DATABASE:
            # Filter kecamatan jika dipilih spesifik
            if selected_district != "all" and spbu.get("district", "").lower() != selected_district.lower():
                continue

            crowd_info = calculate_crowd_score(spbu, user_lat, user_lng)
            
            # Hitung jarak lurus untuk sorting awal
            crowd_info["distance_km"] = haversine(user_lat, user_lng, spbu["latitude"], spbu["longitude"])

            item = {
                "id": spbu["id"],
                "name": spbu["name"],
                "brand": spbu["brand"],
                "city": spbu.get("city", "Kota Medan"),
                "district": spbu.get("district", "Medan Area"),
                "subdistrict": spbu.get("subdistrict", ""),
                "address": spbu["address"],
                "road_name": spbu["road_name"],
                "road_class": spbu["road_class"],
                "latitude": spbu["latitude"],
                "longitude": spbu["longitude"],
                "operating_hours": spbu["operating_hours"],
                "fuel_types": spbu["fuel_types"],
                "facilities": spbu["facilities"],
                "pump_capacity": spbu["pump_capacity"],
                "crowd": crowd_info,
                "google_maps_url": f"https://www.google.com/maps/dir/?api=1&destination={spbu['latitude']},{spbu['longitude']}"
            }
            results.append(item)

        # 3. Pengurutan
        if sort_by == "score_asc":
            results.sort(key=lambda x: x["crowd"]["score"])
        elif sort_by == "score_desc":
            results.sort(key=lambda x: -x["crowd"]["score"])
        else:
            # Berdasarkan jarak jalan raya riil (jika ada) atau jarak lurus
            results.sort(key=lambda x: (
                x["crowd"]["route_real"]["road_distance_km"] 
                if x["crowd"].get("route_real") 
                else x["crowd"]["distance_km"]
            ))

        response_payload = {
            "success": True,
            "user_location": {
                "latitude": user_lat,
                "longitude": user_lng,
                "city": user_geo.get("city", "Kota Medan"),
                "district": user_geo.get("district", "Medan Area"),
                "road": user_geo.get("road", "Jalan Utama"),
                "display_name": user_geo.get("display_name", "Kota Medan")
            },
            "top_nearby_districts": top_districts,
            "total_found": len(results),
            "spbu_list": results
        }
        self.send_json_response(response_payload)

    def handle_detail_spbu(self, params):
        spbu_id = params.get("id", [""])[0]
        spbu = next((s for s in MEDAN_SPBU_DATABASE if s["id"] == spbu_id), None)
        
        if not spbu:
            self.send_json_response({"success": False, "error": "SPBU tidak ditemukan"}, status_code=404)
            return

        try:
            user_lat = float(params.get("lat", [None])[0])
            user_lng = float(params.get("lng", [None])[0])
        except (ValueError, TypeError):
            user_lat, user_lng = None, None

        crowd_info = calculate_crowd_score(spbu, user_lat, user_lng)
        data = {
            **spbu,
            "crowd": crowd_info,
            "google_maps_url": f"https://www.google.com/maps/dir/?api=1&destination={spbu['latitude']},{spbu['longitude']}"
        }
        self.send_json_response({"success": True, "data": data})

    def send_json_response(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

def run():
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, SPBUAppHandler)
    print(f"==================================================")
    print(f" SPBU Medan Crowd Engine v2.0 (Real Geocoding Ready)")
    print(f" Running at: http://localhost:{PORT}")
    print(f" Endpoints:")
    print(f"   - GET http://localhost:{PORT}/api/spbu/nearby")
    print(f"   - GET http://localhost:{PORT}/api/location/resolve")
    print(f"==================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
