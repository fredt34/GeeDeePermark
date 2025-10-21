# GeeDeePerMark API Documentation

Complete technical reference for all API endpoints.

## Table of Contents

- [POST /watermark](#post-watermark) - Main watermarking endpoint
- [POST /download_from_grist](#post-download_from_grist) - Grist attachment download proxy
- [POST /upload_to_grist](#post-upload_to_grist) - Grist attachment upload proxy

---

## POST /watermark

Main watermarking endpoint. Multipart form upload that reads the uploaded file into memory, converts PDFs to raster (first page only), draws a tiled rotated watermark and returns a watermarked file.

### Operating Modes

The `/watermark` endpoint operates in two modes controlled by the **`LOCKED`** deployment constant in `app.py`:

- **`LOCKED = 0` (Unlocked Mode)**: Users can specify custom watermark text and size
- **`LOCKED = 1` (Locked Mode)**: Watermark configuration is loaded from server-side UUID JSON files

### Request

**Content-Type:** `multipart/form-data`

**Parameters:**

#### Unlocked Mode (LOCKED = 0)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | Image (JPEG, PNG, etc.) or PDF file |
| `text` | String | No | `Confidential` | Watermark text to apply |
| `text_size` | Integer | No | `3` | Font size (1-4) |
| `uuid` | String | No | - | **REJECTED** (returns 400 error) |

#### Locked Mode (LOCKED = 1)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | Image (JPEG, PNG, etc.) or PDF file |
| `uuid` | String | Yes | - | Configuration UUID (e.g., `00000000-0000-0000-0000-000000000000`) |
| `text` | String | No | - | **REJECTED** (returns 400 error) |
| `text_size` | Integer | No | - | **REJECTED** (returns 400 error) |

### Response

**Success (200):**
- **For images:** Returns PNG stream with `Content-Type: image/png`
- **For PDFs:** Returns single-page PDF with `Content-Type: application/pdf` (only first page is rasterized)

**Error Responses:**

| Status | Description | Example Detail |
|--------|-------------|----------------|
| 400 | Bad Request | `"Unsupported file. Provide an image or a PDF."` |
| 400 | Bad Request | `"Empty PDF"` |
| 400 | Bad Request | `"Parameter 'uuid' not allowed in unlocked mode"` |
| 400 | Bad Request | `"Parameters 'text' and 'text_size' not allowed in locked mode"` |
| 400 | Bad Request | `"Parameter 'uuid' is required in locked mode"` |
| 400 | Bad Request | `"Invalid UUID format"` |
| 400 | Bad Request | `"Invalid UUID: directory traversal detected"` |
| 404 | Not Found | `"Configuration file not found for UUID: {uuid}"` |
| 413 | Payload Too Large | `"Configuration file too large (max 1 MB)"` |
| 500 | Internal Server Error | `"Watermark error: <exception message>"` |

### Examples

#### Unlocked Mode (LOCKED = 0)

**Watermark an image with custom text:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/id.jpg" \
  -F "text=Confidential" \
  -F "text_size=3" \
  --output protected-id.png
```

**Watermark a PDF with custom text:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/document.pdf" \
  -F "text=For Audit Only" \
  -F "text_size=2" \
  --output protected.pdf
```

**Watermark with defaults:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/document.pdf" \
  --output protected.pdf
```

#### Locked Mode (LOCKED = 1)

**Watermark using UUID configuration:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/document.pdf" \
  -F "uuid=00000000-0000-0000-0000-000000000000" \
  --output protected.pdf
```

**Watermark using different UUID:**
```bash
curl -X POST "https://geedeepermark.cpvo.org/watermark" \
  -F "file=@/path/to/sensitive.jpg" \
  -F "uuid=a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  --output protected.png
```

### Locked Mode Configuration

In locked mode, watermark settings are read from JSON configuration files stored in the `configs/` directory on the server.

#### Configuration File Structure

Configuration files must be named `{uuid}.json` and placed in the `configs/` directory.

**Example: `configs/00000000-0000-0000-0000-000000000000.json`**
```json
{
  "text": "Confidential",
  "text_size": 3
}
```

**Example: `configs/a1b2c3d4-e5f6-7890-abcd-ef1234567890.json`**
```json
{
  "text": "Internal Use Only",
  "text_size": 2
}
```

#### Configuration Keys

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `text` | String | No | `"Confidential"` | Watermark text to apply |
| `text_size` | Integer | No | `3` | Font size (1-4) |

**Note:** If keys are missing from the JSON file, the system falls back to the default values.

#### Security Features

The `load_config_from_uuid()` function implements multiple security measures:

1. **UUID Format Validation**: Only accepts hex digits and hyphens
2. **Directory Traversal Prevention**: Uses `Path.resolve()` to ensure files are inside `configs/`
3. **File Size Limit**: Rejects configuration files larger than 1 MB
4. **Safe JSON Parsing**: Catches and reports JSON parsing errors

#### Setup Requirements

1. Create a `configs/` directory in the application root:
   ```bash
   mkdir configs
   ```

2. Add configuration files for each UUID:
   ```bash
   echo '{"text": "Confidential", "text_size": 3}' > configs/00000000-0000-0000-0000-000000000000.json
   ```

3. Set appropriate file permissions:
   ```bash
   chmod 644 configs/*.json
   ```

4. Ensure the application has read access to the `configs/` directory

### Implementation Details

- **Image processing:** Uses Pillow (PIL) to draw a tiled, rotated watermark onto an RGBA image, then compositing and returning RGB/PNG
- **Font loading:** Attempts common system fonts (DejaVuSans, Arial); falls back to Pillow default font if none found
- **PDF handling:** Uses PyMuPDF (fitz) to render the first page at 144 DPI into an RGB image, then applies watermarking
- **Trademark:** A faint "Created with GeeDeePermark - https://geedeepermark.cpvo.org/" text is drawn at the bottom-right
- **Processing:** All done in-memory via BytesIO; no files written to disk
- **Logging:** IP addresses are NOT logged, only stats
- **Mode switching:** Change `LOCKED` constant in `app.py` and restart the service

---

## POST /download_from_grist

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

## POST /upload_to_grist

Grist integration endpoint that uploads a file to Grist via authenticated proxy with required headers. This endpoint bypasses CORS restrictions and adds the `X-Requested-With: XMLHttpRequest` header that Grist requires for authentication.

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
- **UUID validation:** Prevents directory traversal and malicious file access in locked mode
- **File size limits:** Configuration files limited to 1 MB; upload limits set by reverse proxy

### Operational Notes

- **PDF limitation:** Only first page processed; multi-page support could be added
- **Image formats:** Uses Pillow's autodetection; some exotic formats may fail
- **File size limits:** Set by reverse proxy configuration (`client_max_body_size`)
- **Hot reload:** If code changes, reload uvicorn/systemd service
- **Mode switching:** Change `LOCKED` constant in `app.py` from 0 to 1 (or vice versa) and restart
- **Config updates:** In locked mode, configuration changes require updating JSON files (no restart needed)

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

### Unlocked Mode Workflow

1. **User opens Grist document** with custom widget
2. **Widget requests token:** `grist.docApi.getAccessToken({readOnly: false})`
3. **Widget detects new source files** in attachments column
4. **For each source file:**
   - Call `POST /download_from_grist` with `attachment_id`, `token`, `base_url`
   - Receive original file content
   - Call `POST /watermark` with file content, `text`, `text_size`
   - Receive watermarked file
   - Call `POST /upload_to_grist` with watermarked file, `token`, `base_url`
   - Receive new attachment ID
   - Update destination column with new attachment ID
5. **Result:** Watermarked files appear in destination column

### Locked Mode Workflow

1. **Administrator creates UUID configurations** in `configs/` directory
2. **User opens Grist document** with custom widget
3. **Widget requests token:** `grist.docApi.getAccessToken({readOnly: false})`
4. **Widget reads UUID from Grist column** (or uses hardcoded UUID)
5. **For each source file:**
   - Call `POST /download_from_grist` with `attachment_id`, `token`, `base_url`
   - Receive original file content
   - Call `POST /watermark` with file content and `uuid` (text comes from server config)
   - Receive watermarked file
   - Call `POST /upload_to_grist` with watermarked file, `token`, `base_url`
   - Receive new attachment ID
   - Update destination column with new attachment ID
6. **Result:** Watermarked files appear in destination column with predefined watermarks

---

## Support & Contributing

- **Issues:** Report on GitHub repository
- **Documentation:** [User Guide](index.html) | [Grist Plugin](../grist-plugin/README.md) | [Setup Guide](SETUP.md)
- **Source:** Single-file FastAPI app (`app.py`)

**Author:** FredT34, seasoned DPO
