## Operating Modes

### LOCKED constant

The `/watermark` endpoint supports three LOCKED modes:

- **LOCKED = 0 (Unlocked Mode)**:  
  Accepts `file`, `text` (optional), `text_size` (optional). Rejects `uuid` parameter.

- **LOCKED = 1 (Locked Mode)**:  
  Accepts `file`, `uuid` (required). Rejects `text` and `text_size` parameters. Loads config from `configs/{uuid}.json`.

- **LOCKED = 2 (Mixed Mode)**:  
  Accepts `file`, and EITHER `uuid` OR `text`/`text_size` (mutually exclusive). Returns 400 if both or neither provided.

### Parameters Table
| Parameter    | Unlocked Mode        | Locked Mode    | Mixed Mode  |
|--------------|-----------------------|----------------|-------------|
| file         | Required              | Required        | Required    |
| text         | Optional              | Reject          | Optional    |
| text_size    | Optional              | Reject          | Optional    |
| uuid         | Reject                | Required        | Optional    |

### Examples

**Unlocked Mode:**
```bash
curl -X POST /watermark \
  -F 'file=@path/to/file' \
  -F 'text=Sample text' \
  -F 'text_size=12'
```

**Locked Mode:**
```bash
curl -X POST /watermark \
  -F 'file=@path/to/file' \
  -F 'uuid=your-uuid'
```

**Mixed Mode:**
```bash
curl -X POST /watermark \
  -F 'file=@path/to/file' \
  -F 'text=Sample text' \
  -F 'text_size=12' \
  -F 'uuid=your-uuid'
```

### Security Considerations
- Ensure UUID is validated against a known pattern and exists in the system to prevent unauthorized access to config files.
- Config file loading should be secure to prevent path traversal vulnerabilities.

### Error Responses
- Returns 400 if `uuid` is provided in Unlocked Mode or if both `uuid` and `text/text_size` are provided in Mixed Mode.
- Returns 404 if the provided UUID does not correspond to an existing config file.