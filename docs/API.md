# GeeDeePerMark API Documentation

Complete technical reference for all API endpoints.

## Table of Contents

- [POST /watermark](#post-watermark) - Main watermarking endpoint
- [POST /watermark_grist_download](#post-watermark_grist_download) - Grist attachment download proxy
- [POST /watermark_grist_upload](#post-watermark_grist_upload) - Grist attachment upload proxy

---

## POST /watermark

Main watermarking endpoint. Multipart form upload that reads the uploaded file into memory, converts PDFs to raster (first page only), draws a tiled rotated watermark and returns a watermarked file.

### Operating Modes

The `/watermark` endpoint supports three LOCKED modes (configured via `LOCKED` constant in `app.py`):

#### LOCKED = 0 (Unlocked Mode)
- Accepts `file`, `text` (optional), `text_size` (optional)
- Rejects `uuid` parameter (returns 400)
- Users can specify custom watermark text and size

#### LOCKED = 1 (Locked Mode)
- Accepts `file`, `uuid` (required)
- Rejects `text` and `text_size` parameters (returns 400)
- Watermark configuration loaded from `configs/{uuid}.json`

#### LOCKED = 2 (Mixed Mode)
- Accepts `file`, and EITHER `uuid` OR `text`/`text_size` (mutually exclusive)
- Returns 400 if both uuid and text are provided
- Returns 400 if neither uuid nor text are provided

### Request

**Content-Type:** `multipart/form-data`

**Parameters:**

| Parameter | Type | Unlocked Mode | Locked Mode | Mixed Mode | Default | Description |
|-----------|------|---------------|-------------|------------|---------|-------------|
| `file` | File | Required | Required | Required | - | Image (JPEG, PNG, etc.) or PDF file |
| `text` | String | Optional | Reject | Optional | `Confidential` | Watermark text to apply |
| `text_size` | Integer | Optional | Reject | Optional | `3` | Font size (1-4) |
| `uuid` | String | Reject | Required | Optional | - | Configuration UUID (loads from `configs/{uuid}.json`) |

### Response

**Success (200):**
- **For images:** Returns PNG stream with `Content-Type: image/png`
- **For PDFs:** Returns single-page PDF with `Content-Type: application/pdf` (only first page is rasterized)

**Error Responses:**

| Status | Description | Example Detail |
|--------|-------------|----------------|
| 400 | Bad Request | `"Unsupported file. Provide an image or a PDF."` |
| 400 | Bad Request | `"Empty PDF"` |
| 400 | Mode violation | `"Parameter 'uuid' not allowed in unlocked mode"` |
| 400 | Mode violation | `"Cannot provide both 'uuid' and 'text' parameters in mixed mode"` |
| 400 | Invalid UUID | `"Invalid UUID format"` |
| 404 | Config not found | `"Configuration file not found for UUID: {uuid}"` |
| 413 | File too large | `"Configuration file too large (max 1 MB)"` |
| 500 | Internal Server Error | `"Watermark error: <exception message>"` |

### Examples

**Unlocked Mode (LOCKED=0):**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/id.jpg" \
  -F "text=Confidential" \
  -F "text_size=3" \
  --output protected-id.png
```

**Locked Mode (LOCKED=1):**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/document.pdf" \
  -F "uuid=00000000-0000-0000-0000-000000000000" \
  --output protected.pdf
```

**Mixed Mode (LOCKED=2) - with UUID:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/document.pdf" \
  -F "uuid=00000000-0000-0000-0000-000000000000" \
  --output protected.pdf
```

**Mixed Mode (LOCKED=2) - with custom text:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/document.pdf" \
  -F "text=For Audit Only" \
  -F "text_size=4" \
  --output protected.pdf
```

### UUID Configuration Files

When using `uuid` parameter, the configuration is loaded from `configs/{uuid}.json`:

**Example config file (`configs/00000000-0000-0000-0000-000000000000.json`):**
```json
{
  "text": "Confidential - HR Department",
  "text_size": 3
}
```

**Security features:**
- Validates UUID format (only hex digits and hyphens)
- Prevents directory traversal using `Path.resolve()`
- Rejects files larger than 1 MB
- Returns 404 if file not found

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
- **UUID validation:** Strict format validation and path traversal prevention
- **Config file security:** Size limits (1 MB max), path resolution checks
- **Access tokens:** Grist tokens passed as query parameters, never stored
- **Service account:** Runs under unprivileged user (e.g., `caddy`)
- **TLS required:** Use reverse proxy (Caddy/Nginx) for HTTPS

### Operational Notes

- **PDF limitation:** Only first page processed; multi-page support could be added
- **Image formats:** Uses Pillow's autodetection; some exotic formats may fail
- **File size limits:** Set by reverse proxy configuration (`client_max_body_size`)
- **Hot reload:** If code changes, reload uvicorn/systemd service
- **Endpoint naming:** All endpoints share `/watermark` prefix for simplified reverse proxy configuration

### Error Handling

All endpoints return JSON error responses:
```json
{
  "detail": "Error message here"
}
```

### Reverse Proxy Configuration

See [SETUP.md](SETUP.md) for complete Caddy and Nginx configuration examples with security hardening.

**Simplified configuration with harmonized paths:**

**Caddy:**
```caddy
@api {
    path /watermark*  # Covers all /watermark* endpoints
}
handle @api {
    reverse_proxy 127.0.0.1:8000
}
```

**Nginx:**
```nginx
location ~ ^/watermark {
    proxy_pass http://127.0.0.1:8000;
    # ... proxy headers
}
```

---

## Complete Example Workflow (Grist Integration)

1. **User opens Grist document** with custom widget
2. **Widget requests token:** `grist.docApi.getAccessToken({readOnly: false})`
3. **Widget detects new source files** in attachments column
4. **For each source file:**
   - Call `POST /watermark_grist_download` with `attachment_id`, `token`, `base_url`
   - Receive original file content
   - Call `POST /watermark` with file content, text, size (or uuid)
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