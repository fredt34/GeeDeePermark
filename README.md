# GeeDeePerMark

The privacy watermark. Available at https://geedeepermark.cpvo.org/

## Goal

Provide a simple API to have images watermarked with a given text - So Your Apps Will Never Store Unprotected ID Documents Again.

## Features

- **REST API**: Three endpoints for watermarking and Grist integration
- **In-memory processing**: No files stored on disk
- **Multiple formats**: Images (JPEG, PNG, etc.) and PDF files
- **Grist custom widget**: Auto-watermark documents directly in your Grist tables ([see plugin documentation](grist-plugin/README.md))
- **Configurable**: Text and size customization

## API Endpoints

Three main endpoints are available:

- **POST /watermark** — Main watermarking endpoint (images and PDFs)
- **POST /download_from_grist** — Grist attachment download proxy (bypasses CORS)
- **POST /upload_to_grist** — Grist attachment upload proxy (bypasses CORS)

**[→ Complete API Documentation](docs/API.md)** — Detailed technical reference with examples, parameters, responses, and implementation details.

All process runs in memory - no image is ever stored

## Security of your documents

Whey are processed in-memory only and run under a service account (cadd in this case)

## Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pillow` - Image processing
- `pymupdf` - PDF handling
- `httpx` - HTTP client for Grist proxy endpoints
- `python-multipart` - Form data parsing

Install with: `pip install fastapi uvicorn pillow pymupdf httpx python-multipart`

## Grist Integration

A custom widget is available for Grist users to automatically watermark attachments in tables. The widget supports:
- Auto-processing on row changes
- Centralized configuration via Config table
- Incremental watermarking (only new files)
- Position-based matching to preserve existing watermarks

**[→ Full plugin documentation](grist-plugin/README.md)**

## Logs

We run NO LOGS. We're not spies. We may run basic traffic logs at some point to count visitors. No IP, no file copy, no terminal fingerprinting.

## Language

Python. Has lots of libraries, secure and easy to install & read. Shamelessly vibe-coded with VSCode, Cline and free Grok-AI.

Program was designed be as short as possible - ideally, only 1 single file, no compile, in order to be extremely easy to install and run. No Java.

**Note on Grist integration**: The API includes proxy endpoints (`/download_from_grist` and `/upload_to_grist`) using `httpx` to bypass CORS restrictions when the Grist custom widget uploads attachments. Grist requires either `Content-Type: application/json` or `X-Requested-With: XMLHttpRequest` header for unauthenticated requests, which browser fetch() cannot set from widgets, hence the server-side proxy solution.

## Available on

https://geedeepermark.cpvo.org

This can't work in CloudFlare Workers - so, self-hosting was necessary.

Plus, it's always fun to learn new techs 😃.

Please report if you install it - at least for counting, you don't want to publish the url of your service.

## Documentation

- **[Complete API Documentation](docs/API.md)** - Full technical reference for all endpoints
- **[Full Documentation Site](docs/index.html)** - Overview and use cases
- **[Grist Plugin Guide](grist-plugin/README.md)** - Custom widget setup and configuration
- **[Setup & Installation Guide](docs/SETUP.md)** - Complete deployment instructions with Caddy/Nginx examples

## Origin

Inspired by https://filigrane.beta.gouv.fr/, but this tool has no API

## WARNING

If you change the code, reload your uvicorn or equivalent afterwards.

## Coming next (perhaps)

An UI for your students, users, customers to drop their documents and being able to transmit them securely. I might find the time to write it - or not.

## Author

FredT34, seasonned DPO
