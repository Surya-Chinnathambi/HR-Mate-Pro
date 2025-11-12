import { useState, useEffect } from "react";
import apiClient from "../api/client";

export function CompanyPoliciesModule() {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedPolicy, setSelectedPolicy] = useState<any>(null);

  const [policies, setPolicies] = useState<any[] | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await apiClient.get('/policies');
        if (!mounted) return;
        setPolicies(res.data || []);
      } catch (e) {
        if (!mounted) return;
        setPolicies([]);
      }
    })();
    return () => { mounted = false; };
  }, []);

  const displayPolicies = searchTerm
    ? policies?.filter((policy: any) =>
      policy.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      policy.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
      policy.category.toLowerCase().includes(searchTerm.toLowerCase())
    )
    : policies;
  const filteredPolicies = selectedCategory === "all"
    ? displayPolicies
    : displayPolicies?.filter((policy: any) => policy.category === selectedCategory);

  const categories = policies ? [...new Set(policies.map(p => p.category))] : [];

  const formatPolicyContent = (content: string) => {
    return content.split('\n').map((line, index) => {
      if (line.startsWith('**') && line.endsWith('**')) {
        return (
          <h4 key={index} className="font-bold text-lg text-gray-900 mt-4 mb-2">
            {line.replace(/\*\*/g, '')}
          </h4>
        );
      }
      if (line.startsWith('- ')) {
        return (
          <li key={index} className="ml-4 text-gray-700 mb-1">
            {line.substring(2)}
          </li>
        );
      }
      if (line.match(/^\d+\./)) {
        return (
          <li key={index} className="ml-4 text-gray-700 mb-1 list-decimal">
            {line.substring(line.indexOf('.') + 1).trim()}
          </li>
        );
      }
      if (line.trim() === '') {
        return <br key={index} />;
      }
      return (
        <p key={index} className="text-gray-700 mb-2 leading-relaxed">
          {line}
        </p>
      );
    });
  };

  return (
    <div className="space-y-6 font-['Nexa']">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-4xl font-bold gradient-text">Company Policies</h2>
          <p className="text-gray-600 mt-2">Stay informed about company guidelines and procedures</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-sm text-gray-600">Live Updates</span>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-lg border border-white/20 p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Search Policies
            </label>
            <input
              type="text"
              placeholder="Search by title, content, or category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white/80 backdrop-blur-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white/80 backdrop-blur-sm"
            >
              <option value="all">All Categories</option>
              {categories.map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Policy List */}
        <div className="lg:col-span-1">
          <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-lg border border-white/20">
            <div className="p-6 border-b border-gray-100">
              <h3 className="text-xl font-bold text-gray-900 flex items-center">
                <span className="mr-2">📋</span>
                Policy Directory
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                {filteredPolicies?.length || 0} policies found
              </p>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {filteredPolicies?.map((policy: any) => (
                <button
                  key={policy.id}
                  onClick={() => setSelectedPolicy(policy)}
                  className={`w-full text-left p-4 border-b border-gray-100 hover:bg-blue-50 transition-all duration-200 ${selectedPolicy?.id === policy.id ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                    }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900 mb-1">{policy.title}</h4>
                      <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${policy.category === 'Attendance' ? 'bg-green-100 text-green-800' :
                          policy.category === 'Leave Management' ? 'bg-blue-100 text-blue-800' :
                            policy.category === 'Ethics' ? 'bg-purple-100 text-purple-800' :
                              policy.category === 'Performance' ? 'bg-orange-100 text-orange-800' :
                                'bg-gray-100 text-gray-800'
                        }`}>
                        {policy.category}
                      </span>
                      <p className="text-xs text-gray-500 mt-2">
                        Updated: {new Date(policy.lastUpdated).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="ml-2">
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                        v{policy.version}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Policy Content */}
        <div className="lg:col-span-2">
          <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-lg border border-white/20">
            {selectedPolicy ? (
              <>
                <div className="p-6 border-b border-gray-100">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-2xl font-bold text-gray-900 mb-2">
                        {selectedPolicy.title}
                      </h3>
                      <div className="flex items-center space-x-4 text-sm text-gray-600">
                        <span className={`px-3 py-1 rounded-full font-medium ${selectedPolicy.category === 'Attendance' ? 'bg-green-100 text-green-800' :
                            selectedPolicy.category === 'Leave Management' ? 'bg-blue-100 text-blue-800' :
                              selectedPolicy.category === 'Ethics' ? 'bg-purple-100 text-purple-800' :
                                selectedPolicy.category === 'Performance' ? 'bg-orange-100 text-orange-800' :
                                  'bg-gray-100 text-gray-800'
                          }`}>
                          {selectedPolicy.category}
                        </span>
                        <span>Version {selectedPolicy.version}</span>
                        <span>Updated: {new Date(selectedPolicy.lastUpdated).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <button className="bg-blue-600 text-white px-4 py-2 rounded-xl hover:bg-blue-700 transition-colors text-sm font-medium">
                      Download PDF
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <div className="prose max-w-none">
                    {formatPolicyContent(selectedPolicy.content)}
                  </div>

                  {/* Policy Actions */}
                  <div className="mt-8 pt-6 border-t border-gray-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <button className="bg-green-600 text-white px-4 py-2 rounded-xl hover:bg-green-700 transition-colors text-sm font-medium flex items-center space-x-2">
                          <span>✓</span>
                          <span>Acknowledge</span>
                        </button>
                        <button className="bg-gray-600 text-white px-4 py-2 rounded-xl hover:bg-gray-700 transition-colors text-sm font-medium flex items-center space-x-2">
                          <span>📧</span>
                          <span>Ask Question</span>
                        </button>
                      </div>
                      <div className="text-sm text-gray-500">
                        Policy ID: {selectedPolicy.id}
                      </div>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-12 text-center">
                <div className="text-6xl mb-4">📋</div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Select a Policy</h3>
                <p className="text-gray-600">
                  Choose a policy from the directory to view its details and content.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Access Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-2xl p-6 text-white card-hover">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm">Attendance</p>
              <p className="text-2xl font-bold">95%</p>
              <p className="text-green-100 text-xs">Compliance Rate</p>
            </div>
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <span className="text-2xl">⏰</span>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl p-6 text-white card-hover">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Leave Policies</p>
              <p className="text-2xl font-bold">12</p>
              <p className="text-blue-100 text-xs">Days Remaining</p>
            </div>
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <span className="text-2xl">🏖️</span>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl p-6 text-white card-hover">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Code of Conduct</p>
              <p className="text-2xl font-bold">100%</p>
              <p className="text-purple-100 text-xs">Acknowledged</p>
            </div>
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <span className="text-2xl">⚖️</span>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-r from-orange-500 to-red-500 rounded-2xl p-6 text-white card-hover">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-orange-100 text-sm">Performance</p>
              <p className="text-2xl font-bold">4.8</p>
              <p className="text-orange-100 text-xs">Rating</p>
            </div>
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <span className="text-2xl">⭐</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
