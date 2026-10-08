import os, io, secrets, time
from urllib.parse import urlparse
from threading import Lock
import requests
from PIL import Image, ImageOps
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI(title='Cinematic Frame')
cache = {}
lock = Lock()
Image.MAX_IMAGE_PIXELS = 30_000_000

class PosterRequest(BaseModel):
    openaiFileIdRefs: list[dict]
    movie_title: str = Field(min_length=1, max_length=200)
    logo_url: str | None = None

def download(url):
    p = urlparse(url)
    host = (p.hostname or '').lower()
    allowed = host.endswith('.oaiusercontent.com') or host == 'image.tmdb.org'
    if p.scheme != 'https' or not allowed or p.username or p.password or p.port not in (None,443):
        raise HTTPException(400, 'Unsupported image host. Upload the image/logo in ChatGPT, or use image.tmdb.org.')
    try:
        with requests.Session() as session:
            session.trust_env = False
            with session.get(url, timeout=(5,15), stream=True, allow_redirects=False) as r:
                if r.status_code != 200:
                    raise ValueError('Download failed')
                data = bytearray()
                for chunk in r.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > 15_000_000:
                        raise ValueError('Image too large')
        im = Image.open(io.BytesIO(data))
        im.load()
        return ImageOps.exif_transpose(im).convert('RGBA')
    except Exception:
        raise HTTPException(400, 'Could not download/decode image. Re-upload expired files.')

def compose(frame, logo):
    # Preserve the complete frame. Deliberate solid negative space, no fake outpainting.
    frame = frame.convert('RGB')
    thumb = frame.copy()
    thumb.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
    color = frame.resize((1,1)).getpixel((0,0))
    background = tuple(round(c * .22) for c in color)
    canvas = Image.new('RGB', (2000,2800), background)
    canvas.paste(thumb, ((2000-thumb.width)//2,2800-thumb.height))
    alpha = logo.getchannel('A')
    bbox = alpha.getbbox()
    if not bbox or alpha.getextrema()[0] == 255:
        raise ValueError('Use a transparent PNG/WebP title logo, not a rectangular poster.')
    logo = logo.crop(bbox)
    logo.thumbnail((680,280), Image.Resampling.LANCZOS)
    canvas.paste(logo, ((2000-logo.width)//2,420),logo)
    return canvas

@app.get('/health')
def health():
    return {'ok':True}

@app.post('/posters')
def poster(req: PosterRequest, authorization: str = Header(default='')):
    key = os.environ.get('ACTION_API_KEY','')
    if not key:
        raise HTTPException(503,'Configure ACTION_API_KEY on Render first.')
    if not secrets.compare_digest(authorization, 'Bearer '+key):
        raise HTTPException(401,'Invalid API key')
    files = req.openaiFileIdRefs
    if not files or len(files)>2:
        raise HTTPException(400,'Send frame first and optionally transparent logo second.')
    frame = download(files[0].get('download_link',''))
    logo_url = req.logo_url or (files[1].get('download_link') if len(files)==2 else None)
    if not logo_url:
        raise HTTPException(422,'Original transparent logo required. Supply logo_url or upload logo as second file.')
    logo = download(logo_url)
    try:
        out = compose(frame, logo)
    except ValueError as e:
        raise HTTPException(422,str(e))
    buf = io.BytesIO()
    out.save(buf,format='PNG')
    token = secrets.token_urlsafe(32)
    with lock:
        expired = [k for k,v in cache.items() if time.time()-v[0]>3600]
        for k in expired: del cache[k]
        if len(cache)>=20: del cache[min(cache,key=lambda k: cache[k][0])]
        cache[token]=(time.time(),buf.getvalue())
    base = os.environ.get('RENDER_EXTERNAL_URL','').rstrip('/')
    return {'movie_title':req.movie_title,'width':2000,'height':2800,'aspect_ratio':'5:7','composition':'full frame with solid negative space; no outpainting','poster_url':base+'/outputs/'+token+'.png','expires_in_seconds':3600}

@app.get('/outputs/{token}.png')
def output(token: str):
    with lock:
        item = cache.get(token)
        if not item or time.time()-item[0]>3600:
            raise HTTPException(404,'Poster expired; regenerate it.')
        return Response(item[1],media_type='image/png',headers={'Cache-Control':'no-store'})
