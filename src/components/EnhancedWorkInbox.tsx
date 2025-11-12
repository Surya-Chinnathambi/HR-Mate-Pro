/**
 * Enhanced Work Inbox Module
 * Real-time notification inbox with filtering, bulk actions, and live updates
 */
import { useState, useEffect } from 'react';
import { useNotifications, Notification } from '../hooks/useNotifications';
import {
    Bell, Check, CheckCheck, Trash2, Filter, RefreshCw, Search,
    Clock, MessageSquare, Calendar, AlertCircle, CheckCircle,
    X, Settings, Download, Archive, Mail, MailOpen
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';

export function EnhancedWorkInbox() {
    const {
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
    } = useNotifications();

    const [filterType, setFilterType] = useState<string>('all');
    const [filterRead, setFilterRead] = useState<'all' | 'unread' | 'read'>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedNotifications, setSelectedNotifications] = useState<Set<number>>(new Set());
    const [showFilters, setShowFilters] = useState(false);

    // Filter notifications based on current filters
    const filteredNotifications = notifications.filter(notif => {
        // Type filter
        if (filterType !== 'all' && notif.notification_type !== filterType) {
            return false;
        }

        // Read/unread filter
        if (filterRead === 'unread' && notif.is_read) return false;
        if (filterRead === 'read' && !notif.is_read) return false;

        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            return (
                notif.title.toLowerCase().includes(query) ||
                notif.body.toLowerCase().includes(query)
            );
        }

        return true;
    });

    // Handle select all
    const handleSelectAll = () => {
        if (selectedNotifications.size === filteredNotifications.length) {
            setSelectedNotifications(new Set());
        } else {
            setSelectedNotifications(new Set(filteredNotifications.map(n => n.id)));
        }
    };

    // Handle select single
    const handleSelect = (notificationId: number) => {
        const newSelected = new Set(selectedNotifications);
        if (newSelected.has(notificationId)) {
            newSelected.delete(notificationId);
        } else {
            newSelected.add(notificationId);
        }
        setSelectedNotifications(newSelected);
    };

    // Bulk mark as read
    const handleBulkMarkAsRead = async () => {
        for (const id of Array.from(selectedNotifications)) {
            await markAsRead(id);
        }
        setSelectedNotifications(new Set());
    };

    // Bulk delete
    const handleBulkDelete = async () => {
        if (!confirm(`Delete ${selectedNotifications.size} notifications?`)) return;

        for (const id of Array.from(selectedNotifications)) {
            await deleteNotification(id);
        }
        setSelectedNotifications(new Set());
    };

    // Get icon for notification type
    const getNotificationIcon = (type: string) => {
        switch (type) {
            case 'task_assigned':
            case 'task_updated':
                return <CheckCircle className="w-5 h-5" />;
            case 'message_received':
                return <MessageSquare className="w-5 h-5" />;
            case 'leave_approved':
            case 'leave_rejected':
                return <Calendar className="w-5 h-5" />;
            case 'broadcast':
                return <AlertCircle className="w-5 h-5" />;
            case 'attendance_checked_in':
            case 'attendance_checked_out':
                return <Clock className="w-5 h-5" />;
            default:
                return <Bell className="w-5 h-5" />;
        }
    };

    // Get color for notification type
    const getNotificationColor = (type: string) => {
        switch (type) {
            case 'task_assigned':
            case 'task_updated':
                return 'text-blue-600 bg-blue-50';
            case 'message_received':
                return 'text-green-600 bg-green-50';
            case 'leave_approved':
                return 'text-green-600 bg-green-50';
            case 'leave_rejected':
                return 'text-red-600 bg-red-50';
            case 'broadcast':
                return 'text-orange-600 bg-orange-50';
            case 'attendance_checked_in':
            case 'attendance_checked_out':
                return 'text-purple-600 bg-purple-50';
            default:
                return 'text-gray-600 bg-gray-50';
        }
    };

    // Get unique notification types for filter
    const notificationTypes = Array.from(new Set(notifications.map(n => n.notification_type)));

    return (
        <div className="h-full flex flex-col bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                            <Mail className="w-7 h-7 text-blue-600" />
                            Work Inbox
                        </h1>
                        <p className="text-sm text-gray-500 mt-1">
                            {unreadCount} unread • {notifications.length} total
                            {isConnected && (
                                <span className="ml-2 inline-flex items-center">
                                    <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                                    <span className="text-green-600 font-medium">Live</span>
                                </span>
                            )}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => fetchNotifications({ limit: 100 })}
                            disabled={loading}
                            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                            title="Refresh"
                        >
                            <RefreshCw className={`w-5 h-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                        <button
                            onClick={() => setShowFilters(!showFilters)}
                            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                            title="Filters"
                        >
                            <Filter className="w-5 h-5 text-gray-600" />
                        </button>
                        {unreadCount > 0 && (
                            <button
                                onClick={markAllAsRead}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium flex items-center gap-2"
                            >
                                <CheckCheck className="w-4 h-4" />
                                Mark all read
                            </button>
                        )}
                    </div>
                </div>

                {/* Search Bar */}
                <div className="mt-4 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search notifications..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery('')}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2"
                        >
                            <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
                        </button>
                    )}
                </div>

                {/* Filters Panel */}
                {showFilters && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Type Filter */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Notification Type
                                </label>
                                <select
                                    value={filterType}
                                    onChange={(e) => setFilterType(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="all">All Types</option>
                                    {notificationTypes.map(type => (
                                        <option key={type} value={type}>
                                            {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Read Status Filter */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Read Status
                                </label>
                                <select
                                    value={filterRead}
                                    onChange={(e) => setFilterRead(e.target.value as any)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="all">All Notifications</option>
                                    <option value="unread">Unread Only</option>
                                    <option value="read">Read Only</option>
                                </select>
                            </div>
                        </div>
                    </div>
                )}

                {/* Bulk Actions Bar */}
                {selectedNotifications.size > 0 && (
                    <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
                        <span className="text-sm font-medium text-blue-900">
                            {selectedNotifications.size} selected
                        </span>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={handleBulkMarkAsRead}
                                className="px-3 py-1.5 bg-white border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 transition-colors text-sm font-medium flex items-center gap-2"
                            >
                                <Check className="w-4 h-4" />
                                Mark as Read
                            </button>
                            <button
                                onClick={handleBulkDelete}
                                className="px-3 py-1.5 bg-white border border-red-300 text-red-700 rounded-lg hover:bg-red-50 transition-colors text-sm font-medium flex items-center gap-2"
                            >
                                <Trash2 className="w-4 h-4" />
                                Delete
                            </button>
                            <button
                                onClick={() => setSelectedNotifications(new Set())}
                                className="px-3 py-1.5 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Stats Bar */}
            {stats && (
                <div className="bg-white border-b border-gray-200 px-6 py-3">
                    <div className="flex items-center gap-6 text-sm">
                        <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-700">Total:</span>
                            <span className="text-gray-900">{stats.total}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-700">Unread:</span>
                            <span className="text-blue-600 font-semibold">{stats.unread}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-700">By Type:</span>
                            {Object.entries(stats.by_type).map(([type, count]) => (
                                <span key={type} className="px-2 py-1 bg-gray-100 rounded text-xs">
                                    {type}: {count}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Notifications List */}
            <div className="flex-1 overflow-y-auto p-6">
                {loading && notifications.length === 0 ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="text-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                            <p className="text-gray-500">Loading notifications...</p>
                        </div>
                    </div>
                ) : filteredNotifications.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-center">
                        <Mail className="w-16 h-16 text-gray-300 mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No notifications</h3>
                        <p className="text-gray-500">
                            {searchQuery ? 'No results found for your search.' : 'You\'re all caught up!'}
                        </p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {/* Select All */}
                        <div className="bg-white rounded-lg border border-gray-200 p-3 mb-2">
                            <label className="flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={selectedNotifications.size === filteredNotifications.length}
                                    onChange={handleSelectAll}
                                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                />
                                <span className="ml-3 text-sm font-medium text-gray-700">
                                    Select all ({filteredNotifications.length})
                                </span>
                            </label>
                        </div>

                        {/* Notification Cards */}
                        {filteredNotifications.map((notification) => {
                            const Icon = getNotificationIcon(notification.notification_type);
                            const colorClass = getNotificationColor(notification.notification_type);
                            const isSelected = selectedNotifications.has(notification.id);

                            return (
                                <div
                                    key={notification.id}
                                    className={`bg-white rounded-lg border transition-all ${isSelected
                                            ? 'border-blue-500 shadow-md'
                                            : notification.is_read
                                                ? 'border-gray-200'
                                                : 'border-blue-200 bg-blue-50/30'
                                        } hover:shadow-md`}
                                >
                                    <div className="p-4">
                                        <div className="flex items-start gap-4">
                                            {/* Checkbox */}
                                            <input
                                                type="checkbox"
                                                checked={isSelected}
                                                onChange={() => handleSelect(notification.id)}
                                                className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                            />

                                            {/* Icon */}
                                            <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${colorClass}`}>
                                                {Icon}
                                            </div>

                                            {/* Content */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="flex-1 min-w-0">
                                                        <h3 className={`text-sm font-semibold ${notification.is_read ? 'text-gray-700' : 'text-gray-900'
                                                            }`}>
                                                            {notification.title}
                                                        </h3>
                                                        <p className={`text-sm mt-1 ${notification.is_read ? 'text-gray-500' : 'text-gray-700'
                                                            }`}>
                                                            {notification.body}
                                                        </p>
                                                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                                                            <span className="flex items-center gap-1">
                                                                <Clock className="w-3 h-3" />
                                                                {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                                                            </span>
                                                            <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                                                                {notification.notification_type.replace(/_/g, ' ')}
                                                            </span>
                                                        </div>
                                                    </div>

                                                    {/* Actions */}
                                                    <div className="flex items-center gap-1 flex-shrink-0">
                                                        {!notification.is_read && (
                                                            <button
                                                                onClick={() => markAsRead(notification.id)}
                                                                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                                                                title="Mark as read"
                                                            >
                                                                <MailOpen className="w-4 h-4 text-green-600" />
                                                            </button>
                                                        )}
                                                        <button
                                                            onClick={() => deleteNotification(notification.id)}
                                                            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                                                            title="Delete"
                                                        >
                                                            <Trash2 className="w-4 h-4 text-red-600" />
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
