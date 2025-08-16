import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  BuildingStorefrontIcon,
  EnvelopeIcon,
  IdentificationIcon,
  CogIcon
} from '@heroicons/react/24/outline';
import api from '../services/api';
import { toast } from 'react-toastify';

const CustomerList = () => {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await api.get('/api/customers');
      setCustomers(response.data.data || []);
    } catch (error) {
      console.error('Error fetching customers:', error);
      toast.error('Failed to load customers');
    } finally {
      setLoading(false);
    }
  };

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
        <h1 className="text-3xl font-bold text-gray-900">Customer Management</h1>
        <p className="text-gray-600 mt-2">Manage customer details and product mappings</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {customers.map((customer) => (
          <div key={customer.email} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <BuildingStorefrontIcon className="h-8 w-8 text-blue-600" />
                <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                  Active
                </span>
              </div>
              
              <h2 className="text-xl font-semibold text-gray-900 mb-3">
                {customer.customer_name}
              </h2>
              
              <div className="space-y-2 text-sm">
                <div className="flex items-center text-gray-600">
                  <EnvelopeIcon className="h-4 w-4 mr-2" />
                  <span className="truncate">{customer.email}</span>
                </div>
                
                <div className="flex items-center text-gray-600">
                  <IdentificationIcon className="h-4 w-4 mr-2" />
                  <span>TRN: {customer.trn || 'Not set'}</span>
                </div>
                
                <div className="text-gray-600">
                  <span className="font-medium">Payment:</span> {customer.payment_terms} days
                </div>
              </div>
              
              <div className="mt-6 flex justify-between items-center">
                <button
                  onClick={() => navigate(`/customers/${customer.email}/mappings`)}
                  className="flex items-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
                >
                  <CogIcon className="h-4 w-4 mr-2" />
                  Product Mappings
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {customers.length === 0 && (
        <div className="text-center py-12">
          <BuildingStorefrontIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">No customers found</p>
          <p className="text-gray-400 mt-2">Add customers to start managing product mappings</p>
        </div>
      )}
    </div>
  );
};

export default CustomerList;