import { useState } from "react";

interface PerformanceModuleProps {
  employee: any;
  activeTab?: "goals" | "feedback" | "reviews";
}

export function PerformanceModule({ employee, activeTab = "goals" }: PerformanceModuleProps) {
  const [currentTab, setCurrentTab] = useState<"goals" | "feedback" | "reviews">(activeTab);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-900">Performance</h2>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
          + Add Goal
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="flex border-b">
          <button
            onClick={() => setCurrentTab("goals")}
            className={`px-6 py-3 font-medium text-sm ${currentTab === "goals"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            🎯 My Goals
          </button>
          <button
            onClick={() => setCurrentTab("feedback")}
            className={`px-6 py-3 font-medium text-sm ${currentTab === "feedback"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            💬 Feedback
          </button>
          <button
            onClick={() => setCurrentTab("reviews")}
            className={`px-6 py-3 font-medium text-sm ${currentTab === "reviews"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            ⭐ Reviews
          </button>
        </div>

        <div className="p-6">
          {currentTab === "goals" && (
            <div className="space-y-6">
              {/* Goals Progress Overview */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-xl p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-green-100 text-sm">Completed Goals</p>
                      <p className="text-2xl font-bold">3</p>
                    </div>
                    <div className="w-12 h-12 bg-green-400 rounded-full flex items-center justify-center">
                      <span className="text-green-800 text-xl">✅</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-blue-100 text-sm">In Progress</p>
                      <p className="text-2xl font-bold">2</p>
                    </div>
                    <div className="w-12 h-12 bg-blue-400 rounded-full flex items-center justify-center">
                      <span className="text-blue-800 text-xl">🔄</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-xl p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-orange-100 text-sm">Pending</p>
                      <p className="text-2xl font-bold">1</p>
                    </div>
                    <div className="w-12 h-12 bg-orange-400 rounded-full flex items-center justify-center">
                      <span className="text-orange-800 text-xl">⏳</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Sample Goals */}
              <div className="space-y-4">
                <div className="border rounded-lg p-4 bg-green-50 border-green-200">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Complete React Certification</h4>
                      <p className="text-sm text-gray-600">Q4 2024 • Professional Development</p>
                    </div>
                    <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                      Completed
                    </span>
                  </div>
                  <div className="w-full bg-green-200 rounded-full h-2 mb-2">
                    <div className="bg-green-600 h-2 rounded-full" style={{ width: '100%' }}></div>
                  </div>
                  <p className="text-sm text-gray-700">
                    Successfully completed the advanced React certification course and applied learnings to current projects.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-blue-50 border-blue-200">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Improve Team Collaboration</h4>
                      <p className="text-sm text-gray-600">Q4 2024 • Leadership</p>
                    </div>
                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                      In Progress
                    </span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2 mb-2">
                    <div className="bg-blue-600 h-2 rounded-full" style={{ width: '75%' }}></div>
                  </div>
                  <p className="text-sm text-gray-700">
                    Implementing weekly team sync meetings and cross-functional collaboration initiatives.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-orange-50 border-orange-200">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-medium text-gray-900">Launch New Product Feature</h4>
                      <p className="text-sm text-gray-600">Q1 2025 • Project Delivery</p>
                    </div>
                    <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded-full text-xs font-medium">
                      Pending
                    </span>
                  </div>
                  <div className="w-full bg-orange-200 rounded-full h-2 mb-2">
                    <div className="bg-orange-600 h-2 rounded-full" style={{ width: '25%' }}></div>
                  </div>
                  <p className="text-sm text-gray-700">
                    Lead the development and launch of the new analytics dashboard feature.
                  </p>
                </div>
              </div>
            </div>
          )}

          {currentTab === "feedback" && (
            <div className="space-y-6">
              {/* Feedback Summary */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div className="bg-white border rounded-lg p-6">
                  <h3 className="font-medium text-gray-900 mb-4">Recent Feedback</h3>
                  <div className="space-y-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-green-600">👍</span>
                      <span className="text-sm text-gray-700">Excellent problem-solving skills</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-blue-600">💡</span>
                      <span className="text-sm text-gray-700">Great innovative thinking</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-purple-600">🤝</span>
                      <span className="text-sm text-gray-700">Strong team collaboration</span>
                    </div>
                  </div>
                </div>

                <div className="bg-white border rounded-lg p-6">
                  <h3 className="font-medium text-gray-900 mb-4">Areas for Growth</h3>
                  <div className="space-y-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-yellow-600">📈</span>
                      <span className="text-sm text-gray-700">Public speaking confidence</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-orange-600">⏰</span>
                      <span className="text-sm text-gray-700">Time management optimization</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Feedback History */}
              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                      <span className="text-white text-sm font-medium">MG</span>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">Manager Feedback</h4>
                      <p className="text-sm text-gray-600">2 weeks ago</p>
                    </div>
                  </div>
                  <p className="text-gray-700 mb-2">
                    Outstanding work on the recent project delivery. Your technical expertise and attention to detail
                    ensured we met all client requirements ahead of schedule.
                  </p>
                  <div className="flex items-center space-x-2">
                    <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                      Technical Skills
                    </span>
                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                      Project Management
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {currentTab === "reviews" && (
            <div className="space-y-6">
              {/* Review Summary */}
              <div className="bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl p-6 text-white mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Overall Performance Rating</h3>
                    <div className="flex items-center space-x-2">
                      <div className="flex space-x-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <span key={star} className="text-yellow-300 text-xl">⭐</span>
                        ))}
                      </div>
                      <span className="text-xl font-bold">4.5/5</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-purple-100 text-sm">Last Review</p>
                    <p className="text-lg font-semibold">Q3 2024</p>
                  </div>
                </div>
              </div>

              {/* Review History */}
              <div className="space-y-4">
                <div className="border rounded-lg p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="font-medium text-gray-900">Q3 2024 Performance Review</h4>
                      <p className="text-sm text-gray-600">Reviewed by: Manager • September 2024</p>
                    </div>
                    <div className="flex items-center space-x-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <span key={star} className={`text-lg ${star <= 4 ? 'text-yellow-400' : 'text-gray-300'}`}>⭐</span>
                      ))}
                      <span className="ml-2 font-semibold">4.5</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                    <div>
                      <h5 className="font-medium text-gray-900 mb-2">Strengths</h5>
                      <ul className="text-sm text-gray-700 space-y-1">
                        <li>• Excellent technical problem-solving</li>
                        <li>• Strong team collaboration</li>
                        <li>• Consistent delivery quality</li>
                        <li>• Proactive communication</li>
                      </ul>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900 mb-2">Development Areas</h5>
                      <ul className="text-sm text-gray-700 space-y-1">
                        <li>• Leadership opportunities</li>
                        <li>• Cross-functional collaboration</li>
                        <li>• Strategic thinking</li>
                      </ul>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4">
                    <h5 className="font-medium text-gray-900 mb-2">Manager Comments</h5>
                    <p className="text-sm text-gray-700">
                      Exceptional performance this quarter. Consistently delivers high-quality work and has become
                      a reliable team member. Looking forward to seeing continued growth in leadership areas.
                    </p>
                  </div>
                </div>

                <div className="border rounded-lg p-6 bg-gray-50">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="font-medium text-gray-900">Q2 2024 Performance Review</h4>
                      <p className="text-sm text-gray-600">Reviewed by: Manager • June 2024</p>
                    </div>
                    <div className="flex items-center space-x-1">
                      {[1, 2, 3, 4].map((star) => (
                        <span key={star} className="text-lg text-yellow-400">⭐</span>
                      ))}
                      <span className="text-lg text-gray-300">⭐</span>
                      <span className="ml-2 font-semibold">4.0</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    Solid performance with notable improvements in project delivery and team communication.
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
