import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { toast } from 'react-toastify';
import { 
  DocumentArrowUpIcon, 
  CheckCircleIcon, 
  XCircleIcon,
  InformationCircleIcon,
  DocumentTextIcon,
  BuildingStorefrontIcon,
  CurrencyDollarIcon,
  CalendarIcon,
  TagIcon,
  MapPinIcon,
  ClipboardDocumentListIcon
} from '@heroicons/react/24/outline';

function ParseTester() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [useUnstructured, setUseUnstructured] = useState(true); // Default to new parser
  const [invoiceData, setInvoiceData] = useState({
    // Zoho Required Fields
    customer_name: '',
    invoice_number: '', // Always empty - Zoho will generate this
    invoice_date: new Date().toISOString().split('T')[0],
    due_date: '',
    purchase_order_number: '',
    place_of_supply: 'Dubai',
    payment_days: 30,
    
    // Financial Details
    subtotal: 0,
    tax_total: 0,
    discount: 0,
    total: 0,
    
    // Items
    line_items: []
  });

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await api.get('/api/customers');
      setCustomers(response.data.data || []);
    } catch (error) {
      console.error('Failed to fetch customers:', error);
    }
  };

  const calculateDueDate = (invoiceDate, paymentDays = 30) => {
    // Calculate due date: End of invoice month + payment days
    const date = new Date(invoiceDate);
    // Get last day of the month
    const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
    // Add payment days
    lastDay.setDate(lastDay.getDate() + paymentDays);
    return lastDay.toISOString().split('T')[0];
  };

  useEffect(() => {
    // Auto-calculate due date when invoice date or payment days change
    if (invoiceData.invoice_date) {
      const dueDate = calculateDueDate(invoiceData.invoice_date, invoiceData.payment_days);
      setInvoiceData(prev => ({ ...prev, due_date: dueDate }));
    }
  }, [invoiceData.invoice_date, invoiceData.payment_days]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setResult(null);
  };

  const handleParse = async () => {
    if (!file) {
      toast.error('Please select a file');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    if (selectedCustomer) {
      formData.append('customer_id', selectedCustomer);
    }

    try {
      // Use unstructured or legacy parser based on toggle
      const endpoint = useUnstructured ? '/api/parse/unstructured' : '/api/parse/mapped';
      const response = await api.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const data = response.data.data;
      setResult(data);
      
      // Auto-fill form with parsed data
      const customer = customers.find(c => c.customer_id === data.customer_id);
      
      // Get payment days from customer settings or mappings
      let paymentDays = 30;
      if (customer?.payment_term) {
        const days = parseInt(customer.payment_term.match(/\d+/)?.[0] || '30');
        paymentDays = days;
      }
      
      setInvoiceData(prev => ({
        ...prev,
        customer_name: customer?.chain_alias || customer?.customer_id || data.customer_id || '',
        place_of_supply: customer?.place_of_supply || 'Dubai',
        payment_days: paymentDays,
        line_items: data.items || [],
        subtotal: calculateSubtotal(data.items || []),
        tax_total: calculateTax(data.items || []),
        total: calculateTotal(data.items || [])
      }));
      
      if (data.customer_id) {
        setSelectedCustomer(data.customer_id);
      }
      
      toast.success('File parsed successfully');
    } catch (error) {
      toast.error('Failed to parse file');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const calculateSubtotal = (items) => {
    return items.reduce((sum, item) => {
      const qty = parseFloat(item.quantity) || 0;
      const price = parseFloat(item.price) || 0;
      return sum + (qty * price);
    }, 0);
  };

  const calculateTax = (items) => {
    const subtotal = calculateSubtotal(items);
    return subtotal * 0.05; // 5% VAT
  };

  const calculateTotal = (items) => {
    return calculateSubtotal(items) + calculateTax(items);
  };

  const handleSubmitToZoho = async () => {
    // Validate required fields (invoice_number excluded as it's auto-generated)
    if (!invoiceData.customer_name) {
      toast.error('Please select or enter a customer name');
      return;
    }

    try {
      // This would submit to Zoho API
      console.log('Submitting to Zoho:', invoiceData);
      toast.success('Invoice data prepared for Zoho submission');
    } catch (error) {
      toast.error('Failed to submit to Zoho');
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Invoice Parser & Matcher</h1>
        <p className="text-gray-600 mt-2">Parse PDF invoices and match data for Zoho Books integration</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - File Upload & Customer Selection */}
        <div className="lg:col-span-1 space-y-4">
          {/* Customer Selector */}
          <div className="bg-white shadow rounded-lg p-4">
            <h3 className="font-semibold text-lg mb-3 flex items-center">
              <BuildingStorefrontIcon className="h-5 w-5 mr-2" />
              Customer Selection
            </h3>
            <select
              value={selectedCustomer}
              onChange={(e) => setSelectedCustomer(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Auto-detect from PDF</option>
              {customers.map(customer => (
                <option key={customer.customer_id} value={customer.customer_id}>
                  {customer.chain_alias || customer.customer_id}
                </option>
              ))}
            </select>
          </div>
          {/* File Upload */}
          <div className="bg-white shadow rounded-lg p-4">
            <h3 className="font-semibold text-lg mb-3 flex items-center">
              <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
              Upload Invoice
            </h3>
            
            {/* Parser Selection Toggle */}
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm font-medium text-gray-700">
                  Use Unstructured.io Parser (Recommended)
                </span>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={useUnstructured}
                    onChange={(e) => setUseUnstructured(e.target.checked)}
                    className="sr-only"
                  />
                  <div className={`block w-14 h-8 rounded-full ${useUnstructured ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                  <div className={`absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition-transform ${useUnstructured ? 'transform translate-x-6' : ''}`}></div>
                </div>
              </label>
              <p className="mt-1 text-xs text-gray-500">
                {useUnstructured 
                  ? "Using advanced Unstructured.io parser with better table detection" 
                  : "Using legacy pdfplumber parser"}
              </p>
            </div>
            
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
              <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="mt-4"
                id="file-upload"
              />
              {file && (
                <p className="mt-2 text-sm text-gray-600">
                  📄 {file.name}
                </p>
              )}
            </div>
            <button
              onClick={handleParse}
              disabled={!file || loading}
              className="mt-4 w-full bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 disabled:bg-gray-300 transition-colors"
            >
              {loading ? 'Parsing...' : 'Parse & Extract Data'}
            </button>
          </div>

          {/* Parse Status */}
          {result && (
            <div className="bg-white shadow rounded-lg p-4">
              <h3 className="font-semibold text-lg mb-3">Parse Status</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Customer Match</span>
                  {result.customer_id ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-red-500" />
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Items Extracted</span>
                  <span className="font-semibold">{result.items?.length || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Mappings Used</span>
                  <span className="font-semibold">{result.mappings_used || 0}</span>
                </div>
                {result.extraction_method && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Extraction Method</span>
                    <span className="font-semibold capitalize">{result.extraction_method}</span>
                  </div>
                )}
                {result.extraction_quality && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Quality Score</span>
                    <span className="font-semibold">{result.extraction_quality.overall_score}%</span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-sm">Unmapped Lines</span>
                  <span className="font-semibold text-orange-600">{result.unmapped_count || 0}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Invoice Form */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
              <ClipboardDocumentListIcon className="h-6 w-6 mr-2" />
              Invoice Data Form
            </h2>

            {/* Invoice Details Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              {/* Customer Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Customer Name *
                </label>
                <input
                  type="text"
                  value={invoiceData.customer_name}
                  onChange={(e) => setInvoiceData({...invoiceData, customer_name: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter customer name"
                />
              </div>

              {/* Invoice Number */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Invoice Number
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value=""
                    disabled
                    className="w-full px-3 py-2 border rounded-lg bg-gray-100 text-gray-500 cursor-not-allowed"
                    placeholder="Auto-generated by Zoho"
                  />
                  <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">AUTO</span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">Zoho Books will generate the invoice number</p>
              </div>

              {/* Invoice Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Invoice Date *
                </label>
                <input
                  type="date"
                  value={invoiceData.invoice_date}
                  onChange={(e) => setInvoiceData({...invoiceData, invoice_date: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Due Date with Payment Terms */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Due Date (Auto-calculated)
                </label>
                <div className="flex gap-2">
                  <input
                    type="date"
                    value={invoiceData.due_date}
                    onChange={(e) => setInvoiceData({...invoiceData, due_date: e.target.value})}
                    className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                    readOnly
                  />
                  <div className="flex items-center gap-2 px-3 py-2 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <span className="text-sm text-gray-700">SOA +</span>
                    <input
                      type="number"
                      value={invoiceData.payment_days}
                      onChange={(e) => setInvoiceData({...invoiceData, payment_days: parseInt(e.target.value) || 0})}
                      className="w-16 px-2 py-1 border rounded text-center"
                      min="0"
                      max="365"
                    />
                    <span className="text-sm text-gray-700">days</span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Due date = End of {new Date(invoiceData.invoice_date).toLocaleDateString('en-US', { month: 'short' })} + {invoiceData.payment_days} days
                </p>
              </div>

              {/* Purchase Order Number */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Purchase Order Number
                </label>
                <input
                  type="text"
                  value={invoiceData.purchase_order_number}
                  onChange={(e) => setInvoiceData({...invoiceData, purchase_order_number: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="PO-12345"
                />
              </div>

              {/* Place of Supply */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Place of Supply *
                </label>
                <input
                  type="text"
                  value={invoiceData.place_of_supply}
                  onChange={(e) => setInvoiceData({...invoiceData, place_of_supply: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Dubai"
                />
              </div>
            </div>

            {/* Line Items Table */}
            <div className="mb-6">
              <h3 className="font-semibold text-lg mb-3 flex items-center">
                <TagIcon className="h-5 w-5 mr-2" />
                Line Items
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="border px-4 py-2 text-left">Product</th>
                      <th className="border px-4 py-2 text-center">Quantity</th>
                      <th className="border px-4 py-2 text-center">Unit</th>
                      <th className="border px-4 py-2 text-right">Price</th>
                      <th className="border px-4 py-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoiceData.line_items.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="border px-4 py-8 text-center text-gray-500">
                          No items yet. Parse a PDF to extract line items.
                        </td>
                      </tr>
                    ) : (
                      invoiceData.line_items.map((item, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="border px-4 py-2">
                            <input
                              type="text"
                              value={item.product || ''}
                              onChange={(e) => {
                                const updated = [...invoiceData.line_items];
                                updated[idx] = {...updated[idx], product: e.target.value};
                                setInvoiceData({...invoiceData, line_items: updated});
                              }}
                              className="w-full px-2 py-1 border-0 focus:ring-1 focus:ring-blue-500"
                            />
                          </td>
                          <td className="border px-4 py-2">
                            <input
                              type="number"
                              value={item.quantity || ''}
                              onChange={(e) => {
                                const updated = [...invoiceData.line_items];
                                updated[idx] = {...updated[idx], quantity: e.target.value};
                                setInvoiceData({
                                  ...invoiceData, 
                                  line_items: updated,
                                  subtotal: calculateSubtotal(updated),
                                  tax_total: calculateTax(updated),
                                  total: calculateTotal(updated)
                                });
                              }}
                              className="w-full px-2 py-1 border-0 focus:ring-1 focus:ring-blue-500 text-center"
                            />
                          </td>
                          <td className="border px-4 py-2">
                            <input
                              type="text"
                              value={item.unit || ''}
                              onChange={(e) => {
                                const updated = [...invoiceData.line_items];
                                updated[idx] = {...updated[idx], unit: e.target.value};
                                setInvoiceData({...invoiceData, line_items: updated});
                              }}
                              className="w-full px-2 py-1 border-0 focus:ring-1 focus:ring-blue-500 text-center"
                            />
                          </td>
                          <td className="border px-4 py-2">
                            <input
                              type="number"
                              value={item.price || ''}
                              step="0.01"
                              onChange={(e) => {
                                const updated = [...invoiceData.line_items];
                                updated[idx] = {...updated[idx], price: e.target.value};
                                setInvoiceData({
                                  ...invoiceData, 
                                  line_items: updated,
                                  subtotal: calculateSubtotal(updated),
                                  tax_total: calculateTax(updated),
                                  total: calculateTotal(updated)
                                });
                              }}
                              className="w-full px-2 py-1 border-0 focus:ring-1 focus:ring-blue-500 text-right"
                            />
                          </td>
                          <td className="border px-4 py-2 text-right font-semibold">
                            AED {((parseFloat(item.quantity) || 0) * (parseFloat(item.price) || 0)).toFixed(2)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Totals */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex justify-end">
                <div className="w-64 space-y-2">
                  <div className="flex justify-between">
                    <span>Subtotal:</span>
                    <span className="font-semibold">AED {invoiceData.subtotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>VAT (5%):</span>
                    <span className="font-semibold">AED {invoiceData.tax_total.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold border-t pt-2">
                    <span>Total:</span>
                    <span>AED {invoiceData.total.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex justify-end space-x-4">
              <button
                onClick={() => {
                  setInvoiceData({
                    customer_name: '',
                    invoice_number: '', // Always empty for Zoho
                    invoice_date: new Date().toISOString().split('T')[0],
                    due_date: '',
                    purchase_order_number: '',
                    place_of_supply: 'Dubai',
                    subtotal: 0,
                    tax_total: 0,
                    discount: 0,
                    total: 0,
                    line_items: []
                  });
                  setResult(null);
                }}
                className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Clear Form
              </button>
              <button
                onClick={handleSubmitToZoho}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center"
              >
                <CheckCircleIcon className="h-5 w-5 mr-2" />
                Submit to Zoho Books
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Unmapped Data Alert */}
      {result && result.parsed_data?.unmapped_text && result.parsed_data.unmapped_text.length > 0 && (
        <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start">
            <InformationCircleIcon className="h-5 w-5 text-amber-600 mt-0.5 mr-2 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-amber-900">Unmapped Text Found</h4>
              <p className="text-sm text-amber-700 mt-1">
                {result.unmapped_count} lines couldn't be mapped. Define mappings in the Customer Manager to improve parsing.
              </p>
              <div className="mt-2 max-h-32 overflow-y-auto">
                {result.parsed_data.unmapped_text.slice(0, 3).map((item, idx) => (
                  <div key={idx} className="text-xs text-amber-600 font-mono">
                    {item.text.substring(0, 80)}...
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Debug Information Section */}
      {result && (
        <div className="mt-6 bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-sm">
          <h3 className="text-lg font-bold text-white mb-4">🐛 FULL PYTHON DEBUG OUTPUT</h3>
          
          {/* Customer Information */}
          <div className="mb-4">
            <h4 className="text-yellow-400 font-semibold">📋 CUSTOMER INFO:</h4>
            <div className="ml-4 space-y-1">
              <p>Selected Customer: <span className="text-blue-300">{selectedCustomer || 'None'}</span></p>
              <p>Detected Customer: <span className="text-blue-300">{result.customer_id || 'None'}</span></p>
              <p>Mappings Used: <span className="text-blue-300">{result.mappings_used || 0}</span></p>
            </div>
          </div>

          {/* Raw PDF Content */}
          {result.parsed_data && (
            <>
              <div className="mb-4">
                <h4 className="text-yellow-400 font-semibold">📄 EXTRACTED PRODUCTS:</h4>
                <div className="ml-4">
                  {result.parsed_data.products && result.parsed_data.products.length > 0 ? (
                    result.parsed_data.products.map((product, idx) => (
                      <div key={idx} className="border-l-2 border-green-600 pl-3 mb-2">
                        <p>Product {idx + 1}:</p>
                        <p className="ml-2">Original: <span className="text-cyan-300">"{product.original}"</span></p>
                        <p className="ml-2">Mapped to: <span className="text-green-300">"{product.mapped}"</span></p>
                      </div>
                    ))
                  ) : (
                    <p className="text-red-400 ml-4">❌ No products extracted from PDF</p>
                  )}
                </div>
              </div>

              <div className="mb-4">
                <h4 className="text-yellow-400 font-semibold">📦 FINAL ITEMS:</h4>
                <div className="ml-4">
                  {result.items && result.items.length > 0 ? (
                    result.items.map((item, idx) => (
                      <div key={idx} className="border-l-2 border-blue-600 pl-3 mb-2">
                        <p>Item {idx + 1}:</p>
                        <p className="ml-2">Product: <span className="text-cyan-300">"{item.product}"</span></p>
                        <p className="ml-2">Quantity: <span className="text-yellow-300">{item.quantity}</span></p>
                        <p className="ml-2">Price: <span className="text-yellow-300">{item.price}</span></p>
                        <p className="ml-2">Price Source: <span className={item.price_source === 'customer_pricing' ? 'text-green-300' : 'text-red-300'}>
                          {item.price_source || 'N/A'}
                        </span></p>
                        {item.currency && <p className="ml-2">Currency: <span className="text-yellow-300">{item.currency}</span></p>}
                        {item.vat_rate && <p className="ml-2">VAT Rate: <span className="text-yellow-300">{item.vat_rate}%</span></p>}
                      </div>
                    ))
                  ) : (
                    <p className="text-red-400 ml-4">❌ No items generated</p>
                  )}
                </div>
              </div>

              <div className="mb-4">
                <h4 className="text-yellow-400 font-semibold">❓ ALL UNMAPPED TEXT ({result.parsed_data.unmapped_text?.length || 0} lines):</h4>
                <div className="ml-4 max-h-60 overflow-y-auto bg-black p-2 rounded">
                  {result.parsed_data.unmapped_text && result.parsed_data.unmapped_text.length > 0 ? (
                    result.parsed_data.unmapped_text.map((item, idx) => (
                      <p key={idx} className="text-gray-300 hover:bg-gray-800 px-1">
                        <span className="text-yellow-500 mr-2">{idx + 1}.</span>
                        "{item.text}"
                      </p>
                    ))
                  ) : (
                    <p className="text-gray-500">No unmapped text</p>
                  )}
                </div>
              </div>

              {/* VAT Configuration */}
              {result.vat_config && (
                <div className="mb-4">
                  <h4 className="text-yellow-400 font-semibold">💰 VAT CONFIG:</h4>
                  <div className="ml-4 space-y-1">
                    <p>VAT Rate: <span className="text-blue-300">{result.vat_config.vat_rate}%</span></p>
                    <p>VAT Inclusive: <span className="text-blue-300">{result.vat_config.vat_inclusive ? 'Yes' : 'No'}</span></p>
                    <p>Currency: <span className="text-blue-300">{result.vat_config.default_currency}</span></p>
                  </div>
                </div>
              )}

              {/* Invoice Totals */}
              {result.invoice_totals && (
                <div className="mb-4">
                  <h4 className="text-yellow-400 font-semibold">🧾 INVOICE TOTALS:</h4>
                  <div className="ml-4 space-y-1">
                    <p>Subtotal: <span className="text-green-300">{result.invoice_totals.currency} {result.invoice_totals.subtotal?.toFixed(2)}</span></p>
                    <p>VAT Amount: <span className="text-green-300">{result.invoice_totals.currency} {result.invoice_totals.vat_amount?.toFixed(2)}</span></p>
                    <p>Grand Total: <span className="text-green-300">{result.invoice_totals.currency} {result.invoice_totals.grand_total?.toFixed(2)}</span></p>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Summary */}
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-yellow-400 font-semibold">📊 DEBUGGING SUMMARY:</h4>
            <div className="ml-4 space-y-1">
              <p className={result.customer_id ? 'text-green-300' : 'text-red-300'}>
                ✓ Customer Detection: {result.customer_id ? 'SUCCESS' : 'FAILED'}
              </p>
              <p className={result.parsed_data?.products?.length > 0 ? 'text-green-300' : 'text-red-300'}>
                ✓ Product Extraction: {result.parsed_data?.products?.length > 0 ? 'SUCCESS' : 'FAILED'}
              </p>
              <p className={result.items?.some(item => item.price_source === 'customer_pricing') ? 'text-green-300' : 'text-red-300'}>
                ✓ Custom Pricing Applied: {result.items?.some(item => item.price_source === 'customer_pricing') ? 'SUCCESS' : 'FAILED'}
              </p>
              <p className={result.mappings_used > 0 ? 'text-green-300' : 'text-red-300'}>
                ✓ Mappings Used: {result.mappings_used > 0 ? `${result.mappings_used} mappings` : 'NONE'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ParseTester;
