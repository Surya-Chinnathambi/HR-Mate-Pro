import React, { useState, useEffect } from 'react';
import {
  Users,
  Calendar,
  Clock,
  TrendingUp,
  CheckCircle,
  XCircle,
  Coffee,
  Home,
  AlertCircle,
  BarChart3,
  PieChart,
  Activity,
  UserCheck,
  UserX,
  Briefcase,
  Target,
  Loader,
  Filter,
  Download,
  RefreshCw
} from 'lucide-react';
import { format, parseISO, startOfWeek, endOfWeek, eachDayOfInterval, isSameDay } from 'date-fns';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';

interface TeamMember {
  employee_id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
  department: string;
  position: string;
  avatar_url?: string;
}

interface TeamAttendance {
  employee_id: string;
  employee_name: string;
  date: string;
  status: 'present' | 'absent' | 'on_leave' | 'wfh';
  check_in_time: string | null;
  check_out_time: string | null;
  hours_worked: number | null;
}

interface TeamLeave {
  leave_id: string;
  employee_id: string;
  employee_name: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  days_count: number;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

interface TeamTask {
  task_id: string;
  employee_id: string;
  employee_name: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  due_date: string;
  created_at: string;
}

interface TeamStats {
  total_members: number;
  present_today: number;
  absent_today: number;
  on_leave_today: number;
  wfh_today: number;
  pending_leaves: number;
  active_tasks: number;
  avg_performance_score: number;
}

interface WorkloadData {
  employee_id: string;
  employee_name: string;
  active_tasks: number;
  pending_tasks: number;
  completed_tasks: number;
  workload_percentage: number;
}

const EnhancedMyTeamModule: React.FC = () => {
  const [view, setView] = useState<'overview' | 'attendance' | 'leaves' | 'tasks' | 'workload'>('overview');
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [teamStats, setTeamStats] = useState<TeamStats | null>(null);
  const [teamAttendance, setTeamAttendance] = useState<TeamAttendance[]>([]);
  const [teamLeaves, setTeamLeaves] = useState<TeamLeave[]>([]);
  const [teamTasks, setTeamTasks] = useState<TeamTask[]>([]);
  const [workloadData, setWorkloadData] = useState<WorkloadData[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const { lastMessage: wsMessage } = useWebSocket();

  // Load team members
  const loadTeamMembers = async () => {
    try {
      const response = await api.team.getMembers();
      setTeamMembers(response.data || []);
    } catch (error: any) {
      console.error('Error loading team members:', error);
      toast.error('Failed to load team members');
    }
  };

  // Load team stats
  const loadTeamStats = async () => {
    try {
      const response = await api.team.getStats();
      setTeamStats(response.data);
    } catch (error: any) {
      console.error('Error loading team stats:', error);
    }
  };

  // Load team attendance
  const loadTeamAttendance = async (date?: string) => {
    try {
      setLoading(true);
      const dateParam = date || format(selectedDate, 'yyyy-MM-dd');
      const response = await api.team.getAttendance({ date: dateParam });
      setTeamAttendance(response.data || []);
    } catch (error: any) {
      console.error('Error loading team attendance:', error);
      toast.error('Failed to load team attendance');
    } finally {
      setLoading(false);
    }
  };

  // Load team leaves
  const loadTeamLeaves = async () => {
    try {
      setLoading(true);
      const response = await api.team.getLeaves({ status: filterStatus !== 'all' ? filterStatus : undefined });
      setTeamLeaves(response.data || []);
    } catch (error: any) {
      console.error('Error loading team leaves:', error);
      toast.error('Failed to load team leaves');
    } finally {
      setLoading(false);
    }
  };

  // Load team tasks
  const loadTeamTasks = async () => {
    try {
      setLoading(true);
      const response = await api.team.getTasks();
      setTeamTasks(response.data || []);
    } catch (error: any) {
      console.error('Error loading team tasks:', error);
      toast.error('Failed to load team tasks');
    } finally {
      setLoading(false);
    }
  };

  // Load workload data
  const loadWorkloadData = async () => {
    try {
      setLoading(true);
      const response = await api.team.getWorkload();
      setWorkloadData(response.data || []);
    } catch (error: any) {
      console.error('Error loading workload data:', error);
      toast.error('Failed to load workload data');
    } finally {
      setLoading(false);
    }
  };

  // WebSocket handler
  useEffect(() => {
    if (!wsMessage) return;

    const handleWebSocketMessage = (message: any) => {
      switch (message.type) {
        case 'attendance_checked_in':
        case 'attendance_checked_out':
          if (view === 'attendance' || view === 'overview') {
            loadTeamAttendance();
            loadTeamStats();
          }
          break;
        case 'leave_applied':
        case 'leave_approved':
        case 'leave_rejected':
        case 'leave_cancelled':
          if (view === 'leaves' || view === 'overview') {
            loadTeamLeaves();
            loadTeamStats();
          }
          break;
        case 'task_assigned':
        case 'task_updated':
        case 'task_completed':
          if (view === 'tasks' || view === 'workload' || view === 'overview') {
            loadTeamTasks();
            loadWorkloadData();
            loadTeamStats();
          }
          break;
      }
    };

    handleWebSocketMessage(wsMessage);
  }, [wsMessage, view]);

  // Initial load
  useEffect(() => {
    loadTeamMembers();
    loadTeamStats();
    loadTeamAttendance();
  }, []);

  // Load data based on view
  useEffect(() => {
    switch (view) {
      case 'attendance':
        loadTeamAttendance();
        break;
      case 'leaves':
        loadTeamLeaves();
        break;
      case 'tasks':
        loadTeamTasks();
        break;
      case 'workload':
        loadWorkloadData();
        break;
    }
  }, [view, selectedDate, filterStatus]);

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
      case 'approved':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'rejected':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'present':
        return <CheckCircle className="w-4 h-4" />;
      case 'absent':
        return <XCircle className="w-4 h-4" />;
      case 'on_leave':
        return <Coffee className="w-4 h-4" />;
      case 'wfh':
        return <Home className="w-4 h-4" />;
      default:
        return <AlertCircle className="w-4 h-4" />;
    }
  };

