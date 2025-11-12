import { useState, useEffect } from "react";
import apiClient from "../api/client";

export function OrganizationDirectory() {
  const [filters, setFilters] = useState<any>({});
  const [orgData, setOrgData] = useState<any>({ employees: [], filters: { departments: [], locations: [] } });

  useEffect(() => {
    let mounted = true;
    const fetch = async () => {
      try {
        const res = await apiClient.get('/employees/directory', { params: filters });
        if (!mounted) return;
        setOrgData(res.data ?? { employees: [], filters: { departments: [], locations: [] } });
      } catch (err) {
        console.error('Failed to load organization directory', err);
      }
    };
    fetch();
    return () => { mounted = false; };
  }, [filters]);

  const employees = orgData?.employees || [];
  const departments = orgData?.filters.departments || [];
  const locations = orgData?.filters.locations || [];

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Organization Directory</h2>
      <p className="text-gray-600 dark:text-gray-400">Employee directory will be displayed here...</p>
    </div>
  );
}
