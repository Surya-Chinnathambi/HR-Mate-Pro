import React, { useState, useEffect } from 'react';
import {
    Box,
    Grid,
    Card,
    CardContent,
    CardHeader,
    Typography,
    Button,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Chip,
    Avatar,
    IconButton,
    Badge,
    Tooltip,
    CircularProgress,
    Alert,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Paper,
    LinearProgress,
    Divider,
    Stack,
    ToggleButton,
    ToggleButtonGroup,
    Slider,
    Checkbox,
    FormControlLabel,
    List,
    ListItem,
    ListItemText,
    ListItemAvatar,
    Stepper,
    Step,
    StepLabel,
    StepContent,
    Accordion,
    AccordionSummary,
    AccordionDetails,
} from '@mui/material';
import {
    ViewList as ListViewIcon,
    CalendarMonth as CalendarIcon,
    AccountTree as DependencyIcon,
    FilterList as FilterIcon,
    Add as AddIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    Comment as CommentIcon,
    AttachFile as AttachIcon,
    AccessTime as TimeIcon,
    CheckCircle as CompleteIcon,
    SwapHoriz as DelegateIcon,
    ExpandMore as ExpandMoreIcon,
    Send as SendIcon,
    Close as CloseIcon,
    Timeline as TimelineIcon,
    TrendingUp as ProgressIcon,
    Warning as WarningIcon,
    Announcement as BroadcastIcon,
    People as PeopleIcon,
    SmartToy as AiIcon,
    Schedule as ScheduleIcon,
    Description as TemplateIcon,
    CloudUpload as UploadIcon,
    Group as TeamIcon,
} from '@mui/icons-material';
import { format, formatDistanceToNow, parseISO, addDays } from 'date-fns';
import apiClient from '../api/client';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface Task {
    task_id: number;
    title: string;
    description: string;
    assignee_id: number;
    assigner_id: number;
    assignee_name?: string;
    assigner_name?: string;
    priority: 'low' | 'medium' | 'high' | 'urgent';
    status: 'NOT_STARTED' | 'IN_PROGRESS' | 'BLOCKED' | 'UNDER_REVIEW' | 'COMPLETED' | 'CANCELLED';
    progress_percentage: number;
    due_date?: string;
    estimated_hours?: number;
    actual_hours?: number;
    project_name?: string;
    tags?: string[];
    dependencies?: number[];
    created_at: string;
    updated_at: string;
    is_overdue?: boolean;
    days_until_due?: number;
}

interface TaskComment {
    comment_id: number;
    task_id: number;
    user_id: number;
    user_name: string;
    comment_text: string;
    created_at: string;
    updated_at?: string;
}

interface TaskTimeLog {
    log_id: number;
    task_id: number;
    user_id: number;
    user_name: string;
    hours_logged: number;
    log_date: string;
    description?: string;
    created_at: string;
}

interface TaskHistory {
    timestamp: string;
    user_name: string;
    action: string;
    old_value?: string;
    new_value?: string;
}

interface FilterState {
    status: string[];
    priority: string[];
    project: string;
    dateFrom: string;
    dateTo: string;
    assignedBy: string;
    showCompleted: boolean;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const WorkInbox: React.FC = () => {
    // View State
    const [activeView, setActiveView] = useState<'list' | 'calendar' | 'dependencies'>('list');

    // Data State
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedTask, setSelectedTask] = useState<Task | null>(null);
    const [taskComments, setTaskComments] = useState<TaskComment[]>([]);
    const [taskTimeLogs, setTaskTimeLogs] = useState<TaskTimeLog[]>([]);
    const [taskHistory, setTaskHistory] = useState<TaskHistory[]>([]);

    // Filter State
    const [filters, setFilters] = useState<FilterState>({
        status: [],
        priority: [],
        project: '',
        dateFrom: '',
        dateTo: '',
        assignedBy: '',
        showCompleted: false,
    });
    const [showFilters, setShowFilters] = useState(false);

    // Dialog State
    const [detailDialogOpen, setDetailDialogOpen] = useState(false);
    const [commentText, setCommentText] = useState('');
    const [timeLogForm, setTimeLogForm] = useState({
        date: format(new Date(), 'yyyy-MM-dd'),
        hours: 1,
        description: '',
    });

    // Broadcast Message State
    const [broadcastDialogOpen, setBroadcastDialogOpen] = useState(false);
    const [broadcastMessage, setBroadcastMessage] = useState('');
    const [broadcastRecipients, setBroadcastRecipients] = useState<'all_managers' | 'all_employees' | 'specific_teams' | 'custom'>('all_managers');
    const [selectedTeams, setSelectedTeams] = useState<number[]>([]);
    const [selectedEmployees, setSelectedEmployees] = useState<number[]>([]);
    const [sendingBroadcast, setSendingBroadcast] = useState(false);
    const [broadcastSuccess, setBroadcastSuccess] = useState(false);
    const [scheduleDate, setScheduleDate] = useState('');
    const [scheduleTime, setScheduleTime] = useState('');
    const [useTemplate, setUseTemplate] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState('');
    const [attachments, setAttachments] = useState<File[]>([]);

    // Available data
    const [availableTeams, setAvailableTeams] = useState<any[]>([]);
    const [availableEmployees, setAvailableEmployees] = useState<any[]>([]);
    const [currentEmployee, setCurrentEmployee] = useState<any>(null);

