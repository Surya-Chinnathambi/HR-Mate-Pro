import { useState } from "react";

interface ExpensesModuleProps {
  employee: any;
}

export function ExpensesModule({ employee }: ExpensesModuleProps) {
  const [activeTab, setActiveTab] = useState<"expenses" | "travel" | "reimbursements">("expenses");

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-900">Expenses & Travel</h2>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
          + New Expense
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab("expenses")}
            className={`px-6 py-3 font-medium text-sm ${activeTab === "expenses"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            💳 Expense Claims
          </button>
          <button
            onClick={() => setActiveTab("travel")}
            className={`px-6 py-3 font-medium text-sm ${activeTab === "travel"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            ✈️ Travel Requests
          </button>
          <button
            onClick={() => setActiveTab("reimbursements")}
            className={`px-6 py-3 font-medium text-sm ${activeTab === "reimbursements"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            💰 Reimbursements
          </button>
        </div>

        <div className="p-6">
          {activeTab === "expenses" && (
            <div className="space-y-6">
              {/* Expense Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-xl p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-green-100 text-sm">This Month</p>
                      <p className="text-2xl font-bold">₹12,450</p>
                    </div>
                    <div className="w-12 h-12 bg-green-400 rounded-full flex items-center justify-center">
                      <span className="text-green-800 text-xl">💳</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-blue-100 text-sm">Pending Approval</p>
                      <p className="text-2xl font-bold">₹3,200</p>
                    </div>
                    <div className="w-12 h-12 bg-blue-400 rounded-full flex items-center justify-center">
                      <span className="text-blue-800 text-xl">⏳</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-purple-100 text-sm">Reimbursed</p>
                      <p className="text-2xl font-bold">₹9,250</p>
                    </div>
                    <div className="w-12 h-12 bg-purple-400 rounded-full flex items-center justify-center">
                      <span className="text-purple-800 text-xl">✅</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Recent Expenses */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Recent Expenses</h3>

                <div className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Client Meeting Lunch</h4>
                      <p className="text-sm text-gray-600">December 15, 2024 • Food & Beverage</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">₹2,450</p>
                      <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">
                        Pending
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">
                    Business lunch with potential client to discuss project requirements.
                  </p>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500">📎 Receipt attached</span>
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Uber to Airport</h4>
                      <p className="text-sm text-gray-600">December 12, 2024 • Transportation</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">₹750</p>
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                        Approved
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">
                    Transportation for business trip to Mumbai office.
                  </p>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500">📎 Receipt attached</span>
                  </div>
                </div>

                <div className="border rounded-lg p-4 bg-gray-50">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Office Supplies</h4>
                      <p className="text-sm text-gray-600">December 10, 2024 • Office Equipment</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">₹1,200</p>
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                        Reimbursed
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">
                    Purchased ergonomic mouse and keyboard for workstation setup.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "travel" && (
            <div className="space-y-6">
              {/* Travel Summary */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-blue-100 text-sm">Upcoming Trips</p>
                      <p className="text-2xl font-bold">2</p>
                    </div>
                    <div className="w-12 h-12 bg-blue-400 rounded-full flex items-center justify-center">
                      <span className="text-blue-800 text-xl">✈️</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-green-100 text-sm">Travel Budget Used</p>
                      <p className="text-2xl font-bold">65%</p>
                    </div>
                    <div className="w-12 h-12 bg-green-400 rounded-full flex items-center justify-center">
                      <span className="text-green-800 text-xl">💰</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Travel Requests */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Travel Requests</h3>

                <div className="border rounded-lg p-4 bg-blue-50 border-blue-200">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Mumbai Office Visit</h4>
                      <p className="text-sm text-gray-600">January 15-17, 2025 • Business Trip</p>
                    </div>
                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                      Approved
                    </span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                    <div>
                      <p className="text-gray-500">Flight</p>
                      <p className="font-medium">₹8,500</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Hotel</p>
                      <p className="font-medium">₹6,000</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Meals</p>
                      <p className="font-medium">₹3,000</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Total</p>
                      <p className="font-medium">₹17,500</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700">
                    Quarterly business review meeting with Mumbai team and client presentations.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-yellow-50 border-yellow-200">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Bangalore Conference</h4>
                      <p className="text-sm text-gray-600">February 20-22, 2025 • Conference</p>
                    </div>
                    <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">
                      Pending
                    </span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                    <div>
                      <p className="text-gray-500">Flight</p>
                      <p className="font-medium">₹7,200</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Hotel</p>
                      <p className="font-medium">₹8,000</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Registration</p>
                      <p className="font-medium">₹15,000</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Total</p>
                      <p className="font-medium">₹30,200</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700">
                    Attending TechConf 2025 for latest industry trends and networking opportunities.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "reimbursements" && (
            <div className="space-y-6">
              {/* Reimbursement Status */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white border rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-gray-900">Submitted</h3>
                    <span className="text-2xl">📤</span>
                  </div>
                  <p className="text-2xl font-bold text-blue-600">₹5,650</p>
                  <p className="text-sm text-gray-600">3 claims pending</p>
                </div>

                <div className="bg-white border rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-gray-900">Processing</h3>
                    <span className="text-2xl">⏳</span>
                  </div>
                  <p className="text-2xl font-bold text-yellow-600">₹3,200</p>
                  <p className="text-sm text-gray-600">Under review</p>
                </div>

                <div className="bg-white border rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-gray-900">Completed</h3>
                    <span className="text-2xl">✅</span>
                  </div>
                  <p className="text-2xl font-bold text-green-600">₹12,450</p>
                  <p className="text-sm text-gray-600">This month</p>
                </div>
              </div>

              {/* Reimbursement History */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Reimbursement History</h3>

                <div className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">December Expenses</h4>
                      <p className="text-sm text-gray-600">Processed on Dec 20, 2024</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-green-600">₹4,250</p>
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                        Paid
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700">
                    Reimbursement for travel expenses and client meeting costs.
                  </p>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">November Expenses</h4>
                      <p className="text-sm text-gray-600">Processed on Nov 25, 2024</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-green-600">₹8,200</p>
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                        Paid
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700">
                    Monthly reimbursement including office supplies and transportation.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
