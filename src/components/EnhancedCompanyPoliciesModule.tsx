import React, { useState, useEffect } from 'react';
import {
    FileText,
    Search,
    Download,
    Eye,
    Check,
    Clock,
    X,
    Plus,
    Filter,
    Loader,
    Calendar,
    User,
    Tag
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';

interface Policy {
    policy_id: string;
    title: string;
    description: string;
    category: string;
    version: string;
    content: string;
    document_url?: string;
    effective_date: string;
    created_by: string;
    created_by_name?: string;
    created_at: string;
    updated_at: string;
    requires_acknowledgment: boolean;
    acknowledged?: boolean;
    acknowledged_at?: string;
}

interface PolicyCategory {
    category: string;
    count: number;
}

interface PolicyStats {
    total_policies: number;
    acknowledged_policies: number;
    pending_acknowledgments: number;
    recent_updates: number;
}

interface EnhancedCompanyPoliciesModuleProps {
    currentUser?: {
        employee_id: string;
        role: string;
        name?: string;
    };
}

const EnhancedCompanyPoliciesModule: React.FC<EnhancedCompanyPoliciesModuleProps> = ({ currentUser }) => {
    const [policies, setPolicies] = useState<Policy[]>([]);
    const [categories, setCategories] = useState<PolicyCategory[]>([]);
    const [stats, setStats] = useState<PolicyStats | null>(null);
    const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterCategory, setFilterCategory] = useState<string>('all');
    const [filterAcknowledged, setFilterAcknowledged] = useState<string>('all');

    const { lastMessage: wsMessage } = useWebSocket();

    const isAdmin = currentUser?.role && ['hr', 'admin'].includes(currentUser.role.toLowerCase());

    // Load policies
    const loadPolicies = async () => {
        try {
            setLoading(true);
            const params: any = {};
            if (filterCategory !== 'all') params.category = filterCategory;

            const response = await api.policies.getAll(params);
            setPolicies(response.data || []);
        } catch (error: any) {
            console.error('Error loading policies:', error);
            toast.error('Failed to load policies');
        } finally {
            setLoading(false);
        }
    };

    // Load categories
    const loadCategories = async () => {
        try {
            const response = await api.policies.getCategories();
            setCategories(response.data || []);
        } catch (error: any) {
            console.error('Error loading categories:', error);
        }
    };

    // Load stats
    const loadStats = async () => {
        try {
            const response = await api.policies.getStats();
            setStats(response.data);
        } catch (error: any) {
            console.error('Error loading stats:', error);
        }
    };

    // Acknowledge policy
    const handleAcknowledge = async (policyId: string) => {
        try {
            await api.policies.acknowledge(policyId);
            toast.success('✅ Policy acknowledged!');
            loadPolicies();
            loadStats();
            if (selectedPolicy?.policy_id === policyId) {
                setSelectedPolicy({ ...selectedPolicy, acknowledged: true, acknowledged_at: new Date().toISOString() });
            }
        } catch (error: any) {
            console.error('Error acknowledging policy:', error);
            toast.error('Failed to acknowledge policy');
        }
    };

    // WebSocket handler
    useEffect(() => {
        if (!wsMessage) return;

        const handleWebSocketMessage = (message: any) => {
            if (message.type === 'policy_published' || message.type === 'policy_updated') {
                toast(`📄 New policy: ${message.title || 'Policy updated'}`, {
                    icon: '🔔',
                    duration: 4000
                });
                loadPolicies();
                loadStats();
            }
        };

        handleWebSocketMessage(wsMessage);
    }, [wsMessage]);

    // Initial load
    useEffect(() => {
        loadPolicies();
        loadCategories();
        loadStats();
    }, []);

    // Reload when filters change
    useEffect(() => {
        loadPolicies();
    }, [filterCategory]);

    // Get category color
    const getCategoryColor = (category: string) => {
        const colors: Record<string, string> = {
            'hr': 'bg-blue-100 text-blue-800',
            'it': 'bg-purple-100 text-purple-800',
            'finance': 'bg-green-100 text-green-800',
            'compliance': 'bg-red-100 text-red-800',
            'security': 'bg-orange-100 text-orange-800',
            'general': 'bg-gray-100 text-gray-800'
        };
        return colors[category.toLowerCase()] || 'bg-gray-100 text-gray-800';
    };

    // Filter policies
    const filteredPolicies = policies.filter(policy => {
        const matchesSearch = !searchQuery ||
            policy.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            policy.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
            policy.category.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesAcknowledgment =
            filterAcknowledged === 'all' ||
            (filterAcknowledged === 'acknowledged' && policy.acknowledged) ||
            (filterAcknowledged === 'pending' && !policy.acknowledged && policy.requires_acknowledgment);

        return matchesSearch && matchesAcknowledgment;
    });

    return (
        <div className="max-w-7xl mx-auto p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <FileText className="w-8 h-8 text-blue-600" />
                        Company Policies
                    </h1>
                    <p className="text-gray-600 mt-1">Access and acknowledge company policies</p>
                </div>

                {isAdmin && (
                    <button
                        onClick={() => toast.success('Create policy feature - coming soon!')}
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                    >
                        <Plus className="w-5 h-5" />
                        New Policy
                    </button>
                )}
            </div>

            {/* Stats cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-white rounded-lg border border-gray-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600">Total Policies</p>
                                <p className="text-2xl font-bold text-gray-900">{stats.total_policies}</p>
                            </div>
                            <FileText className="w-8 h-8 text-gray-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-green-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-green-600">Acknowledged</p>
                                <p className="text-2xl font-bold text-green-900">{stats.acknowledged_policies}</p>
                            </div>
                            <Check className="w-8 h-8 text-green-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-orange-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-orange-600">Pending</p>
                                <p className="text-2xl font-bold text-orange-900">{stats.pending_acknowledgments}</p>
                            </div>
                            <Clock className="w-8 h-8 text-orange-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-blue-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-blue-600">Recent Updates</p>
                                <p className="text-2xl font-bold text-blue-900">{stats.recent_updates}</p>
                            </div>
                            <Calendar className="w-8 h-8 text-blue-400" />
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="flex gap-4 flex-wrap">
                <div className="flex-1 min-w-64 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search policies..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <select
                    value={filterCategory}
                    onChange={(e) => setFilterCategory(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                    <option value="all">All Categories</option>
                    {categories.map(cat => (
                        <option key={cat.category} value={cat.category}>
                            {cat.category} ({cat.count})
                        </option>
                    ))}
                </select>
                <select
                    value={filterAcknowledged}
                    onChange={(e) => setFilterAcknowledged(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                    <option value="all">All Status</option>
                    <option value="pending">Pending Acknowledgment</option>
                    <option value="acknowledged">Acknowledged</option>
                </select>
            </div>

            {/* Policies Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Policies list */}
                <div className="lg:col-span-2 space-y-3">
                    {loading ? (
                        <div className="flex items-center justify-center p-8 bg-white rounded-lg border border-gray-200">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : filteredPolicies.length === 0 ? (
                        <div className="text-center p-8 bg-white rounded-lg border border-gray-200 text-gray-500">
                            <FileText className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No policies found</p>
                        </div>
                    ) : (
                        filteredPolicies.map(policy => (
                            <div
                                key={policy.policy_id}
                                className={`bg-white rounded-lg border p-4 cursor-pointer transition-all ${selectedPolicy?.policy_id === policy.policy_id
                                    ? 'border-blue-500 shadow-md'
                                    : 'border-gray-200 hover:border-blue-300 hover:shadow'
                                    }`}
                                onClick={() => setSelectedPolicy(policy)}
                            >
                                <div className="flex items-start justify-between mb-2">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <h3 className="font-semibold text-gray-900">{policy.title}</h3>
                                            {policy.requires_acknowledgment && !policy.acknowledged && (
                                                <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs font-medium">
                                                    Action Required
                                                </span>
                                            )}
                                            {policy.acknowledged && (
                                                <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium flex items-center gap-1">
                                                    <Check className="w-3 h-3" />
                                                    Acknowledged
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-sm text-gray-600 mb-2 line-clamp-2">{policy.description}</p>
                                        <div className="flex items-center gap-3 text-xs text-gray-500">
                                            <span className={`px-2 py-1 rounded-lg font-medium ${getCategoryColor(policy.category)}`}>
                                                {policy.category}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Tag className="w-3 h-3" />
                                                v{policy.version}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Calendar className="w-3 h-3" />
                                                {format(parseISO(policy.effective_date), 'MMM dd, yyyy')}
                                            </span>
                                        </div>
                                    </div>
                                    <Eye className="w-5 h-5 text-gray-400" />
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* Policy details */}
                <div className="bg-white rounded-lg border border-gray-200 p-6 sticky top-4 max-h-[calc(100vh-8rem)] overflow-y-auto">
                    {selectedPolicy ? (
                        <div className="space-y-4">
                            <div>
                                <div className="flex items-center gap-2 mb-2">
                                    <h2 className="text-xl font-bold text-gray-900">{selectedPolicy.title}</h2>
                                    {selectedPolicy.acknowledged && (
                                        <Check className="w-5 h-5 text-green-600" />
                                    )}
                                </div>
                                <span className={`inline-block px-2 py-1 rounded-lg text-sm font-medium ${getCategoryColor(selectedPolicy.category)}`}>
                                    {selectedPolicy.category}
                                </span>
                            </div>

                            <div className="border-t border-gray-200 pt-4">
                                <p className="text-gray-700 mb-4">{selectedPolicy.description}</p>

                                <div className="space-y-2 text-sm">
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-600">Version:</span>
                                        <span className="font-medium text-gray-900">v{selectedPolicy.version}</span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-600">Effective Date:</span>
                                        <span className="font-medium text-gray-900">
                                            {format(parseISO(selectedPolicy.effective_date), 'MMM dd, yyyy')}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-600">Created By:</span>
                                        <span className="font-medium text-gray-900">{selectedPolicy.created_by_name || 'Admin'}</span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-600">Last Updated:</span>
                                        <span className="font-medium text-gray-900">
                                            {formatDistanceToNow(parseISO(selectedPolicy.updated_at), { addSuffix: true })}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {selectedPolicy.content && (
                                <div className="border-t border-gray-200 pt-4">
                                    <h3 className="font-semibold text-gray-900 mb-2">Policy Content</h3>
                                    <div className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                                        {selectedPolicy.content}
                                    </div>
                                </div>
                            )}

                            {selectedPolicy.acknowledged && selectedPolicy.acknowledged_at && (
                                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                                    <div className="flex items-center gap-2 text-green-800">
                                        <Check className="w-5 h-5" />
                                        <div>
                                            <p className="font-medium">Acknowledged</p>
                                            <p className="text-sm">
                                                {formatDistanceToNow(parseISO(selectedPolicy.acknowledged_at), { addSuffix: true })}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="flex gap-3 pt-4 border-t border-gray-200">
                                {selectedPolicy.document_url && (
                                    <a
                                        href={selectedPolicy.document_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                                    >
                                        <Download className="w-5 h-5" />
                                        Download
                                    </a>
                                )}
                                {selectedPolicy.requires_acknowledgment && !selectedPolicy.acknowledged && (
                                    <button
                                        onClick={() => handleAcknowledge(selectedPolicy.policy_id)}
                                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                                    >
                                        <Check className="w-5 h-5" />
                                        Acknowledge
                                    </button>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="text-center p-8 text-gray-500">
                            <FileText className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>Select a policy to view details</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default EnhancedCompanyPoliciesModule;
