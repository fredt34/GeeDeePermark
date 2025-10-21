from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import fitz  # PyMuPDF
import httpx
import json
import re
import os

# Deployment constant: 0 = unlocked, 1 = locked, 2 = mixed
LOCKED = 2

DEFAULT_TEXT = "Confidential"
DEFAULT_TEXT_SIZE = 3
DEFAULT_TRADEMARK = "Created with GeeDeePermark - https://geedeepermark.cpvo.org/"
DEFAULT_TRADEMARK_SIZE = 2

app = FastAPI()

def load_config_from_uuid(uuid: str) -> dict:
    """
    Load watermark configuration from a UUID-based JSON file.
    
    Security features:
    - Validates UUID format (only hex digits and hyphens)
    - Prevents directory traversal using Path.resolve()
    - Rejects files larger than 1 MB
    - Returns 404 if file not found
    
    Args:
        uuid: UUID string (e.g., "00000000-0000-0000-0000-000000000000")
    
    Returns:
        dict with 'text' and 'text_size' keys (with defaults if missing)
    
    Raises:
        HTTPException: 400 for invalid UUID, 404 for missing file, 413 for oversized file
    """
    # Validate UUID format: only hex digits and hyphens
    if not re.match(r'^[0-9a-fA-F-]+$', uuid):
        raise HTTPException(400, "Invalid UUID format")
    
    # Construct safe path and prevent directory traversal
    configs_dir = Path(__file__).parent / "configs"
    config_file = configs_dir / f"{uuid}.json"
    
    try:
        # Resolve to absolute path and verify it's inside configs/
        resolved_path = config_file.resolve()
        resolved_configs_dir = configs_dir.resolve()
        
        if not str(resolved_path).startswith(str(resolved_configs_dir)):
            raise HTTPException(400, "Invalid UUID: directory traversal detected")
    except Exception:
        raise HTTPException(400, "Invalid UUID path")
    
    # Check if file exists
    if not resolved_path.exists():
        raise HTTPException(404, f"Configuration file not found for UUID: {uuid}")
    
    # Check file size (max 1 MB)
    file_size = resolved_path.stat().st_size
    if file_size > 1_000_000:
        raise HTTPException(413, "Configuration file too large (max 1 MB)")
    
    # Load and parse JSON
    try:
        with open(resolved_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(400, f"Invalid JSON in configuration file: {uuid}")
    except Exception as e:
        raise HTTPException(500, f"Error reading configuration file: {e}")
    
    # Return config with defaults for missing keys
    return {
        'text': config.get('text', DEFAULT_TEXT),
        'text_size': config.get('text_size', DEFAULT_TEXT_SIZE)
    }

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
    text: str = Form(None),
    text_size: int = Form(None, ge=1, le=4),
    uuid: str = Form(None),
):
    """
    Apply watermark to an uploaded image or PDF file.
    
    **Operating Modes (controlled by LOCKED constant):**
    
    **LOCKED = 0 (Unlocked Mode):**
    - Parameters: file (required), text (optional), text_size (optional)
    - The 'uuid' parameter is REJECTED (returns 400)
    - Users can specify custom watermark text and size
    - Example: POST with file=@doc.pdf, text="Custom", text_size=3
    
    **LOCKED = 1 (Locked Mode):**
    - Parameters: file (required), uuid (required)
    - The 'text' and 'text_size' parameters are REJECTED (returns 400)
    - Watermark configuration is loaded from configs/{uuid}.json
    - Example: POST with file=@doc.pdf, uuid="00000000-0000-0000-0000-000000000000"
    
    **LOCKED = 2 (Mixed Mode):**
    - Parameters: file (required), EITHER uuid OR text/text_size (but not both)
    - If 'uuid' is provided: loads configuration from configs/{uuid}.json
    - If 'text' is provided: uses custom text and optional text_size
    - Returns 400 if both uuid and text are provided
    - Returns 400 if neither uuid nor text are provided
    - Example 1: POST with file=@doc.pdf, uuid="00000000-0000-0000-0000-000000000000"
    - Example 2: POST with file=@doc.pdf, text="Custom", text_size=3
    
    Args:
        file: Image (JPEG, PNG, etc.) or PDF file to watermark
        text: Watermark text (unlocked/mixed mode only)
        text_size: Font size 1-4 (unlocked/mixed mode only)
        uuid: Configuration UUID (locked/mixed mode only)
    
    Returns:
        Watermarked file (PNG for images, PDF for PDFs)
    
    Raises:
        HTTPException: 400 for invalid parameters or unsupported files
    """
    # Mode-based parameter validation
    if LOCKED == 0:
        # Unlocked mode: reject uuid, allow text/text_size
        if uuid is not None:
            raise HTTPException(400, "Parameter 'uuid' not allowed in unlocked mode")
        
        # Use provided values or defaults
        watermark_text = text if text is not None else DEFAULT_TEXT
        watermark_size = text_size if text_size is not None else DEFAULT_TEXT_SIZE
    
    elif LOCKED == 1:
        # Locked mode: require uuid, reject text/text_size
        if text is not None or text_size is not None:
            raise HTTPException(400, "Parameters 'text' and 'text_size' not allowed in locked mode")
        
        if uuid is None:
            raise HTTPException(400, "Parameter 'uuid' is required in locked mode")
        
        # Load configuration from UUID file
        config = load_config_from_uuid(uuid)
        watermark_text = config['text']
        watermark_size = config['text_size']
    
    elif LOCKED == 2:
        # Mixed mode: accept EITHER uuid OR text/text_size (but not both)
        if uuid is not None and text is not None:
            raise HTTPException(400, "Cannot provide both 'uuid' and 'text' parameters in mixed mode")
        
        if uuid is None and text is None:
            raise HTTPException(400, "Must provide either 'uuid' or 'text' parameter in mixed mode")
        
        if uuid is not None:
            # UUID path: reject text_size if provided with uuid
            if text_size is not None:
                raise HTTPException(400, "Cannot provide 'text_size' when using 'uuid' parameter")
            
            # Load configuration from UUID file
            config = load_config_from_uuid(uuid)
            watermark_text = config['text']
            watermark_size = config['text_size']
        else:
            # Text path: use custom text and optional text_size
            watermark_text = text
            watermark_size = text_size if text_size is not None else DEFAULT_TEXT_SIZE
    
    else:
        raise HTTPException(500, f"Invalid LOCKED mode value: {LOCKED}")
    
    # Validate text_size range
    if not (1 <= watermark_size <= 4):
        raise HTTPException(400, "text_size must be between 1 and 4")
    
    # Process the file
    blob = await file.read()
    try:
        img = open_as_image(blob, file.content_type or "")
    except Exception:
        raise HTTPException(400, "Unsupported file. Provide an image or a PDF.")

    try:
        out = draw_watermark(img, watermark_text, watermark_size)
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