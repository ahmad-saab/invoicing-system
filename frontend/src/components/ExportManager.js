import React, { useState, useEffect } from 'react';
import { Download, FileSpreadsheet, CheckCircle, AlertCircle, Package } from 'lucide-react';

const ExportManager = () => {
  const [parsedInvoices, setParsedInvoices] = useState([]);
  const [selectedInvoices, setSelectedInvoices] = useState([]);
  const [exportStatus, setExportStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchParsedInvoices();
  }, []);

  const fetchParsedInvoices = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/dashboard/stats');
      const result = await response.json();
      // For demo, using recent successful parses
      if (result.status === 'success' && result.data) {
        // Fetch actual parsed data from history
        // This would need a new endpoint to get full invoice data
        setParsedInvoices([]);
      }
    } catch (error) {
      console.error('Error fetching invoices:', error);
    }
  };

  const handleExportSingle = async (invoiceData) => {
    setLoading(true);
    setExportStatus(null);
    
    try {
      const response = await fetch('http://localhost:8001/api/export/zoho', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(invoiceData)
      });

      if (response.ok) {
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `zoho_invoice_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        setExportStatus({
          type: 'success',
          message: 'Invoice exported successfully!'
        });
      } else {
        const error = await response.json();
        setExportStatus({
          type: 'error',
          message: error.detail || 'Export failed'
        });
      }
    } catch (error) {
      setExportStatus({
        type: 'error',
        message: 'Failed to export invoice'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExportBatch = async () => {
    if (selectedInvoices.length === 0) {
      setExportStatus({
        type: 'warning',
        message: 'Please select invoices to export'
      });
      return;
    }

    setLoading(true);
    setExportStatus(null);
    
    try {
      const response = await fetch('http://localhost:8001/api/export/zoho/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(selectedInvoices)
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `zoho_batch_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        setExportStatus({
          type: 'success',
          message: `${selectedInvoices.length} invoices exported successfully!`
        });
        setSelectedInvoices([]);
      } else {
        const error = await response.json();
        setExportStatus({
          type: 'error',
          message: error.detail || 'Batch export failed'
        });
      }
    } catch (error) {
      setExportStatus({
        type: 'error',
        message: 'Failed to export batch'
      });
    } finally {
      setLoading(false);
    }
  };

  const testExport = async () => {
    // Test with sample data
    const testInvoice = {
      po_number: 'TEST-PO-001',
      invoice_number: `INV-${Date.now()}`,
      customer: {
        customer_name: 'Demo Company LLC',
        customer_id_number: 'CUST001',
        email: 'demo@company.com',
        trn: '100000000000003',
        billing_address: '123 Business Street, Dubai, UAE',
        shipping_address: '456 Warehouse Road, Dubai, UAE',
        payment_terms: 30,
        currency: 'AED'
      },
      items: [
        {
          lpo_product_name: 'SUNFLOWER OIL TIN 5L',
          system_product_name: 'Sunflower Oil 5L Tin',
          quantity: 10,
          unit: 'TIN',
          unit_price: 85.00,
          vat_rate: 5,
          total: 850.00
        },
        {
          lpo_product_name: 'CORN OIL BOTTLE 1L',
          system_product_name: 'Corn Oil 1L Bottle',
          quantity: 20,
          unit: 'BOTTLE',
          unit_price: 25.00,
          vat_rate: 5,
          total: 500.00
        }
      ],
      totals: {
        subtotal: 1350.00,
        vat_amount: 67.50,
        total: 1417.50
      }
    };

    await handleExportSingle(testInvoice);
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <FileSpreadsheet className="w-8 h-8 text-blue-600" />
          Export Manager - Zoho Books
        </h2>
        <p className="text-gray-600 mt-2">
          Export parsed invoices to Zoho Books compatible CSV format
        </p>
      </div>

      {/* Export Status */}
      {exportStatus && (
        <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
          exportStatus.type === 'success' ? 'bg-green-50 text-green-800' :
          exportStatus.type === 'error' ? 'bg-red-50 text-red-800' :
          'bg-yellow-50 text-yellow-800'
        }`}>
          {exportStatus.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          {exportStatus.message}
        </div>
      )}

      {/* Export Actions */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Export Options</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Test Export */}
          <div className="border rounded-lg p-4">
            <h4 className="font-medium mb-2">Test Export</h4>
            <p className="text-sm text-gray-600 mb-3">
              Export a sample invoice to test the Zoho Books integration
            </p>
            <button
              onClick={testExport}
              disabled={loading}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              {loading ? 'Exporting...' : 'Export Test Invoice'}
            </button>
          </div>

          {/* Batch Export */}
          <div className="border rounded-lg p-4">
            <h4 className="font-medium mb-2">Batch Export</h4>
            <p className="text-sm text-gray-600 mb-3">
              Export multiple invoices in a single CSV file
            </p>
            <button
              onClick={handleExportBatch}
              disabled={loading || selectedInvoices.length === 0}
              className="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Package className="w-4 h-4" />
              {loading ? 'Exporting...' : `Export ${selectedInvoices.length} Invoices`}
            </button>
          </div>
        </div>
      </div>

      {/* Zoho Fields Reference */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Zoho Books CSV Format</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Required Fields</h4>
            <ul className="space-y-1 text-sm">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Invoice Number
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Invoice Date
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Customer Name
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Item Name
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Item Quantity
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Item Rate (Price)
              </li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Optional Fields</h4>
            <ul className="space-y-1 text-sm text-gray-600">
              <li>• Due Date</li>
              <li>• Customer ID</li>
              <li>• TRN (Tax Registration Number)</li>
              <li>• Order Number (PO Number)</li>
              <li>• Payment Terms</li>
              <li>• Billing/Shipping Address</li>
              <li>• Item Unit & Tax Rate</li>
              <li>• Currency Code</li>
            </ul>
          </div>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-2">Export Features</h4>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>✓ Automatic invoice number generation</li>
            <li>✓ Due date calculation based on payment terms</li>
            <li>✓ Support for multiple items per invoice</li>
            <li>✓ Batch export for multiple invoices</li>
            <li>✓ UTF-8 encoding for international characters</li>
            <li>✓ Validation before export</li>
          </ul>
        </div>

        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-700">
            <strong>File Format:</strong> CSV (Comma-Separated Values)<br/>
            <strong>Encoding:</strong> UTF-8<br/>
            <strong>Max File Size:</strong> 10 MB (Zoho limit)<br/>
            <strong>Export Location:</strong> /exports folder
          </p>
        </div>
      </div>
    </div>
  );
};

export default ExportManager;