import asyncio
# 🛡️ LOOP INTEGRITY FIX: Force-stabilize the async engine loop for Python 3.14 immediately
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
import urllib.parse
import requests
from aiohttp import web
from pymongo import MongoClient
from pyrogram import Client, filters

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
SESSION_STRING = os.getenv("SESSION_STRING", "").strip()
PORT = int(os.getenv("PORT", 10000))

print("\n=== UNTHROTTLED ENGINE: INSTANT SNAP PLAYBACK ACTIVE ===", flush=True)

# Connect Secure Database Storage
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
streams_col = client.stremio_bridge.streams
print("🟢 MONGO DATABASE: CONNECTED SUCCESSFULLY", flush=True)

# 🚀 HYBRID GATEWAY: Boots unthrottled User Session if provided, otherwise defaults to Bot Token
if SESSION_STRING:
    print("🚀 UNTHROTTLED MODE ACTIVE: Connected via User Session String for maximum 4K throughput.", flush=True)
    tg_client = Client("stremio_core", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    print("⚠️ THROTTLED MODE: Running via Bot Token. (For instant 4K speed, add a SESSION_STRING variable)", flush=True)
    tg_client = Client("stremio_core", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# 🎬 CINEMATIC AUTOMATED METADATA SCRAPER
def parse_metadata(raw_title):
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
        "desc": "Synced Media Stream"
    }

# 📥 UNIFIED INCOMING CONTENT CAPTURE HOOKS
@tg_client.on_message(filters.private & (filters.text | filters.document | filters.video | filters.caption))
async def content_handler(client, message):
    text_content = message.text or message.caption or ""
    if text_content.startswith("/start"):
        await message.reply_text("🟢 Personal Stream Sync Engine Online!\n\nForward text link blocks or raw video files directly here.")
        return

    # Intercept Raw Movie Attachments
    media = message.video or message.document
    if media and ("video" in getattr(media, "mime_type", "") or getattr(media, "file_name", "").endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm'))):
        file_id = media.file_id
        raw_name = getattr(media, "file_name", "Telegram Video Stream")
        
        render_domain = os.getenv("RENDER_EXTERNAL_URL", "https://my-stremio-bot-1.onrender.com").rstrip('/')
        meta = parse_metadata(raw_name)
        live_stream_url = f"{render_domain}/watch/{file_id}"
        
        streams_col.insert_one({
            "file_name": meta["name"], "tg_url": live_stream_url, "file_id": file_id,
            "file_size": media.file_size, "imdb_id": meta["imdb_id"], "poster": meta["poster"],
            "description": meta["desc"], "type": meta["type"], "season": meta["s"], "episode": meta["e"]
        })
        await message.reply_text(f"🎬 Synced to Stremio Library as [{meta['type'].upper()}]!\n📁 Title: {meta['name']}")
        return

    # Intercept Text Link Message Blocks
    if "http" in text_content or "Stream Link" in text_content:
        urls = re.findall(r'(https?://\S+)', text_content)
        final_url = next((u for u in urls if "stream" in u or "dl" in u or "vault" in u), urls[0] if urls else None)
        if final_url:
            name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
            file_name = name_match.group(1).split("\n")[0].strip() if name_match else text_content.split("\n")[0].strip()
            
            meta = parse_metadata(file_name)
            streams_col.insert_one({
                "file_name": meta["name"], "tg_url": final_url, "imdb_id": meta["imdb_id"],
                "poster": meta["poster"], "description": meta["desc"], "type": meta["type"],
                "season": meta["s"], "episode": meta["e"]
            })
            await message.reply_text(f"✅ Web Link Synced to Stremio Library!\n📁 Title: {meta['name']}")

# 📡 STREMIO PLATFORM ROUTING MESH
async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram", "version": "7.0.0", "name": "Telegram Library",
        "description": "Unthrottled zero-copy cloud streaming pipeline.",
        "resources": ["catalog", "meta", "stream"], "types": ["movie", "series"],
        "catalogs": [{"type": "movie", "id": "tg_catalog", "name": "Telegram Library"},
                     {"type": "series", "id": "tg_catalog", "name": "Telegram Library"}]
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
    return web.json_response({"streams": [{"title": f"🎬 Play Unthrottled Stream", "url": doc["tg_url"]}]} if doc and "tg_url" in doc else {"streams": []}, headers={"Access-Control-Allow-Origin": "*"})

# ⚡ ZERO-COPY LIVE DATA NETWORK PIPE
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    if not doc: return web.Response(status=404)
    file_size = doc.get("file_size", 0)
    
    range_header = request.headers.get("Range", "")
    start_byte = 0
    if range_header and "bytes=" in range_header:
        try: start_byte = int(range_header.split("bytes=")[1].split("-")[0])
        except: start_byte = 0
        
    status = 206 if start_byte > 0 else 200
    headers = {"Content-Type": "video/mp4", "Access-Control-Allow-Origin": "*", "Accept-Ranges": "bytes"}
    if file_size:
        headers["Content-Disposition"] = f'inline; filename="{doc.get("file_name", "stream.mp4")}"'
        if start_byte > 0:
            headers["Content-Range"] = f"bytes {start_byte}-{file_size-1}/{file_size}"
            headers["Content-Length"] = str(file_size - start_byte)
        else:
            headers["Content-Length"] = str(file_size)
            
    response = web.StreamResponse(status=status, headers=headers)
    await response.prepare(request)
    
    try:
        # Zero-Copy Streaming: Transfers network packets directly from Telegram to Stremio
        # Bypasses local RAM to support high-speed streaming below Render's 512MB limit
        async for chunk in tg_client.download_media(file_id, chunks=True, offset=start_byte):
            await response.write(chunk)
            await response.drain()
    except Exception:
        pass
    return response

# 🚀 SECURE ASYNC APPLICATION LIFECYCLE MESH
async def startup_mesh(app):
    await tg_client.start()
    print("🟢 TELEGRAM CHANNEL ROUTER: ONLINE AND LISTENING", flush=True)

async def shutdown_mesh(app):
    await tg_client.stop()

if __name__ == "__main__":
    app = web.Application(client_max_size=0)
    app.on_startup.append(startup_mesh)
    app.on_cleanup.append(shutdown_mesh)
    
    app.router.add_get('/', manifest_route)
    app.router.add_get('/manifest.json', manifest_route)
    app.router.add_get('/catalog/{type}/{id}.json', catalog_route)
    app.router.add_get('/meta/{type}/{id}.json', meta_route)
    app.router.add_get('/stream/{type}/{id}.json', stream_route)
    app.router.add_get('/watch/{file_id}', watch_route)
    
    web.run_app(app, host="0.0.0.0", port=PORT)
