import { useState, useRef, useEffect } from 'react';
import apiClient from '../api/client';
import { ChatHistorySidebar } from './ChatHistorySidebar';
import { Send, X, History, Sparkles, Clock, Calendar, FileText, Users, DollarSign, Trash2, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';

interface AICommandCenterProps {
  onClose: () => void;
  employee: any;
}

interface Message {
  id: number;
  type: 'ai' | 'user';
  content: string;
  timestamp: Date;
  isTyping?: boolean;
  intent?: string;
  entities?: Record<string, any>;
}

interface BalanceSummary {
  leaveBalance: {
    total_available: number;
    total_used: number;
    by_type: Record<string, any>;
  };
  attendance: {
    attendance_rate: number;
    late_arrivals: number;
    status: string;
  };
  wfh_quota: {
    remaining: number;
    used: number;
    status: string;
  };
  alerts: Array<{
    severity: string;
    category: string;
    message: string;
  }>;
}

export function AICommandCenter({ onClose, employee }: AICommandCenterProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(true);
  const [showBalanceWidget, setShowBalanceWidget] = useState(false);
  const [balanceSummary, setBalanceSummary] = useState<BalanceSummary | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    loadConversation();
    loadBalanceSummary();
  }, []);

  const loadBalanceSummary = async () => {
    try {
      const res = await apiClient.get('/ai/balance/quick-summary');
      if (res.data.success && res.data.full_data) {
        setBalanceSummary({
          leaveBalance: {
            total_available: res.data.full_data.balances ?
              Object.values(res.data.full_data.balances).reduce((sum: number, b: any) => sum + (b.available || 0), 0) : 0,
            total_used: res.data.full_data.balances ?
              Object.values(res.data.full_data.balances).reduce((sum: number, b: any) => sum + (b.used || 0), 0) : 0,
            by_type: res.data.full_data.balances || {}
          },
          attendance: {
            attendance_rate: 95, // Default values
            late_arrivals: 0,
            status: 'good'
          },
          wfh_quota: {
            remaining: 18,
            used: 6,
            status: 'good'
          },
          alerts: []
        });
        setShowBalanceWidget(true);
      }
    } catch (error) {
      console.error('Failed to load balance summary:', error);
    }
  };

  const loadConversation = async () => {
    try {
      const res = await apiClient.get('/ai/history', { params: { limit: 50 } });
      if (res.data.messages && res.data.messages.length > 0) {
        const converted: Message[] = res.data.messages.map((msg: any, idx: number) => ({
          id: idx + 1,
          type: msg.role === 'user' ? 'user' : 'ai',
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          intent: msg.intent,
          entities: msg.entities
        }));
        setMessages(converted);
      } else {
        showWelcome();
      }
    } catch (error) {
      console.error('Load error:', error);
      showWelcome();
    }
  };

  const showWelcome = () => {
    const name = employee?.first_name || employee?.firstName || 'there';
    setMessages([{
      id: 1,
      type: 'ai',
      content: `Hello ${name}! I'm Ellie, your AI HR Assistant. I can help with attendance, leave, payroll, and more. What would you like to do?`,
      timestamp: new Date()
    }]);
  };

  const handleSend = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMsg: Message = {
      id: messages.length + 1,
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    const prompt = inputMessage;
    setInputMessage('');
    setIsLoading(true);

    setMessages(prev => [...prev, {
      id: messages.length + 2,
      type: 'ai',
      content: '...',
      timestamp: new Date(),
      isTyping: true
    }]);

    try {
      const res = await apiClient.post('/ai/chat', null, {
        params: {
          prompt,
          conversation_id: conversationId,
          context: JSON.stringify({
            employee: employee?.first_name,
            role: employee?.designation
          })
        }
      });

      setMessages(prev => prev.filter(m => !m.isTyping));

      // Store conversation ID for continuity
      if (res.data.conversation_id) {
        setConversationId(res.data.conversation_id);
      }

      setMessages(prev => [...prev, {
        id: messages.length + 2,
        type: 'ai',
        content: res.data.response,
        timestamp: new Date(),
        intent: res.data.intent
      }]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => prev.filter(m => !m.isTyping));
      setMessages(prev => [...prev, {
        id: messages.length + 2,
        type: 'ai',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleClear = async () => {
    if (confirm('Clear conversation history?')) {
      try {
        await apiClient.delete('/ai/history');
        setMessages([]);
        setConversationId(null);  // Reset conversation ID
        showWelcome();
      } catch (error) {
        console.error('Clear error:', error);
      }
    }
  };

  const quickActions = [
    { icon: Clock, label: 'Clock In', prompt: 'Clock me in now' },
    { icon: Calendar, label: 'Apply Leave', prompt: 'I want to apply for leave' },
    { icon: FileText, label: 'Leave Balance', prompt: 'What is my leave balance?' },
    { icon: DollarSign, label: 'Payroll', prompt: 'Show my salary slip' },
    { icon: Users, label: 'Team', prompt: 'Show my team members' }
  ];

  const BalanceWidget = () => {
    if (!showBalanceWidget || !balanceSummary) return null;

    return (
      <div className='px-6 py-4 border-t border-purple-500/20 bg-slate-800/30'>
        <div className='flex items-center justify-between mb-3'>
          <h3 className='text-sm font-semibold text-slate-200 flex items-center gap-2'>
            <TrendingUp className='w-4 h-4' />
            Quick Balance
          </h3>
          <button
            onClick={() => setShowBalanceWidget(false)}
            className='text-slate-400 hover:text-slate-200 text-xs'
          >
            Hide
          </button>
        </div>
        <div className='grid grid-cols-3 gap-3'>
          {/* Leave Balance */}
          <div className='bg-gradient-to-br from-blue-600/20 to-purple-600/20 rounded-lg p-3 border border-blue-500/30'>
            <div className='flex items-center gap-2 mb-1'>
              <Calendar className='w-4 h-4 text-blue-400' />
              <span className='text-xs text-slate-300'>Leaves</span>
            </div>
            <div className='text-2xl font-bold text-white'>
              {balanceSummary.leaveBalance.total_available}
            </div>
            <div className='text-xs text-slate-400 mt-1'>
              {balanceSummary.leaveBalance.total_used} used
            </div>
          </div>

          {/* Attendance */}
          <div className='bg-gradient-to-br from-green-600/20 to-emerald-600/20 rounded-lg p-3 border border-green-500/30'>
            <div className='flex items-center gap-2 mb-1'>
              <CheckCircle className='w-4 h-4 text-green-400' />
              <span className='text-xs text-slate-300'>Attendance</span>
            </div>
            <div className='text-2xl font-bold text-white'>
              {balanceSummary.attendance.attendance_rate}%
            </div>
            <div className='text-xs text-slate-400 mt-1'>
              {balanceSummary.attendance.late_arrivals} late
            </div>
          </div>

          {/* WFH Quota */}
          <div className='bg-gradient-to-br from-orange-600/20 to-red-600/20 rounded-lg p-3 border border-orange-500/30'>
            <div className='flex items-center gap-2 mb-1'>
              <Users className='w-4 h-4 text-orange-400' />
              <span className='text-xs text-slate-300'>WFH</span>
            </div>
            <div className='text-2xl font-bold text-white'>
              {balanceSummary.wfh_quota.remaining}
            </div>
            <div className='text-xs text-slate-400 mt-1'>
              {balanceSummary.wfh_quota.used} used
            </div>
          </div>
        </div>

        {/* Alerts */}
        {balanceSummary.alerts && balanceSummary.alerts.length > 0 && (
          <div className='mt-3 space-y-2'>
            {balanceSummary.alerts.slice(0, 2).map((alert, idx) => (
              <div key={idx} className='flex items-start gap-2 bg-yellow-900/20 border border-yellow-600/30 rounded p-2'>
                <AlertCircle className='w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0' />
                <span className='text-xs text-slate-300'>{alert.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className='fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4'>
      <div className='bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 rounded-2xl shadow-2xl w-full max-w-6xl h-[90vh] flex overflow-hidden border border-purple-500/20'>

        {showHistory && (
          <div className='w-80 bg-slate-800/50 border-r border-purple-500/20'>
            <ChatHistorySidebar onNewChat={() => { setMessages([]); showWelcome(); }} />
          </div>
        )}

        <div className='flex-1 flex flex-col'>
          <div className='bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-4 flex items-center justify-between'>
            <div className='flex items-center gap-3'>
              <div className='bg-white/20 p-2 rounded-lg'><Sparkles className='w-6 h-6 text-white' /></div>
              <div>
                <h2 className='text-xl font-bold text-white'>Ellie AI Assistant</h2>
                <p className='text-purple-100 text-sm'>Context-Aware AI</p>
              </div>
            </div>
            <div className='flex items-center gap-2'>
              <button onClick={() => setShowHistory(!showHistory)} className='p-2 hover:bg-white/10 rounded-lg' aria-label="Toggle chat history">
                <History className='w-5 h-5 text-white' />
              </button>
              <button onClick={handleClear} className='p-2 hover:bg-white/10 rounded-lg' aria-label="Clear chat history">
                <Trash2 className='w-5 h-5 text-white' />
              </button>
              <button onClick={onClose} className='p-2 hover:bg-white/10 rounded-lg' aria-label="Close AI chat">
                <X className='w-5 h-5 text-white' />
              </button>
            </div>
          </div>

          <div className='flex-1 overflow-y-auto p-6 space-y-4'>
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${msg.type === 'user'
                  ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                  : msg.isTyping
                    ? 'bg-slate-700/50 text-slate-300 animate-pulse'
                    : 'bg-slate-800/80 text-slate-100 border border-purple-500/20'
                  }`}>
                  <div className='whitespace-pre-wrap'>{msg.content}</div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {messages.length <= 1 && (
            <div className='px-6 py-3 border-t border-purple-500/20 bg-slate-800/30'>
              <div className='grid grid-cols-3 gap-2'>
                {quickActions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => { setInputMessage(action.prompt); inputRef.current?.focus(); }}
                    className='flex items-center gap-2 px-3 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg text-sm text-slate-200'
                  >
                    <action.icon className='w-4 h-4' />
                    <span>{action.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Balance Widget */}
          <BalanceWidget />

          <div className='p-6 border-t border-purple-500/20 bg-slate-800/50'>
            <div className='flex gap-3'>
              <input
                ref={inputRef}
                type='text'
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder='Ask me anything about HR, leave, payroll...'
                className='flex-1 bg-slate-700/50 text-white placeholder-slate-400 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500'
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !inputMessage.trim()}
                className='bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 disabled:from-slate-600 text-white rounded-xl px-6 py-3 font-medium flex items-center gap-2'
              >
                <Send className='w-5 h-5' />
                Send
              </button>
            </div>
            <div className='mt-2 text-xs text-slate-400 text-center'>
              Powered by Azure GPT-4 with Context Memory
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
