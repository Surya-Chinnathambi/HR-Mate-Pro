import React, { useEffect, useState } from 'react';
import apiClient from '../api/client';

export function OrganizationTreeModule() {
  const [orgTree, setOrgTree] = useState<{ department: string; count: number; employees: any[] }[]>([]);

  useEffect(() => {
    let mounted = true;
    const fetch = async () => {
      try {
        const res = await apiClient.get('/employees/organization-tree');
        if (!mounted) return;
        setOrgTree(res.data ?? []);
      } catch (err) {
        console.error('Failed to load organization tree', err);
      }
    };
    fetch();
    return () => { mounted = false; };
  }, []);

  return (
    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Organization Tree</h2>
      <div className="space-y-4">
        {orgTree.map((dept) => (
          <div key={dept.department}>
            <h3 className="font-semibold text-lg text-gray-900 dark:text-white">{dept.department} ({dept.count})</h3>
            <ul className="pl-4 mt-2 space-y-1 border-l-2 border-gray-200 dark:border-gray-700">
              {dept.employees.map((emp: any) => (
                <li key={emp._id} className="text-gray-700 dark:text-gray-300">{emp.firstName} {emp.lastName} - {emp.designation}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
