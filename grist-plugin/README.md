# GeeDeePermark Grist Plugin

A Grist custom widget that automatically watermarks images and PDFs using the GeeDeePermark API. Supports centralized configuration, auto-processing on row changes, and incremental watermarking.

## Features

- **Auto-processing**: Automatically watermarks new files when rows change (configurable)
- **Incremental watermarking**: Only processes new files, preserves existing watermarked documents (position-based matching)
- **Centralized configuration**: Uses a Grist Config table for organization-wide settings
- **Dynamic UI**: Switches between editable inputs and read-only display based on configuration
- **Debug mode**: Show/hide debug elements via configuration parameter
- **Secure authentication**: Uses Grist access tokens with proxy endpoints to avoid CORS issues

## Quick Setup

1. **Host the widget**: Publish `grist-plugin/index.html` and `style.css` to a web server accessible by Grist.

2. **Add Custom Widget**:
   - In your Grist document, add a *Custom* widget
   - Set the widget URL to your hosted `index.html`
   - Enable **Full document access** (required for reading/writing attachments)

3. **Map Columns**:
   - `Source` → Attachments column containing original files
   - `Dest` → Attachments column for watermarked output

4. **Configure** (choose one method):

### Option A: Config Table (Recommended for teams)

Create a table named **Config** with columns:
- `Param` (Text)
- `Value` (Text)
- `Comments` (Text, optional)

Add these rows:

| Param | Value | Comments |
|-------|-------|----------|
| `WatermarkText` | `Confidential` | Default watermark text |
| `WatermarkSize` | `3` | Font size (1-4) |
| `Watermark_API_URL` | `https://geedeepermark.cpvo.org` | API endpoint (required) |
| `WatermarkAllowReprocess` | `0` | Allow re-watermarking (1=yes, 0=no) |
| `WatermarkAutoProcessRow` | `1` | Auto-process on row change (1=yes, 0=no) |
| `WatermarkDebug` | `0` | Show debug UI (1=yes, 0=no) |

When config exists, the widget UI becomes read-only and displays configured values.

### Option B: Per-User Settings (No Config table)

If no Config table exists, users can:
- Enter watermark text and size in the widget
- Check "Allow reprocess" to re-watermark existing files
- Check "Auto-process" to enable automatic watermarking on row changes
- Manually click "Apply watermark" button

Settings are saved in browser localStorage per user.

## How It Works

### Auto-Processing
When `WatermarkAutoProcessRow=1` (or checkbox enabled):
- Widget monitors the Source column for changes
- Automatically watermarks new files when detected
- Uses position-based matching: `source[i]` → `dest[i]`
- Only processes positions where dest is empty or different from source

### Authentication & CORS
- Widget requests Grist access token via `grist.docApi.getAccessToken()`
- Uses proxy endpoints `/download_from_grist` and `/upload_to_grist` to avoid CORS
- Token passed as `?auth=` query parameter + `X-Requested-With: XMLHttpRequest` header

### Processing Flow
1. Download source file from Grist via `/download_from_grist`
2. Send to `/watermark` API with text and size parameters
3. Upload watermarked result to Grist via `/upload_to_grist`
4. Update Dest column with new attachment IDs

## API Requirements

The GeeDeePermark API must provide these endpoints:

- `POST /watermark` - Watermark a file
  - Input: `file`, `text`, `text_size`
  - Output: Watermarked PNG or PDF

- `POST /download_from_grist` - Proxy download from Grist
  - Input: `attachment_id`, `token`, `base_url`
  - Output: File content

- `POST /upload_to_grist` - Proxy upload to Grist
  - Input: `file`, `token`, `base_url`
  - Output: Grist upload response with attachment ID

## Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `WatermarkText` | Text | `Confidential` | Default watermark text |
| `WatermarkSize` | Number | `3` | Font size (1-4) |
| `Watermark_API_URL` | URL | - | API endpoint (required) |
| `WatermarkAllowReprocess` | 0 or 1 | `0` | Allow re-watermarking existing files |
| `WatermarkAutoProcessRow` | 0 or 1 | `0` | Auto-process on row change |
| `WatermarkDebug` | 0 or 1 | `0` | Show debug UI elements |

## Troubleshooting

**Auto-processing not working?**
- Check that `WatermarkAutoProcessRow=1` in Config table (or checkbox enabled)
- Verify Grist "Select By" is not filtering rows
- Ensure Source column actually contains attachments

**Upload fails with 401 Unauthorized?**
- Verify "Full document access" is enabled for the widget
- Check that API endpoints use `?auth=` parameter and `X-Requested-With` header

**All files re-watermark every time?**
- Set `WatermarkAllowReprocess=0` to prevent re-watermarking
- Widget uses position-based matching to preserve existing watermarks

**Need to see what's happening?**
- Set `WatermarkDebug=1` to show debug UI elements
- Check browser console for detailed logs

## Files

- `index.html` - Main widget code (HTML + JavaScript)
- `style.css` - Compact, responsive styling
- `README.md` - This file

## Dependencies

- Grist Plugin API (`grist-plugin-api.js` loaded from CDN)
- GeeDeePermark API (FastAPI backend with httpx for Grist proxying)

## Security Notes

- Widget requires **Full document access** to read/write attachments
- Access tokens obtained via `grist.docApi.getAccessToken()` with `readOnly: false`
- Tokens never stored, requested fresh for each operation
- All file processing happens server-side via API
- Original files remain untouched in Source column
