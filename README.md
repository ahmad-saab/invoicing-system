# Invoice Parser System v4.0

A modern invoice parsing system with unstructured.io integration for superior PDF extraction and customer-defined field mappings.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Start the API Server
```bash
python api_server.py
```
API available at: `http://localhost:8001`

### 3. Start the Frontend (Optional)
```bash
cd frontend
npm install  # First time only
npm start
```
Frontend available at: `http://localhost:3000`

## ✨ Features

- ✅ **Universal PDF Extraction**: Works with any invoice format using unstructured.io
- ✅ **Smart Field Mapping**: Users define what parsed text means through simple UI
- ✅ **No Complex Patterns**: Database-driven mappings instead of hardcoded regex
- ✅ **Customer Management**: Complete customer database with pricing and mappings
- ✅ **React Frontend**: Modern web interface for configuration and testing
- ✅ **Multi-language Support**: Handles English and Arabic documents
- ✅ **Confidence Scoring**: Quality metrics for extracted data
- ✅ **Audit Trail**: Complete parsing history with extraction metrics

## 📁 Project Structure

```
├── api_server.py                    # FastAPI server with all endpoints
├── mapping_parser.py                # Legacy parser with customer mappings
├── simple_extractor.py              # Simple universal data extractor
├── unstructured_mapping_parser.py   # New unstructured.io based parser
├── frontend/                        # React frontend application
├── test lpos/                       # Sample PDF files for testing
├── test_customers.db                # SQLite database with all data
├── venv/                           # Python virtual environment
└── unstructured/                   # Unstructured.io research tools
```

## 🔌 API Endpoints

### Parsing
- `POST /api/parse` - Parse with simple extractor
- `POST /api/parse/mapped` - Parse with legacy mapping parser
- `POST /api/parse/unstructured` - Parse with unstructured.io (recommended)

### Customer Management
- `GET /api/customers` - List all customers
- `GET /api/customers/{id}` - Get specific customer
- `POST /api/customers` - Add new customer
- `PUT /api/customers/{id}` - Update customer

### Field Mappings
- `GET /api/customers/{id}/mappings` - Get customer mappings
- `POST /api/customers/{id}/mappings` - Add new mapping
- `DELETE /api/customers/mappings/{id}` - Delete mapping

### Utility Files (Optional)
- `client_matcher.py` - Customer matching utilities
- `email_processor.py` - Email processing tools  
- `excel_importer.py` - Excel import functionality
- `lpo_parser.py` - Purchase order parsing
- `workflow_orchestrator.py` - Workflow automation
- `venv/` - Python virtual environment

## 💾 Database Schema

The system uses a comprehensive SQLite database with 5 normalized tables:

### 1. **Customers Table** - Main customer information
- Business details (email, TRN, chain name)
- Geographic info (place of supply, currency)
- Product mapping (customer names → standard names)
- Pricing & VAT configuration
- Invoice processing rules

### 2. **Contacts Table** - Customer contact persons
- Contact information linked to customers
- Email addresses for LPO matching
- Active/inactive status management

### 3. **Addresses Table** - Delivery addresses
- Multiple addresses per customer
- Address aliases and full addresses
- Used for LPO delivery matching

### 4. **Holidays Table** - Holiday calendar management
- UAE national holidays pre-loaded
- Custom company holidays
- Business day calculations

### 5. **LPO Config Table** - LPO processing configuration
- Customer-specific parsing rules
- LPO number extraction patterns
- Invoice reference formatting

## 🔧 Troubleshooting

### GUI Won't Start
- **Windows**: Install Python from python.org
- **Linux/WSL**: Install tkinter: `sudo apt-get install python3-tk`
- **macOS**: Use homebrew: `brew install python-tk`

### Missing Dependencies
The app uses only Python standard library modules, so no external dependencies are required for basic functionality.

## 🚀 From Web to Desktop

This application was converted from a FastAPI web application to a desktop GUI for:
- ✅ Better offline functionality
- ✅ Simpler deployment (no server setup)
- ✅ Local data storage
- ✅ Native desktop experience

## 📈 Future Enhancements

Potential additions:
- PDF invoice generation
- CSV/Excel export
- Email integration  
- Invoice templates
- Reporting dashboard
- Multi-currency support

---

**Ready to start?** Double-click `start_invoice_gui.bat` or run `python run_gui.py`!