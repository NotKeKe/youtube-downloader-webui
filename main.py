from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import webbrowser

from src.get_video import get_video, get_meta

app = FastAPI()
# css, js
app.mount("/static", StaticFiles(directory="static"))
# html
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post('/qualities', response_class=JSONResponse)
async def qualities(request: Request):
    data = await request.json()
    url = data['url']
    if not url: return {}
    meta = await get_meta(url)
    print(meta)
    return meta

@app.post('/download', response_class=FileResponse)
async def download(request: Request):
    data = await request.json()
    url = data['url']
    _type = data['type'].lower().strip()
    abr = data.get('abr')
    resolution = data.get('resolution')
    fps = data.get('fps')

    if _type == 'video and audio':
        _type = 'video_audio'

    if not resolution:
        resolution = 'best'
    if not fps:
        fps = 'best'
    if not abr:
        abr = 'best'

    path, status = await get_video(url, _type, resolution, fps, abr)
    if status and not path.exists():
        return HTTPException(status_code=400, detail=status)
    
    return FileResponse(path, filename=path.name)

if __name__ == "__main__":
    import uvicorn
    webbrowser.open_new_tab('http://localhost:8000')
    uvicorn.run(app, host="localhost", port=8000)