  // Get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'urgent':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
      case 'normal':
        return 'bg-blue-100 text-blue-800';
      case 'low':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Get workload color
  const getWorkloadColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-orange-500';
    if (percentage >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="max-w-7xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="w-8 h-8 text-blue-600" />
            My Team
          </h1>
          <p className="text-gray-600 mt-1">Monitor and manage your team's performance</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => {
              loadTeamStats();
              loadTeamAttendance();
              loadTeamLeaves();
              loadTeamTasks();
              loadWorkloadData();
              toast.success('Data refreshed');
            }}
            className="p-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <button
            onClick={() => toast.success('Export feature coming soon!')}
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
          onClick={() => setView('tasks')}
          className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'tasks'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
        >
          <Target className="w-5 h-5 inline mr-2" />
          Tasks
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
      </div>

      {/* Stats cards */}
      {teamStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-600">Total Team</p>
                <p className="text-2xl font-bold text-gray-900">{teamStats.total_members}</p>
              </div>
              <Users className="w-8 h-8 text-gray-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-green-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-green-600">Present</p>
                <p className="text-2xl font-bold text-green-900">{teamStats.present_today}</p>
              </div>
              <UserCheck className="w-8 h-8 text-green-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-red-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-red-600">Absent</p>
                <p className="text-2xl font-bold text-red-900">{teamStats.absent_today}</p>
              </div>
              <UserX className="w-8 h-8 text-red-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-yellow-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-yellow-600">On Leave</p>
                <p className="text-2xl font-bold text-yellow-900">{teamStats.on_leave_today}</p>
              </div>
              <Coffee className="w-8 h-8 text-yellow-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-blue-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-blue-600">WFH</p>
                <p className="text-2xl font-bold text-blue-900">{teamStats.wfh_today}</p>
              </div>
              <Home className="w-8 h-8 text-blue-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-purple-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-purple-600">Pending Leaves</p>
                <p className="text-2xl font-bold text-purple-900">{teamStats.pending_leaves}</p>
              </div>
              <Calendar className="w-8 h-8 text-purple-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-indigo-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-indigo-600">Active Tasks</p>
                <p className="text-2xl font-bold text-indigo-900">{teamStats.active_tasks}</p>
              </div>
              <Briefcase className="w-8 h-8 text-indigo-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-teal-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-teal-600">Avg Performance</p>
                <p className="text-2xl font-bold text-teal-900">{teamStats.avg_performance_score.toFixed(1)}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-teal-400" />
            </div>
          </div>
        </div>
      )}

      {/* Overview */}
      {view === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Team members list */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Team Members</h2>
            </div>
            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {teamMembers.length === 0 ? (
                <div className="text-center p-8 text-gray-500">
                  <Users className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                  <p>No team members found</p>
                </div>
              ) : (
                teamMembers.map((member) => {
                  const attendance = teamAttendance.find(a => a.employee_id === member.employee_id);
                  return (
                    <div key={member.employee_id} className="p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-semibold">
                            {member.first_name[0]}{member.last_name[0]}
                          </div>
                          <div>
                            <p className="font-semibold text-gray-900">
                              {member.first_name} {member.last_name}
                            </p>
                            <p className="text-sm text-gray-600">{member.position || member.role}</p>
                          </div>
                        </div>
                        {attendance && (
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(attendance.status)}`}>
                            {getStatusIcon(attendance.status)}
                            <span className="capitalize">{attendance.status.replace('_', ' ')}</span>
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Quick stats */}
          <div className="space-y-6">
            {/* Attendance pie chart representation */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Today's Attendance</h2>
              {teamStats && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-green-500 rounded"></div>
                      <span className="text-sm text-gray-700">Present</span>
                    </div>
                    <span className="font-semibold text-gray-900">
                      {teamStats.present_today} ({teamStats.total_members > 0 ? ((teamStats.present_today / teamStats.total_members) * 100).toFixed(0) : 0}%)
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-blue-500 rounded"></div>
                      <span className="text-sm text-gray-700">WFH</span>
                    </div>
                    <span className="font-semibold text-gray-900">
                      {teamStats.wfh_today} ({teamStats.total_members > 0 ? ((teamStats.wfh_today / teamStats.total_members) * 100).toFixed(0) : 0}%)
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-yellow-500 rounded"></div>
                      <span className="text-sm text-gray-700">On Leave</span>
                    </div>
                    <span className="font-semibold text-gray-900">
                      {teamStats.on_leave_today} ({teamStats.total_members > 0 ? ((teamStats.on_leave_today / teamStats.total_members) * 100).toFixed(0) : 0}%)
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-red-500 rounded"></div>
                      <span className="text-sm text-gray-700">Absent</span>
                    </div>
                    <span className="font-semibold text-gray-900">
                      {teamStats.absent_today} ({teamStats.total_members > 0 ? ((teamStats.absent_today / teamStats.total_members) * 100).toFixed(0) : 0}%)
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Pending actions */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Pending Actions</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-yellow-600" />
                    <span className="text-sm font-medium text-gray-900">Leave Approvals</span>
                  </div>
                  <span className="px-3 py-1 bg-yellow-600 text-white rounded-full text-sm font-semibold">
                    {teamStats?.pending_leaves || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-blue-600" />
                    <span className="text-sm font-medium text-gray-900">Active Tasks</span>
                  </div>
                  <span className="px-3 py-1 bg-blue-600 text-white rounded-full text-sm font-semibold">
                    {teamStats?.active_tasks || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Attendance view */}
      {view === 'attendance' && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Team Attendance</h2>
            <input
              type="date"
              value={format(selectedDate, 'yyyy-MM-dd')}
              onChange={(e) => setSelectedDate(new Date(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="overflow-x-auto">
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader className="w-6 h-6 animate-spin text-blue-600" />
              </div>
            ) : teamAttendance.length === 0 ? (
              <div className="text-center p-8 text-gray-500">
                <Clock className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p>No attendance data available</p>
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
                    <tr key={record.employee_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {record.employee_name}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(record.status)}`}>
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

      {/* Leaves view */}
      {view === 'leaves' && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Team Leaves</h2>
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>
          <div className="divide-y divide-gray-200">
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader className="w-6 h-6 animate-spin text-blue-600" />
              </div>
            ) : teamLeaves.length === 0 ? (
              <div className="text-center p-8 text-gray-500">
                <Calendar className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p>No leave requests found</p>
              </div>
            ) : (
              teamLeaves.map((leave) => (
                <div key={leave.leave_id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-semibold text-gray-900">{leave.employee_name}</span>
                        <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${getStatusColor(leave.status)}`}>
                          {leave.status}
                        </span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-lg text-xs font-medium">
                          {leave.leave_type}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-700">
                        <span>{format(parseISO(leave.start_date), 'MMM dd, yyyy')}</span>
                        <span>→</span>
                        <span>{format(parseISO(leave.end_date), 'MMM dd, yyyy')}</span>
                        <span className="text-gray-600">({leave.days_count} days)</span>
                      </div>
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatDistanceToNow(parseISO(leave.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tasks view */}
      {view === 'tasks' && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Team Tasks</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader className="w-6 h-6 animate-spin text-blue-600" />
              </div>
            ) : teamTasks.length === 0 ? (
              <div className="text-center p-8 text-gray-500">
                <Target className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p>No tasks found</p>
              </div>
            ) : (
              teamTasks.map((task) => (
                <div key={task.task_id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getPriorityColor(task.priority)}`}>
                          {task.priority}
                        </span>
                        <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded-lg text-xs font-medium">
                          {task.status}
                        </span>
                      </div>
                      <p className="font-semibold text-gray-900 mb-1">{task.title}</p>
                      <p className="text-sm text-gray-600 mb-2">{task.description}</p>
                      <div className="flex items-center gap-4 text-sm text-gray-700">
                        <span className="flex items-center gap-1">
                          <Users className="w-4 h-4" />
                          {task.employee_name}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          Due: {format(parseISO(task.due_date), 'MMM dd, yyyy')}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Workload view */}
      {view === 'workload' && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Team Workload Distribution</h2>
          </div>
          <div className="p-6">
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader className="w-6 h-6 animate-spin text-blue-600" />
              </div>
            ) : workloadData.length === 0 ? (
              <div className="text-center p-8 text-gray-500">
                <BarChart3 className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p>No workload data available</p>
              </div>
            ) : (
              <div className="space-y-4">
                {workloadData.map((data) => (
                  <div key={data.employee_id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-900">{data.employee_name}</span>
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span>Active: {data.active_tasks}</span>
                        <span>Pending: {data.pending_tasks}</span>
                        <span>Completed: {data.completed_tasks}</span>
                        <span className="font-semibold">{data.workload_percentage}%</span>
                      </div>
                    </div>
                    <div className="relative w-full bg-gray-200 rounded-full h-3">
                      <div
                        className={`absolute top-0 left-0 h-3 rounded-full transition-all ${getWorkloadColor(data.workload_percentage)}`}
                        style={{ width: `${Math.min(data.workload_percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedMyTeamModule;
