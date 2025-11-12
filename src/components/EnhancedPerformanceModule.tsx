import React, { useState, useEffect } from 'react';
import {
    Award,
    Target,
    TrendingUp,
    Calendar,
    Plus,
    X,
    Check,
    Edit,
    Trash2,
    Eye,
    Star,
    MessageSquare,
    BarChart3,
    Loader,
    Filter,
    Search,
    Send
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';

interface Goal {
    goal_id: string;
    employee_id: string;
    employee_name?: string;
    title: string;
    description: string;
    category: string;
    target_value: number;
    current_value: number;
    unit: string;
    start_date: string;
    end_date: string;
    status: 'not_started' | 'in_progress' | 'completed' | 'cancelled';
    created_at: string;
}

interface Review {
    review_id: string;
    employee_id: string;
    employee_name?: string;
    reviewer_id: string;
    reviewer_name?: string;
    review_period: string;
    overall_rating: number;
    strengths: string;
    areas_for_improvement: string;
    goals_for_next_period: string;
    status: 'draft' | 'submitted' | 'completed';
    review_date: string;
    created_at: string;
}

interface Feedback {
    feedback_id: string;
    employee_id: string;
    employee_name?: string;
    from_employee_id: string;
    from_employee_name?: string;
    feedback_type: '360' | 'peer' | 'manager' | 'self';
    rating: number;
    comments: string;
    created_at: string;
}

interface PerformanceStats {
    total_goals: number;
    completed_goals: number;
    in_progress_goals: number;
    avg_rating: number;
    total_reviews: number;
    pending_reviews: number;
}

interface EnhancedPerformanceModuleProps {
    currentUser?: {
        employee_id: string;
        role: string;
        name?: string;
    };
}

const EnhancedPerformanceModule: React.FC<EnhancedPerformanceModuleProps> = ({ currentUser }) => {
    const [view, setView] = useState<'goals' | 'reviews' | 'feedback' | 'overview'>('overview');
    const [goals, setGoals] = useState<Goal[]>([]);
    const [reviews, setReviews] = useState<Review[]>([]);
    const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
    const [stats, setStats] = useState<PerformanceStats | null>(null);
    const [loading, setLoading] = useState(false);
    const [selectedItem, setSelectedItem] = useState<Goal | Review | Feedback | null>(null);
    const [showAddGoalModal, setShowAddGoalModal] = useState(false);
    const [showAddFeedbackModal, setShowAddFeedbackModal] = useState(false);
    const [filterStatus, setFilterStatus] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');

    // Form states
    const [goalForm, setGoalForm] = useState({
        title: '',
        description: '',
        category: 'individual',
        target_value: '',
        unit: 'tasks',
        start_date: '',
        end_date: ''
    });

    const [feedbackForm, setFeedbackForm] = useState({
        employee_id: '',
        feedback_type: 'peer' as '360' | 'peer' | 'manager' | 'self',
        rating: 5,
        comments: ''
    });

    const { message: wsMessage } = useWebSocket();

    const isManager = currentUser?.role && ['manager', 'hr', 'admin'].includes(currentUser.role.toLowerCase());

    // Load stats
    const loadStats = async () => {
        try {
            const response = await api.performance.getStats();
            setStats(response.data);
        } catch (error: any) {
            console.error('Error loading stats:', error);
        }
    };

    // Load goals
    const loadGoals = async () => {
        try {
            setLoading(true);
            const params: any = {};
            if (filterStatus !== 'all') params.status = filterStatus;

            const response = await api.performance.getGoals(params);
            setGoals(response.data || []);
        } catch (error: any) {
            console.error('Error loading goals:', error);
            toast.error('Failed to load goals');
        } finally {
            setLoading(false);
        }
    };

    // Load reviews
    const loadReviews = async () => {
        try {
            setLoading(true);
            const response = await api.performance.getReviews();
            setReviews(response.data || []);
        } catch (error: any) {
            console.error('Error loading reviews:', error);
            toast.error('Failed to load reviews');
        } finally {
            setLoading(false);
        }
    };

    // Load feedback
    const loadFeedback = async () => {
        try {
            setLoading(true);
            const response = await api.performance.getFeedback();
            setFeedbacks(response.data || []);
        } catch (error: any) {
            console.error('Error loading feedback:', error);
            toast.error('Failed to load feedback');
        } finally {
            setLoading(false);
        }
    };

    // Create goal
    const handleCreateGoal = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!goalForm.title || !goalForm.start_date || !goalForm.end_date) {
            toast.error('Please fill all required fields');
            return;
        }

        try {
            await api.performance.createGoal({
                title: goalForm.title,
                description: goalForm.description,
                category: goalForm.category,
                target_value: parseFloat(goalForm.target_value) || 0,
                unit: goalForm.unit,
                start_date: goalForm.start_date,
                end_date: goalForm.end_date
            });

            toast.success('✅ Goal created successfully!');
            setShowAddGoalModal(false);
            setGoalForm({
                title: '',
                description: '',
                category: 'individual',
                target_value: '',
                unit: 'tasks',
                start_date: '',
                end_date: ''
            });
            loadGoals();
            loadStats();
        } catch (error: any) {
            console.error('Error creating goal:', error);
            toast.error(error.response?.data?.detail || 'Failed to create goal');
        }
    };

    // Update goal progress
    const handleUpdateGoalProgress = async (goalId: string, currentValue: number) => {
        try {
            await api.performance.updateGoalProgress(goalId, { current_value: currentValue });
            toast.success('Progress updated!');
            loadGoals();
            loadStats();
        } catch (error: any) {
            console.error('Error updating progress:', error);
            toast.error('Failed to update progress');
        }
    };

    // Submit feedback
    const handleSubmitFeedback = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!feedbackForm.employee_id || !feedbackForm.comments) {
            toast.error('Please fill all required fields');
            return;
        }

        try {
            await api.performance.submitFeedback({
                employee_id: feedbackForm.employee_id,
                feedback_type: feedbackForm.feedback_type,
                rating: feedbackForm.rating,
                comments: feedbackForm.comments
            });

            toast.success('✅ Feedback submitted!');
            setShowAddFeedbackModal(false);
            setFeedbackForm({
                employee_id: '',
                feedback_type: 'peer',
                rating: 5,
                comments: ''
            });
            loadFeedback();
        } catch (error: any) {
            console.error('Error submitting feedback:', error);
            toast.error(error.response?.data?.detail || 'Failed to submit feedback');
        }
    };

    // WebSocket handler
    useEffect(() => {
        if (!wsMessage) return;

        const handleWebSocketMessage = (message: any) => {
            switch (message.type) {
                case 'goal_created':
                case 'goal_updated':
                case 'goal_completed':
                    loadGoals();
                    loadStats();
                    break;
                case 'review_completed':
                    loadReviews();
                    loadStats();
                    break;
                case 'feedback_received':
                    loadFeedback();
                    toast.success('New feedback received!');
                    break;
            }
        };

        handleWebSocketMessage(wsMessage);
    }, [wsMessage]);

    // Initial load
    useEffect(() => {
        loadStats();
        loadGoals();
    }, []);

    // Load data based on view
    useEffect(() => {
        switch (view) {
            case 'goals':
                loadGoals();
                break;
            case 'reviews':
                loadReviews();
                break;
            case 'feedback':
                loadFeedback();
                break;
        }
    }, [view, filterStatus]);

    // Get status color
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'bg-green-100 text-green-800 border-green-300';
            case 'in_progress':
                return 'bg-blue-100 text-blue-800 border-blue-300';
            case 'not_started':
                return 'bg-gray-100 text-gray-800 border-gray-300';
            case 'cancelled':
                return 'bg-red-100 text-red-800 border-red-300';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-300';
        }
    };

    // Get rating stars
    const getRatingStars = (rating: number) => {
        return Array.from({ length: 5 }, (_, i) => (
            <Star
                key={i}
                className={`w-4 h-4 ${i < rating ? 'text-yellow-500 fill-yellow-500' : 'text-gray-300'}`}
            />
        ));
    };

    // Filter items
    const filteredGoals = goals.filter(goal => {
        const matchesStatus = filterStatus === 'all' || goal.status === filterStatus;
        const matchesSearch = !searchQuery ||
            goal.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            goal.description.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesStatus && matchesSearch;
    });

    return (
        <div className="max-w-7xl mx-auto p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <Award className="w-8 h-8 text-blue-600" />
                        Performance Management
                    </h1>
                    <p className="text-gray-600 mt-1">Track goals, reviews, and feedback</p>
                </div>

                <div className="flex gap-2">
                    {view === 'goals' && (
                        <button
                            onClick={() => setShowAddGoalModal(true)}
                            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                        >
                            <Plus className="w-5 h-5" />
                            Add Goal
                        </button>
                    )}
                    {view === 'feedback' && (
                        <button
                            onClick={() => setShowAddFeedbackModal(true)}
                            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                        >
                            <MessageSquare className="w-5 h-5" />
                            Give Feedback
                        </button>
                    )}
                </div>
            </div>

            {/* View tabs */}
            <div className="flex gap-2 overflow-x-auto">
                <button
                    onClick={() => setView('overview')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'overview' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <BarChart3 className="w-5 h-5 inline mr-2" />
                    Overview
                </button>
                <button
                    onClick={() => setView('goals')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'goals' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Target className="w-5 h-5 inline mr-2" />
                    Goals
                </button>
                <button
                    onClick={() => setView('reviews')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'reviews' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Award className="w-5 h-5 inline mr-2" />
                    Reviews
                </button>
                <button
                    onClick={() => setView('feedback')}
                    className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${view === 'feedback' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <MessageSquare className="w-5 h-5 inline mr-2" />
                    Feedback
                </button>
            </div>

            {/* Stats cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    <div className="bg-white rounded-lg border border-gray-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-gray-600">Total Goals</p>
                                <p className="text-2xl font-bold text-gray-900">{stats.total_goals}</p>
                            </div>
                            <Target className="w-8 h-8 text-gray-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-green-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-green-600">Completed</p>
                                <p className="text-2xl font-bold text-green-900">{stats.completed_goals}</p>
                            </div>
                            <Check className="w-8 h-8 text-green-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-blue-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-blue-600">In Progress</p>
                                <p className="text-2xl font-bold text-blue-900">{stats.in_progress_goals}</p>
                            </div>
                            <TrendingUp className="w-8 h-8 text-blue-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-yellow-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-yellow-600">Avg Rating</p>
                                <p className="text-2xl font-bold text-yellow-900">{stats.avg_rating.toFixed(1)}</p>
                            </div>
                            <Star className="w-8 h-8 text-yellow-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-purple-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-purple-600">Total Reviews</p>
                                <p className="text-2xl font-bold text-purple-900">{stats.total_reviews}</p>
                            </div>
                            <Award className="w-8 h-8 text-purple-400" />
                        </div>
                    </div>
                    <div className="bg-white rounded-lg border border-orange-200 p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-orange-600">Pending</p>
                                <p className="text-2xl font-bold text-orange-900">{stats.pending_reviews}</p>
                            </div>
                            <Calendar className="w-8 h-8 text-orange-400" />
                        </div>
                    </div>
                </div>
            )}

            {/* Overview */}
            {view === 'overview' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Goals overview */}
                    <div className="bg-white rounded-lg border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Goals</h2>
                        {goals.slice(0, 5).length === 0 ? (
                            <div className="text-center p-8 text-gray-500">
                                <Target className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                <p>No goals yet</p>
                                <button
                                    onClick={() => {
                                        setView('goals');
                                        setShowAddGoalModal(true);
                                    }}
                                    className="mt-2 text-blue-600 hover:text-blue-700"
                                >
                                    Create your first goal
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {goals.slice(0, 5).map(goal => (
                                    <div key={goal.goal_id} className="border border-gray-200 rounded-lg p-3">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="font-semibold text-gray-900">{goal.title}</span>
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(goal.status)}`}>
                                                {goal.status.replace('_', ' ')}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                                                <div
                                                    className="bg-blue-600 h-2 rounded-full transition-all"
                                                    style={{ width: `${Math.min((goal.current_value / goal.target_value) * 100, 100)}%` }}
                                                />
                                            </div>
                                            <span className="text-sm text-gray-600 min-w-20">
                                                {goal.current_value}/{goal.target_value} {goal.unit}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Recent feedback */}
                    <div className="bg-white rounded-lg border border-gray-200 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Feedback</h2>
                        {feedbacks.slice(0, 5).length === 0 ? (
                            <div className="text-center p-8 text-gray-500">
                                <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                <p>No feedback yet</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {feedbacks.slice(0, 5).map(feedback => (
                                    <div key={feedback.feedback_id} className="border border-gray-200 rounded-lg p-3">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm font-medium text-gray-900">
                                                From: {feedback.from_employee_name || 'Anonymous'}
                                            </span>
                                            <div className="flex items-center gap-1">
                                                {getRatingStars(feedback.rating)}
                                            </div>
                                        </div>
                                        <p className="text-sm text-gray-600 line-clamp-2">{feedback.comments}</p>
                                        <span className="text-xs text-gray-500 mt-1 block">
                                            {formatDistanceToNow(parseISO(feedback.created_at), { addSuffix: true })}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Goals view */}
            {view === 'goals' && (
                <div className="space-y-4">
                    {/* Filters */}
                    <div className="flex gap-4">
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Search goals..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <select
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value)}
                            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="all">All Status</option>
                            <option value="not_started">Not Started</option>
                            <option value="in_progress">In Progress</option>
                            <option value="completed">Completed</option>
                            <option value="cancelled">Cancelled</option>
                        </select>
                    </div>

                    {/* Goals list */}
                    <div className="bg-white rounded-lg border border-gray-200">
                        {loading ? (
                            <div className="flex items-center justify-center p-8">
                                <Loader className="w-6 h-6 animate-spin text-blue-600" />
                            </div>
                        ) : filteredGoals.length === 0 ? (
                            <div className="text-center p-8 text-gray-500">
                                <Target className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                <p>No goals found</p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-200">
                                {filteredGoals.map(goal => (
                                    <div key={goal.goal_id} className="p-4 hover:bg-gray-50">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <h3 className="font-semibold text-gray-900">{goal.title}</h3>
                                                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(goal.status)}`}>
                                                        {goal.status.replace('_', ' ')}
                                                    </span>
                                                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-lg text-xs font-medium">
                                                        {goal.category}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-600 mb-3">{goal.description}</p>
                                                <div className="flex items-center gap-4 text-sm text-gray-700">
                                                    <span className="flex items-center gap-1">
                                                        <Calendar className="w-4 h-4" />
                                                        {format(parseISO(goal.start_date), 'MMM dd')} - {format(parseISO(goal.end_date), 'MMM dd, yyyy')}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between text-sm">
                                                <span className="text-gray-600">Progress</span>
                                                <span className="font-semibold text-gray-900">
                                                    {goal.current_value}/{goal.target_value} {goal.unit} ({Math.min((goal.current_value / goal.target_value) * 100, 100).toFixed(0)}%)
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="flex-1 bg-gray-200 rounded-full h-3">
                                                    <div
                                                        className="bg-blue-600 h-3 rounded-full transition-all"
                                                        style={{ width: `${Math.min((goal.current_value / goal.target_value) * 100, 100)}%` }}
                                                    />
                                                </div>
                                                {goal.status === 'in_progress' && (
                                                    <button
                                                        onClick={() => {
                                                            const newValue = prompt(`Update progress (current: ${goal.current_value} ${goal.unit}):`);
                                                            if (newValue) {
                                                                handleUpdateGoalProgress(goal.goal_id, parseFloat(newValue));
                                                            }
                                                        }}
                                                        className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                                                        title="Update progress"
                                                    >
                                                        <Edit className="w-4 h-4" />
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Reviews view */}
            {view === 'reviews' && (
                <div className="bg-white rounded-lg border border-gray-200">
                    <div className="p-4 border-b border-gray-200">
                        <h2 className="text-xl font-semibold text-gray-900">Performance Reviews</h2>
                    </div>
                    {loading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : reviews.length === 0 ? (
                        <div className="text-center p-8 text-gray-500">
                            <Award className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No reviews yet</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-200">
                            {reviews.map(review => (
                                <div key={review.review_id} className="p-4 hover:bg-gray-50">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="font-semibold text-gray-900">{review.employee_name}</span>
                                                <span className="text-sm text-gray-600">- {review.review_period}</span>
                                                <div className="flex items-center gap-1">
                                                    {getRatingStars(review.overall_rating)}
                                                    <span className="text-sm font-semibold text-gray-900 ml-1">
                                                        {review.overall_rating.toFixed(1)}
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="space-y-2 text-sm">
                                                <div>
                                                    <span className="font-medium text-gray-700">Strengths:</span>
                                                    <p className="text-gray-600">{review.strengths}</p>
                                                </div>
                                                <div>
                                                    <span className="font-medium text-gray-700">Areas for Improvement:</span>
                                                    <p className="text-gray-600">{review.areas_for_improvement}</p>
                                                </div>
                                            </div>
                                            <span className="text-xs text-gray-500 mt-2 block">
                                                Reviewed by {review.reviewer_name} on {format(parseISO(review.review_date), 'MMM dd, yyyy')}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Feedback view */}
            {view === 'feedback' && (
                <div className="bg-white rounded-lg border border-gray-200">
                    <div className="p-4 border-b border-gray-200">
                        <h2 className="text-xl font-semibold text-gray-900">Feedback History</h2>
                    </div>
                    {loading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : feedbacks.length === 0 ? (
                        <div className="text-center p-8 text-gray-500">
                            <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No feedback yet</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-200">
                            {feedbacks.map(feedback => (
                                <div key={feedback.feedback_id} className="p-4 hover:bg-gray-50">
                                    <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-gray-900">{feedback.from_employee_name}</span>
                                            <span className="text-sm text-gray-600">→ {feedback.employee_name}</span>
                                            <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-lg text-xs font-medium">
                                                {feedback.feedback_type}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            {getRatingStars(feedback.rating)}
                                        </div>
                                    </div>
                                    <p className="text-sm text-gray-600 mb-2">{feedback.comments}</p>
                                    <span className="text-xs text-gray-500">
                                        {formatDistanceToNow(parseISO(feedback.created_at), { addSuffix: true })}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Add Goal Modal */}
            {showAddGoalModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-md w-full p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold text-gray-900">Create New Goal</h2>
                            <button
                                onClick={() => setShowAddGoalModal(false)}
                                className="p-2 hover:bg-gray-100 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleCreateGoal} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Title <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={goalForm.title}
                                    onChange={(e) => setGoalForm({ ...goalForm, title: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                                <textarea
                                    value={goalForm.description}
                                    onChange={(e) => setGoalForm({ ...goalForm, description: e.target.value })}
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                                    <select
                                        value={goalForm.category}
                                        onChange={(e) => setGoalForm({ ...goalForm, category: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="individual">Individual</option>
                                        <option value="team">Team</option>
                                        <option value="department">Department</option>
                                        <option value="company">Company</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
                                    <select
                                        value={goalForm.unit}
                                        onChange={(e) => setGoalForm({ ...goalForm, unit: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="tasks">Tasks</option>
                                        <option value="hours">Hours</option>
                                        <option value="projects">Projects</option>
                                        <option value="percentage">Percentage</option>
                                        <option value="count">Count</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Target Value</label>
                                <input
                                    type="number"
                                    value={goalForm.target_value}
                                    onChange={(e) => setGoalForm({ ...goalForm, target_value: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    min="0"
                                    step="0.1"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Start Date <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="date"
                                        value={goalForm.start_date}
                                        onChange={(e) => setGoalForm({ ...goalForm, start_date: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        End Date <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="date"
                                        value={goalForm.end_date}
                                        onChange={(e) => setGoalForm({ ...goalForm, end_date: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                        required
                                    />
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowAddGoalModal(false)}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                                >
                                    Create Goal
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Add Feedback Modal */}
            {showAddFeedbackModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-md w-full p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold text-gray-900">Give Feedback</h2>
                            <button
                                onClick={() => setShowAddFeedbackModal(false)}
                                className="p-2 hover:bg-gray-100 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleSubmitFeedback} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Employee ID <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={feedbackForm.employee_id}
                                    onChange={(e) => setFeedbackForm({ ...feedbackForm, employee_id: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    placeholder="Enter employee ID"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Feedback Type</label>
                                <select
                                    value={feedbackForm.feedback_type}
                                    onChange={(e) => setFeedbackForm({ ...feedbackForm, feedback_type: e.target.value as any })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="peer">Peer Feedback</option>
                                    <option value="manager">Manager Feedback</option>
                                    <option value="360">360 Feedback</option>
                                    <option value="self">Self Assessment</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Rating: {feedbackForm.rating}/5
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="5"
                                    value={feedbackForm.rating}
                                    onChange={(e) => setFeedbackForm({ ...feedbackForm, rating: parseInt(e.target.value) })}
                                    className="w-full"
                                />
                                <div className="flex justify-center gap-1 mt-2">
                                    {getRatingStars(feedbackForm.rating)}
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Comments <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={feedbackForm.comments}
                                    onChange={(e) => setFeedbackForm({ ...feedbackForm, comments: e.target.value })}
                                    rows={4}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    placeholder="Share your feedback..."
                                    required
                                />
                            </div>
                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowAddFeedbackModal(false)}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center justify-center gap-2"
                                >
                                    <Send className="w-5 h-5" />
                                    Submit
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EnhancedPerformanceModule;
