import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { authApi } from '@/lib/api';

const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const token = searchParams.get('token');

  useEffect(() => {
    const handleAuth = async () => {
      if (token) {
        try {
          // Verify token and get user info
          const user = await authApi.getMe(token);
          if (user) {
            // Store token
            localStorage.setItem('auth_token', token);
            // Reload the page to update auth context
            window.location.href = '/';
          }
        } catch (err) {
          setError('Failed to authenticate. Please try again.');
          setTimeout(() => navigate('/login'), 3000);
        }
      } else {
        // No token, redirect to login
        navigate('/login');
      }
    };

    handleAuth();
  }, [token, navigate]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-4 text-red-600">{error}</h2>
          <p className="text-gray-600 dark:text-gray-400">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white mx-auto mb-4"></div>
        <h2 className="text-2xl font-semibold mb-4">Completing sign in...</h2>
        <p className="text-gray-600 dark:text-gray-400">Please wait while we redirect you.</p>
      </div>
    </div>
  );
};

export default AuthCallback;

