from pytubefix import AsyncYouTube, StreamQuery, Stream
from httpx import AsyncClient
import os
from pathlib import Path
import re
import asyncio
import tempfile
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from .utils import *
from .config import *

client = AsyncClient()

required_TYPE = Literal['video', 'audio', 'video_audio', 'Unknown']

# ffmpeg
def merge_video_audio_low_memory(video_file: str, audio_file: str, output_file: str = ''):
    """
    針對大檔案的記憶體優化版本
    """
    if not output_file:
        base, _ = os.path.splitext(video_file)
        output_file = base + "_merged.mp4"

    if not Path(video_file).exists():
        raise FileNotFoundError(f"找不到影片檔案: {video_file}")

    if not Path(audio_file).exists():
        raise FileNotFoundError(f"找不到音訊檔案: {audio_file}")

    # 使用臨時目錄
    with tempfile.TemporaryDirectory() as temp_dir:
        # 分段處理策略
        temp_output = os.path.join(temp_dir, "temp_output.mp4")
        
        # 更保守的 FFmpeg 參數
        cmd = [
            'ffmpeg',
            '-i', video_file,
            '-i', audio_file,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-y',
            temp_output
        ]

        print("FFmpeg start")
        
        # 使用 subprocess.run 但限制資源
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
        )
        
        # 移動最終檔案
        if os.path.exists(temp_output):
            if os.path.exists(output_file):
                os.remove(output_file)
            shutil.move(temp_output, output_file)
        
        print(f"合併完成 → {output_file}")
        return output_file
    
def safe_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', ' ', filename)
    filename = re.sub(r'[^\w\s\-\.\u4e00-\u9fff]', ' ', filename)
    filename = filename.strip()[:255]
    
    return filename

# stream process
def get_best_video_stream(streams: StreamQuery, resolution: int = 0, fps: int = 0) -> tuple[Stream, str, int] | None:
    '''
    Return:
        tuple[Stream, resolution(str), fps(int)]
    '''
    video_candidates = streams.filter(adaptive=True, only_video=True)
    
    candidates_list = list(video_candidates)

    if resolution and fps:
        stream_query = streams.filter(adaptive=True, resolution=f'{resolution}p', fps=fps, only_video=True)
    elif resolution:
        stream_query = streams.filter(adaptive=True, resolution=f'{resolution}p', only_video=True)
    elif fps:
        stream_query = streams.filter(adaptive=True, fps=fps, only_video=True)
    else:
        stream_query = streams.filter(adaptive=True, only_video=True)
    
    candidates_list = list(stream_query)

    candidates_list.sort(
        key=lambda s: (
            # 把 "1080p" 的 'p' 去掉並轉成整數，如果沒解析度則為 0
            int(s.resolution[:-1]) if s.resolution else 0,
            # 接著比對 FPS
            s.fps
        ),
        reverse=True # 從大到小排序 (Desc)
    )

    # 4. 回傳第一名 (即解析度最高且 FPS 最高的)
    if candidates_list:
        stream: Stream = candidates_list[0]
        return stream, stream.resolution, stream.fps
    return None

def get_best_audio_stream(streams: StreamQuery) -> tuple[Stream, str] | None:
    best_audio = (
        streams
        .filter(adaptive=True, only_audio=True)
        .order_by("abr")
        .desc()
        .first()
    )
    
    if best_audio:
        return best_audio, best_audio.abr
    
    return None

def to_get_format(resolution: int, fps: int, abr: int, required_type: required_TYPE = 'Unknown') -> str:
    if required_type == 'video_audio':
        return f'video_audio-{resolution}_{fps}-{abr}'
    elif required_type == 'video':
        return f'video-{resolution}_{fps}'
    elif required_type == 'audio':
        return f'audio-{abr}'

    # no required_type
    if resolution and abr:
        required_type = required_type or 'video_audio'
        return f'video_audio-{resolution}_{fps}-{abr}'
    elif resolution:
        required_type = required_type or 'video'
        return f'video-{resolution}_{fps}'
    elif abr:
        required_type = required_type or 'audio'
        return f'audio-{abr}'
    else:
        return ''
    
def add_to_url(url: str, file_path: Path, resolution: int, fps: int, abr: int, meta: dict[str, set], required_type: required_TYPE = 'Unknown'):
    '''add to temp, at data/urls.json'''
    # required to has true resolution and abr
    urls[url]['options'][to_get_format(resolution, fps, abr, required_type)] = str(file_path)

    resolutions = list(meta['resolution'])
    resolutions = [int(item[:-1]) for item in resolutions]
    fpses = list(meta['fps'])
    abrs = list(meta['abr'])
    abrs = [int(item[:-4]) for item in abrs]

    resolutions.sort(reverse=True)
    fpses.sort(reverse=True)
    abrs.sort(reverse=True)

    urls[url]['meta'] = {
        'resolution': resolutions,
        'fps': fpses,
        'abr': abrs
    }

    with open(URLS_PATH, 'wb') as f:
        f.write(orjson.dumps(urls, option=orjson.OPT_INDENT_2))

