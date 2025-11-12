import React, { useState, useEffect } from 'react';
import {
    BarChart3,
    TrendingUp,
    TrendingDown,
    Users,
    Calendar,
    Clock,
    DollarSign,
    Award,
    Activity,
    Download,
    RefreshCw,
    Filter,
    Loader,
    PieChart,
    LineChart
} from 'lucide-react';
import { format, subDays, startOfMonth, endOfMonth, eachDayOfInterval, parseISO } from 'date-fns';
import toast from 'react-hot-toast';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';

interface AttendanceTrend {
    date: string;
    present: number;
    absent: number;
    wfh: number;
    on_leave: number;
}

interface LeaveTrend {
    month: string;
    annual: number;
    sick: number;
    casual: number;
    other: number;
}

interface DepartmentStats {
    department: string;
    total_employees: number;
    present_today: number;
    avg_performance: number;
    active_tasks: number;
}

interface PerformanceMetric {
    metric_name: string;
    current_value: number;
    previous_value: number;
    change_percentage: number;
    trend: 'up' | 'down' | 'stable';
}

interface WorkloadDistribution {
    employee_name: string;
    department: string;
    active_tasks: number;
    completed_tasks: number;
    workload_score: number;
}

interface AnalyticsOverview {
    total_employees: number;
    attendance_rate: number;
    avg_working_hours: number;
    leave_utilization: number;
    task_completion_rate: number;
    avg_performance_score: number;
    total_payroll: number;
    pending_approvals: number;
}

