import sys
from pathlib import Path
import asyncio

root = Path(__file__).parent.parent
sys.path.append(str(root))

from src.get_video import *

async def test_get_video():
    path, status = await get_video('https://youtu.be/eN1GDh6b4U8?si=zranEP2V5m3CFUL0', required_type='audio')
    print(path)
    print(status)

asyncio.run(test_get_video())