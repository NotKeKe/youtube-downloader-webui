from pathlib import Path
import orjson
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'
DATA_DIR.mkdir(exist_ok=True)


TMP_DIR = DATA_DIR / 'tmp'
OUTPUT_DIR = DATA_DIR / 'outputs'
URLS_PATH = DATA_DIR / 'urls.json'

TMP_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

if not URLS_PATH.exists() or URLS_PATH.stat().st_size == 0:
    URLS_PATH.touch(exist_ok=True)
    URLS_PATH.write_text('{}')

def _tree():
    return defaultdict(_tree)

with open(URLS_PATH, 'rb') as f:
    _urls = orjson.loads(f.read())
    urls = defaultdict(lambda: defaultdict(dict), _urls)

    urls = _tree()
    for k, v in _urls.items():
        urls[k].update(v)
    '''
    {
        "url": {
            "options": {
                "video_audio:720p30:128": "c:/path/to/file.mp4",
            }
        }
    }
    '''