const EnhancedAnalyticsDashboard: React.FC = () => {
    const [view, setView] = useState<'overview' | 'attendance' | 'leaves' | 'performance' | 'workload' | 'departments'>('overview');
    const [timeRange, setTimeRange] = useState<'7days' | '30days' | '90days' | 'year'>('30days');
    const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
    const [attendanceTrends, setAttendanceTrends] = useState<AttendanceTrend[]>([]);
    const [leaveTrends, setLeaveTrends] = useState<LeaveTrend[]>([]);
    const [departmentStats, setDepartmentStats] = useState<DepartmentStats[]>([]);
    const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetric[]>([]);
    const [workloadDistribution, setWorkloadDistribution] = useState<WorkloadDistribution[]>([]);
    const [loading, setLoading] = useState(false);

    const { lastMessage: wsMessage } = useWebSocket();

    // Load analytics overview
    const loadOverview = async () => {
        try {
            const response = await api.analytics.getOverview({ time_range: timeRange });
            setOverview(response.data);
        } catch (error: any) {
            console.error('Error loading overview:', error);
            toast.error('Failed to load analytics overview');
        }
    };

    // Load attendance trends
    const loadAttendanceTrends = async () => {
        try {
            setLoading(true);
            const response = await api.analytics.getAttendanceTrends({ time_range: timeRange });
            setAttendanceTrends(response.data || []);
        } catch (error: any) {
            console.error('Error loading attendance trends:', error);
            toast.error('Failed to load attendance trends');
        } finally {
            setLoading(false);
        }
    };

    // Load leave trends
    const loadLeaveTrends = async () => {
        try {
            setLoading(true);
            const response = await api.analytics.getLeaveTrends({ time_range: timeRange });
            setLeaveTrends(response.data || []);
        } catch (error: any) {
            console.error('Error loading leave trends:', error);
            toast.error('Failed to load leave trends');
        } finally {
            setLoading(false);
        }
    };

    // Load department stats
    const loadDepartmentStats = async () => {
        try {
            setLoading(true);
            const response = await api.analytics.getDepartmentStats();
            setDepartmentStats(response.data || []);
        } catch (error: any) {
            console.error('Error loading department stats:', error);
            toast.error('Failed to load department statistics');
        } finally {
            setLoading(false);
        }
    };

    // Load performance metrics
    const loadPerformanceMetrics = async () => {
        try {
            setLoading(true);
            const response = await api.analytics.getPerformanceMetrics({ time_range: timeRange });
            setPerformanceMetrics(response.data || []);
        } catch (error: any) {
            console.error('Error loading performance metrics:', error);
            toast.error('Failed to load performance metrics');
        } finally {
            setLoading(false);
        }
    };

    // Load workload distribution
    const loadWorkloadDistribution = async () => {
        try {
            setLoading(true);
            const response = await api.analytics.getWorkloadDistribution();
            setWorkloadDistribution(response.data || []);
        } catch (error: any) {
            console.error('Error loading workload distribution:', error);
            toast.error('Failed to load workload distribution');
        } finally {
            setLoading(false);
        }
    };

    // WebSocket handler for real-time updates
    useEffect(() => {
        if (!wsMessage) return;

        const handleWebSocketMessage = (message: any) => {
            // Reload analytics data on relevant events
            const reloadEvents = [
                'attendance_checked_in',
                'attendance_checked_out',
                'leave_approved',
                'leave_rejected',
                'task_completed',
                'performance_updated'
            ];

            if (reloadEvents.includes(message.type)) {
                // Debounce reload to avoid too many API calls
                setTimeout(() => {
                    loadOverview();
                    if (view === 'attendance') loadAttendanceTrends();
                    if (view === 'leaves') loadLeaveTrends();
                    if (view === 'performance') loadPerformanceMetrics();
                    if (view === 'workload') loadWorkloadDistribution();
                    if (view === 'departments') loadDepartmentStats();
                }, 2000);
            }
        };

        handleWebSocketMessage(wsMessage);
    }, [wsMessage, view]);

    // Initial load
    useEffect(() => {
        loadOverview();
        loadAttendanceTrends();
        loadDepartmentStats();
    }, []);

    // Reload data when view or time range changes
    useEffect(() => {
        switch (view) {
            case 'attendance':
                loadAttendanceTrends();
                break;
            case 'leaves':
                loadLeaveTrends();
                break;
            case 'performance':
                loadPerformanceMetrics();
                break;
            case 'workload':
                loadWorkloadDistribution();
                break;
            case 'departments':
                loadDepartmentStats();
                break;
        }
    }, [view, timeRange]);

    // Calculate max value for chart scaling
    const getMaxValue = (data: AttendanceTrend[]) => {
        const maxValues = data.map(d => Math.max(d.present, d.absent, d.wfh, d.on_leave));
        return Math.max(...maxValues, 1);
    };

    // Get trend icon and color
    const getTrendIndicator = (trend: string, changePercentage: number) => {
        if (trend === 'up') {
            return {
                icon: <TrendingUp className="w-4 h-4" />,
                color: 'text-green-600',
                bgColor: 'bg-green-100'
            };
        } else if (trend === 'down') {
            return {
                icon: <TrendingDown className="w-4 h-4" />,
                color: 'text-red-600',
                bgColor: 'bg-red-100'
            };
        }
        return {
            icon: <Activity className="w-4 h-4" />,
            color: 'text-gray-600',
            bgColor: 'bg-gray-100'
        };
    };

    // Export data handler
    const handleExport = () => {
        toast.success('Export feature coming soon!');
    };

    return (
        <div className="max-w-7xl mx-auto p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <BarChart3 className="w-8 h-8 text-blue-600" />
                        Analytics Dashboard
                    </h1>
                    <p className="text-gray-600 mt-1">Real-time insights and data visualization</p>
                </div>

                <div className="flex gap-2">
                    <select
                        value={timeRange}
                        onChange={(e) => setTimeRange(e.target.value as any)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="7days">Last 7 Days</option>
                        <option value="30days">Last 30 Days</option>
                        <option value="90days">Last 90 Days</option>
                        <option value="year">Last Year</option>
                    </select>
                    <button
                        onClick={() => {
                            loadOverview();
                            loadAttendanceTrends();
                            loadLeaveTrends();
                            loadDepartmentStats();
                            loadPerformanceMetrics();
                            loadWorkloadDistribution();
                            toast.success('Data refreshed');
                        }}
                        className="p-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw className="w-5 h-5" />
                    </button>
                    <button
                        onClick={handleExport}
                        className="p-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                        title="Export"
                    >
                        <Download className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* View tabs */}
            <div className="flex gap-2 overflow-x-auto">
                <button
                    onClick={() => setView('overview')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'overview'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Activity className="w-5 h-5 inline mr-2" />
                    Overview
                </button>
                <button
                    onClick={() => setView('attendance')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'attendance'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Clock className="w-5 h-5 inline mr-2" />
                    Attendance
                </button>
                <button
                    onClick={() => setView('leaves')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'leaves'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Calendar className="w-5 h-5 inline mr-2" />
                    Leaves
                </button>
                <button
                    onClick={() => setView('performance')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'performance'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Award className="w-5 h-5 inline mr-2" />
                    Performance
                </button>
                <button
                    onClick={() => setView('workload')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'workload'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <BarChart3 className="w-5 h-5 inline mr-2" />
                    Workload
                </button>
                <button
                    onClick={() => setView('departments')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'departments'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Users className="w-5 h-5 inline mr-2" />
                    Departments
                </button>
            </div>

            {/* Overview */}
            {view === 'overview' && overview && (
                <div className="space-y-6">
                    {/* KPI Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200 p-6">
                            <div className="flex items-center justify-between mb-2">
                                <Users className="w-8 h-8 text-blue-600" />
                                <span className="text-xs font-medium text-blue-600 bg-blue-200 px-2 py-1 rounded-full">
                                    Total
                                </span>
                            </div>
                            <p className="text-3xl font-bold text-blue-900 mb-1">{overview.total_employees}</p>
                            <p className="text-sm text-blue-700">Total Employees</p>
                        </div>

                        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg border border-green-200 p-6">
                            <div className="flex items-center justify-between mb-2">
                                <Clock className="w-8 h-8 text-green-600" />
                                <span className="text-xs font-medium text-green-600 bg-green-200 px-2 py-1 rounded-full">
                                    Today
                                </span>
                            </div>
                            <p className="text-3xl font-bold text-green-900 mb-1">{overview.attendance_rate.toFixed(1)}%</p>
                            <p className="text-sm text-green-700">Attendance Rate</p>
                        </div>

                        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200 p-6">
                            <div className="flex items-center justify-between mb-2">
                                <Award className="w-8 h-8 text-purple-600" />
                                <span className="text-xs font-medium text-purple-600 bg-purple-200 px-2 py-1 rounded-full">
                                    Avg
                                </span>
                            </div>
                            <p className="text-3xl font-bold text-purple-900 mb-1">{overview.avg_performance_score.toFixed(1)}</p>
                            <p className="text-sm text-purple-700">Performance Score</p>
                        </div>

                        <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg border border-orange-200 p-6">
                            <div className="flex items-center justify-between mb-2">
                                <Activity className="w-8 h-8 text-orange-600" />
                                <span className="text-xs font-medium text-orange-600 bg-orange-200 px-2 py-1 rounded-full">
                                    Rate
                                </span>
                            </div>
                            <p className="text-3xl font-bold text-orange-900 mb-1">{overview.task_completion_rate.toFixed(1)}%</p>
                            <p className="text-sm text-orange-700">Task Completion</p>
                        </div>
                    </div>

                    {/* Secondary Metrics */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="bg-white rounded-lg border border-gray-200 p-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-600">Avg Working Hours</p>
                                    <p className="text-2xl font-bold text-gray-900">{overview.avg_working_hours.toFixed(1)}</p>
                                </div>
                                <Clock className="w-8 h-8 text-gray-400" />
                            </div>
                        </div>

                        <div className="bg-white rounded-lg border border-gray-200 p-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-600">Leave Utilization</p>
                                    <p className="text-2xl font-bold text-gray-900">{overview.leave_utilization.toFixed(1)}%</p>
                                </div>
                                <Calendar className="w-8 h-8 text-gray-400" />
                            </div>
                        </div>

                        <div className="bg-white rounded-lg border border-gray-200 p-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-600">Total Payroll</p>
                                    <p className="text-2xl font-bold text-gray-900">${(overview.total_payroll / 1000).toFixed(0)}K</p>
                                </div>
                                <DollarSign className="w-8 h-8 text-gray-400" />
                            </div>
                        </div>

                        <div className="bg-white rounded-lg border border-gray-200 p-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-600">Pending Approvals</p>
                                    <p className="text-2xl font-bold text-gray-900">{overview.pending_approvals}</p>
                                </div>
                                <Activity className="w-8 h-8 text-gray-400" />
                            </div>
                        </div>
                    </div>

                    {/* Quick attendance chart */}
                    <div className="bg-white rounded-lg border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Attendance Trend (Last 7 Days)</h2>
                        {attendanceTrends.length > 0 && (
                            <div className="space-y-2">
                                {attendanceTrends.slice(-7).map((trend, index) => {
                                    const maxValue = getMaxValue(attendanceTrends.slice(-7));
                                    return (
                                        <div key={index} className="space-y-1">
                                            <div className="flex items-center justify-between text-sm">
                                                <span className="text-gray-600">{format(parseISO(trend.date), 'MMM dd')}</span>
                                                <div className="flex gap-4 text-xs">
                                                    <span className="text-green-600">Present: {trend.present}</span>
                                                    <span className="text-blue-600">WFH: {trend.wfh}</span>
                                                    <span className="text-yellow-600">Leave: {trend.on_leave}</span>
                                                    <span className="text-red-600">Absent: {trend.absent}</span>
                                                </div>
                                            </div>
                                            <div className="flex gap-1 h-8">
                                                <div
                                                    className="bg-green-500 rounded transition-all"
                                                    style={{ width: `${(trend.present / maxValue) * 100}%` }}
                                                    title={`Present: ${trend.present}`}
                                                />
                                                <div
                                                    className="bg-blue-500 rounded transition-all"
                                                    style={{ width: `${(trend.wfh / maxValue) * 100}%` }}
                                                    title={`WFH: ${trend.wfh}`}
                                                />
                                                <div
                                                    className="bg-yellow-500 rounded transition-all"
                                                    style={{ width: `${(trend.on_leave / maxValue) * 100}%` }}
                                                    title={`On Leave: ${trend.on_leave}`}
                                                />
                                                <div
                                                    className="bg-red-500 rounded transition-all"
                                                    style={{ width: `${(trend.absent / maxValue) * 100}%` }}
                                                    title={`Absent: ${trend.absent}`}
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Attendance View */}
            {view === 'attendance' && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h2 className="text-xl font-semibold text-gray-900 mb-6">Attendance Trends</h2>
                    {loading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : attendanceTrends.length === 0 ? (
                        <div className="text-center p-8 text-gray-500">
                            <LineChart className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No attendance data available</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {attendanceTrends.map((trend, index) => {
                                const maxValue = getMaxValue(attendanceTrends);
                                const total = trend.present + trend.wfh + trend.on_leave + trend.absent;
                                return (
                                    <div key={index} className="space-y-2">
                                        <div className="flex items-center justify-between text-sm">
                                            <span className="font-medium text-gray-900 min-w-24">
                                                {format(parseISO(trend.date), 'MMM dd, yyyy')}
                                            </span>
                                            <div className="flex gap-4 text-xs">
                                                <span className="text-green-600">
                                                    Present: {trend.present} ({total > 0 ? ((trend.present / total) * 100).toFixed(0) : 0}%)
                                                </span>
                                                <span className="text-blue-600">
                                                    WFH: {trend.wfh} ({total > 0 ? ((trend.wfh / total) * 100).toFixed(0) : 0}%)
                                                </span>
                                                <span className="text-yellow-600">
                                                    Leave: {trend.on_leave} ({total > 0 ? ((trend.on_leave / total) * 100).toFixed(0) : 0}%)
                                                </span>
                                                <span className="text-red-600">
                                                    Absent: {trend.absent} ({total > 0 ? ((trend.absent / total) * 100).toFixed(0) : 0}%)
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex gap-1 h-10 rounded-lg overflow-hidden">
                                            <div
                                                className="bg-green-500 transition-all flex items-center justify-center text-white text-xs font-semibold"
                                                style={{ width: `${(trend.present / maxValue) * 100}%` }}
                                            >
                                                {trend.present > 0 && trend.present}
                                            </div>
                                            <div
                                                className="bg-blue-500 transition-all flex items-center justify-center text-white text-xs font-semibold"
                                                style={{ width: `${(trend.wfh / maxValue) * 100}%` }}
                                            >
                                                {trend.wfh > 0 && trend.wfh}
                                            </div>
                                            <div
                                                className="bg-yellow-500 transition-all flex items-center justify-center text-white text-xs font-semibold"
                                                style={{ width: `${(trend.on_leave / maxValue) * 100}%` }}
                                            >
                                                {trend.on_leave > 0 && trend.on_leave}
                                            </div>
                                            <div
                                                className="bg-red-500 transition-all flex items-center justify-center text-white text-xs font-semibold"
                                                style={{ width: `${(trend.absent / maxValue) * 100}%` }}
                                            >
                                                {trend.absent > 0 && trend.absent}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Leaves View */}
            {view === 'leaves' && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h2 className="text-xl font-semibold text-gray-900 mb-6">Leave Trends</h2>
                    {loading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : leaveTrends.length === 0 ? (
                        <div className="text-center p-8 text-gray-500">
                            <Calendar className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No leave data available</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {leaveTrends.map((trend, index) => {
                                const total = trend.annual + trend.sick + trend.casual + trend.other;
                                const maxValue = Math.max(...leaveTrends.map(t => t.annual + t.sick + t.casual + t.other));
                                return (
                                    <div key={index} className="space-y-2">
                                        <div className="flex items-center justify-between text-sm">
                                            <span className="font-medium text-gray-900 min-w-32">{trend.month}</span>
                                            <div className="flex gap-4 text-xs">
                                                <span className="text-blue-600">Annual: {trend.annual}</span>
                                                <span className="text-red-600">Sick: {trend.sick}</span>
                                                <span className="text-green-600">Casual: {trend.casual}</span>
                                                <span className="text-gray-600">Other: {trend.other}</span>
                                                <span className="font-semibold text-gray-900">Total: {total}</span>
                                            </div>
                                        </div>
                                        <div className="flex gap-1 h-10 rounded-lg overflow-hidden bg-gray-100">
                                            {trend.annual > 0 && (
                                                <div
                                                    className="bg-blue-500 transition-all flex items-center justify-center text-white text-xs font-semibold"
                                                    style={{ width: `${(trend.annual / maxValue) * 100}%` }}
                                                >
                                                    {trend.annual}
                                                </div>
                                            )}
                                            {trend.sick > 0 && (
                                                <div
                                                    className="bg-red-500 transition-all flex items-center justify-center text-white text-xs font-semibold"
                                                    style={{ width: `${(trend.sick / maxValue) * 100}%` }}
                                                >
                                                    {trend.sick}
                                                </div>
                                            )}
                                            {trend.casual > 0 && (
                                                <div
                                                    className="bg-green-500 transition-all flex items-center justify-center text-white text-xs font-semibold"
                                                    style={{ width: `${(trend.casual / maxValue) * 100}%` }}
                                                >
                                                    {trend.casual}
                                                </div>
                                            )}
                                            {trend.other > 0 && (
                                                <div
                                                    className="bg-gray-500 transition-all flex items-center justify-center text-white text-xs font-semibold"
                                                    style={{ width: `${(trend.other / maxValue) * 100}%` }}
                                                >
                                                    {trend.other}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Performance View */}
            {view === 'performance' && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h2 className="text-xl font-semibold text-gray-900 mb-6">Performance Metrics</h2>
                    {loading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : performanceMetrics.length === 0 ? (
                        <div className="text-center p-8 text-gray-500">
                            <Award className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No performance data available</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {performanceMetrics.map((metric, index) => {
                                const indicator = getTrendIndicator(metric.trend, metric.change_percentage);
                                return (
                                    <div key={index} className="bg-gray-50 rounded-lg border border-gray-200 p-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className="font-semibold text-gray-900">{metric.metric_name}</h3>
                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${indicator.bgColor} ${indicator.color}`}>
                                                {indicator.icon}
                                                {Math.abs(metric.change_percentage).toFixed(1)}%
                                            </span>
                                        </div>
                                        <div className="flex items-baseline gap-2">
                                            <p className="text-3xl font-bold text-gray-900">{metric.current_value.toFixed(1)}</p>
                                            <p className="text-sm text-gray-600">from {metric.previous_value.toFixed(1)}</p>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Workload View */}
            {view === 'workload' && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h2 className="text-xl font-semibold text-gray-900 mb-6">Workload Distribution</h2>
                    {loading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : workloadDistribution.length === 0 ? (
                        <div className="text-center p-8 text-gray-500">
                            <BarChart3 className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No workload data available</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {workloadDistribution.map((data, index) => {
                                const totalTasks = data.active_tasks + data.completed_tasks;
                                const completionRate = totalTasks > 0 ? (data.completed_tasks / totalTasks) * 100 : 0;
                                return (
                                    <div key={index} className="border border-gray-200 rounded-lg p-4">
                                        <div className="flex items-center justify-between mb-3">
                                            <div>
                                                <p className="font-semibold text-gray-900">{data.employee_name}</p>
                                                <p className="text-sm text-gray-600">{data.department}</p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-2xl font-bold text-gray-900">{data.workload_score}</p>
                                                <p className="text-xs text-gray-600">Workload Score</p>
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-3 gap-3 mb-3">
                                            <div className="bg-blue-50 rounded-lg p-2 text-center">
                                                <p className="text-xl font-bold text-blue-900">{data.active_tasks}</p>
                                                <p className="text-xs text-blue-700">Active</p>
                                            </div>
                                            <div className="bg-green-50 rounded-lg p-2 text-center">
                                                <p className="text-xl font-bold text-green-900">{data.completed_tasks}</p>
                                                <p className="text-xs text-green-700">Completed</p>
                                            </div>
                                            <div className="bg-purple-50 rounded-lg p-2 text-center">
                                                <p className="text-xl font-bold text-purple-900">{completionRate.toFixed(0)}%</p>
                                                <p className="text-xs text-purple-700">Completion</p>
                                            </div>
                                        </div>
                                        <div className="relative w-full bg-gray-200 rounded-full h-3">
                                            <div
                                                className="absolute top-0 left-0 h-3 rounded-full transition-all bg-gradient-to-r from-blue-500 to-green-500"
                                                style={{ width: `${Math.min(data.workload_score, 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Departments View */}
            {view === 'departments' && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h2 className="text-xl font-semibold text-gray-900 mb-6">Department Statistics</h2>
                    {loading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : departmentStats.length === 0 ? (
                        <div className="text-center p-8 text-gray-500">
                            <Users className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No department data available</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Department</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Total Employees</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Present Today</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Attendance Rate</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Avg Performance</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Active Tasks</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {departmentStats.map((dept, index) => {
                                        const attendanceRate = dept.total_employees > 0
                                            ? (dept.present_today / dept.total_employees) * 100
                                            : 0;
                                        return (
                                            <tr key={index} className="hover:bg-gray-50">
                                                <td className="px-4 py-3 text-sm font-medium text-gray-900">{dept.department}</td>
                                                <td className="px-4 py-3 text-sm text-gray-900">{dept.total_employees}</td>
                                                <td className="px-4 py-3 text-sm text-gray-900">{dept.present_today}</td>
                                                <td className="px-4 py-3">
                                                    <div className="flex items-center gap-2">
                                                        <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-32">
                                                            <div
                                                                className="bg-green-500 h-2 rounded-full transition-all"
                                                                style={{ width: `${attendanceRate}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-sm font-semibold text-gray-900 min-w-12">
                                                            {attendanceRate.toFixed(0)}%
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-lg text-sm font-semibold">
                                                        <Award className="w-4 h-4" />
                                                        {dept.avg_performance.toFixed(1)}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-800 rounded-lg text-sm font-semibold">
                                                        <Activity className="w-4 h-4" />
                                                        {dept.active_tasks}
                                                    </span>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default EnhancedAnalyticsDashboard;
