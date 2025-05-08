import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, AuthResponse } from '../types';
import { authAPI } from '../services/api';

interface AuthContextProps {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, email: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextProps | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 初始化 - 检查登录状态
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const user = await authAPI.getCurrentUser();
        setUser(user);
        setIsAuthenticated(true);
      } catch (err) {
        console.error('认证检查失败:', err);
        localStorage.removeItem('token');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  // 登录
  const login = async (username: string, password: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const data = await authAPI.login(username, password);
      handleAuthSuccess(data);
      return true;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || '登录失败，请检查用户名和密码';
      setError(errorMessage);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // 注册
  const register = async (username: string, email: string, password: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const data = await authAPI.register(username, email, password);
      handleAuthSuccess(data);
      return true;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || '注册失败，请稍后重试';
      setError(errorMessage);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // 登出
  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setIsAuthenticated(false);
  };

  // 处理认证成功响应
  const handleAuthSuccess = (data: AuthResponse) => {
    localStorage.setItem('token', data.access_token);
    
    if (data.user) {
      setUser(data.user);
    }
    
    setIsAuthenticated(true);
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        loading,
        error,
        login,
        register,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// 自定义Hook用于获取认证上下文
export const useAuth = (): AuthContextProps => {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth必须在AuthProvider内部使用');
  }
  
  return context;
}; 