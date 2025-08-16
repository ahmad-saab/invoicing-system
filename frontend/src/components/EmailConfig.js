import React, { useState, useEffect } from 'react';
import { Mail, Server, Lock, Check, AlertCircle, RefreshCw, Save, Eye, EyeOff, Clock, Globe } from 'lucide-react';

const EmailConfig = () => {
  const [config, setConfig] = useState({
    config_name: 'default',
    email_address: '',
    password: '',
    server: 'imap.gmail.com',
    port: 993,
    use_ssl: true,
    use_tls: false,
    check_interval: 300,
    folders: 'INBOX',
    search_subjects: 'LPO,Purchase Order,PO,Local Purchase Order',
    unseen_only: true,
    active: true,
    // New time configuration fields
    check_lookback_hours: 24,
    server_timezone_offset: 0,
    auto_detect_timezone: true,
    force_local_time: true,
    // Daily cutoff time fields
    daily_cutoff_time: '17:00',
    skip_weekends: true,
    cutoff_timezone: 'local'
  });

  const [testStatus, setTestStatus] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/email-config/default');
      const result = await response.json();
      if (result.status === 'success' && result.data) {
        setConfig({
          ...config,
          ...result.data,
          password: '' // Don't show password
        });
      }
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setTestStatus(null);
    
    try {
      const response = await fetch('http://localhost:8001/api/email-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
      });

      const result = await response.json();
      
      if (result.status === 'success') {
        setTestStatus({
          type: 'success',
          message: 'Configuration saved successfully!'
        });
      } else {
        setTestStatus({
          type: 'error',
          message: 'Failed to save configuration'
        });
      }
    } catch (error) {
      setTestStatus({
        type: 'error',
        message: 'Error saving configuration'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestStatus(null);
    
    try {
      const response = await fetch('http://localhost:8001/api/email-config/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
      });

      const result = await response.json();
      setTestStatus({
        type: result.status === 'success' ? 'success' : 'error',
        message: result.message
      });
    } catch (error) {
      setTestStatus({
        type: 'error',
        message: 'Failed to test connection'
      });
    } finally {
      setTesting(false);
    }
  };

  const handleChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Mail className="w-8 h-8 text-blue-600" />
          Email Configuration
        </h2>
        <p className="text-gray-600 mt-2">
          Configure email settings to automatically fetch and process LPO emails
        </p>
      </div>

      {/* Status Messages */}
      {testStatus && (
        <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
          testStatus.type === 'success' ? 'bg-green-50 text-green-800' :
          'bg-red-50 text-red-800'
        }`}>
          {testStatus.type === 'success' ? (
            <Check className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          {testStatus.message}
        </div>
      )}

      {/* Configuration Form */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Email Settings */}
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Mail className="w-5 h-5" />
              Email Account
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={config.email_address}
                  onChange={(e) => handleChange('email_address', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="orders@atrade.ae"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password / App Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={config.password}
                    onChange={(e) => handleChange('password', e.target.value)}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter app password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  For Gmail, use an App Password instead of your regular password
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Check Interval (seconds)
                </label>
                <input
                  type="number"
                  value={config.check_interval}
                  onChange={(e) => handleChange('check_interval', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="60"
                />
                <p className="text-xs text-gray-500 mt-1">
                  How often to check for new emails (minimum 60 seconds)
                </p>
              </div>
            </div>
          </div>

          {/* Server Settings */}
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Server className="w-5 h-5" />
              Server Settings
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  IMAP Server
                </label>
                <input
                  type="text"
                  value={config.server}
                  onChange={(e) => handleChange('server', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="imap.gmail.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Port
                </label>
                <input
                  type="number"
                  value={config.port}
                  onChange={(e) => handleChange('port', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.use_ssl}
                    onChange={(e) => handleChange('use_ssl', e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Use SSL</span>
                </label>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.use_tls}
                    onChange={(e) => handleChange('use_tls', e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Use TLS</span>
                </label>
              </div>
            </div>
          </div>

          {/* Cutoff Time Settings */}
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Daily Cutoff Time Settings
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Daily Order Cutoff Time
                </label>
                <input
                  type="time"
                  value={config.daily_cutoff_time}
                  onChange={(e) => handleChange('daily_cutoff_time', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Time when daily orders stop being accepted (e.g., 17:00 for 5:00 PM)
                </p>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.skip_weekends}
                    onChange={(e) => handleChange('skip_weekends', e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Skip Weekends</span>
                </label>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-start gap-2">
                  <Clock className="w-4 h-4 text-blue-600 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-blue-800">How Cutoff Time Works:</p>
                    <ul className="text-blue-700 mt-2 space-y-1">
                      <li>• <strong>Before Cutoff:</strong> System searches from yesterday's cutoff to now</li>
                      <li>• <strong>After Cutoff:</strong> System searches from today's cutoff to now</li>
                      <li>• <strong>Example:</strong> If cutoff is 5:00 PM and it's 3:00 PM, search from yesterday 5:00 PM</li>
                      <li>• <strong>Example:</strong> If cutoff is 5:00 PM and it's 7:00 PM, search from today 5:00 PM</li>
                      <li>• <strong>Weekends:</strong> Automatically skipped if enabled (Sat/Sun → next Monday)</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Legacy Time Settings - Hidden by default */}
          <div className="hidden">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Legacy Time Settings
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Check Lookback (Hours) - Legacy
                </label>
                <input
                  type="number"
                  value={config.check_lookback_hours}
                  onChange={(e) => handleChange('check_lookback_hours', parseInt(e.target.value) || 24)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="1"
                  max="168"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Legacy: How many hours back to search for emails (1-168 hours)
                </p>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.force_local_time}
                    onChange={(e) => handleChange('force_local_time', e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Use Local Time</span>
                </label>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.auto_detect_timezone}
                    onChange={(e) => handleChange('auto_detect_timezone', e.target.checked)}
                    className="rounded border-gray-300"
                    disabled={config.force_local_time}
                  />
                  <span className="text-sm">Auto-detect Server Timezone</span>
                </label>
              </div>

              {!config.force_local_time && !config.auto_detect_timezone && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Manual Timezone Offset (Minutes)
                  </label>
                  <input
                    type="number"
                    value={config.server_timezone_offset}
                    onChange={(e) => handleChange('server_timezone_offset', parseInt(e.target.value) || 0)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="-720"
                    max="720"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Server time offset from local time in minutes (-720 to +720)
                  </p>
                </div>
              )}

              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                <div className="flex items-start gap-2">
                  <Globe className="w-4 h-4 text-amber-600 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-amber-800">Timezone Configuration:</p>
                    <ul className="text-amber-700 mt-1 space-y-1">
                      <li>• <strong>Use Local Time:</strong> Recommended for most users - searches based on your system time</li>
                      <li>• <strong>Auto-detect:</strong> Automatically detects email server timezone differences</li>
                      <li>• <strong>Manual Offset:</strong> Set manual timezone difference if auto-detection fails</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Search Settings */}
          <div className="md:col-span-2">
            <h3 className="text-lg font-semibold mb-4">Search Settings</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Folders to Search
                </label>
                <input
                  type="text"
                  value={config.folders}
                  onChange={(e) => handleChange('folders', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="INBOX"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Comma-separated list of folders to search
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subject Keywords
                </label>
                <input
                  type="text"
                  value={config.search_subjects}
                  onChange={(e) => handleChange('search_subjects', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="LPO,Purchase Order,PO"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Comma-separated keywords to search in email subjects
                </p>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.unseen_only}
                    onChange={(e) => handleChange('unseen_only', e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Only fetch unread emails</span>
                </label>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.active}
                    onChange={(e) => handleChange('active', e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">Configuration active</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex gap-3">
          <button
            onClick={handleTest}
            disabled={testing || !config.email_address || !config.password}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${testing ? 'animate-spin' : ''}`} />
            {testing ? 'Testing...' : 'Test Connection'}
          </button>

          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>

        {/* Help Section */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-2">Gmail Configuration Help</h4>
          <ol className="text-sm text-blue-800 space-y-1">
            <li>1. Enable 2-factor authentication in your Google account</li>
            <li>2. Generate an App Password: Go to Google Account → Security → 2-Step Verification → App passwords</li>
            <li>3. Use the generated App Password instead of your regular password</li>
            <li>4. Server: imap.gmail.com, Port: 993, SSL: Enabled</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default EmailConfig;