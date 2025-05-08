import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Chip,
  Pagination,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Launch as LaunchIcon,
  ContentCopy as ContentCopyIcon,
} from '@mui/icons-material';
import Navbar from '../components/Navbar';
import { dataAPI } from '../services/api';
import { HistoryRecord } from '../types';

const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [historyRecords, setHistoryRecords] = useState<HistoryRecord[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [queryType, setQueryType] = useState<string | null>(null);

  const rowsPerPage = 10;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const offset = (page - 1) * rowsPerPage;
      const response = await dataAPI.getQueryHistory(rowsPerPage, offset, queryType || undefined);
      
      if (response.history) {
        setHistoryRecords(response.history);
        // 假设总数为记录数量的10倍，实际项目应从API获取总数
        setTotalPages(Math.ceil((response.history.length * 10) / rowsPerPage));
      } else {
        setHistoryRecords([]);
        setTotalPages(1);
      }
    } catch (err: any) {
      console.error('获取历史记录失败:', err);
      setError(err.response?.data?.detail || '获取历史记录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [page, queryType]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // 这里可以根据搜索词筛选历史记录
    // 在实际应用中，应该调用API的搜索功能
    console.log('搜索查询:', searchTerm);
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  const handleQueryTypeChange = (type: string | null) => {
    setQueryType(type);
    setPage(1); // 重置为第一页
  };

  const executeQuery = (query: string) => {
    navigate(`/query?q=${encodeURIComponent(query)}`);
  };

  const copyQuery = (query: string) => {
    navigator.clipboard.writeText(query);
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
  };

  const renderStatusChip = (status: string) => {
    const statusMap: Record<string, { color: 'success' | 'error' | 'warning' | 'default', label: string }> = {
      success: { color: 'success', label: '成功' },
      error: { color: 'error', label: '错误' },
      partial: { color: 'warning', label: '部分完成' },
      pending: { color: 'default', label: '处理中' },
    };

    const { color, label } = statusMap[status] || { color: 'default', label: status };
    
    return <Chip size="small" color={color} label={label} />;
  };

  return (
    <>
      <Navbar />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
        <Typography
          variant="h4"
          component="h1"
          sx={{
            mb: 4,
            color: '#4285F4',
            fontWeight: 'bold',
            fontFamily: '"Product Sans", Arial, sans-serif',
            letterSpacing: '-1px',
          }}
        >
          查询历史
        </Typography>

        {/* 搜索和过滤 */}
        <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Box component="form" onSubmit={handleSearch} sx={{ flexGrow: 1, maxWidth: 500 }}>
            <TextField
              fullWidth
              size="small"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="搜索查询历史..."
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
              sx={{ 
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2
                }
              }}
            />
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip 
              label="全部" 
              color={queryType === null ? 'primary' : 'default'}
              onClick={() => handleQueryTypeChange(null)}
              clickable
            />
            <Chip 
              label="自然语言" 
              color={queryType === 'nl2sql' ? 'primary' : 'default'}
              onClick={() => handleQueryTypeChange('nl2sql')}
              clickable
            />
            <Chip 
              label="直接SQL" 
              color={queryType === 'direct' ? 'primary' : 'default'}
              onClick={() => handleQueryTypeChange('direct')}
              clickable
            />
          </Box>
          
          <IconButton onClick={fetchHistory} title="刷新">
            <RefreshIcon />
          </IconButton>
        </Box>

        {/* 错误提示 */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* 加载状态 */}
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {/* 历史记录表格 */}
            {historyRecords.length > 0 ? (
              <Paper sx={{ width: '100%', overflow: 'hidden', borderRadius: 2 }}>
                <TableContainer sx={{ maxHeight: 600 }}>
                  <Table stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>查询内容</TableCell>
                        <TableCell>时间</TableCell>
                        <TableCell>类型</TableCell>
                        <TableCell>状态</TableCell>
                        <TableCell>操作</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {historyRecords.map((record) => (
                        <TableRow
                          key={record.id}
                          sx={{ '&:hover': { backgroundColor: '#f8f9fa' } }}
                        >
                          <TableCell
                            sx={{
                              maxWidth: 450,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {record.query}
                          </TableCell>
                          <TableCell>{formatTimestamp(record.timestamp)}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={record.query_type === 'nl2sql' ? '自然语言' : record.query_type}
                            />
                          </TableCell>
                          <TableCell>{renderStatusChip(record.status)}</TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex' }}>
                              <IconButton
                                size="small"
                                onClick={() => executeQuery(record.query)}
                                title="重新执行"
                              >
                                <LaunchIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                size="small"
                                onClick={() => copyQuery(record.query)}
                                title="复制查询"
                              >
                                <ContentCopyIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                
                {/* 分页 */}
                <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
                  <Pagination
                    count={totalPages}
                    page={page}
                    onChange={handlePageChange}
                    color="primary"
                  />
                </Box>
              </Paper>
            ) : (
              <Paper sx={{ p: 4, textAlign: 'center', borderRadius: 2 }}>
                <Typography variant="body1" color="textSecondary">
                  没有查询历史记录
                </Typography>
                <Button
                  variant="outlined"
                  component="a"
                  href="/query"
                  sx={{ mt: 2, textTransform: 'none' }}
                >
                  开始一个新查询
                </Button>
              </Paper>
            )}
          </>
        )}
      </Container>
    </>
  );
};

export default HistoryPage; 