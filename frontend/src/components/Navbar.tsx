import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  Toolbar,
  IconButton,
  Typography,
  Menu,
  MenuItem,
  Button,
  Tooltip,
  Avatar,
  Container,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import SearchIcon from '@mui/icons-material/Search';
import HistoryIcon from '@mui/icons-material/History';
import { useAuth } from '../utils/auth-context';

const Navbar: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorElNav, setAnchorElNav] = useState<null | HTMLElement>(null);
  const [anchorElUser, setAnchorElUser] = useState<null | HTMLElement>(null);

  const pages = [
    { name: '查询', path: '/query', icon: <SearchIcon /> },
    { name: '历史记录', path: '/history', icon: <HistoryIcon /> },
  ];

  const handleOpenNavMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElNav(event.currentTarget);
  };

  const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElUser(event.currentTarget);
  };

  const handleCloseNavMenu = () => {
    setAnchorElNav(null);
  };

  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };

  const handleLogout = () => {
    logout();
    handleCloseUserMenu();
    navigate('/login');
  };

  const isActivePage = (path: string) => {
    return location.pathname === path;
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <AppBar position="static" color="inherit" elevation={1}>
      <Container maxWidth="xl">
        <Toolbar disableGutters>
          {/* 桌面端Logo */}
          <Typography
            variant="h6"
            noWrap
            component={Link}
            to="/"
            sx={{
              mr: 2,
              display: { xs: 'none', md: 'flex' },
              fontWeight: 700,
              color: '#4285F4',
              textDecoration: 'none',
              alignItems: 'center',
            }}
          >
            电商智能API
          </Typography>

          {/* 移动端菜单按钮 */}
          <Box sx={{ flexGrow: 1, display: { xs: 'flex', md: 'none' } }}>
            <IconButton
              size="large"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleOpenNavMenu}
              color="inherit"
            >
              <MenuIcon />
            </IconButton>
            <Menu
              id="menu-appbar"
              anchorEl={anchorElNav}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'left',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'left',
              }}
              open={Boolean(anchorElNav)}
              onClose={handleCloseNavMenu}
              sx={{
                display: { xs: 'block', md: 'none' },
              }}
            >
              {pages.map((page) => (
                <MenuItem
                  key={page.name}
                  component={Link}
                  to={page.path}
                  onClick={handleCloseNavMenu}
                  selected={isActivePage(page.path)}
                  sx={{
                    color: isActivePage(page.path) ? '#4285F4' : 'inherit',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ mr: 1 }}>{page.icon}</Box>
                    <Typography textAlign="center">{page.name}</Typography>
                  </Box>
                </MenuItem>
              ))}
            </Menu>
          </Box>

          {/* 移动端Logo */}
          <Typography
            variant="h6"
            noWrap
            component={Link}
            to="/"
            sx={{
              mr: 2,
              display: { xs: 'flex', md: 'none' },
              flexGrow: 1,
              fontWeight: 700,
              color: '#4285F4',
              textDecoration: 'none',
            }}
          >
            电商智能API
          </Typography>

          {/* 桌面端导航菜单 */}
          <Box sx={{ flexGrow: 1, display: { xs: 'none', md: 'flex' } }}>
            {pages.map((page) => (
              <Button
                key={page.name}
                component={Link}
                to={page.path}
                startIcon={page.icon}
                onClick={handleCloseNavMenu}
                sx={{
                  my: 2,
                  mx: 1,
                  color: isActivePage(page.path) ? '#4285F4' : 'inherit',
                  display: 'flex',
                  fontWeight: isActivePage(page.path) ? 'bold' : 'normal',
                  borderBottom: isActivePage(page.path) ? '2px solid #4285F4' : 'none',
                  borderRadius: 0,
                  '&:hover': {
                    backgroundColor: 'transparent',
                    borderBottom: '2px solid #FBBC05',
                  },
                }}
              >
                {page.name}
              </Button>
            ))}
          </Box>

          {/* 用户菜单 */}
          <Box sx={{ flexGrow: 0 }}>
            <Tooltip title="打开设置">
              <IconButton onClick={handleOpenUserMenu} sx={{ p: 0 }}>
                <Avatar
                  sx={{ bgcolor: '#FBBC05' }}
                  alt={user?.username || 'User'}
                >
                  {user?.username?.[0]?.toUpperCase() || 'U'}
                </Avatar>
              </IconButton>
            </Tooltip>
            <Menu
              sx={{ mt: '45px' }}
              id="menu-appbar"
              anchorEl={anchorElUser}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorElUser)}
              onClose={handleCloseUserMenu}
            >
              <MenuItem component={Link} to="/profile" onClick={handleCloseUserMenu}>
                <Typography textAlign="center">个人信息</Typography>
              </MenuItem>
              <MenuItem onClick={handleLogout}>
                <Typography textAlign="center">退出登录</Typography>
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Navbar; 