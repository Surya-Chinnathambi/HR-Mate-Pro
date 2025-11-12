import { useState } from "react";

export function NotificationInbox() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications] = useState([
    {
      id: 1,
      title: "Leave Request Approved",
      message: "Your casual leave request for Dec 20-21 has been approved.",
      type: "success",
      timestamp: "2 hours ago",
      read: false,
    },
    {
      id: 2,
      title: "Payroll Generated",
      message: "Your payslip for November 2024 is now available.",
      type: "info",
      timestamp: "1 day ago",
      read: false,
    },
    {
      id: 3,
      title: "Training Reminder",
      message: "Leadership Skills training starts tomorrow at 10 AM.",
      type: "warning",
      timestamp: "2 days ago",
      read: true,
    },
    {
      id: 4,
      title: "Policy Update",
      message: "Work from home policy has been updated. Please review.",
      type: "info",
      timestamp: "3 days ago",
      read: true,
    },
  ]);

  const unreadCount = notifications.filter(n => !n.read).length;

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "success":
        return "✅";
      case "warning":
        return "⚠️";
      case "error":
        return "❌";
      default:
        return "ℹ️";
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case "success":
        return "border-green-200 bg-green-50";
      case "warning":
        return "border-yellow-200 bg-yellow-50";
      case "error":
        return "border-red-200 bg-red-50";
      default:
        return "border-blue-200 bg-blue-50";
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowNotifications(!showNotifications)}
        className="relative p-2 text-gray-600 hover:text-gray-900 transition-colors rounded-xl hover:bg-white/50"
      >
        <span className="text-xl">🔔</span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-gradient-to-r from-red-500 to-pink-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-bold shadow-lg">
            {unreadCount}
          </span>
        )}
      </button>

      {showNotifications && (
        <div className="absolute right-0 mt-2 w-80 bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border border-gray-200/50 z-50">
          <div className="p-4 border-b border-gray-200/50 bg-gradient-to-r from-blue-50 to-purple-50 rounded-t-2xl">
            <h3 className="font-bold text-gray-900">Notifications</h3>
            <p className="text-sm text-gray-600">{unreadCount} unread messages</p>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {notifications.length > 0 ? (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-4 border-b border-gray-100 hover:bg-gray-50/50 transition-colors ${
                    !notification.read ? "bg-blue-50/50" : ""
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className={`p-2 rounded-xl ${getNotificationColor(notification.type)}`}>
                      <span className="text-lg">
                        {getNotificationIcon(notification.type)}
                      </span>
                    </div>
                    <div className="flex-1">
                      <h4 className="font-bold text-gray-900 text-sm">
                        {notification.title}
                      </h4>
                      <p className="text-gray-600 text-sm mt-1 leading-relaxed">
                        {notification.message}
                      </p>
                      <p className="text-gray-400 text-xs mt-2">
                        {notification.timestamp}
                      </p>
                    </div>
                    {!notification.read && (
                      <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-gray-500">
                <span className="text-4xl mb-4 block">📭</span>
                <p>No notifications</p>
              </div>
            )}
          </div>
          <div className="p-4 border-t border-gray-200/50 bg-gray-50/50 rounded-b-2xl">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors">
              Mark all as read
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
