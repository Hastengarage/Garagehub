from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import urllib.parse
import urllib.request
import hashlib
import re
import os

DATA_FILE = 'data.json'

def load_db():
    if not os.path.exists(DATA_FILE):
        default_db = {
            "users": {
                "admin": {
                    "hash": hashlib.sha256("garage2026".encode('utf-8')).hexdigest(),
                    "is_admin": True,
                    "is_vip": True
                }
            },
            "parts": [], "cars": [], "market": [], "vipMarket": []
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

        if parsed_url.path == '/api/login':
            user = body.get('user', '').strip().lower()
            pass_hash = hashlib.sha256(body.get('pass', '').encode('utf-8')).hexdigest()

            self.send_json_response()
            if user in db["users"] and db["users"][user]["hash"] == pass_hash:
                u_info = db["users"][user]
                self.wfile.write(json.dumps({"success": True, "isAdmin": u_info.get("is_admin", False), "isVip": u_info.get("is_vip", False)}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"success": False}).encode('utf-8'))
            return

        elif parsed_url.path == '/api/save-part':
            db["parts"].append(body)
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        elif parsed_url.path == '/api/mount-part':
            part_id = body.get('partId')
            car_reg = body.get('carReg')
            car_title = body.get('carTitle')
            for p in db["parts"]:
                if p.get('id') == part_id:
                    p["mountedTo"] = car_title
                    p["mountedToReg"] = car_reg
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        elif parsed_url.path == '/api/add-service-log':
            car_id = body.get('carId')
            note = body.get('note')
            date_str = body.get('date')
            for c in db["cars"]:
                if c.get('id') == car_id:
                    if "logs" not in c: c["logs"] = []
                    c["logs"].append({"date": date_str, "note": note})
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        elif parsed_url.path == '/api/delete-part':
            pid = body.get('id')
            db["parts"] = [p for p in db["parts"] if p.get('id') != pid]
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        elif parsed_url.path == '/api/save-car':
            db["cars"].append(body)
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        elif parsed_url.path == '/api/save-market':
            if body.get('isVip'): db["vipMarket"].append(body)
            else: db["market"].append(body)
            save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        elif parsed_url.path == '/api/admin/toggle-perm':
            target_user = body.get('targetUser')
            if target_user in db["users"]:
                db["users"][target_user]["is_vip"] = not db["users"][target_user].get("is_vip", False)
                save_db(db)
            self.send_json_response()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)

        if parsed_url.path == '/api/data':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            req_user = query_params.get('user', [''])[0].strip().lower()
            
            db = load_db()
            u_info = db["users"].get(req_user, {})
            is_admin = u_info.get("is_admin", False)

            visible_parts = [p for p in db["parts"] if is_admin or p.get('user', '').lower() == req_user]
            visible_cars = [c for c in db["cars"] if is_admin or c.get('user', '').lower() == req_user]

            users_list = []
            if is_admin:
                for uname, udata in db["users"].items():
                    users_list.append({"user": uname, "isAdmin": udata.get("is_admin", False), "isVip": udata.get("is_vip", False)})

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
            car_data = self.fetch_real_car_data(reg_nr)
            self.wfile.write(json.dumps(car_data).encode('utf-8'))
            return

        return super().do_GET()

    def send_json_response(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def fetch_real_car_data(self, reg):
        reg = reg.strip().upper().replace(" ", "")
        if not reg or len(reg) < 5: return {"success": False}

        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            url = f"https://biluppgifter.se/fordon/{reg}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8', errors='ignore')
                title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                if title_match and reg in title_match.group(1).upper():
                    clean_title = title_match.group(1).split('- Biluppgifter')[0].replace(reg, '').replace('-', '').strip()
                    year_match = re.search(r'\b(19\d\d|20\d\d)\b', clean_title)
                    year = year_match.group(1) if year_match else ""
                    parts = re.sub(r'\b(19\d\d|20\d\d)\b', '', clean_title).strip().split()
                    return {"success": True, "reg": reg, "make": parts[0] if parts else "", "model": " ".join(parts[1:]) if len(parts) > 1 else "", "year": year}
        except Exception: pass
        return {"success": False}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), CustomHandler)
    server.serve_forever()
