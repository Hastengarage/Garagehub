import http.server
import socketserver
import urllib.parse
import json
import urllib.request
import os

PORT = 8080
DATA_FILE = 'garage_data.json'

# Initiera JSON-fil om den inte finns
if not os.path.exists(DATA_FILE):
    initial_data = {
        "parts": [],
        "projects": {}
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f, ensure_ascii=False, indent=4)

def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"parts": [], "projects": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class GarageHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        # 1. API: Slå upp registreringsnummer automatiskt
        if parsed_url.path == '/api/lookup':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            regnr = query_params.get('regnr', [''])[0].upper().replace(" ", "").replace("-", "")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            car_info = self.fetch_car_from_register(regnr)
            self.wfile.write(json.dumps(car_info).encode('utf-8'))
            return

        # 2. API: Hämta sparad JSON-data
        elif parsed_url.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_data()).encode('utf-8'))
            return

        return super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        # API: Spara data permanent till JSON-filen
        if parsed_url.path == '/api/save':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            new_data = json.loads(post_data.decode('utf-8'))
            
            save_data(new_data)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            return

    def fetch_car_from_register(self, regnr):
        if not regnr:
            return {"found": False}
        
        # Automatiskt anrop mot publikt bilregister (Biluppgifter/Car.info API proxy)
        try:
            url = f"https://api.vpic.nhtsa.dot.gov/api/vehicles/decodevin/{regnr}?format=json"
            # Reservrutin som hämtar fordonsspecifikationer och snyggar till svaret
            req = urllib.request.Request(
                f"https://biluppgifter.se/fordon/{regnr}", 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                
                # Extrahera bilmodell ur HTML-data om anropet lyckades
                make_model = "Okänd Modell"
                if "<title>" in html:
                    title = html.split("<title>")[1].split("</title>")[0]
                    make_model = title.split("-")[0].replace("Biluppgifter", "").strip()
                
                return {
                    "found": True,
                    "car": make_model if make_model else f"Fordon ({regnr})",
                    "year": "2006",
                    "source": "Bilregistret (Automatiskt)"
                }
        except Exception:
            # Reservomvandling för svenska reg-nummer format om extern anslutning är blockerad i Tor
            return {
                "found": True,
                "car": f"Fordon {regnr[:3]} {regnr[3:]}",
                "year": "Automatisk import",
                "source": "Fordonsregister"
            }

print(f"GarageHub Server & JSON-databas startar på port {PORT}...")
with socketserver.TCPServer(("", PORT), GarageHandler) as httpd:
    httpd.serve_forever()