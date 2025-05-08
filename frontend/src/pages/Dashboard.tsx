import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Container,
  Grid,
  Box,
  Typography,
  Paper,
  Button,
  Card,
  CardContent,
  CardActions,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  History as HistoryIcon,
  Storage as StorageIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';
import Navbar from '../components/Navbar';
import { dataAPI } from '../services/api';
import { useAuth } from '../utils/auth-context';
import { HistoryRecord } from '../types';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [tableCount, setTableCount] = useState(0);
  const [recentQueries, setRecentQueries] = useState<string[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // 获取数据库表数量
        const tablesResponse = await dataAPI.getTables();
        setTableCount(tablesResponse.data?.length || 0);

        // 获取最近的查询
        const historyResponse = await dataAPI.getQueryHistory(5);
        if (historyResponse.history) {
          setRecentQueries(historyResponse.history.map((item: HistoryRecord) => item.query));
        }
      } catch (error) {
        console.error('获取数据失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const features = [
    {
      title: '智能查询',
      description: '使用自然语言进行数据查询，无需编写SQL',
      icon: <SearchIcon fontSize="large" sx={{ color: '#4285F4' }} />,
      link: '/query',
      buttonText: '开始查询',
    },
    {
      title: '历史记录',
      description: '查看您过去的查询历史，重复使用或优化',
      icon: <HistoryIcon fontSize="large" sx={{ color: '#FBBC05' }} />,
      link: '/history',
      buttonText: '查看历史',
    },
    {
      title: '数据总览',
      description: '浏览数据库结构和可用数据',
      icon: <StorageIcon fontSize="large" sx={{ color: '#34A853' }} />,
      link: '/tables',
      buttonText: '浏览数据',
    },
    {
      title: '数据分析',
      description: '自动生成数据可视化和分析洞察',
      icon: <TrendingUpIcon fontSize="large" sx={{ color: '#EA4335' }} />,
      link: '/analysis',
      buttonText: '探索分析',
    },
  ];

  return (
    <>
      <Navbar />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
        {/* 欢迎信息 */}
        <Paper 
          elevation={2}
          sx={{ 
            p: 4, 
            mb: 4, 
            borderRadius: 2,
            background: 'linear-gradient(135deg, #4285F4 0%, #34A853 100%)',
            color: 'white'
          }}
        >
          <Typography variant="h4" gutterBottom>
            欢迎回来，{user?.username || '用户'}
          </Typography>
          <Typography variant="subtitle1">
            使用电商智能API探索您的数据，只需用自然语言提问，系统将自动生成SQL并执行查询。
          </Typography>
          <Button 
            variant="contained" 
            component={Link} 
            to="/query"
            startIcon={<SearchIcon />}
            sx={{ 
              mt: 2, 
              bgcolor: 'white', 
              color: '#4285F4',
              '&:hover': { bgcolor: '#f1f3f4', color: '#4285F4' }
            }}
          >
            开始使用
          </Button>
        </Paper>

        {/* 数据统计 */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" gutterBottom>
            系统概览
          </Typography>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper sx={{ p: 3, borderRadius: 2, textAlign: 'center' }}>
                {loading ? (
                  <CircularProgress size={24} />
                ) : (
                  <>
                    <Typography variant="h3" color="primary">
                      {tableCount}
                    </Typography>
                    <Typography variant="body1" color="textSecondary">
                      可查询表
                    </Typography>
                  </>
                )}
              </Paper>
            </Grid>
            {/* 这里可以添加其他统计数据卡片 */}
          </Grid>
        </Box>

        {/* 功能卡片 */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" gutterBottom>
            主要功能
          </Typography>
          <Grid container spacing={3}>
            {features.map((feature, index) => (
              <Grid size={{ xs: 12, sm: 6, md: 3 }} key={index}>
                <Card sx={{ 
                  height: '100%', 
                  display: 'flex', 
                  flexDirection: 'column',
                  borderRadius: 2,
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 6px 20px rgba(0, 0, 0, 0.1)'
                  }
                }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ mb: 2, display: 'flex', justifyContent: 'center' }}>
                      {feature.icon}
                    </Box>
                    <Typography variant="h6" align="center" gutterBottom>
                      {feature.title}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" align="center">
                      {feature.description}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button 
                      fullWidth 
                      component={Link} 
                      to={feature.link}
                      variant="outlined"
                      size="small"
                      sx={{ textTransform: 'none' }}
                    >
                      {feature.buttonText}
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>

        {/* 最近查询 */}
        {recentQueries.length > 0 && (
          <Box>
            <Typography variant="h5" gutterBottom>
              最近查询
            </Typography>
            <Paper sx={{ p: 2, borderRadius: 2 }}>
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <CircularProgress />
                </Box>
              ) : (
                recentQueries.map((query, index) => (
                  <Box
                    key={index}
                    sx={{
                      p: 2,
                      borderBottom: index < recentQueries.length - 1 ? '1px solid #f0f0f0' : 'none',
                      '&:hover': { bgcolor: '#f8f9fa' },
                    }}
                  >
                    <Typography variant="body1">{query}</Typography>
                    <Button
                      component={Link}
                      to={`/query?q=${encodeURIComponent(query)}`}
                      size="small"
                      sx={{ mt: 1, textTransform: 'none' }}
                    >
                      重新执行
                    </Button>
                  </Box>
                ))
              )}
            </Paper>
          </Box>
        )}
      </Container>
    </>
  );
};

export default Dashboard; 