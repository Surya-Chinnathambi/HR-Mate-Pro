import { useState } from "react";

interface EngageModuleProps {
  employee: any;
  activeTab?: "posts" | "polls" | "praise";
}

export function EngageModule({ employee, activeTab = "posts" }: EngageModuleProps) {
  const [currentTab, setCurrentTab] = useState(activeTab);

  const renderTabContent = () => {
    switch (currentTab) {
      case "posts":
        return (
          <div className="space-y-6">
            {/* Sample Posts */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">HR</span>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">HR Team</h4>
                  <p className="text-sm text-gray-600">2 hours ago</p>
                </div>
              </div>
              <p className="text-gray-700 mb-3">
                🎉 Exciting news! We're launching a new employee wellness program starting next month.
                Stay tuned for more details about fitness challenges, mental health resources, and team activities!
              </p>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <button className="hover:text-blue-600">👍 12 Likes</button>
                <button className="hover:text-blue-600">💬 3 Comments</button>
                <button className="hover:text-blue-600">🔄 Share</button>
              </div>
            </div>

            <div className="border rounded-lg p-4">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">JS</span>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">John Smith</h4>
                  <p className="text-sm text-gray-600">1 day ago</p>
                </div>
              </div>
              <p className="text-gray-700 mb-3">
                Just completed the React certification course! 🚀 Thanks to the company's learning budget.
                Excited to apply these new skills to our upcoming projects.
              </p>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <button className="hover:text-blue-600">👍 8 Likes</button>
                <button className="hover:text-blue-600">💬 5 Comments</button>
                <button className="hover:text-blue-600">🔄 Share</button>
              </div>
            </div>
          </div>
        );

      case "polls":
        return (
          <div className="space-y-6">
            {/* Sample Poll */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">HR</span>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">HR Team</h4>
                  <p className="text-sm text-gray-600">3 hours ago</p>
                </div>
              </div>
              <h3 className="font-medium text-gray-900 mb-3">
                What type of team building activity would you prefer for our next company event?
              </h3>
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between p-2 bg-blue-50 rounded border">
                  <span className="text-sm">🎳 Bowling</span>
                  <span className="text-sm text-gray-600">45% (18 votes)</span>
                </div>
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded border">
                  <span className="text-sm">🏞️ Outdoor Adventure</span>
                  <span className="text-sm text-gray-600">30% (12 votes)</span>
                </div>
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded border">
                  <span className="text-sm">🍕 Cooking Class</span>
                  <span className="text-sm text-gray-600">25% (10 votes)</span>
                </div>
              </div>
              <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm">
                Vote
              </button>
            </div>
          </div>
        );

      case "praise":
        return (
          <div className="space-y-6">
            {/* Sample Praise */}
            <div className="border rounded-lg p-4 bg-yellow-50 border-yellow-200">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">SJ</span>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">Sarah Johnson</h4>
                  <p className="text-sm text-gray-600">praised John Smith • 2 hours ago</p>
                </div>
              </div>
              <p className="text-gray-700 mb-3">
                👏 Huge shoutout to John for his amazing work on the new dashboard!
                His attention to detail and user-focused approach made all the difference.
                The client feedback has been overwhelmingly positive! 🌟
              </p>
              <div className="flex items-center space-x-2">
                <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">
                  Teamwork
                </span>
                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                  Innovation
                </span>
              </div>
            </div>

            <div className="border rounded-lg p-4 bg-green-50 border-green-200">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-teal-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">MD</span>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">Mike Davis</h4>
                  <p className="text-sm text-gray-600">praised Sarah Johnson • 1 day ago</p>
                </div>
              </div>
              <p className="text-gray-700 mb-3">
                🎯 Sarah's presentation to the stakeholders was absolutely brilliant!
                She clearly communicated complex technical concepts and secured buy-in for our new initiative.
                Outstanding work! 💪
              </p>
              <div className="flex items-center space-x-2">
                <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                  Leadership
                </span>
                <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded-full text-xs font-medium">
                  Communication
                </span>
              </div>
            </div>

            <div className="text-center py-8">
              <button className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white px-6 py-3 rounded-lg hover:from-yellow-600 hover:to-orange-600 transition-all duration-200 flex items-center space-x-2 mx-auto">
                <span>👏</span>
                <span>Give Praise</span>
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-900">Engage</h2>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
          + Create Post
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="flex border-b">
          <button
            onClick={() => setCurrentTab("posts")}
            className={`px-6 py-3 font-medium text-sm ${currentTab === "posts"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            📝 Posts
          </button>
          <button
            onClick={() => setCurrentTab("polls")}
            className={`px-6 py-3 font-medium text-sm ${currentTab === "polls"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            📊 Polls
          </button>
          <button
            onClick={() => setCurrentTab("praise")}
            className={`px-6 py-3 font-medium text-sm ${currentTab === "praise"
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            👏 Praise
          </button>
        </div>

        <div className="p-6">
          {renderTabContent()}

          {/* Empty State for all tabs */}
          <div className="text-center py-8 border-t mt-6">
            <div className="text-4xl mb-4">
              {currentTab === "posts" ? "📝" : currentTab === "polls" ? "📊" : "👏"}
            </div>
            <p className="text-gray-500">
              {currentTab === "posts" && "Share your thoughts and updates with the team"}
              {currentTab === "polls" && "Create polls to gather team feedback"}
              {currentTab === "praise" && "Recognize and appreciate your colleagues"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
