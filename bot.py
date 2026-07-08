import asyncio
# 🛡️ EVENT LOOP RECOVERY: Secures the asynchronous environment for Python 3.14 immediately
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
import urllib.parse
import requests
import time
import threading
from aiohttp import web
from pymongo import MongoClient
from pyrogram import Client

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
PORT = int(os.getenv("PORT", 10000))

print("\n=== RESTORING ORIGINAL ENGINE: STABLE LAYOUT ACTIVATED ===", flush=True)

# Connect Database Storage Grid
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams
print("🟢 MONGO DATABASE: CONNECTED SUCCESSFULLY", flush=True)

try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
    print("🧹 Webhook cache cleared!", flush=True)
except Exception:
    pass

# Initialize Pyrogram purely as a passive asset for file downloads
tg_client = Client("stremio_fine_wine", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# 🎬 CINEMATIC POSTER & SERIES METADATA MATCHING
def fetch_movie_metadata(raw_title):
    try:
        clean = re.sub(r'\.(mkv|mp4|avi|mov|webm)$', '', raw_title, flags=re.IGNORECASE)
        clean = clean.replace('.', ' ').replace('_', ' ')
        
        is_series, season, episode = False, 1, 1
        series_match = re.search(r's(\d+)\s*e(\d+)', clean, re.IGNORECASE)
        if series_match:
            is_series, season, episode = True, int(series_match.group(1)), int(series_match.group(2))
        else:
            ep_match = re.search(r'(v|ep|e|episode)\s*(\d+)', clean, re.IGNORECASE)
            if ep_match:
                is_series, episode = True, int(ep_match.group(2))
            if "season" in clean.lower():
                is_series = True
                sea_match = re.search(r'season\s*(\d+)', clean, re.IGNORECASE)
                if sea_match: season = int(sea_match.group(1))

        clean = re.sub(r'(1080p|720p|2160p|4k|bluray|hdrip|web\s*dl|brrip|x264|x265|hevc|aac|hindi|english|yts|mx|s\d+e\d+|season\s*\d+|episode\s*\d+|ep\s*\d+).*', '', clean, flags=re.IGNORECASE)
        clean_query = clean.strip()
        if len(clean_query) < 2: clean_query = raw_title[:30]

        media_type = "series" if is_series else "movie"
        res = requests.get(f"https://v3-cinemeta.strem.io/catalog/{media_type}/top/search={urllib.parse.quote(clean_query)}.json", timeout=5).json()
        if metas := res.get("metas", []):
            return {
                "imdb_id": metas[0].get("id"), "name": metas[0].get("name"),
                "poster": metas[0].get("poster"), "desc": metas[0].get("description", ""),
                "type": media_type, "s": season, "e": episode
            }
    except Exception:
        pass
    return {
        "imdb_id": None, "name": raw_title, "type": "movie", "s": 1, "e": 1,
        "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg", 
        "desc": "Synced Movie File"
    }

# 📡 BULLETPROOF DECOUPLED HTTP LONG POLLING PIPELINE
def telegram_polling_loop():
    print("🟢 TELEGRAM BOT LISTENER ONLINE AND ACTIVE", flush=True)
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=5"
            req = requests.get(url, timeout=10)
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
                    reply = "🟢 Extraction Bot Online!\n\nForward movie text link blocks or raw media files here to sync them instantly."
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue

                # Process Raw Movie File Attachments
                media = msg.get("video") or msg.get("document")
                if media and ("video" in media.get("mime_type", "") or media.get("file_name", "").endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm'))):
                    file_id = media.get("file_id")
                    raw_name = media.get("file_name", "Telegram Video Stream")
                    file_size = media.get("file_size")
                    
                    render_domain = os.getenv("RENDER_EXTERNAL_URL", "https://my-stremio-bot-1.onrender.com").rstrip('/')
                    live_stream_url = f"{render_domain}/watch/{file_id}"
                    meta = fetch_movie_metadata(raw_name)
                    
                    streams_col.insert_one({
                        "file_name": meta["name"], "tg_url": live_stream_url,
                        "file_id": file_id, "file_size": file_size, "imdb_id": meta["imdb_id"],
                        "poster": meta["poster"], "description": meta["desc"],
                        "type": meta["type"], "season": meta["s"], "episode": meta["e"]
                    })
                    reply = f"✅ Raw File Synced as [{meta['type'].upper()}]!\n📁 {meta['name']} " + (f"(S{meta['s']}E{meta['e']})" if meta['type'] == 'series' else "")
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue

                # Process Text Link Blocks
                if "http" in text_content or "Stream Link" in text_content:
                    urls = re.findall(r'(https?://\S+)', text_content)
                    final_url = next((u for u in urls if "stream" in u or "dl" in u or "vault" in u), urls[0] if urls else None)
                    if final_url:
                        name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
                        file_name = name_match.group(1).split("\n")[0].strip() if name_match else text_content.split("\n")[0].strip()
                        
                        meta = fetch_movie_metadata(file_name)
                        streams_col.insert_one({
                            "file_name": meta["name"], "tg_url": final_url, "imdb_id": meta["imdb_id"],
                            "poster": meta["poster"], "description": meta["desc"],
                            "type": meta["type"], "season": meta["s"], "episode": meta["e"]
                        })
                        reply = f"✅ Link Synced as [{meta['type'].upper()}]!\n📁 {meta['name']}"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
            if not results:
                time.sleep(1)
        except Exception:
            time.sleep(2)

# 📡 STREMIO PLATFORM SPECIFICATION ROUTERS
async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram", "version": "6.6.0", "name": "Telegram Library",
        "description": "Original stable streaming proxy tunnel.",
        "resources": ["catalog", "meta", "stream"], "types": ["movie", "series"],
        "catalogs": [{"type": "movie", "id": "tg_movie", "name": "Telegram Library"},
                     {"type": "series", "id": "tg_series", "name": "Telegram Library"}]
    }, headers={"Access-Control-Allow-Origin": "*"})

