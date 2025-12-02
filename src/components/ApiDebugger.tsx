import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

/**
 * API Data Debugger Component
 * 
 * This component tests all API endpoints and displays the actual data structure
 * being returned. Use this to debug frontend data display issues.
 * 
 * Usage: Add <ApiDebugger /> to your dashboard
 */

export const ApiDebugger: React.FC = () => {
    const [endpoints, setEndpoints] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState<string | null>(null);

    useEffect(() => {
        testAllEndpoints();
    }, []);

    const testAllEndpoints = async () => {
        setLoading(true);
        const results: any[] = [];

        // Test each endpoint
        const tests = [
            { name: 'Inbox Notifications', test: () => api.inbox.getNotifications() },
            { name: 'Inbox Stats', test: () => api.inbox.getStats() },
            { name: 'Attendance Today', test: () => api.attendance.getTodayStatus() },
            { name: 'Attendance Stats', test: () => api.attendance.getStats() },
            { name: 'Leave Balance', test: () => api.leaves.getBalance() },
            { name: 'Leave Applications', test: () => api.leaves.getAll() },
            { name: 'Team Members', test: () => api.team.getMembers() },
            { name: 'Employees Current', test: () => api.employees.current() },
            { name: 'Employees All', test: () => api.employees.getAll({ limit: 10 }) },
            { name: 'Analytics Overview', test: () => api.analytics.getOverview() },
            { name: 'Policies', test: () => api.policies.getAll() },
            { name: 'Organization Departments', test: () => api.organization.getDepartments() },
        ];

        for (const { name, test } of tests) {
            try {
                const startTime = Date.now();
                const response = await test();
                const endTime = Date.now();

                results.push({
                    name,
                    status: 'success',
                    statusCode: response.status,
                    responseTime: endTime - startTime,
                    dataStructure: getDataStructure(response.data),
                    sampleData: JSON.stringify(response.data, null, 2).substring(0, 500),
                    fullData: response.data,
                });
            } catch (error: any) {
                results.push({
                    name,
                    status: 'error',
                    statusCode: error.response?.status || 'Network Error',
                    error: error.response?.data?.detail || error.message,
                });
            }
        }

        setEndpoints(results);
        setLoading(false);
    };

    const getDataStructure = (data: any): string => {
        if (Array.isArray(data)) {
            return `Array[${data.length}] of ${data.length > 0 ? typeof data[0] : 'unknown'}`;
        }
        if (typeof data === 'object' && data !== null) {
            const keys = Object.keys(data);
            return `Object {${keys.slice(0, 5).join(', ')}${keys.length > 5 ? '...' : ''}}`;
        }
        return typeof data;
    };

    if (loading) {
        return (
            <div className="p-6 bg-white rounded-lg shadow">
                <div className="animate-pulse">
                    <h2 className="text-xl font-bold mb-4">Testing API Endpoints...</h2>
                    <div className="space-y-2">
                        {[1, 2, 3, 4, 5].map(i => (
                            <div key={i} className="h-12 bg-gray-200 rounded"></div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    const successCount = endpoints.filter(e => e.status === 'success').length;
    const errorCount = endpoints.filter(e => e.status === 'error').length;

    return (
        <div className="p-6 bg-white rounded-lg shadow max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">API Data Debugger</h2>
                <div className="flex gap-4">
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                        ✓ {successCount} Success
                    </span>
                    <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">
                        ✗ {errorCount} Errors
                    </span>
                    <button
                        onClick={testAllEndpoints}
                        className="px-4 py-1 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
                    >
                        Retest All
                    </button>
                </div>
            </div>

            <div className="space-y-3">
                {endpoints.map((endpoint, index) => (
                    <div
                        key={index}
                        className={`border rounded-lg ${endpoint.status === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
                            }`}
                    >
                        <div
                            className="p-4 cursor-pointer flex items-center justify-between"
                            onClick={() => setExpanded(expanded === endpoint.name ? null : endpoint.name)}
                        >
                            <div className="flex items-center gap-3">
                                <span className={`text-2xl ${endpoint.status === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                                    {endpoint.status === 'success' ? '✓' : '✗'}
                                </span>
                                <div>
                                    <h3 className="font-semibold text-gray-900">{endpoint.name}</h3>
                                    <p className="text-sm text-gray-600">
                                        Status: {endpoint.statusCode}
                                        {endpoint.responseTime && ` | ${endpoint.responseTime}ms`}
                                        {endpoint.dataStructure && ` | ${endpoint.dataStructure}`}
                                    </p>
                                </div>
                            </div>
                            <svg
                                className={`w-5 h-5 transform transition-transform ${expanded === endpoint.name ? 'rotate-180' : ''
                                    }`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </div>

                        {expanded === endpoint.name && (
                            <div className="border-t p-4 bg-white">
                                {endpoint.status === 'success' ? (
                                    <div className="space-y-3">
                                        <div>
                                            <h4 className="font-medium text-gray-700 mb-2">Data Preview:</h4>
                                            <pre className="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto">
                                                {endpoint.sampleData}...
                                            </pre>
                                        </div>
                                        <div>
                                            <h4 className="font-medium text-gray-700 mb-2">Full Data:</h4>
                                            <pre className="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto max-h-96">
                                                {JSON.stringify(endpoint.fullData, null, 2)}
                                            </pre>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-red-600">
                                        <h4 className="font-medium mb-2">Error:</h4>
                                        <pre className="bg-red-50 p-3 rounded text-sm">{endpoint.error}</pre>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="font-semibold text-blue-900 mb-2">How to Use This Debugger:</h3>
                <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                    <li>Green checkmarks indicate successful API calls with data</li>
                    <li>Red X marks indicate API errors or failures</li>
                    <li>Click on any endpoint to see the actual data structure being returned</li>
                    <li>Compare the data structure with what your component expects</li>
                    <li>Check if arrays are empty or if expected fields are missing</li>
                </ul>
            </div>
        </div>
    );
};

export default ApiDebugger;
