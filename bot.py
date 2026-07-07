import asyncio
# 🛡️ SYSTEM FIX: Force-initialize the core event loop environment for Python 3.14 immediately
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
import json
import requests
import urllib.parse
from aiohttp import web
from pymongo import MongoClient

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
PORT = int(os.getenv("PORT", 10000))

# Pre-clear any lingering webhook blocks on Telegram's core database
try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
except Exception:
    pass

# Safe-import the MTProto client system
from pyrogram import Client, filters

print("\n=== INITIALIZING MASTER TELEGRAM STREMIO ENGINE ===", flush=True)

# Connect Secure Database Storage
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams

# Initialize High-Speed Tunnel Client
tg_client = Client("stremio_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 🎬 AUTOMATED METADATA SCRAPER: Fetches official posters & details using Stremio's core database
def fetch_movie_poster(raw_title):
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
    return {"imdb_id": None, "display_name": raw_title, "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg", "description": "Stream Ready"}

# 📥 1. PARSE INCOMING TEXT LINKS (StreamVault Pro)
@tg_client.on_message(filters.text | filters.caption)
async def text_link_handler(client, message):
    text_content = message.text or message.caption or ""
    if text_content.startswith("/start"):
        await message.reply_text("🟢 High-Speed Cloud Streaming Engine Active!\n\nForward text links or raw movie files here to sync them instantly.")
        return

    if "http" in text_content or "Stream Link" in text_content:
        urls = re.findall(r'(https?://\S+)', text_content)
        stream_urls = [u for u in urls if "stream" in u or "dl" in u or "vault" in u]
        final_url = stream_urls[0] if stream_urls else (urls[0] if urls else None)
        
        if final_url:
            file_name = "Extracted Video Link"
            name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
            if name_match:
                file_name = name_match.group(1).split("\n")[0].strip()
            
            meta = fetch_movie_poster(file_name)
            streams_col.insert_one({
                "file_name": meta["display_name"],
                "tg_url": final_url,
                "imdb_id": meta["imdb_id"],
                "poster": meta["poster"],
                "description": meta["description"]
            })
            await message.reply_text(f"✅ Link Added with Poster Sync!\n\n📁 {meta['display_name']}")

# 🚀 2. PARSE NATIVE VIDEO ATTACHMENTS (Lucy Files)
@tg_client.on_message(filters.video | filters.document)
async def native_file_handler(client, message):
    media = message.video or message.document
    file_name = getattr(media, 'file_name', '') or "Telegram Video Stream"
    
    if file_name.endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm')) or "video" in getattr(media, 'mime_type', ''):
        await message.reply_text("⏳ Processing movie formatting and scraping cinematic poster elements...")
        
        file_id = media.file_id
        file_size = media.file_size
        
        render_domain = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
        if not render_domain:
            render_domain = "https://my-stremio-bot-1.onrender.com"
            
        live_stream_url = f"{render_domain}/watch/{file_id}"
        meta = fetch_movie_poster(file_name)
        
        streams_col.insert_one({
            "file_name": meta["display_name"],
            "tg_url": live_stream_url,
            "file_id": file_id,
            "file_size": file_size,
            "imdb_id": meta["imdb_id"],
            "poster": meta["poster"],
            "description": meta["description"]
        })
        await message.reply_text(f"✅ Raw File Stream Engaged!\n\n📁 {meta['display_name']}\n\nConverted and added to Stremio with official posters.")

# 📡 3. STREMIO NETWORK LIFECYCLE CONTROLLERS
async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram",
        "version": "4.0.0",
        "name": "Telegram Library",
        "description": "Instant high-speed player streaming from your bot storage data cells.",
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
        print(f"🔴 Catalog compilation warning: {e}", flush=True)
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*"})

async def meta_route(request):
    raw_id = request.match_info['id'].replace(".json", "").split(":")[-1]
    try:
        # If it's a native IMDb ID, delegate the heavy rendering layout directly to Stremio
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
        # Look up match based on either IMDb ID format or custom MongoDB string reference
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
        print(f"🔴 Processing stream lookup error: {e}", flush=True)
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*"})

# ⚡ 4. LIVE CHUNK TUNNEL STREAM ENGINE
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    file_size = doc["file_size"] if doc else None
    file_name = doc["file_name"] if doc else "video.mkv"
    
    headers = {"Content-Type": "video/mp4", "Access-Control-Allow-Origin": "*"}
    if file_size:
        headers["Content-Length"] = str(file_size)
        headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        
    response = web.StreamResponse(status=200, headers=headers)
    await response.prepare(request)
    try:
        # Feeds the stream directly from Telegram cloud data centers to your player
        async for chunk in tg_client.stream_media(file_id):
            await response.write(chunk)
    except Exception:
        pass
    return response

# Combined Single-Loop Framework Engine
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
    print(f"🟢 Web Addon proxy hosting on port {PORT}", flush=True)
    
    await tg_client.start()
    print("🟢 HIGH-SPEED TELEGRAM ROUTER ONLINE AND CONNECTED", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
