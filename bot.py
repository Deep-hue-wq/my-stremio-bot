import asyncio
# 🛡️ SYSTEM INTEGRITY FIX: Force-initialize the event loop environment for Python 3.14 immediately
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
import json
import time
import threading
import requests
import urllib.parse
from aiohttp import web
from pymongo import MongoClient

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
SESSION_STRING = os.getenv("SESSION_STRING", "").strip()  # Optional: Paste a User Session String here for unthrottled speed
PORT = int(os.getenv("PORT", 10000))

print("\n=== MASTER CORE: MULTI-CLASSIFICATION SPEED ENGINE ONLINE ===", flush=True)

# Connect Secure Database Storage
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams

try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
except Exception:
    pass

from pyrogram import Client, filters

# ⚡ UNTHROTTLED GOD-SPEED GATEWAY: Swaps from Throttled Bot Token to Unthrottled User Account if present
if SESSION_STRING:
    print("🚀 UNTHROTTLED MODE: User String Session Detected! Bypassing Bot Speed Limits.", flush=True)
    tg_client = Client("stremio_session", session_string=SESSION_STRING)
else:
    print("⚠️ BOT MODE: Running via Bot Token. (For premium 4K unthrottled speed, generate a SESSION_STRING variable)", flush=True)
    tg_client = Client("stremio_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 🎬 ADVANCED MEDIA CLASSIFIER & METADATA PARSER
def parse_and_fetch_metadata(raw_title):
    try:
        clean = re.sub(r'\.(mkv|mp4|avi|mov|webm)$', '', raw_title, flags=re.IGNORECASE)
        clean = clean.replace('.', ' ').replace('_', ' ')
        
        # Determine if file is a Series episode (detecting S01E01, Season 1, Ep 2 formats)
        is_series = False
        season = 1
        episode = 1
        
        series_match = re.search(r's(\d+)\s*e(\d+)', clean, re.IGNORECASE)
        if series_match:
            is_series = True
            season = int(series_match.group(1))
            episode = int(series_match.group(2))
        else:
            ep_match = re.search(r'(v|ep|e|episode)\s*(\d+)', clean, re.IGNORECASE)
            if ep_match:
                is_series = True
                episode = int(ep_match.group(2))
            if "season" in clean.lower():
                is_series = True
                sea_match = re.search(r'season\s*(\d+)', clean, re.IGNORECASE)
                if sea_match:
                    season = int(sea_match.group(1))

        # Strip standard video metadata noise
        clean = re.sub(r'(1080p|720p|2160p|4k|bluray|hdrip|web\s*dl|brrip|x264|x265|hevc|aac|hindi|english|yts|mx|s\d+e\d+|season\s*\d+|episode\s*\d+|ep\s*\d+).*', '', clean, flags=re.IGNORECASE)
        clean_query = clean.strip()
        
        # If fallback cleaning leaves nothing, salvage the original text
        if len(clean_query) < 2:
            clean_query = raw_title[:30]

        encoded_query = urllib.parse.quote(clean_query)
        media_type = "series" if is_series else "movie"
        
        # Query the correct corresponding database catalog
        res = requests.get(f"https://v3-cinemeta.strem.io/catalog/{media_type}/top/search={encoded_query}.json", timeout=5).json()
        metas = res.get("metas", [])
        
        if metas:
            return {
                "imdb_id": metas[0].get("id"),
                "display_name": metas[0].get("name"),
                "poster": metas[0].get("poster"),
                "description": metas[0].get("description", "Ready to Stream"),
                "type": media_type,
                "season": season,
                "episode": episode
            }
    except Exception as e:
        print(f"Metadata extraction error: {e}", flush=True)
        
    return {
        "imdb_id": None, 
        "display_name": raw_title, 
        "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg", 
        "description": "Synced Cloud File Stream",
        "type": "movie",
        "season": 1,
        "episode": 1
    }

# 📡 HTTP CHAT PROCESSOR LOOP
def telegram_polling_loop():
    print("🟢 TELEGRAM INCOMING PIPELINE ACTIVE", flush=True)
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
                    reply = "🟢 High-Speed Extraction Engine Active!\n\nForward movie text links or raw media files here to sync them instantly."
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue
                
                # Intercept Raw File Messages
                media = msg.get("video") or msg.get("document")
                if media and ("video" in media.get("mime_type", "") or media.get("file_name", "").endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm'))):
                    file_id = media.get("file_id")
                    raw_name = media.get("file_name", "Telegram Video Stream")
                    file_size = media.get("file_size")
                    
                    render_domain = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
                    if not render_domain:
                        render_domain = "https://my-stremio-bot-1.onrender.com"
                    
                    live_stream_url = f"{render_domain}/watch/{file_id}"
                    meta = parse_and_fetch_metadata(raw_name)
                    
                    streams_col.insert_one({
                        "file_name": meta["display_name"],
                        "tg_url": live_stream_url,
                        "file_id": file_id,
                        "file_size": file_size,
                        "imdb_id": meta["imdb_id"],
                        "poster": meta["poster"],
                        "description": meta["description"],
                        "type": meta["type"],
                        "season": meta["season"],
                        "episode": meta["episode"]
                    })
                    
                    reply = f"✅ Synced as [{meta['type'].upper()}]!\n📁 {meta['display_name']} " + (f"(S{meta['season']}E{meta['episode']})" if meta['type'] == 'series' else "")
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue
                
                # Intercept Text Links
                if "http" in text_content or "Stream Link" in text_content:
                    urls = re.findall(r'(https?://\S+)', text_content)
                    stream_urls = [u for u in urls if "stream" in u or "dl" in u or "vault" in u]
                    final_url = stream_urls[0] if stream_urls else (urls[0] if urls else None)
                    if final_url:
                        file_name = "Extracted Video Stream"
                        name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
                        if name_match:
                            file_name = name_match.group(1).split("\n")[0].strip()
                        
                        meta = parse_and_fetch_metadata(file_name)
                        streams_col.insert_one({
                            "file_name": meta["display_name"],
                            "tg_url": final_url,
                            "imdb_id": meta["imdb_id"],
                            "poster": meta["poster"],
                            "description": meta["description"],
                            "type": meta["type"],
                            "season": meta["season"],
                            "episode": meta["episode"]
                        })
                        reply = f"✅ Link Synced as [{meta['type'].upper()}]!\n📁 {meta['display_name']}"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
            if not results:
                time.sleep(1)
        except Exception:
            time.sleep(2)

# 📡 STREMIO PLATFORM INTERFACE ENDPOINTS
async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram",
        "version": "5.0.0",
        "name": "Telegram Library",
        "description": "Multi-classification unthrottled streaming engine.",
        "resources": ["catalog", "meta", "stream"],
        "types": ["movie", "series"],
        "catalogs": [
            {"type": "movie", "id": "tg_catalog", "name": "Telegram Library"},
            {"type": "series", "id": "tg_series_catalog", "name": "Telegram Library"}
        ]
    }, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"})

async def catalog_route(request):
    req_type = request.match_info['type']
    metas = []
    try:
        # Dynamically filters items by requested catalog type (movie vs series)
        for doc in streams_col.find({"type": req_type}).sort("_id", -1).limit(100):
            item_id = doc.get("imdb_id") if doc.get("imdb_id") else f"tg_custom_{str(doc['_id'])}"
            metas.append({
                "id": item_id,
                "type": req_type,
                "name": doc["file_name"],
                "poster": doc.get("poster"),
                "description": doc.get("description")
            })
    except Exception as e:
        print(f"🔴 Catalog Fetch Error: {e}", flush=True)
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*"})

async def meta_route(request):
    req_type = request.match_info['type']
    raw_id = request.match_info['id'].replace(".json", "").split(":")[-1]
    try:
        if raw_id.startswith("tt"):
            # Fetch structural description directly from Stremio Cinemeta mirrors
            res = requests.get(f"https://v3-cinemeta.strem.io/meta/{req_type}/{raw_id}.json", timeout=5).json()
            meta_data = res.get("meta", {})
            
            # If a Series is requested, append the custom streaming episodes structure to the layout
            if req_type == "series" and meta_data:
                db_eps = streams_col.find({"imdb_id": raw_id, "type": "series"})
                episodes_list = []
                for ep_doc in db_eps:
                    ep_id = f"{raw_id}:{ep_doc.get('season', 1)}:{ep_doc.get('episode', 1)}"
                    episodes_list.append({
                        "id": ep_id,
                        "title": f"Episode {ep_doc.get('episode', 1)}: {ep_doc.get('file_name')}",
                        "season": ep_doc.get("season", 1),
                        "episode": ep_doc.get("episode", 1)
                    })
                if episodes_list:
                    meta_data["episodes"] = episodes_list
                    return web.json_response({"meta": meta_data}, headers={"Access-Control-Allow-Origin": "*"})
            return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
            
        from bson.objectid import ObjectId
        doc = streams_col.find_one({"_id": ObjectId(raw_id)})
        if doc:
            return web.json_response({"meta": {
                "id": f"tg_custom_{str(doc['_id'])}",
                "type": req_type,
                "name": doc["file_name"],
                "poster": doc.get("poster"),
                "description": doc.get("description")
            }}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception:
        pass
    return web.json_response({"meta": {}}, headers={"Access-Control-Allow-Origin": "*"})

async def stream_route(request):
    raw_id = request.match_info['id'].replace(".json", "")
    
    # Handle both movie IDs and segmented series formats (imdb:season:episode)
    parts = raw_id.split(":")
    imdb_id = parts[0]
    
    streams = []
    try:
        query = {"imdb_id": imdb_id}
        if len(parts) == 3:  # If it matches a series format
            query["season"] = int(parts[1])
            query["episode"] = int(parts[2])
            
        doc = streams_col.find_one(query)
        if not doc and not imdb_id.startswith("tt"):
            from bson.objectid import ObjectId
            try: doc = streams_col.find_one({"_id": ObjectId(imdb_id)})
            except: pass
            
        if doc and "tg_url" in doc:
            streams.append({"title": f"🎬 Stream: {doc['file_name']}", "url": doc["tg_url"]})
    except Exception as e:
        print(f"🔴 Stream Routing Error: {e}", flush=True)
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*"})

# ⚡ LIVE MULTI-CHUNK DATA TRANSFERRED HOOK
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    file_size = doc["file_size"] if doc else None
    file_name = doc["file_name"] if doc else "stream.mkv"
    
    range_header = request.headers.get("Range", "")
    start_byte = 0
    if range_header and "bytes=" in range_header:
        try: start_byte = int(range_header.split("bytes=")[1].split("-")[0])
        except: start_byte = 0

    chunk_size = 1024 * 1024
    offset_chunks = start_byte // chunk_size
    
    status = 206 if start_byte > 0 else 200
    headers = {
        "Content-Type": "video/mp4",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Accept-Ranges": "bytes"
    }
    
    if file_size:
        headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        if start_byte > 0:
            headers["Content-Range"] = f"bytes {start_byte}-{file_size-1}/{file_size}"
            headers["Content-Length"] = str(file_size - start_byte)
        else:
            headers["Content-Length"] = str(file_size)
            
    response = web.StreamResponse(status=status, headers=headers)
    await response.prepare(request)
    
    try:
        buffer = bytearray()
        buffer_target_size = 2 * 1024 * 1024  # Increased to 2MB aggregation blocks for faster 4K transfer
        
        async for chunk in tg_client.stream_media(file_id, offset=offset_chunks):
            buffer.extend(chunk)
            if len(buffer) >= buffer_target_size:
                await response.write(buffer)
                buffer = bytearray()
        if buffer:
            await response.write(buffer)
    except Exception:
        pass
    return response

async def main():
    app = web.Application()
    app.router.add_get('/', manifest_route)
    app.router.add_get('/manifest.json', manifest_route)
    app.router.add_get('/catalog/{type}/{id}.json', catalog_route)
    app.router.add_get('/meta/{type}/{id}.json', meta_route)
    app.router.add_get('/stream/{type}/{id}.json', stream_route)
    app.router.add_get('/watch/{file_id}', watch_route)
    
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    print(f"🟢 Stremio Core Router hosting on port {PORT}", flush=True)
    
    await tg_client.start()
    print("🟢 MTProto Streaming Tunnel connected successfully!", flush=True)
    
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
