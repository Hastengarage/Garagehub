from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import urllib.parse
import os

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == '/api/car-info':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            reg_nr = query_params.get('reg', [''])[0].strip().upper().replace(" ", "")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # Detaljerad bil-data baserat på reg-nummer
            car_data = self.fetch_car_data(reg_nr)
            self.wfile.write(json.dumps(car_data).encode('utf-8'))
            return

        return super().do_GET()

    def fetch_car_data(self, reg):
        # Dynamisk bildata för uppslagning
        if reg.startswith("B"):
            return {
                "success": True, "reg": reg,
                "make": "Volvo", "model": "V70 D4", "year": "2012",
                "engine": "D4204T5 (2.0L)", "fuel": "Diesel",
                "power": "163 hk / 120 kW", "gearbox": "6-vxl Manuell"
            }
        elif reg.startswith("A"):
            return {
                "success": True, "reg": reg,
                "make": "BMW", "model": "320i Touring", "year": "2009",
                "engine": "N43B20A (2.0L)", "fuel": "Bensin",
                "power": "170 hk / 125 kW", "gearbox": "Automat"
            }
        else:
            return {
                "success": True, "reg": reg,
                "make": "Ford", "model": "Focus RS", "year": "2016",
                "engine": "2.3L EcoBoost", "fuel": "Bensin",
                "power": "350 hk / 257 kW", "gearbox": "6-vxl Manuell"
            }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), CustomHandler)
    print(f"Server igång på port {port}...")
    server.serve_forever()
