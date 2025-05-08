import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 60000, // 增加超时时间到60秒
  headers: {
    'Content-Type': 'application/json',
  },
});

// 设置axios默认行为
axios.defaults.withCredentials = true; // 确保跨域请求发送认证信息

// 请求拦截器 - 添加认证token
api.interceptors.request.use(
  (config) => {
    console.log(`请求拦截: ${config.method?.toUpperCase()} ${config.url}`);
    
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log(`添加认证头: Bearer ${token.substring(0, 15)}...`);
    } else {
      console.log('未找到认证令牌，发送未认证请求');
    }
    
    // 打印完整请求配置（敏感信息除外）
    console.log('请求配置:', {
      url: config.url,
      method: config.method,
      headers: {
        ...config.headers,
        Authorization: config.headers.Authorization 
          ? `Bearer ${config.headers.Authorization.toString().split(' ')[1]?.substring(0, 10)}...` 
          : undefined
      },
      data: config.data ? typeof config.data : null,
      baseURL: config.baseURL
    });
    
    return config;
  },
  (error) => {
    console.error('请求拦截器错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => {
    console.log('请求成功，状态码:', response.status);
    console.log('响应数据片段:', JSON.stringify(response.data).substring(0, 100) + '...');
    return response;
  },
  (error) => {
    console.error('响应拦截器捕获错误:', error);
    
    if (error.response) {
      console.error('错误状态码:', error.response.status);
      console.error('错误响应数据:', error.response.data);
      console.error('错误响应头:', error.response.headers);
      
      // 根据错误状态码处理不同情况
      switch (error.response.status) {
        case 401:
          // 认证失败 - 清除本地存储的token
          console.error('认证失败，清除token');
          localStorage.removeItem('token');
          // 重定向到登录页
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          break;
        case 403:
          console.error('权限不足');
          break;
        case 404:
          console.error('请求的资源不存在');
          break;
        case 422:
          console.error('请求参数验证失败', error.response.data);
          break;
        case 500:
          console.error('服务器内部错误');
          break;
        default:
          console.error(`未处理的错误状态码: ${error.response.status}`);
      }
    } else if (error.request) {
      console.error('请求已发送但未收到响应:', error.request);
    } else {
      console.error('请求设置错误:', error.message);
    }
    
    return Promise.reject(error);
  }
);

// 验证令牌是否存在，如不存在则返回错误
const ensureToken = () => {
  const token = localStorage.getItem('token');
  if (!token) {
    throw new Error('未授权，请先登录');
  }
  return token;
};

// 认证相关API
export const authAPI = {
  // 用户注册
  register: async (username: string, email: string, password: string) => {
    try {
      console.log(`开始注册用户: ${username}, ${email}`);
      const response = await api.post('/auth/register', {
        username,
        email,
        password,
      });
      console.log('注册成功');
      
      // 保存token到localStorage
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
      }
      
      return response.data;
    } catch (error: any) {
      console.error('注册失败:', error);
      throw error;
    }
  },

  // 用户登录
  login: async (username: string, password: string) => {
    console.log(`尝试登录: ${username}`);
    
    try {
      // 表单编码方式 - 使用URLSearchParams格式化数据
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      console.log('请求URL:', `${api.defaults.baseURL}/auth/login`);
      console.log('表单数据格式:', formData.toString());
      
      const response = await api.post('/auth/login', formData.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      
      console.log('登录响应状态:', response.status, response.statusText);
      console.log('登录响应数据:', JSON.stringify(response.data).substring(0, 100) + '...');
      
      // 保存token到localStorage
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        console.log('Token已保存到localStorage');
      } else {
        console.error('登录响应中未包含access_token');
      }
      
      return response.data;
    } catch (error: any) {
      console.error('登录请求出错:', error);
      if (error.response) {
        console.error('登录错误状态码:', error.response.status);
        console.error('登录错误响应:', error.response.data);
      }
      throw error;
    }
  },

  // 获取当前用户信息
  getCurrentUser: async () => {
    try {
      ensureToken();
      console.log('获取当前用户信息');
      const response = await api.get('/auth/me');
      console.log('获取到用户信息:', response.data);
      return response.data;
    } catch (error) {
      console.error('获取用户信息失败:', error);
      throw error;
    }
  },
  
  // 退出登录
  logout: () => {
    console.log('用户退出登录，清除token');
    localStorage.removeItem('token');
    window.location.href = '/login';
  }
};

