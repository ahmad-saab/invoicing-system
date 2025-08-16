import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { toast } from 'react-toastify';
import { 
  ChartBarIcon, 
  DocumentTextIcon, 
  UserGroupIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CurrencyDollarIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  DocumentMagnifyingGlassIcon
} from '@heroicons/react/24/outline';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    // Refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const response = await api.get('/api/dashboard/stats');
      setStats(response.data.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-AE', { 
      style: 'currency', 
      currency: 'AED' 
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  const overallStats = stats?.overall_stats || {};
  const dailyStats = stats?.daily_stats || [];
  const topCustomers = stats?.top_customers || [];
  const failedInvoices = stats?.failed_invoices || [];
  const statusBreakdown = stats?.status_breakdown || [];

  // Calculate max value for chart scaling
  const maxDailyCount = Math.max(...dailyStats.map(d => d.count || 0), 1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white shadow rounded-lg p-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Invoice Parser Dashboard</h1>
        <p className="text-gray-600">Real-time parsing analytics and performance metrics</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Parsed */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Parsed</p>
              <p className="text-3xl font-bold text-gray-900">{overallStats.total || 0}</p>
              <p className="text-xs text-gray-500 mt-1">All time</p>
            </div>
            <div className="bg-blue-100 p-3 rounded-full">
              <DocumentTextIcon className="h-8 w-8 text-blue-600" />
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Success Rate</p>
              <p className="text-3xl font-bold text-green-600">
                {overallStats.success_rate?.toFixed(1) || 0}%
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {overallStats.success || 0} successful
              </p>
            </div>
            <div className="bg-green-100 p-3 rounded-full">
              <CheckCircleIcon className="h-8 w-8 text-green-600" />
            </div>
          </div>
        </div>

        {/* Failed Invoices */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Failed</p>
              <p className="text-3xl font-bold text-red-600">{overallStats.failed || 0}</p>
              <p className="text-xs text-gray-500 mt-1">
                {overallStats.partial || 0} partial
              </p>
            </div>
            <div className="bg-red-100 p-3 rounded-full">
              <XCircleIcon className="h-8 w-8 text-red-600" />
            </div>
          </div>
        </div>

        {/* Total Revenue */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Processed</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(overallStats.total_revenue)}
              </p>
              <p className="text-xs text-gray-500 mt-1">From parsed invoices</p>
            </div>
            <div className="bg-yellow-100 p-3 rounded-full">
              <CurrencyDollarIcon className="h-8 w-8 text-yellow-600" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Daily Activity Chart */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold text-lg mb-4">Parsing Activity (Last 7 Days)</h3>
          <div className="space-y-3">
            {dailyStats.length > 0 ? (
              dailyStats.map((day, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <div className="w-20 text-sm text-gray-600">
                    {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-8 relative overflow-hidden">
                        <div 
                          className="bg-blue-500 h-full rounded-full flex items-center justify-end pr-2"
                          style={{ width: `${(day.count / maxDailyCount) * 100}%` }}
                        >
                          <span className="text-xs text-white font-medium">{day.count}</span>
                        </div>
                        {day.success_count > 0 && (
                          <div 
                            className="absolute top-0 left-0 bg-green-500 h-full rounded-full"
                            style={{ width: `${(day.success_count / maxDailyCount) * 100}%` }}
                          />
                        )}
                      </div>
                      <span className="text-sm text-gray-600 w-16 text-right">
                        {((day.success_count / day.count) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-center py-8">No parsing data available</p>
            )}
          </div>
          <div className="mt-4 flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
              <span>Successful</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-blue-500 rounded"></div>
              <span>Total</span>
            </div>
          </div>
        </div>

        {/* Status Breakdown Pie Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold text-lg mb-4">Status Breakdown</h3>
          <div className="space-y-3">
            {statusBreakdown.map((status, idx) => {
              const percentage = ((status.count / overallStats.total) * 100).toFixed(1);
              const colors = {
                success: 'bg-green-500',
                failed: 'bg-red-500',
                partial: 'bg-yellow-500'
              };
              const icons = {
                success: <CheckCircleIcon className="h-5 w-5" />,
                failed: <XCircleIcon className="h-5 w-5" />,
                partial: <ExclamationTriangleIcon className="h-5 w-5" />
              };
              
              return (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`${colors[status.status]} text-white p-1 rounded`}>
                      {icons[status.status]}
                    </div>
                    <span className="capitalize">{status.status}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{status.count}</span>
                    <span className="text-sm text-gray-500">({percentage}%)</span>
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* Visual representation */}
          <div className="mt-4 h-4 bg-gray-200 rounded-full overflow-hidden flex">
            {statusBreakdown.map((status, idx) => {
              const percentage = (status.count / overallStats.total) * 100;
              const colors = {
                success: 'bg-green-500',
                failed: 'bg-red-500',
                partial: 'bg-yellow-500'
              };
              return (
                <div
                  key={idx}
                  className={colors[status.status]}
                  style={{ width: `${percentage}%` }}
                />
              );
            })}
          </div>
        </div>
      </div>

      {/* Top Customers and Failed Invoices */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Customers */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold text-lg mb-4">Top Customers by Volume</h3>
          <div className="space-y-3">
            {topCustomers.length > 0 ? (
              topCustomers.map((customer, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="bg-blue-100 text-blue-600 font-bold w-8 h-8 rounded-full flex items-center justify-center text-sm">
                      {idx + 1}
                    </div>
                    <div>
                      <p className="font-medium">{customer.customer_name || customer.customer_id}</p>
                      <p className="text-xs text-gray-500">{customer.invoice_count} invoices</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{formatCurrency(customer.total_amount)}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-center py-8">No customer data available</p>
            )}
          </div>
        </div>

        {/* Recent Failed Invoices */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg">Recent Failed Invoices</h3>
            <span className="text-sm text-red-600 font-medium">{failedInvoices.length} failed</span>
          </div>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {failedInvoices.length > 0 ? (
              failedInvoices.map((invoice, idx) => (
                <div key={idx} className="p-3 bg-red-50 rounded-lg border border-red-200">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{invoice.filename}</p>
                      <p className="text-xs text-red-600 mt-1">
                        {invoice.error_message || 'Unknown error'}
                      </p>
                      {invoice.unmapped_count > 0 && (
                        <p className="text-xs text-gray-500 mt-1">
                          {invoice.unmapped_count} unmapped fields
                        </p>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 ml-2">
                      {formatDate(invoice.parsed_at)}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-center py-8">No failed invoices</p>
            )}
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <UserGroupIcon className="h-6 w-6 text-gray-600" />
            <div>
              <p className="text-sm text-gray-600">Active Customers</p>
              <p className="text-xl font-semibold">{stats?.customer_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <DocumentMagnifyingGlassIcon className="h-6 w-6 text-gray-600" />
            <div>
              <p className="text-sm text-gray-600">Field Mappings</p>
              <p className="text-xl font-semibold">{stats?.mapping_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <ClockIcon className="h-6 w-6 text-gray-600" />
            <div>
              <p className="text-sm text-gray-600">Avg Processing Time</p>
              <p className="text-xl font-semibold">
                {((overallStats.avg_processing_time || 0) / 1000).toFixed(1)}s
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;