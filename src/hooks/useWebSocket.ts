import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

// ============================================================================
// TYPES
// ============================================================================

interface WebSocketState {
    isConnected: boolean;
    isAuthenticated: boolean;
    connectionError: string | null;
    lastMessage: any;
}

interface UseWebSocketOptions {
    url?: string;
    autoConnect?: boolean;
    reconnectionAttempts?: number;
    reconnectionDelay?: number;
}

interface WebSocketMessage {
    event: string;
    data: any;
    timestamp: string;
}

// ============================================================================
// CUSTOM HOOK
// ============================================================================

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
    const {
        url = import.meta.env.VITE_WS_URL || 'http://localhost:8000/ws',
        autoConnect = true,
        reconnectionAttempts = 5,
        reconnectionDelay = 3000,
    } = options;

    const [state, setState] = useState<WebSocketState>({
        isConnected: false,
        isAuthenticated: false,
        connectionError: null,
        lastMessage: null,
    });

    const socketRef = useRef<Socket | null>(null);
    const eventHandlersRef = useRef<Map<string, Function[]>>(new Map());
    const reconnectAttemptsRef = useRef(0);

    // ============================================================================
    // CONNECTION MANAGEMENT
    // ============================================================================

    const connect = useCallback(() => {
        if (socketRef.current?.connected) {
            console.log('WebSocket already connected');
            return;
        }

        const token = localStorage.getItem('access_token');
        if (!token) {
            setState((prev) => ({
                ...prev,
                connectionError: 'No authentication token found',
            }));
            return;
        }

        console.log('Connecting to WebSocket:', url);

        socketRef.current = io(url, {
            auth: {
                token: `Bearer ${token}`,
            },
            transports: ['websocket', 'polling'],
            reconnectionAttempts,
            reconnectionDelay,
        });

        const socket = socketRef.current;

        // Connection events
        socket.on('connect', () => {
            console.log('✅ WebSocket connected:', socket.id);
            setState((prev) => ({
                ...prev,
                isConnected: true,
                connectionError: null,
            }));
            reconnectAttemptsRef.current = 0;

            // Auto-authenticate with user_id from token
            // In production, decode JWT to get user_id
            const userId = parseInt(localStorage.getItem('user_id') || '0');
            if (userId) {
                socket.emit('authenticate', { user_id: userId, token });
            }
        });

        socket.on('connected', (data: any) => {
            console.log('Connected event:', data);
        });

        socket.on('authenticated', (data: any) => {
            console.log('✅ WebSocket authenticated:', data);
            setState((prev) => ({
                ...prev,
                isAuthenticated: true,
            }));
        });

        socket.on('disconnect', (reason: string) => {
            console.log('❌ WebSocket disconnected:', reason);
            setState((prev) => ({
                ...prev,
                isConnected: false,
                isAuthenticated: false,
            }));

            // Auto-reconnect if disconnected by server
            if (reason === 'io server disconnect') {
                socket.connect();
            }
        });

        socket.on('connect_error', (error: Error) => {
            console.error('WebSocket connection error:', error);
            setState((prev) => ({
                ...prev,
                connectionError: error.message,
            }));

            reconnectAttemptsRef.current += 1;
            if (reconnectAttemptsRef.current >= reconnectionAttempts) {
                console.error('Max reconnection attempts reached');
                socket.disconnect();
            }
        });

        socket.on('error', (data: any) => {
            console.error('WebSocket error:', data);
            setState((prev) => ({
                ...prev,
                connectionError: data.message || 'Unknown error',
            }));
        });

        socket.on('pong', () => {
            // Heartbeat response
            console.log('Pong received');
        });

        // Register all event handlers
        eventHandlersRef.current.forEach((handlers, event) => {
            handlers.forEach((handler) => {
                socket.on(event, handler as (...args: any[]) => void);
            });
        });
    }, [url, reconnectionAttempts, reconnectionDelay]);

    const disconnect = useCallback(() => {
        if (socketRef.current) {
            console.log('Disconnecting WebSocket');
            socketRef.current.disconnect();
            socketRef.current = null;
            setState((prev) => ({
                ...prev,
                isConnected: false,
                isAuthenticated: false,
            }));
        }
    }, []);

    // ============================================================================
    // EVENT HANDLERS
    // ============================================================================

    const on = useCallback((event: string, handler: Function) => {
        // Store handler for future reconnections
        if (!eventHandlersRef.current.has(event)) {
            eventHandlersRef.current.set(event, []);
        }
        eventHandlersRef.current.get(event)?.push(handler);

        // Register with current socket if connected
        if (socketRef.current) {
            socketRef.current.on(event, handler as any);
        }

        // Return cleanup function
        return () => {
            const handlers = eventHandlersRef.current.get(event);
            if (handlers) {
                const index = handlers.indexOf(handler);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
            }
            if (socketRef.current) {
                socketRef.current.off(event, handler as any);
            }
        };
    }, []);

    const emit = useCallback((event: string, data?: any) => {
        if (socketRef.current?.connected) {
            socketRef.current.emit(event, data);
        } else {
            console.warn('Cannot emit, WebSocket not connected');
        }
    }, []);

    // ============================================================================
    // CONVENIENCE METHODS
    // ============================================================================

    const subscribeToTeam = useCallback((teamId: number) => {
        emit('subscribe_to_team', { team_id: teamId });
    }, [emit]);

    const subscribeToDepartment = useCallback((department: string) => {
        emit('subscribe_to_team', { department });
    }, [emit]);

    const ping = useCallback(() => {
        emit('ping');
    }, [emit]);

    // ============================================================================
    // LIFECYCLE
    // ============================================================================

    useEffect(() => {
        if (autoConnect) {
            connect();
        }

        // Cleanup on unmount
        return () => {
            disconnect();
        };
    }, [autoConnect, connect, disconnect]);

    // Heartbeat ping every 30 seconds
    useEffect(() => {
        if (state.isConnected) {
            const interval = setInterval(() => {
                ping();
            }, 30000);

            return () => clearInterval(interval);
        }
    }, [state.isConnected, ping]);

    // ============================================================================
    // RETURN
    // ============================================================================

    return {
        ...state,
        socket: socketRef.current,
        connect,
        disconnect,
        on,
        emit,
        subscribeToTeam,
        subscribeToDepartment,
        ping,
    };
};

// ============================================================================
// EVENT TYPE DEFINITIONS (for TypeScript autocomplete)
// ============================================================================

export type WebSocketEvent =
    | 'new_notification'
    | 'approval_updated'
    | 'task_updated'
    | 'task_status_changed'
    | 'new_comment'
    | 'workload_alert'
    | 'test_message';

export interface NewNotificationEvent {
    notification_id: number;
    title: string;
    message: string;
    type: string;
    priority: string;
    created_at: string;
}

export interface ApprovalUpdatedEvent {
    approval_id: number;
    status: string;
    level: number;
    approver_name: string;
    comments: string;
}

export interface TaskUpdatedEvent {
    task_id: number;
    title: string;
    status: string;
    progress_percentage: number;
    updated_by: string;
}

export interface TaskStatusChangedEvent {
    task_id: number;
    old_status: string;
    new_status: string;
    changed_by: string;
    assignee_id: number;
    assigner_id: number;
}

export interface NewCommentEvent {
    comment_id: number;
    task_id: number;
    user_name: string;
    comment_text: string;
    created_at: string;
}

export interface WorkloadAlertEvent {
    employee_id: number;
    employee_name: string;
    utilization_percent: number;
    status: 'overloaded' | 'balanced' | 'available';
    message: string;
}
