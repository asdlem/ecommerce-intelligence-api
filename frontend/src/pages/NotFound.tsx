import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Container, Box, Typography, Button, Paper } from '@mui/material';
import { Home as HomeIcon } from '@mui/icons-material';
import Navbar from '../components/Navbar';
import { useAuth } from '../utils/auth-context';

const NotFound: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  const handleReturn = () => {
    if (isAuthenticated) {
      navigate('/dashboard'); // 已登录用户返回到Dashboard
    } else {
      navigate('/login'); // 未登录用户返回到登录页
    }
  };

  return (
    <>
      <Navbar />
      <Container maxWidth="md">
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '70vh',
            textAlign: 'center',
          }}
        >
          <Paper
            elevation={0}
            sx={{
              p: 6,
              borderRadius: 2,
              backgroundColor: 'transparent',
            }}
          >
            <Typography
              variant="h1"
              component="h1"
              sx={{
                fontSize: { xs: '6rem', sm: '8rem' },
                fontWeight: 'bold',
                color: '#4285F4',
                mb: 2,
              }}
            >
              404
            </Typography>
            
            <Typography
              variant="h4"
              component="h2"
              sx={{ mb: 3, color: '#5f6368' }}
            >
              找不到页面
            </Typography>
            
            <Typography
              variant="body1"
              sx={{ mb: 4, color: '#5f6368', maxWidth: '600px', mx: 'auto' }}
            >
              您请求的页面不存在。可能已被移除、名称已更改或暂时不可用。
            </Typography>
            
            <Button
              variant="contained"
              color="primary"
              onClick={handleReturn}
              startIcon={<HomeIcon />}
              sx={{
                textTransform: 'none',
                py: 1,
                px: 3,
                backgroundColor: '#4285F4',
                '&:hover': { backgroundColor: '#3367d6' },
              }}
            >
              {isAuthenticated ? '返回首页' : '返回登录页'}
            </Button>
          </Paper>
        </Box>
      </Container>
    </>
  );
};

export default NotFound; 