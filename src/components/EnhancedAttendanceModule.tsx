import React, { useState, useEffect } from 'react';
import {
    Clock,
    MapPin,
    Calendar,
    CheckCircle,
    XCircle,
    Coffee,
    Home,
    TrendingUp,
    Users,
    ChevronLeft,
    ChevronRight,
    LogIn,
    LogOut,
    Loader
} from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, parseISO } from 'date-fns';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';

interface AttendanceRecord {
    attendance_id: string;
    employee_id: string;
    employee_name?: string;
    date: string;
    check_in_time: string | null;
    check_out_time: string | null;
    status: 'present' | 'absent' | 'on_leave' | 'wfh';
    hours_worked: number | null;
    check_in_location?: string;
    check_out_location?: string;
    notes?: string;
}

interface TodayStatus {
    attendance_id?: string;
    date: string;
    check_in_time: string | null;
    check_out_time: string | null;
    status: 'present' | 'absent' | 'on_leave' | 'wfh' | 'not_started';
    hours_worked: number | null;
    check_in_location?: string;
    check_out_location?: string;
}

interface AttendanceStats {
    total_days: number;
    present_days: number;
    absent_days: number;
    wfh_days: number;
    leave_days: number;
    avg_hours: number;
}

interface EnhancedAttendanceModuleProps {
    currentUser?: {
        employee_id: string;
        role: string;
    };
}

