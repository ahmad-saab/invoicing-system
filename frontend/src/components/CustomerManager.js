import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UserPlusIcon,
  BuildingOfficeIcon,
  EnvelopeIcon,
  IdentificationIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
  CheckCircleIcon,
  MagnifyingGlassIcon,
  PencilIcon
} from '@heroicons/react/24/outline';
import api from '../services/api';
import { toast } from 'react-toastify';
import DeliveryCalendar from './DeliveryCalendar';

const CustomerManager = () => {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [formData, setFormData] = useState({
    email: '',
    unique_alias: '',
    customer_name: '',
    customer_id_number: '',
    trn: '',
    billing_address: '',
    shipping_address: '',
    payment_terms: 30,
    currency: 'AED',
    delivery_calendar: '{"monday": true, "tuesday": true, "wednesday": true, "thursday": true, "friday": true, "saturday": false, "sunday": false}'
  });

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await api.get('/api/customers');
      setCustomers(response.data.data || []);
    } catch (error) {
      console.error('Error fetching customers:', error);
      toast.error('Failed to fetch customers');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!formData.email || !formData.customer_name || !formData.trn) {
      toast.error('Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      if (editingCustomer) {
        // Update existing customer
        await api.put(`/api/customers/${editingCustomer.email}`, formData);
        toast.success('Customer updated successfully');
      } else {
        // Create new customer
        await api.post('/api/customers', formData);
        toast.success('Customer created successfully');
      }
      
      // Reset form and refresh list
      resetForm();
      fetchCustomers();
    } catch (error) {
      console.error('Error saving customer:', error);
      toast.error(error.response?.data?.detail || 'Failed to save customer');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      email: '',
      unique_alias: '',
      customer_name: '',
      customer_id_number: '',
      trn: '',
      billing_address: '',
      shipping_address: '',
      payment_terms: 30,
      currency: 'AED'
    });
    setShowAddForm(false);
    setEditingCustomer(null);
  };

  const handleEdit = (customer) => {
    setFormData(customer);
    setEditingCustomer(customer);
    setShowAddForm(true);
  };

  const handleProductMappings = (email) => {
    navigate(`/product-mappings?customer=${email}`);
  };

  // Filter customers based on search
  const filteredCustomers = customers.filter(customer => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      customer.customer_name?.toLowerCase().includes(query) ||
      customer.email?.toLowerCase().includes(query) ||
      customer.customer_id_number?.toLowerCase().includes(query) ||
      customer.trn?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Customer Management</h1>
          <p className="text-gray-600 mt-2">Manage your customers and their information</p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center"
        >
          <UserPlusIcon className="h-5 w-5 mr-2" />
          {showAddForm ? 'Cancel' : 'Add Customer'}
        </button>
      </div>

      {/* Add/Edit Customer Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">
            {editingCustomer ? 'Edit Customer' : 'Add New Customer'}
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address *
                </label>
                <div className="relative">
                  <EnvelopeIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    disabled={editingCustomer}
                    required
                    className="pl-10 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="customer@example.com"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  This will be used to identify the customer from email sender
                </p>
              </div>

              {/* Customer Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Customer Name *
                </label>
                <div className="relative">
                  <BuildingOfficeIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    name="customer_name"
                    value={formData.customer_name}
                    onChange={handleInputChange}
                    required
                    className="pl-10 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Company Name"
                  />
                </div>
              </div>

              {/* Customer ID */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Customer ID Number
                </label>
                <div className="relative">
                  <IdentificationIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    name="customer_id_number"
                    value={formData.customer_id_number}
                    onChange={handleInputChange}
                    className="pl-10 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="CUST-001"
                  />
                </div>
              </div>

              {/* TRN */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  TRN (Tax Registration Number) *
                </label>
                <div className="relative">
                  <DocumentTextIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    name="trn"
                    value={formData.trn}
                    onChange={handleInputChange}
                    required
                    className="pl-10 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="100000000000000"
                  />
                </div>
              </div>

              {/* Unique Alias */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Unique Alias
                </label>
                <input
                  type="text"
                  name="unique_alias"
                  value={formData.unique_alias}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Optional: For customers with multiple branches"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use for customers with multiple branches
                </p>
              </div>

              {/* Payment Terms */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Payment Terms (Days)
                </label>
                <input
                  type="number"
                  name="payment_terms"
                  value={formData.payment_terms}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="30"
                />
              </div>

              {/* Currency */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Currency
                </label>
                <div className="relative">
                  <CurrencyDollarIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
                  <select
                    name="currency"
                    value={formData.currency}
                    onChange={handleInputChange}
                    className="pl-10 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="AED">AED</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Billing Address */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Billing Address
              </label>
              <textarea
                name="billing_address"
                value={formData.billing_address}
                onChange={handleInputChange}
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter billing address"
              />
            </div>

            {/* Shipping Address */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Shipping Address
              </label>
              <textarea
                name="shipping_address"
                value={formData.shipping_address}
                onChange={handleInputChange}
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter shipping address"
              />
            </div>

            {/* Delivery Calendar */}
            <div className="mt-4">
              <DeliveryCalendar 
                customerEmail={null}  // Don't pass email to prevent API calls
                initialCalendar={formData.delivery_calendar}
                embedded={true}
                onSave={(calendarJson) => {
                  // Just update local state, don't make API calls
                  setFormData(prev => ({ ...prev, delivery_calendar: calendarJson }));
                  return Promise.resolve(); // Return resolved promise
                }}
              />
            </div>

            {/* Submit Buttons */}
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 flex items-center"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Saving...
                  </>
                ) : (
                  <>
                    <CheckCircleIcon className="h-5 w-5 mr-2" />
                    {editingCustomer ? 'Update Customer' : 'Create Customer'}
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Search Bar */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search customers by name, email, ID, or TRN..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {searchQuery && (
              <p className="text-sm text-gray-500 mt-2">
                Found {filteredCustomers.length} of {customers.length} customers
              </p>
            )}
          </div>
        </div>

        {/* Customer Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Customer Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Customer ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  TRN
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Payment Terms
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Currency
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredCustomers.map((customer) => (
                <tr key={customer.email} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {customer.customer_name}
                    </div>
                    {customer.unique_alias && (
                      <div className="text-xs text-gray-500">
                        Alias: {customer.unique_alias}
                      </div>
                    )}
                    {customer.is_multi_location && (
                      <div className="mt-1">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                          <svg className="mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                          </svg>
                          {customer.total_locations} Locations
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{customer.email}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {customer.customer_id_number || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{customer.trn}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{customer.payment_terms} days</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
                      {customer.currency}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => handleEdit(customer)}
                      className="text-blue-600 hover:text-blue-900 mr-3"
                      title="Edit Customer"
                    >
                      <PencilIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleProductMappings(customer.email)}
                      className="text-green-600 hover:text-green-900"
                      title="Product Mappings"
                    >
                      Configure Products
                    </button>
                  </td>
                </tr>
              ))}
              {filteredCustomers.length === 0 && (
                <tr>
                  <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                    No customers found. Click "Add Customer" to create one.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Instructions */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">Customer Setup Instructions:</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• The email address will be used to identify customers when parsing LPOs</li>
          <li>• In production, this email will come from the SMTP sender</li>
          <li>• Make sure to enter accurate TRN and customer details for invoicing</li>
          <li>• After adding a customer, set up their product mappings by clicking "Configure Products"</li>
          <li>• Use unique alias for customers with multiple branches or locations</li>
        </ul>
      </div>
    </div>
  );
};

export default CustomerManager;