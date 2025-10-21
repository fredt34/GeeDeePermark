# GeeDeePerMark API Documentation

Complete technical reference for all API endpoints.

## Table of Contents

- [POST /watermark](#post-watermark) - Main watermarking endpoint
- [POST /watermark_grist_download](#post-watermark_grist_download) - Grist attachment download proxy
- [POST /watermark_grist_upload](#post-watermark_grist_upload) - Grist attachment upload proxy

---

## POST /watermark

Main watermarking endpoint. Multipart form upload that reads the uploaded file into memory, converts PDFs to raster (first page only), draws a tiled rotated watermark and returns a watermarked file.

### Request

**Content-Type:** `multipart/form-data`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | Image (JPEG, PNG, etc.) or PDF file |
| `text` | String | No | `Confidential` | Watermark text to apply |
| `text_size` | Integer | No | `3` | Font size (1-4) |

### Response

**Success (200):**
- **For images:** Returns PNG stream with `Content-Type: image/png`
- **For PDFs:** Returns single-page PDF with `Content-Type: application/pdf` (only first page is rasterized)

**Error Responses:**

| Status | Description | Example Detail |
|--------|-------------|----------------|
| 400 | Bad Request | `"Unsupported file. Provide an image or a PDF."` |
| 400 | Bad Request | `"Empty PDF"` |
| 500 | Internal Server Error | `"Watermark error: <exception message>"` |

### Examples

**Watermark an image:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/id.jpg" \
  -F "text=Confidential" \
  -F "text_size=3" \
  --output protected-id.png
```

**Watermark a PDF:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/document.pdf" \
  -F "text=For Audit Only" \
  --output protected.pdf
```

### Implementation Details

- **Image processing:** Uses Pillow (PIL) to draw a tiled, rotated watermark onto an RGBA image, then compositing and returning RGB/PNG
- **Font loading:** Attempts common system fonts (DejaVuSans, Arial); falls back to Pillow default font if none found
- **PDF handling:** Uses PyMuPDF (fitz) to render the first page at 144 DPI into an RGB image, then applies watermarking
- **Trademark:** A faint "Created with GeeDeePermark - https://geedeepermark.cpvo.org/" text is drawn at the bottom-right
- **Processing:** All done in-memory via BytesIO; no files written to disk
- **Logging:** IP addresses are NOT logged, only stats

---

## POST /watermark_grist_download

Grist integration endpoint that downloads an attachment from Grist via authenticated proxy. This endpoint bypasses CORS restrictions when the Grist custom widget needs to download attachments.

### Request

**Content-Type:** `multipart/form-data`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `attachment_id` | Integer | Yes | Grist attachment ID to download |
| `token` | String | Yes | Grist access token (obtained via `grist.docApi.getAccessToken()`) |
| `base_url` | String | Yes | Grist document base URL (e.g., `https://docs.getgrist.com/o/org/doc/docId`) |

### Response

**Success (200):**
- Returns the file content with the original `Content-Type` from Grist
- Streams the attachment directly from Grist to the client

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Missing required parameters or invalid request |
| 500 | Error downloading from Grist (network error, invalid token, etc.) |

### Implementation Details

- Uses `httpx.AsyncClient` for async HTTP requests
- Constructs download URL: `{base_url}/attachments/{attachment_id}/download?auth={token}`
- Streams response directly without storing in memory
- Required to bypass browser CORS restrictions from Grist widgets

---

## POST /watermark_grist_upload

Grist integration endpoint that uploads a file to Grist via authenticated proxy with required headers. This endpoint bypasses CORS restrictions and adds the `X-Requested-With: XMLHttpRequest` header required by Grist for unauthenticated requests.

### Request

**Content-Type:** `multipart/form-data`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | File to upload to Grist |
| `token` | String | Yes | Grist access token (obtained via `grist.docApi.getAccessToken()`) |
| `base_url` | String | Yes | Grist document base URL |

### Response

**Success (200):**
- Returns Grist upload response as JSON (contains attachment ID)
- Example: `[123]` (array with new attachment ID)

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Missing required parameters or invalid request |
| 500 | Error uploading to Grist (network error, invalid token, permission denied, etc.) |

### Implementation Details

- Uses `httpx.AsyncClient` for async HTTP requests
- Constructs upload URL: `{base_url}/attachments?auth={token}`
- **Critical header:** Sets `X-Requested-With: XMLHttpRequest` to satisfy Grist authentication requirements
- Grist requires either `Content-Type: application/json` or `X-Requested-With: XMLHttpRequest` for requests
- Browser `fetch()` from widgets cannot set `X-Requested-With` header due to CORS, hence the server-side proxy

### Why This Endpoint Exists

Grist has strict authentication requirements for API requests:
- Requires specific headers that browser security policies prevent setting from custom widgets
- Direct upload from widget results in: `"Unauthenticated requests require one of the headers 'Content-Type: application/json' or 'X-Requested-With: XMLHttpRequest'"`
- This proxy adds the required header server-side, bypassing browser limitations

---

## Technical Architecture

### Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pillow` - Image processing and watermarking
- `pymupdf` - PDF to image conversion
- `httpx` - Async HTTP client for Grist proxy endpoints
- `python-multipart` - Multipart form data parsing

### Security Considerations

- **In-memory processing:** No files are persisted to disk
- **No IP logging:** Only basic traffic stats collected
- **Access tokens:** Grist tokens passed as query parameters, never stored
- **Service account:** Runs under unprivileged user (e.g., `caddy`)
- **TLS required:** Use reverse proxy (Caddy/Nginx) for HTTPS

### Operational Notes

- **PDF limitation:** Only first page processed; multi-page support could be added
- **Image formats:** Uses Pillow's autodetection; some exotic formats may fail
- **File size limits:** Set by reverse proxy configuration (`client_max_body_size`)
- **Hot reload:** If code changes, reload uvicorn/systemd service

### Error Handling

All endpoints return JSON error responses:
```json
{
  "detail": "Error message here"
}
```

### Reverse Proxy Configuration

See [SETUP.md](SETUP.md) for complete Caddy and Nginx configuration examples with security hardening.

---

## Complete Example Workflow (Grist Integration)

1. **User opens Grist document** with custom widget
2. **Widget requests token:** `grist.docApi.getAccessToken({readOnly: false})`
3. **Widget detects new source files** in attachments column
4. **For each source file:**
   - Call `POST /watermark_grist_download` with `attachment_id`, `token`, `base_url`
   - Receive original file content
   - Call `POST /watermark` with file content, text, size
   - Receive watermarked file
   - Call `POST /watermark_grist_upload` with watermarked file, `token`, `base_url`
   - Receive new attachment ID
   - Update destination column with new attachment ID
5. **Result:** Watermarked files appear in destination column

---

## Support & Contributing

- **Issues:** Report on GitHub repository
- **Documentation:** [User Guide](index.html) | [Grist Plugin](../grist-plugin/README.md) | [Setup Guide](SETUP.md)
- **Source:** Single-file FastAPI app (`app.py`)

**Author:** FredT34, seasoned DPO
