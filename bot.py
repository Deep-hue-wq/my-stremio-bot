import os
import re
import asyncio
import requests
from aiohttp import web
from pymongo import MongoClient

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
PORT = int(os.getenv("PORT", 10000))

# 🧹 ANTI-HIJACK: Forcefully delete any stuck ghost webhooks from Telegram's servers
print("🧹 Cleaning stuck Telegram webhooks...", flush=True)
try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=10)
    print("✨ Telegram server cache cleared successfully!", flush=True)
except Exception as e:
    print(f"⚠️ Webhook clear bypass note: {e}", flush=True)

# Now import Pyrogram safely after the network reset
from pyrogram import Client, filters

print("\n=== UPGRADED STREMIO STREAM ENGINE ONLINE ===", flush=True)

# Connect Global Database
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams

# Initialize MTProto Streaming Client
tg_client = Client("stremio_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 🎬 1. PARSE INCOMING TEXT LINKS (StreamVault Pro Layouts)
@tg_client.on_message(filters.text | filters.caption)
async def text_link_handler(client, message):
    text_content = message.text or message.caption or ""
    if text_content.startswith("/start"):
        reply = "🟢 High-Speed Extraction Engine Natively Active!\n\n• Forward raw movie files directly here to play them.\n• Forward link text blocks to sync them automatically."
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
            await message.reply_text(f"✅ Text Link Synced to Stremio!\n📁 {file_name}")

# 🚀 2. PARSE RAW VIDEO ATTACHMENTS (Lucy Files)
@tg_client.on_message(filters.video | filters.document)
async def native_file_handler(client, message):
    media = message.video or message.document
    file_name = getattr(media, 'file_name', '') or "Telegram Video Stream"
    
    if file_name.endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm')) or "video" in getattr(media, 'mime_type', ''):
        file_id = media.file_id
        file_size = media.file_size
        
        # Pull the dynamic Render URL domain directly from the server layout configuration
        render_domain = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
        if not render_domain:
            render_domain = "https://my-stremio-bot.onrender.com"
            
        live_stream_url = f"{render_domain}/watch/{file_id}"
        
        streams_col.insert_one({
            "file_name": file_name,
            "tg_url": live_stream_url,
            "file_id": file_id,
            "file_size": file_size
        })
        await message.reply_text(f"✅ Raw Video File Synced to Stremio!\n📁 {file_name}")

# 📡 3. STREMIO LAYER ROUTER CORES
async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram",
        "version": "3.0.0",
        "name": "Telegram Library",
        "description": "Instant high-speed video streams synced from your bot.",
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
        print(f"🔴 Catalog Error: {e}", flush=True)
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
                "title": f"🎬 Play Live Stream",
                "url": doc["tg_url"]
            })
    except Exception as e:
        print(f"🔴 Stream Engine Translation Block: {e}", flush=True)
        
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*"})

# ⚡ 4. CHUNK PROXIER (Streams file directly from cloud arrays without utilizing local storage)
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    file_size = doc["file_size"] if doc else None
    file_name = doc["file_name"] if doc else "stream.mkv"
    
    headers = {"Content-Type": "video/mp4", "Access-Control-Allow-Origin": "*"}
    if file_size:
        headers["Content-Length"] = str(file_size)
        headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        
    response = web.StreamResponse(status=200, headers=headers)
    await response.prepare(request)
    try:
        async for chunk in tg_client.stream_media(file_id):
            await response.write(chunk)
    except Exception:
        pass
    return response

# Clean integration into Python 3.14 Event lifecycle loop
async def startup_bridge(app):
    await tg_client.start()
    print("🟢 HIGH-SPEED TELEGRAM STREAM TUNNEL INSTANTIATED", flush=True)

async def shutdown_bridge(app):
    await tg_client.stop()

if __name__ == "__main__":
    app = web.Application()
    app.on_startup.append(startup_bridge)
    app.on_cleanup.append(shutdown_bridge)
    
    app.router.add_get('/', manifest_route)
    app.router.add_get('/manifest.json', manifest_route)
    app.router.add_get('/catalog/{type}/{id}.json', catalog_route)
    app.router.add_get('/stream/{type}/{id}.json', stream_route)
    app.router.add_get('/watch/{file_id}', watch_route)
    
    web.run_app(app, host="0.0.0.0", port=PORT)
