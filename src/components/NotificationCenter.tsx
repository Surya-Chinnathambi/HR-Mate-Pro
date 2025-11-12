import React, { useEffect, useState } from 'react';
import {
    Badge,
    IconButton,
    Menu,
    MenuItem,
    ListItemText,
    ListItemAvatar,
    Avatar,
    Typography,
    Divider,
    Box,
    Chip,
    Button,
    Alert,
} from '@mui/material';
import {
    Notifications as NotificationsIcon,
    Circle as CircleIcon,
    CheckCircle as CheckCircleIcon,
    Close as CloseIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import {
    useWebSocket,
    NewNotificationEvent,
    ApprovalUpdatedEvent,
    TaskUpdatedEvent,
    WorkloadAlertEvent,
} from '../hooks/useWebSocket';
import apiClient from '../api/client';

// ============================================================================
// TYPES
// ============================================================================

interface Notification {
    id: number;
    title: string;
    message: string;
    type: string;
    priority: string;
    is_read: boolean;
    created_at: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

const NotificationCenter: React.FC = () => {
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);

    const { isConnected, isAuthenticated, on } = useWebSocket({
        autoConnect: true,
    });

    // ============================================================================
    // DATA FETCHING
    // ============================================================================

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get('/notifications', {
                params: { limit: 20 },
            });
            setNotifications(response.data || []);
            setUnreadCount(response.data?.filter((n: Notification) => !n.is_read).length || 0);
        } catch (error) {
            console.error('Error fetching notifications:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchNotifications();
    }, []);

    // ============================================================================
    // WEBSOCKET EVENT HANDLERS
    // ============================================================================

    useEffect(() => {
        if (!isAuthenticated) return;

        // Handle new notification event
        const unsubscribeNotification = on('new_notification', (data: NewNotificationEvent) => {
            console.log('📬 New notification received:', data);

            const newNotification: Notification = {
                id: data.notification_id,
                title: data.title,
                message: data.message,
                type: data.type,
                priority: data.priority,
                is_read: false,
                created_at: data.created_at,
            };

            setNotifications((prev) => [newNotification, ...prev]);
            setUnreadCount((prev) => prev + 1);

            // Show browser notification if permitted
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification(data.title, {
                    body: data.message,
                    icon: '/logo.png',
                });
            }
        });

        // Handle approval update event
        const unsubscribeApproval = on('approval_updated', (data: ApprovalUpdatedEvent) => {
            console.log('✅ Approval updated:', data);

            const notification: Notification = {
                id: Date.now(),
                title: 'Approval Updated',
                message: `Your approval request has been ${data.status} by ${data.approver_name}`,
                type: 'approval',
                priority: 'high',
                is_read: false,
                created_at: new Date().toISOString(),
            };

            setNotifications((prev) => [notification, ...prev]);
            setUnreadCount((prev) => prev + 1);
        });

        // Handle task update event
        const unsubscribeTask = on('task_updated', (data: TaskUpdatedEvent) => {
            console.log('📋 Task updated:', data);

            const notification: Notification = {
                id: Date.now(),
                title: 'Task Updated',
                message: `"${data.title}" status changed to ${data.status}`,
                type: 'task',
                priority: 'medium',
                is_read: false,
                created_at: new Date().toISOString(),
            };

            setNotifications((prev) => [notification, ...prev]);
            setUnreadCount((prev) => prev + 1);
        });

        // Handle workload alert event
        const unsubscribeWorkload = on('workload_alert', (data: WorkloadAlertEvent) => {
            console.log('⚠️ Workload alert:', data);

            const notification: Notification = {
                id: Date.now(),
                title: 'Workload Alert',
                message: data.message,
                type: 'alert',
                priority: 'urgent',
                is_read: false,
                created_at: new Date().toISOString(),
            };

            setNotifications((prev) => [notification, ...prev]);
            setUnreadCount((prev) => prev + 1);
        });

        // Cleanup
        return () => {
            unsubscribeNotification();
            unsubscribeApproval();
            unsubscribeTask();
            unsubscribeWorkload();
        };
    }, [isAuthenticated, on]);

    // Request browser notification permission
    useEffect(() => {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }, []);

    // ============================================================================
    // HANDLERS
    // ============================================================================

    const handleOpen = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorEl(event.currentTarget);
    };

    const handleClose = () => {
        setAnchorEl(null);
    };

    const handleMarkAsRead = async (notificationId: number) => {
        try {
            await apiClient.patch(`/notifications/${notificationId}/read`);
            setNotifications((prev) =>
                prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
            );
            setUnreadCount((prev) => Math.max(0, prev - 1));
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    };

    const handleMarkAllAsRead = async () => {
        try {
            await apiClient.post('/notifications/mark-all-read');
            setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
            setUnreadCount(0);
        } catch (error) {
            console.error('Error marking all as read:', error);
        }
    };

    const handleClearAll = () => {
        setNotifications([]);
        setUnreadCount(0);
        handleClose();
    };

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================

    const getPriorityColor = (priority: string): 'error' | 'warning' | 'info' | 'default' => {
        switch (priority) {
            case 'urgent':
                return 'error';
            case 'high':
                return 'warning';
            case 'medium':
                return 'info';
            default:
                return 'default';
        }
    };

    const getTypeIcon = (type: string): string => {
        const icons: Record<string, string> = {
            approval: '✅',
            task: '📋',
            alert: '⚠️',
            info: 'ℹ️',
            success: '🎉',
            warning: '⚠️',
            error: '❌',
        };
        return icons[type] || '📬';
    };

    // ============================================================================
    // RENDER
    // ============================================================================

    const open = Boolean(anchorEl);

    return (
        <>
            {/* Connection Status */}
            {!isConnected && (
                <Chip
                    label="Offline"
                    size="small"
                    color="error"
                    sx={{ mr: 1 }}
                />
            )}

            {/* Notification Bell */}
            <IconButton color="inherit" onClick={handleOpen}>
                <Badge badgeContent={unreadCount} color="error">
                    <NotificationsIcon />
                </Badge>
            </IconButton>

            {/* Notification Menu */}
            <Menu
                anchorEl={anchorEl}
                open={open}
                onClose={handleClose}
                PaperProps={{
                    sx: {
                        maxHeight: 500,
                        width: 400,
                        maxWidth: '100%',
                    },
                }}
                transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            >
                {/* Header */}
                <Box sx={{ p: 2, pb: 1 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="h6" fontWeight="bold">
                            Notifications
                        </Typography>
                        <IconButton size="small" onClick={handleClose}>
                            <CloseIcon />
                        </IconButton>
                    </Box>
                    {unreadCount > 0 && (
                        <Box display="flex" gap={1} mt={1}>
                            <Button size="small" onClick={handleMarkAllAsRead}>
                                Mark all as read
                            </Button>
                            <Button size="small" onClick={handleClearAll} color="error">
                                Clear all
                            </Button>
                        </Box>
                    )}
                </Box>

                <Divider />

                {/* WebSocket Status */}
                {!isConnected && (
                    <Alert severity="warning" sx={{ m: 1 }}>
                        Real-time updates disconnected. Reconnecting...
                    </Alert>
                )}

                {/* Notification List */}
                {loading ? (
                    <Box sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="body2" color="text.secondary">
                            Loading...
                        </Typography>
                    </Box>
                ) : notifications.length === 0 ? (
                    <Box sx={{ p: 4, textAlign: 'center' }}>
                        <NotificationsIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
                        <Typography variant="body2" color="text.secondary">
                            No notifications
                        </Typography>
                    </Box>
                ) : (
                    notifications.slice(0, 10).map((notification, index) => (
                        <React.Fragment key={notification.id}>
                            {index > 0 && <Divider />}
                            <MenuItem
                                sx={{
                                    py: 1.5,
                                    px: 2,
                                    bgcolor: notification.is_read ? 'transparent' : 'action.hover',
                                    display: 'block',
                                }}
                                onClick={() => !notification.is_read && handleMarkAsRead(notification.id)}
                            >
                                <Box display="flex" gap={1.5} alignItems="start">
                                    <Avatar sx={{ width: 36, height: 36, bgcolor: 'primary.main' }}>
                                        {getTypeIcon(notification.type)}
                                    </Avatar>
                                    <Box flex={1}>
                                        <Box display="flex" justifyContent="space-between" alignItems="start" mb={0.5}>
                                            <Typography variant="subtitle2" fontWeight="bold">
                                                {notification.title}
                                            </Typography>
                                            {!notification.is_read && (
                                                <CircleIcon sx={{ fontSize: 8, color: 'primary.main', ml: 1 }} />
                                            )}
                                        </Box>
                                        <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                                            {notification.message}
                                        </Typography>
                                        <Box display="flex" gap={1} alignItems="center">
                                            <Chip
                                                label={notification.priority}
                                                size="small"
                                                color={getPriorityColor(notification.priority)}
                                                sx={{ height: 20, fontSize: '0.7rem' }}
                                            />
                                            <Typography variant="caption" color="text.secondary">
                                                {formatDistanceToNow(new Date(notification.created_at), {
                                                    addSuffix: true,
                                                })}
                                            </Typography>
                                        </Box>
                                    </Box>
                                </Box>
                            </MenuItem>
                        </React.Fragment>
                    ))
                )}

                {/* Footer */}
                {notifications.length > 10 && (
                    <>
                        <Divider />
                        <Box sx={{ p: 1, textAlign: 'center' }}>
                            <Button size="small" onClick={() => console.log('View all')}>
                                View all notifications
                            </Button>
                        </Box>
                    </>
                )}
            </Menu>
        </>
    );
};

export default NotificationCenter;
