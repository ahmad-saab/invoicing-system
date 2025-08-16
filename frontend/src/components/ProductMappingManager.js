import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeftIcon,
  PlusIcon,
  TrashIcon,
  CheckIcon,
  XMarkIcon,
  PencilIcon
} from '@heroicons/react/24/outline';
import api from '../services/api';
import { toast } from 'react-toastify';

const ProductMappingManager = () => {
  const { customerEmail } = useParams();
  const navigate = useNavigate();
  const [customer, setCustomer] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingPaymentTerms, setEditingPaymentTerms] = useState(false);
  const [paymentTerms, setPaymentTerms] = useState(30);
  const [editingAlias, setEditingAlias] = useState(false);
  const [uniqueAlias, setUniqueAlias] = useState('');
  const [branches, setBranches] = useState([]);
  const [showBranchForm, setShowBranchForm] = useState(false);
  const [newBranch, setNewBranch] = useState({
    branch_identifier: '',
    branch_name: '',
    delivery_address: ''
  });
  const [newMapping, setNewMapping] = useState({
    lpo_product_name: '',
    system_product_name: '',
    unit_price: '',
    unit: 'EACH'
  });

  useEffect(() => {
    fetchData();
  }, [customerEmail]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch customer details
      const custResponse = await api.get(`/api/customers/${customerEmail}`);
      setCustomer(custResponse.data.data);
      setPaymentTerms(custResponse.data.data.payment_terms || 30);
      setUniqueAlias(custResponse.data.data.unique_alias || '');
      
      // Fetch product mappings
      const mappingResponse = await api.get(`/api/customers/${customerEmail}/mappings`);
      setMappings(mappingResponse.data.data);
      
      // Fetch branches
      const branchResponse = await api.get(`/api/customers/${customerEmail}/branches`);
      setBranches(branchResponse.data.data);
      
    } catch (error) {
      toast.error('Failed to load data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMapping = async () => {
    if (!newMapping.lpo_product_name || !newMapping.system_product_name || !newMapping.unit_price) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      await api.post(`/api/customers/${customerEmail}/mappings`, {
        customer_email: customerEmail,
        ...newMapping,
        unit_price: parseFloat(newMapping.unit_price)
      });
      
      toast.success('Product mapping added');
      setNewMapping({
        lpo_product_name: '',
        system_product_name: '',
        unit_price: '',
        unit: 'EACH'
      });
      setShowAddForm(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to add mapping');
      console.error(error);
    }
  };

  const handleDeleteMapping = async (mappingId) => {
    if (window.confirm('Are you sure you want to delete this mapping?')) {
      try {
        await api.delete(`/api/mappings/${mappingId}`);
        toast.success('Mapping deleted');
        fetchData();
      } catch (error) {
        toast.error('Failed to delete mapping');
      }
    }
  };

  const handleSavePaymentTerms = async () => {
    try {
      await api.put(`/api/customers/${customerEmail}`, {
        ...customer,
        payment_terms: parseInt(paymentTerms)
      });
      toast.success('Payment terms updated');
      setEditingPaymentTerms(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to update payment terms');
      console.error(error);
    }
  };

  const handleSaveAlias = async () => {
    try {
      await api.put(`/api/customers/${customerEmail}`, {
        ...customer,
        unique_alias: uniqueAlias.trim() || null
      });
      toast.success('Unique alias updated');
      setEditingAlias(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to update alias');
      console.error(error);
    }
  };

  const handleAddBranch = async () => {
    if (!newBranch.branch_identifier || !newBranch.branch_name) {
      toast.error('Please fill branch identifier and name');
      return;
    }

    try {
      await api.post(`/api/customers/${customerEmail}/branches`, {
        customer_email: customerEmail,
        ...newBranch
      });
      toast.success('Branch added');
      setNewBranch({
        branch_identifier: '',
        branch_name: '',
        delivery_address: ''
      });
      setShowBranchForm(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to add branch');
      console.error(error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/customers')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back to Customers
        </button>
        
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Product Mappings for {customer?.customer_name}
          </h1>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Email:</span>
              <p className="font-medium">{customer?.email}</p>
            </div>
            <div>
              <span className="text-gray-500">Customer ID:</span>
              <p className="font-medium">{customer?.customer_id_number}</p>
            </div>
            <div>
              <span className="text-gray-500">TRN:</span>
              <p className="font-medium">{customer?.trn}</p>
            </div>
            <div>
              <span className="text-gray-500">Unique Alias:</span>
              {editingAlias ? (
                <div className="flex items-center space-x-1">
                  <input
                    type="text"
                    value={uniqueAlias}
                    onChange={(e) => setUniqueAlias(e.target.value)}
                    className="w-24 px-2 py-1 border rounded text-sm"
                    placeholder="Branch ID"
                  />
                  <button
                    onClick={handleSaveAlias}
                    className="text-green-600 hover:text-green-800"
                  >
                    <CheckIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      setEditingAlias(false);
                      setUniqueAlias(customer?.unique_alias || '');
                    }}
                    className="text-red-600 hover:text-red-800"
                  >
                    <XMarkIcon className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <p className="font-medium">{customer?.unique_alias || 'Not set'}</p>
                  <button
                    onClick={() => setEditingAlias(true)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <PencilIcon className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
            <div>
              <span className="text-gray-500">Payment Terms:</span>
              {editingPaymentTerms ? (
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    value={paymentTerms}
                    onChange={(e) => setPaymentTerms(e.target.value)}
                    className="w-20 px-2 py-1 border rounded text-sm"
                    min="0"
                    max="365"
                  />
                  <span className="text-sm">days</span>
                  <button
                    onClick={handleSavePaymentTerms}
                    className="text-green-600 hover:text-green-800"
                  >
                    <CheckIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      setEditingPaymentTerms(false);
                      setPaymentTerms(customer?.payment_terms || 30);
                    }}
                    className="text-red-600 hover:text-red-800"
                  >
                    <XMarkIcon className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <p className="font-medium">{customer?.payment_terms} days</p>
                  <button
                    onClick={() => setEditingPaymentTerms(true)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <PencilIcon className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Product Mappings Section */}
      <div className="bg-white rounded-lg shadow-sm">
        <div className="bg-gray-800 text-white px-6 py-3 rounded-t-lg flex justify-between items-center">
          <h2 className="text-lg font-semibold">Product Name Mappings</h2>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm flex items-center"
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Mapping
          </button>
        </div>

        <div className="p-6">
          {/* Add Form */}
          {showAddForm && (
            <div className="bg-blue-50 p-4 rounded-lg mb-6">
              <h3 className="font-semibold mb-3">Add New Product Mapping</h3>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    LPO Product Name *
                  </label>
                  <input
                    type="text"
                    placeholder="As appears in LPO"
                    value={newMapping.lpo_product_name}
                    onChange={(e) => setNewMapping({...newMapping, lpo_product_name: e.target.value})}
                    className="w-full px-3 py-2 border rounded-md text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    System Product Name *
                  </label>
                  <input
                    type="text"
                    placeholder="Your product name"
                    value={newMapping.system_product_name}
                    onChange={(e) => setNewMapping({...newMapping, system_product_name: e.target.value})}
                    className="w-full px-3 py-2 border rounded-md text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Unit Price (AED) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="85.00"
                    value={newMapping.unit_price}
                    onChange={(e) => setNewMapping({...newMapping, unit_price: e.target.value})}
                    className="w-full px-3 py-2 border rounded-md text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Unit
                  </label>
                  <select
                    value={newMapping.unit}
                    onChange={(e) => setNewMapping({...newMapping, unit: e.target.value})}
                    className="w-full px-3 py-2 border rounded-md text-sm"
                  >
                    <option value="EACH">EACH</option>
                    <option value="CASE">CASE</option>
                    <option value="BOX">BOX</option>
                    <option value="CAN">CAN</option>
                    <option value="BOTTLE">BOTTLE</option>
                    <option value="TIN">TIN</option>
                    <option value="PACK">PACK</option>
                    <option value="KG">KG</option>
                    <option value="LTR">LTR</option>
                  </select>
                </div>
                <div className="flex items-end space-x-2">
                  <button
                    onClick={handleAddMapping}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm flex items-center"
                  >
                    <CheckIcon className="h-4 w-4 mr-1" />
                    Save
                  </button>
                  <button
                    onClick={() => {
                      setShowAddForm(false);
                      setNewMapping({
                        lpo_product_name: '',
                        system_product_name: '',
                        unit_price: '',
                        unit: 'EACH'
                      });
                    }}
                    className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded text-sm flex items-center"
                  >
                    <XMarkIcon className="h-4 w-4 mr-1" />
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Mappings Table */}
          {mappings.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      LPO Product Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      System Product Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Unit Price
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Unit
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {mappings.map((mapping) => (
                    <tr key={mapping.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {mapping.lpo_product_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {mapping.system_product_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        AED {mapping.unit_price}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {mapping.unit}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <button
                          onClick={() => handleDeleteMapping(mapping.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">No product mappings yet</p>
              <p className="text-sm text-gray-400">
                Add mappings to tell the system how to recognize products in this customer's LPOs
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Branch Management Section */}
      {customer?.unique_alias && (
        <div className="mt-6 bg-white rounded-lg shadow-sm">
          <div className="bg-gray-800 text-white px-6 py-3 rounded-t-lg flex justify-between items-center">
            <h2 className="text-lg font-semibold">Branch Identifiers</h2>
            <button
              onClick={() => setShowBranchForm(!showBranchForm)}
              className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm flex items-center"
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              Add Branch
            </button>
          </div>
          
          <div className="p-6">
            {/* Add Branch Form */}
            {showBranchForm && (
              <div className="bg-blue-50 p-4 rounded-lg mb-6">
                <h3 className="font-semibold mb-3">Add New Branch Identifier</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Branch Identifier Text *
                    </label>
                    <input
                      type="text"
                      placeholder="Text in LPO that identifies branch"
                      value={newBranch.branch_identifier}
                      onChange={(e) => setNewBranch({...newBranch, branch_identifier: e.target.value})}
                      className="w-full px-3 py-2 border rounded-md text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Branch Name *
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., Dubai Mall Branch"
                      value={newBranch.branch_name}
                      onChange={(e) => setNewBranch({...newBranch, branch_name: e.target.value})}
                      className="w-full px-3 py-2 border rounded-md text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Delivery Address
                    </label>
                    <input
                      type="text"
                      placeholder="Branch delivery address"
                      value={newBranch.delivery_address}
                      onChange={(e) => setNewBranch({...newBranch, delivery_address: e.target.value})}
                      className="w-full px-3 py-2 border rounded-md text-sm"
                    />
                  </div>
                </div>
                <div className="mt-3 flex space-x-2">
                  <button
                    onClick={handleAddBranch}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm flex items-center"
                  >
                    <CheckIcon className="h-4 w-4 mr-1" />
                    Save Branch
                  </button>
                  <button
                    onClick={() => {
                      setShowBranchForm(false);
                      setNewBranch({
                        branch_identifier: '',
                        branch_name: '',
                        delivery_address: ''
                      });
                    }}
                    className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded text-sm flex items-center"
                  >
                    <XMarkIcon className="h-4 w-4 mr-1" />
                    Cancel
                  </button>
                </div>
              </div>
            )}
            
            {/* Branches List */}
            {branches.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Branch Identifier
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Branch Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Delivery Address
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {branches.map((branch, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {branch.branch_identifier}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {branch.branch_name}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {branch.delivery_address || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">No branch identifiers configured</p>
                <p className="text-sm text-gray-400">
                  Add branch identifiers to help the system identify different delivery locations in LPOs
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
        <h3 className="font-semibold text-amber-900 mb-2">System Configuration Guide:</h3>
        
        <div className="mb-3">
          <h4 className="font-semibold text-amber-800">Unique Alias:</h4>
          <p className="text-sm text-amber-700">
            Set this when one email address sends LPOs for multiple branches/locations. 
            The alias helps identify which branch the LPO is for.
          </p>
        </div>
        
        <div className="mb-3">
          <h4 className="font-semibold text-amber-800">Branch Identifiers:</h4>
          <p className="text-sm text-amber-700">
            Only appears when Unique Alias is set. Add text patterns that appear in LPOs to identify specific branches 
            (e.g., "Dubai Mall", "DIFC Branch").
          </p>
        </div>
        
        <div>
          <h4 className="font-semibold text-amber-800">Product Mapping:</h4>
          <ul className="text-sm text-amber-700 space-y-1 mt-1">
            <li>• <strong>LPO Product Name:</strong> Exactly how the product appears in the customer's LPO</li>
            <li>• <strong>System Product Name:</strong> Your internal product name for invoicing</li>
            <li>• <strong>Unit Price:</strong> The agreed price for this customer (will be used instead of LPO price)</li>
            <li>• <strong>Unit:</strong> The unit of measurement (CASE, CAN, etc.)</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ProductMappingManager;