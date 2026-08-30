from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import urllib.parse
import hashlib
import os

DATA_FILE = 'data.json'

def load_db():
    if not os.path.exists(DATA_FILE):
        default_db = {
            "users": {
                "admin": {
                    "hash": hashlib.sha256("garage2026".encode('utf-8')).hexdigest(),
                    "is_admin": True,
                    "is_vip": True,
                    "can_see_admin_inv": True
                }
            },
            "parts": [],
            "cars": [],
            "market": [],
            "vipMarket": []
        }
        save_db(default_db)
        return default_db
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "parts": [], "cars": [], "market": [], "vipMarket": []}

def save_db(db):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

class CustomHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        body = json.loads(post_data.decode('utf-8'))
        
        db = load_db()

        # INLOGGNING
        if parsed_url.path == '/api/login':
            user = body.get('user', '').strip().lower()
            password = body.get('pass', '')
            pass_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

            self.send_json_response()
            if user in db["users"] and db["users"][user]["hash"] == pass_hash:
                u_info = db["users"][user]
                self.wfile.write(json.dumps({
                    "success": True,
                    "isAdmin": u_info.get("is_admin", False),
                    "isVip": u_info.get("is_vip", False)
                }).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"success": False, "message": "Fel användarnamn eller lösenord"}).encode('utf-8'))
            return

        # SPARA DEL
        elif parsed_url.path == '/api/save-part':
            db["parts"].append(body)
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        # RADERA DEL
        elif parsed_url.path == '/api/delete-part':
            pid = body.get('id')
            db["parts"] = [p for p in db["parts"] if p.get('id') != pid]
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        # TINGA / RESERVERA DEL
        elif parsed_url.path == '/api/reserve-part':
            pid = body.get('id')
            for p in db["parts"]:
                if p.get('id') == pid:
                    p["reserved"] = not p.get("reserved", False)
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        # SPARA BIL
        elif parsed_url.path == '/api/save-car':
            db["cars"].append(body)
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        # SPARA MARKNADSANNONS
        elif parsed_url.path == '/api/save-market':
            if body.get('isVip'):
                db["vipMarket"].append(body)
            else:
                db["market"].append(body)
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        # ADMIN: ÄNDRA BEHÖRIGHET
        elif parsed_url.path == '/api/admin/toggle-perm':
            target_user = body.get('targetUser')
            perm_type = body.get('permType')
            if target_user in db["users"]:
                if perm_type == 'adminInv':
                    db["users"][target_user]["can_see_admin_inv"] = not db["users"][target_user].get("can_see_admin_inv", False)
                elif perm_type == 'vip':
                    db["users"][target_user]["is_vip"] = not db["users"][target_user].get("is_vip", False)
                save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        # ÄNDRA PROFIL
        elif parsed_url.path == '/api/update-profile':
            curr_user = body.get('currUser', '').strip().lower()
            curr_pass = body.get('currPass', '')
            new_user = body.get('newUser', '').strip().lower()
            new_pass = body.get('newPass', '')

            curr_hash = hashlib.sha256(curr_pass.encode('utf-8')).hexdigest()
            self.send_json_response()

            if curr_user in db["users"] and db["users"][curr_user]["hash"] == curr_hash:
                u_data = db["users"].pop(curr_user)
                if new_pass:
                    u_data["hash"] = hashlib.sha256(new_pass.encode('utf-8')).hexdigest()
                target = new_user if new_user else curr_user
                db["users"][target] = u_data
                save_db(db)
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"success": False, "message": "Felaktigt nuvarande lösenord"}).encode('utf-8'))
            return

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)

        if parsed_url.path == '/api/data':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            req_user = query_params.get('user', [''])[0].strip().lower()
            
            db = load_db()
            u_info = db["users"].get(req_user, {})
            is_admin = u_info.get("is_admin", False)
            can_see_admin = u_info.get("can_see_admin_inv", False)

            # BEHÖRIGHETS-LOGIK:
            # Admin ser ALLT.
            # Vanlig användare ser sina egna delar + Admin-delar om Admin godkänt.
            visible_parts = []
            for p in db["parts"]:
                owner = p.get('user', '').lower()
                if is_admin or owner == req_user or (owner == 'admin' and can_see_admin):
                    visible_parts.append(p)

            visible_cars = [c for c in db["cars"] if is_admin or c.get('user', '').lower() == req_user]

            users_list = []
            if is_admin:
                for uname, udata in db["users"].items():
                    users_list.append({
                        "user": uname,
                        "isAdmin": udata.get("is_admin", False),
                        "isVip": udata.get("is_vip", False),
                        "canSeeAdminInventory": udata.get("can_see_admin_inv", False)
                    })

            self.send_json_response()
            self.wfile.write(json.dumps({
                "parts": visible_parts,
                "cars": visible_cars,
                "market": db.get("market", []),
                "vipMarket": db.get("vipMarket", []) if (is_admin or u_info.get("is_vip")) else [],
                "users": users_list
            }).encode('utf-8'))
            return

        elif parsed_url.path == '/api/car-info':
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
            return {"success": True, "reg": reg, "make": "Volvo", "model": "V70 D4", "year": "2012", "engine": "D4204T5 (2.0L)", "fuel": "Diesel", "power": "163 hk / 120 kW"}
        elif reg.startswith("A"):
            return {"success": True, "reg": reg, "make": "BMW", "model": "320i Touring", "year": "2009", "engine": "N43B20A (2.0L)", "fuel": "Bensin", "power": "170 hk / 125 kW"}
        else:
            return {"success": True, "reg": reg, "make": "Ford", "model": "Focus RS", "year": "2016", "engine": "2.3L EcoBoost", "fuel": "Bensin", "power": "350 hk / 257 kW"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), CustomHandler)
    print(f"Server igång på port {port}...")
    server.serve_forever()
