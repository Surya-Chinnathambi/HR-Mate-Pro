import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { Plus, Archive, Pin, Trash2, Edit2, MessageSquare, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface Conversation {
    id: number;
    title: string;
    is_pinned: boolean;
    is_active: boolean;
    is_archived: boolean;
    last_message_at: string;
    message_count: number;
    created_at: string;
}

interface ChatHistorySidebarProps {
    onConversationSelect?: (conversationId: number) => void;
    onNewChat?: () => void;
}

export function ChatHistorySidebar({ onConversationSelect, onNewChat }: ChatHistorySidebarProps) {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [showArchived, setShowArchived] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editTitle, setEditTitle] = useState('');

    useEffect(() => {
        loadConversations();
    }, [showArchived]);

    const loadConversations = async () => {
        try {
            setLoading(true);

            // Load conversations from new AI system with PostgreSQL storage
            const res = await apiClient.get('/ai/conversations', {
                params: { limit: 20 }
            });

            if (res.data.conversations && res.data.conversations.length > 0) {
                // Convert to expected format
                const converted: Conversation[] = res.data.conversations.map((conv: any) => ({
                    id: conv.conversation_id,
                    title: `Chat from ${conv.date}`,
                    is_pinned: false,
                    is_active: true,
                    is_archived: false,
                    last_message_at: conv.last_message_at,
                    message_count: 0,
                    created_at: conv.last_message_at
                }));
                setConversations(converted);
            } else {
                // No old conversations, check today's history
                const historyRes = await apiClient.get('/ai/history', {
                    params: { limit: 50 }
                });

                if (historyRes.data.messages && historyRes.data.messages.length > 0) {
                    const conversation: Conversation = {
                        id: 1,
                        title: `Today's Chat (${historyRes.data.total} messages)`,
                        is_pinned: true,
                        is_active: true,
                        is_archived: false,
                        last_message_at: historyRes.data.messages[0]?.timestamp || new Date().toISOString(),
                        message_count: historyRes.data.total,
                        created_at: historyRes.data.session_date || new Date().toISOString()
                    };
                    setConversations([conversation]);
                    setActiveConversationId(1);
                } else {
                    setConversations([]);
                }
            }
        } catch (error) {
            console.error('Failed to load conversations:', error);
            setConversations([]);
        } finally {
            setLoading(false);
        }
    };

    const createNewChat = async () => {
        try {
            // Clear Redis history for new chat
            await apiClient.delete('/ai/history');
            setActiveConversationId(null);
            setConversations([]);
            if (onNewChat) onNewChat();
        } catch (error) {
            console.error('Failed to create new chat:', error);
        }
    };

    const switchConversation = async (conversationId: number) => {
        try {
            await apiClient.put(`/api/chat/conversations/${conversationId}/activate`);
            setActiveConversationId(conversationId);
            if (onConversationSelect) onConversationSelect(conversationId);
        } catch (error) {
            console.error('Failed to switch conversation:', error);
        }
    };

    const deleteConversation = async (conversationId: number, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm('Delete this conversation? This action cannot be undone.')) return;

        try {
            await apiClient.delete(`/api/chat/conversations/${conversationId}`);
            await loadConversations();
        } catch (error) {
            console.error('Failed to delete conversation:', error);
        }
    };

    const togglePin = async (conversationId: number, isPinned: boolean, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await apiClient.put(`/api/chat/conversations/${conversationId}`, {
                is_pinned: !isPinned
            });
            await loadConversations();
        } catch (error) {
            console.error('Failed to pin conversation:', error);
        }
    };

    const archiveConversation = async (conversationId: number, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await apiClient.put(`/api/chat/conversations/${conversationId}`, {
                is_archived: true
            });
            await loadConversations();
        } catch (error) {
            console.error('Failed to archive conversation:', error);
        }
    };

    const startEdit = (conv: Conversation, e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingId(conv.id);
        setEditTitle(conv.title);
    };

    const saveEdit = async (conversationId: number) => {
        try {
            await apiClient.put(`/api/chat/conversations/${conversationId}`, {
                title: editTitle
            });
            setEditingId(null);
            await loadConversations();
        } catch (error) {
            console.error('Failed to update conversation:', error);
        }
    };

    const cancelEdit = () => {
        setEditingId(null);
        setEditTitle('');
    };

    if (loading) {
        return (
            <div className="w-64 bg-gray-900 dark:bg-gray-950 text-white h-full flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
            </div>
        );
    }

    return (
        <div className="w-64 bg-gray-900 dark:bg-gray-950 text-white h-full flex flex-col border-r border-gray-800">
            {/* Header */}
            <div className="p-4 border-b border-gray-800">
                <button
                    onClick={createNewChat}
                    className="w-full p-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 rounded-lg flex items-center justify-center gap-2 transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                    <Plus size={20} />
                    <span className="font-semibold">New Chat</span>
                </button>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
                {conversations.length === 0 ? (
                    <div className="p-6 text-center">
                        <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                        <p className="text-sm text-gray-400">No conversations yet</p>
                        <p className="text-xs text-gray-500 mt-1">Start a new chat to begin</p>
                    </div>
                ) : (
                    <div className="p-2 space-y-1">
                        {conversations.map((conv) => (
                            <div
                                key={conv.id}
                                onClick={() => switchConversation(conv.id)}
                                className={`p-3 rounded-lg cursor-pointer group transition-all duration-200 ${activeConversationId === conv.id
                                    ? 'bg-gray-800 border border-blue-500 shadow-lg'
                                    : 'hover:bg-gray-800 border border-transparent'
                                    }`}
                            >
                                {editingId === conv.id ? (
                                    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                                        <input
                                            type="text"
                                            value={editTitle}
                                            onChange={(e) => setEditTitle(e.target.value)}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') saveEdit(conv.id);
                                                if (e.key === 'Escape') cancelEdit();
                                            }}
                                            className="flex-1 px-2 py-1 bg-gray-700 rounded text-sm border border-gray-600 focus:outline-none focus:border-blue-500"
                                            placeholder="Enter conversation title"
                                            aria-label="Rename conversation"
                                            autoFocus
                                        />
                                        <button
                                            onClick={() => saveEdit(conv.id)}
                                            className="p-1 hover:bg-green-600 rounded text-xs"
                                        >
                                            ✓
                                        </button>
                                        <button
                                            onClick={cancelEdit}
                                            className="p-1 hover:bg-red-600 rounded text-xs"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                ) : (
                                    <>
                                        <div className="flex items-start justify-between mb-1">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    {conv.is_pinned && (
                                                        <Pin size={12} className="text-yellow-400 flex-shrink-0" />
                                                    )}
                                                    <span className="text-sm font-medium truncate">{conv.title}</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-gray-400">
                                                    <Clock size={10} />
                                                    <span>
                                                        {conv.last_message_at
                                                            ? formatDistanceToNow(new Date(conv.last_message_at), { addSuffix: true })
                                                            : 'No messages'}
                                                    </span>
                                                </div>
                                                <div className="text-xs text-gray-500 mt-1">
                                                    {conv.message_count} {conv.message_count === 1 ? 'message' : 'messages'}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Action Buttons (show on hover) */}
                                        <div className="hidden group-hover:flex gap-1 mt-2">
                                            <button
                                                onClick={(e) => togglePin(conv.id, conv.is_pinned, e)}
                                                className="p-1 hover:bg-yellow-600 rounded flex-1 text-xs flex items-center justify-center gap-1"
                                                title={conv.is_pinned ? 'Unpin' : 'Pin'}
                                            >
                                                <Pin size={12} />
                                            </button>
                                            <button
                                                onClick={(e) => startEdit(conv, e)}
                                                className="p-1 hover:bg-blue-600 rounded flex-1 text-xs flex items-center justify-center gap-1"
                                                title="Rename"
                                            >
                                                <Edit2 size={12} />
                                            </button>
                                            <button
                                                onClick={(e) => archiveConversation(conv.id, e)}
                                                className="p-1 hover:bg-gray-600 rounded flex-1 text-xs flex items-center justify-center gap-1"
                                                title="Archive"
                                            >
                                                <Archive size={12} />
                                            </button>
                                            <button
                                                onClick={(e) => deleteConversation(conv.id, e)}
                                                className="p-1 hover:bg-red-600 rounded flex-1 text-xs flex items-center justify-center gap-1"
                                                title="Delete"
                                            >
                                                <Trash2 size={12} />
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-800">
                <button
                    onClick={() => setShowArchived(!showArchived)}
                    className="w-full p-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg flex items-center justify-center gap-2 transition-colors"
                >
                    <Archive size={16} />
                    <span>{showArchived ? 'Hide Archived' : 'Show Archived'}</span>
                </button>
            </div>
        </div>
    );
}

export default ChatHistorySidebar;
