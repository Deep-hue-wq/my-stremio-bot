import os
import re
import json
import time
import threading
import requests
from aiohttp import web
from pymongo import MongoClient

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
PORT = int(os.getenv("PORT", 10000))

print("\n=== ENGINE UPGRADE: META PLAYBACK PIPELINE ACTIVATED ===", flush=True)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
    db = client.stremio_bridge
    streams_col = db.streams
    client.admin.command('ping')
    print("🟢 MONGO DATABASE: CONNECTED", flush=True)
except Exception as e:
    print(f"🔴 MONGO DATABASE: ERROR -> {e}", flush=True)

try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
    print("🧹 Webhook cache cleared!", flush=True)
except Exception:
    pass

async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram",
        "version": "4.0.0",
        "name": "Telegram Library",
        "description": "Instant video playback synced from your bot links.",
        "resources": ["catalog", "meta", "stream"],
        "types": ["movie", "series"],
        "catalogs": [{"type": "movie", "id": "tg_catalog", "name": "Telegram Library"}]
    }, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"})

async def catalog_route(request):
    metas = []
    try:
        for doc in streams_col.find().sort("_id", -1).limit(100):
            metas.append({
                "id": f"tg_meta:{str(doc['_id'])}",
                "type": "movie",
                "name": doc["file_name"],
                "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg",
                "description": "Stream Ready"
            })
    except Exception as e:
        print(f"🔴 Catalog Error: {e}", flush=True)
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"})

async def meta_route(request):
    raw_id = request.match_info['id']
    clean_id = raw_id.replace(".json", "").split(":")[-1]
    try:
        from bson.objectid import ObjectId
        doc = streams_col.find_one({"_id": ObjectId(clean_id)})
        if doc:
            meta = {
                "id": f"tg_meta:{str(doc['_id'])}",
                "type": "movie",
                "name": doc["file_name"],
                "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg",
                "description": "Telegram Video Cloud Stream Layout Link.",
                "background": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg"
            }
            return web.json_response({"meta": meta}, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"})
    except Exception as e:
        print(f"🔴 Meta Error: {e}", flush=True)
    return web.json_response({"meta": {}}, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"})

async def stream_route(request):
    raw_id = request.match_info['id']
    clean_id = raw_id.replace(".json", "").split(":")[-1]
    streams = []
    try:
        from bson.objectid import ObjectId
        doc = streams_col.find_one({"_id": ObjectId(clean_id)})
        if doc and "tg_url" in doc:
            streams.append({
                "title": "🎬 Play Stream Live",
                "url": doc["tg_url"]
            })
    except Exception as e:
        print(f"🔴 Stream Error: {e}", flush=True)
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"})

def telegram_polling_loop():
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
                    reply = "🟢 Extraction Bot Online!\n\nForward any text link block message from your link generator bot here."
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
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    app = web.Application()
    app.router.add_get('/', manifest_route)
    app.router.add_get('/manifest.json', manifest_route)
    app.router.add_get('/catalog/{type}/{id}.json', catalog_route)
    app.router.add_get('/meta/{type}/{id}.json', meta_route)
    app.router.add_get('/stream/{type}/{id}.json', stream_route)
    web.run_app(app, host="0.0.0.0", port=PORT)
