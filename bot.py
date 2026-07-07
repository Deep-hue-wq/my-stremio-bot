# 🛡️ PYTHON 3.14 SEMANTICS FIX: Patches the strict asyncio event loop policy before loading Pyrogram
import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
from aiohttp import web
from pymongo import MongoClient
from pyrogram import Client, filters

# Load Core Configurations Safely
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
PORT = int(os.getenv("PORT", 10000))

# Fallback URL generator if Render domain key is missing
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
if not RENDER_URL:
    RENDER_URL = "https://my-stremio-bot.onrender.com"

print("\n=== UPGRADED STREMIO STREAM ENGINE ONLINE ===", flush=True)

# Secure DB Connection Setup
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams

# Spin up MTProto Pyrogram Engine
tg_client = Client("stremio_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 🎬 1. CAPTURE TEXT LINKS (StreamVault Pro Layouts)
@tg_client.on_message(filters.text | filters.caption)
async def text_link_handler(client, message):
    text_content = message.text or message.caption or ""
    if text_content.startswith("/start"):
        reply = "🟢 Extraction Engine Online!\n\n• Forward raw movie files directly here to play them.\n• Forward link text blocks to sync them automatically."
        await message.reply_text(reply)
        return

    if "http" in text_content or "Stream Link" in text_content:
        urls = re.findall(r'(https?://\S+)', text_content)
        stream_urls = [u for u in urls if "stream" in u or "dl" in u or "vault" in u]
        final_url = stream_urls[0] if stream_urls else (urls[0] if urls else None)
        
        if final_url:
            file_name = "Synced Media Link"
            name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
            if name_match:
                file_name = name_match.group(1).split("\n")[0].strip()
            else:
                first_line = text_content.split("\n")[0]
                if len(first_line) > 5:
                    file_name = first_line.strip()
            
            file_name = file_name.replace("*", "").replace("_", " ").strip()
            streams_col.insert_one({"file_name": file_name, "tg_url": final_url})
            await message.reply_text(f"✅ Text Link Synced!\n📁 {file_name}")

# 🚀 2. CAPTURE RAW FORWARDED TELEGRAM VIDEO ATTACHMENTS (Lucy Files)
@tg_client.on_message(filters.video | filters.document)
async def native_file_handler(client, message):
    media = message.video or message.document
    file_name = getattr(media, 'file_name', '') or "Telegram Video Stream"
    
    if file_name.endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm')) or "video" in getattr(media, 'mime_type', ''):
        file_id = media.file_id
        file_size = media.file_size
        
        # Point Stremio playback requests back to our high-speed stream router
        live_stream_url = f"{RENDER_URL}/watch/{file_id}"
        
        streams_col.insert_one({
            "file_name": file_name,
            "tg_url": live_stream_url,
            "file_id": file_id,
            "file_size": file_size
        })
        await message.reply_text(f"✅ Raw Video File Synced To Stremio!\n📁 {file_name}")

# 📡 3. STREMIO ADDON INTERFACE MANAGER
async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram",
        "version": "2.0.0",
        "name": "Telegram Library",
        "description": "Instant high-speed video streams matched from your personal bot files.",
        "resources": ["catalog", "stream"],
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
                "description": "Ready to Stream Natively"
            })
    except Exception as e:
        print(f"🔴 Catalog Generation Error: {e}", flush=True)
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*"})

async def stream_route(request):
    raw_id = request.match_info['id']
    clean_id = raw_id.replace(".json", "").split(":")[-1]
    
    streams = []
    try:
        from bson.objectid import ObjectId
        doc = streams_col.find_one({"_id": ObjectId(clean_id)})
        if doc and "tg_url" in doc:
            streams.append({
                "title": f"🎬 Stream Live: {doc['file_name']}",
                "url": doc["tg_url"]
            })
    except Exception as e:
        print(f"🔴 Stream Request Mapping Error: {e}", flush=True)
        
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*"})

# ⚡ 4. LIVE STREAM STORAGE BRIDGE (Feeds data to video player in fast chunks)
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    file_size = doc["file_size"] if doc else None
    file_name = doc["file_name"] if doc else "stream.mkv"
    
    headers = {
        "Content-Type": "video/mp4",
        "Access-Control-Allow-Origin": "*",
    }
    if file_size:
        headers["Content-Length"] = str(file_size)
        headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        
    response = web.StreamResponse(status=200, headers=headers)
    await response.prepare(request)
    
    try:
        # Feeds the video data line straight from Telegram core server to Stremio on-the-fly
        async for chunk in tg_client.stream_media(file_id):
            await response.write(chunk)
    except Exception:
        pass
    return response

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', manifest_route)
    app.router.add_get('/manifest.json', manifest_route)
    app.router.add_get('/catalog/{type}/{id}.json', catalog_route)
    app.router.add_get('/stream/{type}/{id}', stream_route)
    app.router.add_get('/watch/{file_id}', watch_route)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    print(f"🟢 Web Addon server listening on port {PORT}", flush=True)

async def main():
    await start_web_server()
    await tg_client.start()
    print("🟢 HIGH-SPEED TELEGRAM STREAM TUNNEL INSTANTIATED", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