async def get_meta(url: str) -> dict[str, list]:
    if url in urls:
        return urls[url]['meta']

    yt = AsyncYouTube(url)
    streams = await yt.streams()
    meta = defaultdict(set)

    # get meta
    for stream in streams:
        if hasattr(stream, 'resolution') and stream.resolution:
            meta['resolution'].add(stream.resolution)
        if hasattr(stream, 'fps') and stream.fps:
            meta['fps'].add(stream.fps)
        if hasattr(stream, 'abr') and stream.abr:
            meta['abr'].add(stream.abr)

    resolutions = list(meta['resolution'])
    resolutions = [int(item[:-1]) for item in resolutions]
    fpses = list(meta['fps'])
    abrs = list(meta['abr'])
    abrs = [int(item[:-4]) for item in abrs]

    resolutions.sort(reverse=True)
    fpses.sort(reverse=True)
    abrs.sort(reverse=True)

    meta = {
        'resolution': resolutions,
        'fps': fpses,
        'abr': abrs
    }

    urls[url]['meta'] = meta

    with open(URLS_PATH, 'wb') as f:
        f.write(orjson.dumps(urls, option=orjson.OPT_INDENT_2))

    return meta

async def get_video(url: str, required_type: required_TYPE = 'Unknown', resolution: int | str = 'best', fps: int | str = 'best', abr: int | str = 'best') -> tuple[Path, str]:
    # if not resolution and not abr: means return meta
    # if only resolution: return video only
    # if only abr: return audio only
    # if resolution and abr: return combined video (include video and audio)
    yt = AsyncYouTube(url)
    streams = await yt.streams()
    status = ''
    meta = defaultdict(set)

    # get meta
    for stream in streams:
        if hasattr(stream, 'resolution') and stream.resolution:
            meta['resolution'].add(stream.resolution)
        if hasattr(stream, 'fps') and stream.fps:
            meta['fps'].add(stream.fps)
        if hasattr(stream, 'abr') and stream.abr:
            meta['abr'].add(stream.abr)

    # get video
    result = get_best_video_stream(
        streams, 
        resolution if isinstance(resolution, int) else 0, 
        fps if isinstance(fps, int) else 0
    )
    best_video, resolution, fps = result if result else (0, 0, 0)

    if not best_video:
        result = get_best_video_stream(streams)
        best_video, resolution, fps = result if result else (0, 0, 0)
        status = "Didn't find the resolution you want. Using the best resolution instead."

    # get audio
    if abr == 'best':
        result = get_best_audio_stream(streams)
        best_audio, abr = result if result else (0, 0)
    else:
        best_audio = (
            streams
            .filter(abr=abr, only_audio=True)
            .first()
        )
        abr = best_audio.abr if best_audio else 0
    if not abr:
        result = get_best_audio_stream(streams)
        best_audio, abr = result if result else (0, 0)
        status = "Didn't find the audio quality you want. Using the best audio quality instead."

    resolution = int(resolution[:-1]) if isinstance(resolution, str) else resolution
    abr = int(abr[:-4]) if isinstance(abr, str) else abr
    
    assert isinstance(fps, int)
    _to_get_format = to_get_format(resolution, fps, abr, required_type)
    print(_to_get_format)

    if url in urls:
        options = urls[url].get('options', {})
        if options.get(_to_get_format):
            return Path(options[_to_get_format]), status

    base_name = safe_filename(await yt.title())
    output_base_filename = f"{base_name}-{_to_get_format}"


    if not best_video and not best_audio:
        return Path(), 'Cannot find any video or audio stream.'
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        loop = asyncio.get_running_loop()
        tasks = []
    
        # 其實這裡能有更好的找暫存方法，像是先去 outputs 裡面找有沒有單 video / audio 的，但我想不到怎麼做會比較好看，所以暫時沒寫

        if _to_get_format.startswith('video') or _to_get_format.startswith('video_audio'):
            assert best_video
            tasks.append(
                loop.run_in_executor(executor, lambda: best_video.download(str(TMP_DIR)))
            )

            print('Downloading video...')

        if _to_get_format.startswith('audio') or _to_get_format.startswith('video_audio'):
            assert best_audio
            tasks.append(
                loop.run_in_executor(executor, lambda: best_audio.download(str(TMP_DIR)))
            )

            print('Downloading audio...')

        results = await asyncio.gather(*tasks)

        if len(results) == 2:
            output_filename = output_base_filename + '.mp4'
            await loop.run_in_executor(executor, lambda: merge_video_audio_low_memory(
                results[0], # type: ignore
                results[1], # type: ignore
                str(OUTPUT_DIR / output_filename)
            ))
        else:
            # move file to output dir
            name, ext = os.path.splitext(results[0])
            output_filename: str = output_base_filename + ext
            if (OUTPUT_DIR / output_filename).exists(): 
                (OUTPUT_DIR / output_filename).unlink()
            os.rename(results[0], str(OUTPUT_DIR / output_filename))

    for file in results:
        if not file: continue
        file = Path(file)
        if not file.exists(): continue

        if file.is_dir():
            shutil.rmtree(file)
        else:
            file.unlink()
    
    add_to_url(url, OUTPUT_DIR / output_filename, resolution, fps, abr, meta, required_type)

    return OUTPUT_DIR / output_filename, status