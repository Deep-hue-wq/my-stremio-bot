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
PORT = int(os.getenv("PORT", 10000))

print("\n=== HYBRID CORE: HIGH-SPEED MEDIA PROTOCOL ONLINE ===", flush=True)

# Connect Secure Database Storage
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams

# Forcefully wipe any stuck webhook hooks on Telegram routing databases
try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
except Exception:
    pass

# Initialize MTProto Streaming Asset (Imported safely after loop generation)
from pyrogram import Client, filters
tg_client = Client("stremio_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 🎬 CINEMATIC POSTER MATCH ENGINE: Automatically queries Stremio's database for official artwork
def fetch_movie_metadata(raw_title):
    try:
        clean = re.sub(r'\.(mkv|mp4|avi|mov|webm)$', '', raw_title, flags=re.IGNORECASE)
        clean = clean.replace('.', ' ').replace('_', ' ')
        clean = re.sub(r'(1080p|720p|2160p|bluray|web-dl|brrip|x264|x265|hevc|aac|hindi|english|yts|mx).*', '', clean, flags=re.IGNORECASE)
        clean_query = clean.strip()
        
        encoded_query = urllib.parse.quote(clean_query)
        res = requests.get(f"https://v3-cinemeta.strem.io/catalog/movie/top/search={encoded_query}.json", timeout=5).json()
        metas = res.get("metas", [])
        if metas:
            return {
                "imdb_id": metas[0].get("id"),
                "display_name": metas[0].get("name"),
                "poster": metas[0].get("poster"),
                "description": metas[0].get("description", "Ready to Stream Natively")
            }
    except Exception:
        pass
    return {
        "imdb_id": None, 
        "display_name": raw_title, 
        "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg", 
        "description": "Cloud Stream Layout Loaded Successfully"
    }

# 📡 1. BULLETPROOF NATIVE HTTP TELEGRAM ENGINE (Immune to Python 3.14 deadlocks)
def telegram_polling_loop():
    print("🟢 TELEGRAM DETECTION LOOP: ACTIVE AND SCANNING", flush=True)
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
                    reply = "🟢 High-Speed Extraction Engine Active!\n\n• Forward link text blocks to sync them.\n• Forward raw media files directly to play them with full poster matching!"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue
                
                # 🚀 INTERCEPT RAW VIDEO ATTACHMENTS (Lucy / FiLE Ai items)
                media = msg.get("video") or msg.get("document")
                if media and ("video" in media.get("mime_type", "") or media.get("file_name", "").endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm'))):
                    file_id = media.get("file_id")
                    raw_name = media.get("file_name", "Telegram Video Stream")
                    file_size = media.get("file_size")
                    
                    render_domain = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
                    if not render_domain:
                        render_domain = "https://my-stremio-bot-1.onrender.com"
                    
                    live_stream_url = f"{render_domain}/watch/{file_id}"
                    meta = fetch_movie_metadata(raw_name)
                    
                    streams_col.insert_one({
                        "file_name": meta["display_name"],
                        "tg_url": live_stream_url,
                        "file_id": file_id,
                        "file_size": file_size,
                        "imdb_id": meta["imdb_id"],
                        "poster": meta["poster"],
                        "description": meta["description"]
                    })
                    
                    reply = f"✅ Raw Video File Synced!\n\n📁 {meta['display_name']}\n\nConverted and added to Stremio with official cinematic posters!"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                    continue
                
                # 🎬 INTERCEPT TEXT STREAM LINKS (StreamVault Pro)
                if "http" in text_content or "Stream Link" in text_content:
                    urls = re.findall(r'(https?://\S+)', text_content)
                    stream_urls = [u for u in urls if "stream" in u or "dl" in u or "vault" in u]
                    final_url = stream_urls[0] if stream_urls else (urls[0] if urls else None)
                    
                    if final_url:
                        file_name = "Extracted Stream Source Link"
                        name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
                        if name_match:
                            file_name = name_match.group(1).split("\n")[0].strip()
                        else:
                            first_line = text_content.split("\n")[0]
                            if len(first_line) > 5:
                                file_name = first_line.strip()
                        
                        meta = fetch_movie_metadata(file_name)
                        streams_col.insert_one({
                            "file_name": meta["display_name"],
                            "tg_url": final_url,
                            "imdb_id": meta["imdb_id"],
                            "poster": meta["poster"],
                            "description": meta["description"]
                        })
                        
                        reply = f"✅ Automated Sync Complete!\n\n📁 {meta['display_name']}\n\nhas been pushed to Stremio with poster configuration!"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
            
            if not results:
                time.sleep(1)
        except Exception:
            time.sleep(2)

# 📡 2. STREMIO LAYER ROUTER SYSTEM
async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram",
        "version": "4.0.0",
        "name": "Telegram Library",
        "description": "Instant cloud video playback engine.",
        "resources": ["catalog", "meta", "stream"],
        "types": ["movie"],
        "catalogs": [{"type": "movie", "id": "tg_catalog", "name": "Telegram Library"}]
    }, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"})

async def catalog_route(request):
    metas = []
    try:
        for doc in streams_col.find().sort("_id", -1).limit(100):
            item_id = doc.get("imdb_id") if doc.get("imdb_id") else f"tg_custom:{str(doc['_id'])}"
            metas.append({
                "id": item_id,
                "type": "movie",
                "name": doc["file_name"],
                "poster": doc.get("poster"),
                "description": doc.get("description")
            })
    except Exception as e:
        print(f"🔴 Catalog Error: {e}", flush=True)
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*"})

async def meta_route(request):
    raw_id = request.match_info['id'].replace(".json", "").split(":")[-1]
    try:
        if raw_id.startswith("tt"):
            res = requests.get(f"https://v3-cinemeta.strem.io/meta/movie/{raw_id}.json", timeout=5).json()
            return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
        
        from bson.objectid import ObjectId
        doc = streams_col.find_one({"_id": ObjectId(raw_id)})
        if doc:
            return web.json_response({"meta": {
                "id": f"tg_custom:{str(doc['_id'])}",
                "type": "movie",
                "name": doc["file_name"],
                "poster": doc.get("poster"),
                "description": doc.get("description")
            }}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception:
        pass
    return web.json_response({"meta": {}}, headers={"Access-Control-Allow-Origin": "*"})

async def stream_route(request):
    raw_id = request.match_info['id'].replace(".json", "").split(":")[-1]
    streams = []
    try:
        doc = streams_col.find_one({"imdb_id": raw_id}) if raw_id.startswith("tt") else None
        if not doc:
            from bson.objectid import ObjectId
            try:
                doc = streams_col.find_one({"_id": ObjectId(raw_id)})
            except:
                pass
        if doc and "tg_url" in doc:
            streams.append({"title": "🎬 Play Stream Live", "url": doc["tg_url"]})
    except Exception as e:
        print(f"🔴 Stream Error: {e}", flush=True)
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*"})

# ⚡ 3. LIVE SEEK-AWARE TUNNEL STREAM ROUTER (Supports instant timeline fast-forwarding)
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    file_size = doc["file_size"] if doc else None
    file_name = doc["file_name"] if doc else "stream.mkv"
    
    # Check for HTTP Range headers from Stremio to calculate timeline position
    range_header = request.headers.get("Range", "")
    start_byte = 0
    if range_header and "bytes=" in range_header:
        try:
            start_byte = int(range_header.split("bytes=")[1].split("-")[0])
        except Exception:
            start_byte = 0

    # Telegram/Pyrogram chunk partition index is 1 MiB (1,048,576 bytes)
    chunk_size = 1024 * 1024
    offset_chunks = start_byte // chunk_size
    
    status = 206 if start_byte > 0 else 200
    headers = {
        "Content-Type": "video/mp4",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Accept-Ranges": "bytes"  # Crucial: Unlocks scrubbing timelines on player
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
        # Request data pipeline starting directly from the skipped block location offset
        async for chunk in tg_client.stream_media(file_id, offset=offset_chunks):
            await response.write(chunk)
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
    print(f"🟢 Stremio Core Router active on port {PORT}", flush=True)
    
    await tg_client.start()
    print("🟢 MTProto Streaming Tunnel connected successfully!", flush=True)
    
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
