import React, { useState, useEffect } from 'react';
import {
    Calendar,
    Plus,
    X,
    Check,
    Clock,
    User,
    FileText,
    Send,
    AlertCircle,
    CheckCircle,
    XCircle,
    Loader,
    ChevronRight,
    Filter,
    Search
} from 'lucide-react';
import { format, parseISO, differenceInDays } from 'date-fns';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';

interface LeaveRequest {
    leave_id: string;
    employee_id: string;
    employee_name?: string;
    leave_type: string;
    start_date: string;
    end_date: string;
    days_count: number;
    reason: string;
    status: 'pending' | 'approved' | 'rejected' | 'cancelled';
    created_at: string;
    approved_by?: string;
    approved_at?: string;
    rejection_reason?: string;
}

interface LeaveBalance {
    leave_type: string;
    total_days: number;
    used_days: number;
    remaining_days: number;
}

interface EnhancedLeaveModuleProps {
    currentUser?: {
        employee_id: string;
        role: string;
        name?: string;
    };
}

const EnhancedLeaveModule: React.FC<EnhancedLeaveModuleProps> = ({ currentUser }) => {
    const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
    const [balances, setBalances] = useState<LeaveBalance[]>([]);
    const [selectedLeave, setSelectedLeave] = useState<LeaveRequest | null>(null);
    const [showApplyModal, setShowApplyModal] = useState(false);
    const [view, setView] = useState<'my-leaves' | 'approvals'>('my-leaves');
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    // Filters
    const [filterStatus, setFilterStatus] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');

    // Form state
    const [formData, setFormData] = useState({
        leave_type: 'annual',
        start_date: '',
        end_date: '',
        reason: ''
    });

    const { message: wsMessage } = useWebSocket();

    const isManager = currentUser?.role && ['manager', 'hr', 'admin'].includes(currentUser.role.toLowerCase());

    // Load leaves
    const loadLeaves = async () => {
        try {
            setLoading(true);
            const params: any = {};
            if (view === 'approvals' && isManager) {
                params.status = 'pending'; // Only show pending for approvals
            }

            const response = view === 'approvals' && isManager
                ? await api.leaves.getPendingApprovals(params)
                : await api.leaves.getAll(params);

            setLeaves(response.data || []);
        } catch (error: any) {
            console.error('Error loading leaves:', error);
            toast.error('Failed to load leave requests');
        } finally {
            setLoading(false);
        }
    };

    // Load balances
    const loadBalances = async () => {
        try {
            const response = await api.leaves.getBalance();
            setBalances(response.data || []);
        } catch (error: any) {
            console.error('Error loading balances:', error);
        }
    };

    // Apply for leave
    const handleApplyLeave = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.leave_type || !formData.start_date || !formData.end_date || !formData.reason) {
            toast.error('Please fill all required fields');
            return;
        }

        const startDate = new Date(formData.start_date);
        const endDate = new Date(formData.end_date);

        if (endDate < startDate) {
            toast.error('End date must be after start date');
            return;
        }

        try {
            setSubmitting(true);

            await api.leaves.create({
                leave_type: formData.leave_type,
                start_date: formData.start_date,
                end_date: formData.end_date,
                reason: formData.reason
            });

            toast.success('✅ Leave request submitted successfully!');
            setShowApplyModal(false);
            setFormData({ leave_type: 'annual', start_date: '', end_date: '', reason: '' });
            await loadLeaves();
            await loadBalances();
        } catch (error: any) {
            console.error('Error applying leave:', error);
            toast.error(error.response?.data?.detail || 'Failed to submit leave request');
        } finally {
            setSubmitting(false);
        }
    };

    // Approve leave
    const handleApprove = async (leaveId: string) => {
        try {
            await api.leaves.approve(leaveId);
            toast.success('✅ Leave request approved');
            await loadLeaves();
            setSelectedLeave(null);
        } catch (error: any) {
            console.error('Error approving leave:', error);
            toast.error(error.response?.data?.detail || 'Failed to approve leave');
        }
    };

    // Reject leave
    const handleReject = async (leaveId: string) => {
        const reason = prompt('Please provide a reason for rejection:');
        if (!reason) return;

        try {
            await api.leaves.reject(leaveId, { reason });
            toast.success('Leave request rejected');
            await loadLeaves();
            setSelectedLeave(null);
        } catch (error: any) {
            console.error('Error rejecting leave:', error);
            toast.error(error.response?.data?.detail || 'Failed to reject leave');
        }
    };

    // Cancel leave
    const handleCancel = async (leaveId: string) => {
        if (!confirm('Are you sure you want to cancel this leave request?')) return;

        try {
            await api.leaves.cancel(leaveId);
            toast.success('Leave request cancelled');
            await loadLeaves();
            setSelectedLeave(null);
        } catch (error: any) {
            console.error('Error cancelling leave:', error);
            toast.error(error.response?.data?.detail || 'Failed to cancel leave');
        }
    };

    // WebSocket handler
    useEffect(() => {
        if (!wsMessage) return;

        const handleWebSocketMessage = (message: any) => {
            switch (message.type) {
                case 'leave_approved':
                    toast.success(`✅ Leave request approved by ${message.approver_name || 'manager'}`, {
                        icon: '🎉',
                        duration: 5000
                    });
                    loadLeaves();
                    loadBalances();
                    break;
                case 'leave_rejected':
                    toast.error(`❌ Leave request rejected: ${message.reason || 'No reason provided'}`, {
                        duration: 5000
                    });
                    loadLeaves();
                    break;
                case 'leave_applied':
                    if (isManager && view === 'approvals') {
                        toast(`📋 New leave request from ${message.employee_name || 'employee'}`, {
                            icon: '🔔',
                            duration: 4000
                        });
                        loadLeaves();
                    }
                    break;
                case 'leave_cancelled':
                    toast(`Leave request cancelled by ${message.employee_name || 'employee'}`, {
                        icon: 'ℹ️'
                    });
                    loadLeaves();
                    break;
            }
        };

        handleWebSocketMessage(wsMessage);
    }, [wsMessage, isManager, view]);

    // Initial load
    useEffect(() => {
        loadLeaves();
        loadBalances();
    }, [view]);

    // Get status color
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'approved':
                return 'bg-green-100 text-green-800 border-green-300';
            case 'rejected':
                return 'bg-red-100 text-red-800 border-red-300';
            case 'pending':
                return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            case 'cancelled':
                return 'bg-gray-100 text-gray-800 border-gray-300';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-300';
        }
    };

    // Get status icon
    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'approved':
                return <CheckCircle className="w-4 h-4" />;
            case 'rejected':
                return <XCircle className="w-4 h-4" />;
            case 'pending':
                return <Clock className="w-4 h-4" />;
            case 'cancelled':
                return <X className="w-4 h-4" />;
            default:
                return <AlertCircle className="w-4 h-4" />;
        }
    };

    // Get leave type color
    const getLeaveTypeColor = (type: string) => {
        switch (type.toLowerCase()) {
            case 'annual':
                return 'bg-blue-100 text-blue-800';
            case 'sick':
                return 'bg-red-100 text-red-800';
            case 'casual':
                return 'bg-green-100 text-green-800';
            case 'maternity':
            case 'paternity':
                return 'bg-purple-100 text-purple-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    // Filter leaves
    const filteredLeaves = leaves.filter(leave => {
        const matchesStatus = filterStatus === 'all' || leave.status === filterStatus;
        const matchesSearch = !searchQuery ||
            leave.reason.toLowerCase().includes(searchQuery.toLowerCase()) ||
            leave.leave_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (leave.employee_name && leave.employee_name.toLowerCase().includes(searchQuery.toLowerCase()));
        return matchesStatus && matchesSearch;
    });

    return (
        <div className="max-w-7xl mx-auto p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <Calendar className="w-8 h-8 text-blue-600" />
                        Leave Management
                    </h1>
                    <p className="text-gray-600 mt-1">Apply for leave and track your balance</p>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={() => setView('my-leaves')}
                        className={`px-4 py-2 rounded-lg transition-colors ${view === 'my-leaves'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        My Leaves
                    </button>
                    {isManager && (
                        <button
                            onClick={() => setView('approvals')}
                            className={`px-4 py-2 rounded-lg transition-colors ${view === 'approvals'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            Approvals
                        </button>
                    )}
                    {view === 'my-leaves' && (
                        <button
                            onClick={() => setShowApplyModal(true)}
                            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                        >
                            <Plus className="w-5 h-5" />
                            Apply Leave
                        </button>
                    )}
                </div>
            </div>

            {/* Leave balance cards */}
            {view === 'my-leaves' && balances.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {balances.map((balance) => (
                        <div key={balance.leave_type} className="bg-white rounded-lg border border-gray-200 p-4">
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="font-semibold text-gray-900 capitalize">{balance.leave_type}</h3>
                                <Calendar className="w-5 h-5 text-gray-400" />
                            </div>
                            <div className="space-y-1">
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-600">Total:</span>
                                    <span className="font-medium text-gray-900">{balance.total_days} days</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-600">Used:</span>
                                    <span className="font-medium text-red-600">{balance.used_days} days</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-600">Remaining:</span>
                                    <span className="font-bold text-green-600">{balance.remaining_days} days</span>
                                </div>
                            </div>
                            <div className="mt-2 bg-gray-200 rounded-full h-2">
                                <div
                                    className="bg-green-600 h-2 rounded-full transition-all"
                                    style={{ width: `${(balance.remaining_days / balance.total_days) * 100}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Filters */}
            <div className="flex gap-4">
                <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search leaves..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>
                <div className="flex items-center gap-2">
                    <Filter className="w-5 h-5 text-gray-400" />
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                        <option value="all">All Status</option>
                        <option value="pending">Pending</option>
                        <option value="approved">Approved</option>
                        <option value="rejected">Rejected</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                </div>
            </div>

            {/* Leave requests list */}
            <div className="bg-white rounded-lg border border-gray-200">
                <div className="p-4 border-b border-gray-200">
                    <h2 className="text-xl font-semibold text-gray-900">
                        {view === 'approvals' ? 'Pending Approvals' : 'Leave Requests'}
                    </h2>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center p-8">
                        <Loader className="w-6 h-6 animate-spin text-blue-600" />
                    </div>
                ) : filteredLeaves.length === 0 ? (
                    <div className="text-center p-8 text-gray-500">
                        <Calendar className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                        <p>No leave requests found</p>
                        {view === 'my-leaves' && (
                            <button
                                onClick={() => setShowApplyModal(true)}
                                className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Apply for Leave
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="divide-y divide-gray-200">
                        {filteredLeaves.map((leave) => (
                            <div
                                key={leave.leave_id}
                                className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                                onClick={() => setSelectedLeave(leave)}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getLeaveTypeColor(leave.leave_type)}`}>
                                                {leave.leave_type}
                                            </span>
                                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(leave.status)}`}>
                                                {getStatusIcon(leave.status)}
                                                {leave.status}
                                            </span>
                                            {view === 'approvals' && leave.employee_name && (
                                                <span className="text-sm text-gray-600 flex items-center gap-1">
                                                    <User className="w-4 h-4" />
                                                    {leave.employee_name}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4 text-sm text-gray-700 mb-2">
                                            <div className="flex items-center gap-1">
                                                <Calendar className="w-4 h-4" />
                                                <span>{format(parseISO(leave.start_date), 'MMM dd, yyyy')}</span>
                                            </div>
                                            <ChevronRight className="w-4 h-4 text-gray-400" />
                                            <div className="flex items-center gap-1">
                                                <Calendar className="w-4 h-4" />
                                                <span>{format(parseISO(leave.end_date), 'MMM dd, yyyy')}</span>
                                            </div>
                                            <span className="text-gray-600">({leave.days_count} days)</span>
                                        </div>
                                        <p className="text-sm text-gray-600 line-clamp-2">{leave.reason}</p>
                                        {leave.rejection_reason && (
                                            <p className="mt-2 text-sm text-red-600 flex items-center gap-1">
                                                <AlertCircle className="w-4 h-4" />
                                                Rejection reason: {leave.rejection_reason}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex flex-col items-end gap-2">
                                        <span className="text-xs text-gray-500">
                                            {formatDistanceToNow(parseISO(leave.created_at), { addSuffix: true })}
                                        </span>
                                        {view === 'approvals' && leave.status === 'pending' && (
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleApprove(leave.leave_id);
                                                    }}
                                                    className="p-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                                                    title="Approve"
                                                >
                                                    <Check className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleReject(leave.leave_id);
                                                    }}
                                                    className="p-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                                                    title="Reject"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </div>
                                        )}
                                        {view === 'my-leaves' && leave.status === 'pending' && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleCancel(leave.leave_id);
                                                }}
                                                className="text-xs text-red-600 hover:text-red-700 font-medium"
                                            >
                                                Cancel
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Apply leave modal */}
            {showApplyModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-md w-full p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold text-gray-900">Apply for Leave</h2>
                            <button
                                onClick={() => {
                                    setShowApplyModal(false);
                                    setFormData({ leave_type: 'annual', start_date: '', end_date: '', reason: '' });
                                }}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleApplyLeave} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Leave Type <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={formData.leave_type}
                                    onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                >
                                    <option value="annual">Annual Leave</option>
                                    <option value="sick">Sick Leave</option>
                                    <option value="casual">Casual Leave</option>
                                    <option value="maternity">Maternity Leave</option>
                                    <option value="paternity">Paternity Leave</option>
                                    <option value="unpaid">Unpaid Leave</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Start Date <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="date"
                                    value={formData.start_date}
                                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    End Date <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="date"
                                    value={formData.end_date}
                                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                />
                            </div>

                            {formData.start_date && formData.end_date && (
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                    <p className="text-sm text-blue-900">
                                        <strong>Duration:</strong> {differenceInDays(new Date(formData.end_date), new Date(formData.start_date)) + 1} days
                                    </p>
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Reason <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={formData.reason}
                                    onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                                    rows={4}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                    placeholder="Please provide a reason for your leave request..."
                                    required
                                />
                            </div>

                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowApplyModal(false);
                                        setFormData({ leave_type: 'annual', start_date: '', end_date: '', reason: '' });
                                    }}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                    {submitting ? (
                                        <>
                                            <Loader className="w-5 h-5 animate-spin" />
                                            Submitting...
                                        </>
                                    ) : (
                                        <>
                                            <Send className="w-5 h-5" />
                                            Submit Request
                                        </>
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Leave detail modal */}
            {selectedLeave && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-2xl w-full p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold text-gray-900">Leave Details</h2>
                            <button
                                onClick={() => setSelectedLeave(null)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div className="flex items-center gap-2">
                                <span className={`px-3 py-1 rounded-lg text-sm font-medium ${getLeaveTypeColor(selectedLeave.leave_type)}`}>
                                    {selectedLeave.leave_type}
                                </span>
                                <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(selectedLeave.status)}`}>
                                    {getStatusIcon(selectedLeave.status)}
                                    {selectedLeave.status}
                                </span>
                            </div>

                            {selectedLeave.employee_name && (
                                <div className="flex items-center gap-2">
                                    <User className="w-5 h-5 text-gray-400" />
                                    <span className="font-medium text-gray-900">{selectedLeave.employee_name}</span>
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <p className="text-sm text-gray-600 mb-1">Start Date</p>
                                    <p className="font-semibold text-gray-900">
                                        {format(parseISO(selectedLeave.start_date), 'MMM dd, yyyy')}
                                    </p>
                                </div>
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <p className="text-sm text-gray-600 mb-1">End Date</p>
                                    <p className="font-semibold text-gray-900">
                                        {format(parseISO(selectedLeave.end_date), 'MMM dd, yyyy')}
                                    </p>
                                </div>
                            </div>

                            <div className="bg-blue-50 rounded-lg p-4">
                                <p className="text-sm text-blue-900">
                                    <strong>Duration:</strong> {selectedLeave.days_count} days
                                </p>
                            </div>

                            <div>
                                <p className="text-sm text-gray-600 mb-2">Reason</p>
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <p className="text-gray-900 whitespace-pre-wrap">{selectedLeave.reason}</p>
                                </div>
                            </div>

                            {selectedLeave.rejection_reason && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                    <p className="text-sm text-red-900 font-medium mb-1 flex items-center gap-1">
                                        <AlertCircle className="w-4 h-4" />
                                        Rejection Reason
                                    </p>
                                    <p className="text-red-800">{selectedLeave.rejection_reason}</p>
                                </div>
                            )}

                            {selectedLeave.approved_by && selectedLeave.approved_at && (
                                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                                    <p className="text-sm text-green-900">
                                        Approved by <strong>{selectedLeave.approved_by}</strong> on{' '}
                                        {format(parseISO(selectedLeave.approved_at), 'MMM dd, yyyy')}
                                    </p>
                                </div>
                            )}

                            <div className="flex justify-between items-center pt-4 border-t border-gray-200">
                                <span className="text-xs text-gray-500">
                                    Applied {formatDistanceToNow(parseISO(selectedLeave.created_at), { addSuffix: true })}
                                </span>
                                {view === 'approvals' && selectedLeave.status === 'pending' && (
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => handleReject(selectedLeave.leave_id)}
                                            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                                        >
                                            <X className="w-5 h-5" />
                                            Reject
                                        </button>
                                        <button
                                            onClick={() => handleApprove(selectedLeave.leave_id)}
                                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                                        >
                                            <Check className="w-5 h-5" />
                                            Approve
                                        </button>
                                    </div>
                                )}
                                {view === 'my-leaves' && selectedLeave.status === 'pending' && (
                                    <button
                                        onClick={() => handleCancel(selectedLeave.leave_id)}
                                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                                    >
                                        Cancel Request
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EnhancedLeaveModule;
