import asyncio
# 🛡️ EVENT LOOP PROTECTION: Stabilizes async execution environment for Python 3.14
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
import hashlib
from aiohttp import web
from pymongo import MongoClient
from pyrogram import Client

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
# Using your provided Storage1 cluster as the default connection!
MONGO_URI = os.getenv("MONGO_URI1", "mongodb+srv://deepthanki1111:Lexh54sjL9BAggp0@storage1.cwhzyf9.mongodb.net/?appName=Storage1").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
PORT = int(os.getenv("PORT", 10000))

# 🔑 TMDB API KEY FOR FLAWLESS SERIES METADATA
TMDB_API_KEY = "d8e9f93d8a60953c67c8756c446c72fb"

print("\n=== STARTING CORE: SPIDERMAN FAST-STREAM ACTIVE (TMDB EDITION) ===", flush=True)

# Connect Database Storage Grid
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams
print("🟢 MONGO DATABASE: CONNECTED SUCCESSFULLY", flush=True)

try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
    print("🧹 Webhook cache cleared successfully!", flush=True)
except Exception:
    pass

# Initialize Pyrogram purely as a passive asset for file downloads
tg_client = Client("stremio_fine_wine", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# 🎬 CINEMATIC POSTER & SERIES METADATA MATCHING (POWERED BY TMDB)
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

        # Strip resolution and encoder tags to get pure movie/series name
        clean = re.sub(r'(1080p|720p|2160p|4k|bluray|hdrip|web\s*dl|brrip|x264|x265|hevc|aac|hindi|english|yts|mx|s\d+e\d+|season\s*\d+|episode\s*\d+|ep\s*\d+).*', '', clean, flags=re.IGNORECASE)
        clean_query = clean.strip()
        if len(clean_query) < 2: clean_query = raw_title[:30]

        media_type = "tv" if is_series else "movie"
        stremio_type = "series" if is_series else "movie"

        # 1️⃣ SEARCH TMDB DIRECTLY FOR THE BEST ACCURACY
        tmdb_url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={TMDB_API_KEY}&query={urllib.parse.quote(clean_query)}"
        res = requests.get(tmdb_url, timeout=5).json()
        
        if res.get("results"):
            best_match = res["results"][0]
            tmdb_id = best_match.get("id")
            name = best_match.get("name") if is_series else best_match.get("title")
            poster_path = best_match.get("poster_path")
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            desc = best_match.get("overview", "")
            
            # 2️⃣ FETCH EXTERNAL IMDB ID SO STREMIO MERGES IT PERFECTLY
            ext_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
            ext_res = requests.get(ext_url, timeout=5).json()
            imdb_id = ext_res.get("imdb_id")
            
            if not imdb_id:
                # If no IMDB ID (common for some Anime/K-Dramas), generate a permanent hash ID 
                # so all episodes group under the exact same series folder in Stremio.
                imdb_id = "tg_" + hashlib.md5(name.encode()).hexdigest()[:10]

            return {
                "imdb_id": imdb_id, "name": name, "poster": poster, "desc": desc,
                "type": stremio_type, "s": season, "e": episode
            }

        # 3️⃣ FALLBACK TO STREMIO CINEMETA IF TMDB FAILS
        cm_res = requests.get(f"https://v3-cinemeta.strem.io/catalog/{stremio_type}/top/search={urllib.parse.quote(clean_query)}.json", timeout=5).json()
        if metas := cm_res.get("metas", []):
            return {
                "imdb_id": metas[0].get("id"), "name": metas[0].get("name"),
                "poster": metas[0].get("poster"), "desc": metas[0].get("description", ""),
                "type": stremio_type, "s": season, "e": episode
            }
            
    except Exception as e:
        print(f"Metadata error: {e}", flush=True)

    # 4️⃣ ABSOLUTE FALLBACK
    stable_id = "tg_" + hashlib.md5(raw_title[:15].encode()).hexdigest()[:10]
    return {
        "imdb_id": stable_id, "name": raw_title, "type": "movie" if not is_series else "series", 
        "s": season, "e": episode,
        "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg", 
        "desc": "Synced Telegram File"
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

                # Process Raw Movie/Series File Attachments
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
        "id": "org.deepsstremio.telegram", "version": "8.0.0", "name": "Telegram Library",
        "description": "Original high-speed sequential streaming proxy tunnel.",
        "resources": ["catalog", "meta", "stream"], "types": ["movie", "series"],
        "catalogs": [{"type": "movie", "id": "tg_movie", "name": "Telegram Library"},
                     {"type": "series", "id": "tg_series", "name": "Telegram Library"}]
    }, headers={"Access-Control-Allow-Origin": "*"})

