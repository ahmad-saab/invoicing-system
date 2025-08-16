import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Import components
import Dashboard from './components/Dashboard';
import CustomerList from './components/CustomerList';
import CustomerManager from './components/CustomerManager';
import ProductMappingManager from './components/ProductMappingManager';
import ParsingTest from './components/ParsingTest';
import ParsingFailures from './components/ParsingFailures';
import ExportManager from './components/ExportManager';
import EmailConfig from './components/EmailConfig';
import PipelineManager from './components/PipelineManager';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        {/* Navigation Header */}
        <nav className="bg-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-xl font-bold text-gray-800">Simple Invoice Parser</h1>
                </div>
                <div className="hidden md:ml-6 md:flex md:space-x-8">
                  <Link to="/" className="border-b-2 border-transparent hover:border-gray-300 text-gray-900 inline-flex items-center px-1 pt-1 text-sm font-medium">
                    Dashboard
                  </Link>
                  <Link to="/manage-customers" className="border-b-2 border-transparent hover:border-gray-300 text-gray-900 inline-flex items-center px-1 pt-1 text-sm font-medium">
                    Manage Customers
                  </Link>
                  <Link to="/customers" className="border-b-2 border-transparent hover:border-gray-300 text-gray-900 inline-flex items-center px-1 pt-1 text-sm font-medium">
                    Product Mappings
                  </Link>
                  <Link to="/parse" className="border-b-2 border-transparent hover:border-gray-300 text-gray-900 inline-flex items-center px-1 pt-1 text-sm font-medium">
                    Parsing Test
                  </Link>
                  <Link to="/failures" className="border-b-2 border-transparent hover:border-gray-300 text-gray-900 inline-flex items-center px-1 pt-1 text-sm font-medium">
                    Parsing Failures
                  </Link>
                  <Link to="/export" className="border-b-2 border-transparent hover:border-gray-300 text-gray-900 inline-flex items-center px-1 pt-1 text-sm font-medium">
                    Export
                  </Link>
                  <Link to="/pipeline" className="border-b-2 border-transparent hover:border-gray-300 text-gray-900 inline-flex items-center px-1 pt-1 text-sm font-medium">
                    Pipeline
                  </Link>
                  <Link to="/email-config" className="border-b-2 border-transparent hover:border-gray-300 text-gray-900 inline-flex items-center px-1 pt-1 text-sm font-medium">
                    Email Config
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main>
          <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/manage-customers" element={<CustomerManager />} />
              <Route path="/customers" element={<CustomerList />} />
              <Route path="/customers/:customerEmail/mappings" element={<ProductMappingManager />} />
              <Route path="/product-mappings" element={<ProductMappingManager />} />
              <Route path="/parse" element={<ParsingTest />} />
              <Route path="/failures" element={<ParsingFailures />} />
              <Route path="/export" element={<ExportManager />} />
              <Route path="/pipeline" element={<PipelineManager />} />
              <Route path="/email-config" element={<EmailConfig />} />
            </Routes>
          </div>
        </main>

        {/* Toast notifications */}
        <ToastContainer position="bottom-right" />
      </div>
    </Router>
  );
}

export default App;