const EnhancedAttendanceModule: React.FC<EnhancedAttendanceModuleProps> = ({ currentUser }) => {
    const [todayStatus, setTodayStatus] = useState<TodayStatus | null>(null);
    const [attendanceRecords, setAttendanceRecords] = useState<AttendanceRecord[]>([]);
    const [stats, setStats] = useState<AttendanceStats | null>(null);
    const [selectedDate, setSelectedDate] = useState<Date>(new Date());
    const [view, setView] = useState<'today' | 'history' | 'calendar' | 'team'>('today');
    const [loading, setLoading] = useState(false);
    const [checkInLoading, setCheckInLoading] = useState(false);
    const [checkOutLoading, setCheckOutLoading] = useState(false);
    const [teamAttendance, setTeamAttendance] = useState<AttendanceRecord[]>([]);

    const { lastMessage: wsMessage } = useWebSocket();

    const isManager = currentUser?.role && ['manager', 'hr', 'admin'].includes(currentUser.role.toLowerCase());

    // Load today's status
    const loadTodayStatus = async () => {
        try {
            const response = await api.attendance.getTodayStatus();
            setTodayStatus(response.data);
        } catch (error: any) {
            console.error('Error loading today status:', error);
            // Initialize default status if error
            setTodayStatus({
                date: format(new Date(), 'yyyy-MM-dd'),
                check_in_time: null,
                check_out_time: null,
                status: 'not_started',
                hours_worked: null
            });
        }
    };

    // Load attendance records
    const loadAttendanceRecords = async (start?: string, end?: string) => {
        try {
            setLoading(true);
            const params: any = { limit: 100 };
            if (start) params.start_date = start;
            if (end) params.end_date = end;

            const response = await api.attendance.getRecords(params);
            setAttendanceRecords(response.data || []);
        } catch (error: any) {
            console.error('Error loading attendance records:', error);
            toast.error('Failed to load attendance records');
        } finally {
            setLoading(false);
        }
    };

    // Load stats
    const loadStats = async () => {
        try {
            const response = await api.attendance.getStats();
            setStats(response.data);
        } catch (error: any) {
            console.error('Error loading stats:', error);
        }
    };

    // Load team attendance (for managers)
    const loadTeamAttendance = async () => {
        if (!isManager) return;

        try {
            setLoading(true);
            const today = format(new Date(), 'yyyy-MM-dd');
            const response = await api.team.getAttendance({ date: today });
            setTeamAttendance(response.data || []);
        } catch (error: any) {
            console.error('Error loading team attendance:', error);
            toast.error('Failed to load team attendance');
        } finally {
            setLoading(false);
        }
    };

    // Check in
    const handleCheckIn = async () => {
        try {
            setCheckInLoading(true);

            // Get location if available
            let location = 'Unknown';
            if (navigator.geolocation) {
                try {
                    const position = await new Promise<GeolocationPosition>((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
                    });
                    location = `${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`;
                } catch (geoError) {
                    console.warn('Location access denied or unavailable');
                }
            }

            // Get employee_id from current user or fetch from current endpoint
            const empId = currentUser?.employee_id || (await api.employees.current()).data.employee_id;

            const response = await api.attendance.checkIn({
                employee_id: Number(empId)
            });

            toast.success('✅ Checked in successfully!');
            await loadTodayStatus();
            await loadAttendanceRecords();
            await loadStats();
        } catch (error: any) {
            console.error('Error checking in:', error);
            toast.error(error.response?.data?.detail || 'Failed to check in');
        } finally {
            setCheckInLoading(false);
        }
    };

    // Check out
    const handleCheckOut = async () => {
        try {
            setCheckOutLoading(true);

            // Get location if available
            let location = 'Unknown';
            if (navigator.geolocation) {
                try {
                    const position = await new Promise<GeolocationPosition>((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
                    });
                    location = `${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`;
                } catch (geoError) {
                    console.warn('Location access denied or unavailable');
                }
            }

            // Get employee_id from current user or fetch from current endpoint
            const empId = currentUser?.employee_id || (await api.employees.current()).data.employee_id;

            const response = await api.attendance.checkOut({
                employee_id: Number(empId),
                location
            });

            toast.success('👋 Checked out successfully!');
            await loadTodayStatus();
            await loadAttendanceRecords();
            await loadStats();
        } catch (error: any) {
            console.error('Error checking out:', error);
            toast.error(error.response?.data?.detail || 'Failed to check out');
        } finally {
            setCheckOutLoading(false);
        }
    };

    // WebSocket handler
    useEffect(() => {
        if (!wsMessage) return;

        const handleWebSocketMessage = (message: any) => {
            switch (message.type) {
                case 'attendance_checked_in':
                    // Reload today status and records
                    loadTodayStatus();
                    if (view === 'team' && isManager) {
                        loadTeamAttendance();
                    }
                    toast.success(`${message.employee_name || 'Someone'} checked in`);
                    break;
                case 'attendance_checked_out':
                    // Reload today status and records
                    loadTodayStatus();
                    if (view === 'team' && isManager) {
                        loadTeamAttendance();
                    }
                    toast.success(`${message.employee_name || 'Someone'} checked out`);
                    break;
            }
        };

        handleWebSocketMessage(wsMessage);
    }, [wsMessage, view, isManager]);

    // Initial load
    useEffect(() => {
        loadTodayStatus();
        loadAttendanceRecords();
        loadStats();
        if (isManager) {
            loadTeamAttendance();
        }
    }, []);

    // Reload when view changes
    useEffect(() => {
        if (view === 'history') {
            loadAttendanceRecords();
        } else if (view === 'calendar') {
            const start = format(startOfMonth(selectedDate), 'yyyy-MM-dd');
            const end = format(endOfMonth(selectedDate), 'yyyy-MM-dd');
            loadAttendanceRecords(start, end);
        } else if (view === 'team' && isManager) {
            loadTeamAttendance();
        }
    }, [view, selectedDate]);

    // Get status color
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'present':
                return 'bg-green-100 text-green-800 border-green-300';
            case 'absent':
                return 'bg-red-100 text-red-800 border-red-300';
            case 'on_leave':
                return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            case 'wfh':
                return 'bg-blue-100 text-blue-800 border-blue-300';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-300';
        }
    };

    // Get status icon
    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'present':
                return <CheckCircle className="w-5 h-5" />;
            case 'absent':
                return <XCircle className="w-5 h-5" />;
            case 'on_leave':
                return <Coffee className="w-5 h-5" />;
            case 'wfh':
                return <Home className="w-5 h-5" />;
            default:
                return <Clock className="w-5 h-5" />;
        }
    };

    // Render calendar view
    const renderCalendar = () => {
        const monthStart = startOfMonth(selectedDate);
        const monthEnd = endOfMonth(selectedDate);
        const days = eachDayOfInterval({ start: monthStart, end: monthEnd });

        const recordsByDate = attendanceRecords.reduce((acc, record) => {
            acc[record.date] = record;
            return acc;
        }, {} as Record<string, AttendanceRecord>);

        return (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
                {/* Month navigation */}
                <div className="flex items-center justify-between mb-4">
                    <button
                        onClick={() => setSelectedDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth() - 1))}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    <h3 className="text-lg font-semibold">
                        {format(selectedDate, 'MMMM yyyy')}
                    </h3>
                    <button
                        onClick={() => setSelectedDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth() + 1))}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <ChevronRight className="w-5 h-5" />
                    </button>
                </div>

                {/* Calendar grid */}
                <div className="grid grid-cols-7 gap-2">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                        <div key={day} className="text-center text-sm font-semibold text-gray-600 p-2">
                            {day}
                        </div>
                    ))}
                    {days.map(day => {
                        const dateStr = format(day, 'yyyy-MM-dd');
                        const record = recordsByDate[dateStr];
                        const isToday = isSameDay(day, new Date());

                        return (
                            <div
                                key={dateStr}
                                className={`
                  p-2 text-center rounded-lg border
                  ${isToday ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}
                  ${record ? getStatusColor(record.status) : 'bg-gray-50'}
                `}
                            >
                                <div className="text-sm font-medium">{format(day, 'd')}</div>
                                {record && (
                                    <div className="mt-1 flex justify-center">
                                        {getStatusIcon(record.status)}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    };

    return (
        <div className="max-w-7xl mx-auto p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <Clock className="w-8 h-8 text-blue-600" />
                        Attendance
                    </h1>
                    <p className="text-gray-600 mt-1">Track your attendance and work hours</p>
                </div>

                {/* View tabs */}
                <div className="flex gap-2">
                    <button
                        onClick={() => setView('today')}
                        className={`px-4 py-2 rounded-lg transition-colors ${view === 'today'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        Today
                    </button>
                    <button
                        onClick={() => setView('history')}
                        className={`px-4 py-2 rounded-lg transition-colors ${view === 'history'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        History
                    </button>
                    <button
                        onClick={() => setView('calendar')}
                        className={`px-4 py-2 rounded-lg transition-colors ${view === 'calendar'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        Calendar
                    </button>
                    {isManager && (
                        <button
                            onClick={() => setView('team')}
                            className={`px-4 py-2 rounded-lg transition-colors ${view === 'team'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            Team
                        </button>
                    )}
                </div>
            </div>

            {/* Stats cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                    <div className="bg-white rounded-lg border border-gray-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600">Total Days</p>
                                <p className="text-2xl font-bold text-gray-900">{stats.total_days}</p>
                            </div>
                            <Calendar className="w-8 h-8 text-gray-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-green-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-green-600">Present</p>
                                <p className="text-2xl font-bold text-green-900">{stats.present_days}</p>
                            </div>
                            <CheckCircle className="w-8 h-8 text-green-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-red-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-red-600">Absent</p>
                                <p className="text-2xl font-bold text-red-900">{stats.absent_days}</p>
                            </div>
                            <XCircle className="w-8 h-8 text-red-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-blue-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-blue-600">WFH</p>
                                <p className="text-2xl font-bold text-blue-900">{stats.wfh_days}</p>
                            </div>
                            <Home className="w-8 h-8 text-blue-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-yellow-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-yellow-600">Avg Hours</p>
                                <p className="text-2xl font-bold text-yellow-900">{stats.avg_hours.toFixed(1)}</p>
                            </div>
                            <TrendingUp className="w-8 h-8 text-yellow-400" />
                        </div>
                    </div>
                </div>
            )}

            {/* Today view */}
            {view === 'today' && todayStatus && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Check in/out card */}
                    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Today's Attendance</h2>

                        {/* Status badge */}
                        <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border mb-4 ${getStatusColor(todayStatus.status)}`}>
                            {getStatusIcon(todayStatus.status)}
                            <span className="font-medium capitalize">{todayStatus.status.replace('_', ' ')}</span>
                        </div>

                        {/* Check in info */}
                        {todayStatus.check_in_time && (
                            <div className="bg-white rounded-lg p-4 mb-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <LogIn className="w-5 h-5 text-green-600" />
                                    <span className="font-semibold text-gray-900">Check In</span>
                                </div>
                                <p className="text-2xl font-bold text-gray-900 mb-1">
                                    {format(parseISO(todayStatus.check_in_time), 'hh:mm a')}
                                </p>
                                {todayStatus.check_in_location && (
                                    <div className="flex items-center gap-1 text-sm text-gray-600">
                                        <MapPin className="w-4 h-4" />
                                        <span>{todayStatus.check_in_location}</span>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Check out info */}
                        {todayStatus.check_out_time && (
                            <div className="bg-white rounded-lg p-4 mb-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <LogOut className="w-5 h-5 text-red-600" />
                                    <span className="font-semibold text-gray-900">Check Out</span>
                                </div>
                                <p className="text-2xl font-bold text-gray-900 mb-1">
                                    {format(parseISO(todayStatus.check_out_time), 'hh:mm a')}
                                </p>
                                {todayStatus.check_out_location && (
                                    <div className="flex items-center gap-1 text-sm text-gray-600">
                                        <MapPin className="w-4 h-4" />
                                        <span>{todayStatus.check_out_location}</span>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Hours worked */}
                        {todayStatus.hours_worked !== null && (
                            <div className="bg-white rounded-lg p-4 mb-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <Clock className="w-5 h-5 text-blue-600" />
                                    <span className="font-semibold text-gray-900">Hours Worked</span>
                                </div>
                                <p className="text-2xl font-bold text-gray-900">
                                    {todayStatus.hours_worked.toFixed(1)} hours
                                </p>
                            </div>
                        )}

                        {/* Action buttons */}
                        <div className="flex gap-3">
                            {!todayStatus.check_in_time && (
                                <button
                                    onClick={handleCheckIn}
                                    disabled={checkInLoading}
                                    className="flex-1 bg-green-600 text-white px-4 py-3 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                                >
                                    {checkInLoading ? (
                                        <>
                                            <Loader className="w-5 h-5 animate-spin" />
                                            Checking In...
                                        </>
                                    ) : (
                                        <>
                                            <LogIn className="w-5 h-5" />
                                            Check In
                                        </>
                                    )}
                                </button>
                            )}
                            {todayStatus.check_in_time && !todayStatus.check_out_time && (
                                <button
                                    onClick={handleCheckOut}
                                    disabled={checkOutLoading}
                                    className="flex-1 bg-red-600 text-white px-4 py-3 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                                >
                                    {checkOutLoading ? (
                                        <>
                                            <Loader className="w-5 h-5 animate-spin" />
                                            Checking Out...
                                        </>
                                    ) : (
                                        <>
                                            <LogOut className="w-5 h-5" />
                                            Check Out
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Quick stats */}
                    <div className="bg-white rounded-lg border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">This Month</h2>
                        {stats && (
                            <div className="space-y-4">
                                <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                                    <div className="flex items-center gap-2">
                                        <CheckCircle className="w-5 h-5 text-green-600" />
                                        <span className="font-medium text-gray-900">Present Days</span>
                                    </div>
                                    <span className="text-xl font-bold text-green-600">{stats.present_days}</span>
                                </div>
                                <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                                    <div className="flex items-center gap-2">
                                        <XCircle className="w-5 h-5 text-red-600" />
                                        <span className="font-medium text-gray-900">Absent Days</span>
                                    </div>
                                    <span className="text-xl font-bold text-red-600">{stats.absent_days}</span>
                                </div>
                                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                                    <div className="flex items-center gap-2">
                                        <Home className="w-5 h-5 text-blue-600" />
                                        <span className="font-medium text-gray-900">WFH Days</span>
                                    </div>
                                    <span className="text-xl font-bold text-blue-600">{stats.wfh_days}</span>
                                </div>
                                <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                                    <div className="flex items-center gap-2">
                                        <TrendingUp className="w-5 h-5 text-purple-600" />
                                        <span className="font-medium text-gray-900">Average Hours</span>
                                    </div>
                                    <span className="text-xl font-bold text-purple-600">{stats.avg_hours.toFixed(1)} hrs</span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* History view */}
            {view === 'history' && (
                <div className="bg-white rounded-lg border border-gray-200">
                    <div className="p-4 border-b border-gray-200">
                        <h2 className="text-xl font-semibold text-gray-900">Attendance History</h2>
                    </div>
                    <div className="overflow-x-auto">
                        {loading ? (
                            <div className="flex items-center justify-center p-8">
                                <Loader className="w-6 h-6 animate-spin text-blue-600" />
                            </div>
                        ) : attendanceRecords.length === 0 ? (
                            <div className="text-center p-8 text-gray-500">
                                <Clock className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                <p>No attendance records found</p>
                            </div>
                        ) : (
                            <table className="w-full">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Date</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Check In</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Check Out</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Hours</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Location</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {attendanceRecords.map((record) => (
                                        <tr key={record.attendance_id} className="hover:bg-gray-50">
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                {format(parseISO(record.date), 'MMM dd, yyyy')}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(record.status)}`}>
                                                    {getStatusIcon(record.status)}
                                                    <span className="capitalize">{record.status.replace('_', ' ')}</span>
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                {record.check_in_time ? format(parseISO(record.check_in_time), 'hh:mm a') : '-'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                {record.check_out_time ? format(parseISO(record.check_out_time), 'hh:mm a') : '-'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                {record.hours_worked !== null ? `${record.hours_worked.toFixed(1)} hrs` : '-'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-600">
                                                {record.check_in_location ? (
                                                    <div className="flex items-center gap-1">
                                                        <MapPin className="w-4 h-4" />
                                                        <span className="truncate max-w-xs">{record.check_in_location}</span>
                                                    </div>
                                                ) : '-'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            )}

            {/* Calendar view */}
            {view === 'calendar' && renderCalendar()}

            {/* Team view (for managers) */}
            {view === 'team' && isManager && (
                <div className="bg-white rounded-lg border border-gray-200">
                    <div className="p-4 border-b border-gray-200">
                        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                            <Users className="w-6 h-6 text-blue-600" />
                            Team Attendance Today
                        </h2>
                    </div>
                    <div className="overflow-x-auto">
                        {loading ? (
                            <div className="flex items-center justify-center p-8">
                                <Loader className="w-6 h-6 animate-spin text-blue-600" />
                            </div>
                        ) : teamAttendance.length === 0 ? (
                            <div className="text-center p-8 text-gray-500">
                                <Users className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                <p>No team attendance data available</p>
                            </div>
                        ) : (
                            <table className="w-full">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Employee</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Check In</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Check Out</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Hours</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {teamAttendance.map((record) => (
                                        <tr key={record.attendance_id} className="hover:bg-gray-50">
                                            <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                                {record.employee_name || `Employee ${record.employee_id}`}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(record.status)}`}>
                                                    {getStatusIcon(record.status)}
                                                    <span className="capitalize">{record.status.replace('_', ' ')}</span>
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                {record.check_in_time ? format(parseISO(record.check_in_time), 'hh:mm a') : '-'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                {record.check_out_time ? format(parseISO(record.check_out_time), 'hh:mm a') : '-'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                {record.hours_worked !== null ? `${record.hours_worked.toFixed(1)} hrs` : '-'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default EnhancedAttendanceModule;
