from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import fitz  # PyMuPDF
import httpx

DEFAULT_TEXT = "Confidential"
DEFAULT_TEXT_SIZE = 3
DEFAULT_TRADEMARK = "Created with GeeDeePermark - https://geedeepermark.cpvo.org/"
DEFAULT_TRADEMARK_SIZE = 2

app = FastAPI()

def load_font(px):
    # Try common system font; fall back to Pillow default
    for name in ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(name, px)
        except Exception:
            pass
    from PIL import ImageFont as IF
    return IF.load_default()

def draw_watermark(img: Image.Image, text: str, size: int) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    px = {1: 12, 2: 18, 3: 24, 4: 30}[size]
    font = load_font(px)

    # base tile 3x size of image
    tile_w, tile_h = w * 3, h * 3
    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)

    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)

    step_x = int(tw * 1.15) # inter words
    step_y = int(th * 2.8) # inter lines
    for y in range(0, tile_h, step_y):
        for x in range(0, tile_w, step_x):
            draw.text((x, y), text, font=font, fill=(128, 128, 128, 128))

    tile = tile.rotate(30, expand=1)

    # center-crop back to image size
    x0 = (tile.width - w) // 2
    y0 = (tile.height - h) // 2
    tile = tile.crop((x0, y0, x0 + w, y0 + h))

    out = Image.alpha_composite(img, tile)

    # Add trademark in bottom-right
    trademark_font = load_font(12)  # size hardcoded to 12
    draw_out = ImageDraw.Draw(out)

    # Get trademark text dimensions
    try:
        bbox = draw_out.textbbox((0, 0), DEFAULT_TRADEMARK, font=trademark_font)
        tw_trademark = bbox[2] - bbox[0]
        th_trademark = bbox[3] - bbox[1]
    except AttributeError:
        tw_trademark, th_trademark = draw_out.textsize(DEFAULT_TRADEMARK, font=trademark_font)

    # Add trademark at bottom right
    x_bottom_right = max(0, w - tw_trademark - 10)
    y_bottom_right = max(0, h - th_trademark - 10)
    draw_out.text((x_bottom_right, y_bottom_right), DEFAULT_TRADEMARK, font=trademark_font, fill=(128,128,128,128))

    return out.convert("RGB")

def open_as_image(data: bytes, content_type: str) -> Image.Image:
    if content_type and "pdf" in content_type.lower():
        # render first page to image; extend to loop pages if needed
        doc = fitz.open(stream=data, filetype="pdf")
        if len(doc) == 0:
            raise HTTPException(400, "Empty PDF")
        page = doc[0]
        pix = page.get_pixmap(alpha=False, dpi=144)  # crisp raster
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    # fallback: try PIL sniffing regardless of content_type
    return Image.open(BytesIO(data))

@app.post("/watermark")
async def watermark(
    file: UploadFile = File(...),
    text: str = Form(DEFAULT_TEXT),      # default text
    text_size: int = Form(DEFAULT_TEXT_SIZE, ge=1, le=4),  # default = 3
):
    blob = await file.read()
    try:
        img = open_as_image(blob, file.content_type or "")
    except Exception:
        raise HTTPException(400, "Unsupported file. Provide an image or a PDF.")

    try:
        out = draw_watermark(img, text, text_size)
    except Exception as e:
        import traceback
        raise HTTPException(500, f"Watermark error: {e}\n{traceback.format_exc()}")

    buf = BytesIO()
    if file.content_type and "pdf" in file.content_type.lower():
        # re-embed raster in single-page PDF
        pdf_bytes = BytesIO()
        out.save(pdf_bytes, format="PDF", resolution=144)
        return Response(content=pdf_bytes.getvalue(), media_type="application/pdf")
    else:
        out.save(buf, format="PNG", optimize=True)
        return Response(content=buf.getvalue(), media_type="image/png")


@app.post("/download_from_grist")
async def download_from_grist(
    attachment_id: str = Form(...),
    token: str = Form(...),
    base_url: str = Form(...)
):
    url = f"{base_url}/attachments/{attachment_id}/download?auth={token}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if not response.is_success:
            raise HTTPException(response.status_code, f"Failed to download from Grist: {response.text}")
        return Response(content=response.content, media_type=response.headers.get("content-type", "application/octet-stream"))


@app.post("/upload_to_grist")
async def upload_to_grist(
    file: UploadFile = File(...),
    token: str = Form(...),
    base_url: str = Form(...)
):
    # Adjust base_url for REST API
    rest_base = base_url.replace('/o/docs/api', '/api')
    url = f"{rest_base}/attachments?auth={token}"
    files = {"upload": (file.filename, await file.read(), file.content_type)}
    headers = {"X-Requested-With": "XMLHttpRequest"}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, files=files, headers=headers)
        if not response.is_success:
            raise HTTPException(response.status_code, f"Failed to upload to Grist: {response.text}")
        result = response.json()
        attachment_id = result[0] if isinstance(result, list) else result.get("id") or result.get("attachmentId") or result.get("AttachmentId")
        if not attachment_id:
            raise HTTPException(500, "Upload did not return an attachment ID")
        return {"id": attachment_id}
