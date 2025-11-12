import React, { useState, useEffect } from 'react';
import {
  Headphones,
  Plus,
  X,
  Send,
  Clock,
  CheckCircle,
  AlertCircle,
  MessageSquare,
  User,
  Calendar,
  Tag,
  Search,
  Filter,
  Loader
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';

interface Ticket {
  ticket_id: string;
  employee_id: string;
  employee_name?: string;
  title: string;
  description: string;
  category: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  assigned_to?: string;
  assigned_to_name?: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
}

interface TicketComment {
  comment_id: string;
  ticket_id: string;
  employee_id: string;
  employee_name?: string;
  comment: string;
  created_at: string;
}

interface HelpdeskStats {
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  resolved_tickets: number;
  avg_resolution_time: number;
}

const EnhancedHelpdeskModule: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<TicketComment[]>([]);
  const [stats, setStats] = useState<HelpdeskStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [newComment, setNewComment] = useState('');

  const [ticketForm, setTicketForm] = useState({
    title: '',
    description: '',
    category: 'technical',
    priority: 'medium' as 'low' | 'medium' | 'high' | 'urgent'
  });

  const { message: wsMessage } = useWebSocket();

  // Load tickets
  const loadTickets = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (filterStatus !== 'all') params.status = filterStatus;
      if (filterPriority !== 'all') params.priority = filterPriority;
      
      const response = await api.helpdesk.getTickets(params);
      setTickets(response.data || []);
    } catch (error: any) {
      console.error('Error loading tickets:', error);
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  // Load stats
  const loadStats = async () => {
    try {
      const response = await api.helpdesk.getStats();
      setStats(response.data);
    } catch (error: any) {
      console.error('Error loading stats:', error);
    }
  };

  // Load comments
  const loadComments = async (ticketId: string) => {
    try {
      const response = await api.helpdesk.getComments(ticketId);
      setComments(response.data || []);
    } catch (error: any) {
      console.error('Error loading comments:', error);
    }
  };

  // Create ticket
  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!ticketForm.title || !ticketForm.description) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      await api.helpdesk.createTicket(ticketForm);
      toast.success('✅ Ticket created successfully!');
      setShowCreateModal(false);
      setTicketForm({ title: '', description: '', category: 'technical', priority: 'medium' });
      loadTickets();
      loadStats();
    } catch (error: any) {
      console.error('Error creating ticket:', error);
      toast.error('Failed to create ticket');
    }
  };

  // Add comment
  const handleAddComment = async () => {
    if (!newComment.trim() || !selectedTicket) return;

    try {
      await api.helpdesk.addComment(selectedTicket.ticket_id, { comment: newComment });
      setNewComment('');
      loadComments(selectedTicket.ticket_id);
      toast.success('Comment added');
    } catch (error: any) {
      console.error('Error adding comment:', error);
      toast.error('Failed to add comment');
    }
  };

  // WebSocket handler
  useEffect(() => {
    if (!wsMessage) return;

    const handleWebSocketMessage = (message: any) => {
      if (message.type === 'ticket_created' || message.type === 'ticket_updated') {
        loadTickets();
        loadStats();
      }
    };

    handleWebSocketMessage(wsMessage);
  }, [wsMessage]);

  useEffect(() => {
    loadTickets();
    loadStats();
  }, []);

  useEffect(() => {
    loadTickets();
  }, [filterStatus, filterPriority]);

  useEffect(() => {
    if (selectedTicket) {
      loadComments(selectedTicket.ticket_id);
    }
  }, [selectedTicket]);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'in_progress': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'resolved': return 'bg-green-100 text-green-800 border-green-300';
      case 'closed': return 'bg-gray-100 text-gray-800 border-gray-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const filteredTickets = tickets.filter(ticket => {
    const matchesSearch = !searchQuery ||
      ticket.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  return (
    <div className="max-w-7xl mx-auto p-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Headphones className="w-8 h-8 text-blue-600" />
            Helpdesk
          </h1>
          <p className="text-gray-600 mt-1">Submit and track support tickets</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          New Ticket
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-600">Total</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_tickets}</p>
              </div>
              <Headphones className="w-8 h-8 text-gray-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-blue-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-blue-600">Open</p>
                <p className="text-2xl font-bold text-blue-900">{stats.open_tickets}</p>
              </div>
              <AlertCircle className="w-8 h-8 text-blue-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-yellow-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-yellow-600">In Progress</p>
                <p className="text-2xl font-bold text-yellow-900">{stats.in_progress_tickets}</p>
              </div>
              <Clock className="w-8 h-8 text-yellow-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-green-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-green-600">Resolved</p>
                <p className="text-2xl font-bold text-green-900">{stats.resolved_tickets}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
          </div>
          <div className="bg-white rounded-lg border border-purple-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-purple-600">Avg Time</p>
                <p className="text-2xl font-bold text-purple-900">{stats.avg_resolution_time.toFixed(0)}h</p>
              </div>
              <Clock className="w-8 h-8 text-purple-400" />
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search tickets..."
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
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Priority</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Tickets</h2>
          </div>
          <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader className="w-6 h-6 animate-spin text-blue-600" />
              </div>
            ) : filteredTickets.length === 0 ? (
              <div className="text-center p-8 text-gray-500">
                <Headphones className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p>No tickets found</p>
              </div>
            ) : (
              filteredTickets.map((ticket) => (
                <div
                  key={ticket.ticket_id}
                  className={`p-4 hover:bg-gray-50 cursor-pointer ${selectedTicket?.ticket_id === ticket.ticket_id ? 'bg-blue-50' : ''}`}
                  onClick={() => setSelectedTicket(ticket)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">{ticket.title}</h3>
                    <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                      {ticket.priority}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 line-clamp-2 mb-2">{ticket.description}</p>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                      {ticket.status.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-gray-500">
                      {formatDistanceToNow(parseISO(ticket.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200">
          {selectedTicket ? (
            <>
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-xl font-semibold text-gray-900">{selectedTicket.title}</h2>
                  <button onClick={() => setSelectedTicket(null)} className="p-1 hover:bg-gray-100 rounded">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(selectedTicket.status)}`}>
                    {selectedTicket.status.replace('_', ' ')}
                  </span>
                  <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getPriorityColor(selectedTicket.priority)}`}>
                    {selectedTicket.priority}
                  </span>
                  <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-lg text-xs font-medium">
                    {selectedTicket.category}
                  </span>
                </div>
              </div>
              <div className="p-4 space-y-4 max-h-[400px] overflow-y-auto">
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-2">Description</p>
                  <p className="text-gray-900">{selectedTicket.description}</p>
                </div>
                <div className="border-t pt-4">
                  <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <MessageSquare className="w-5 h-5" />
                    Comments ({comments.length})
                  </h3>
                  <div className="space-y-3">
                    {comments.map((comment) => (
                      <div key={comment.comment_id} className="bg-gray-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <User className="w-4 h-4 text-gray-400" />
                          <span className="text-sm font-medium text-gray-900">{comment.employee_name}</span>
                          <span className="text-xs text-gray-500">
                            {formatDistanceToNow(parseISO(comment.created_at), { addSuffix: true })}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">{comment.comment}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="p-4 border-t border-gray-200">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Add a comment..."
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    onKeyPress={(e) => e.key === 'Enter' && handleAddComment()}
                  />
                  <button
                    onClick={handleAddComment}
                    className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full p-8 text-gray-500">
              <div className="text-center">
                <Headphones className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p>Select a ticket to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Create New Ticket</h2>
              <button onClick={() => setShowCreateModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateTicket} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={ticketForm.title}
                  onChange={(e) => setTicketForm({ ...ticketForm, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={ticketForm.description}
                  onChange={(e) => setTicketForm({ ...ticketForm, description: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={ticketForm.category}
                    onChange={(e) => setTicketForm({ ...ticketForm, category: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="technical">Technical</option>
                    <option value="hr">HR</option>
                    <option value="it">IT</option>
                    <option value="facilities">Facilities</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={ticketForm.priority}
                    onChange={(e) => setTicketForm({ ...ticketForm, priority: e.target.value as any })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                >
                  Create Ticket
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedHelpdeskModule;
