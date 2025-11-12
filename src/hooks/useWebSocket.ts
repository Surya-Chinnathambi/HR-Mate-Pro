import { useEffect, useState, useCallback, useRef } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketMessage {
    type: string;
    data: any;
    timestamp?: string;
}

interface WebSocketState {
    status: WebSocketStatus;
    isConnected: boolean;
    connectionError: string | null;
    lastMessage: WebSocketMessage | null;
}

interface UseWebSocketOptions {
    url?: string;
    autoConnect?: boolean;
    reconnectionAttempts?: number;
    reconnectionDelay?: number;
    onMessage?: (message: WebSocketMessage) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Event) => void;
}

// ============================================================================
// CUSTOM HOOK - Native WebSocket (not Socket.IO)
// ============================================================================

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
    const {
        url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
        autoConnect = true,
        reconnectionAttempts = 5,
        reconnectionDelay = 3000,
        onMessage,
        onConnect,
        onDisconnect,
        onError,
    } = options;

    const [state, setState] = useState<WebSocketState>({
        status: 'disconnected',
        isConnected: false,
        connectionError: null,
        lastMessage: null,
    });

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);

    // ============================================================================
    // CONNECTION MANAGEMENT
    // ============================================================================

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        const token = localStorage.getItem('access_token');
        if (!token) {
            setState((prev) => ({
                ...prev,
                status: 'error',
                connectionError: 'No authentication token found',
            }));
            return;
        }

        console.log('🔌 Connecting to WebSocket:', url);
        setState(prev => ({ ...prev, status: 'connecting' }));

        // Add token as query parameter for authentication
        const wsUrl = `${url}?token=${encodeURIComponent(token)}`;

        try {
            wsRef.current = new WebSocket(wsUrl);
            const ws = wsRef.current;

            ws.onopen = () => {
                console.log('✅ WebSocket connected');
                setState((prev) => ({
                    ...prev,
                    status: 'connected',
                    isConnected: true,
                    connectionError: null,
                }));
                reconnectAttemptsRef.current = 0;

                // Start heartbeat
                if (heartbeatIntervalRef.current) {
                    clearInterval(heartbeatIntervalRef.current);
                }
                heartbeatIntervalRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 30000); // Ping every 30 seconds

                onConnect?.();
            };

            ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    console.log('📨 WebSocket message:', message);

                    setState((prev) => ({
                        ...prev,
                        lastMessage: message,
                    }));

                    // Handle pong responses
                    if (message.type === 'pong') {
                        return;
                    }

                    onMessage?.(message);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                setState((prev) => ({
                    ...prev,
                    status: 'error',
                    connectionError: 'Connection error',
                }));
                onError?.(error);
            };

            ws.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                setState((prev) => ({
                    ...prev,
                    status: 'disconnected',
                    isConnected: false,
                }));

                // Clear heartbeat
                if (heartbeatIntervalRef.current) {
                    clearInterval(heartbeatIntervalRef.current);
                    heartbeatIntervalRef.current = null;
                }

                onDisconnect?.();

                // Attempt reconnection
                if (reconnectAttemptsRef.current < reconnectionAttempts) {
                    reconnectAttemptsRef.current += 1;
                    console.log(`Reconnecting... (${reconnectAttemptsRef.current}/${reconnectionAttempts})`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, reconnectionDelay);
                } else {
                    console.error('Max reconnection attempts reached');
                    setState((prev) => ({
                        ...prev,
                        status: 'error',
                        connectionError: 'Max reconnection attempts reached',
                    }));
                }
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            setState((prev) => ({
                ...prev,
                status: 'error',
                connectionError: 'Failed to create connection',
            }));
        }
    }, [url, reconnectionAttempts, reconnectionDelay, onMessage, onConnect, onDisconnect, onError]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
            heartbeatIntervalRef.current = null;
        }

        if (wsRef.current) {
            console.log('Disconnecting WebSocket');
            wsRef.current.close();
            wsRef.current = null;
        }

        setState((prev) => ({
            ...prev,
            status: 'disconnected',
            isConnected: false,
        }));
        reconnectAttemptsRef.current = 0;
    }, []);

    // ============================================================================
    // MESSAGE SENDING
    // ============================================================================

    const sendMessage = useCallback((message: any) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
            return true;
        } else {
            console.warn('WebSocket not connected. Message not sent:', message);
            return false;
        }
    }, []);

    const ping = useCallback(() => {
        sendMessage({ type: 'ping' });
    }, [sendMessage]);

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
    }, [autoConnect]); // Only run on mount/unmount, not when connect/disconnect changes

    // ============================================================================
    // RETURN
    // ============================================================================

    return {
        ...state,
        ws: wsRef.current,
        connect,
        disconnect,
        sendMessage,
        ping,
    };
};

// ============================================================================
// EVENT TYPE DEFINITIONS (for TypeScript autocomplete)
// ============================================================================

export type WebSocketEventType =
    | 'new_notification'
    | 'notification_created'
    | 'notification_updated'
    | 'notification_deleted'
    | 'task_assigned'
    | 'task_updated'
    | 'task_status_changed'
    | 'leave_approved'
    | 'leave_rejected'
    | 'leave_cancelled'
    | 'message_received'
    | 'broadcast_received'
    | 'approval_pending'
    | 'approval_completed'
    | 'attendance_checked_in'
    | 'attendance_checked_out'
    | 'expense_submitted'
    | 'expense_approved'
    | 'expense_rejected'
    | 'performance_review_created'
    | 'performance_feedback_received'
    | 'ping'
    | 'pong';

export interface TaskAssignedEvent {
    task_id: number;
    title: string;
    description: string;
    assigned_to_employee_id: number;
    assigned_by_employee_id: number;
    priority: string;
    due_date?: string;
}

export interface LeaveEvent {
    leave_request_id: number;
    employee_id: number;
    leave_type: string;
    start_date: string;
    end_date: string;
    days_count: number;
    status: string;
    comments?: string;
}

export interface MessageEvent {
    message_id: number;
    sender_employee_id: number;
    sender_name: string;
    subject: string;
    body: string;
    priority: string;
}

export interface BroadcastEvent {
    broadcast_id: number;
    title: string;
    body: string;
    sender_name: string;
    sender_role: string;
    priority: string;
    target_scope: string;
}
