import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import {
  Calendar,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Clock,
  CheckCircle,
  XCircle,
  BarChart3,
  PieChart,
  History,
  Info
} from 'lucide-react';

interface LeaveBalanceProps {
  employeeId: string;
}

export const EnhancedLeaveBalance: React.FC<LeaveBalanceProps> = ({ employeeId }) => {
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [viewMode, setViewMode] = useState<'summary' | 'detailed' | 'history'>('summary');
  const [leaveBalance, setLeaveBalance] = useState<any[]>([]);
  const [balanceSummary, setBalanceSummary] = useState<any | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetch = async () => {
      try {
        const res = await apiClient.get('/leaves/balance', { params: { employee_id: employeeId, year: selectedYear } });
        if (!mounted) return;
        const balances = res.data ?? [];
        setLeaveBalance(balances);

        // compute a lightweight summary
        const totalAvailable = balances.reduce((s: number, b: any) => s + (b.balance?.balance || 0), 0);
        const totalConsumed = balances.reduce((s: number, b: any) => s + (b.balance?.consumed || 0), 0);
        const totalPending = balances.reduce((s: number, b: any) => s + (b.pendingDays || 0), 0);
        const totalOpeningAccrued = balances.reduce((s: number, b: any) => s + ((b.balance?.opening || 0) + (b.balance?.accrued || 0)), 0);
        const utilizationRate = totalOpeningAccrued > 0 ? Math.round((totalConsumed / totalOpeningAccrued) * 100) : 0;

        setBalanceSummary({
          totalAvailable,
          totalConsumed,
          totalPending,
          utilizationRate,
          lowBalanceTypes: balances.filter((b: any) => b.isLowBalance),
          upcomingLeaves: []
        });
      } catch (err) {
        console.error('Failed to load leave balance', err);
      }
    };
    fetch();
    return () => { mounted = false; };
  }, [employeeId, selectedYear]);

  if (!leaveBalance || balanceSummary === null) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/3"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-32 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 5 }, (_, i) => currentYear - 2 + i);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Leave Balance</h2>
          <p className="text-gray-600">Track your leave entitlements and usage</p>
        </div>

        <div className="flex items-center space-x-4">
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {years.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>

          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('summary')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${viewMode === 'summary'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Summary
            </button>
            <button
              onClick={() => setViewMode('detailed')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${viewMode === 'detailed'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Detailed
            </button>
            <button
              onClick={() => setViewMode('history')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${viewMode === 'history'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              History
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Available</p>
              <p className="text-2xl font-bold text-blue-600">{balanceSummary.totalAvailable}</p>
              <p className="text-xs text-gray-500">days remaining</p>
            </div>
            <Calendar className="w-8 h-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Used This Year</p>
              <p className="text-2xl font-bold text-green-600">{balanceSummary.totalConsumed}</p>
              <p className="text-xs text-gray-500">days taken</p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Pending Approval</p>
              <p className="text-2xl font-bold text-orange-600">{balanceSummary.totalPending}</p>
              <p className="text-xs text-gray-500">days pending</p>
            </div>
            <Clock className="w-8 h-8 text-orange-500" />
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Utilization Rate</p>
              <p className="text-2xl font-bold text-purple-600">{balanceSummary.utilizationRate}%</p>
              <p className="text-xs text-gray-500">of total leaves</p>
            </div>
            <BarChart3 className="w-8 h-8 text-purple-500" />
          </div>
        </div>
      </div>

      {/* Alerts */}
      {balanceSummary.lowBalanceTypes.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />
            <div>
              <h3 className="font-medium text-amber-800">Low Balance Alert</h3>
              <p className="text-sm text-amber-700 mt-1">
                You have low balance in: {balanceSummary.lowBalanceTypes.map((item: any) => item.leaveType.name).join(', ')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      {viewMode === 'summary' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Leave Types Balance */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Leave Types</h3>
              <p className="text-gray-600">Current balance by leave type</p>
            </div>
            <div className="p-6 space-y-4">
              {leaveBalance.map((item: any) => (
                <div key={item.leaveType._id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-gray-900">{item.leaveType.name}</span>
                      {item.isLowBalance && (
                        <AlertTriangle className="w-4 h-4 text-amber-500" />
                      )}
                    </div>
                    <div className="text-right">
                      <span className="font-semibold text-gray-900">{item.balance.balance || 0}</span>
                      <span className="text-gray-500 text-sm"> / {(item.balance.opening || 0) + (item.balance.accrued || 0)}</span>
                    </div>
                  </div>

                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${item.utilizationPercentage > 80 ? 'bg-red-500' :
                          item.utilizationPercentage > 60 ? 'bg-amber-500' :
                            'bg-green-500'
                        }`}
                      style={{ width: `${Math.min(item.utilizationPercentage, 100)}%` }}
                    ></div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Used: {item.balance.consumed} days</span>
                    <span>{item.utilizationPercentage}% utilized</span>
                  </div>

                  {item.pendingDays > 0 && (
                    <div className="text-xs text-orange-600">
                      {item.pendingDays} days pending approval
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming Leaves */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Upcoming Leaves</h3>
              <p className="text-gray-600">Your approved upcoming leaves</p>
            </div>
            <div className="p-6">
              {balanceSummary.upcomingLeaves.length > 0 ? (
                <div className="space-y-4">
                  {balanceSummary.upcomingLeaves.map((leave: any) => (
                    <div key={leave._id} className="flex items-center space-x-4 p-3 bg-blue-50 rounded-lg">
                      <Calendar className="w-5 h-5 text-blue-600" />
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">
                          {leave.startDate === leave.endDate
                            ? new Date(leave.startDate).toLocaleDateString()
                            : `${new Date(leave.startDate).toLocaleDateString()} - ${new Date(leave.endDate).toLocaleDateString()}`
                          }
                        </p>
                        <p className="text-sm text-gray-600">{leave.reason}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-blue-600">{leave.totalDays} days</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No upcoming leaves</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {viewMode === 'detailed' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Detailed Balance Breakdown</h3>
            <p className="text-gray-600">Complete breakdown of your leave balance for {selectedYear}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Leave Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Opening
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Accrued
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Consumed
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Pending
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Balance
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {leaveBalance.map((item: any) => (
                  <tr key={item.leaveType._id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {item.leaveType.name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {item.leaveType.code}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.balance.opening}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.balance.accrued}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.balance.consumed}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-orange-600">
                      {item.pendingDays}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {item.balance.balance}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        {item.isLowBalance ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            <AlertTriangle className="w-3 h-3 mr-1" />
                            Low
                          </span>
                        ) : (item.balance.balance || 0) > 10 ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Good
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            <Info className="w-3 h-3 mr-1" />
                            Moderate
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {viewMode === 'history' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Balance History</h3>
            <p className="text-gray-600">Historical view of your leave balance trends</p>
          </div>
          <div className="p-6">
            <div className="text-center py-12">
              <History className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Balance History</h3>
              <p className="text-gray-600">
                Historical balance tracking will be available here. This feature shows trends and patterns in your leave usage over time.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
