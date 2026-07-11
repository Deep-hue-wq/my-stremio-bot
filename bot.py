import asyncio
# 🛡️ EVENT LOOP PROTECTION
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
MONGO_URI = os.getenv("MONGO_URI1", "mongodb+srv://deepthanki1111:Lexh54sjL9BAggp0@storage1.cwhzyf9.mongodb.net/?appName=Storage1").strip()
API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
PORT = int(os.getenv("PORT", 10000))

# 🔑 TMDB API KEY
TMDB_API_KEY = "d8e9f93d8a60953c67c8756c446c72fb"

print("\n=== STARTING CORE: SPIDERMAN FAST-STREAM (WEEBZONE NATIVE EDITION) ===", flush=True)

# Connect Database
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
db = client.stremio_bridge
streams_col = db.streams
print("🟢 MONGO DATABASE: CONNECTED SUCCESSFULLY", flush=True)

try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
except Exception: pass

tg_client = Client("stremio_fine_wine", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

def fetch_movie_metadata(raw_title, text_content=""):
    try:
        # ⚡ 1. OVERRIDE TRICK: Check if user pasted an IMDB ID (tt...) in the Telegram caption
        forced_imdb_id = None
        imdb_match = re.search(r'(tt\d{7,8})', text_content)
        if imdb_match:
            forced_imdb_id = imdb_match.group(1)
            
        # ⚡ Also support TMDB URL overrides
        tmdb_match = re.search(r'themoviedb\.org/(movie|tv)/(\d+)', text_content)
        if tmdb_match and not forced_imdb_id:
            m_type, m_id = tmdb_match.group(1), tmdb_match.group(2)
            try:
                ext_url = f"https://api.themoviedb.org/3/{m_type}/{m_id}/external_ids?api_key={TMDB_API_KEY}"
                ext_res = requests.get(ext_url, timeout=5).json()
                forced_imdb_id = ext_res.get("imdb_id")
            except: pass

        # Clean title & Parse Series Details
        clean = re.sub(r'\.(mkv|mp4|avi|mov|webm)$', '', raw_title, flags=re.IGNORECASE)
        clean = clean.replace('.', ' ').replace('_', ' ')
        
        is_series, season, episode = False, 1, 1
        series_match = re.search(r'(?:s|season)\s*(\d+)\s*(?:e|ep|episode)\s*(\d+)', clean, re.IGNORECASE)
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

        # Extreme junk tag stripping
        clean = re.sub(r'(1080p|720p|2160p|4k|bluray|hdrip|web\s*dl|brrip|x264|x265|hevc|aac|hindi|english|yts|mx|s\d+e\d+|season\s*\d+|episode\s*\d+|ep\s*\d+|\[.*?\]|\(.*?\)).*', '', clean, flags=re.IGNORECASE)
        clean_query = clean.strip()
        if len(clean_query) < 2: clean_query = "Unknown Media"

        stremio_type = "series" if is_series else "movie"
        media_type = "tv" if is_series else "movie"

        stremio_id = forced_imdb_id
        poster, desc, name = None, "", clean_query

        # If User provided IMDB ID, fetch exactly that!
        if stremio_id:
            try:
                cm_res = requests.get(f"https://v3-cinemeta.strem.io/meta/{stremio_type}/{stremio_id}.json", timeout=5).json()
                if "meta" in cm_res:
                    name, poster, desc = cm_res["meta"].get("name", name), cm_res["meta"].get("poster"), cm_res["meta"].get("description", "")
            except: pass
        else:
            # Auto-Search Cinemeta First for 1:1 Stremio Matching
            try:
                cm_res = requests.get(f"https://v3-cinemeta.strem.io/catalog/{stremio_type}/top/search={urllib.parse.quote(clean_query)}.json", timeout=5).json()
                if metas := cm_res.get("metas", []):
                    stremio_id, name, poster, desc = metas[0].get("id"), metas[0].get("name"), metas[0].get("poster"), metas[0].get("description", "")
            except: pass

            # Auto-Search TMDB Fallback
            if not stremio_id:
                try:
                    tmdb_url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={TMDB_API_KEY}&query={urllib.parse.quote(clean_query)}"
                    res = requests.get(tmdb_url, timeout=5).json()
                    if res.get("results"):
                        best = res["results"][0]
                        if not poster and best.get("poster_path"): poster = f"https://image.tmdb.org/t/p/w500{best.get('poster_path')}"
                        if not desc: desc = best.get("overview", "")
                        ext_res = requests.get(f"https://api.themoviedb.org/3/{media_type}/{best.get('id')}/external_ids?api_key={TMDB_API_KEY}", timeout=5).json()
                        stremio_id = ext_res.get("imdb_id")
                except: pass
                
        if not stremio_id: stremio_id = "tg_" + hashlib.md5(name.encode()).hexdigest()[:10]

        return {"imdb_id": stremio_id, "name": name, "poster": poster, "desc": desc, "type": stremio_type, "s": season, "e": episode}
            
    except Exception:
        stable_id = "tg_" + hashlib.md5(raw_title[:15].encode()).hexdigest()[:10]
        return {"imdb_id": stable_id, "name": raw_title, "type": "movie", "s": 1, "e": 1, "poster": "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg", "desc": "Telegram File"}

def telegram_polling_loop():
    print("🟢 TELEGRAM BOT LISTENER ONLINE", flush=True)
    offset = 0
    while True:
        try:
            req = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=5", timeout=10)
            if req.status_code != 200:
                time.sleep(2)
                continue
            for update in req.json().get("result", []):
                offset = update["update_id"] + 1
                if "message" not in update: continue
                msg = update["message"]
                chat_id, text_content = msg["chat"]["id"], msg.get("text", "") or msg.get("caption", "") or ""
                
                if text_content.startswith("/start"):
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "🟢 Extraction Bot Online!\n\nPro-Tip: Forward a file and paste an IMDB ID (e.g., tt1234567) in the caption to perfectly force-sync it!"})
                    continue

                media = msg.get("video") or msg.get("document")
                if media and ("video" in media.get("mime_type", "") or media.get("file_name", "").endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm'))):
                    file_id, raw_name, file_size = media.get("file_id"), media.get("file_name", "Stream"), media.get("file_size")
                    render_domain = os.getenv("RENDER_EXTERNAL_URL", "https://my-stremio-bot-1.onrender.com").rstrip('/')
                    
                    # Pass the text_content so the bot can hunt for forced IMDB IDs
                    meta = fetch_movie_metadata(raw_name, text_content)
                    streams_col.insert_one({"file_name": meta["name"], "tg_url": f"{render_domain}/watch/{file_id}", "file_id": file_id, "file_size": file_size, "imdb_id": meta["imdb_id"], "poster": meta["poster"], "description": meta["desc"], "type": meta["type"], "season": meta["s"], "episode": meta["e"]})
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Synced: {meta['name']} (S{meta['s']}E{meta['e']})"})
                    continue

                if "http" in text_content:
                    urls = re.findall(r'(https?://\S+)', text_content)
                    if final_url := next((u for u in urls if "stream" in u or "dl" in u), urls[0] if urls else None):
                        name_match = re.search(r'File:\s*(.*)', text_content, re.IGNORECASE)
                        file_name = name_match.group(1).split("\n")[0].strip() if name_match else text_content.split("\n")[0].strip()
                        meta = fetch_movie_metadata(file_name, text_content)
                        streams_col.insert_one({"file_name": meta["name"], "tg_url": final_url, "imdb_id": meta["imdb_id"], "poster": meta["poster"], "description": meta["desc"], "type": meta["type"], "season": meta["s"], "episode": meta["e"]})
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Link Synced: {meta['name']} (S{meta['s']}E{meta['e']})"})
            if not req.json().get("result", []): time.sleep(1)
        except Exception: time.sleep(2)

async def manifest_route(request):
    return web.json_response({
        "id": "org.deepsstremio.telegram", "version": "12.0.0", "name": "Telegram Library",
        "description": "High-speed sequential streaming proxy tunnel.",
        "resources": [
            "catalog", 
            "stream", 
            {"name": "meta", "types": ["movie", "series"], "idPrefixes": ["tg_"]} # ⚡ NATIVE HANDOFF: Stremio now handles official TV posters natively!
        ], 
        "types": ["movie", "series"],
        "catalogs": [{"type": "movie", "id": "tg_movie", "name": "Telegram Library"}, {"type": "series", "id": "tg_series", "name": "Telegram Library"}],
        "idPrefixes": ["tt", "tg_"]
    }, headers={"Access-Control-Allow-Origin": "*"})

async def catalog_route(request):
    req_type = request.match_info['type']
    
    def fetch_catalog():
        try:
            docs = list(streams_col.find({"type": req_type}).sort("_id", -1).limit(400))
            seen, metas = set(), []
            for d in docs:
                imdb_id = d.get("imdb_id")
                if imdb_id and imdb_id not in seen:
                    seen.add(imdb_id)
                    metas.append({"id": imdb_id, "type": req_type, "name": d.get("file_name", "Media"), "poster": d.get("poster") or "https://images.slideteam.net/wp-content/uploads/2016/11/04/Video-player-icon-graphic-design-PowerPoint-Templates-Slide-1.jpg", "description": d.get("description", "")})
                if len(metas) >= 100: break
            return metas
        except: return []

    metas = await asyncio.to_thread(fetch_catalog)
    return web.json_response({"metas": metas}, headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-cache"})

async def meta_route(request):
    # This route is now ONLY called for Custom "tg_" IDs, vastly reducing server load!
    req_type, raw_id = request.match_info['type'], request.match_info['id'].replace(".json", "")

    def fetch_meta():
        doc = streams_col.find_one({"imdb_id": raw_id, "type": req_type})
        if not doc: return {"meta": {}}
        meta = {"id": raw_id, "type": req_type, "name": doc.get("file_name", "Media"), "poster": doc.get("poster"), "description": doc.get("description", "")}
        if req_type == "series":
            meta["videos"] = [{"id": f"{raw_id}:{ep.get('season', 1)}:{ep.get('episode', 1)}", "title": f"Episode {ep.get('episode', 1)}", "season": ep.get("season", 1), "episode": ep.get("episode", 1)} for ep in streams_col.find({"imdb_id": raw_id, "type": "series"}).sort([("season", 1), ("episode", 1)])]
        return {"meta": meta}

    result = await asyncio.to_thread(fetch_meta)
    return web.json_response(result, headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-cache"})

async def stream_route(request):
    req_type = request.match_info['type']
    parts = request.match_info['id'].replace(".json", "").split(":")
    imdb_id = parts[0]
    
    def fetch_streams():
        season, episode = None, None
        if len(parts) == 3:
            season, episode = int(parts[1]), int(parts[2])
            query = {"imdb_id": imdb_id, "season": season, "episode": episode}
        else:
            query = {"imdb_id": imdb_id}
            
        docs = list(streams_col.find(query))
        
        # Fuzzy Fallback
        if not docs and imdb_id.startswith("tt"):
            try:
                cm_res = requests.get(f"https://v3-cinemeta.strem.io/meta/{req_type}/{imdb_id}.json", timeout=5).json()
                if real_name := cm_res.get("meta", {}).get("name"):
                    base_words = " ".join(re.sub(r'[^a-zA-Z0-9 ]', '', real_name).split()[:3])
                    if season and episode:
                        fuzzy_query = {"type": "series", "season": season, "episode": episode, "file_name": {"$regex": base_words, "$options": "i"}}
                    else:
                        fuzzy_query = {"type": "movie", "file_name": {"$regex": base_words, "$options": "i"}}
                    docs = list(streams_col.find(fuzzy_query))
            except: pass

        return [{"name": "⚡ NATIVE SPEED", "title": f"🎬 Play File Natively\n💾 {round(d.get('file_size', 0)/(1024*1024), 2) if d.get('file_size') else 'Unknown'} MB", "url": d["tg_url"]} for d in docs]

    streams = await asyncio.to_thread(fetch_streams)
    return web.json_response({"streams": streams}, headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-cache"})

async def watch_route(request):
    file_id = request.match_info['file_id']
    doc = await asyncio.to_thread(streams_col.find_one, {"file_id": file_id})
    if not doc: return web.Response(status=404)
        
    file_size, file_name = doc.get("file_size", 0), doc.get("file_name", "stream.mp4")
    headers = {"Accept-Ranges": "bytes", "Content-Type": "video/mp4", "Access-Control-Allow-Origin": "*"}
    range_header = request.headers.get("Range")
    
    if not range_header or not file_size:
        headers.update({"Content-Length": str(file_size), "Content-Disposition": f'inline; filename="{file_name}"'})
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        try:
            async for chunk in tg_client.stream_media(file_id):
                await response.write(chunk)
                await response.drain()
        except: pass
        return response

    try:
        rm = re.match(r"bytes=(\d+)-(\d*)", range_header)
        start_byte, end_byte = int(rm.group(1)), int(rm.group(2)) if rm.group(2) else file_size - 1
    except:
        start_byte, end_byte = 0, file_size - 1

    if start_byte >= file_size: return web.Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

    content_length = end_byte - start_byte + 1
    headers.update({"Content-Length": str(content_length), "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}", "Content-Disposition": f'inline; filename="{file_name}"'})
    response = web.StreamResponse(status=206, headers=headers)
    await response.prepare(request)

    chunk_size = 1024 * 1024  
    offset_chunks, skip_bytes = start_byte // chunk_size, start_byte % chunk_size

    try:
        async for chunk in tg_client.stream_media(file_id, limit=0, offset=offset_chunks):
            if skip_bytes > 0: chunk, skip_bytes = chunk[skip_bytes:], 0
            if content_length <= len(chunk):
                await response.write(chunk[:content_length])
                await response.drain()
                break
            await response.write(chunk)
            await response.drain()
            content_length -= len(chunk)
    except: pass
    return response

async def main():
    app = web.Application(client_max_size=0)
    for route, handler in [('/', manifest_route), ('/manifest.json', manifest_route), ('/catalog/{type}/{id}.json', catalog_route), ('/meta/{type}/{id}.json', meta_route), ('/stream/{type}/{id}.json', stream_route), ('/watch/{file_id}', watch_route)]:
        app.router.add_get(route, handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    print(f"🟢 Stremio Core Router active on port {PORT}", flush=True)
    
    await tg_client.start()
    threading.Thread(target=telegram_polling_loop, daemon=True).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
