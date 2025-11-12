import { useEffect, useState, useRef } from "react";
import apiClient from "../api/client";
import { toast } from "react-hot-toast";
import { format, startOfMonth, endOfMonth, differenceInHours, differenceInMinutes } from "date-fns";
import { GroupChat } from "./GroupChat";

interface EmployeeDashboardProps {
  employee: any | null;
}

export function EmployeeDashboard({ employee }: EmployeeDashboardProps) {
  const [todayAttendance, setTodayAttendance] = useState<any | null>(null);
  const [leaveBalance, setLeaveBalance] = useState<any[] | null>(null);
  const [monthAttendance, setMonthAttendance] = useState<any[]>([]);
  const [upcomingLeaves, setUpcomingLeaves] = useState<any[]>([]);
  const [recentActivities, setRecentActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [showGroupChat, setShowGroupChat] = useState(false);

  // Swipe states
  const [clockInSwipeX, setClockInSwipeX] = useState(0);
  const [clockOutSwipeX, setClockOutSwipeX] = useState(0);
  const [isClockInDragging, setIsClockInDragging] = useState(false);
  const [isClockOutDragging, setIsClockOutDragging] = useState(false);
  const clockInRef = useRef<HTMLDivElement>(null);
  const clockOutRef = useRef<HTMLDivElement>(null);

  // Update current time every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!employee) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        const today = new Date();
        const monthStart = format(startOfMonth(today), 'yyyy-MM-dd');
        const monthEnd = format(endOfMonth(today), 'yyyy-MM-dd');

        const [attRes, leaveRes, monthAttRes, upcomingLeavesRes] = await Promise.all([
          apiClient.get('/attendance/today', { params: { employee_id: employee.id } }),
          apiClient.get('/leaves/balance', { params: { employee_id: employee.id, year: new Date().getFullYear() } }),
          apiClient.get('/attendance/history', {
            params: {
              employee_id: employee.id,
              start_date: monthStart,
              end_date: monthEnd
            }
          }).catch(() => ({ data: [] })),
          apiClient.get('/leaves/applications', {
            params: {
              employee_id: employee.id,
              status: 'approved'
            }
          }).catch(() => ({ data: [] }))
        ]);

        setTodayAttendance(attRes.data ?? null);
        setLeaveBalance(leaveRes.data ?? null);
        setMonthAttendance(monthAttRes.data ?? []);
        setUpcomingLeaves(upcomingLeavesRes.data?.slice(0, 3) ?? []);

        // Mock recent activities (can be replaced with real API)
        setRecentActivities([
          { type: 'clock_in', time: '09:00 AM', date: format(today, 'MMM dd') },
          { type: 'leave_applied', time: '03:30 PM', date: format(new Date(today.getTime() - 86400000), 'MMM dd') },
          { type: 'clock_out', time: '06:00 PM', date: format(new Date(today.getTime() - 86400000), 'MMM dd') }
        ]);

      } catch (err: any) {
        console.error('Failed to load dashboard data', err);
        toast.error('Failed to load some dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [employee]);

  // Swipe constants
  const SWIPE_THRESHOLD = 0.75; // 75% of container width triggers action

  // Mouse event handlers
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isClockInDragging) {
        if (!clockInRef.current) return;
        const rect = clockInRef.current.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const containerWidth = rect.width;
        const newX = Math.max(0, Math.min(offsetX, containerWidth));
        setClockInSwipeX(newX);

        if (newX / containerWidth >= SWIPE_THRESHOLD && !todayAttendance?.checkIn) {
          handleClockIn();
          setIsClockInDragging(false);
          setTimeout(() => setClockInSwipeX(0), 300);
        }
      }

      if (isClockOutDragging) {
        if (!clockOutRef.current) return;
        const rect = clockOutRef.current.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const containerWidth = rect.width;
        const newX = Math.max(0, Math.min(offsetX, containerWidth));
        setClockOutSwipeX(newX);

        if (newX / containerWidth >= SWIPE_THRESHOLD && todayAttendance?.checkIn && !todayAttendance?.checkOut) {
          handleClockOut();
          setIsClockOutDragging(false);
          setTimeout(() => setClockOutSwipeX(0), 300);
        }
      }
    };

    const handleMouseUp = () => {
      setIsClockInDragging(false);
      setIsClockOutDragging(false);
      setClockInSwipeX(0);
      setClockOutSwipeX(0);
    };

    if (isClockInDragging || isClockOutDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isClockInDragging, isClockOutDragging, todayAttendance, SWIPE_THRESHOLD]);

  const handleClockIn = async () => {
    if (!employee) return;
    try {
      await apiClient.post('/attendance/check-in', null, { params: { employee_id: employee.id } });
      toast.success('Clocked in successfully!');
      const res = await apiClient.get('/attendance/today', { params: { employee_id: employee.id } });
      setTodayAttendance(res.data ?? null);
    } catch (err: any) {
      toast.error(err?.message || 'Failed to clock in');
    }
  };

  const handleClockOut = async () => {
    if (!employee) return;
    try {
      await apiClient.post('/attendance/check-out', null, { params: { employee_id: employee.id } });
      toast.success('Clocked out successfully!');
      const res = await apiClient.get('/attendance/today', { params: { employee_id: employee.id } });
      setTodayAttendance(res.data ?? null);
    } catch (err: any) {
      toast.error(err?.message || 'Failed to clock out');
    }
  };

  if (!employee) {
    return <div className="p-6">Loading...</div>;
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  // Calculate month statistics
  const monthStats = monthAttendance.reduce(
    (acc: any, att: any) => {
      if (att.checkIn && att.checkOut) {
        const hours = differenceInHours(new Date(att.checkOut), new Date(att.checkIn));
        const minutes = differenceInMinutes(new Date(att.checkOut), new Date(att.checkIn)) % 60;
        acc.totalHours += hours + minutes / 60;
        acc.daysPresent += 1;
      }
      return acc;
    },
    { totalHours: 0, daysPresent: 0 }
  );

  const avgHours = monthStats.daysPresent > 0 ? (monthStats.totalHours / monthStats.daysPresent).toFixed(1) : 0;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header with Date & Time */}
      <div className="bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 dark:from-blue-600 dark:via-purple-600 dark:to-pink-600 p-8 rounded-2xl text-white shadow-xl">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold mb-2">Welcome back, {employee.first_name}! 👋</h1>
            <p className="text-blue-100 text-lg">{format(currentTime, 'EEEE, MMMM dd, yyyy')}</p>
          </div>
          <div className="text-right">
            <div className="text-5xl font-bold">{format(currentTime, 'HH:mm')}</div>
            <div className="text-blue-100 text-sm">{format(currentTime, 'ss')} sec</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Main Content */}
        <div className="lg:col-span-2 space-y-6">

          {/* Swipe to Clock In/Out */}
          <div className="space-y-4">
            {/* Clock In Swipe */}
            {!todayAttendance?.checkIn ? (
              <div
                ref={clockInRef}
                className="relative bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 rounded-2xl overflow-hidden cursor-pointer select-none shadow-lg border-2 border-green-200 dark:border-green-700"
                onMouseDown={(e) => {
                  if (todayAttendance?.checkIn) return;
                  setIsClockInDragging(true);
                  e.preventDefault();
                }}
                onTouchStart={(e) => {
                  if (todayAttendance?.checkIn) return;
                  setIsClockInDragging(true);
                  e.preventDefault();
                }}
              >
                {/* Progress Background */}
                <div
                  className="absolute inset-0 bg-gradient-to-r from-green-400 to-green-600 transition-all duration-200"
                  style={{
                    width: clockInRef.current ? `${(clockInSwipeX / clockInRef.current.offsetWidth) * 100}%` : '0%',
                    opacity: 0.3
                  }}
                />

                {/* Content */}
                <div className="relative z-10 p-6 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 bg-green-500 rounded-full flex items-center justify-center text-white text-2xl shadow-lg">
                      ▶
                    </div>
                    <div>
                      <p className="text-xl font-bold text-green-700 dark:text-green-300">Swipe to Clock In →</p>
                      <p className="text-sm text-green-600 dark:text-green-400">Start your workday</p>
                    </div>
                  </div>
                  <div className="text-green-600 dark:text-green-400 text-4xl animate-pulse">➜</div>
                </div>
              </div>
            ) : (
              <div className="bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 rounded-2xl p-6 border-2 border-green-500 dark:border-green-600 shadow-lg">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 bg-green-500 rounded-full flex items-center justify-center text-white text-2xl">
                    ✓
                  </div>
                  <div>
                    <p className="text-xl font-bold text-green-700 dark:text-green-300">Clocked In</p>
                    <p className="text-sm text-green-600 dark:text-green-400">
                      {todayAttendance?.checkIn && new Date(todayAttendance.checkIn).toString() !== 'Invalid Date'
                        ? format(new Date(todayAttendance.checkIn), 'hh:mm a')
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Clock Out Swipe */}
            {todayAttendance?.checkIn && !todayAttendance?.checkOut ? (
              <div
                ref={clockOutRef}
                className="relative bg-gradient-to-r from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-800/20 rounded-2xl overflow-hidden cursor-pointer select-none shadow-lg border-2 border-red-200 dark:border-red-700"
                onMouseDown={(e) => {
                  if (!todayAttendance?.checkIn || todayAttendance?.checkOut) return;
                  setIsClockOutDragging(true);
                  e.preventDefault();
                }}
                onTouchStart={(e) => {
                  if (!todayAttendance?.checkIn || todayAttendance?.checkOut) return;
                  setIsClockOutDragging(true);
                  e.preventDefault();
                }}
              >
                {/* Progress Background */}
                <div
                  className="absolute inset-0 bg-gradient-to-r from-red-400 to-red-600 transition-all duration-200"
                  style={{
                    width: clockOutRef.current ? `${(clockOutSwipeX / clockOutRef.current.offsetWidth) * 100}%` : '0%',
                    opacity: 0.3
                  }}
                />

                {/* Content */}
                <div className="relative z-10 p-6 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 bg-red-500 rounded-full flex items-center justify-center text-white text-2xl shadow-lg">
                      ◼
                    </div>
                    <div>
                      <p className="text-xl font-bold text-red-700 dark:text-red-300">Swipe to Clock Out →</p>
                      <p className="text-sm text-red-600 dark:text-red-400">End your workday</p>
                    </div>
                  </div>
                  <div className="text-red-600 dark:text-red-400 text-4xl animate-pulse">➜</div>
                </div>
              </div>
            ) : todayAttendance?.checkOut ? (
              <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800/50 dark:to-gray-700/50 rounded-2xl p-6 border-2 border-gray-300 dark:border-gray-600 shadow-lg">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 bg-gray-500 rounded-full flex items-center justify-center text-white text-2xl">
                    ✓
                  </div>
                  <div>
                    <p className="text-xl font-bold text-gray-700 dark:text-gray-300">Clocked Out</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {todayAttendance?.checkOut && new Date(todayAttendance.checkOut).toString() !== 'Invalid Date'
                        ? format(new Date(todayAttendance.checkOut), 'hh:mm a')
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          {/* Quick Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-3xl">📅</span>
                <h3 className="font-semibold text-gray-700 dark:text-gray-300">Days Present</h3>
              </div>
              <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{monthStats.daysPresent}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">This month</p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-3xl">⏱️</span>
                <h3 className="font-semibold text-gray-700 dark:text-gray-300">Avg Hours</h3>
              </div>
              <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{avgHours}h</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Per day</p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-3xl">🕐</span>
                <h3 className="font-semibold text-gray-700 dark:text-gray-300">Total Hours</h3>
              </div>
              <p className="text-3xl font-bold text-green-600 dark:text-green-400">{monthStats.totalHours.toFixed(1)}h</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">This month</p>
            </div>
          </div>

          {/* Recent Activities */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-bold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
              <span className="text-2xl">📊</span>
              Recent Activities
            </h3>
            <div className="space-y-3">
              {recentActivities.map((activity, idx) => (
                <div key={idx} className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${activity.type === 'clock_in' ? 'bg-green-100 dark:bg-green-900/30 text-green-600' :
                    activity.type === 'clock_out' ? 'bg-red-100 dark:bg-red-900/30 text-red-600' :
                      'bg-blue-100 dark:bg-blue-900/30 text-blue-600'
                    }`}>
                    {activity.type === 'clock_in' ? '▶' : activity.type === 'clock_out' ? '◼' : '📝'}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 dark:text-white">
                      {activity.type === 'clock_in' ? 'Clocked In' :
                        activity.type === 'clock_out' ? 'Clocked Out' :
                          'Leave Applied'}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{activity.date} at {activity.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column - Sidebar */}
        <div className="space-y-6">
          {/* Leave Balance */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-bold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
              <span className="text-2xl">🏖️</span>
              Leave Balance
            </h3>
            {leaveBalance && leaveBalance.length > 0 ? (
              <div className="space-y-3">
                {leaveBalance.slice(0, 4).map((lb: any) => (
                  <div key={lb.leaveType._id} className="flex justify-between items-center p-3 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg">
                    <span className="font-medium text-gray-700 dark:text-gray-300">{lb.leaveType.name}</span>
                    <span className="font-bold text-lg text-blue-600 dark:text-blue-400">{lb.balance.balance}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">No leave balance available</p>
            )}
          </div>

          {/* Upcoming Leaves */}
          {upcomingLeaves.length > 0 && (
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700">
              <h3 className="text-xl font-bold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
                <span className="text-2xl">📆</span>
                Upcoming Leaves
              </h3>
              <div className="space-y-3">
                {upcomingLeaves.map((leave: any, idx: number) => (
                  <div key={idx} className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
                    <p className="font-medium text-gray-900 dark:text-white">{leave.leaveType?.name || 'Leave'}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {leave.startDate && new Date(leave.startDate).toString() !== 'Invalid Date'
                        ? format(new Date(leave.startDate), 'MMM dd')
                        : 'N/A'} -
                      {leave.endDate && new Date(leave.endDate).toString() !== 'Invalid Date'
                        ? format(new Date(leave.endDate), 'MMM dd')
                        : 'N/A'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">Quick Actions</h3>
            <div className="space-y-2">
              <button className="w-full py-3 px-4 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg font-medium transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2">
                <span>📝</span> Apply Leave
              </button>
              <button className="w-full py-3 px-4 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white rounded-lg font-medium transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2">
                <span>💰</span> Submit Expense
              </button>
              <button className="w-full py-3 px-4 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white rounded-lg font-medium transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2">
                <span>📊</span> View Reports
              </button>
              <button
                onClick={() => setShowGroupChat(!showGroupChat)}
                className="w-full py-3 px-4 bg-gradient-to-r from-pink-500 to-pink-600 hover:from-pink-600 hover:to-pink-700 text-white rounded-lg font-medium transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
              >
                <span>💬</span> Group Chat
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Floating Group Chat */}
      {showGroupChat && employee && (
        <GroupChat employee={employee} onClose={() => setShowGroupChat(false)} />
      )}
    </div>
  );
}