// 数据查询相关API
export const dataAPI = {
  // 自然语言转SQL
  nl2sql: async (query: string) => {
    try {
      const token = ensureToken();
      console.log(`开始nl2sql请求: "${query}"`);
      
      const response = await api.post('/data/nl2sql', { query }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      console.log('nl2sql响应:', response.data);
      return response.data;
    } catch (error) {
      console.error('nl2sql请求失败:', error);
      throw error;
    }
  },

  // 执行自然语言查询
  nlQuery: async (query: string, needVisualization = true, includeSuggestions = true) => {
    try {
      const token = ensureToken();
      console.log(`开始发送nlQuery请求: "${query}"`);
      console.log(`请求参数: need_visualization=${needVisualization}, include_suggestions=${includeSuggestions}`);
      
      const requestData = {
        query,
        need_visualization: needVisualization,
        include_suggestions: includeSuggestions,
      };
      
      console.log('请求数据:', JSON.stringify(requestData));
      console.log('请求URL:', `${api.defaults.baseURL}/data/nl2sql-query`);
      console.log('使用Token:', token ? `${token.substring(0, 15)}...` : '无Token');
      
      // 请求重试逻辑
      let retryCount = 0;
      const maxRetries = 2;
      
      while (retryCount <= maxRetries) {
        try {
          // 确保请求头中包含认证信息和正确的内容类型
          const response = await api.post('/data/nl2sql-query', requestData, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            timeout: 60000, // 增加超时时间到60秒，因为NL2SQL可能需要较长时间
          });
          
          console.log('nlQuery API响应状态:', response.status, response.statusText);
          console.log('nlQuery响应数据:', JSON.stringify(response.data).substring(0, 200) + '...');
          
          return response.data;
        } catch (err: any) {
          if (err.response && err.response.status === 401) {
            // 认证错误不重试
            throw err;
          }
          
          if (retryCount < maxRetries) {
            retryCount++;
            console.log(`尝试第${retryCount}次重试nlQuery请求...`);
            await new Promise(resolve => setTimeout(resolve, 1000 * retryCount)); // 等待时间随重试次数增加
          } else {
            console.error(`已达最大重试次数(${maxRetries})，nlQuery请求失败`);
            throw err;
          }
        }
      }
      
      throw new Error('超过最大重试次数');
    } catch (error: any) {
      console.error('nlQuery请求出错:', error);
      if (error.response) {
        // 服务器响应了请求，但状态码不在2xx范围内
        console.error('错误状态码:', error.response.status);
        console.error('错误响应:', error.response.data);
        console.error('错误头信息:', error.response.headers);
      } else if (error.request) {
        // 请求已发送但没有收到响应
        console.error('未收到响应:', error.request);
      } else {
        // 请求设置过程中出现错误
        console.error('请求错误:', error.message);
      }
      throw error;
    }
  },

  // 直接执行SQL查询
  executeQuery: async (query: string, maxResults = 100) => {
    try {
      const token = ensureToken();
      console.log(`执行SQL查询: "${query}"`);
      
      const response = await api.post('/data/query', {
        query,
        max_results: maxResults,
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      console.log('SQL查询响应:', response.data);
      return response.data;
    } catch (error) {
      console.error('执行SQL查询失败:', error);
      throw error;
    }
  },

  // 获取数据库表列表
  getTables: async () => {
    try {
      const token = ensureToken();
      console.log('获取数据库表列表');
      
      const response = await api.get('/data/tables', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      console.log('数据库表列表响应:', response.data);
      return response.data;
    } catch (error) {
      console.error('获取数据库表列表失败:', error);
      throw error;
    }
  },

  // 获取查询历史
  getQueryHistory: async (limit = 10, offset = 0, queryType?: string) => {
    try {
      const token = ensureToken();
      const params: any = { limit, offset };
      if (queryType) {
        params.query_type = queryType;
      }
      
      console.log(`获取查询历史, 参数: limit=${limit}, offset=${offset}, queryType=${queryType || '全部'}`);
      
      const response = await api.get('/data/history', { 
        params,
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      console.log('查询历史响应:', response.data);
      return response.data;
    } catch (error) {
      console.error('获取查询历史失败:', error);
      throw error;
    }
  },

  // 生成查询结果解释
  generateExplanation: async (query: string, sql: string, results: any[]) => {
    try {
      const token = ensureToken();
      console.log(`生成查询结果解释: "${query.substring(0, 30)}..."`);
      
      const response = await api.post('/data/explain-results', {
        query,
        sql,
        results
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      console.log('解释生成响应:', response.data);
      return response.data;
    } catch (error) {
      console.error('生成解释失败:', error);
      throw error;
    }
  },

  // 清除查询缓存
  clearCache: async () => {
    try {
      const token = ensureToken();
      console.log('清除查询缓存');
      
      const response = await api.delete('/data/cache', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      console.log('清除缓存响应:', response.data);
      return response.data;
    } catch (error) {
      console.error('清除缓存失败:', error);
      throw error;
    }
  },
};

export default api; 