import os
import http.server
import socketserver
import threading
import json
import requests
import time
import re
from pymongo import MongoClient

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
PORT = int(os.getenv("PORT", 10000))  # Render uses port 10000 by default

print("\n=== STREMIO LIVE ENGINE ONLINE ===", flush=True)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
    db = client.stremio_bridge
    streams_col = db.streams
    client.admin.command('ping')
    print("🟢 MONGO DATABASE CONNECTION: SUCCESSFUL", flush=True)
except Exception as e:
    print(f"🔴 MONGO DATABASE CONNECTION: FAILED -> {e}", flush=True)

class StremioRouter(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        super().end_headers()

    def do_GET(self):
        if self.path == "/" or "manifest.json" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            manifest = {
                "id": "org.deepsstremio.telegram",
                "version": "1.0.0",
                "name": "Telegram Library Addon",
                "description": "Instant video streaming feed synced straight from your telegram bots.",
                "resources": ["catalog", "stream"],
                "types": ["movie", "series"],
                "catalogs": [{"type": "movie", "id": "tg_catalog", "name": "Telegram Library"}]
            }
            self.wfile.write(json.dumps(manifest).encode())
            return
        elif "/catalog/" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            metas = []
            try:
                for doc in streams_col.find().sort("_id", -1).limit(100):
                    metas.append({
                        "id": str(doc["_id"]),
                        "type": "movie",
                        "name": doc["file_name"],
                        "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg",
                        "description": "Ready to Stream"
                    })
            except Exception as e:
                print(f"🔴 Catalog Error: {e}", flush=True)
            self.wfile.write(json.dumps({"metas": metas}).encode())
            return
        elif "/stream/" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            streams = []
            try:
                clean_path = self.path.split(".json")[0]
                doc_id = clean_path.split(":")[-1]
                from bson.objectid import ObjectId
                doc = streams_col.find_one({"_id": ObjectId(doc_id)})
                if doc and "tg_url" in doc:
                    streams.append({"title": f"🎬 Play: {doc['file_name']}", "url": doc["tg_url"]})
            except Exception as e:
                print(f"🔴 Stream Error: {e}", flush=True)
            self.wfile.write(json.dumps({"streams": streams}).encode())
            return
        self.send_response(200)
        self.end_headers()

def telegram_polling_loop():
    print("🟢 TELEGRAM DETECTION ENGINE: ACTIVE AND MONITORING", flush=True)
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=10"
            req = requests.get(url, timeout=15)
            if req.status_code != 200:
                time.sleep(5)
                continue
            response = req.json()
            for update in response.get("result", []):
                offset = update["update_id"] + 1
                if "message" not in update:
                    continue
                msg = update["message"]
                chat_id = msg["chat"]["id"]
                text_content = msg.get("text", "") or msg.get("caption", "") or ""
                
                if text_content.startswith("/start"):
                    reply = "🟢 Extraction Bot Online!\n\nForward any message text block containing streaming links here and I will inject them directly to Stremio layout."
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue

                if "http" in text_content or "Stream Link" in text_content or "Download Link" in text_content:
                    urls = re.findall(r'(https?://\S+)', text_content)
                    stream_urls = [u for u in urls if "stream" in u or "dl" in u or "vault" in u]
                    final_url = stream_urls[0] if stream_urls else (urls[0] if urls else None)
                    
                    if final_url:
                        file_name = "Extracted Video Stream"
                        name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
                        if name_match:
                            file_name = name_match.group(1).split("\n")[0].strip()
                        else:
                            first_line = text_content.split("\n")[0]
                            if len(first_line) > 5:
                                file_name = first_line.strip()
                        
                        file_name = file_name.replace("*", "").replace("_", " ").strip()
                        streams_col.insert_one({"file_name": file_name, "tg_url": final_url})
                        
                        reply = f"✅ Automated Sync Complete!\n\n📁 {file_name}\n\nhas been pushed to Stremio. Refresh your player layout now!"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), StremioRouter) as httpd:
        httpd.serve_forever()
