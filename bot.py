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
import time
import threading
from aiohttp import web
from pymongo import MongoClient
from pyrogram import Client
from pyrogram.file_id import FileId
from pyrogram.raw.functions.upload import GetFile
from pyrogram.raw.types import InputDocumentFileLocation

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI1", "").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
PORT = int(os.getenv("PORT", 10000))

print("\n=== SYSTEM CORE: SNAP-SEEK RANGE CONTROLLER ONLINE ===", flush=True)

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

# Initialize Pyrogram purely as a passive asset for low-level protocol calls
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
                        "type": meta["type"], "season": meta["s"], "episode": meta["e"],
                        "chat_id": chat_id, "message_id": msg["message_id"]  # Saved for reference matching
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
        "id": "org.deepsstremio.telegram", "version": "7.5.0", "name": "Telegram Library",
        "description": "Original stable streaming proxy tunnel with instant MTProto seek optimization.",
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

# ⚡ THE UNTHROTTLED MTPROTO TARGET SEEKER (Fulfills Range Requests instantly)
async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = streams_col.find_one({"file_id": file_id})
    if not doc: return web.Response(status=404)
    
    file_size = doc.get("file_size", 0)
    chat_id = doc.get("chat_id")
    message_id = doc.get("message_id")
    
    range_header = request.headers.get("Range", "")
    start_byte = 0
    end_byte = file_size - 1 if file_size else 0
    
    if range_header and "bytes=" in range_header:
        try:
            coords = range_header.split("bytes=")[1].split("-")
            start_byte = int(coords[0])
            if coords[1]: end_byte = int(coords[1])
        except:
            start_byte = 0
            
    status = 206 if range_header else 200
    headers = {
        "Content-Type": "video/mp4", 
        "Access-Control-Allow-Origin": "*",
        "Accept-Ranges": "bytes"
    }
    if file_size:
        headers["Content-Disposition"] = f'inline; filename="{doc.get("file_name", "stream.mp4")}"'
        if range_header:
            headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{file_size}"
            headers["Content-Length"] = str(end_byte - start_byte + 1)
        else:
            headers["Content-Length"] = str(file_size)
            
    response = web.StreamResponse(status=status, headers=headers)
    await response.prepare(request)
    
    try:
        # Dynamically refresh the file location reference on demand
        target_file_id = file_id
        if chat_id and message_id:
            try:
                msg = await tg_client.get_messages(chat_id, message_id)
                media = msg.video or msg.document
                if media: target_file_id = media.file_id
            except:
                pass
                
        # Decode the location profile
        decoded_profile = FileId.decode(target_file_id)
        location = InputDocumentFileLocation(
            id=decoded_profile.media_id,
            access_hash=decoded_profile.access_hash,
            file_reference=decoded_profile.file_reference,
            thumb_size=""
        )
        
        # Configure chunk alignment parameters (512KB chunks matched to 4096-byte blocks)
        chunk_size = 512 * 1024
        mtproto_offset = (start_byte // 4096) * 4096
        skip_inside_first_chunk = start_byte - mtproto_offset
        current_offset = mtproto_offset
        
        while current_offset < file_size:
            if current_offset > end_byte:
                break
                
            file_part = await tg_client.invoke(
                GetFile(location=location, offset=current_offset, limit=chunk_size)
            )
            
            if not file_part or not hasattr(file_part, "bytes") or not file_part.bytes:
                break
                
            data = file_part.bytes
            
            if current_offset == mtproto_offset and skip_inside_first_chunk > 0:
                data = data[skip_inside_first_chunk:]
                
            chunk_end_pos_adjusted = (mtproto_offset + skip_inside_first_chunk + len(data)) if current_offset == mtproto_offset else (current_offset + len(data))
            if chunk_end_pos_adjusted > end_byte + 1:
                allowed_len = (end_byte - (current_offset + (skip_inside_first_chunk if current_offset == mtproto_offset else 0))) + 1
                data = data[:int(allowed_len)]
                
            await response.write(data)
            await response.drain()
            
            if len(data) == 0:
                break
            current_offset += chunk_size
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
    print("🟢 MTProto Seek Asset connected successfully!", flush=True)
    
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
