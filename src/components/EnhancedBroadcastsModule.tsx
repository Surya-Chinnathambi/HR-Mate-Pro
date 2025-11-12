/**
 * Enhanced Broadcasts Module
 * Create and view company-wide announcements with real-time delivery
 */
import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import {
    Megaphone, Plus, Send, Users, Building, Briefcase, AlertCircle,
    Calendar, Filter, Search, X, ArrowLeft, Check
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { toast } from 'react-hot-toast';

interface Broadcast {
    broadcast_id: number;
    sender_employee_id: number;
    sender_name: string;
    sender_role?: string;
    title: string;
    body: string;
    sent_at: string;
    is_read: boolean;
    read_at?: string;
    metadata?: {
        priority?: string;
        target_scope?: string;
        recipients_count?: number;
    };
}

interface Department {
    id: number;
    name: string;
}

export function EnhancedBroadcastsModule({ currentUser }: { currentUser: any }) {
    const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
    const [selectedBroadcast, setSelectedBroadcast] = useState<Broadcast | null>(null);
    const [loading, setLoading] = useState(false);
    const [composing, setComposing] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterPriority, setFilterPriority] = useState<string>('all');

    // Compose form state
    const [title, setTitle] = useState('');
    const [body, setBody] = useState('');
    const [priority, setPriority] = useState('normal');
    const [targetScope, setTargetScope] = useState('all');
    const [targetDepartmentId, setTargetDepartmentId] = useState<number | null>(null);
    const [targetRole, setTargetRole] = useState('');
    const [sending, setSending] = useState(false);

    const { isConnected, lastMessage } = useWebSocket({
        onMessage: handleWebSocketMessage,
    });

    // Check if user can create broadcasts (HR/Admin/Manager)
    const canCreateBroadcast = ['hr', 'admin', 'manager'].includes(
        currentUser?.role?.toLowerCase() || ''
    );

    useEffect(() => {
        loadBroadcasts();
    }, [filterPriority]);

    function handleWebSocketMessage(message: any) {
        if (message.type === 'broadcast_received') {
            loadBroadcasts();
            toast('📢 ' + message.data.title, { duration: 5000 });
        }
    }

    async function loadBroadcasts() {
        try {
            setLoading(true);
            const params: any = { limit: 100 };
            if (filterPriority !== 'all') {
                params.priority = filterPriority;
            }
            const response = await api.broadcasts.getAll(params);
            setBroadcasts(response.data.broadcasts || []);
        } catch (error) {
            console.error('Failed to load broadcasts:', error);
            toast.error('Failed to load broadcasts');
        } finally {
            setLoading(false);
        }
    }

    async function handleSendBroadcast() {
        if (!title.trim() || !body.trim()) {
            toast.error('Please fill in title and message');
            return;
        }

        if (targetScope === 'department' && !targetDepartmentId) {
            toast.error('Please select a department');
            return;
        }

        if (targetScope === 'role' && !targetRole.trim()) {
            toast.error('Please enter a role');
            return;
        }

        try {
            setSending(true);
            const response = await api.broadcasts.create({
                title: title.trim(),
                body: body.trim(),
                priority,
                target_scope: targetScope,
                target_department_id: targetDepartmentId || undefined,
                target_role: targetRole || undefined,
            });

            toast.success(
                `Broadcast sent to ${response.data.recipients_count} recipients!`
            );

            setComposing(false);
            resetForm();
            await loadBroadcasts();
        } catch (error: any) {
            console.error('Failed to send broadcast:', error);
            toast.error(error.response?.data?.detail || 'Failed to send broadcast');
        } finally {
            setSending(false);
        }
    }

    function resetForm() {
        setTitle('');
        setBody('');
        setPriority('normal');
        setTargetScope('all');
        setTargetDepartmentId(null);
        setTargetRole('');
    }

    // Filter broadcasts
    const filteredBroadcasts = broadcasts.filter(broadcast => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            broadcast.title.toLowerCase().includes(query) ||
            broadcast.body.toLowerCase().includes(query) ||
            broadcast.sender_name.toLowerCase().includes(query)
        );
    });

    const getPriorityColor = (priority?: string) => {
        switch (priority) {
            case 'urgent':
                return 'bg-red-100 text-red-800 border-red-200';
            case 'high':
                return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'normal':
                return 'bg-blue-100 text-blue-800 border-blue-200';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getScopeIcon = (scope?: string) => {
        switch (scope) {
            case 'all':
                return <Users className="w-4 h-4" />;
            case 'department':
                return <Building className="w-4 h-4" />;
            case 'role':
                return <Briefcase className="w-4 h-4" />;
            default:
                return <Users className="w-4 h-4" />;
        }
    };

    return (
        <div className="h-full flex flex-col bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                            <Megaphone className="w-7 h-7 text-blue-600" />
                            Broadcasts
                        </h1>
                        <p className="text-sm text-gray-500 mt-1">
                            {broadcasts.length} announcements
                            {isConnected && (
                                <span className="ml-2 inline-flex items-center">
                                    <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                                    <span className="text-green-600 font-medium">Live</span>
                                </span>
                            )}
                        </p>
                    </div>
                    {canCreateBroadcast && (
                        <button
                            onClick={() => setComposing(true)}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                        >
                            <Plus className="w-4 h-4" />
                            New Broadcast
                        </button>
                    )}
                </div>

                {/* Search and Filters */}
                <div className="mt-4 flex items-center gap-3">
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search broadcasts..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <select
                        value={filterPriority}
                        onChange={(e) => setFilterPriority(e.target.value)}
                        className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="all">All Priorities</option>
                        <option value="urgent">Urgent</option>
                        <option value="high">High</option>
                        <option value="normal">Normal</option>
                        <option value="low">Low</option>
                    </select>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                {composing ? (
                    /* Compose Form */
                    <div className="max-w-3xl mx-auto bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-semibold text-gray-900">Create Broadcast</h2>
                            <button
                                onClick={() => {
                                    setComposing(false);
                                    resetForm();
                                }}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5 text-gray-500" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            {/* Title */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Title *
                                </label>
                                <input
                                    type="text"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="Enter broadcast title"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>

                            {/* Message */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Message *
                                </label>
                                <textarea
                                    value={body}
                                    onChange={(e) => setBody(e.target.value)}
                                    placeholder="Enter broadcast message"
                                    rows={6}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                                />
                            </div>

                            {/* Priority */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Priority
                                </label>
                                <select
                                    value={priority}
                                    onChange={(e) => setPriority(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="low">Low</option>
                                    <option value="normal">Normal</option>
                                    <option value="high">High</option>
                                    <option value="urgent">Urgent</option>
                                </select>
                            </div>

                            {/* Target Scope */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Send To
                                </label>
                                <select
                                    value={targetScope}
                                    onChange={(e) => setTargetScope(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="all">All Employees</option>
                                    <option value="department">Specific Department</option>
                                    <option value="role">Specific Role</option>
                                </select>
                            </div>

                            {/* Department (if selected) */}
                            {targetScope === 'department' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Department *
                                    </label>
                                    <input
                                        type="number"
                                        value={targetDepartmentId || ''}
                                        onChange={(e) => setTargetDepartmentId(parseInt(e.target.value))}
                                        placeholder="Enter department ID"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                            )}

                            {/* Role (if selected) */}
                            {targetScope === 'role' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Role *
                                    </label>
                                    <input
                                        type="text"
                                        value={targetRole}
                                        onChange={(e) => setTargetRole(e.target.value)}
                                        placeholder="Enter role (e.g., manager, employee)"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                            )}

                            {/* Actions */}
                            <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
                                <button
                                    onClick={() => {
                                        setComposing(false);
                                        resetForm();
                                    }}
                                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSendBroadcast}
                                    disabled={!title.trim() || !body.trim() || sending}
                                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                >
                                    {sending ? (
                                        <>
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                            Sending...
                                        </>
                                    ) : (
                                        <>
                                            <Send className="w-4 h-4" />
                                            Send Broadcast
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Broadcasts List */
                    <div className="max-w-5xl mx-auto">
                        {loading ? (
                            <div className="flex items-center justify-center h-64">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                            </div>
                        ) : filteredBroadcasts.length === 0 ? (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                                <Megaphone className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                                <h3 className="text-lg font-medium text-gray-900 mb-2">No broadcasts</h3>
                                <p className="text-gray-500">
                                    {searchQuery ? 'No results found for your search.' : 'No company announcements yet.'}
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {filteredBroadcasts.map((broadcast) => (
                                    <div
                                        key={broadcast.broadcast_id}
                                        className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1">
                                                {/* Header */}
                                                <div className="flex items-center gap-2 mb-2">
                                                    {broadcast.metadata?.priority && (
                                                        <span className={`px-2 py-1 rounded text-xs font-medium ${getPriorityColor(broadcast.metadata.priority)}`}>
                                                            {broadcast.metadata.priority.toUpperCase()}
                                                        </span>
                                                    )}
                                                    {broadcast.metadata?.target_scope && (
                                                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                                                            {getScopeIcon(broadcast.metadata.target_scope)}
                                                            {broadcast.metadata.target_scope}
                                                        </span>
                                                    )}
                                                    {!broadcast.is_read && (
                                                        <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                                                    )}
                                                </div>

                                                {/* Title */}
                                                <h3 className="text-xl font-bold text-gray-900 mb-2">
                                                    {broadcast.title}
                                                </h3>

                                                {/* Body */}
                                                <p className="text-gray-700 mb-3 whitespace-pre-wrap">
                                                    {broadcast.body}
                                                </p>

                                                {/* Footer */}
                                                <div className="flex items-center gap-4 text-sm text-gray-500">
                                                    <span className="flex items-center gap-1">
                                                        <Users className="w-4 h-4" />
                                                        {broadcast.sender_name}
                                                        {broadcast.sender_role && ` • ${broadcast.sender_role}`}
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                        <Calendar className="w-4 h-4" />
                                                        {formatDistanceToNow(new Date(broadcast.sent_at), { addSuffix: true })}
                                                    </span>
                                                    {broadcast.metadata?.recipients_count && (
                                                        <span>
                                                            Sent to {broadcast.metadata.recipients_count} recipients
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
