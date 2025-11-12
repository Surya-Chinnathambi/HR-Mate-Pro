import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import {
  Inbox,
  Clock,
  CheckCircle,
  XCircle,
  Calendar,
  DollarSign,
  FileText,
  AlertCircle,
  Filter,
  Search,
  Bell,
  BellOff
} from 'lucide-react';
import { toast } from 'sonner';

interface InboxItem {
  _id: string;
  title: string;
  description: string;
  type: string;
  entityId: string;
  entityType: string;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'completed' | 'expired';
  dueDate?: string;
  metadata: {
    employeeName?: string;
    amount?: number;
    days?: number;
    period?: string;
  };
  _creationTime: number;
}

export const EnhancedInbox: React.FC = () => {
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPriority, setSelectedPriority] = useState<string>('all');
  const [inboxItems, setInboxItems] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any>({ notifications: [], unreadCount: 0 });

  useEffect(() => {
    let mounted = true;
    const fetch = async () => {
      try {
        const [inboxRes, notifRes] = await Promise.all([
          apiClient.get('/realtime/inbox-items'),
          apiClient.get('/realtime/notifications')
        ]);
        if (!mounted) return;
        setInboxItems(inboxRes.data ?? []);
        setNotifications(notifRes.data ?? { notifications: [], unreadCount: 0 });
      } catch (err) {
        console.error('Failed to load inbox data', err);
      }
    };
    fetch();
    return () => { mounted = false; };
  }, []);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'leave_approval':
        return <Calendar className="w-5 h-5 text-blue-500" />;
      case 'attendance_regularization':
        return <Clock className="w-5 h-5 text-orange-500" />;
      case 'timesheet_approval':
        return <FileText className="w-5 h-5 text-green-500" />;
      case 'expense_approval':
        return <DollarSign className="w-5 h-5 text-purple-500" />;
      case 'overtime_approval':
        return <Clock className="w-5 h-5 text-red-500" />;
      default:
        return <Inbox className="w-5 h-5 text-gray-500" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const handleApprove = async (item: InboxItem) => {
    try {
      if (item.type === 'leave_approval') {
        // backend endpoint: PUT /leaves/{leave_id}/approve
        await apiClient.put(`/leaves/${item.entityId}/approve`, { comments: 'Approved via inbox' });
      }
      // Add other approval types here
      toast.success('Request approved successfully');
    } catch (error) {
      toast.error('Failed to approve request');
    }
  };

  const handleReject = async (item: InboxItem) => {
    try {
      if (item.type === 'leave_approval') {
        await apiClient.put(`/leaves/${item.entityId}/reject`, { comments: 'Rejected via inbox' });
      }
      toast.success('Request rejected');
    } catch (error) {
      toast.error('Failed to reject request');
    }
  };

  const markNotificationRead = async (notificationId: number) => {
    try {
      await apiClient.post(`/realtime/notifications/${notificationId}/mark-read`);
      // refresh notifications
      const notifRes = await apiClient.get('/realtime/notifications');
      setNotifications(notifRes.data ?? { notifications: [], unreadCount: 0 });
    } catch (err) {
      console.error('Failed to mark notification read', err);
    }
  };

  const filteredItems = inboxItems.filter(item => {
    const matchesFilter = selectedFilter === 'all' || item.type === selectedFilter;
    const matchesPriority = selectedPriority === 'all' || item.priority === selectedPriority;
    const matchesSearch = searchTerm === '' ||
      item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.metadata.employeeName?.toLowerCase().includes(searchTerm.toLowerCase());

    return matchesFilter && matchesPriority && matchesSearch;
  });

  const pendingItems = filteredItems.filter(item => item.status === 'pending');
  const completedItems = filteredItems.filter(item => item.status === 'completed');

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Inbox className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Inbox</h1>
            <p className="text-gray-600">
              {pendingItems.length} pending items • {notifications.unreadCount} unread notifications
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            <Bell className="w-4 h-4" />
            <span>Notifications</span>
            {notifications.unreadCount > 0 && (
              <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                {notifications.unreadCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search inbox..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={selectedFilter}
              onChange={(e) => setSelectedFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Types</option>
              <option value="leave_approval">Leave Approvals</option>
              <option value="attendance_regularization">Attendance</option>
              <option value="timesheet_approval">Timesheets</option>
              <option value="expense_approval">Expenses</option>
              <option value="overtime_approval">Overtime</option>
            </select>
          </div>

          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Pending</p>
              <p className="text-2xl font-bold text-orange-600">{pendingItems.length}</p>
            </div>
            <Clock className="w-8 h-8 text-orange-500" />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Completed</p>
              <p className="text-2xl font-bold text-green-600">{completedItems.length}</p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">High Priority</p>
              <p className="text-2xl font-bold text-red-600">
                {pendingItems.filter(item => item.priority === 'high').length}
              </p>
            </div>
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Notifications</p>
              <p className="text-2xl font-bold text-blue-600">{notifications.unreadCount}</p>
            </div>
            <Bell className="w-8 h-8 text-blue-500" />
          </div>
        </div>
      </div>

      {/* Inbox Items */}
      <div className="space-y-6">
        {/* Pending Items */}
        {pendingItems.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Pending Actions</h2>
              <p className="text-gray-600">Items requiring your attention</p>
            </div>
            <div className="divide-y divide-gray-200">
              {pendingItems.map((item) => (
                <div key={item._id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4">
                      {getTypeIcon(item.type)}
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <h3 className="font-semibold text-gray-900">{item.title}</h3>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full border ${getPriorityColor(item.priority)}`}>
                            {item.priority}
                          </span>
                        </div>
                        <p className="text-gray-600 mb-2">{item.description}</p>
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          {item.metadata.employeeName && (
                            <span>Employee: {item.metadata.employeeName}</span>
                          )}
                          {item.metadata.days && (
                            <span>Days: {item.metadata.days}</span>
                          )}
                          {item.metadata.amount && (
                            <span>Amount: ${item.metadata.amount}</span>
                          )}
                          {item.dueDate && (
                            <span>Due: {new Date(item.dueDate).toLocaleDateString()}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleApprove(item)}
                        className="flex items-center space-x-1 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                      >
                        <CheckCircle className="w-4 h-4" />
                        <span>Approve</span>
                      </button>
                      <button
                        onClick={() => handleReject(item)}
                        className="flex items-center space-x-1 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Reject</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Notifications */}
        {notifications.notifications.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Recent Notifications</h2>
              <p className="text-gray-600">Latest updates and alerts</p>
            </div>
            <div className="divide-y divide-gray-200">
              {notifications.notifications.slice(0, 10).map((notification: any) => (
                <div
                  key={notification._id}
                  className={`p-6 hover:bg-gray-50 transition-colors ${!notification.isRead ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                    }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="font-semibold text-gray-900">{notification.title}</h3>
                        {!notification.isRead && (
                          <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                        )}
                      </div>
                      <p className="text-gray-600 mb-2">{notification.message}</p>
                      <p className="text-sm text-gray-500">
                        {new Date(notification._creationTime).toLocaleString()}
                      </p>
                    </div>

                    {!notification.isRead && (
                      <button
                        onClick={() => markNotificationRead(notification._id)}
                        className="text-blue-600 hover:text-blue-700 transition-colors"
                      >
                        <BellOff className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {pendingItems.length === 0 && notifications.notifications.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <Inbox className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">All caught up!</h3>
            <p className="text-gray-600">No pending items or notifications at the moment.</p>
          </div>
        )}
      </div>
    </div>
  );
};
