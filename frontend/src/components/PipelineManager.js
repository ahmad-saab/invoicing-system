import React, { useState, useEffect } from 'react';
import { PlayCircle, RefreshCw, Package, Mail, FileSpreadsheet, AlertCircle, CheckCircle, Clock } from 'lucide-react';

const PipelineManager = () => {
  const [stats, setStats] = useState(null);
  const [queue, setQueue] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [fetchingEmails, setFetchingEmails] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState(null);
  const [selectedTab, setSelectedTab] = useState('overview');
  const [exportedFiles, setExportedFiles] = useState([]);

  useEffect(() => {
    fetchStats();
    fetchQueue();
    fetchExportedFiles();
    const interval = setInterval(() => {
      fetchStats();
      fetchQueue();
      fetchExportedFiles();
    }, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/pipeline/stats');
      const result = await response.json();
      if (result.status === 'success') {
        setStats(result.data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchQueue = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/pipeline/queue?limit=20');
      const result = await response.json();
      if (result.status === 'success') {
        setQueue(result.data);
      }
    } catch (error) {
      console.error('Error fetching queue:', error);
    }
  };

  const fetchExportedFiles = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/exports');
      const result = await response.json();
      if (result.status === 'success') {
        setExportedFiles(result.data);
      }
    } catch (error) {
      console.error('Error fetching exported files:', error);
    }
  };

  const downloadFile = (filename) => {
    const link = document.createElement('a');
    link.href = `http://localhost:8001/api/exports/${filename}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const runPipeline = async () => {
    setProcessing(true);
    setMessage(null);
    
    try {
      const response = await fetch('http://localhost:8001/api/pipeline/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ fetch_emails: false, auto_export: true })
      });

      const result = await response.json();
      
      if (result.status === 'success') {
        setMessage({
          type: 'success',
          text: result.message
        });
        fetchStats();
        fetchQueue();
      } else {
        setMessage({
          type: 'error',
          text: 'Pipeline processing failed'
        });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Error running pipeline'
      });
    } finally {
      setProcessing(false);
    }
  };

  const fetchEmails = async () => {
    setFetchingEmails(true);
    setMessage(null);
    
    try {
      const response = await fetch('http://localhost:8001/api/pipeline/fetch-emails', {
        method: 'POST'
      });

      const result = await response.json();
      
      if (result.status === 'success') {
        setMessage({
          type: 'success',
          text: result.message
        });
        fetchStats();
        fetchQueue();
      } else {
        setMessage({
          type: 'error',
          text: result.data?.errors?.join(', ') || 'Failed to fetch emails'
        });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Error fetching emails'
      });
    } finally {
      setFetchingEmails(false);
    }
  };

  const exportBatch = async () => {
    setExporting(true);
    setMessage(null);
    
    try {
      // Simple approach: just call the pipeline export endpoint
      const response = await fetch('http://localhost:8001/api/pipeline/export-batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const result = await response.json();
      
      if (result.status === 'success' && result.data.export_path) {
        // Download the exported file
        const filename = result.data.export_path.split('/').pop();
        const downloadUrl = `http://localhost:8001/api/exports/${filename}`;
        
        // Create a temporary link and click it to download
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        setMessage({
          type: 'success',
          text: `Exported ${result.data.exported_count} invoice(s) successfully!`
        });
        
        // Refresh stats and queue
        fetchStats();
        fetchQueue();
        fetchExportedFiles();
      } else if (result.data.exported_count === 0) {
        setMessage({
          type: 'warning',
          text: 'No invoices ready for export'
        });
      } else {
        setMessage({
          type: 'error',
          text: result.data.errors?.join(', ') || 'Export failed'
        });
      }
    } catch (error) {
      console.error('Export error:', error);
      setMessage({
        type: 'error',
        text: 'Error exporting invoices: ' + error.message
      });
    } finally {
      setExporting(false);
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'processing':
        return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      'completed': 'bg-green-100 text-green-800',
      'processing': 'bg-blue-100 text-blue-800',
      'failed': 'bg-red-100 text-red-800',
      'pending': 'bg-yellow-100 text-yellow-800',
      'exported': 'bg-purple-100 text-purple-800'
    };
    
    return (
      <span className={`px-2 py-1 text-xs rounded-full ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <RefreshCw className="w-8 h-8 text-blue-600" />
          Invoice Processing Pipeline
        </h2>
        <p className="text-gray-600 mt-2">
          Manage the complete workflow from email to export
        </p>
      </div>

      {/* Status Message */}
      {message && (
        <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
          message.type === 'success' ? 'bg-green-50 text-green-800' :
          'bg-red-50 text-red-800'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          {message.text}
        </div>
      )}

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
            <div className="text-sm text-gray-600">Total Invoices</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
            <div className="text-sm text-gray-600">Pending</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-blue-600">
              {stats.by_status?.processing || 0}
            </div>
            <div className="text-sm text-gray-600">Processing</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
            <div className="text-sm text-gray-600">Completed</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
            <div className="text-sm text-gray-600">Failed</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-purple-600">{stats.exported}</div>
            <div className="text-sm text-gray-600">Exported</div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Pipeline Actions</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={fetchEmails}
            disabled={fetchingEmails}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <Mail className={`w-5 h-5 ${fetchingEmails ? 'animate-pulse' : ''}`} />
            {fetchingEmails ? 'Fetching Emails...' : 'Fetch Emails'}
          </button>

          <button
            onClick={runPipeline}
            disabled={processing}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            <PlayCircle className={`w-5 h-5 ${processing ? 'animate-spin' : ''}`} />
            {processing ? 'Processing...' : 'Process Queue'}
          </button>

          <button
            onClick={exportBatch}
            disabled={exporting || (stats?.ready_for_export || 0) === 0}
            className="flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            <FileSpreadsheet className={`w-5 h-5 ${exporting ? 'animate-pulse' : ''}`} />
            {exporting ? 'Exporting...' : `Export (${stats?.ready_for_export || 0})`}
          </button>
        </div>

        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            <strong>Workflow:</strong> Fetch Emails → Process Queue → Export to Zoho CSV
          </p>
          <p className="text-sm text-gray-600 mt-2">
            <strong>Test Mode:</strong> You can also add invoices manually from the <a href="/parse" className="text-blue-600 hover:underline">Parsing Test</a> page by checking "Add to pipeline queue"
          </p>
        </div>
      </div>

      {/* Queue Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h3 className="text-lg font-semibold">Processing Queue</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Filename</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Export</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {queue.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm text-gray-900">#{item.id}</td>
                  <td className="px-4 py-2 text-sm">
                    {item.source === 'email' ? (
                      <Mail className="w-4 h-4 text-blue-500" />
                    ) : (
                      <Package className="w-4 h-4 text-gray-500" />
                    )}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-900">
                    {item.filename}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-600">
                    {item.customer_email || '-'}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(item.status)}
                      {getStatusBadge(item.status)}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    {item.export_status && getStatusBadge(item.export_status)}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-600">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {queue.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              No items in queue
            </div>
          )}
        </div>
      </div>

      {/* Exported Files Section */}
      <div className="bg-white rounded-lg shadow mt-6">
        <div className="p-4 border-b">
          <h3 className="text-lg font-semibold">Exported Files</h3>
          <p className="text-sm text-gray-600 mt-1">Previously exported CSV files ready for download</p>
        </div>
        
        <div className="overflow-x-auto">
          {exportedFiles.length > 0 ? (
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Filename</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Size</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {exportedFiles.slice(0, 5).map((file) => (
                  <tr key={file.filename} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm text-gray-900">
                      <div className="flex items-center gap-2">
                        <FileSpreadsheet className="w-4 h-4 text-green-500" />
                        {file.filename}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {(file.size / 1024).toFixed(2)} KB
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {new Date(file.created).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() => downloadFile(file.filename)}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-gray-500">
              No exported files yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PipelineManager;