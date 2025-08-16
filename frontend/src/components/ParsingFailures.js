import React, { useState, useEffect } from 'react';
import {
  ExclamationTriangleIcon,
  XCircleIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ClipboardDocumentListIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline';
import api from '../services/api';
import { toast } from 'react-toastify';

const ParsingFailures = () => {
  const [failures, setFailures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [filter, setFilter] = useState('all'); // all, no_extraction, unmapped_products, parse_error

  useEffect(() => {
    fetchFailures();
    // Refresh every 30 seconds
    const interval = setInterval(fetchFailures, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchFailures = async () => {
    try {
      const response = await api.get('/api/parsing-failures');
      setFailures(response.data.data || []);
    } catch (error) {
      console.error('Error fetching failures:', error);
      toast.error('Failed to fetch parsing failures');
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (failureId, notes = '') => {
    try {
      await api.post(`/api/parsing-failures/${failureId}/resolve`, { resolution_notes: notes });
      toast.success('Failure marked as resolved');
      fetchFailures();
    } catch (error) {
      console.error('Error resolving failure:', error);
      toast.error('Failed to resolve failure');
    }
  };

  const toggleExpand = (id) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getErrorTypeIcon = (errorType) => {
    switch (errorType) {
      case 'no_extraction':
        return <XCircleIcon className="h-5 w-5 text-red-600" />;
      case 'unmapped_products':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600" />;
      default:
        return <DocumentTextIcon className="h-5 w-5 text-gray-600" />;
    }
  };

  const getErrorTypeLabel = (errorType) => {
    switch (errorType) {
      case 'no_extraction':
        return 'No Products Extracted';
      case 'unmapped_products':
        return 'Unmapped Products';
      case 'parse_error':
        return 'Parse Error';
      default:
        return errorType;
    }
  };

  const filteredFailures = failures.filter(failure => {
    if (filter === 'all') return true;
    return failure.error_type === filter;
  });

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Parsing Failures</h1>
        <p className="text-gray-600 mt-2">
          Monitor and resolve failed parsing attempts with detailed debug information
        </p>
      </div>

      {/* Statistics Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Failures</p>
              <p className="text-2xl font-bold text-gray-900">{failures.length}</p>
            </div>
            <DocumentTextIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">No Extraction</p>
              <p className="text-2xl font-bold text-red-600">
                {failures.filter(f => f.error_type === 'no_extraction').length}
              </p>
            </div>
            <XCircleIcon className="h-8 w-8 text-red-400" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Unmapped Products</p>
              <p className="text-2xl font-bold text-yellow-600">
                {failures.filter(f => f.error_type === 'unmapped_products').length}
              </p>
            </div>
            <ExclamationTriangleIcon className="h-8 w-8 text-yellow-400" />
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Parse Errors</p>
              <p className="text-2xl font-bold text-gray-600">
                {failures.filter(f => f.error_type === 'parse_error').length}
              </p>
            </div>
            <DocumentTextIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Filter by type:</span>
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1 rounded text-sm ${
                filter === 'all' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All ({failures.length})
            </button>
            <button
              onClick={() => setFilter('no_extraction')}
              className={`px-3 py-1 rounded text-sm ${
                filter === 'no_extraction' 
                  ? 'bg-red-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              No Extraction
            </button>
            <button
              onClick={() => setFilter('unmapped_products')}
              className={`px-3 py-1 rounded text-sm ${
                filter === 'unmapped_products' 
                  ? 'bg-yellow-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Unmapped
            </button>
            <button
              onClick={() => setFilter('parse_error')}
              className={`px-3 py-1 rounded text-sm ${
                filter === 'parse_error' 
                  ? 'bg-gray-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Parse Error
            </button>
          </div>
        </div>
      </div>

      {/* Failures List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {filteredFailures.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <CheckCircleIcon className="h-12 w-12 mx-auto mb-4 text-green-500" />
            <p className="text-lg">No parsing failures to display</p>
            <p className="text-sm mt-2">All documents are parsing successfully!</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredFailures.map((failure) => (
              <div key={failure.id} className="hover:bg-gray-50">
                {/* Main Row */}
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      <button
                        onClick={() => toggleExpand(failure.id)}
                        className="mt-1"
                      >
                        {expandedRows.has(failure.id) ? (
                          <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                        ) : (
                          <ChevronRightIcon className="h-5 w-5 text-gray-400" />
                        )}
                      </button>
                      
                      <div className="mt-1">
                        {getErrorTypeIcon(failure.error_type)}
                      </div>
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-gray-900">
                            {failure.filename}
                          </p>
                          <span className={`px-2 py-0.5 text-xs rounded ${
                            failure.error_type === 'no_extraction' 
                              ? 'bg-red-100 text-red-800'
                              : failure.error_type === 'unmapped_products'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {getErrorTypeLabel(failure.error_type)}
                          </span>
                        </div>
                        
                        <p className="text-sm text-gray-600 mt-1">
                          {failure.customer_name || failure.customer_email || 'Unknown Customer'}
                        </p>
                        
                        <p className="text-sm text-red-600 mt-1">
                          {failure.error_message}
                        </p>
                        
                        {failure.unmapped_products && failure.unmapped_products.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs text-gray-500">Unmapped products:</p>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {failure.unmapped_products.map((product, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-yellow-50 text-yellow-700 text-xs rounded">
                                  {product}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="text-right ml-4">
                      <p className="text-xs text-gray-500">
                        {formatDate(failure.created_at)}
                      </p>
                      <button
                        onClick={() => {
                          const notes = prompt('Resolution notes (optional):');
                          if (notes !== null) {
                            handleResolve(failure.id, notes);
                          }
                        }}
                        className="mt-2 px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                      >
                        Mark Resolved
                      </button>
                    </div>
                  </div>
                </div>
                
                {/* Expanded Debug Info */}
                {expandedRows.has(failure.id) && (
                  <div className="px-4 pb-4 bg-gray-50 border-t">
                    <div className="mt-4 space-y-4">
                      {/* Debug Info */}
                      {failure.debug_info && (
                        <div>
                          <h4 className="font-medium text-sm text-gray-700 mb-2">Debug Information:</h4>
                          <div className="bg-white p-3 rounded border text-xs">
                            {typeof failure.debug_info === 'object' ? (
                              <div className="space-y-1">
                                {Object.entries(failure.debug_info).map(([key, value]) => (
                                  <div key={key}>
                                    <span className="font-medium">{key}:</span> {
                                      typeof value === 'object' 
                                        ? JSON.stringify(value, null, 2)
                                        : String(value)
                                    }
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <pre>{failure.debug_info}</pre>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {/* Extracted Text Preview */}
                      {failure.extracted_text && (
                        <div>
                          <h4 className="font-medium text-sm text-gray-700 mb-2">Extracted Text Preview:</h4>
                          <div className="bg-white p-3 rounded border">
                            <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                              {failure.extracted_text}
                            </pre>
                          </div>
                        </div>
                      )}
                      
                      {/* Action Buttons */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            // Navigate to product mappings for this customer
                            if (failure.customer_email) {
                              window.location.href = `/product-mappings?customer=${failure.customer_email}`;
                            }
                          }}
                          disabled={!failure.customer_email}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                        >
                          Configure Product Mappings
                        </button>
                        <button
                          onClick={() => {
                            // Re-parse the document
                            toast.info('Re-parsing functionality coming soon');
                          }}
                          className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
                        >
                          Re-parse Document
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">Understanding Parsing Failures:</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>No Extraction:</strong> The system couldn't find any products in the document</li>
          <li>• <strong>Unmapped Products:</strong> Products were found but aren't in the customer's mappings</li>
          <li>• <strong>Parse Error:</strong> Document structure couldn't be processed</li>
          <li>• Click the arrow to expand and see detailed debug information</li>
          <li>• Use "Configure Product Mappings" to add missing product mappings</li>
        </ul>
      </div>
    </div>
  );
};

export default ParsingFailures;