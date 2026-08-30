from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import urllib.parse
import hashlib
import os

# Lagring av användare i serverminnet
# Standard: admin / garage2026 (Admin har alltid VIP-access)
USERS_DB = {
    "admin": {
        "hash": hashlib.sha256("garage2026".encode('utf-8')).hexdigest(),
        "is_vip": True
    }
}

class CustomHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        body = json.loads(post_data.decode('utf-8'))

        # 1. Inloggning
        if parsed_url.path == '/api/login':
            user = body.get('user', '').strip().lower()
            password = body.get('pass', '')
            pass_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

            self.send_json_response()

            if user in USERS_DB and USERS_DB[user]["hash"] == pass_hash:
                self.wfile.write(json.dumps({
                    "success": True,
                    "isVip": USERS_DB[user]["is_vip"]
                }).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"success": False, "message": "Felaktigt användarnamn eller lösenord"}).encode('utf-8'))
            return

        # 2. Ändra Användarnamn & Lösenord
        elif parsed_url.path == '/api/update-profile':
            curr_user = body.get('currUser', '').strip().lower()
            curr_pass = body.get('currPass', '')
            new_user = body.get('newUser', '').strip().lower()
            new_pass = body.get('newPass', '')

            curr_hash = hashlib.sha256(curr_pass.encode('utf-8')).hexdigest()

            self.send_json_response()

            # Verifiera att nuvarande lösenord stämmer
            if curr_user in USERS_DB and USERS_DB[curr_user]["hash"] == curr_hash:
                user_data = USERS_DB.pop(curr_user)
                
                # Uppdatera lösenord om nytt har angivits
                if new_pass:
                    user_data["hash"] = hashlib.sha256(new_pass.encode('utf-8')).hexdigest()
                
                # Spara under nytt eller gammalt användarnamn
                target_user = new_user if new_user else curr_user
                USERS_DB[target_user] = user_data

                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"success": False, "message": "Felaktigt nuvarande lösenord"}).encode('utf-8'))
            return

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == '/api/car-info':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            reg_nr = query_params.get('reg', [''])[0].strip().upper().replace(" ", "")

            self.send_json_response()
            car_data = self.fetch_car_data(reg_nr)
            self.wfile.write(json.dumps(car_data).encode('utf-8'))
            return

        return super().do_GET()

    def send_json_response(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def fetch_car_data(self, reg):
        if reg.startswith("B"):
            return {
                "success": True, "reg": reg,
                "make": "Volvo", "model": "V70 D4", "year": "2012",
                "engine": "D4204T5 (2.0L)", "fuel": "Diesel",
                "power": "163 hk / 120 kW"
            }
        elif reg.startswith("A"):
            return {
                "success": True, "reg": reg,
                "make": "BMW", "model": "320i Touring", "year": "2009",
                "engine": "N43B20A (2.0L)", "fuel": "Bensin",
                "power": "170 hk / 125 kW"
            }
        else:
            return {
                "success": True, "reg": reg,
                "make": "Ford", "model": "Focus RS", "year": "2016",
                "engine": "2.3L EcoBoost", "fuel": "Bensin",
                "power": "350 hk / 257 kW"
            }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), CustomHandler)
    print(f"Server igång på port {port}...")
    server.serve_forever()
