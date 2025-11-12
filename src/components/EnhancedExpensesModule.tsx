import React, { useState, useEffect } from 'react';
import {
    DollarSign,
    Plus,
    X,
    Check,
    Clock,
    Upload,
    FileText,
    Calendar,
    CreditCard,
    TrendingUp,
    Download,
    Search,
    Filter,
    Loader,
    Eye,
    CheckCircle,
    XCircle
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';

interface Expense {
    expense_id: string;
    employee_id: string;
    employee_name?: string;
    category: string;
    amount: number;
    currency: string;
    description: string;
    date: string;
    status: 'draft' | 'submitted' | 'approved' | 'rejected' | 'reimbursed';
    receipt_url?: string;
    approver_id?: string;
    approver_name?: string;
    approval_date?: string;
    rejection_reason?: string;
    reimbursement_date?: string;
    created_at: string;
}

interface ExpenseStats {
    total_expenses: number;
    total_amount: number;
    pending_amount: number;
    approved_amount: number;
    reimbursed_amount: number;
    rejected_count: number;
}

interface EnhancedExpensesModuleProps {
    currentUser?: {
        employee_id: string;
        role: string;
        name?: string;
    };
}

const EnhancedExpensesModule: React.FC<EnhancedExpensesModuleProps> = ({ currentUser }) => {
    const [view, setView] = useState<'my-expenses' | 'approvals'>('my-expenses');
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [stats, setStats] = useState<ExpenseStats | null>(null);
    const [loading, setLoading] = useState(false);
    const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [filterStatus, setFilterStatus] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');

    // Form state
    const [expenseForm, setExpenseForm] = useState({
        category: 'travel',
        amount: '',
        currency: 'USD',
        description: '',
        date: format(new Date(), 'yyyy-MM-dd'),
        receipt: null as File | null
    });

    const { lastMessage: wsMessage } = useWebSocket();

    const isManager = currentUser?.role && ['manager', 'hr', 'admin'].includes(currentUser.role.toLowerCase());

    // Load stats
    const loadStats = async () => {
        try {
            const response = await api.expenses.getStats();
            setStats(response.data);
        } catch (error: any) {
            console.error('Error loading stats:', error);
        }
    };

    // Load expenses
    const loadExpenses = async () => {
        try {
            setLoading(true);
            const params: any = {};
            if (filterStatus !== 'all') params.status = filterStatus;

            const response = view === 'approvals' && isManager
                ? await api.expenses.getPendingApprovals(params)
                : await api.expenses.getAll(params);

            setExpenses(response.data || []);
        } catch (error: any) {
            console.error('Error loading expenses:', error);
            toast.error('Failed to load expenses');
        } finally {
            setLoading(false);
        }
    };

    // Submit expense
    const handleSubmitExpense = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!expenseForm.category || !expenseForm.amount || !expenseForm.description) {
            toast.error('Please fill all required fields');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('category', expenseForm.category);
            formData.append('amount', expenseForm.amount);
            formData.append('currency', expenseForm.currency);
            formData.append('description', expenseForm.description);
            formData.append('date', expenseForm.date);
            if (expenseForm.receipt) {
                formData.append('receipt', expenseForm.receipt);
            }

            await api.expenses.create(formData);

            toast.success('✅ Expense submitted successfully!');
            setShowAddModal(false);
            setExpenseForm({
                category: 'travel',
                amount: '',
                currency: 'USD',
                description: '',
                date: format(new Date(), 'yyyy-MM-dd'),
                receipt: null
            });
            loadExpenses();
            loadStats();
        } catch (error: any) {
            console.error('Error submitting expense:', error);
            toast.error(error.response?.data?.detail || 'Failed to submit expense');
        }
    };

    // Approve expense
    const handleApprove = async (expenseId: string) => {
        try {
            await api.expenses.approve(expenseId);
            toast.success('✅ Expense approved');
            loadExpenses();
            setSelectedExpense(null);
        } catch (error: any) {
            console.error('Error approving expense:', error);
            toast.error(error.response?.data?.detail || 'Failed to approve expense');
        }
    };

    // Reject expense
    const handleReject = async (expenseId: string) => {
        const reason = prompt('Please provide a reason for rejection:');
        if (!reason) return;

        try {
            await api.expenses.reject(expenseId, { comments: reason });
            toast.success('Expense rejected');
            loadExpenses();
            setSelectedExpense(null);
        } catch (error: any) {
            console.error('Error rejecting expense:', error);
            toast.error(error.response?.data?.detail || 'Failed to reject expense');
        }
    };

    // WebSocket handler
    useEffect(() => {
        if (!wsMessage) return;

        const handleWebSocketMessage = (message: any) => {
            switch (message.type) {
                case 'expense_submitted':
                    if (isManager && view === 'approvals') {
                        toast(`📋 New expense claim from ${message.employee_name}`, { icon: '💰' });
                        loadExpenses();
                    }
                    loadStats();
                    break;
                case 'expense_approved':
                    toast.success(`✅ Expense approved by ${message.approver_name}`);
                    loadExpenses();
                    loadStats();
                    break;
                case 'expense_rejected':
                    toast.error(`❌ Expense rejected: ${message.reason}`);
                    loadExpenses();
                    break;
                case 'expense_reimbursed':
                    toast.success('💰 Expense reimbursed!', { icon: '🎉' });
                    loadExpenses();
                    loadStats();
                    break;
            }
        };

        handleWebSocketMessage(wsMessage);
    }, [wsMessage, isManager, view]);

    // Initial load
    useEffect(() => {
        loadStats();
        loadExpenses();
    }, [view]);

    // Reload when filters change
    useEffect(() => {
        loadExpenses();
    }, [filterStatus]);

    // Get status color
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'approved':
                return 'bg-green-100 text-green-800 border-green-300';
            case 'rejected':
                return 'bg-red-100 text-red-800 border-red-300';
            case 'submitted':
            case 'pending':
                return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            case 'reimbursed':
                return 'bg-blue-100 text-blue-800 border-blue-300';
            case 'draft':
                return 'bg-gray-100 text-gray-800 border-gray-300';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-300';
        }
    };

    // Get category icon
    const getCategoryIcon = (category: string) => {
        switch (category.toLowerCase()) {
            case 'travel':
                return '✈️';
            case 'meals':
                return '🍽️';
            case 'accommodation':
                return '🏨';
            case 'transport':
                return '🚗';
            case 'office':
                return '🏢';
            case 'equipment':
                return '💻';
            case 'training':
                return '📚';
            default:
                return '💰';
        }
    };

    // Filter expenses
    const filteredExpenses = expenses.filter(expense => {
        const matchesStatus = filterStatus === 'all' || expense.status === filterStatus;
        const matchesSearch = !searchQuery ||
            expense.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
            expense.category.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesStatus && matchesSearch;
    });

    return (
        <div className="max-w-7xl mx-auto p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <DollarSign className="w-8 h-8 text-green-600" />
                        Expense Management
                    </h1>
                    <p className="text-gray-600 mt-1">Submit and track expense claims</p>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={() => setView('my-expenses')}
                        className={`px-4 py-2 rounded-lg transition-colors ${view === 'my-expenses'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        My Expenses
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
                    {view === 'my-expenses' && (
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                        >
                            <Plus className="w-5 h-5" />
                            New Expense
                        </button>
                    )}
                </div>
            </div>

            {/* Stats cards */}
            {stats && view === 'my-expenses' && (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    <div className="bg-white rounded-lg border border-gray-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-gray-600">Total</p>
                                <p className="text-2xl font-bold text-gray-900">{stats.total_expenses}</p>
                            </div>
                            <FileText className="w-8 h-8 text-gray-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-blue-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-blue-600">Total Amount</p>
                                <p className="text-2xl font-bold text-blue-900">${stats.total_amount.toFixed(0)}</p>
                            </div>
                            <DollarSign className="w-8 h-8 text-blue-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-yellow-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-yellow-600">Pending</p>
                                <p className="text-2xl font-bold text-yellow-900">${stats.pending_amount.toFixed(0)}</p>
                            </div>
                            <Clock className="w-8 h-8 text-yellow-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-green-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-green-600">Approved</p>
                                <p className="text-2xl font-bold text-green-900">${stats.approved_amount.toFixed(0)}</p>
                            </div>
                            <CheckCircle className="w-8 h-8 text-green-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-purple-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-purple-600">Reimbursed</p>
                                <p className="text-2xl font-bold text-purple-900">${stats.reimbursed_amount.toFixed(0)}</p>
                            </div>
                            <CreditCard className="w-8 h-8 text-purple-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-red-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-red-600">Rejected</p>
                                <p className="text-2xl font-bold text-red-900">{stats.rejected_count}</p>
                            </div>
                            <XCircle className="w-8 h-8 text-red-400" />
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="flex gap-4">
                <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search expenses..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <div className="flex items-center gap-2">
                    <Filter className="w-5 h-5 text-gray-400" />
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="all">All Status</option>
                        <option value="draft">Draft</option>
                        <option value="submitted">Submitted</option>
                        <option value="approved">Approved</option>
                        <option value="rejected">Rejected</option>
                        <option value="reimbursed">Reimbursed</option>
                    </select>
                </div>
            </div>

            {/* Expenses list */}
            <div className="bg-white rounded-lg border border-gray-200">
                <div className="p-4 border-b border-gray-200">
                    <h2 className="text-xl font-semibold text-gray-900">
                        {view === 'approvals' ? 'Pending Approvals' : 'Expense Claims'}
                    </h2>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center p-8">
                        <Loader className="w-6 h-6 animate-spin text-blue-600" />
                    </div>
                ) : filteredExpenses.length === 0 ? (
                    <div className="text-center p-8 text-gray-500">
                        <DollarSign className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                        <p>No expenses found</p>
                        {view === 'my-expenses' && (
                            <button
                                onClick={() => setShowAddModal(true)}
                                className="mt-4 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                            >
                                Submit Your First Expense
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="divide-y divide-gray-200">
                        {filteredExpenses.map((expense) => (
                            <div
                                key={expense.expense_id}
                                className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                                onClick={() => setSelectedExpense(expense)}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-2xl">{getCategoryIcon(expense.category)}</span>
                                            <span className="font-semibold text-gray-900">{expense.description}</span>
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(expense.status)}`}>
                                                {expense.status}
                                            </span>
                                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-lg text-xs font-medium capitalize">
                                                {expense.category}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4 text-sm text-gray-700">
                                            <span className="flex items-center gap-1">
                                                <Calendar className="w-4 h-4" />
                                                {format(parseISO(expense.date), 'MMM dd, yyyy')}
                                            </span>
                                            {expense.receipt_url && (
                                                <span className="flex items-center gap-1 text-blue-600">
                                                    <FileText className="w-4 h-4" />
                                                    Receipt attached
                                                </span>
                                            )}
                                            {view === 'approvals' && expense.employee_name && (
                                                <span className="text-gray-600">By: {expense.employee_name}</span>
                                            )}
                                        </div>
                                        {expense.rejection_reason && (
                                            <p className="mt-2 text-sm text-red-600 flex items-center gap-1">
                                                <XCircle className="w-4 h-4" />
                                                {expense.rejection_reason}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex flex-col items-end gap-2">
                                        <span className="text-2xl font-bold text-green-600">
                                            {expense.currency} ${expense.amount.toFixed(2)}
                                        </span>
                                        <span className="text-xs text-gray-500">
                                            {formatDistanceToNow(parseISO(expense.created_at), { addSuffix: true })}
                                        </span>
                                        {view === 'approvals' && expense.status === 'submitted' && (
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleApprove(expense.expense_id);
                                                    }}
                                                    className="p-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                                                    title="Approve"
                                                >
                                                    <Check className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleReject(expense.expense_id);
                                                    }}
                                                    className="p-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                                                    title="Reject"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Add Expense Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-md w-full p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold text-gray-900">Submit New Expense</h2>
                            <button
                                onClick={() => setShowAddModal(false)}
                                className="p-2 hover:bg-gray-100 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleSubmitExpense} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Category <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={expenseForm.category}
                                    onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    required
                                >
                                    <option value="travel">Travel</option>
                                    <option value="meals">Meals</option>
                                    <option value="accommodation">Accommodation</option>
                                    <option value="transport">Transport</option>
                                    <option value="office">Office Supplies</option>
                                    <option value="equipment">Equipment</option>
                                    <option value="training">Training</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Amount <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="number"
                                        value={expenseForm.amount}
                                        onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                        placeholder="0.00"
                                        step="0.01"
                                        min="0"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
                                    <select
                                        value={expenseForm.currency}
                                        onChange={(e) => setExpenseForm({ ...expenseForm, currency: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="USD">USD</option>
                                        <option value="EUR">EUR</option>
                                        <option value="GBP">GBP</option>
                                        <option value="INR">INR</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Date <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="date"
                                    value={expenseForm.date}
                                    onChange={(e) => setExpenseForm({ ...expenseForm, date: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Description <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={expenseForm.description}
                                    onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    placeholder="Describe the expense..."
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Receipt (Optional)
                                </label>
                                <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-blue-500 transition-colors">
                                    <input
                                        type="file"
                                        accept="image/*,.pdf"
                                        onChange={(e) => setExpenseForm({ ...expenseForm, receipt: e.target.files?.[0] || null })}
                                        className="hidden"
                                        id="receipt-upload"
                                    />
                                    <label htmlFor="receipt-upload" className="cursor-pointer">
                                        <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                                        <p className="text-sm text-gray-600">
                                            {expenseForm.receipt ? expenseForm.receipt.name : 'Click to upload receipt'}
                                        </p>
                                        <p className="text-xs text-gray-500 mt-1">PNG, JPG or PDF (max 5MB)</p>
                                    </label>
                                </div>
                            </div>

                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowAddModal(false)}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                                >
                                    Submit Expense
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Expense Detail Modal */}
            {selectedExpense && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-2xl w-full p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold text-gray-900">Expense Details</h2>
                            <button
                                onClick={() => setSelectedExpense(null)}
                                className="p-2 hover:bg-gray-100 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div className="flex items-center gap-2">
                                <span className="text-3xl">{getCategoryIcon(selectedExpense.category)}</span>
                                <div className="flex-1">
                                    <h3 className="text-lg font-semibold text-gray-900">{selectedExpense.description}</h3>
                                    <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(selectedExpense.status)}`}>
                                        {selectedExpense.status}
                                    </span>
                                </div>
                                <span className="text-3xl font-bold text-green-600">
                                    {selectedExpense.currency} ${selectedExpense.amount.toFixed(2)}
                                </span>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <p className="text-sm text-gray-600 mb-1">Category</p>
                                    <p className="font-semibold text-gray-900 capitalize">{selectedExpense.category}</p>
                                </div>
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <p className="text-sm text-gray-600 mb-1">Date</p>
                                    <p className="font-semibold text-gray-900">
                                        {format(parseISO(selectedExpense.date), 'MMM dd, yyyy')}
                                    </p>
                                </div>
                            </div>

                            {selectedExpense.employee_name && (
                                <div className="bg-blue-50 rounded-lg p-4">
                                    <p className="text-sm text-blue-900">
                                        <strong>Employee:</strong> {selectedExpense.employee_name}
                                    </p>
                                </div>
                            )}

                            {selectedExpense.receipt_url && (
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <p className="text-sm text-gray-600 mb-2">Receipt</p>
                                    <a
                                        href={selectedExpense.receipt_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-2 text-blue-600 hover:text-blue-700"
                                    >
                                        <FileText className="w-5 h-5" />
                                        View Receipt
                                        <Download className="w-4 h-4" />
                                    </a>
                                </div>
                            )}

                            {selectedExpense.rejection_reason && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                    <p className="text-sm text-red-900 font-medium mb-1 flex items-center gap-1">
                                        <XCircle className="w-4 h-4" />
                                        Rejection Reason
                                    </p>
                                    <p className="text-red-800">{selectedExpense.rejection_reason}</p>
                                </div>
                            )}

                            {selectedExpense.approver_name && selectedExpense.approval_date && (
                                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                                    <p className="text-sm text-green-900">
                                        Approved by <strong>{selectedExpense.approver_name}</strong> on{' '}
                                        {format(parseISO(selectedExpense.approval_date), 'MMM dd, yyyy')}
                                    </p>
                                </div>
                            )}

                            {selectedExpense.reimbursement_date && (
                                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                                    <p className="text-sm text-purple-900">
                                        Reimbursed on {format(parseISO(selectedExpense.reimbursement_date), 'MMM dd, yyyy')}
                                    </p>
                                </div>
                            )}

                            <div className="flex justify-between items-center pt-4 border-t border-gray-200">
                                <span className="text-xs text-gray-500">
                                    Submitted {formatDistanceToNow(parseISO(selectedExpense.created_at), { addSuffix: true })}
                                </span>
                                {view === 'approvals' && selectedExpense.status === 'submitted' && (
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => handleReject(selectedExpense.expense_id)}
                                            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
                                        >
                                            <X className="w-5 h-5" />
                                            Reject
                                        </button>
                                        <button
                                            onClick={() => handleApprove(selectedExpense.expense_id)}
                                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
                                        >
                                            <Check className="w-5 h-5" />
                                            Approve
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EnhancedExpensesModule;
