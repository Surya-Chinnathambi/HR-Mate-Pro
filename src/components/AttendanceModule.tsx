import { useState, useEffect } from "react";
import apiClient from "../api/client";

interface AttendanceModuleProps {
  employee?: any;
}

export function AttendanceModule({ employee }: AttendanceModuleProps) {
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [todayAttendance, setTodayAttendance] = useState<any | null>(null);

  useEffect(() => {
    if (!employee) {
      setTodayAttendance(null);
      return;
    }

    const fetchToday = async () => {
      try {
        const res = await apiClient.get(`/attendance/today`, { params: { employee_id: employee.id } });
        setTodayAttendance(res.data ?? null);
      } catch (err: any) {
        if (err.response?.status === 404) {
          setTodayAttendance(null);
        } else {
          console.error("Failed to fetch today's attendance", err);
        }
      }
    };

    fetchToday();
  }, [employee]);

  const handleClockIn = async () => {
    if (!employee) return;
    try {
      await apiClient.post(`/attendance/check-in`, null, { params: { employee_id: employee.id } });
      // refresh
      const res = await apiClient.get(`/attendance/today`, { params: { employee_id: employee.id } });
      setTodayAttendance(res.data ?? null);
    } catch (error) {
      console.error(error);
    }
  };

  const handleClockOut = async () => {
    if (!employee) return;
    try {
      await apiClient.post(`/attendance/check-out`, null, { params: { employee_id: employee.id } });
      const res = await apiClient.get(`/attendance/today`, { params: { employee_id: employee.id } });
      setTodayAttendance(res.data ?? null);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">Today's Attendance</h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-600 dark:text-gray-400">Status: <span className="font-semibold text-blue-600 dark:text-blue-400">{todayAttendance?.status || "Not Clocked In"}</span></p>
            <p className="text-gray-600 dark:text-gray-400">Clock In: <span className="font-semibold text-gray-900 dark:text-white">{todayAttendance?.checkIn ?? "--:--"}</span></p>
            <p className="text-gray-600 dark:text-gray-400">Clock Out: <span className="font-semibold text-gray-900 dark:text-white">{todayAttendance?.checkOut ?? "--:--"}</span></p>
          </div>
          <div className="flex gap-4">
            <button onClick={handleClockIn} disabled={!!todayAttendance?.checkIn} className="px-4 py-2 bg-green-500 text-white rounded-lg disabled:bg-gray-400 dark:disabled:bg-gray-600 hover:bg-green-600 transition-colors">Clock In</button>
            <button onClick={handleClockOut} disabled={!todayAttendance?.checkIn || !!todayAttendance?.checkOut} className="px-4 py-2 bg-red-500 text-white rounded-lg disabled:bg-gray-400 dark:disabled:bg-gray-600 hover:bg-red-600 transition-colors">Clock Out</button>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">Monthly Stats</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="bg-green-100 dark:bg-green-900/30 p-4 rounded-lg border border-green-200 dark:border-green-800">
            <p className="text-2xl font-bold text-green-700 dark:text-green-400">22</p>
            <p className="text-sm text-green-600 dark:text-green-500">Present</p>
          </div>
          <div className="bg-red-100 dark:bg-red-900/30 p-4 rounded-lg border border-red-200 dark:border-red-800">
            <p className="text-2xl font-bold text-red-700 dark:text-red-400">0</p>
            <p className="text-sm text-red-600 dark:text-red-500">Absent</p>
          </div>
          <div className="bg-yellow-100 dark:bg-yellow-900/30 p-4 rounded-lg border border-yellow-200 dark:border-yellow-800">
            <p className="text-2xl font-bold text-yellow-700 dark:text-yellow-400">0</p>
            <p className="text-sm text-yellow-600 dark:text-yellow-500">Late</p>
          </div>
          <div className="bg-blue-100 dark:bg-blue-900/30 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-2xl font-bold text-blue-700 dark:text-blue-400">8.0h</p>
            <p className="text-sm text-blue-600 dark:text-blue-500">Avg. Hours</p>
          </div>
        </div>
      </div>
    </div>
  );
}
