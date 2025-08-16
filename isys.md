# Invoice Processing System Documentation

## Application Launch and Configuration

### How to Start the Application

The application uses a startup script that launches both frontend and backend:

```bash
./start_app.sh
```

This script:
1. Starts the FastAPI backend on port 8001
2. Starts the React frontend on port 3001
3. Both services run concurrently in the background

### API Configuration

**Backend API Server:**
- URL: `http://localhost:8001`
- Framework: FastAPI
- Main file: `api_server.py`

**Frontend Application:**
- URL: `http://localhost:3001` 
- Framework: React
- API Base URL (hardcoded): `http://localhost:8001`
- Configuration file: `frontend/src/services/api.js`

### Database Configuration

- Database: SQLite
- File: `test_customers.db` (hardcoded path)
- Location: Root directory of the application

### Email Configuration

**Email Server Settings (Working Configuration):**
- Server: `mail.atrade.ae`
- Port: `993`
- SSL: Enabled
- Protocol: IMAP
- Authentication: Username/Password

**API Endpoints for Email:**
- GET `/api/email-config` - Retrieve email configurations
- POST `/api/email-config` - Save email configuration  
- POST `/api/email-config/test` - Test email connection

### Document Processing

**Supported Formats:**
- PDF documents
- Excel files (.xlsx, .xls)
- HTML files (.html, .htm)
- Images (.png, .jpg, .jpeg, .gif, .bmp, .tiff)
- Text files (.txt)
- Email bodies (saved as HTML/TXT)
- Word documents (.docx, .doc)
- CSV, JSON, XML files

**Parser:** 
- Uses unstructured.io library for universal document parsing
- Main parser file: `simple_parser.py`
- Class: `SimpleParserUnstructured`

### File Paths and Structure

```
/home/ahmad/Downloads/invoice.atrade.ae/
├── api_server.py              # Main API server
├── start_app.sh              # Application launcher script
├── test_customers.db         # SQLite database
├── simple_parser.py          # Document parser
├── email_manager.py          # Email processing
├── frontend/
│   ├── src/
│   │   ├── services/api.js   # API configuration
│   │   └── components/EmailConfig.js  # Email settings UI
│   └── package.json
├── temp/                     # Temporary file storage
└── exports/                  # Generated export files
```

### Current Working Status

✅ **Email Connection:** Successfully connects to mail.atrade.ae:993
✅ **Document Parsing:** Supports all major formats via unstructured.io
✅ **Database:** SQLite database operational with all required tables
✅ **API Server:** FastAPI running on port 8001
✅ **Frontend:** React app running on port 3001 with password visibility toggle
✅ **Multi-format Processing:** Email bodies saved and parsed when no attachments present

### Key Features Implemented

1. **Universal Document Parser:** Uses unstructured.io to parse ANY document format
2. **Email Body Fallback:** When no attachments, saves email body as HTML/TXT for parsing
3. **JSON-based Product Matching:** Reverse-engineers parsing to catch all products
4. **Password Visibility Toggle:** Eye icon in email configuration for password field
5. **Automatic Email Format Testing:** Tries both full email and username-only formats
6. **Multi-location Customer Support:** Branch detection and routing
7. **Comprehensive Error Logging:** Detailed logs for troubleshooting

### Startup Verification

When application starts successfully, you should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

Email connection test should show:
```
INFO:email_manager:Successfully connected to mail.atrade.ae as [username]
```