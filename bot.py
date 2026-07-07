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
PORT = int(os.getenv("PORT", 10000))

print("\n=== ENGINE RESET: PURE HTTP BOT ACTIVATED ===", flush=True)

# Connect Database Storage Grid
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
    db = client.stremio_bridge
    streams_col = db.streams
    client.admin.command('ping')
    print("🟢 MONGO DATABASE: CONNECTED SUCCESSFULLY", flush=True)
except Exception as e:
    print(f"🔴 MONGO DATABASE: CONNECTION FAILED -> {e}", flush=True)

# Forcefully remove any lingering webhook rules on Telegram's end
try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
    print("🧹 Telegram webhook cache explicitly cleared!", flush=True)
except Exception:
    pass

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
                "version": "3.5.0",
                "name": "Telegram Library",
                "description": "Instant high-speed video streams synced from your bot link blocks.",
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
                        "id": f"tg_meta:{str(doc['_id'])}",
                        "type": "movie",
                        "name": doc["file_name"],
                        "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg",
                        "description": "Stream Link Ready"
                    })
            except Exception as e:
                print(f"🔴 Catalog Error: {e}", flush=True)
            self.wfile.write(json.dumps({"metas": metas}).encode())
            return
            
        elif "/stream/" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            raw_id = self.path.replace(".json", "").split(":")[-1]
            streams = []
            try:
                from bson.objectid import ObjectId
                doc = streams_col.find_one({"_id": ObjectId(raw_id)})
                if doc and "tg_url" in doc:
                    streams.append({
                        "title": f"🎬 Play Stream: {doc['file_name']}",
                        "url": doc["tg_url"]
                    })
            except Exception as e:
                print(f"🔴 Stream Fetch Error: {e}", flush=True)
            self.wfile.write(json.dumps({"streams": streams}).encode())
            return
            
        self.send_response(200)
        self.end_headers()

def run_web_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), StremioRouter) as httpd:
        print(f"🟢 Stremio Web Server active on port {PORT}", flush=True)
        httpd.serve_forever()

def telegram_polling_loop():
    print("🟢 TELEGRAM HTTP LISTENER ONLINE AND ACTIVE", flush=True)
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=0"
            req = requests.get(url, headers={"Connection": "close"}, timeout=5)
            if req.status_code != 200:
                time.sleep(2)
                continue
                
            response = req.json()
            results = response.get("result", [])
            
            for update in results:
                offset = update["update_id"] + 1
                if "message" not in update:
                    continue
                msg = update["message"]
                chat_id = msg["chat"]["id"]
                
                text_content = msg.get("text", "") or msg.get("caption", "") or ""
                
                if text_content.startswith("/start"):
                    reply = "🟢 Extraction Bot Online!\n\nForward any text link block message from your link generator bot (like StreamVault Pro) here, and I will instantly extract the streaming links into Stremio layout!"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue
                
                # Explicitly catch raw media attachments (Lucy style files) to instruct the user
                if "video" in msg or "document" in msg:
                    reply = "⚠️ Raw File Forwarding Note!\n\nBecause this video file is hosted on Telegram's internal network, standard bots cannot stream it directly due to file size limits.\n\n👉 **Fix:** Please forward the text link block message from your link generator bot (the one with the 'Stream Link' HTTP URL layout) instead of the raw file!"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue
                
                if "http" in text_content or "Stream Link" in text_content:
                    urls = re.findall(r'(https?://\S+)', text_content)
                    stream_urls = [u for u in urls if "stream" in u or "dl" in u or "vault" in u]
                    final_url = stream_urls[0] if stream_urls else (urls[0] if urls else None)
                    
                    if final_url:
                        file_name = "Extracted Stream"
                        name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
                        if name_match:
                            file_name = name_match.group(1).split("\n")[0].strip()
                        else:
                            first_line = text_content.split("\n")[0]
                            if len(first_line) > 5:
                                file_name = first_line.strip()
                                
                        file_name = file_name.replace("*", "").replace("_", " ").strip()
                        streams_col.insert_one({"file_name": file_name, "tg_url": final_url})
                        
                        reply = f"✅ Automated Sync Complete!\n\n📁 {file_name}\n\nhas been pushed to Stremio. Open your player row now!"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
            
            if not results:
                time.sleep(1)
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    telegram_polling_loop()
