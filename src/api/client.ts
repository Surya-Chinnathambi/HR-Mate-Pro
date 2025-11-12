import axios, { AxiosResponse } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
export const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add token to requests
apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Handle auth errors
apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = '/';
        }
        return Promise.reject(error);
    }
);

// ============================================================================
// API ENDPOINTS - Organized by module
// ============================================================================

export const api = {
    // Auth
    auth: {
        login: (data: { username: string; password: string }) =>
            apiClient.post('/auth/token', data),
        me: () => apiClient.get('/auth/me'),
        logout: () => apiClient.post('/auth/logout'),
        changePassword: (data: { old_password: string; new_password: string }) =>
            apiClient.post('/auth/change-password', data),
    },

    // Inbox & Notifications
    inbox: {
        getNotifications: (params?: { skip?: number; limit?: number; is_read?: boolean; notification_type?: string }) =>
            apiClient.get('/inbox/notifications', { params }),
        markAsRead: (notificationId: number) =>
            apiClient.post(`/inbox/notifications/${notificationId}/read`),
        markAllAsRead: () =>
            apiClient.post('/inbox/notifications/mark-all-read'),
        deleteNotification: (notificationId: number) =>
            apiClient.delete(`/inbox/notifications/${notificationId}`),
        getStats: () =>
            apiClient.get('/inbox/stats'),
    },

    // Messages
    messages: {
        send: (data: { recipient_employee_id: number; subject: string; body: string; priority?: string }) =>
            apiClient.post('/messages/send', data),
        getInbox: (params?: { skip?: number; limit?: number }) =>
            apiClient.get('/messages/inbox', { params }),
        getDetails: (messageId: number) =>
            apiClient.get(`/messages/${messageId}`),
    },

    // Broadcasts
    broadcasts: {
        create: (data: {
            title: string;
            body: string;
            priority?: string;
            target_scope?: string;
            target_department_id?: number;
            target_role?: string;
        }) => apiClient.post('/broadcasts', data),
        getAll: (params?: { skip?: number; limit?: number; priority?: string }) =>
            apiClient.get('/broadcasts', { params }),
        getDetails: (broadcastId: number) =>
            apiClient.get(`/broadcasts/${broadcastId}`),
        delete: (broadcastId: number) =>
            apiClient.delete(`/broadcasts/${broadcastId}`),
    },

    // Team (Manager only)
    team: {
        getMembers: (params?: { skip?: number; limit?: number; status_filter?: string }) =>
            apiClient.get('/team/members', { params }),
        getWorkload: () =>
            apiClient.get('/team/workload'),
        getAttendance: (params?: { date_from?: string; date_to?: string }) =>
            apiClient.get('/team/attendance', { params }),
        getLeaves: (params?: { status_filter?: string }) =>
            apiClient.get('/team/leaves', { params }),
        getPerformanceSummary: () =>
            apiClient.get('/team/performance-summary'),
    },

    // Employees
    employees: {
        current: () => apiClient.get('/employees/current'),
        getById: (id: number) => apiClient.get(`/employees/${id}`),
        getAll: (params?: { skip?: number; limit?: number; department?: string; role?: string }) =>
            apiClient.get('/employees/', { params }),
        create: (data: any) => apiClient.post('/employees/', data),
        update: (id: number, data: any) => apiClient.put(`/employees/${id}`, data),
        delete: (id: number) => apiClient.delete(`/employees/${id}`),
    },

    // Attendance
    attendance: {
        checkIn: (data?: { location?: string; notes?: string }) =>
            apiClient.post('/attendance/check-in', data),
        checkOut: (data?: { notes?: string }) =>
            apiClient.post('/attendance/check-out', data),
        getRecords: (params?: { start_date?: string; end_date?: string; employee_id?: number }) =>
            apiClient.get('/attendance/records', { params }),
        getStats: (params?: { start_date?: string; end_date?: string }) =>
            apiClient.get('/attendance/stats', { params }),
        getTodayStatus: () =>
            apiClient.get('/attendance/today'),
    },

    // Leaves
    leaves: {
        create: (data: {
            leave_type: string;
            start_date: string;
            end_date: string;
            reason: string;
            days_count: number;
        }) => apiClient.post('/leaves/requests', data),
        getAll: (params?: { skip?: number; limit?: number; status?: string }) =>
            apiClient.get('/leaves/requests', { params }),
        getById: (id: number) => apiClient.get(`/leaves/requests/${id}`),
        approve: (id: number, data?: { comments?: string }) =>
            apiClient.post(`/leaves/requests/${id}/approve`, data),
        reject: (id: number, data: { comments: string }) =>
            apiClient.post(`/leaves/requests/${id}/reject`, data),
        cancel: (id: number) =>
            apiClient.post(`/leaves/requests/${id}/cancel`),
        getBalance: () =>
            apiClient.get('/leaves/balance'),
    },

    // Tasks
    tasks: {
        create: (data: {
            title: string;
            description?: string;
            assigned_to_employee_id?: number;
            priority?: string;
            due_date?: string;
        }) => apiClient.post('/tasks/', data),
        getAll: (params?: { skip?: number; limit?: number; status?: string; priority?: string }) =>
            apiClient.get('/tasks/', { params }),
        getById: (id: number) => apiClient.get(`/tasks/${id}`),
        update: (id: number, data: any) =>
            apiClient.put(`/tasks/${id}`, data),
        updateStatus: (id: number, status: string, data?: { comments?: string }) =>
            apiClient.post(`/tasks/${id}/status`, { status, ...data }),
        delete: (id: number) =>
            apiClient.delete(`/tasks/${id}`),
    },

    // Expenses
    expenses: {
        create: (data: any) => apiClient.post('/expenses/', data),
        getAll: (params?: { skip?: number; limit?: number; status?: string }) =>
            apiClient.get('/expenses/', { params }),
        getById: (id: number) => apiClient.get(`/expenses/${id}`),
        approve: (id: number, data?: { comments?: string }) =>
            apiClient.post(`/expenses/${id}/approve`, data),
        reject: (id: number, data: { comments: string }) =>
            apiClient.post(`/expenses/${id}/reject`, data),
    },

    // Performance
    performance: {
        getReviews: (params?: { skip?: number; limit?: number; status?: string }) =>
            apiClient.get('/performance/reviews', { params }),
        getById: (id: number) => apiClient.get(`/performance/reviews/${id}`),
        create: (data: any) => apiClient.post('/performance/reviews', data),
        update: (id: number, data: any) => apiClient.put(`/performance/reviews/${id}`, data),
        submitFeedback: (id: number, data: any) =>
            apiClient.post(`/performance/reviews/${id}/feedback`, data),
    },

    // Payroll
    payroll: {
        getPayslips: (params?: { skip?: number; limit?: number; year?: number; month?: number }) =>
            apiClient.get('/payroll/payslips', { params }),
        getById: (id: number) => apiClient.get(`/payroll/payslips/${id}`),
        downloadPdf: (id: number) => apiClient.get(`/payroll/payslips/${id}/pdf`, { responseType: 'blob' }),
    },

    // Analytics
    analytics: {
        getDashboard: () => apiClient.get('/analytics/dashboard'),
        getAttendanceAnalytics: (params?: { start_date?: string; end_date?: string }) =>
            apiClient.get('/analytics/attendance', { params }),
        getLeaveAnalytics: (params?: { start_date?: string; end_date?: string }) =>
            apiClient.get('/analytics/leaves', { params }),
        getPerformanceAnalytics: () =>
            apiClient.get('/analytics/performance'),
        getWorkloadAnalytics: () =>
            apiClient.get('/analytics/workload'),
    },

    // Policies
    policies: {
        getAll: () => apiClient.get('/policies/'),
        getById: (id: number) => apiClient.get(`/policies/${id}`),
        create: (data: any) => apiClient.post('/policies/', data),
        update: (id: number, data: any) => apiClient.put(`/policies/${id}`, data),
        delete: (id: number) => apiClient.delete(`/policies/${id}`),
    },

    // Helpdesk
    helpdesk: {
        createTicket: (data: { title: string; description: string; category?: string; priority?: string }) =>
            apiClient.post('/helpdesk/tickets', data),
        getTickets: (params?: { skip?: number; limit?: number; status?: string }) =>
            apiClient.get('/helpdesk/tickets', { params }),
        getById: (id: number) => apiClient.get(`/helpdesk/tickets/${id}`),
        update: (id: number, data: any) => apiClient.put(`/helpdesk/tickets/${id}`, data),
        addComment: (id: number, comment: string) =>
            apiClient.post(`/helpdesk/tickets/${id}/comments`, { comment }),
    },

    // Real-time (legacy endpoint, use WebSocket instead)
    realtime: {
        getNotifications: () => apiClient.get('/realtime/notifications'),
    },
};

export default apiClient;
