import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Supplier APIs
export const supplierAPI = {
  getAll: () => api.get('/api/suppliers'),
  getById: (id) => api.get(`/api/suppliers/${id}`),
  create: (data) => api.post('/api/suppliers', data),
  update: (id, data) => api.put(`/api/suppliers/${id}`, data),
  delete: (id) => api.delete(`/api/suppliers/${id}`),
};

// Field Pattern APIs
export const fieldPatternAPI = {
  getBySupplier: (supplierId) => api.get(`/api/patterns/fields/${supplierId}`),
  create: (data) => api.post('/api/patterns/fields', data),
  update: (id, data) => api.put(`/api/patterns/fields/${id}`, data),
};

// Item Pattern APIs
export const itemPatternAPI = {
  getBySupplier: (supplierId) => api.get(`/api/patterns/items/${supplierId}`),
  create: (data) => api.post('/api/patterns/items', data),
};

// UOM APIs
export const uomAPI = {
  getMappings: () => api.get('/api/uom/mappings'),
  createMapping: (data) => api.post('/api/uom/mappings', data),
  normalize: (uom) => api.post('/api/uom/normalize', { uom }),
};

// Parser APIs
export const parserAPI = {
  parseFile: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/parse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  testParse: (filePath) => api.post('/api/parse/test', { file_path: filePath }),
};

// History APIs
export const historyAPI = {
  getAll: (limit = 100) => api.get(`/api/history?limit=${limit}`),
  getByFile: (fileName) => api.get(`/api/history/${fileName}`),
};

// Customer Mapping APIs
export const customerAPI = {
  getMappings: () => api.get('/api/customers/mappings'),
  createMapping: (data) => api.post('/api/customers/mappings', data),
};

// Settings APIs
export const settingsAPI = {
  getAll: () => api.get('/api/settings'),
  update: (data) => api.post('/api/settings', data),
};

// System Status API
export const systemAPI = {
  getStatus: () => api.get('/api/status'),
};

// CSV Export APIs
export const exportAPI = {
  exportToZohoCSV: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/export/zoho-csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob'
    });
  },
  parseAndExport: (filePath) => api.post('/api/export/parse-and-export', { file_path: filePath }),
  downloadCSV: (filename) => api.get(`/api/export/download/${filename}`, { responseType: 'blob' })
};

export default api;