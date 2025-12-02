import React from 'react';
import ApiDebugger from './components/ApiDebugger';

/**
 * Debug Page for Testing API Data
 * 
 * To use this:
 * 1. Import this component in App.tsx
 * 2. Add a route: <Route path="/debug" element={<DebugPage />} />
 * 3. Navigate to http://localhost:5173/debug
 * 
 * This will show you exactly what data each API endpoint is returning
 * and help identify any frontend display issues.
 */

function DebugPage() {
    return (
        <div className="min-h-screen bg-gray-100 py-8">
            <div className="max-w-7xl mx-auto">
                <div className="mb-8 text-center">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">
                        HRMS API Data Debugger
                    </h1>
                    <p className="text-gray-600">
                        This page shows the actual data being returned from each API endpoint.
                        Use this to debug frontend display issues.
                    </p>
                </div>

                <ApiDebugger />

                <div className="mt-8 bg-white rounded-lg shadow p-6">
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Common Issues & Solutions</h2>

                    <div className="space-y-4">
                        <div className="border-l-4 border-yellow-400 bg-yellow-50 p-4">
                            <h3 className="font-semibold text-yellow-900">Empty Arrays</h3>
                            <p className="text-yellow-800 text-sm mt-1">
                                If you see empty arrays ([]), it means the database has no data for that endpoint.
                                Solution: Generate sample data using the backend scripts like generate_25_employees_complete.py
                            </p>
                        </div>

                        <div className="border-l-4 border-blue-400 bg-blue-50 p-4">
                            <h3 className="font-semibold text-blue-900">Wrong Data Structure</h3>
                            <p className="text-blue-800 text-sm mt-1">
                                If the data structure doesn't match what your component expects, check:
                                - Frontend is using response.data (Axios response format)
                                - Backend is returning the correct field names
                                - Component is accessing the correct nested properties
                            </p>
                        </div>

                        <div className="border-l-4 border-red-400 bg-red-50 p-4">
                            <h3 className="font-semibold text-red-900">API Errors (500, 422, 404)</h3>
                            <p className="text-red-800 text-sm mt-1">
                                500: Internal server error - Check backend logs<br />
                                422: Validation error - Check request parameters<br />
                                404: Endpoint not found - Check if route is registered in backend
                            </p>
                        </div>

                        <div className="border-l-4 border-green-400 bg-green-50 p-4">
                            <h3 className="font-semibold text-green-900">Success but No Display</h3>
                            <p className="text-green-800 text-sm mt-1">
                                If API returns success but data doesn't display:
                                - Check component's console.log statements
                                - Verify component is mapping over the correct array
                                - Check if conditional rendering is hiding the data
                                - Verify the component is actually using the fetched data in its render
                            </p>
                        </div>
                    </div>
                </div>

                <div className="mt-8 bg-white rounded-lg shadow p-6">
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Quick Fixes for Common Problems</h2>

                    <div className="grid md:grid-cols-2 gap-4">
                        <div className="bg-gray-50 p-4 rounded">
                            <h3 className="font-semibold mb-2">Frontend shows "0" for all stats</h3>
                            <p className="text-sm text-gray-700">
                                Usually means API is returning empty data. Generate sample data in backend:
                            </p>
                            <code className="block mt-2 bg-gray-800 text-green-400 p-2 rounded text-xs">
                                cd hrms_backend<br />
                                python generate_25_employees_complete.py
                            </code>
                        </div>

                        <div className="bg-gray-50 p-4 rounded">
                            <h3 className="font-semibold mb-2">Tables/Lists show no items</h3>
                            <p className="text-sm text-gray-700">
                                Check if component is correctly accessing array:
                            </p>
                            <code className="block mt-2 bg-gray-800 text-green-400 p-2 rounded text-xs">
                                {`// Correct
response.data.map(item => ...)

// OR if wrapped
response.data.items.map(item => ...)`}
                            </code>
                        </div>

                        <div className="bg-gray-50 p-4 rounded">
                            <h3 className="font-semibold mb-2">Undefined property errors</h3>
                            <p className="text-sm text-gray-700">
                                Add optional chaining and default values:
                            </p>
                            <code className="block mt-2 bg-gray-800 text-green-400 p-2 rounded text-xs">
                                {`employee?.first_name || 'N/A'
data?.items || []
stats?.total ?? 0`}
                            </code>
                        </div>

                        <div className="bg-gray-50 p-4 rounded">
                            <h3 className="font-semibold mb-2">Date formatting issues</h3>
                            <p className="text-sm text-gray-700">
                                Backend returns ISO strings, format them properly:
                            </p>
                            <code className="block mt-2 bg-gray-800 text-green-400 p-2 rounded text-xs">
                                {`new Date(item.created_at)
  .toLocaleDateString()`}
                            </code>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default DebugPage;
