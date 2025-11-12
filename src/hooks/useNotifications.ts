/**
 * Notifications Hook - Real-time notification management
 * Integrates with WebSocket and API for comprehensive notification handling
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useWebSocket } from './useWebSocket';
import { toast } from 'react-hot-toast';

export interface Notification {
    id: number;
    employee_id: number;
    notification_type: string;
    title: string;
    body: string;
    is_read: boolean;
    created_at: string;
    read_at?: string;
    metadata?: any;
    message_id?: number;
}

export interface NotificationStats {
    total: number;
    unread: number;
    read: number;
    by_type: Record<string, number>;
}

export function useNotifications() {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [stats, setStats] = useState<NotificationStats | null>(null);
    const [loading, setLoading] = useState(false);

    // WebSocket connection for real-time updates
    const { isConnected, lastMessage } = useWebSocket({
        autoConnect: true,
        onMessage: (message) => {
            handleWebSocketMessage(message);
        },
    });

    // Fetch initial notifications
    const fetchNotifications = useCallback(async (params?: {
        skip?: number;
        limit?: number;
        is_read?: boolean;
        notification_type?: string
    }) => {
        try {
            setLoading(true);
            const response = await api.inbox.getNotifications(params);
            const data = response.data;

            setNotifications(data.notifications || []);
            setUnreadCount(data.unread_count || 0);
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
            toast.error('Failed to load notifications');
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch notification stats
    const fetchStats = useCallback(async () => {
        try {
            const response = await api.inbox.getStats();
            setStats(response.data);
        } catch (error) {
            console.error('Failed to fetch notification stats:', error);
        }
    }, []);

    // Mark notification as read
    const markAsRead = useCallback(async (notificationId: number) => {
        try {
            await api.inbox.markAsRead(notificationId);

            // Update local state
            setNotifications(prev =>
                prev.map(notif =>
                    notif.id === notificationId
                        ? { ...notif, is_read: true, read_at: new Date().toISOString() }
                        : notif
                )
            );

            setUnreadCount(prev => Math.max(0, prev - 1));

        } catch (error) {
            console.error('Failed to mark notification as read:', error);
            toast.error('Failed to mark as read');
        }
    }, []);

    // Mark all as read
    const markAllAsRead = useCallback(async () => {
        try {
            const response = await api.inbox.markAllAsRead();
            const count = response.data.count || 0;

            // Update local state
            setNotifications(prev =>
                prev.map(notif => ({ ...notif, is_read: true, read_at: new Date().toISOString() }))
            );

            setUnreadCount(0);

            toast.success(`Marked ${count} notifications as read`);
        } catch (error) {
            console.error('Failed to mark all as read:', error);
            toast.error('Failed to mark all as read');
        }
    }, []);

    // Delete notification
    const deleteNotification = useCallback(async (notificationId: number) => {
        try {
            await api.inbox.deleteNotification(notificationId);

            // Update local state
            const deletedNotif = notifications.find(n => n.id === notificationId);
            setNotifications(prev => prev.filter(notif => notif.id !== notificationId));

            if (deletedNotif && !deletedNotif.is_read) {
                setUnreadCount(prev => Math.max(0, prev - 1));
            }

            toast.success('Notification deleted');
        } catch (error) {
            console.error('Failed to delete notification:', error);
            toast.error('Failed to delete notification');
        }
    }, [notifications]);

    // Handle WebSocket real-time messages
    const handleWebSocketMessage = useCallback((message: any) => {
        console.log('📨 Notification WebSocket message:', message);

        // Handle different message types
        switch (message.type) {
            case 'new_notification':
            case 'notification_created':
                // Add new notification to the list
                const newNotif: Notification = message.data;
                setNotifications(prev => [newNotif, ...prev]);

                if (!newNotif.is_read) {
                    setUnreadCount(prev => prev + 1);
                }

                // Show toast notification
                showToastNotification(newNotif);
                break;

            case 'notification_updated':
                // Update existing notification
                const updatedNotif: Notification = message.data;
                setNotifications(prev =>
                    prev.map(notif =>
                        notif.id === updatedNotif.id ? updatedNotif : notif
                    )
                );
                break;

            case 'notification_deleted':
                // Remove notification
                const deletedId = message.data.notification_id;
                setNotifications(prev => prev.filter(notif => notif.id !== deletedId));
                break;

            case 'task_assigned':
            case 'task_updated':
            case 'leave_approved':
            case 'leave_rejected':
            case 'message_received':
            case 'broadcast_received':
                // These are handled by creating notifications automatically
                // Just show a toast
                showToastForEvent(message.type, message.data);
                break;
        }
    }, []);

    // Show toast notification based on type
    const showToastNotification = useCallback((notification: Notification) => {
        const duration = 5000;

        switch (notification.notification_type) {
            case 'task_assigned':
                toast.success(`📋 ${notification.title}`, { duration });
                break;
            case 'leave_approved':
                toast.success(`✅ ${notification.title}`, { duration });
                break;
            case 'leave_rejected':
                toast.error(`❌ ${notification.title}`, { duration });
                break;
            case 'message_received':
                toast(`💬 ${notification.title}`, { duration, icon: '💬' });
                break;
            case 'broadcast':
                toast(`📢 ${notification.title}`, { duration, icon: '📢' });
                break;
            case 'approval_pending':
                toast(`⏳ ${notification.title}`, { duration, icon: '⏳' });
                break;
            default:
                toast(`🔔 ${notification.title}`, { duration });
        }
    }, []);

    // Show toast for real-time events
    const showToastForEvent = useCallback((eventType: string, data: any) => {
        switch (eventType) {
            case 'task_assigned':
                toast.success(`📋 New task assigned: ${data.title}`);
                break;
            case 'task_updated':
                toast(`📋 Task updated: ${data.title}`);
                break;
            case 'leave_approved':
                toast.success(`✅ Leave request approved`);
                break;
            case 'leave_rejected':
                toast.error(`❌ Leave request rejected`);
                break;
            case 'message_received':
                toast(`💬 New message from ${data.sender_name}`);
                break;
            case 'broadcast_received':
                toast(`📢 ${data.title}`);
                break;
        }
    }, []);

    // Load initial data
    useEffect(() => {
        fetchNotifications({ limit: 50 });
        fetchStats();
    }, [fetchNotifications, fetchStats]);

    // Refresh notifications periodically (fallback if WebSocket fails)
    useEffect(() => {
        if (!isConnected) {
            const interval = setInterval(() => {
                fetchNotifications({ limit: 50 });
            }, 30000); // Every 30 seconds

            return () => clearInterval(interval);
        }
    }, [isConnected, fetchNotifications]);

    return {
        notifications,
        unreadCount,
        stats,
        loading,
        isConnected,
        fetchNotifications,
        fetchStats,
        markAsRead,
        markAllAsRead,
        deleteNotification,
    };
}
