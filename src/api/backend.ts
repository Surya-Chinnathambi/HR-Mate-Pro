import apiClient from './client';

// Central backend API helpers matching FastAPI endpoints.
// Functions return the raw data from the backend (snake_case fields).

export async function getCurrentEmployee() {
    const res = await apiClient.get('/employees/current');
    return res.data;
}

export async function getNotifications() {
    const res = await apiClient.get('/realtime/notifications');
    return res.data;
}

export async function attendanceCheckIn(employee_id: number) {
    const res = await apiClient.post('/attendance/check-in', null, { params: { employee_id } });
    return res.data;
}

export async function attendanceCheckOut(employee_id: number) {
    const res = await apiClient.post('/attendance/check-out', null, { params: { employee_id } });
    return res.data;
}

export async function getTodayAttendance(employee_id: number) {
    const res = await apiClient.get('/attendance/today', { params: { employee_id } });
    return res.data;
}

export async function getAttendanceStats(employee_id: number, month: number, year: number) {
    const res = await apiClient.get('/attendance/stats', { params: { employee_id, month: String(month), year } });
    return res.data;
}

export async function getDashboardSummary() {
    const res = await apiClient.get('/realtime/dashboard-summary');
    return res.data;
}

// Add more helpers as needed (leaves, payroll, employees directory, etc.)

export default {
    getCurrentEmployee,
    getNotifications,
    attendanceCheckIn,
    attendanceCheckOut,
    getTodayAttendance,
    getAttendanceStats,
    getDashboardSummary,
};
