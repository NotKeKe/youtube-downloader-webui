from .import scrapetube
from urllib.parse import urlparse, parse_qs
import httpx

async def get_all_video_ids_from_playlist(playlist_id: str) -> list:
    results = scrapetube.get_playlist(playlist_id=playlist_id, limit=100)
    return [result['videoId'] async for result in results]

def get_video_id(url: str):
    parsed = urlparse(url)

    if parsed.netloc == "youtu.be": # 因為連結中可能包含 ?t=...
        video_id = parsed.path.lstrip("/")
    else: # 處理 youtube.com or other urls
        query = parse_qs(parsed.query)
        video_id = query.get("v", [None])[0]

    return video_id

def convert_to_short_url(url: str) -> str:
    video_id = get_video_id(url)
    if not video_id: return ''
    return f'https://youtu.be/{video_id}'

def video_id_to_url(video_id: str) -> str:
    return f'https://youtu.be/{video_id}'

async def check_url_alive(audio_url: str, client: httpx.AsyncClient | None = None) -> bool:
    try:
        if not audio_url: return False
        _client = client or httpx.AsyncClient()
        resp = await _client.head(audio_url, timeout=5)
        return resp.status_code == 200
    except:
        return False
    finally:
        if client is None:
            await _client.aclose()