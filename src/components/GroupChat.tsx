import { useState, useEffect, useRef } from 'react';
import { Box, Paper, TextField, IconButton, Avatar, Typography, Chip, Tooltip } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import CloseIcon from '@mui/icons-material/Close';
import EmojiEmotionsIcon from '@mui/icons-material/EmojiEmotions';
import { format } from 'date-fns';
import api from '../api/client';
import { toast } from 'react-hot-toast';

interface Message {
    id: number;
    sender_id: number;
    sender_name: string;
    sender_role: string;
    message: string;
    message_type: string;
    created_at: string;
    is_edited: boolean;
    reactions?: string;
}

interface GroupChatProps {
    employee: any;
    onClose: () => void;
}

export function GroupChat({ employee, onClose }: GroupChatProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [newMessage, setNewMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [ws, setWs] = useState<WebSocket | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const chatBoxRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Fetch initial messages
    useEffect(() => {
        if (!employee) return;

        const fetchMessages = async () => {
            try {
                const response = await api.get('/group-chat/messages', {
                    params: { limit: 50 }
                });
                setMessages(response.data);
            } catch (error) {
                console.error('Failed to load messages:', error);
                toast.error('Failed to load chat messages');
            }
        };

        fetchMessages();
    }, [employee]);

    // Setup WebSocket connection
    useEffect(() => {
        if (!employee) return;

        const token = localStorage.getItem('token');
        if (!token) return;

        const websocket = new WebSocket(
            `ws://localhost:8000/api/group-chat/ws/${employee.id}?token=${token}`
        );

        websocket.onopen = () => {
            console.log('WebSocket connected');
            setWs(websocket);
        };

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'new_message') {
                setMessages((prev) => [...prev, data.message]);
            } else if (data.type === 'message_edited') {
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === data.message_id
                            ? { ...msg, message: data.new_message, is_edited: true }
                            : msg
                    )
                );
            } else if (data.type === 'message_deleted') {
                setMessages((prev) => prev.filter((msg) => msg.id !== data.message_id));
            } else if (data.type === 'reaction_added') {
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === data.message_id
                            ? { ...msg, reactions: JSON.stringify(data.reactions) }
                            : msg
                    )
                );
            }
        };

        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        websocket.onclose = () => {
            console.log('WebSocket disconnected');
        };

        return () => {
            websocket.close();
        };
    }, [employee]);

    const handleSendMessage = async () => {
        if (!newMessage.trim()) return;

        setLoading(true);
        try {
            await api.post('/group-chat/messages', {
                message: newMessage,
                message_type: 'text'
            });
            setNewMessage('');
        } catch (error: any) {
            console.error('Failed to send message:', error);
            toast.error(error?.response?.data?.detail || 'Failed to send message');
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const getRoleColor = (role: string) => {
        switch (role) {
            case 'super_admin':
                return 'error';
            case 'hr':
                return 'warning';
            case 'manager':
                return 'info';
            default:
                return 'default';
        }
    };

    const getRoleBadge = (role: string) => {
        switch (role) {
            case 'super_admin':
                return 'Admin';
            case 'hr':
                return 'HR';
            case 'manager':
                return 'Manager';
            default:
                return null;
        }
    };

    return (
        <Paper
            elevation={8}
            sx={{
                position: 'fixed',
                bottom: 20,
                right: 20,
                width: 400,
                height: 600,
                display: 'flex',
                flexDirection: 'column',
                zIndex: 1000,
                borderRadius: 2,
                overflow: 'hidden'
            }}
        >
            {/* Header */}
            <Box
                sx={{
                    p: 2,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}
            >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="h6" fontWeight="bold">
                        💬 Company Chat
                    </Typography>
                    <Chip
                        label={`${messages.length} messages`}
                        size="small"
                        sx={{
                            bgcolor: 'rgba(255, 255, 255, 0.2)',
                            color: 'white',
                            fontWeight: 'bold'
                        }}
                    />
                </Box>
                <IconButton onClick={onClose} size="small" sx={{ color: 'white' }}>
                    <CloseIcon />
                </IconButton>
            </Box>

            {/* Messages Area */}
            <Box
                ref={chatBoxRef}
                sx={{
                    flex: 1,
                    overflowY: 'auto',
                    p: 2,
                    bgcolor: '#f5f5f5',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 1.5
                }}
            >
                {messages.map((msg) => {
                    const isOwnMessage = msg.sender_id === employee.id;
                    return (
                        <Box
                            key={msg.id}
                            sx={{
                                display: 'flex',
                                justifyContent: isOwnMessage ? 'flex-end' : 'flex-start',
                                gap: 1
                            }}
                        >
                            {!isOwnMessage && (
                                <Avatar
                                    sx={{
                                        width: 32,
                                        height: 32,
                                        bgcolor: '#667eea',
                                        fontSize: '0.875rem'
                                    }}
                                >
                                    {msg.sender_name.charAt(0)}
                                </Avatar>
                            )}

                            <Box sx={{ maxWidth: '70%' }}>
                                {!isOwnMessage && (
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                                        <Typography variant="caption" fontWeight="bold" color="text.secondary">
                                            {msg.sender_name}
                                        </Typography>
                                        {getRoleBadge(msg.sender_role) && (
                                            <Chip
                                                label={getRoleBadge(msg.sender_role)}
                                                size="small"
                                                color={getRoleColor(msg.sender_role)}
                                                sx={{ height: 16, fontSize: '0.65rem' }}
                                            />
                                        )}
                                    </Box>
                                )}

                                <Paper
                                    sx={{
                                        p: 1.5,
                                        bgcolor: isOwnMessage ? '#667eea' : 'white',
                                        color: isOwnMessage ? 'white' : 'text.primary',
                                        borderRadius: 2,
                                        wordBreak: 'break-word'
                                    }}
                                >
                                    <Typography variant="body2">{msg.message}</Typography>
                                    {msg.is_edited && (
                                        <Typography variant="caption" sx={{ opacity: 0.7, fontSize: '0.65rem' }}>
                                            (edited)
                                        </Typography>
                                    )}
                                </Paper>

                                <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    sx={{ display: 'block', mt: 0.5, fontSize: '0.7rem' }}
                                >
                                    {format(new Date(msg.created_at), 'hh:mm a')}
                                </Typography>
                            </Box>

                            {isOwnMessage && (
                                <Avatar
                                    sx={{
                                        width: 32,
                                        height: 32,
                                        bgcolor: '#667eea',
                                        fontSize: '0.875rem'
                                    }}
                                >
                                    {msg.sender_name.charAt(0)}
                                </Avatar>
                            )}
                        </Box>
                    );
                })}
                <div ref={messagesEndRef} />
            </Box>

            {/* Input Area */}
            <Box
                sx={{
                    p: 2,
                    bgcolor: 'white',
                    borderTop: '1px solid',
                    borderColor: 'divider',
                    display: 'flex',
                    gap: 1
                }}
            >
                <TextField
                    fullWidth
                    size="small"
                    placeholder="Type a message..."
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={loading}
                    multiline
                    maxRows={3}
                    sx={{
                        '& .MuiOutlinedInput-root': {
                            borderRadius: 3
                        }
                    }}
                />
                <Tooltip title="Send message">
                    <IconButton
                        color="primary"
                        onClick={handleSendMessage}
                        disabled={loading || !newMessage.trim()}
                        sx={{
                            bgcolor: '#667eea',
                            color: 'white',
                            '&:hover': { bgcolor: '#5568d3' },
                            '&:disabled': { bgcolor: '#e0e0e0' }
                        }}
                    >
                        <SendIcon />
                    </IconButton>
                </Tooltip>
            </Box>
        </Paper>
    );
}
