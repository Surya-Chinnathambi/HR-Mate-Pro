import { useState, useEffect } from 'react';
import { JWTAuthForm } from './components/JWTAuthForm';
import { EnhancedHRMSDashboard } from './components/EnhancedHRMSDashboard';
import apiClient from './api/client';

function App() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await apiClient.get('/auth/me');
        console.log('User loaded from /auth/me:', response.data);
        setUser(response.data);
      } catch (error) {
        console.error('Failed to fetch user:', error);
        localStorage.removeItem('access_token');
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  const handleSignIn = (token: string, userData: any) => {
    console.log('handleSignIn called with user:', userData);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <JWTAuthForm onAuthSuccess={handleSignIn} />;
  }

  return <EnhancedHRMSDashboard user={user} onLogout={handleLogout} />;
}
export default App;