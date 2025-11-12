/**
 * Enhanced Messaging Module
 * Real-time direct messaging with read receipts
 */
import { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import {
    MessageSquare, Send, Search, X, User, Clock, Check, CheckCheck,
    ArrowLeft, Plus, Filter, Trash2, MoreVertical, Paperclip
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { toast } from 'react-hot-toast';

interface Message {
    message_id: number;
    sender_employee_id: number;
    sender_name: string;
    subject: string;
    body: string;
    sent_at: string;
    is_read: boolean;
    read_at?: string;
    priority?: string;
    metadata?: any;
}

interface Employee {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    role?: string;
    department?: string;
}

export function EnhancedMessagingModule() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [loading, setLoading] = useState(false);
    const [composing, setComposing] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    
    // Compose form state
    const [recipient, setRecipient] = useState<Employee | null>(null);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [priority, setPriority] = useState('normal');
    const [sending, setSending] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    const { isConnected, lastMessage } = useWebSocket({
        onMessage: handleWebSocketMessage,
    });

    // Load initial data
    useEffect(() => {
        loadMessages();
        loadEmployees();
    }, []);

    // Handle WebSocket messages
    function handleWebSocketMessage(message: any) {
        if (message.type === 'message_received') {
            // Add new message to list
            loadMessages();
            toast.success(`New message from ${message.data.sender_name}`);
        }
    }

    async function loadMessages() {
        try {
            setLoading(true);
            const response = await api.messages.getInbox({ limit: 100 });
            setMessages(response.data.messages || []);
        } catch (error) {
            console.error('Failed to load messages:', error);
            toast.error('Failed to load messages');
        } finally {
            setLoading(false);
        }
    }

    async function loadEmployees() {
        try {
            const response = await api.employees.getAll({ limit: 1000 });
            setEmployees(response.data || []);
        } catch (error) {
            console.error('Failed to load employees:', error);
        }
    }

    async function handleSendMessage() {
        if (!recipient || !subject.trim() || !body.trim()) {
            toast.error('Please fill in all fields');
            return;
        }

        try {
            setSending(true);
            await api.messages.send({
                recipient_employee_id: recipient.id,
                subject: subject.trim(),
                body: body.trim(),
                priority,
            });

            toast.success('Message sent successfully!');
            setComposing(false);
            setRecipient(null);
            setSubject('');
            setBody('');
            setPriority('normal');
            
            // Reload messages
            await loadMessages();
        } catch (error) {
            console.error('Failed to send message:', error);
            toast.error('Failed to send message');
        } finally {
            setSending(false);
        }
    }

    async function handleSelectMessage(message: Message) {
        setSelectedMessage(message);
        
        // Mark as read if unread
        if (!message.is_read) {
            try {
                // Mark notification as read (inbox notification associated with this message)
                // This would require getting the notification_id from the message
                // For now, we'll just update local state
                setMessages(prev => 
                    prev.map(m => 
                        m.message_id === message.message_id 
                            ? { ...m, is_read: true, read_at: new Date().toISOString() }
                            : m
                    )
                );
            } catch (error) {
                console.error('Failed to mark message as read:', error);
            }
        }
    }

    // Filter messages
    const filteredMessages = messages.filter(msg => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            msg.sender_name.toLowerCase().includes(query) ||
            msg.subject.toLowerCase().includes(query) ||
            msg.body.toLowerCase().includes(query)
        );
    });

    // Filter employees for recipient search
    const filteredEmployees = employees.filter(emp => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            emp.first_name.toLowerCase().includes(query) ||
            emp.last_name.toLowerCase().includes(query) ||
            emp.email.toLowerCase().includes(query)
        );
    });

    const unreadCount = messages.filter(m => !m.is_read).length;

    return (
        <div className="h-full flex bg-gray-50">
            {/* Messages List Sidebar */}
            <div className={`${selectedMessage && !composing ? 'hidden md:flex' : 'flex'} w-full md:w-96 flex-col bg-white border-r border-gray-200`}>
                {/* Header */}
                <div className="p-4 border-b border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                            <MessageSquare className="w-6 h-6 text-blue-600" />
                            Messages
                        </h2>
                        <button
                            onClick={() => {
                                setComposing(true);
                                setSelectedMessage(null);
                            }}
                            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            title="New Message"
                        >
                            <Plus className="w-5 h-5" />
                        </button>
                    </div>
                    <p className="text-sm text-gray-500">
                        {unreadCount} unread • {messages.length} total
                        {isConnected && (
                            <span className="ml-2 inline-flex items-center">
                                <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                                <span className="text-green-600 font-medium">Live</span>
                            </span>
                        )}
                    </p>

                    {/* Search */}
                    <div className="mt-3 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search messages..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                </div>

                {/* Messages List */}
                <div className="flex-1 overflow-y-auto">
                    {loading ? (
                        <div className="flex items-center justify-center h-64">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : filteredMessages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-64 text-center px-4">
                            <MessageSquare className="w-12 h-12 text-gray-300 mb-3" />
                            <p className="text-gray-500">No messages</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-100">
                            {filteredMessages.map((message) => (
                                <button
                                    key={message.message_id}
                                    onClick={() => handleSelectMessage(message)}
                                    className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                                        selectedMessage?.message_id === message.message_id ? 'bg-blue-50' : ''
                                    } ${!message.is_read ? 'bg-blue-50/30' : ''}`}
                                >
                                    <div className="flex items-start gap-3">
                                        <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                                            <User className="w-5 h-5 text-blue-600" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between gap-2">
                                                <span className={`text-sm font-semibold truncate ${
                                                    message.is_read ? 'text-gray-700' : 'text-gray-900'
                                                }`}>
                                                    {message.sender_name}
                                                </span>
                                                <span className="text-xs text-gray-500 flex-shrink-0">
                                                    {formatDistanceToNow(new Date(message.sent_at), { addSuffix: true })}
                                                </span>
                                            </div>
                                            <p className={`text-sm mt-1 truncate ${
                                                message.is_read ? 'text-gray-600' : 'text-gray-900 font-medium'
                                            }`}>
                                                {message.subject}
                                            </p>
                                            <p className="text-xs text-gray-500 mt-1 truncate">
                                                {message.body}
                                            </p>
                                        </div>
                                        {!message.is_read && (
                                            <div className="flex-shrink-0 w-2 h-2 bg-blue-600 rounded-full"></div>
                                        )}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Message Detail / Compose Area */}
            <div className="flex-1 flex flex-col bg-white">
                {composing ? (
                    /* Compose New Message */
                    <div className="flex flex-col h-full">
                        {/* Compose Header */}
                        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setComposing(false)}
                                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors md:hidden"
                                >
                                    <ArrowLeft className="w-5 h-5" />
                                </button>
                                <h2 className="text-lg font-semibold text-gray-900">New Message</h2>
                            </div>
                            <button
                                onClick={() => {
                                    setComposing(false);
                                    setRecipient(null);
                                    setSubject('');
                                    setBody('');
                                }}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5 text-gray-500" />
                            </button>
                        </div>

                        {/* Compose Form */}
                        <div className="flex-1 overflow-y-auto p-6">
                            <div className="max-w-3xl mx-auto space-y-4">
                                {/* To Field */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        To *
                                    </label>
                                    {recipient ? (
                                        <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                            <div className="flex items-center gap-2">
                                                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                                    <User className="w-4 h-4 text-blue-600" />
                                                </div>
                                                <div>
                                                    <p className="text-sm font-medium text-gray-900">
                                                        {recipient.first_name} {recipient.last_name}
                                                    </p>
                                                    <p className="text-xs text-gray-500">{recipient.email}</p>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => setRecipient(null)}
                                                className="p-1 hover:bg-blue-100 rounded transition-colors"
                                            >
                                                <X className="w-4 h-4 text-gray-500" />
                                            </button>
                                        </div>
                                    ) : (
                                        <div>
                                            <input
                                                type="text"
                                                placeholder="Search for recipient..."
                                                value={searchQuery}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            />
                                            {searchQuery && (
                                                <div className="mt-2 max-h-48 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-100">
                                                    {filteredEmployees.slice(0, 10).map((emp) => (
                                                        <button
                                                            key={emp.id}
                                                            onClick={() => {
                                                                setRecipient(emp);
                                                                setSearchQuery('');
                                                            }}
                                                            className="w-full p-3 text-left hover:bg-gray-50 transition-colors"
                                                        >
                                                            <p className="text-sm font-medium text-gray-900">
                                                                {emp.first_name} {emp.last_name}
                                                            </p>
                                                            <p className="text-xs text-gray-500">{emp.email}</p>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Subject Field */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Subject *
                                    </label>
                                    <input
                                        type="text"
                                        value={subject}
                                        onChange={(e) => setSubject(e.target.value)}
                                        placeholder="Enter message subject"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>

                                {/* Priority Field */}
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

                                {/* Body Field */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Message *
                                    </label>
                                    <textarea
                                        value={body}
                                        onChange={(e) => setBody(e.target.value)}
                                        placeholder="Type your message here..."
                                        rows={10}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                                    />
                                </div>

                                {/* Send Button */}
                                <div className="flex items-center justify-end gap-3 pt-4">
                                    <button
                                        onClick={() => {
                                            setComposing(false);
                                            setRecipient(null);
                                            setSubject('');
                                            setBody('');
                                        }}
                                        className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleSendMessage}
                                        disabled={!recipient || !subject.trim() || !body.trim() || sending}
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
                                                Send Message
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                ) : selectedMessage ? (
                    /* Message Detail View */
                    <div className="flex flex-col h-full">
                        {/* Message Header */}
                        <div className="p-4 border-b border-gray-200">
                            <div className="flex items-center justify-between">
                                <button
                                    onClick={() => setSelectedMessage(null)}
                                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors md:hidden"
                                >
                                    <ArrowLeft className="w-5 h-5" />
                                </button>
                                <div className="flex items-center gap-3 flex-1">
                                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                                        <User className="w-5 h-5 text-blue-600" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-gray-900">{selectedMessage.sender_name}</h3>
                                        <p className="text-sm text-gray-500">
                                            {format(new Date(selectedMessage.sent_at), 'PPpp')}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-1">
                                    {selectedMessage.is_read && (
                                        <div className="text-xs text-green-600 flex items-center gap-1">
                                            <CheckCheck className="w-4 h-4" />
                                            Read
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Message Body */}
                        <div className="flex-1 overflow-y-auto p-6">
                            <div className="max-w-3xl mx-auto">
                                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                                    {selectedMessage.subject}
                                </h2>
                                {selectedMessage.priority && selectedMessage.priority !== 'normal' && (
                                    <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium mb-4 ${
                                        selectedMessage.priority === 'urgent' ? 'bg-red-100 text-red-800' :
                                        selectedMessage.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                                        'bg-blue-100 text-blue-800'
                                    }`}>
                                        {selectedMessage.priority.toUpperCase()} PRIORITY
                                    </span>
                                )}
                                <div className="prose max-w-none">
                                    <p className="text-gray-700 whitespace-pre-wrap">{selectedMessage.body}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Empty State */
                    <div className="flex-1 flex items-center justify-center">
                        <div className="text-center">
                            <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">No message selected</h3>
                            <p className="text-gray-500 mb-4">Choose a message from the list or compose a new one</p>
                            <button
                                onClick={() => setComposing(true)}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
                            >
                                <Plus className="w-4 h-4" />
                                New Message
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
