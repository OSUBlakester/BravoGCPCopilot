# Accent MTI File Migration Process - Comprehensive Guide

This document describes how the Bravo application migrates user configurations from Accent AAC devices using MTI (Multilevel Therapeutic Intervention) files.

---

## Table of Contents

1. [Overview](#overview)
2. [MTI File Format](#mti-file-format)
3. [Migration Architecture](#migration-architecture)
4. [Frontend Flow](#frontend-flow)
5. [Parsing Details](#parsing-details)
6. [Data Mapping](#data-mapping)
7. [API Endpoints](#api-endpoints)
8. [Complete Data Flow](#complete-data-flow)

---

## Overview

The Bravo MTI migration process allows users to import their Accent device configurations into Bravo. The migration involves:

1. **Upload**: User uploads a `.mti` file from their Accent device
2. **Parse**: Server parses the binary MTI file to extract pages and buttons
3. **Preview**: User selects buttons to import and chooses a destination page
4. **Map**: Accent button/page data is converted to Bravo format
5. **Import**: Mapped buttons are saved to the user's Bravo account

### Key Files

| File | Purpose |
|------|---------|
| `accent_mti_parser.py` | Parses binary MTI files; extracts page/button data |
| `accent_bravo_mapper.py` | Converts Accent format to Bravo format |
| `static/accent_migration.js` | Frontend UI for migration workflow |
| `static/accent_migration.html` | Migration interface template |
| `server.py` (routes) | API endpoints for migration |

---

## MTI File Format

### File Structure

MTI files are **binary files** containing compressed Accent device configuration data. The format consists of:

```
[MTI Header]
[Zlib Compressed Data]
  ├─ Page Records (m-records)
  ├─ Button Records  
  ├─ Navigation Data
  └─ Function Markers
```

### High-Level Format

1. **Header** (typically `MTI1` or similar magic bytes)
2. **Zlib Compression**: All configuration data is zlib-compressed
3. **Decompressed Data**: Contains binary button definitions

### Button Records (m-records)

Button data is stored as repeating **m-records** with the following structure:

```
Offset  Size  Description
------  ----  -----------
0       4     Marker: b'm\x00\x04\xfd'
4       2     Page ID (2 bytes, byte-swapped)
6       1     Sequence (button position on grid)
7       2     Reserved/Header info
9       1     Format byte (determines how to parse rest of button)
10+     ...   Variable-length button data (depends on format)
```

### Button Grid Positioning

- **Accent Grid**: 7 rows × 16 columns = 112 buttons per page
- **Sequence Calculation**:
  ```
  row = sequence / 16
  col = sequence % 16
  ```

### Page ID Encoding

Page IDs are stored with byte-swapping:
- **Raw bytes**: `0x00 0x04`
- **Interpreted** (after swap): `0x0400`
- **Displayed**: `"0400"`

Example: `[0x04, 0x00]` → swap to `[0x00, 0x04]` → int value `0x0400` → hex string `"0400"`

---

## MTI File Format

### Five Button Format Types

The parser handles **5 different button data formats** based on the byte-9 value:

#### Format 5: Function-Based (byte_9: 0x87, 0xAF, 0xCC, 0xFF)

Used for buttons with complex functions (navigation, speech markers, etc.)

**Structure**:
```
Offset  Size  Description
------  ----  -----------
9       1     Format marker (0x87, 0xAF, 0xCC, or 0xFF)
10-12   3     Reserved/padding
13      1     Button name length
14      ...   Button name (ASCII, variable length)
14+len  ...   Icon length + Icon name
...     ...   Function markers (0xA4-prefixed)
...     2     Terminator (CRLF: \r\n)
```

**Function Markers** (start with byte 0xA4):
- `0xA4 0x3A`: Speech text (continues until next marker or CRLF)
- `0xA4 0x06`: RANDOM-CHOICE function reference
- `0xA4 0x85`: GO-BACK-PAGE function
- `0xA4 0x8B`: GOTO-HOME function
- `0xA4 0x8C`: SET-PAGE(target) permanent navigation
- `0xA4 0x8D`: SET-PAGE(target) temporary navigation

**Special Patterns** (also Format 5):
- `0xFF 0x80 0x85 0xFE`: GOTO-HOME inline marker
- `0xFF 0x80 0x8C ...`: SET-PAGE(name) inline
- `0xFF 0x80 0x3A 0xFE`: CLEAR-DISPLAY inline
- `0xFF 0x81 0x05 0xFE`: GO-BACK-PAGE inline

#### Format 2: Null-Terminated (byte_9: 0x00)

Simple format with no structured fields.

**Structure**:
```
Offset  Size  Description
------  ----  -----------
9-10    ...   Null bytes (padding)
11+     ...   Button name/speech text (ASCII)
...     2     Terminator (CRLF: \r\n)
```

- All text from position 11 until CRLF is treated as the button name and speech (combined)
- Serves as both label and spoken text

#### Format 1: Standard (byte_9: 1-49)

The byte_9 value IS the button name length.

**Structure**:
```
Offset  Size  Description
------  ----  -----------
9       1     Name length (1-49 bytes)
10      ...   Button name (ASCII, exact length from byte_9)
10+len  1     Icon length (or 0x00 if no icon)
...     ...   Icon name (if length > 0)
...     ...   Function markers (0xA4-prefixed, like Format 5)
...     2     Terminator (CRLF: \r\n)
```

**Special Handling**: Detects **merged buttons** (multiple buttons stored sequentially in same record):
- Merged buttons are separated by CRLF within the record
- Parser extends the read window to capture all merged button data

#### Format 4: Simple Speech (byte_9: 50-100)

Used for buttons that are primarily speech-text buttons.

**Structure**:
```
Offset  Size  Description
------  ----  -----------
9       1     Speech length (50-100 bytes)
10      ...   Speech text (ASCII, exact length from byte_9)
...     ...   Optional function markers
...     2     Terminator (CRLF: \r\n)
```

#### Format 3: Offset Name (byte_9: > 100)

Used when button name is stored at an offset or has complex encoding.

**Structure**:
```
Offset  Size  Description
------  ----  -----------
9       1     Offset or complex indicator (> 100)
10+     ...   Inline FF 80 navigation patterns (like Format 5)
...     2     Terminator (CRLF: \r\n)
```

---

## Special Control Markers and Sequences

### Control Characters

| Byte/Sequence | Meaning | Handled As |
|---------------|---------|-----------|
| `0x1C` | WAIT-ANY-KEY marker | `[PAUSE]` |
| `0xFF 0x80 0x1C 0xFE` | Wait/pause marker | `[PAUSE]` |
| `0xFF 0x80 { 0xFE` | PROMPT-MARKER | `{` |
| `«WAIT-ANY-KEY»` (UTF-8) | Wait marker text | `[PAUSE]` |
| `«PROMPT-MARKER»` (UTF-8) | Prompt marker text | Extracted as button name |
| `0x03` (inside speech) | VOICE-SET-TEMPORARY marker | `VOICE-SET-TEMPORARY(voiceparam)` |
| `0x04` (inside speech) | VOICE-CLEAR-TEMPORARY marker | `VOICE-CLEAR-TEMPORARY()` |

### Guillemet Markers (« »)

Markers in UTF-8 text format (inside button data):
- `«SET-PAGE(...)»`: Navigate to page
- `«GOTO-HOME»`: Navigate to home
- `«GO-BACK-PAGE»`: Go back in history
- `«CLEAR-DISPLAY»`: Clear display
- `«RANDOM-CHOICE(...)»`: Choose random option

Parser extracts these and converts to Bravo functions.

---

## Parsing Details

### Step-by-Step Parsing Algorithm

#### 1. File Decompression

```python
# Read entire MTI file as binary
with open(file_path, 'rb') as f:
    data = f.read()

# Skip header, find and decompress zlib data
compressed_start = data.find(b'x\x9c')  # zlib magic bytes (or similar)
decompressed = zlib.decompress(data[compressed_start:])
```

#### 2. Find m-records

```python
pos = 0
while pos < len(decompressed):
    # Look for marker: b'm\x00\x04\xfd'
    if decompressed[pos:pos+4] == b'm\x00\x04\xfd':
        # Extract page ID and sequence
        page_id_bytes = decompressed[pos+4:pos+6]
        # === BYTE SWAP ===
        page_id_raw = struct.unpack('<H', page_id_bytes)[0]
        page_id_swapped = ((page_id_raw & 0xFF) << 8) | ((page_id_raw >> 8) & 0xFF)
        
        sequence = decompressed[pos+6]  # Button position
        row = sequence // 16  # Convert to grid position
        col = sequence % 16
        
        # Parse button data starting at offset 9
        parse_button(decompressed, pos, page_id_swapped, sequence, row, col)
    pos += 1
```

#### 3. Determine Format and Parse

```python
byte_9 = decompressed[pos+9]

if byte_9 in [0x87, 0xAF, 0xCC, 0xFF]:
    # === FORMAT 5: Function-based ===
    parse_format_5(decompressed, pos)
    
elif byte_9 == 0x00:
    # === FORMAT 2: Null-terminated ===
    parse_format_2(decompressed, pos)
    
elif 1 <= byte_9 <= 49:
    # === FORMAT 1: Standard ===
    parse_format_1(decompressed, pos, byte_9)
    
elif 50 <= byte_9 <= 100:
    # === FORMAT 4: Simple speech ===
    parse_format_4(decompressed, pos, byte_9)
    
elif byte_9 > 100:
    # === FORMAT 3: Offset name ===
    parse_format_3(decompressed, pos)
```

#### 4. Format 5 Parsing (Common Case)

```python
def parse_format_5(data, pos):
    name_len = data[pos+13]
    button_name = data[pos+14:pos+14+name_len].decode('ascii', errors='ignore')
    pos_cursor = pos + 14 + name_len
    
    # Skip null terminator
    if data[pos_cursor] == 0:
        pos_cursor += 1
    
    # Extract icon (prefixed by length byte)
    icon_len = data[pos_cursor]
    pos_cursor += 1
    icon_name = data[pos_cursor:pos_cursor+icon_len].decode('ascii', errors='ignore')
    pos_cursor += icon_len
    
    # Parse function markers (0xA4-prefixed sequences)
    speech_text = None
    functions = []
    navigation = None
    
    while data[pos_cursor] == 0xA4:
        func_type = data[pos_cursor+1]
        pos_cursor += 2
        
        if func_type == 0x3A:  # Speech
            # Read until next marker or CRLF
            speech_end = pos_cursor
            while data[speech_end] != 0xA4 and data[speech_end:speech_end+2] != b'\r\n':
                speech_end += 1
            speech_text = data[pos_cursor:speech_end].decode('ascii', errors='ignore').strip()
            pos_cursor = speech_end
            
        elif func_type == 0x06:  # RANDOM-CHOICE
            # Extract page reference in parentheses
            ref_start = data.find(b'(', pos_cursor)
            ref_end = data.find(b')', ref_start)
            ref_page = data[ref_start+1:ref_end].decode('ascii', errors='ignore')
            functions.append(f'RANDOM-CHOICE({ref_page})')
            pos_cursor = ref_end + 1
            
        elif func_type == 0x8B:  # GOTO-HOME
            navigation = ('PERMANENT', '0400')
            functions.append('GOTO-HOME')
            
        elif func_type in [0x8C, 0x8D]:  # SET-PAGE
            nav_type = 'PERMANENT' if func_type == 0x8C else 'TEMPORARY'
            target_start = data.find(b'(', pos_cursor)
            target_end = data.find(b')', target_start)
            target = data[target_start+1:target_end].decode('ascii', errors='ignore')
            navigation = (nav_type, target)
            functions.append(f'SET-PAGE({target})')
            pos_cursor = target_end + 1
    
    return {
        'name': button_name,
        'icon': icon_name,
        'speech': speech_text,
        'functions': functions,
        'navigation_type': navigation[0] if navigation else None,
        'navigation_target': navigation[1] if navigation else None
    }
```

#### 5. Text Sanitization

Parser applies multiple sanitization steps:

**Speech Sanitization**:
```python
def sanitize_speech(speech):
    # 1. Replace control markers with [PAUSE]
    speech = speech.replace('\x1c', '[PAUSE]')
    speech = speech.replace('\xff\x80\x1c\xfe', '[PAUSE]')
    speech = speech.replace('«WAIT-ANY-KEY»', '[PAUSE]')
    
    # 2. Remove control characters (ord < 32)
    speech = ''.join(ch for ch in speech if ord(ch) >= 32 or ch in '\n\t')
    
    # 3. Normalize multiple spaces
    while '  ' in speech:
        speech = speech.replace('  ', ' ')
    
    # 4. Strip and remove trailing garbage
    speech = speech.strip()
    garbage_chars = ['$', '/', '|', '#', '>', '<', '_', '+', 'F', 'N', 'e', '0']
    while speech and speech[-1] in garbage_chars:
        speech = speech[:-1].strip()
    
    return speech if speech else None
```

**Name Post-Processing**:
```python
def post_process_button_name(name):
    # 1. Remove guillemet markers
    name = re.sub(r'«[A-Z\-]+(?:\([^)]*\))?»', '', name)
    
    # 2. Remove SET-PAGE(...) text
    name = re.sub(r'\bSET-PAGE\s*\([^)]*\)', '', name, flags=re.IGNORECASE)
    
    # 3. Extract text before brace marker
    if '{' in name:
        name = name.split('{')[0].strip()
    
    # 4. Remove duplicate word sequences (e.g., "word word" → "word")
    words = name.split()
    if len(words) % 2 == 0 and words[:len(words)//2] == words[len(words)//2:]:
        name = ' '.join(words[:len(words)//2])
    
    # 5. Keep only alphabetic words
    if re.search(r'\bpage\b', name, re.IGNORECASE):
        alpha_match = re.match(r"[A-Za-z ]+", name)
        if alpha_match:
            name = alpha_match.group(0).strip()
    
    return name
```

---

## Data Mapping

### Accent Button → Bravo Button

**Accent Format**:
```python
{
    "page_id": "0400",
    "sequence": 19,
    "row": 1,
    "col": 3,
    "name": "pick up lines",
    "icon": "HELLO",
    "speech": "hi",
    "functions": ["RANDOM-CHOICE(random hi)"],
    "navigation_type": "PERMANENT",
    "navigation_target": "0001"
}
```

**Bravo Format**:
```python
{
    "row": 1,
    "col": 3,
    "text": "pick up lines",
    "speechPhrase": "hi",  # or "{RANDOM:hi|hello|hey}" if RANDOM-CHOICE
    "targetPage": "pickuplines",
    "navigationType": "PERMANENT",
    "LLMQuery": "",
    "queryType": "options",
    "hidden": false
}
```

### Mapping Rules (in detail)

#### 1. Button Text (`text`)
```
Accent.name  →  Bravo.text
Applied transformations:
  - Remove guillemet markers («...»)
  - Remove duplicate words
  - Extract text before brace
  - Keep only alphabetic content
```

#### 2. Speech Phrase (`speechPhrase`)

**Case 1: RANDOM-CHOICE function**
```
Accent:  functions: ["RANDOM-CHOICE(random hi)"]
Bravo:   speechPhrase: "{RANDOM:hi|hello|hey}"
         (options extracted from target page buttons)
```

**Case 2: Simple speech text**
```
Accent:  speech: "hello"
Bravo:   speechPhrase: "hello"
```

**Case 3: Navigation button (no speech)**
```
Accent:  navigation_type: "PERMANENT"
Bravo:   speechPhrase: null or undefined
         (navigation-only buttons have no speech)
```

#### 3. Target Page Navigation (`targetPage`)

**GOTO-HOME Function**:
```
Accent:  functions: ["GOTO-HOME"]
Bravo:   targetPage: "home"
```

**SET-PAGE Function**:
```
Accent:  functions: ["SET-PAGE(pickuplines)"]
Bravo:   targetPage: "pickuplines"
         (or maps Accent page ID → Bravo page name)
```

**GO-BACK-PAGE Function**:
```
Accent:  functions: ["GO-BACK-PAGE"]
Bravo:   targetPage: ""  (empty, back button handled by app)
```

**Regular Navigation**:
```
Accent:  navigation_type: "PERMANENT"
         navigation_target: "0201"
Bravo:   targetPage: mapped_page_name_for_0201
         (uses page name mapping from user input)
```

#### 4. Icon Mapping (`assigned_image_url`)

Icons are mapped from Accent names to Bravo identifiers:

```python
ACCENT_TO_BRAVO_ICON_MAP = {
    "HELLO": "wave",
    "GOODBYE": "wave",
    "QUESTION": "question",
    "HELP": "help",
    "YES": "check",
    "NO": "cancel",
    "HAPPY": "happy",
    "SAD": "sad",
    "ANGRY": "angry",
    "FOOD": "food",
    "DRINK": "drink",
    "ANIMALS": "paw",
    "HOME": "home",
    "SCHOOL": "school",
    "PEOPLE": "person",
    "ACTIVITIES": "play",
    # ... more mappings
}
```

#### 5. Grid Position Mapping

**Direct mapping** (Accent 7×16 → Bravo 10×10):
```python
If accent_row < 10 and accent_col < 10:
    bravo_row = accent_row
    bravo_col = accent_col
Else (proportional scaling):
    bravo_row = min(int(accent_row * 10 / 7), 9)
    bravo_col = min(int(accent_col * 10 / 16), 9)
```

---

## Frontend Flow

### Migration UI Workflow

1. **Upload Tab** (`#upload-content`)
   - User selects or drags `.mti` file
   - Frontend calls `/api/migration/upload` (multipart form)
   - Server parses file, stores in-memory, returns session ID
   - UI transitions to "Page Selection" tab

2. **Page Selection Tab** (`#page-selection-content`)
   - Dropdown displays all extracted Accent pages
   - User selects a page to import from
   - UI displays buttons in that page as a grid preview
   - User can select/deselect individual buttons

3. **Destination Tab** (`#destination-content`)
   - User chooses: "Create New Page" or "Add to Existing Page"
   - If new: enters page name
   - If existing: selects target page from dropdown
   - Preview shows mapping results

4. **Execute Tab** (`#execute-content`)
   - Shows final mapping summary
   - User clicks "Import" to execute migration
   - Calls `/api/migration/import-buttons`
   - Shows success/error modal

### Key JavaScript Functions

```javascript
// Upload file
async function handleFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await authenticatedFetch('/api/migration/upload', {
        method: 'POST',
        body: formData
    });
    sessionId = response.session_id;
    mtiData = response.parsed_data;
}

// Select page to import from
async function handlePageSelect(event) {
    const pageId = event.target.value;
    currentPageData = mtiData.pages[pageId];
    displayButtonGrid(currentPageData.buttons);
}

// Toggle button selection
function toggleButton(buttonIndex) {
    if (selectedButtons.has(buttonIndex)) {
        selectedButtons.delete(buttonIndex);
    } else {
        selectedButtons.add(buttonIndex);
    }
    updateButtonDisplay();
}

// Execute migration
async function executeMigration() {
    const response = await authenticatedFetch('/api/migration/import-buttons', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: sessionId,
            accent_page_id: currentPageData.page_id,
            selected_button_indices: Array.from(selectedButtons),
            destination_type: destinationType,  // 'new' or 'existing'
            destination_page_name: destinationPageName,
            create_navigation_pages: createNavPages
        })
    });
}
```

---

## API Endpoints

### 1. POST `/api/migration/upload`

**Purpose**: Upload and parse MTI file

**Request**:
```
multipart/form-data
- file: .mti binary file
```

**Response**:
```json
{
    "session_id": "uuid",
    "parsed_data": {
        "pages": {
            "0400": {
                "page_id": "0400",
                "inferred_name": "home",
                "button_count": 112,
                "buttons": [
                    {
                        "name": "hello",
                        "row": 0,
                        "col": 0,
                        "speech": "hi",
                        "functions": []
                    },
                    ...
                ]
            }
        },
        "total_pages": 5,
        "total_buttons": 450,
        "metadata_pages": { ... }
    }
}
```

**Side Effects**:
- Stores parsed data and mapper in in-memory session (expires after 24 hours)
- Logs page/button count statistics

### 2. POST `/api/migration/import-buttons`

**Purpose**: Import selected buttons to user's Bravo page

**Request**:
```json
{
    "session_id": "uuid",
    "accent_page_id": "0400",
    "selected_button_indices": [0, 1, 2, 5],
    "destination_type": "new",
    "destination_page_name": "My Imported Page",
    "create_navigation_pages": false,
    "conflict_resolutions": {
        "page_exists": "overwrite" | "ignore"
    }
}
```

**Response** (On Success):
```json
{
    "success": true,
    "page_name": "myimportedpage",
    "imported_button_count": 4,
    "navigation_pages_created": [],
    "message": "Successfully imported 4 buttons to page 'myimportedpage'"
}
```

**Response** (Conflict):
```json
{
    "status": "conflict",
    "conflicts": [
        {
            "type": "page_exists",
            "page_name": "My Imported Page",
            "is_home": false,
            "message": "Page 'My Imported Page' already exists"
        }
    ]
}
```

**Side Effects**:
- Creates or updates Bravo page in Firestore
- Saves mapped buttons to user's page collection
- Updates user's pages metadata

---

## Complete Data Flow

### Sequence Diagram

```
User (Browser)           Frontend JS          Server (server.py)              MTI Parser
   │                         │                        │                         │
   ├─ Upload .mti file ──────>│                        │                         │
   │                         │─ POST /upload ────────>│                         │
   │                         │                        ├─ Save temp file          │
   │                         │                        ├─ Call parser.parse_file()─>│
   │                         │                        │                         ├─ Decompress zlib
   │                         │                        │                         ├─ Find m-records
   │                         │                        │                         ├─ Parse buttons
   │                         │                        │<── return parsed_data ──┤
   │                         │                        ├─ Create session        │
   │                         │<── JSON response ──────│                         │
   │                         │                        │                         │
   │                           (User selects page)    │                         │
   │                           (User selects buttons) │                         │
   │                         │                        │                         │
   ├─ Click "Import" ────────>│                        │                         │
   │                         ├─ POST /import-buttons->│                         │
   │                         │                        ├─ Load session          │
   │                         │                        ├─ Filter selected buttons
   │                         │                        ├─ Apply mapper ─────────>│
   │                         │                        │                  (convert format)
   │                         │                        │<─ Mapped buttons ──────┤
   │                         │                        ├─ Load existing pages
   │                         │                        ├─ Check conflicts
   │                         │<─ Conflict response ───│  (if conflicts exist)
   │                         │                        │
   │  (resolve conflicts)    │                        │                         │
   │                         │────────────────────────>│                         │
   │                         │                        ├─ Save to Firestore    │
   │                         │<─ Success response ────│                         │
   │<─ Show success modal ───│                        │                         │
```

### Field Transformation Example

**Raw MTI Button Data**:
```
Page 0400, Sequence 19 (row 1, col 3)
Format 5 (function-based)
  name: "pick up lines"
  icon: "HELLO"
  function 0xA4 0x3A: speech "hi"
  function 0xA4 0x06: RANDOM-CHOICE(random hi)
```

**After Parser Post-Processing**:
```python
{
    "page_id": "0400",
    "sequence": 19,
    "row": 1,
    "col": 3,
    "name": "pick up lines",
    "icon": "HELLO",
    "speech": "hi",
    "functions": ["RANDOM-CHOICE(random hi)"],
    "navigation_type": None,
    "navigation_target": None
}
```

**After Data Mapper (with session context)**:
```python
{
    "row": 1,
    "col": 3,
    "text": "pick up lines",
    "speechPhrase": "{RANDOM:hi|hello|hey}",  # (resolved by looking up "random hi" page)
    "targetPage": "",
    "navigationType": "",
    "LLMQuery": "",
    "queryType": "options",
    "hidden": false
}
```

**Saved to Firestore**:
```
users/{uid}/pages/{page_name}/buttons/[
    {
        "row": 1,
        "col": 3,
        "text": "pick up lines",
        "speechPhrase": "{RANDOM:hi|hello|hey}",
        "targetPage": "",
        "navigationType": "",
        "LLMQuery": "",
        "queryType": "options",
        "hidden": false
    }
]
```

---

## Session Management

### In-Memory Session Storage

Parsed MTI data is stored temporarily in memory during the migration:

```python
migration_sessions = {
    "session_uuid": {
        "account_id": "user_account_id",
        "aac_user_id": "user_id",
        "timestamp": time.time(),
        "parsed_data": { ... MTI parse output ... },
        "mapper": AccentToBravoMapper(...)
    }
}
```

### Session Lifecycle

1. **Created**: When user uploads MTI file → `/api/migration/upload`
2. **Active**: 24 hours (configurable)
3. **Used**: When importing buttons → `/api/migration/import-buttons`
4. **Expired**: Automatically cleaned up after timeout

### Cleanup Strategy

```python
def cleanup_expired_sessions():
    current_time = time.time()
    expired = [
        sid for sid, session in migration_sessions.items() 
        if current_time - session['timestamp'] > SESSION_TIMEOUT
    ]
    for sid in expired:
        del migration_sessions[sid]
    
# Run cleanup:
scheduler.add_job(cleanup_expired_sessions, 'interval', hours=1)
```

---

## Error Handling

### Common Errors and Handling

| Error | Cause | Resolution |
|-------|-------|-----------|
| Invalid file format | Not a valid MTI file | Prompt user to select correct file |
| Zlib decompression failed | Corrupted file | Inform user file may be corrupted |
| No pages found | Empty MTI or parser error | Inform user no data found, check file |
| Page already exists | Destination page name in use | Show conflict resolution options |
| Parsing error | Unexpected binary format | Log error, show generic error message |
| Upload timeout | File too large | Increase timeout or limit file size |
| Session expired | User took too long | Restart migration from upload |

### Validation

**File Validation**:
```python
def validate_mti_file(file_path: str) -> bool:
    # Check file extension
    if not file_path.lower().endswith('.mti'):
        raise ValueError("File must be .mti format")
    
    # Check file size (max 50 MB)
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > 50:
        raise ValueError(f"File too large: {size_mb}MB (max 50MB)")
    
    # Check magic bytes
    with open(file_path, 'rb') as f:
        header = f.read(10)
        if not (b'MTI' in header or b'x\x9c' in header):
            raise ValueError("File does not appear to be valid MTI format")
    
    return True
```

---

## Performance Considerations

### Optimization Strategies

1. **Streaming Parse**: Don't load entire file into memory
   - Read in chunks, process m-records incrementally

2. **Caching**: Cache frequently parsed files (by hash)
   - Avoid re-parsing same MTI multiple times

3. **Lazy Mapping**: Don't map all buttons immediately
   - Only map selected buttons during import

4. **Batch Save**: Batch button inserts to Firestore
   - Use batch writes instead of individual writes

### Known Bottlenecks

- **Zlib Decompression**: Large files (>10MB) may take 1-2 seconds
- **Firestore Writes**: Each button is a separate document write (optimize with batch)
- **RANDOM-CHOICE Resolution**: Must load target page to extract options (consider caching)

---

## Testing and Debugging

### Logging

Enable debug logging in parser:
```python
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Example logs:
# "Extracted 112 buttons from 1 page"
# "Format 5 detected: picked up lines (icon: HELLO)"
# "GOTO-HOME function detected on page 0400, button home"
```

### Manual Testing

```bash
# Parse a specific MTI file
python3
>>> from accent_mti_parser import AccentMTIParser
>>> parser = AccentMTIParser()
>>> result = parser.parse_file('/path/to/test.mti')
>>> print(f"Pages: {result['total_pages']}, Buttons: {result['total_buttons']}")
>>> for page_id, page in result['pages'].items():
>>>     print(f"  {page_id}: {page['button_count']} buttons")

# Inspect raw bytes
hexdump -C test.mti | head -100
```

### Debug Endpoints

Add debug endpoints to server for inspection:

```python
@app.get("/api/migration/session/{session_id}")
async def inspect_session(session_id: str):
    if session_id not in migration_sessions:
        raise HTTPException(status_code=404)
    session = migration_sessions[session_id]
    return {
        "pages_count": len(session['parsed_data']['pages']),
        "pages": list(session['parsed_data']['pages'].keys()),
        "created_ago_seconds": time.time() - session['timestamp']
    }
```

---

## Appendix: Example MTI Parsing Walkthrough

### Raw MTI Data Example

```hex
4D 54 49 31    "MTI1" (header)
...
78 9C          zlib magic bytes
(compressed data...)
```

### After Decompression

```hex
6D 00 04 FD    "m" record marker
04 00          Page ID (swapped: 0x0400)
13             Sequence 19 (row 1, col 3)
FF CC          Format indicator (Format 5)
00 00 00       Padding
10             Name length (16 bytes)
70 69 63 6B 20...   "pick up lines"
01             Icon length (1 byte)
48             "H" (first letter of icon, followed by rest)
...
A4 3A          Speech marker (0xA4, type 0x3A)
68 69          "hi"
A4 06          RANDOM-CHOICE marker
28 72 61 6E 64 6F 6D 20 68 69 29    "(random hi)"
0D 0A          CRLF (end of record)
```

### Parsed Output

```json
{
    "page_id": "0400",
    "sequence": 19,
    "row": 1,
    "col": 3,
    "name": "pick up lines",
    "icon": "HELLO",
    "speech": "hi",
    "functions": ["RANDOM-CHOICE(random hi)"],
    "navigation_type": null,
    "navigation_target": null
}
```

### Mapped Output

```json
{
    "row": 1,
    "col": 3,
    "text": "pick up lines",
    "speechPhrase": "{RANDOM:hi|hello|hey}",
    "targetPage": "",
    "navigationType": "",
    "LLMQuery": "",
    "queryType": "options",
    "hidden": false
}
```

---

## Summary

The Bravo MTI migration process provides a comprehensive way to import Accent device configurations. The process:

1. **Parses** complex binary MTI files with 5 different button formats
2. **Sanitizes** text and extracts control markers and functions
3. **Maps** Accent data structures precisely to Bravo format
4. **Handles** conflicts and validation gracefully
5. **Persists** imported data to user's Firestore collection

Understanding this process is key to debugging migration issues, extending support for new Accent features, or migrating from other AAC devices.
