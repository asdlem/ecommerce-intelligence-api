// 用户相关类型
export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

// 可视化相关类型
export interface Visualization {
  chart_type: string;
  x_field: string;
  y_field: string;
  series_field?: string;
  config: any;
}

// 查询相关类型
export interface QueryResult {
  success: boolean;
  data: {
    query: string;
    sql: string;
    results: any[];
    row_count: number;
    explanation?: string;
    visualization?: Visualization;
    suggestions?: string[];
  };
  total: number;
}

// 历史记录相关类型
export interface HistoryRecord {
  id: number;
  query: string;
  query_type: string;
  timestamp: string;
  status: string;
  model?: string;
  processing_time?: number;
}

export interface HistoryResponse {
  history: HistoryRecord[];
}

export interface CacheResponse {
  success: boolean;
  message: string;
}

// UI状态相关类型
export interface FormErrors {
  username?: string;
  email?: string;
  password?: string;
  query?: string;
}

export interface AppState {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
} 