async def catalog_route(request):
    req_type = request.match_info['type']
    
    # AGGREGATION: Groups episodes under ONE series poster so the catalog isn't cluttered!
    pipeline = [
        {"$match": {"type": req_type}},
        {"$sort": {"_id": -1}},
        {"$group": {"_id": "$imdb_id", "doc": {"$first": "$$ROOT"}}},
        {"$limit": 100}
    ]
    
    metas = []
    for agg in streams_col.aggregate(pipeline):
        d = agg["doc"]
        metas.append({
            "id": d["imdb_id"],
            "type": req_type,
            "name": d["file_name"],
            "poster": d.get("poster"),
            "description": d.get("description")
        })
        
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*"})

async def meta_route(request):
    req_type = request.match_info['type']
    raw_id = request.match_info['id'].replace(".json", "")

    # Native Stremio UI pass-through
    if raw_id.startswith("tt"):
        res = requests.get(f"https://v3-cinemeta.strem.io/meta/{req_type}/{raw_id}.json", timeout=5).json()
        return web.json_response(res, headers={"Access-Control-Allow-Origin": "*"})
    
    # Custom Series Handler (For K-Dramas & items without an IMDB ID)
    doc = streams_col.find_one({"imdb_id": raw_id, "type": req_type})
    if not doc:
        return web.json_response({"meta": {}}, headers={"Access-Control-Allow-Origin": "*"})
        
    meta = {
        "id": raw_id, "type": req_type, "name": doc["file_name"],
        "poster": doc.get("poster"), "description": doc.get("description", "")
    }
    
    # Inject custom episode grid so Stremio can render them properly
    if req_type == "series":
        episodes = []
        for ep in streams_col.find({"imdb_id": raw_id, "type": "series"}).sort([("season", 1), ("episode", 1)]):
            episodes.append({
                "id": f"{raw_id}:{ep['season']}:{ep['episode']}",
                "title": f"Episode {ep['episode']}",
                "season": ep["season"],
                "episode": ep["episode"]
            })
        meta["videos"] = episodes
        
    return web.json_response({"meta": meta}, headers={"Access-Control-Allow-Origin": "*"})

async def stream_route(request):
    parts = request.match_info['id'].replace(".json", "").split(":")
    imdb_id = parts[0]
    
    # Properly maps click to specific season/episode
    if len(parts) == 3:
        query = {"imdb_id": imdb_id, "season": int(parts[1]), "episode": int(parts[2])}
    else:
        query = {"imdb_id": imdb_id}
        
    streams = []
    # Find all available qualities/files for this specific episode/movie
    for doc in streams_col.find(query):
        size_mb = round(doc.get("file_size", 0) / (1024 * 1024), 2) if doc.get("file_size") else "Unknown"
        streams.append({
            "title": f"🎬 NATIVE STREAM\n💾 {size_mb} MB",
            "url": doc["tg_url"],
            "behaviorHints": {"notWebReady": True}
        })
        
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*"})

# ⚡ GOD-LEVEL STREAMING ENGINE: Full HTTP 206 Range Support & Offset Routing
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    if not doc: 
        return web.Response(status=404)
        
    file_size = doc.get("file_size", 0)
    file_name = doc.get("file_name", "stream.mp4")
    
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": "video/mp4",
        "Access-Control-Allow-Origin": "*"
    }
    
    range_header = request.headers.get("Range")
    
    if not range_header or not file_size:
        headers["Content-Length"] = str(file_size)
        headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        
        try:
            async for chunk in tg_client.stream_media(file_id):
                await response.write(chunk)
                await response.drain()
        except Exception:
            pass
        return response

    try:
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        start_byte = int(range_match.group(1))
        end_byte = int(range_match.group(2)) if range_match.group(2) else file_size - 1
    except Exception:
        start_byte = 0
        end_byte = file_size - 1

    if start_byte >= file_size:
        return web.Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    content_length = end_byte - start_byte + 1
    
    headers.update({
        "Content-Length": str(content_length),
        "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
        "Content-Disposition": f'inline; filename="{file_name}"'
    })

    response = web.StreamResponse(status=206, headers=headers)
    await response.prepare(request)

    chunk_size = 1024 * 1024  
    offset_chunks = start_byte // chunk_size
    skip_bytes = start_byte % chunk_size

    try:
        async for chunk in tg_client.stream_media(file_id, limit=0, offset=offset_chunks):
            if skip_bytes > 0:
                chunk = chunk[skip_bytes:]
                skip_bytes = 0
            
            if content_length <= len(chunk):
                await response.write(chunk[:content_length])
                await response.drain()
                break
                
            await response.write(chunk)
            await response.drain()
            content_length -= len(chunk)
            
    except ConnectionResetError:
        pass 
    except Exception as e:
        print(f"Stream interrupt: {e}", flush=True)

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
    print("🟢 MTProto Engine Connected Successfully!", flush=True)
    
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
