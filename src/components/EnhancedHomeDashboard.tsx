/**
 * Enhanced Dashboard with Real-time Data
 * Main home dashboard showing live stats, recent activities, and quick actions
 */
import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import {
    Home, Clock, Calendar, TrendingUp, Users, CheckCircle, AlertCircle,
    Activity, ArrowUp, ArrowDown, Zap, BarChart3
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface DashboardStats {
    attendance_today?: { status: string; check_in_time?: string; hours_worked?: number };
    pending_tasks: number;
    pending_leaves: number;
    unread_messages: number;
    upcoming_reviews: number;
}

interface RecentActivity {
    id: number;
    type: string;
    title: string;
    description: string;
    timestamp: string;
    icon: any;
    color: string;
}

export function EnhancedHomeDashboard({ employee }: { employee: any }) {
    const [stats, setStats] = useState<DashboardStats>({
        pending_tasks: 0,
        pending_leaves: 0,
        unread_messages: 0,
        upcoming_reviews: 0,
    });
    const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([]);
    const [loading, setLoading] = useState(true);

    const { isConnected, lastMessage } = useWebSocket({
        onMessage: handleWebSocketMessage,
    });

    // Load initial dashboard data
    useEffect(() => {
        loadDashboardData();
    }, []);

    async function loadDashboardData() {
        try {
            setLoading(true);

            const [attendanceRes, tasksRes, leavesRes, messagesRes, notificationsRes] = await Promise.all([
                api.attendance.getTodayStatus().catch(() => ({ data: null })),
                api.tasks.getAll({ status: 'pending' }).catch(() => ({ data: [] })),
                api.leaves.getAll({ status: 'pending' }).catch(() => ({ data: [] })),
                api.messages.getInbox({ limit: 10 }).catch(() => ({ data: { messages: [] } })),
                api.inbox.getNotifications({ limit: 20 }).catch(() => ({ data: { notifications: [] } })),
            ]);

            setStats({
                attendance_today: attendanceRes.data,
                pending_tasks: Array.isArray(tasksRes.data) ? tasksRes.data.length : 0,
                pending_leaves: Array.isArray(leavesRes.data) ? leavesRes.data.length : 0,
                unread_messages: messagesRes.data.messages?.filter((m: any) => !m.is_read).length || 0,
                upcoming_reviews: 0,
            });

            // Convert notifications to recent activities
            const activities: RecentActivity[] = notificationsRes.data.notifications?.slice(0, 5).map((notif: any) => ({
                id: notif.id,
                type: notif.notification_type,
                title: notif.title,
                description: notif.body,
                timestamp: notif.created_at,
                icon: getActivityIcon(notif.notification_type),
                color: getActivityColor(notif.notification_type),
            })) || [];

            setRecentActivities(activities);

        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        } finally {
            setLoading(false);
        }
    }

    function handleWebSocketMessage(message: any) {
        console.log('Dashboard received WebSocket message:', message);

        // Update stats based on message type
        switch (message.type) {
            case 'task_assigned':
                setStats(prev => ({ ...prev, pending_tasks: prev.pending_tasks + 1 }));
                addRecentActivity({
                    id: Date.now(),
                    type: 'task',
                    title: 'New Task Assigned',
                    description: message.data.title,
                    timestamp: new Date().toISOString(),
                    icon: CheckCircle,
                    color: 'blue',
                });
                break;

            case 'leave_approved':
            case 'leave_rejected':
                setStats(prev => ({ ...prev, pending_leaves: Math.max(0, prev.pending_leaves - 1) }));
                addRecentActivity({
                    id: Date.now(),
                    type: 'leave',
                    title: message.type === 'leave_approved' ? 'Leave Approved' : 'Leave Rejected',
                    description: message.data.comments || '',
                    timestamp: new Date().toISOString(),
                    icon: Calendar,
                    color: message.type === 'leave_approved' ? 'green' : 'red',
                });
                break;

            case 'message_received':
                setStats(prev => ({ ...prev, unread_messages: prev.unread_messages + 1 }));
                break;
        }
    }

    function addRecentActivity(activity: RecentActivity) {
        setRecentActivities(prev => [activity, ...prev.slice(0, 9)]);
    }

    function getActivityIcon(type: string) {
        switch (type) {
            case 'task_assigned':
            case 'task_updated':
                return CheckCircle;
            case 'leave_approved':
            case 'leave_rejected':
                return Calendar;
            case 'message_received':
                return Activity;
            case 'broadcast':
                return AlertCircle;
            default:
                return Zap;
        }
    }

    function getActivityColor(type: string) {
        switch (type) {
            case 'task_assigned':
                return 'blue';
            case 'task_updated':
                return 'indigo';
            case 'leave_approved':
                return 'green';
            case 'leave_rejected':
                return 'red';
            case 'message_received':
                return 'purple';
            case 'broadcast':
                return 'orange';
            default:
                return 'gray';
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            {/* Welcome Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">
                        Welcome back, {employee?.first_name || 'User'}!
                    </h1>
                    <p className="text-gray-500 mt-1">
                        {new Date().toLocaleDateString('en-US', {
                            weekday: 'long',
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                        })}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${isConnected ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                        }`}>
                        <span className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-yellow-500'
                            }`}></span>
                        {isConnected ? 'Live' : 'Connecting...'}
                    </span>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Attendance Status */}
                <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Today's Status</p>
                            <h3 className="text-2xl font-bold text-gray-900 mt-2">
                                {stats.attendance_today?.status === 'present' ? 'Present' : 'Not Checked In'}
                            </h3>
                            {stats.attendance_today?.check_in_time && (
                                <p className="text-sm text-gray-500 mt-1">
                                    Since {new Date(stats.attendance_today.check_in_time).toLocaleTimeString()}
                                </p>
                            )}
                        </div>
                        <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                            <Clock className="w-6 h-6 text-green-600" />
                        </div>
                    </div>
                </div>

                {/* Pending Tasks */}
                <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Pending Tasks</p>
                            <h3 className="text-2xl font-bold text-gray-900 mt-2">{stats.pending_tasks}</h3>
                            <p className="text-sm text-gray-500 mt-1">Tasks to complete</p>
                        </div>
                        <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                            <CheckCircle className="w-6 h-6 text-blue-600" />
                        </div>
                    </div>
                </div>

                {/* Pending Leaves */}
                <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Leave Requests</p>
                            <h3 className="text-2xl font-bold text-gray-900 mt-2">{stats.pending_leaves}</h3>
                            <p className="text-sm text-gray-500 mt-1">Pending approval</p>
                        </div>
                        <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                            <Calendar className="w-6 h-6 text-purple-600" />
                        </div>
                    </div>
                </div>

                {/* Unread Messages */}
                <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Unread Messages</p>
                            <h3 className="text-2xl font-bold text-gray-900 mt-2">{stats.unread_messages}</h3>
                            <p className="text-sm text-gray-500 mt-1">New messages</p>
                        </div>
                        <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                            <Activity className="w-6 h-6 text-orange-600" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Recent Activities */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-6 border-b border-gray-200">
                    <h2 className="text-xl font-semibold text-gray-900">Recent Activities</h2>
                </div>
                <div className="divide-y divide-gray-100">
                    {recentActivities.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                            No recent activities
                        </div>
                    ) : (
                        recentActivities.map((activity) => {
                            const Icon = activity.icon;
                            return (
                                <div key={activity.id} className="p-4 hover:bg-gray-50 transition-colors">
                                    <div className="flex items-start gap-4">
                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-${activity.color}-100`}>
                                            <Icon className={`w-5 h-5 text-${activity.color}-600`} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                                            <p className="text-sm text-gray-600 mt-1">{activity.description}</p>
                                            <p className="text-xs text-gray-500 mt-2">
                                                {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <button className="bg-white rounded-lg shadow-sm p-4 border border-gray-200 hover:shadow-md transition-shadow text-left">
                    <Clock className="w-8 h-8 text-green-600 mb-2" />
                    <h3 className="font-medium text-gray-900">Check In/Out</h3>
                    <p className="text-sm text-gray-500 mt-1">Mark attendance</p>
                </button>
                <button className="bg-white rounded-lg shadow-sm p-4 border border-gray-200 hover:shadow-md transition-shadow text-left">
                    <Calendar className="w-8 h-8 text-purple-600 mb-2" />
                    <h3 className="font-medium text-gray-900">Apply Leave</h3>
                    <p className="text-sm text-gray-500 mt-1">Request time off</p>
                </button>
                <button className="bg-white rounded-lg shadow-sm p-4 border border-gray-200 hover:shadow-md transition-shadow text-left">
                    <CheckCircle className="w-8 h-8 text-blue-600 mb-2" />
                    <h3 className="font-medium text-gray-900">My Tasks</h3>
                    <p className="text-sm text-gray-500 mt-1">View assignments</p>
                </button>
                <button className="bg-white rounded-lg shadow-sm p-4 border border-gray-200 hover:shadow-md transition-shadow text-left">
                    <TrendingUp className="w-8 h-8 text-orange-600 mb-2" />
                    <h3 className="font-medium text-gray-900">Performance</h3>
                    <p className="text-sm text-gray-500 mt-1">View reviews</p>
                </button>
            </div>
        </div>
    );
}