async def catalog_route(request):
    req_type = request.match_info['type']
    metas = [{"id": d.get("imdb_id") or f"tg_custom_{str(d['_id'])}", "type": req_type, "name": d["file_name"], "poster": d.get("poster"), "description": d.get("description")} 
             for d in streams_col.find({"type": req_type}).sort("_id", -1).limit(100)]
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*"})

async def meta_route(request):
    req_type, raw_id = request.match_info['type'], request.match_info['id'].replace(".json", "").split(":")[-1]
    if raw_id.startswith("tt"):
        res = requests.get(f"https://v3-cinemeta.strem.io/meta/{req_type}/{raw_id}.json", timeout=5).json()
        if req_type == "series" and "meta" in res:
            res["meta"]["episodes"] = [{"id": f"{raw_id}:{ep.get('season',1)}:{ep.get('episode',1)}", "title": f"Episode {ep.get('episode',1)}: {ep.get('file_name')}", "season": ep.get("season",1), "episode": ep.get("episode",1)} for ep in streams_col.find({"imdb_id": raw_id, "type": "series"})]
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    
    from bson.objectid import ObjectId
    if doc := streams_col.find_one({"_id": ObjectId(raw_id)}):
        return web.json_response({"meta": {"id": f"tg_custom_{str(doc['_id'])}", "type": req_type, "name": doc["file_name"], "poster": doc.get("poster"), "description": doc.get("description")}}, headers={"Access-Control-Allow-Origin": "*"})
    return web.json_response({"meta": {}}, headers={"Access-Control-Allow-Origin": "*"})

async def stream_route(request):
    parts = request.match_info['id'].replace(".json", "").split(":")
    query = {"imdb_id": parts[0], "season": int(parts[1]), "episode": int(parts[2])} if len(parts) == 3 else {"imdb_id": parts[0]}
    doc = streams_col.find_one(query)
    if not doc and not parts[0].startswith("tt"):
        from bson.objectid import ObjectId
        try: doc = streams_col.find_one({"_id": ObjectId(parts[0])})
        except: pass
    return web.json_response({"streams": [{"title": f"🎬 Play Stream Natively", "url": doc["tg_url"]}]} if doc and "tg_url" in doc else {"streams": []}, headers={"Access-Control-Allow-Origin": "*"})

async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    if not doc: return web.Response(status=404)
    file_size = doc.get("file_size", 0)
    
    headers = {"Content-Type": "video/mp4", "Access-Control-Allow-Origin": "*"}
    if file_size:
        headers["Content-Disposition"] = f'inline; filename="{doc.get("file_name", "stream.mkv")}"'
        headers["Content-Length"] = str(file_size)
            
    response = web.StreamResponse(status=200, headers=headers)
    await response.prepare(request)
    try:
        async for chunk in tg_client.download_media(file_id, chunks=True):
            await response.write(chunk)
    except Exception:
        pass
    return response

# 🚀 CONTAINER START ENTRYPOINT
async def main():
    app = web.Application(client_max_size=0)
    app.router.add_get('/', manifest_route)
    app.router.add_get('/manifest.json', manifest_route)
    app.router.add_get('/catalog/{type}/{id}.json', catalog_route)
    app.router.add_get('/meta/{type}/{id}.json', meta_route)
    app.router.add_get('/stream/{type}/{id}.json', stream_route)
    app.router.add_get('/watch/{file_id}', watch_route)
    
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    print(f"🟢 Stremio Core Router active on port {PORT}", flush=True)
    
    await tg_client.start()
    print("🟢 MTProto Passive Asset connected successfully!", flush=True)
    
    # Run the standalone polling thread
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
