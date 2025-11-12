// Employee Dashboard Content - Modern UI with integrated chat
import { useState, useEffect } from "react";
import {
    Clock, Calendar, TrendingUp, Users, Award, Activity,
    CheckCircle, XCircle, AlertCircle, ArrowUp, ArrowDown,
    Zap, Target, BarChart3, Coffee, Timer, LogIn, LogOut as LogOutIcon,
    MessageCircle, X, Send
} from "lucide-react";
import {
    LineChart, Line, AreaChart, Area, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend
} from "recharts";
import apiClient, { api } from "../api/client";

interface EmployeeDashboardContentProps {
    employee: any;
}

export function EmployeeDashboardContent({ employee }: EmployeeDashboardContentProps) {
    const [attendanceData, setAttendanceData] = useState<any[]>([]);
    const [activityFeed, setActivityFeed] = useState<any[]>([]);
    const [stats, setStats] = useState<any>(null);
    const [isClockingIn, setIsClockingIn] = useState(false);
    const [clockStatus, setClockStatus] = useState<'clocked-out' | 'clocked-in'>('clocked-out');
    const [todayHours, setTodayHours] = useState(0);
    const [messages, setMessages] = useState<any[]>([]);
    const [newMessage, setNewMessage] = useState('');
    const [isSendingMessage, setIsSendingMessage] = useState(false);

    // Helper to get the numeric employee ID (not the string employee_id like "EMP1004")
    const getEmployeeNumericId = () => {
        // Backend expects the numeric 'id' field, not the string 'employee_id' field
        if (!employee) return null;
        
        // Check if id exists and is a number
        if (typeof employee.id === 'number') {
            return employee.id;
        }
        
        // Fallback: try to find a numeric field
        // Some APIs might use different field names
        if (typeof employee.employee_number === 'number') {
            return employee.employee_number;
        }
        
        // Debug: log the employee object to see what fields are available
        console.error('❌ Cannot find numeric employee ID in employee object:', employee);
        console.log('Available fields:', Object.keys(employee));
        
        return null;
    };

    // Fetch initial data
    useEffect(() => {
        const fetchData = async () => {
            const empId = getEmployeeNumericId();
            if (!empId) return;

            try {
                // Fetch attendance history
                const attendanceRes = await apiClient.get('/attendance/history', {
                    params: { employee_id: empId }
                }).catch(() => ({ data: [] }));
                setAttendanceData(attendanceRes?.data || []);

                // Check if clocked in today
                const todayAttendance = await apiClient.get('/attendance/today', {
                    params: { employee_id: empId }
                }).catch(() => ({ data: null }));

                const today = todayAttendance?.data;
                if (today && today.checkIn && !today.checkOut) {
                    setClockStatus('clocked-in');
                    // Parse time string to calculate hours
                    const [hours, minutes] = today.checkIn.split(':').map(Number);
                    const clockIn = new Date();
                    clockIn.setHours(hours, minutes, 0, 0);
                    const now = new Date();
                    const hoursWorked = (now.getTime() - clockIn.getTime()) / (1000 * 60 * 60);
                    setTodayHours(Math.max(0, Math.round(hoursWorked * 10) / 10));
                }
            } catch (error) {
                console.error('Failed to fetch attendance data:', error);
            }

            // Fetch chat messages
            try {
                const chatRes = await apiClient.get('/group-chat/messages', { params: { limit: 50 } }).catch(() => ({ data: [] }));
                setMessages(chatRes?.data || []);
            } catch (error) {
                console.error('Failed to fetch chat messages:', error);
            }

            // Fetch stats (optional, with fallback)
            try {
                const statsRes = await apiClient.get('/activity/stats').catch(() => ({ data: {} }));
                setStats(statsRes?.data || {});
            } catch (error) {
                console.error('Failed to fetch stats:', error);
                setStats({});
            }
        };

        if (employee && getEmployeeNumericId()) {
            fetchData();
            // Refresh messages every 10 seconds
            const interval = setInterval(() => {
                if (employee?.employee_id) {
                    apiClient.get('/group-chat/messages', { params: { limit: 50 } })
                        .then(res => setMessages(res?.data || []))
                        .catch(err => console.error('Failed to refresh messages:', err));
                }
            }, 10000);
            return () => clearInterval(interval);
        }
    }, [employee]);

    // Update hours worked counter every minute when clocked in
    useEffect(() => {
        if (clockStatus === 'clocked-in') {
            const interval = setInterval(async () => {
                const empId = getEmployeeNumericId();
                if (!empId) return;

                try {
                    const todayAttendance = await apiClient.get('/attendance/today', {
                        params: { employee_id: empId }
                    });

                    const today = todayAttendance?.data;
                    if (today && today.checkIn && !today.checkOut) {
                        // Parse time string to calculate hours
                        const [hours, minutes] = today.checkIn.split(':').map(Number);
                        const clockIn = new Date();
                        clockIn.setHours(hours, minutes, 0, 0);
                        const now = new Date();
                        const hoursWorked = (now.getTime() - clockIn.getTime()) / (1000 * 60 * 60);
                        setTodayHours(Math.max(0, Math.round(hoursWorked * 10) / 10));
                    }
                } catch (error) {
                    console.error('Failed to update hours:', error);
                }
            }, 60000); // Update every minute

            return () => clearInterval(interval);
        }
    }, [clockStatus, employee]);

    const handleClockAction = async () => {
        const empId = getEmployeeNumericId();
        if (!empId) {
            alert('Employee information not available. Please refresh the page.');
            return;
        }

        setIsClockingIn(true);
        try {
            if (clockStatus === 'clocked-out') {
                await api.attendance.checkIn({
                    employee_id: empId
                });
                setClockStatus('clocked-in');
                setTodayHours(0);
            } else {
                await api.attendance.checkOut({
                    employee_id: empId
                });
                setClockStatus('clocked-out');
            }

            // Refresh attendance data
            const res = await apiClient.get('/attendance/history', {
                params: { employee_id: empId }
            });
            setAttendanceData(res?.data || []);
        } catch (error: any) {
            console.error('Clock action failed:', error);
            const errorMsg = error.response?.data?.detail || 'Failed to record attendance. Please try again.';
            alert(errorMsg);
        } finally {
            setIsClockingIn(false);
        }
    }; const handleSendMessage = async () => {
        if (!newMessage.trim() || isSendingMessage) return;

        setIsSendingMessage(true);
        try {
            await apiClient.post('/group-chat/messages', {
                message: newMessage,
                message_type: 'text'
            });
            setNewMessage('');
            // Refresh messages
            const res = await apiClient.get('/group-chat/messages', { params: { limit: 50 } });
            setMessages(res?.data || []);
        } catch (error: any) {
            console.error('Failed to send message:', error);
            alert(error?.response?.data?.detail || 'Failed to send message');
        } finally {
            setIsSendingMessage(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // Chart data preparation
    const last30DaysData = attendanceData.slice(0, 30).reverse().map((item: any, index) => {
        // Backend returns time strings like "09:30" and date strings like "2025-11-12"
        const dateStr = item.date;
        const hours = item.workHours || 0;

        return {
            day: dateStr ? new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : `Day ${index + 1}`,
            hours: hours,
            status: item.status
        };
    });

    const leaveBalanceData = [
        { name: 'Used', value: stats?.leaves_used || 5, color: '#ef4444' },
        { name: 'Remaining', value: stats?.leaves_remaining || 15, color: '#10b981' }
    ];

    const performanceData = [
        { metric: 'Tasks Completed', value: stats?.tasks_completed || 42, target: 50 },
        { metric: 'Attendance %', value: stats?.attendance_percentage || 96, target: 100 },
        { metric: 'Team Collaboration', value: stats?.collaboration_score || 88, target: 100 }
    ];

    if (!employee) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600 font-semibold">Loading your dashboard...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Welcome Header with Real-time Status */}
            <div className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 rounded-3xl p-8 text-white shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-32 -mt-32 blur-3xl"></div>
                <div className="absolute bottom-0 left-0 w-96 h-96 bg-white/5 rounded-full -ml-48 -mb-48 blur-3xl"></div>

                <div className="relative z-10">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h1 className="text-3xl font-bold mb-2">
                                Welcome back, {employee.first_name}! 👋
                            </h1>
                            <p className="text-blue-100 text-lg">
                                {new Date().toLocaleDateString('en-US', {
                                    weekday: 'long',
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric'
                                })}
                            </p>
                        </div>
                    </div>

                    {/* Clock In/Out Button */}
                    <div className="flex items-center gap-6">
                        <button
                            onClick={handleClockAction}
                            disabled={isClockingIn}
                            className={`flex items-center gap-3 px-8 py-4 rounded-2xl font-bold text-lg transition-all duration-300 transform hover:scale-105 shadow-xl ${clockStatus === 'clocked-out'
                                ? 'bg-green-500 hover:bg-green-600 text-white'
                                : 'bg-red-500 hover:bg-red-600 text-white'
                                } ${isClockingIn ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            {isClockingIn ? (
                                <>
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                                    <span>Processing...</span>
                                </>
                            ) : clockStatus === 'clocked-out' ? (
                                <>
                                    <LogIn className="w-6 h-6" />
                                    <span>Clock In</span>
                                </>
                            ) : (
                                <>
                                    <LogOutIcon className="w-6 h-6" />
                                    <span>Clock Out</span>
                                </>
                            )}
                        </button>

                        {clockStatus === 'clocked-in' && (
                            <div className="bg-white/20 backdrop-blur-sm px-6 py-4 rounded-2xl">
                                <div className="flex items-center gap-2 text-sm font-medium mb-1">
                                    <Timer className="w-4 h-4" />
                                    <span>Hours Today</span>
                                </div>
                                <div className="text-3xl font-bold">{todayHours}h</div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-white/20 rounded-xl">
                            <Clock className="w-6 h-6" />
                        </div>
                        <div className="flex items-center gap-1 text-sm font-semibold bg-white/20 px-3 py-1 rounded-full">
                            <ArrowUp className="w-4 h-4" />
                            <span>+12%</span>
                        </div>
                    </div>
                    <div className="text-3xl font-bold mb-1">{stats?.total_hours || 168}h</div>
                    <div className="text-blue-100">Total Hours (30d)</div>
                </div>

                <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-white/20 rounded-xl">
                            <Calendar className="w-6 h-6" />
                        </div>
                        <div className="flex items-center gap-1 text-sm font-semibold bg-white/20 px-3 py-1 rounded-full">
                            <CheckCircle className="w-4 h-4" />
                            <span>96%</span>
                        </div>
                    </div>
                    <div className="text-3xl font-bold mb-1">{stats?.attendance_days || 22}/23</div>
                    <div className="text-green-100">Attendance</div>
                </div>

                <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-white/20 rounded-xl">
                            <Coffee className="w-6 h-6" />
                        </div>
                        <div className="flex items-center gap-1 text-sm font-semibold bg-white/20 px-3 py-1 rounded-full">
                            <span>{stats?.leaves_remaining || 15} left</span>
                        </div>
                    </div>
                    <div className="text-3xl font-bold mb-1">{stats?.leaves_used || 5}/20</div>
                    <div className="text-purple-100">Leaves Used</div>
                </div>

                <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-white/20 rounded-xl">
                            <Target className="w-6 h-6" />
                        </div>
                        <div className="flex items-center gap-1 text-sm font-semibold bg-white/20 px-3 py-1 rounded-full">
                            <ArrowUp className="w-4 h-4" />
                            <span>+8%</span>
                        </div>
                    </div>
                    <div className="text-3xl font-bold mb-1">{stats?.tasks_completed || 42}/50</div>
                    <div className="text-orange-100">Tasks Completed</div>
                </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 30-Day Attendance Chart */}
                <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-lg">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                            30-Day Attendance Trend
                        </h2>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                            <span className="text-sm text-gray-600 dark:text-gray-400">Hours Worked</span>
                        </div>
                    </div>
                    <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={last30DaysData}>
                            <defs>
                                <linearGradient id="colorHours" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                                dataKey="day"
                                stroke="#9ca3af"
                                tick={{ fill: '#6b7280', fontSize: 12 }}
                            />
                            <YAxis
                                stroke="#9ca3af"
                                tick={{ fill: '#6b7280', fontSize: 12 }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#fff',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '12px',
                                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                                }}
                            />
                            <Area
                                type="monotone"
                                dataKey="hours"
                                stroke="#3b82f6"
                                strokeWidth={3}
                                fill="url(#colorHours)"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Leave Balance */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-lg">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
                        Leave Balance
                    </h2>
                    <ResponsiveContainer width="100%" height={200}>
                        <PieChart>
                            <Pie
                                data={leaveBalanceData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {leaveBalanceData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip />
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="mt-4 space-y-2">
                        {leaveBalanceData.map((item, index) => (
                            <div key={index} className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-3 h-3 rounded-full"
                                        style={{ backgroundColor: item.color }}
                                    ></div>
                                    <span className="text-sm text-gray-600 dark:text-gray-400">
                                        {item.name}
                                    </span>
                                </div>
                                <span className="text-sm font-bold text-gray-900 dark:text-white">
                                    {item.value} days
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Performance Metrics & Team Chat */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Performance Metrics */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-lg">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
                        Performance Metrics
                    </h2>
                    <div className="space-y-6">
                        {performanceData.map((item, index) => (
                            <div key={index}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                        {item.metric}
                                    </span>
                                    <span className="text-sm font-bold text-gray-900 dark:text-white">
                                        {item.value}/{item.target}
                                    </span>
                                </div>
                                <div className="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-500 ${item.value >= item.target * 0.9
                                            ? 'bg-gradient-to-r from-green-500 to-green-600'
                                            : item.value >= item.target * 0.7
                                                ? 'bg-gradient-to-r from-yellow-500 to-yellow-600'
                                                : 'bg-gradient-to-r from-red-500 to-red-600'
                                            }`}
                                        style={{ width: `${(item.value / item.target) * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Team Chat */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg flex flex-col h-[500px]">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-500 to-purple-500">
                        <div className="flex items-center gap-3">
                            <MessageCircle className="w-6 h-6 text-white" />
                            <div>
                                <h2 className="text-lg font-bold text-white">Team Chat</h2>
                                <p className="text-xs text-blue-100">Stay connected with your team</p>
                            </div>
                        </div>
                    </div>

                    {/* Messages Area */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {messages.length > 0 ? (
                            messages.slice().reverse().map((msg, index) => {
                                const isCurrentUser = msg.sender_id === employee?.employee_id;
                                return (
                                    <div
                                        key={index}
                                        className={`flex ${isCurrentUser ? 'justify-end' : 'justify-start'}`}
                                    >
                                        <div className={`max-w-[70%] ${isCurrentUser
                                            ? 'bg-blue-500 text-white'
                                            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
                                            } rounded-2xl px-4 py-2 shadow-sm`}>
                                            {!isCurrentUser && (
                                                <div className="text-xs font-semibold mb-1 opacity-75">
                                                    {msg.sender_name}
                                                </div>
                                            )}
                                            <div className="text-sm break-words">{msg.message}</div>
                                            <div className={`text-xs mt-1 ${isCurrentUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'}`}>
                                                {new Date(msg.created_at).toLocaleTimeString('en-US', {
                                                    hour: '2-digit',
                                                    minute: '2-digit'
                                                })}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-center">
                                    <MessageCircle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                                    <p className="text-gray-500 dark:text-gray-400">No messages yet</p>
                                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Start a conversation with your team</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Message Input */}
                    <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                        <div className="flex items-center gap-2">
                            <input
                                type="text"
                                value={newMessage}
                                onChange={(e) => setNewMessage(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Type a message..."
                                disabled={isSendingMessage}
                                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                            />
                            <button
                                onClick={handleSendMessage}
                                disabled={!newMessage.trim() || isSendingMessage}
                                className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 font-medium"
                            >
                                {isSendingMessage ? (
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                                ) : (
                                    <>
                                        <Send className="w-5 h-5" />
                                        <span>Send</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
