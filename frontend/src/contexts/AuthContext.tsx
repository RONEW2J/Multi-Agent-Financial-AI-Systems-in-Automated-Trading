import React, { createContext, useState, useContext, useEffect } from 'react';
import { userApi } from '../services/api';

interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (username: string, email: string, password: string, initialCapital: number) => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load user on mount if token exists
    if (token) {
      loadUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const loadUser = async () => {
    try {
      const userData = await userApi.getMe();
      setUser(userData);
    } catch (error) {
      console.error('Failed to load user:', error);
      // If token is invalid, clear it
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    const response = await userApi.login({ username, password });
    const newToken = response.access_token;
    
    localStorage.setItem('token', newToken);
    setToken(newToken);
    
    // User data is already in response
    setUser(response.user);
  };

  const register = async (username: string, email: string, password: string, initialCapital: number) => {
    // Register returns UserInfo, not LoginResponse
    await userApi.register({
      username,
      email,
      password,
      initial_capital: initialCapital,
    });
    
    // Auto-login after registration
    const loginResponse = await userApi.login({ username, password });
    const newToken = loginResponse.access_token;
    
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(loginResponse.user);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        register,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
