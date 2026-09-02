from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import urllib.parse
import urllib.request
import hashlib
import re
import os

# Stöd för MongoDB Atlas via miljövariabel på Render
MONGO_URI = os.environ.get('MONGO_URI')
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

        elif parsed_url.path == '/api/edit-part':
            pid = body.get('id')
            for i, p in enumerate(db["parts"]):
                if p.get('id') == pid:
                    db["parts"][i] = body
                    break
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

            self.send_json_response()
            self.wfile.write(json.dumps({
                "parts": visible_parts,
                "cars": visible_cars,
                "market": db.get("market", []),
                "vipMarket": db.get("vipMarket", []) if (is_admin or u_info.get("is_vip")) else [],
            }).encode('utf-8'))
            return

        return super().do_GET()

    def send_json_response(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), CustomHandler)
    server.serve_forever()
