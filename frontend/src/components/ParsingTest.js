import React, { useState } from 'react';
import { 
  DocumentArrowUpIcon,
  MagnifyingGlassIcon,
  CheckCircleIcon,
  XCircleIcon,
  TableCellsIcon
} from '@heroicons/react/24/outline';
import api from '../services/api';
import { toast } from 'react-toastify';

const ParsingTest = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [customers, setCustomers] = useState([]);
  const [parseResult, setParseResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [addToQueue, setAddToQueue] = useState(false);

  React.useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await api.get('/api/customers');
      setCustomers(response.data.data || []);
    } catch (error) {
      console.error('Error fetching customers:', error);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      setParseResult(null);
    } else {
      toast.error('Please select a PDF file');
    }
  };

  const handleParse = async () => {
    if (!selectedFile || !selectedCustomer) {
      toast.error('Please select both a file and a customer');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('customer_email', selectedCustomer);
    formData.append('add_to_queue', addToQueue);

    try {
      const response = await api.post('/api/parse', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setParseResult(response.data);
      
      if (response.data.status === 'success') {
        if (response.data.added_to_queue) {
          toast.success(`File parsed and added to queue (ID: ${response.data.queue_id})`);
        } else {
          toast.success('File parsed successfully');
        }
      } else {
        toast.warning('Parse completed with issues');
      }
    } catch (error) {
      console.error('Parse error:', error);
      toast.error('Failed to parse file');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">LPO Parsing Test</h1>
        <p className="text-gray-600 mt-2">Test the extraction of products and quantities from LPO files</p>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Step 1: Select LPO File and Customer</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              LPO File (PDF)
            </label>
            <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
              <div className="space-y-1 text-center">
                <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                <div className="flex text-sm text-gray-600">
                  <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500">
                    <span>Upload a file</span>
                    <input
                      type="file"
                      className="sr-only"
                      accept=".pdf"
                      onChange={handleFileSelect}
                    />
                  </label>
                </div>
                {selectedFile && (
                  <p className="text-sm text-green-600 font-medium">
                    ✓ {selectedFile.name}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Customer Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Customer (Simulating email sender)
            </label>
            <select
              value={selectedCustomer}
              onChange={(e) => setSelectedCustomer(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a customer...</option>
              {customers.map((customer) => (
                <option key={customer.email} value={customer.email}>
                  {customer.customer_name} ({customer.email})
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              In production, this will come from the email sender
            </p>
          </div>
        </div>

        {/* Add to Queue Option */}
        <div className="mt-4 flex items-center">
          <input
            type="checkbox"
            id="addToQueue"
            checked={addToQueue}
            onChange={(e) => setAddToQueue(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="addToQueue" className="ml-2 block text-sm text-gray-700">
            Add to processing pipeline queue after parsing
          </label>
        </div>

        <button
          onClick={handleParse}
          disabled={!selectedFile || !selectedCustomer || loading}
          className="mt-6 w-full md:w-auto px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
        >
          <MagnifyingGlassIcon className="h-5 w-5 mr-2" />
          {loading ? 'Parsing...' : 'Parse LPO'}
        </button>
      </div>

      {/* Results Section */}
      {parseResult && (
        <div className="space-y-6">
          {/* Queue Status */}
          {parseResult.added_to_queue && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center">
              <CheckCircleIcon className="h-6 w-6 text-green-600 mr-3" />
              <div>
                <p className="text-green-800 font-medium">Added to Processing Pipeline</p>
                <p className="text-green-600 text-sm">Queue ID: #{parseResult.queue_id} - You can now export this invoice from the Pipeline page</p>
              </div>
            </div>
          )}
          
          {/* Customer Info */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Customer Information (from Database)</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Customer:</span>
                <p className="font-medium">{parseResult.customer?.customer_name}</p>
              </div>
              <div>
                <span className="text-gray-500">Email:</span>
                <p className="font-medium">{parseResult.customer?.email}</p>
              </div>
              <div>
                <span className="text-gray-500">TRN:</span>
                <p className="font-medium">{parseResult.customer?.trn}</p>
              </div>
              <div>
                <span className="text-gray-500">PO Number:</span>
                <p className="font-medium">{parseResult.po_number || 'Not found'}</p>
              </div>
            </div>
          </div>

          {/* Extracted Items */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center">
              <TableCellsIcon className="h-5 w-5 mr-2" />
              Extracted Products
            </h2>
            
            {parseResult.items && parseResult.items.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        LPO Product Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Mapped To
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Quantity
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Unit
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Unit Price
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Total
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {parseResult.items.map((item, index) => (
                      <tr key={index} className={item.needs_mapping ? 'bg-yellow-50' : ''}>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                          {item.lpo_product_name}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {item.system_product_name}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900 font-semibold">
                          {item.quantity}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {item.unit}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {item.unit_price ? `AED ${item.unit_price}` : '-'}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {item.total ? `AED ${item.total}` : '-'}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          {item.needs_mapping ? (
                            <span className="flex items-center text-yellow-600">
                              <XCircleIcon className="h-5 w-5 mr-1" />
                              Needs Mapping
                            </span>
                          ) : (
                            <span className="flex items-center text-green-600">
                              <CheckCircleIcon className="h-5 w-5 mr-1" />
                              Mapped
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No products extracted from the LPO
              </div>
            )}
          </div>

          {/* Totals */}
          {parseResult.totals && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold mb-4">Invoice Totals</h2>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <p className="text-gray-500">Subtotal</p>
                  <p className="text-xl font-semibold">AED {parseResult.totals.subtotal}</p>
                </div>
                <div className="text-center">
                  <p className="text-gray-500">VAT ({parseResult.totals.vat_rate}%)</p>
                  <p className="text-xl font-semibold">AED {parseResult.totals.vat_amount}</p>
                </div>
                <div className="text-center">
                  <p className="text-gray-500">Total</p>
                  <p className="text-xl font-semibold text-green-600">AED {parseResult.totals.total}</p>
                </div>
              </div>
            </div>
          )}

          {/* Errors */}
          {parseResult.errors && parseResult.errors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-red-800 font-semibold mb-2">Errors:</h3>
              <ul className="text-sm text-red-700 list-disc list-inside">
                {parseResult.errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Debug Information */}
          <div className="bg-gray-100 border border-gray-300 rounded-lg p-4">
            <h3 className="text-gray-800 font-semibold mb-2">Debug Information:</h3>
            <div className="space-y-2">
              {parseResult.debug_info && (
                <div className="text-sm">
                  <p className="text-gray-700">
                    <span className="font-medium">Total Elements Found:</span> {parseResult.debug_info.total_elements || 0}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-medium">Tables Found:</span> {parseResult.debug_info.tables_found || 0}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-medium">Items Extracted:</span> {parseResult.debug_info.items_extracted || 0}
                  </p>
                  {parseResult.debug_info.element_types && (
                    <div className="mt-2">
                      <span className="font-medium">Element Types:</span>
                      <ul className="ml-4 mt-1">
                        {Object.entries(parseResult.debug_info.element_types).map(([type, count]) => (
                          <li key={type} className="text-gray-600">
                            • {type}: {count}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              <details className="mt-3">
                <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-800">
                  Show Full Parse Result (JSON)
                </summary>
                <pre className="mt-2 text-xs bg-white p-3 rounded border border-gray-200 overflow-x-auto">
                  {JSON.stringify(parseResult, null, 2)}
                </pre>
              </details>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">How Extraction Works:</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• The system identifies tables in the PDF containing product information</li>
          <li>• It looks for columns with product names and quantities</li>
          <li>• Product names are matched against your configured mappings</li>
          <li>• Quantities are extracted from the quantity column</li>
          <li>• Prices come from your database, NOT the LPO</li>
          <li>• Items showing "Needs Mapping" require configuration in the customer's product mappings</li>
        </ul>
      </div>
    </div>
  );
};

export default ParsingTest;