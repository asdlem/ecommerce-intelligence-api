import React, { useState, useRef, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  CircularProgress,
  Alert,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider,
  Chip,
  Card,
  CardContent,
  CardActions,
  Collapse,
  Tabs,
  Tab,
  List,
  ListItem,
  Avatar,
  Grid,
} from '@mui/material';
import {
  Search as SearchIcon,
  Mic as MicIcon,
  ContentCopy as ContentCopyIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Code as CodeIcon,
  QueryStats as QueryStatsIcon,
  BarChart as BarChartIcon,
  Lightbulb as LightbulbIcon,
  Send as SendIcon,
  QuestionAnswer as QuestionAnswerIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  ErrorOutline as ErrorIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import Navbar from '../components/Navbar';
import { dataAPI } from '../services/api';
import { QueryResult } from '../types';
import { useAuth } from '../utils/auth-context';

// 消息类型定义
interface Message {
  id: string;
  content: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  sql?: string;
  isExecuting?: boolean;
  results?: any[];
  error?: string;
  suggestions?: string[];
  explanation?: string; // 添加字段用于存储Markdown格式的解释内容
  isGeneratingExplanation?: boolean; // 标记是否正在生成解释
  canGenerateExplanation?: boolean; // 标记是否可以生成解释
}

const QueryPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sqlGenerated, setSqlGenerated] = useState<string | null>(null);
  const [showSql, setShowSql] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      content: '你好！我是电商数据助手，请用自然语言向我提问，例如："销量最高的3个商品是什么？"',
      sender: 'bot',
      timestamp: new Date(),
    }
  ]);
  
  const messagesEndRef = useRef<null | HTMLDivElement>(null);
  
  // 检查用户认证状态
  useEffect(() => {
    if (!isAuthenticated) {
      setError('您需要登录后才能使用查询功能');
    } else {
      setError(null);
    }
  }, [isAuthenticated]);
  
  // 自动滚动到最新消息
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 处理SQL复制
  const handleCopySQL = (sql: string) => {
    navigator.clipboard.writeText(sql);
  };
  
  // 处理建议点击
  const handleSuggestionClick = (suggestion: string) => {
    if (loading) return;
    handleFullQuery(suggestion);
  };

  // 生成查询结果解释
  const handleGenerateExplanation = async (messageId: string, userQuery: string, sql: string, results: any[]) => {
    if (loading) return;
    
    // 标记消息正在生成解释
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? {
        ...msg,
        isGeneratingExplanation: true,
        explanation: '', // 初始化为空字符串，用于流式更新
        canGenerateExplanation: false // 防止重复点击
      } : msg
    ));
    
    try {
      // 调用API生成解释 - 使用流式方式
      await dataAPI.generateExplanation(
        userQuery, 
        sql, 
        results,
        {
          // 收到每个文本块时更新UI
          onToken: (token: string) => {
            setMessages(prev => prev.map(msg => 
              msg.id === messageId ? {
                ...msg,
                explanation: (msg.explanation || '') + token
              } : msg
            ));
          },
          // 完成时更新状态
          onComplete: (fullText: string) => {
            setMessages(prev => prev.map(msg => 
              msg.id === messageId ? {
                ...msg,
                explanation: fullText,
                isGeneratingExplanation: false
              } : msg
            ));
          },
          // 错误处理
          onError: (error: string) => {
            setMessages(prev => prev.map(msg => 
              msg.id === messageId ? {
                ...msg,
                isGeneratingExplanation: false,
                canGenerateExplanation: true, // 允许重试
                error: error || '生成解释失败，请稍后重试'
              } : msg
            ));
          }
        }
      );
    } catch (err: any) {
      console.error('生成解释出错:', err);
      
      // 更新消息状态，显示错误
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? {
          ...msg,
          isGeneratingExplanation: false,
          canGenerateExplanation: true, // 允许重试
          error: err.response?.data?.detail || err.message || '生成解释失败，请稍后重试'
        } : msg
      ));
    }
  };
  
  // 执行生成的SQL
  const handleExecuteQuery = async (sqlToExecute: string) => {
    if (!sqlToExecute || loading) return;
    
    const messageId = Date.now().toString();
    setLoading(true);
    
    // 添加正在执行的消息
    setMessages(prev => [...prev, {
      id: messageId,
      content: '正在执行查询...',
      sender: 'bot',
      timestamp: new Date(),
      isExecuting: true
    }]);
    
    try {
      // 执行查询并获取结果
      const data = await dataAPI.executeQuery(sqlToExecute);
      
      if (data.success) {
        // 更新执行消息为结果
        setMessages(prev => prev.map(msg => 
          msg.id === messageId ? {
            ...msg,
            content: '查询执行完成，以下是结果：',
            isExecuting: false,
            results: data.data
          } : msg
        ));
      } else {
        throw new Error(data.message || '查询执行失败');
      }
    } catch (err: any) {
      console.error('执行查询出错:', err);
      
      // 更新为错误消息
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? {
          ...msg,
          content: '查询执行失败。',
          isExecuting: false,
          error: err.response?.data?.detail || err.message || '查询失败，请稍后重试'
        } : msg
      ));
    } finally {
      setLoading(false);
    }
  };
  
  // 执行自然语言查询（一步完成）
  const handleFullQuery = async (userQuery: string) => {
    if (!userQuery.trim() || loading) return;
    
    if (!isAuthenticated) {
      setError('请先登录后再进行查询');
      return;
    }
    
    setLoading(true);
    
    // 添加用户消息
    const userMessageId = Date.now().toString();
    setMessages(prev => [...prev, {
      id: userMessageId,
      content: userQuery,
      sender: 'user',
      timestamp: new Date()
    }]);
    
    // 添加系统思考消息
    const processingMessageId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, {
      id: processingMessageId,
      content: '正在分析您的问题...',
      sender: 'bot',
      timestamp: new Date(),
      isExecuting: true
    }]);
    
    try {
      // 执行完整的自然语言查询，但不包括解释生成
      const data = await dataAPI.nlQuery(userQuery, true, true);
      
      if (data.success) {
        // 更新系统消息为结果，但不包含解释
        setMessages(prev => prev.map(msg => 
          msg.id === processingMessageId ? {
            ...msg,
            content: '查询结果：',
            isExecuting: false,
            sql: data.data.sql,
            results: data.data.results,
            suggestions: data.data.suggestions,
            canGenerateExplanation: true // 标记可以生成解释
          } : msg
        ));
      } else {
        throw new Error(data.message || '查询执行失败');
      }
    } catch (err: any) {
      console.error('查询出错:', err);
      
      // 详细记录错误信息
      const errorMessage = err.response?.data?.detail || 
                         err.response?.data?.message || 
                         err.message || 
                         '查询失败，请稍后重试';
      
      console.error('错误详情:', errorMessage);
      
      // 更新为错误消息
      setMessages(prev => prev.map(msg => 
        msg.id === processingMessageId ? {
          ...msg,
          content: '抱歉，处理您的问题时出错了。',
          isExecuting: false,
          error: errorMessage
        } : msg
      ));
    } finally {
      setLoading(false);
      setQuery(''); // 清空输入框
    }
  };

  // 生成SQL但不执行
  const handleGenerateSql = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim() || loading) {
      setError('请输入查询语句');
      return;
    }
    
    if (!isAuthenticated) {
      setError('请先登录后再进行查询');
      return;
    }

    setLoading(true);
    setError(null);
    setSqlGenerated(null);
    
    // 添加用户消息
    const userMessageId = Date.now().toString();
    setMessages(prev => [...prev, {
      id: userMessageId,
      content: query,
      sender: 'user',
      timestamp: new Date()
    }]);

    try {
      // 首先只生成SQL
      const data = await dataAPI.nl2sql(query);
      if (data.success && data.data.sql) {
        setSqlGenerated(data.data.sql);
        
        // 添加系统响应
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          content: '我已根据您的问题生成SQL查询语句。以下是SQL查询结果。',
          sender: 'bot',
          timestamp: new Date(),
          sql: data.data.sql,
          suggestions: data.data.suggestions || []
        }]);
      } else {
        throw new Error(data.message || '无法生成SQL查询');
      }
    } catch (err: any) {
      console.error('生成SQL出错:', err);
      setError(err.response?.data?.detail || err.message || '生成SQL失败，请稍后重试');
      
      // 添加错误消息
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        content: '抱歉，我在尝试理解您的问题时遇到了困难。',
        sender: 'bot',
        timestamp: new Date(),
        error: err.response?.data?.detail || err.message || '生成SQL失败，请稍后重试'
      }]);
    } finally {
      setLoading(false);
      setQuery(''); // 清空输入框
    }
  };

  // 创建自定义样式的Markdown组件
  const MarkdownContent = ({ content }: { content: string }) => {
    if (!content) return null;
    
    return (
      <Box 
        sx={{ 
          mt: 2, 
          p: 2, 
          bgcolor: '#f8f9fa', 
          borderRadius: 1,
          borderLeft: '4px solid #4285F4',
          '& h3': { 
            color: '#4285F4', 
            fontSize: '1.1rem',
            fontWeight: 'bold',
            mt: 2,
            mb: 1
          },
          '& h4': { 
            color: '#5f6368', 
            fontSize: '1rem',
            fontWeight: 'bold',
            mt: 1.5,
            mb: 0.5
          },
          '& p': { 
            mb: 1 
          },
          '& ul, & ol': { 
            pl: 3,
            mb: 1
          },
          '& li': {
            mb: 0.5
          },
          '& strong': {
            color: '#34A853'
          }
        }}
      >
        <ReactMarkdown>
          {content}
        </ReactMarkdown>
      </Box>
    );
  };

  return (
    <>
      <Navbar />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
        {/* 顶部标题 */}
        <Typography
          variant="h4"
          component="h1"
          sx={{
            mb: 3,
            color: '#4285F4',
            fontWeight: 'bold',
            fontFamily: '"Product Sans", Arial, sans-serif',
            letterSpacing: '-1px',
            textAlign: 'center',
          }}
        >
          电商数据智能查询
        </Typography>

        {/* 错误提示 */}
        {error && (
          <Alert 
            severity="error" 
            sx={{ mt: 2, mb: 2 }}
            action={
              !isAuthenticated && (
                <Button color="inherit" size="small" href="/login">
                  去登录
                </Button>
              )
            }
          >
            {error}
          </Alert>
        )}
        
        {/* 对话历史区域 */}
        <Paper 
          elevation={2}
          sx={{ 
            p: 2, 
            mb: 2, 
            minHeight: '60vh',
            maxHeight: '60vh',
            overflowY: 'auto',
            borderRadius: 2,
            bgcolor: '#f8f9fa'
          }}
        >
          <List>
            {messages.map((message) => (
              <ListItem 
                key={message.id}
                alignItems="flex-start"
                sx={{ 
                  mb: 2,
                  flexDirection: message.sender === 'user' ? 'row-reverse' : 'row',
                }}
              >
                <Avatar 
                  sx={{ 
                    bgcolor: message.sender === 'user' ? '#4285F4' : '#34A853',
                    mr: message.sender === 'user' ? 0 : 2,
                    ml: message.sender === 'user' ? 2 : 0,
                  }}
                >
                  {message.sender === 'user' ? <PersonIcon /> : <BotIcon />}
                </Avatar>
                
                <Box 
                  sx={{ 
                    maxWidth: '85%',
                    bgcolor: message.sender === 'user' ? '#E3F2FD' : 'white',
                    borderRadius: 2,
                    p: 2,
                    boxShadow: 1,
                  }}
                >
                  <Typography variant="body1" gutterBottom>
                    {message.content}
                  </Typography>
                  
                  {/* 生成解释按钮 */}
                  {message.canGenerateExplanation && !message.explanation && !message.isGeneratingExplanation && (
                    <Button
                      variant="outlined"
                      color="primary"
                      size="small"
                      onClick={() => handleGenerateExplanation(message.id, (
                        // 查找对应的用户消息
                        messages.find(m => 
                          m.sender === 'user' && 
                          new Date(m.timestamp).getTime() < new Date(message.timestamp).getTime()
                        )?.content || ''),
                        message.sql || '',
                        message.results || []
                      )}
                      sx={{ mt: 1, mb: 2 }}
                      startIcon={<LightbulbIcon />}
                    >
                      生成解释
                    </Button>
                  )}
                  
                  {/* 正在生成解释提示 */}
                  {message.isGeneratingExplanation && (
                    <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, mb: 2 }}>
                      <CircularProgress size={16} sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        正在生成解释...
                      </Typography>
                    </Box>
                  )}
                  
                  {/* Markdown格式的解释内容 */}
                  {message.explanation && (
                    <MarkdownContent content={message.explanation} />
                  )}
                  
                  {/* 错误信息 */}
                  {message.error && (
                    <Alert 
                      severity="error" 
                      sx={{ mt: 1, mb: 1 }}
                      icon={<ErrorIcon />}
                    >
                      <Typography variant="body2">{message.error}</Typography>
                      {message.error === '未授权，请先登录' && (
                        <Button size="small" color="error" href="/login" sx={{ mt: 1 }}>
                          前往登录
                        </Button>
                      )}
                    </Alert>
                  )}
                  
                  {/* SQL代码 */}
                  {message.sql && (
                    <Paper 
                      sx={{ 
                        p: 2, 
                        mt: 2, 
                        bgcolor: '#f5f5f5', 
                        position: 'relative',
                        fontFamily: 'monospace',
                        fontSize: '0.9rem',
                        maxHeight: '200px',
                        overflowY: 'auto',
                      }}
                    >
                      <Box sx={{ position: 'absolute', top: 5, right: 5 }}>
                        <IconButton size="small" onClick={() => handleCopySQL(message.sql || '')}>
                          <ContentCopyIcon fontSize="small" />
                        </IconButton>
                      </Box>
                      <pre style={{ margin: 0, overflow: 'auto' }}>{message.sql}</pre>
                    </Paper>
                  )}
                  
                  {/* 查询结果 */}
                  {message.results && message.results.length > 0 && (
                    <TableContainer 
                      component={Paper} 
                      sx={{ 
                        mt: 2, 
                        maxHeight: '300px',
                        overflowY: 'auto',
                      }}
                    >
                      <Table size="small">
                        <TableHead sx={{ bgcolor: '#f5f5f5' }}>
                          <TableRow>
                            {Object.keys(message.results[0]).map((key) => (
                              <TableCell key={key}>
                                <Typography variant="body2" fontWeight="bold">
                                  {key}
                                </Typography>
                              </TableCell>
                            ))}
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {message.results.map((row, idx) => (
                            <TableRow key={idx}>
                              {Object.values(row).map((value, i) => (
                                <TableCell key={i}>{String(value)}</TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                  
                  {/* 建议列表 */}
                  {message.suggestions && message.suggestions.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom sx={{ color: '#5f6368' }}>
                        您可能还想问：
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {message.suggestions.map((suggestion, idx) => (
                          <Chip
                            key={idx}
                            label={suggestion}
                            size="small"
                            onClick={() => handleSuggestionClick(suggestion)}
                            clickable
                            color="primary"
                            variant="outlined"
                            sx={{ margin: 0.5 }}
                            disabled={loading}
                          />
                        ))}
                      </Box>
                    </Box>
                  )}
                  
                  {/* 正在执行提示 */}
                  {message.isExecuting && (
                    <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                      <CircularProgress size={16} sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        处理中...
                      </Typography>
                    </Box>
                  )}
                  
                  <Typography 
                    variant="caption" 
                    color="text.secondary"
                    sx={{ 
                      display: 'block',
                      mt: 1,
                      textAlign: message.sender === 'user' ? 'right' : 'left'
                    }}
                  >
                    {message.timestamp.toLocaleTimeString()}
                  </Typography>
                </Box>
              </ListItem>
            ))}
            <div ref={messagesEndRef} />
          </List>
        </Paper>
        
        {/* 输入框区域 */}
        <Paper 
          elevation={3}
          component="form"
          onSubmit={(e) => {
            e.preventDefault();
            handleFullQuery(query);
          }}
          sx={{ 
            p: 2,
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <TextField
            fullWidth
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="使用自然语言提问，如：销量最高的3个商品是什么"
            variant="outlined"
            size="medium"
            disabled={loading || !isAuthenticated}
            InputProps={{
              sx: { borderRadius: 28 }
            }}
            error={!isAuthenticated}
            helperText={!isAuthenticated ? "请先登录后再使用查询功能" : ""}
          />
          <Button
            color="primary"
            variant="contained"
            disabled={loading || !query.trim() || !isAuthenticated}
            onClick={() => handleFullQuery(query)}
            sx={{ 
              ml: 2,
              px: 3,
              py: 1,
              borderRadius: 28,
              minWidth: 120
            }}
            endIcon={<SendIcon />}
          >
            发送
          </Button>
        </Paper>
      </Container>
    </>
  );
};

export default QueryPage; 