    // Pagination State
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);

    // ============================================================================
    // DATA FETCHING
    // ============================================================================

    useEffect(() => {
        fetchCurrentEmployee();
        fetchTasks();
    }, [filters, page]);

    const fetchCurrentEmployee = async () => {
        try {
            const response = await apiClient.get('/employees/current');
            setCurrentEmployee(response.data);
        } catch (error) {
            console.error('Error fetching current employee:', error);
        }
    };

    const fetchTasks = async () => {
        try {
            setLoading(true);
            const params: any = {
                skip: (page - 1) * 20,
                limit: 20,
            };

            if (filters.status.length > 0) {
                params.status = filters.status.join(',');
            }
            if (filters.priority.length > 0) {
                params.priority = filters.priority.join(',');
            }
            if (filters.project) {
                params.project_name = filters.project;
            }
            if (filters.dateFrom) {
                params.due_date_from = filters.dateFrom;
            }
            if (filters.dateTo) {
                params.due_date_to = filters.dateTo;
            }
            if (!filters.showCompleted) {
                params.exclude_completed = true;
            }

            const response = await apiClient.get('/work-assignments/', { params });

            if (page === 1) {
                setTasks(response.data || []);
            } else {
                setTasks((prev) => [...prev, ...(response.data || [])]);
            }

            setHasMore(response.data && response.data.length === 20);
        } catch (error) {
            console.error('Error fetching tasks:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchTaskDetails = async (taskId: number) => {
        try {
            const [commentsRes, timeLogsRes] = await Promise.all([
                apiClient.get(`/work-assignments/${taskId}/comments`),
                apiClient.get(`/work-assignments/${taskId}/time-logs`),
            ]);

            setTaskComments(commentsRes.data || []);
            setTaskTimeLogs(timeLogsRes.data || []);

            // Mock history data (in production, this would come from audit_logs)
            setTaskHistory([
                {
                    timestamp: new Date().toISOString(),
                    user_name: 'John Doe',
                    action: 'Status changed',
                    old_value: 'NOT_STARTED',
                    new_value: 'IN_PROGRESS',
                },
            ]);
        } catch (error) {
            console.error('Error fetching task details:', error);
        }
    };

    const handleTaskClick = async (task: Task) => {
        setSelectedTask(task);
        setDetailDialogOpen(true);
        await fetchTaskDetails(task.task_id);
    };

    const handleUpdateStatus = async (taskId: number, newStatus: string) => {
        try {
            await apiClient.put(`/work-assignments/${taskId}`, { status: newStatus });
            fetchTasks();
            if (selectedTask?.task_id === taskId) {
                setSelectedTask({ ...selectedTask, status: newStatus as any });
            }
        } catch (error) {
            console.error('Error updating status:', error);
        }
    };

    const handleUpdateProgress = async (taskId: number, progress: number) => {
        try {
            await apiClient.put(`/work-assignments/${taskId}`, { progress_percentage: progress });
            fetchTasks();
            if (selectedTask?.task_id === taskId) {
                setSelectedTask({ ...selectedTask, progress_percentage: progress });
            }
        } catch (error) {
            console.error('Error updating progress:', error);
        }
    };

    const handleAddComment = async () => {
        if (!selectedTask || !commentText.trim()) return;

        try {
            await apiClient.post(`/work-assignments/${selectedTask.task_id}/comments`, {
                comment_text: commentText,
            });
            setCommentText('');
            await fetchTaskDetails(selectedTask.task_id);
        } catch (error) {
            console.error('Error adding comment:', error);
        }
    };

    const handleAddTimeLog = async () => {
        if (!selectedTask || !timeLogForm.hours) return;

        try {
            await apiClient.post(`/work-assignments/${selectedTask.task_id}/time-logs`, {
                hours_logged: timeLogForm.hours,
                log_date: timeLogForm.date,
                description: timeLogForm.description,
            });
            setTimeLogForm({ date: format(new Date(), 'yyyy-MM-dd'), hours: 1, description: '' });
            await fetchTaskDetails(selectedTask.task_id);
            fetchTasks(); // Refresh to update actual hours
        } catch (error) {
            console.error('Error adding time log:', error);
        }
    };

    const handleCompleteTask = async (taskId: number) => {
        await handleUpdateStatus(taskId, 'COMPLETED');
        await handleUpdateProgress(taskId, 100);
    };

    const handleDelegateTask = async (taskId: number) => {
        // This would open a delegate dialog in production
        console.log('Delegate task:', taskId);
    };

    // ============================================================================
    // MESSAGE TEMPLATES
    // ============================================================================

    const messageTemplates = {
        task_reminder: {
            name: 'Task Completion Reminder',
            content: `Dear Team,

This is a friendly reminder to review your assigned tasks and ensure all pending items are completed or updated.

**Action Required:**
• Check your task list for overdue items
• Update task statuses to reflect current progress
• Escalate any blockers or dependencies

Please complete this by end of day today.

Thank you for your cooperation!`
        },
        weekly_review: {
            name: 'Weekly Team Review',
            content: `Hi Team,

Time for our weekly review! Please ensure the following:

**This Week's Focus:**
• Complete all high-priority tasks
• Update project status reports
• Review team workload distribution
• Address any pending approvals

Let's make this a productive week!`
        },
        urgent_action: {
            name: 'Urgent Action Required',
            content: `🚨 URGENT: Immediate Action Required

Dear Team Member,

This message requires your immediate attention.

**Required Actions:**
• [Specify action items here]
• Timeline: [Specify deadline]
• Contact: [Your contact info]

Please acknowledge receipt of this message.

Thank you for your prompt response.`
        },
        workload_check: {
            name: 'Workload Balance Check',
            content: `Hello,

Let's ensure optimal workload distribution across the team.

**Please Review:**
• Current task allocation for your team
• Any overloaded team members
• Opportunities for task redistribution
• Resource requirements

Your feedback is valuable for team efficiency.`
        },
        policy_update: {
            name: 'Policy Update Announcement',
            content: `Important: Policy Update

Dear All,

We have updated our workplace policies. Please review the following:

**What's New:**
• [Policy area]
• Effective Date: [Date]
• Key Changes: [Brief summary]

Full details are available in the Company Policies section.

Please acknowledge that you have read and understood these updates.`
        }
    };

    // ============================================================================
    // BROADCAST MESSAGE FUNCTIONS
    // ============================================================================

    useEffect(() => {
        if (broadcastDialogOpen) {
            fetchTeamsAndEmployees();
        }
    }, [broadcastDialogOpen]);

    const fetchTeamsAndEmployees = async () => {
        try {
            const [teamsRes, employeesRes] = await Promise.all([
                apiClient.get('/teams/'),
                apiClient.get('/employees/')
            ]);
            setAvailableTeams(teamsRes.data || []);
            setAvailableEmployees(employeesRes.data || []);
        } catch (error) {
            console.error('Error fetching teams/employees:', error);
        }
    };

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files) {
            const newFiles = Array.from(event.target.files);
            setAttachments([...attachments, ...newFiles]);
        }
    };

    const removeAttachment = (index: number) => {
        setAttachments(attachments.filter((_, i) => i !== index));
    };

    const getRecipientsList = async () => {
        let recipients: any[] = [];

        switch (broadcastRecipients) {
            case 'all_managers':
                const managersRes = await apiClient.get('/employees/', { params: { role: 'manager' } });
                recipients = managersRes.data || [];
                break;

            case 'all_employees':
                const employeesRes = await apiClient.get('/employees/');
                recipients = employeesRes.data || [];
                break;

            case 'specific_teams':
                if (selectedTeams.length > 0) {
                    const teamPromises = selectedTeams.map(teamId =>
                        apiClient.get('/employees/', { params: { team_id: teamId } })
                    );
                    const teamResults = await Promise.all(teamPromises);
                    recipients = teamResults.flatMap(res => res.data || []);
                }
                break;

            case 'custom':
                recipients = availableEmployees.filter(emp => selectedEmployees.includes(emp.id));
                break;
        }

        return recipients;
    };

    const handleSendBroadcast = async () => {
        if (!broadcastMessage.trim()) return;

        // Check if scheduling
        if (scheduleDate && scheduleTime) {
            await handleScheduleBroadcast();
            return;
        }

        setSendingBroadcast(true);
        try {
            const recipients = await getRecipientsList();

            if (recipients.length === 0) {
                throw new Error('No recipients selected');
            }

            // Upload attachments first if any
            let attachmentUrls: string[] = [];
            if (attachments.length > 0) {
                const formData = new FormData();
                attachments.forEach(file => formData.append('files', file));

                const uploadRes = await apiClient.post('/files/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                attachmentUrls = uploadRes.data.urls || [];
            }

            // Create notification for each recipient
            const notificationPromises = recipients.map((recipient: any) =>
                apiClient.post('/realtime/notifications', {
                    employee_id: recipient.id,
                    title: 'HR Broadcast Message',
                    message: broadcastMessage,
                    priority: 'high',
                    category: 'announcement',
                    action_url: '/work-inbox',
                    metadata: {
                        attachments: attachmentUrls,
                        broadcast_type: broadcastRecipients,
                        sender: 'HR'
                    }
                })
            );

            await Promise.all(notificationPromises);

            setBroadcastSuccess(true);
            setTimeout(() => {
                setBroadcastDialogOpen(false);
                resetBroadcastForm();
            }, 2000);
        } catch (error: any) {
            console.error('Error sending broadcast:', error);
            alert(error.message || 'Failed to send broadcast message. Please try again.');
        } finally {
            setSendingBroadcast(false);
        }
    };

    const handleScheduleBroadcast = async () => {
        try {
            const scheduledDateTime = new Date(`${scheduleDate}T${scheduleTime}`);

            const recipients = await getRecipientsList();

            // Store scheduled broadcast
            await apiClient.post('/scheduled-broadcasts/', {
                message: broadcastMessage,
                recipient_type: broadcastRecipients,
                recipient_ids: recipients.map((r: any) => r.id),
                scheduled_time: scheduledDateTime.toISOString(),
                attachments: attachments.map(f => f.name),
                template_used: selectedTemplate || null
            });

            alert(`Broadcast scheduled for ${scheduledDateTime.toLocaleString()}`);
            setBroadcastDialogOpen(false);
            resetBroadcastForm();
        } catch (error) {
            console.error('Error scheduling broadcast:', error);
            alert('Failed to schedule broadcast. Please try again.');
        }
    };

    const resetBroadcastForm = () => {
        setBroadcastMessage('');
        setBroadcastSuccess(false);
        setScheduleDate('');
        setScheduleTime('');
        setAttachments([]);
        setSelectedTeams([]);
        setSelectedEmployees([]);
        setUseTemplate(false);
        setSelectedTemplate('');
    };

    const applyTemplate = (templateKey: string) => {
        const template = messageTemplates[templateKey as keyof typeof messageTemplates];
        if (template) {
            setBroadcastMessage(template.content);
            setSelectedTemplate(templateKey);
        }
    };

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================

    const getPriorityColor = (priority: string): string => {
        const colors: Record<string, string> = {
            urgent: '#d32f2f',
            high: '#f57c00',
            medium: '#1976d2',
            low: '#388e3c',
        };
        return colors[priority] || '#757575';
    };

    const getStatusColor = (status: string): string => {
        const colors: Record<string, string> = {
            NOT_STARTED: '#757575',
            IN_PROGRESS: '#1976d2',
            BLOCKED: '#d32f2f',
            UNDER_REVIEW: '#f57c00',
            COMPLETED: '#388e3c',
            CANCELLED: '#424242',
        };
        return colors[status] || '#757575';
    };

    const formatDueDate = (dueDate?: string): string => {
        if (!dueDate) return 'No due date';
        const date = parseISO(dueDate);
        const now = new Date();
        const daysDiff = Math.floor((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

        if (daysDiff < 0) return `Overdue by ${Math.abs(daysDiff)} days`;
        if (daysDiff === 0) return 'Due today';
        if (daysDiff === 1) return 'Due tomorrow';
        return `Due in ${daysDiff} days`;
    };

    const getFilteredTasks = (): Task[] => {
        return tasks.filter((task) => {
            if (filters.status.length > 0 && !filters.status.includes(task.status)) return false;
            if (filters.priority.length > 0 && !filters.priority.includes(task.priority)) return false;
            if (filters.project && task.project_name !== filters.project) return false;
            if (!filters.showCompleted && task.status === 'COMPLETED') return false;
            return true;
        });
    };

    // ============================================================================
    // RENDER: FILTER PANEL
    // ============================================================================

    const renderFilters = () => (
        <Accordion expanded={showFilters} onChange={() => setShowFilters(!showFilters)}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" gap={1}>
                    <FilterIcon />
                    <Typography>Filters</Typography>
                    {(filters.status.length > 0 || filters.priority.length > 0) && (
                        <Chip
                            label={`${filters.status.length + filters.priority.length} active`}
                            size="small"
                            color="primary"
                        />
                    )}
                </Box>
            </AccordionSummary>
            <AccordionDetails>
                <Grid container spacing={2}>
                    <Grid item xs={12} md={3}>
                        <Typography variant="caption" gutterBottom>Status</Typography>
                        <Stack spacing={0.5}>
                            {['NOT_STARTED', 'IN_PROGRESS', 'BLOCKED', 'UNDER_REVIEW', 'COMPLETED'].map((status) => (
                                <FormControlLabel
                                    key={status}
                                    control={
                                        <Checkbox
                                            size="small"
                                            checked={filters.status.includes(status)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setFilters({ ...filters, status: [...filters.status, status] });
                                                } else {
                                                    setFilters({ ...filters, status: filters.status.filter((s) => s !== status) });
                                                }
                                                setPage(1);
                                            }}
                                        />
                                    }
                                    label={<Typography variant="body2">{status.replace('_', ' ')}</Typography>}
                                />
                            ))}
                        </Stack>
                    </Grid>

                    <Grid item xs={12} md={3}>
                        <Typography variant="caption" gutterBottom>Priority</Typography>
                        <Stack spacing={0.5}>
                            {['low', 'medium', 'high', 'urgent'].map((priority) => (
                                <FormControlLabel
                                    key={priority}
                                    control={
                                        <Checkbox
                                            size="small"
                                            checked={filters.priority.includes(priority)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setFilters({ ...filters, priority: [...filters.priority, priority] });
                                                } else {
                                                    setFilters({ ...filters, priority: filters.priority.filter((p) => p !== priority) });
                                                }
                                                setPage(1);
                                            }}
                                        />
                                    }
                                    label={
                                        <Chip
                                            label={priority.toUpperCase()}
                                            size="small"
                                            sx={{ bgcolor: getPriorityColor(priority), color: 'white' }}
                                        />
                                    }
                                />
                            ))}
                        </Stack>
                    </Grid>

                    <Grid item xs={12} md={3}>
                        <Typography variant="caption" gutterBottom>Date Range</Typography>
                        <Stack spacing={1}>
                            <TextField
                                label="From"
                                type="date"
                                size="small"
                                fullWidth
                                InputLabelProps={{ shrink: true }}
                                value={filters.dateFrom}
                                onChange={(e) => {
                                    setFilters({ ...filters, dateFrom: e.target.value });
                                    setPage(1);
                                }}
                            />
                            <TextField
                                label="To"
                                type="date"
                                size="small"
                                fullWidth
                                InputLabelProps={{ shrink: true }}
                                value={filters.dateTo}
                                onChange={(e) => {
                                    setFilters({ ...filters, dateTo: e.target.value });
                                    setPage(1);
                                }}
                            />
                        </Stack>
                    </Grid>

                    <Grid item xs={12} md={3}>
                        <Typography variant="caption" gutterBottom>Options</Typography>
                        <Stack spacing={1}>
                            <FormControlLabel
                                control={
                                    <Checkbox
                                        checked={filters.showCompleted}
                                        onChange={(e) => {
                                            setFilters({ ...filters, showCompleted: e.target.checked });
                                            setPage(1);
                                        }}
                                    />
                                }
                                label="Show completed"
                            />
                            <Button
                                size="small"
                                onClick={() => {
                                    setFilters({
                                        status: [],
                                        priority: [],
                                        project: '',
                                        dateFrom: '',
                                        dateTo: '',
                                        assignedBy: '',
                                        showCompleted: false,
                                    });
                                    setPage(1);
                                }}
                            >
                                Clear All
                            </Button>
                        </Stack>
                    </Grid>
                </Grid>
            </AccordionDetails>
        </Accordion>
    );

    // ============================================================================
    // RENDER: TASK LIST VIEW
    // ============================================================================

    const renderTaskList = () => {
        const filteredTasks = getFilteredTasks();

        return (
            <Box>
                {loading && page === 1 ? (
                    <Box display="flex" justifyContent="center" p={4}>
                        <CircularProgress />
                    </Box>
                ) : filteredTasks.length === 0 ? (
                    <Alert severity="info">No tasks found. Adjust your filters or create a new task.</Alert>
                ) : (
                    <Grid container spacing={2}>
                        {filteredTasks.map((task) => (
                            <Grid item xs={12} key={task.task_id}>
                                <Card
                                    sx={{
                                        cursor: 'pointer',
                                        '&:hover': { boxShadow: 4 },
                                        borderLeft: `4px solid ${getPriorityColor(task.priority)}`,
                                    }}
                                    onClick={() => handleTaskClick(task)}
                                >
                                    <CardContent>
                                        <Box display="flex" justifyContent="space-between" alignItems="start" mb={1}>
                                            <Box flex={1}>
                                                <Typography variant="h6" gutterBottom>
                                                    {task.title}
                                                </Typography>
                                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                                    {task.description.length > 100
                                                        ? `${task.description.substring(0, 100)}...`
                                                        : task.description}
                                                </Typography>
                                            </Box>
                                            <Box display="flex" gap={1}>
                                                <Tooltip title="Complete Task">
                                                    <IconButton
                                                        size="small"
                                                        color="success"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleCompleteTask(task.task_id);
                                                        }}
                                                        disabled={task.status === 'COMPLETED'}
                                                    >
                                                        <CompleteIcon />
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="Delegate Task">
                                                    <IconButton
                                                        size="small"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleDelegateTask(task.task_id);
                                                        }}
                                                    >
                                                        <DelegateIcon />
                                                    </IconButton>
                                                </Tooltip>
                                            </Box>
                                        </Box>

                                        <Box display="flex" flexWrap="wrap" gap={1} mb={1}>
                                            <Chip
                                                label={task.priority.toUpperCase()}
                                                size="small"
                                                sx={{ bgcolor: getPriorityColor(task.priority), color: 'white' }}
                                            />
                                            <Chip
                                                label={task.status.replace('_', ' ')}
                                                size="small"
                                                sx={{ bgcolor: getStatusColor(task.status), color: 'white' }}
                                            />
                                            {task.due_date && (
                                                <Chip
                                                    label={formatDueDate(task.due_date)}
                                                    size="small"
                                                    icon={<TimeIcon />}
                                                    color={task.is_overdue ? 'error' : 'default'}
                                                />
                                            )}
                                            {task.project_name && (
                                                <Chip label={task.project_name} size="small" variant="outlined" />
                                            )}
                                            {task.tags && task.tags.map((tag) => (
                                                <Chip key={tag} label={tag} size="small" variant="outlined" />
                                            ))}
                                        </Box>

                                        <Box display="flex" alignItems="center" gap={2}>
                                            <Box flex={1}>
                                                <Box display="flex" justifyContent="space-between" mb={0.5}>
                                                    <Typography variant="caption">Progress</Typography>
                                                    <Typography variant="caption">{task.progress_percentage}%</Typography>
                                                </Box>
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={task.progress_percentage}
                                                    sx={{ height: 6, borderRadius: 1 }}
                                                />
                                            </Box>
                                            {task.estimated_hours && (
                                                <Typography variant="caption" color="text.secondary">
                                                    {task.actual_hours || 0}h / {task.estimated_hours}h
                                                </Typography>
                                            )}
                                        </Box>

                                        <Box display="flex" justifyContent="space-between" mt={1}>
                                            <Typography variant="caption" color="text.secondary">
                                                Assigned by: {task.assigner_name || 'Unknown'}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary">
                                                Updated {formatDistanceToNow(parseISO(task.updated_at))} ago
                                            </Typography>
                                        </Box>
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}

                        {hasMore && (
                            <Grid item xs={12}>
                                <Box display="flex" justifyContent="center" p={2}>
                                    <Button
                                        variant="outlined"
                                        onClick={() => setPage((p) => p + 1)}
                                        disabled={loading}
                                    >
                                        {loading ? <CircularProgress size={24} /> : 'Load More'}
                                    </Button>
                                </Box>
                            </Grid>
                        )}
                    </Grid>
                )}
            </Box>
        );
    };

    // ============================================================================
    // RENDER: TASK DETAIL MODAL
    // ============================================================================

    const renderTaskDetail = () => {
        if (!selectedTask) return null;

        return (
            <Dialog
                open={detailDialogOpen}
                onClose={() => setDetailDialogOpen(false)}
                maxWidth="md"
                fullWidth
            >
                <DialogTitle>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="h6">{selectedTask.title}</Typography>
                        <Box display="flex" gap={1}>
                            <Chip
                                label={selectedTask.priority.toUpperCase()}
                                size="small"
                                sx={{ bgcolor: getPriorityColor(selectedTask.priority), color: 'white' }}
                            />
                            <IconButton size="small" onClick={() => setDetailDialogOpen(false)}>
                                <CloseIcon />
                            </IconButton>
                        </Box>
                    </Box>
                </DialogTitle>
                <DialogContent dividers>
                    <Stack spacing={3}>
                        {/* Description */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                Description
                            </Typography>
                            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                                <Typography variant="body2" style={{ whiteSpace: 'pre-wrap' }}>
                                    {selectedTask.description}
                                </Typography>
                            </Paper>
                        </Box>

                        {/* Status and Progress */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                Status & Progress
                            </Typography>
                            <Grid container spacing={2}>
                                <Grid item xs={6}>
                                    <FormControl fullWidth size="small">
                                        <InputLabel>Status</InputLabel>
                                        <Select
                                            value={selectedTask.status}
                                            onChange={(e) => handleUpdateStatus(selectedTask.task_id, e.target.value)}
                                        >
                                            <MenuItem value="NOT_STARTED">Not Started</MenuItem>
                                            <MenuItem value="IN_PROGRESS">In Progress</MenuItem>
                                            <MenuItem value="BLOCKED">Blocked</MenuItem>
                                            <MenuItem value="UNDER_REVIEW">Under Review</MenuItem>
                                            <MenuItem value="COMPLETED">Completed</MenuItem>
                                            <MenuItem value="CANCELLED">Cancelled</MenuItem>
                                        </Select>
                                    </FormControl>
                                </Grid>
                                <Grid item xs={6}>
                                    <Typography variant="caption" gutterBottom>
                                        Progress: {selectedTask.progress_percentage}%
                                    </Typography>
                                    <Slider
                                        value={selectedTask.progress_percentage}
                                        onChange={(_, value) => handleUpdateProgress(selectedTask.task_id, value as number)}
                                        valueLabelDisplay="auto"
                                        step={10}
                                        marks
                                        min={0}
                                        max={100}
                                    />
                                </Grid>
                            </Grid>
                        </Box>

                        {/* Assignee Info */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                Assignment Details
                            </Typography>
                            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                                <Grid container spacing={2}>
                                    <Grid item xs={6}>
                                        <Typography variant="caption" color="text.secondary">
                                            Assigned to
                                        </Typography>
                                        <Typography variant="body2">
                                            {selectedTask.assignee_name || 'Unknown'}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="caption" color="text.secondary">
                                            Assigned by
                                        </Typography>
                                        <Typography variant="body2">
                                            {selectedTask.assigner_name || 'Unknown'}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="caption" color="text.secondary">
                                            Due Date
                                        </Typography>
                                        <Typography variant="body2">
                                            {selectedTask.due_date
                                                ? format(parseISO(selectedTask.due_date), 'MMM dd, yyyy')
                                                : 'No due date'}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="caption" color="text.secondary">
                                            Hours (Actual / Estimated)
                                        </Typography>
                                        <Typography variant="body2">
                                            {selectedTask.actual_hours || 0}h / {selectedTask.estimated_hours || 0}h
                                        </Typography>
                                    </Grid>
                                </Grid>
                            </Paper>
                        </Box>

                        {/* Status History Timeline */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                <TimelineIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Status History
                            </Typography>
                            <Stepper orientation="vertical">
                                {taskHistory.map((history, index) => (
                                    <Step key={index} active completed={index < taskHistory.length - 1}>
                                        <StepLabel>
                                            <Typography variant="caption">
                                                {format(parseISO(history.timestamp), 'MMM dd, yyyy HH:mm')}
                                            </Typography>
                                        </StepLabel>
                                        <StepContent>
                                            <Typography variant="body2">
                                                <strong>{history.user_name}</strong> {history.action}
                                                {history.old_value && history.new_value && (
                                                    <>
                                                        {' '}from <Chip label={history.old_value} size="small" /> to{' '}
                                                        <Chip label={history.new_value} size="small" />
                                                    </>
                                                )}
                                            </Typography>
                                        </StepContent>
                                    </Step>
                                ))}
                            </Stepper>
                        </Box>

                        {/* Time Logging */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                Time Logging
                            </Typography>
                            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                                <Grid container spacing={2} mb={2}>
                                    <Grid item xs={4}>
                                        <TextField
                                            label="Date"
                                            type="date"
                                            size="small"
                                            fullWidth
                                            InputLabelProps={{ shrink: true }}
                                            value={timeLogForm.date}
                                            onChange={(e) => setTimeLogForm({ ...timeLogForm, date: e.target.value })}
                                        />
                                    </Grid>
                                    <Grid item xs={4}>
                                        <TextField
                                            label="Hours"
                                            type="number"
                                            size="small"
                                            fullWidth
                                            inputProps={{ min: 0.1, max: 24, step: 0.5 }}
                                            value={timeLogForm.hours}
                                            onChange={(e) => setTimeLogForm({ ...timeLogForm, hours: parseFloat(e.target.value) })}
                                        />
                                    </Grid>
                                    <Grid item xs={4}>
                                        <Button
                                            variant="contained"
                                            fullWidth
                                            size="large"
                                            onClick={handleAddTimeLog}
                                        >
                                            Log Time
                                        </Button>
                                    </Grid>
                                    <Grid item xs={12}>
                                        <TextField
                                            label="Description (optional)"
                                            size="small"
                                            fullWidth
                                            multiline
                                            rows={2}
                                            value={timeLogForm.description}
                                            onChange={(e) => setTimeLogForm({ ...timeLogForm, description: e.target.value })}
                                        />
                                    </Grid>
                                </Grid>

                                {taskTimeLogs.length > 0 && (
                                    <Box>
                                        <Typography variant="caption" color="text.secondary" gutterBottom>
                                            Time Log History
                                        </Typography>
                                        <List dense>
                                            {taskTimeLogs.map((log) => (
                                                <ListItem key={log.log_id}>
                                                    <ListItemText
                                                        primary={`${log.hours_logged}h - ${log.user_name}`}
                                                        secondary={`${format(parseISO(log.log_date), 'MMM dd, yyyy')} ${log.description ? `- ${log.description}` : ''
                                                            }`}
                                                    />
                                                </ListItem>
                                            ))}
                                        </List>
                                    </Box>
                                )}
                            </Paper>
                        </Box>

                        {/* Comments Thread */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                <CommentIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Comments ({taskComments.length})
                            </Typography>

                            <Stack spacing={2} mb={2}>
                                {taskComments.map((comment) => (
                                    <Paper key={comment.comment_id} sx={{ p: 2 }}>
                                        <Box display="flex" gap={2}>
                                            <Avatar sx={{ width: 32, height: 32 }}>
                                                {comment.user_name.charAt(0)}
                                            </Avatar>
                                            <Box flex={1}>
                                                <Box display="flex" justifyContent="space-between" mb={0.5}>
                                                    <Typography variant="subtitle2" fontWeight="bold">
                                                        {comment.user_name}
                                                    </Typography>
                                                    <Typography variant="caption" color="text.secondary">
                                                        {formatDistanceToNow(parseISO(comment.created_at))} ago
                                                    </Typography>
                                                </Box>
                                                <Typography variant="body2" style={{ whiteSpace: 'pre-wrap' }}>
                                                    {comment.comment_text}
                                                </Typography>
                                            </Box>
                                        </Box>
                                    </Paper>
                                ))}
                            </Stack>

                            <Box display="flex" gap={1}>
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={2}
                                    placeholder="Add a comment..."
                                    value={commentText}
                                    onChange={(e) => setCommentText(e.target.value)}
                                />
                                <Button
                                    variant="contained"
                                    startIcon={<SendIcon />}
                                    onClick={handleAddComment}
                                    disabled={!commentText.trim()}
                                >
                                    Send
                                </Button>
                            </Box>
                        </Box>
                    </Stack>
                </DialogContent>
            </Dialog>
        );
    };

    // ============================================================================
    // RENDER: BROADCAST MESSAGE DIALOG
    // ============================================================================

    const renderBroadcastDialog = () => (
        <Dialog
            open={broadcastDialogOpen}
            onClose={() => !sendingBroadcast && setBroadcastDialogOpen(false)}
            maxWidth="lg"
            fullWidth
        >
            <DialogTitle>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Box display="flex" alignItems="center" gap={1}>
                        <BroadcastIcon color="primary" />
                        <Typography variant="h6">Send Broadcast Message</Typography>
                    </Box>
                    <Box display="flex" gap={1}>
                        <Tooltip title="Use Template">
                            <IconButton onClick={() => setUseTemplate(!useTemplate)} color="secondary">
                                <TemplateIcon />
                            </IconButton>
                        </Tooltip>
                    </Box>
                </Box>
            </DialogTitle>
            <DialogContent>
                {broadcastSuccess ? (
                    <Alert severity="success" sx={{ mb: 2 }}>
                        ✅ Message sent successfully to {broadcastRecipients.replace('_', ' ')}!
                    </Alert>
                ) : (
                    <Grid container spacing={3}>
                        <Grid item xs={12}>
                            <Alert severity="info" icon={<AiIcon />}>
                                💡 Tip: Use the AI Assistant (purple sparkle button in header) to generate broadcast messages.
                                Just say "send this message to all managers" and the AI will help you compose it!
                            </Alert>
                        </Grid>

                        {/* Template Selector */}
                        {useTemplate && (
                            <Grid item xs={12}>
                                <FormControl fullWidth>
                                    <InputLabel>Select Template</InputLabel>
                                    <Select
                                        value={selectedTemplate}
                                        onChange={(e) => applyTemplate(e.target.value)}
                                        label="Select Template"
                                    >
                                        {Object.entries(messageTemplates).map(([key, template]) => (
                                            <MenuItem key={key} value={key}>
                                                <Box>
                                                    <Typography variant="body2" fontWeight="bold">{template.name}</Typography>
                                                    <Typography variant="caption" color="text.secondary">
                                                        {template.content.substring(0, 60)}...
                                                    </Typography>
                                                </Box>
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                        )}

                        {/* Recipients Selection */}
                        <Grid item xs={12} md={6}>
                            <FormControl fullWidth>
                                <InputLabel>Recipients</InputLabel>
                                <Select
                                    value={broadcastRecipients}
                                    onChange={(e) => setBroadcastRecipients(e.target.value as any)}
                                    label="Recipients"
                                >
                                    <MenuItem value="all_managers">
                                        <Box display="flex" alignItems="center" gap={1}>
                                            <PeopleIcon fontSize="small" />
                                            All Managers
                                        </Box>
                                    </MenuItem>
                                    <MenuItem value="all_employees">
                                        <Box display="flex" alignItems="center" gap={1}>
                                            <PeopleIcon fontSize="small" />
                                            All Employees
                                        </Box>
                                    </MenuItem>
                                    <MenuItem value="specific_teams">
                                        <Box display="flex" alignItems="center" gap={1}>
                                            <TeamIcon fontSize="small" />
                                            Specific Teams
                                        </Box>
                                    </MenuItem>
                                    <MenuItem value="custom">
                                        <Box display="flex" alignItems="center" gap={1}>
                                            <PeopleIcon fontSize="small" />
                                            Custom Recipients
                                        </Box>
                                    </MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>

                        {/* Schedule Option */}
                        <Grid item xs={12} md={6}>
                            <Box display="flex" gap={1}>
                                <TextField
                                    type="date"
                                    label="Schedule Date (Optional)"
                                    value={scheduleDate}
                                    onChange={(e) => setScheduleDate(e.target.value)}
                                    InputLabelProps={{ shrink: true }}
                                    fullWidth
                                />
                                <TextField
                                    type="time"
                                    label="Time"
                                    value={scheduleTime}
                                    onChange={(e) => setScheduleTime(e.target.value)}
                                    InputLabelProps={{ shrink: true }}
                                    fullWidth
                                    disabled={!scheduleDate}
                                />
                            </Box>
                        </Grid>

                        {/* Team Selection (if specific_teams) */}
                        {broadcastRecipients === 'specific_teams' && (
                            <Grid item xs={12}>
                                <FormControl fullWidth>
                                    <InputLabel>Select Teams</InputLabel>
                                    <Select
                                        multiple
                                        value={selectedTeams}
                                        onChange={(e) => setSelectedTeams(e.target.value as number[])}
                                        label="Select Teams"
                                        renderValue={(selected) => (
                                            <Box display="flex" flexWrap="wrap" gap={0.5}>
                                                {selected.map((teamId) => {
                                                    const team = availableTeams.find(t => t.id === teamId);
                                                    return <Chip key={teamId} label={team?.name || `Team ${teamId}`} size="small" />;
                                                })}
                                            </Box>
                                        )}
                                    >
                                        {availableTeams.map((team) => (
                                            <MenuItem key={team.id} value={team.id}>
                                                <Checkbox checked={selectedTeams.includes(team.id)} />
                                                <ListItemText primary={team.name} secondary={`${team.member_count || 0} members`} />
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                        )}

                        {/* Custom Recipients (if custom) */}
                        {broadcastRecipients === 'custom' && (
                            <Grid item xs={12}>
                                <FormControl fullWidth>
                                    <InputLabel>Select Recipients</InputLabel>
                                    <Select
                                        multiple
                                        value={selectedEmployees}
                                        onChange={(e) => setSelectedEmployees(e.target.value as number[])}
                                        label="Select Recipients"
                                        renderValue={(selected) => (
                                            <Box display="flex" flexWrap="wrap" gap={0.5}>
                                                {selected.map((empId) => {
                                                    const emp = availableEmployees.find(e => e.id === empId);
                                                    return <Chip key={empId} label={emp?.first_name || `Employee ${empId}`} size="small" />;
                                                })}
                                            </Box>
                                        )}
                                    >
                                        {availableEmployees.map((emp) => (
                                            <MenuItem key={emp.id} value={emp.id}>
                                                <Checkbox checked={selectedEmployees.includes(emp.id)} />
                                                <ListItemAvatar>
                                                    <Avatar src={emp.avatar} />
                                                </ListItemAvatar>
                                                <ListItemText
                                                    primary={`${emp.first_name} ${emp.last_name}`}
                                                    secondary={emp.designation}
                                                />
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                        )}

                        {/* Message Editor */}
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                multiline
                                rows={10}
                                label="Message"
                                placeholder="Type your message here or use AI/Template to generate..."
                                value={broadcastMessage}
                                onChange={(e) => setBroadcastMessage(e.target.value)}
                                disabled={sendingBroadcast}
                            />
                        </Grid>

                        {/* File Attachments */}
                        <Grid item xs={12}>
                            <Box>
                                <input
                                    accept="image/*,application/pdf,.doc,.docx,.xls,.xlsx"
                                    style={{ display: 'none' }}
                                    id="broadcast-file-upload"
                                    type="file"
                                    multiple
                                    onChange={handleFileUpload}
                                />
                                <label htmlFor="broadcast-file-upload">
                                    <Button
                                        variant="outlined"
                                        component="span"
                                        startIcon={<UploadIcon />}
                                    >
                                        Attach Files
                                    </Button>
                                </label>
                                {attachments.length > 0 && (
                                    <Box mt={1} display="flex" flexWrap="wrap" gap={1}>
                                        {attachments.map((file, index) => (
                                            <Chip
                                                key={index}
                                                label={file.name}
                                                onDelete={() => removeAttachment(index)}
                                                icon={<AttachIcon />}
                                                color="primary"
                                                variant="outlined"
                                            />
                                        ))}
                                    </Box>
                                )}
                            </Box>
                        </Grid>

                        {/* Message Preview */}
                        <Grid item xs={12}>
                            <Paper elevation={2} sx={{ p: 2, bgcolor: 'grey.50' }}>
                                <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                                    <strong>📱 Preview:</strong>
                                </Typography>
                                <Divider sx={{ my: 1 }} />
                                <Box sx={{ p: 1 }}>
                                    <Typography variant="body2" fontWeight="bold" color="primary">
                                        📢 Broadcast Message from HR
                                    </Typography>
                                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mt: 1 }}>
                                        {broadcastMessage || '(Your message will appear here)'}
                                    </Typography>
                                    {attachments.length > 0 && (
                                        <Box mt={1}>
                                            <Typography variant="caption" color="text.secondary">
                                                📎 {attachments.length} attachment(s)
                                            </Typography>
                                        </Box>
                                    )}
                                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', fontStyle: 'italic' }}>
                                        {scheduleDate ? `Scheduled for ${scheduleDate} ${scheduleTime}` : 'Sending immediately'}
                                    </Typography>
                                </Box>
                            </Paper>
                        </Grid>
                    </Grid>
                )}
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
                <Button
                    onClick={() => {
                        setBroadcastDialogOpen(false);
                        resetBroadcastForm();
                    }}
                    disabled={sendingBroadcast}
                >
                    Cancel
                </Button>
                {scheduleDate && scheduleTime && (
                    <Button
                        variant="outlined"
                        startIcon={<ScheduleIcon />}
                        onClick={handleSendBroadcast}
                        disabled={!broadcastMessage.trim() || sendingBroadcast}
                    >
                        Schedule Broadcast
                    </Button>
                )}
                <Button
                    variant="contained"
                    startIcon={sendingBroadcast ? <CircularProgress size={16} /> : <SendIcon />}
                    onClick={handleSendBroadcast}
                    disabled={!broadcastMessage.trim() || sendingBroadcast || broadcastSuccess}
                >
                    {sendingBroadcast ? 'Sending...' : scheduleDate ? 'Schedule & Send' : 'Send Now'}
                </Button>
            </DialogActions>
        </Dialog>
    );

    // ============================================================================
    // RENDER: CALENDAR VIEW
    // ============================================================================

    const renderCalendar = () => (
        <Box>
            <Alert severity="info" icon={<CalendarIcon />}>
                Calendar view coming soon. This will use FullCalendar to display tasks by due date with
                drag-and-drop rescheduling capabilities.
            </Alert>
            <Paper sx={{ p: 4, mt: 2, textAlign: 'center' }}>
                <CalendarIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                    Calendar View
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Visualize your tasks on a calendar grid with color-coded priorities and due dates.
                    Features: Month/Week/Day views, drag-drop reschedule, overdue highlighting.
                </Typography>
            </Paper>
        </Box>
    );

    // ============================================================================
    // RENDER: DEPENDENCIES VIEW
    // ============================================================================

    const renderDependencies = () => (
        <Box>
            <Alert severity="info" icon={<DependencyIcon />}>
                Dependencies view coming soon. This will use React Flow to display task relationships as a
                directed graph with critical path highlighting.
            </Alert>
            <Paper sx={{ p: 4, mt: 2, textAlign: 'center' }}>
                <DependencyIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                    Task Dependencies Graph
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Interactive graph showing task dependencies and relationships. Features: Critical path
                    analysis, block indicators, dependency chains, drag-to-arrange nodes.
                </Typography>
            </Paper>
        </Box>
    );

    // ============================================================================
    // MAIN RENDER
    // ============================================================================

    return (
        <Box sx={{ p: 3 }}>
            {/* Header */}
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h4" fontWeight="bold">
                    My Work Inbox
                </Typography>
                <Box display="flex" gap={2} alignItems="center">
                    <Chip
                        label={`${tasks.filter((t) => t.status !== 'COMPLETED').length} Active`}
                        color="primary"
                    />
                    <Chip
                        label={`${tasks.filter((t) => t.is_overdue).length} Overdue`}
                        color="error"
                    />
                    {/* Broadcast button - HR only */}
                    {currentEmployee?.role === 'hr' && (
                        <Button
                            variant="contained"
                            startIcon={<BroadcastIcon />}
                            onClick={() => setBroadcastDialogOpen(true)}
                            sx={{
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                '&:hover': {
                                    background: 'linear-gradient(135deg, #5568d3 0%, #614a8c 100%)',
                                }
                            }}
                        >
                            Send Broadcast
                        </Button>
                    )}
                </Box>
            </Box>

            {/* View Toggle */}
            <Box mb={2}>
                <ToggleButtonGroup
                    value={activeView}
                    exclusive
                    onChange={(_, newView) => newView && setActiveView(newView)}
                >
                    <ToggleButton value="list">
                        <ListViewIcon sx={{ mr: 1 }} />
                        List
                    </ToggleButton>
                    <ToggleButton value="calendar">
                        <CalendarIcon sx={{ mr: 1 }} />
                        Calendar
                    </ToggleButton>
                    <ToggleButton value="dependencies">
                        <DependencyIcon sx={{ mr: 1 }} />
                        Dependencies
                    </ToggleButton>
                </ToggleButtonGroup>
            </Box>

            {/* Filters */}
            {activeView === 'list' && <Box mb={2}>{renderFilters()}</Box>}

            {/* Content */}
            <Box>
                {activeView === 'list' && renderTaskList()}
                {activeView === 'calendar' && renderCalendar()}
                {activeView === 'dependencies' && renderDependencies()}
            </Box>

            {/* Task Detail Modal */}
            {renderTaskDetail()}

            {/* Broadcast Message Dialog */}
            {renderBroadcastDialog()}
        </Box>
    );
};

export default WorkInbox;
