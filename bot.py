import os
import re
import asyncio
from aiohttp import web
from pymongo import MongoClient
from pyrogram import Client, filters

# Load Configuration Setup
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
PORT = int(os.getenv("PORT", 10000))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')

# Connect Database Storage Grid
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams

# Initialize High-Speed MTProto Engine
tg_client = Client("stremio_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

print("\n=== UPGRADED STREMIO STREAM ENGINE ONLINE ===", flush=True)

# 🎬 1. PARSE INCOMING TEXT LINKS
@tg_client.on_message(filters.text | filters.caption)
async def text_link_handler(client, message):
    text_content = message.text or message.caption or ""
    if message.text and message.text.startswith("/start"):
        reply = "🟢 High-Speed Extraction Engine Fully Active!\n\n• Forward raw video files here to stream them natively.\n• Forward text blocks containing web links to inject them directly."
        await message.reply_text(reply)
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
            else:
                first_line = text_content.split("\n")[0]
                if len(first_line) > 5:
                    file_name = first_line.strip()
            
            file_name = file_name.replace("*", "").replace("_", " ").strip()
            streams_col.insert_one({"file_name": file_name, "tg_url": final_url})
            await message.reply_text(f"✅ Link Synced to Stremio!\n\n📁 {file_name}")

# 🚀 2. CONVERT NATIVE TELEGRAM VIDEO FILES TO LIVE STREAMS
@tg_client.on_message(filters.video | filters.document)
async def native_file_handler(client, message):
    media = message.video or message.document
    mime = media.mime_type or ""
    
    # Check if the file format is a playable video stream layout
    if "video" in mime or media.file_name.endswith(('.mkv', '.mp4', '.avi', '.mov')):
        file_id = media.file_id
        file_name = media.file_name or "Telegram Media Stream"
        file_size = media.file_size
        
        # Build direct streaming proxy link targeting our Render web server
        live_stream_url = f"{RENDER_EXTERNAL_URL}/watch/{file_id}"
        
        # Commit to global catalog database
        streams_col.insert_one({
            "file_name": file_name,
            "tg_url": live_stream_url,
            "file_id": file_id,
            "file_size": file_size
        })
        print(f"💾 File converted and saved: {file_name}", flush=True)
        await message.reply_text(f"✅ Raw File Stream Engaged!\n\n📁 {file_name}\n\nConverted and injected directly to your Stremio library.")

# 📡 3. ASYNC HTTP WEBPROXY SERVER FOR STREMIO LAYOUTS
async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram",
        "version": "2.0.0",
        "name": "Telegram Cloud Addon",
        "description": "Instant video streaming feed synced straight from your telegram bot.",
        "resources": ["catalog", "stream"],
        "types": ["movie", "series"],
        "catalogs": [{"type": "movie", "id": "tg_catalog", "name": "Telegram Library"}]
    }, headers={"Access-Control-Allow-Origin": "*"})

async def catalog_route(request):
    metas = []
    try:
        for doc in streams_col.find().sort("_id", -1).limit(100):
            metas.append({
                "id": str(doc["_id"]),
                "type": "movie",
                "name": doc["file_name"],
                "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg",
                "description": "Click to stream directly from Cloud Storage"
            })
    except Exception as e:
        print(f"🔴 Catalog Fetch Error: {e}", flush=True)
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*"})

async def stream_route(request):
    doc_id = request.match_info['id'].split(".json")[0].split(":")[-1]
    from bson.objectid import ObjectId
    doc = streams_col.find_one({"_id": ObjectId(doc_id)})
    streams = []
    if doc and "tg_url" in doc:
        streams.append({"title": f"🎬 Play: {doc['file_name']}", "url": doc["tg_url"]})
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*"})

# ⚡ 4. LIVE CHUNK PIPELINE STREAMER (Bypasses Local Disk Completely)
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    file_size = doc["file_size"] if doc else None
    file_name = doc["file_name"] if doc else "video.mkv"
    
    headers = {
        "Content-Type": "video/mp4",
        "Access-Control-Allow-Origin": "*",
    }
    if file_size:
        headers["Content-Length"] = str(file_size)
        headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
        
    response = web.StreamResponse(status=200, headers=headers)
    await response.prepare(request)
    
    try:
        # Stream chunks directly from Telegram's Core DC directly to the HTTP line
        async for chunk in tg_client.stream_media(file_id):
            await response.write(chunk)
    except Exception as e:
        print(f"⚠️ Stream connection closure or seek reset: {e}", flush=True)
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
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🟢 Web Router actively hosting on port {PORT}", flush=True)

async def main():
    await start_web_server()
    await tg_client.start()
    print("🟢 TELEGRAM CLOUD ENGINE RUNNING...", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
