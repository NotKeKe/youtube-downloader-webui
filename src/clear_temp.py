from .config import *

def clear_tmp():
    for f in TMP_DIR.iterdir():
        f.unlink()

    for f in OUTPUT_DIR.iterdir():
        f.unlink()

    URLS_PATH.unlink()