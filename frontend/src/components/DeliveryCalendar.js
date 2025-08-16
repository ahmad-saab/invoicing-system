import React, { useState, useEffect } from 'react';
import { Calendar, Check, X, Save, AlertCircle } from 'lucide-react';

const DeliveryCalendar = ({ customerEmail, initialCalendar, onSave, embedded = true }) => {
  const [calendar, setCalendar] = useState({
    monday: true,
    tuesday: true,
    wednesday: true,
    thursday: true,
    friday: true,
    saturday: false,
    sunday: false
  });
  
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const dayNames = [
    { key: 'monday', label: 'Monday', abbr: 'Mon' },
    { key: 'tuesday', label: 'Tuesday', abbr: 'Tue' },
    { key: 'wednesday', label: 'Wednesday', abbr: 'Wed' },
    { key: 'thursday', label: 'Thursday', abbr: 'Thu' },
    { key: 'friday', label: 'Friday', abbr: 'Fri' },
    { key: 'saturday', label: 'Saturday', abbr: 'Sat' },
    { key: 'sunday', label: 'Sunday', abbr: 'Sun' }
  ];

  useEffect(() => {
    if (initialCalendar) {
      try {
        const parsed = typeof initialCalendar === 'string' 
          ? JSON.parse(initialCalendar) 
          : initialCalendar;
        setCalendar(parsed);
      } catch (e) {
        console.error('Error parsing calendar:', e);
      }
    }
  }, [initialCalendar]);

  const toggleDay = (day) => {
    if (!isEditing) return;
    setCalendar(prev => ({
      ...prev,
      [day]: !prev[day]
    }));
    // Don't auto-save, just update the state
  };

  const saveCalendar = async (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    
    setIsSaving(true);
    setMessage(null);
    
    try {
      const calendarJson = JSON.stringify(calendar);
      
      if (onSave) {
        // If parent component provided onSave callback (embedded mode)
        await onSave(calendarJson);
        // When embedded, just show a brief success and close edit mode
        if (embedded) {
          setIsEditing(false);
          // Don't show message in embedded mode to avoid confusion
        } else {
          setMessage({ type: 'success', text: 'Calendar settings saved!' });
          setIsEditing(false);
        }
      } else if (customerEmail && !embedded) {
        // Direct API call only for standalone use (not embedded)
        const response = await fetch(`http://localhost:8001/api/customers/${customerEmail}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: customerEmail,
            delivery_calendar: calendarJson
          })
        });

        if (response.ok) {
          setMessage({ type: 'success', text: 'Delivery calendar updated successfully!' });
          setIsEditing(false);
        } else {
          throw new Error('Failed to update calendar');
        }
      } else {
        // Just close edit mode
        setIsEditing(false);
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save calendar' });
      console.error('Error saving calendar:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const cancelEdit = () => {
    setIsEditing(false);
    // Reset to initial calendar
    if (initialCalendar) {
      try {
        const parsed = typeof initialCalendar === 'string' 
          ? JSON.parse(initialCalendar) 
          : initialCalendar;
        setCalendar(parsed);
      } catch (e) {
        console.error('Error parsing calendar:', e);
      }
    }
  };

  // Check if at least one day is selected
  const hasValidSelection = Object.values(calendar).some(val => val === true);

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-900">Delivery Calendar</h3>
        </div>
        
        {!isEditing ? (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsEditing(true);
            }}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Edit Calendar
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                cancelEdit();
              }}
              className="px-2 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={saveCalendar}
              disabled={isSaving || !hasValidSelection}
              className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center gap-1"
            >
              <Save className="w-3 h-3" />
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        )}
      </div>

      <p className="text-sm text-gray-600 mb-3">
        Select delivery days for invoice generation. System will use the nearest allowed day.
      </p>

      {message && (
        <div className={`mb-4 p-3 rounded flex items-center gap-2 ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          <AlertCircle className="w-4 h-4" />
          {message.text}
        </div>
      )}

      {!hasValidSelection && isEditing && (
        <div className="mb-4 p-3 rounded bg-yellow-50 text-yellow-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          At least one delivery day must be selected
        </div>
      )}

      <div className="grid grid-cols-7 gap-1">
        {dayNames.map(day => (
          <div key={day.key} className="text-center">
            <div className="text-xs text-gray-500 mb-1 font-medium">
              {day.abbr}
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleDay(day.key);
              }}
              disabled={!isEditing}
              className={`
                w-full p-2 rounded border transition-all text-xs
                ${isEditing ? 'cursor-pointer hover:shadow-sm' : 'cursor-not-allowed'}
                ${calendar[day.key] 
                  ? 'bg-blue-100 border-blue-400 text-blue-700' 
                  : 'bg-gray-50 border-gray-300 text-gray-400'
                }
              `}
            >
              {calendar[day.key] ? (
                <Check className="w-4 h-4 mx-auto" />
              ) : (
                <X className="w-4 h-4 mx-auto" />
              )}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-4 p-3 bg-gray-50 rounded text-xs">
        <h4 className="font-semibold text-gray-700 mb-1">How it works:</h4>
        <ul className="text-gray-600 space-y-0.5">
          <li>• Invoice date: Nearest allowed delivery day</li>
          <li>• Due date: End of month + payment terms</li>
          <li>• Example: Saturday LPO → Monday invoice</li>
        </ul>
      </div>

      {/* Preview of next delivery dates */}
      <div className="mt-3 p-3 bg-blue-50 rounded text-xs">
        <div className="text-blue-800">
          <div>
            <span className="font-semibold">Active Days:</span>{' '}
            {dayNames
              .filter(day => calendar[day.key])
              .map(day => day.abbr)
              .join(', ') || 'None'}
          </div>
          <div className="mt-1">
            <span className="font-semibold">Next Date:</span>{' '}
            {(() => {
              const today = new Date();
              const dayMap = [
                'sunday', 'monday', 'tuesday', 'wednesday', 
                'thursday', 'friday', 'saturday'
              ];
              
              for (let i = 0; i < 7; i++) {
                const checkDate = new Date(today);
                checkDate.setDate(today.getDate() + i);
                const checkDay = dayMap[checkDate.getDay()];
                
                if (calendar[checkDay]) {
                  return checkDate.toLocaleDateString('en-US', { 
                    weekday: 'short', 
                    month: 'short', 
                    day: 'numeric' 
                  });
                }
              }
              return 'No days selected';
            })()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeliveryCalendar;