import { useState } from 'react';
import {
  Alert,
  AppBar,
  Avatar,
  Box,
  Divider,
  Menu,
  MenuItem,
  Snackbar,
  Stack,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import LogoutIcon from '@mui/icons-material/Logout';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../views/login_register/auth_context';
import SettingsModal from './settings';

const DRAWER_WIDTH = 232;

const getUserDisplay = () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || user?.email || 'User';
  const initials = displayName
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return { user, displayName, initials };
};

export function MenuItemsSign({ open, handleClose, anchorEl }) {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { user, displayName, initials } = getUserDisplay();
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleSignOut = async () => {
    handleClose();
    await logout();
    navigate('/login');
  };

  return (
    <Menu
      anchorEl={anchorEl}
      open={open}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      PaperProps={{ sx: { width: 240, borderRadius: 2, mt: 1 } }}
    >
      <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar sx={{ width: 36, height: 36, bgcolor: '#7c3aed', fontSize: 13, fontWeight: 900 }}>
          {initials}
        </Avatar>
        <Box sx={{ minWidth: 0 }}>
          <Typography fontWeight={700} fontSize={14} noWrap>{displayName}</Typography>
          <Typography fontSize={12} color="text.secondary" noWrap>{user?.email}</Typography>
        </Box>
      </Box>

      <Divider />
      <MenuItem onClick={() => setSettingsOpen(true)}>
        <SettingsIcon sx={{ mr: 1.5, fontSize: 18 }} /> Settings
      </MenuItem>
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <Divider />
      <MenuItem onClick={handleSignOut} sx={{ color: 'error.main' }}>
        <LogoutIcon sx={{ mr: 1.5, fontSize: 18 }} /> Sign out
      </MenuItem>
    </Menu>
  );
}

function TopBar({ title, leftContent, centerContent, rightContent }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [noticeOpen, setNoticeOpen] = useState(false);
  const open = Boolean(anchorEl);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { initials } = getUserDisplay();

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        width: { xs: '100%', md: `calc(100% - ${DRAWER_WIDTH}px)` },
        ml: { xs: 0, md: `${DRAWER_WIDTH}px` },
        background: 'rgba(251,252,248,0.78)',
        borderBottom: '1px solid rgba(17,24,39,0.08)',
        boxShadow: '0 18px 48px rgba(17,24,39,0.05)',
        backdropFilter: 'blur(18px)',
      }}
    >
      <Toolbar sx={{ minHeight: '56px !important', justifyContent: 'space-between', px: { xs: 1.5, md: 3 } }}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Typography variant="subtitle1" fontWeight={900} color="#1f2328" noWrap sx={{ letterSpacing: 0 }}>
            {title}
          </Typography>
          {!isMobile && leftContent}
        </Stack>

        {!isMobile && (
          <Box
            sx={{
              position: 'absolute',
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {centerContent}
          </Box>
        )}

        <Stack direction="row" alignItems="center" spacing={1} sx={{ ml: 'auto' }}>
          {!isMobile && rightContent}
          <Avatar
            sx={{
              width: 34,
              height: 34,
              bgcolor: '#1f2328',
              color: '#c084fc',
              fontWeight: 900,
              fontSize: 13,
              cursor: 'pointer',
              border: '2px solid rgba(168,85,247,0.45)',
            }}
            onClick={(event) => setAnchorEl(event.currentTarget)}
          >
            {initials}
          </Avatar>
        </Stack>
      </Toolbar>

      {isMobile && centerContent && (
        <Box sx={{ px: 1.5, pb: 1, display: 'flex', justifyContent: 'center', borderTop: '1px solid #ede9fe' }}>
          {centerContent}
        </Box>
      )}

      <MenuItemsSign open={open} handleClose={() => setAnchorEl(null)} anchorEl={anchorEl} />
      <Snackbar
        open={noticeOpen}
        autoHideDuration={2600}
        onClose={() => setNoticeOpen(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        sx={{ mt: 7 }}
      >
        <Alert
          severity="info"
          variant="filled"
          onClose={() => setNoticeOpen(false)}
          sx={{ borderRadius: 2, fontWeight: 700, boxShadow: '0 16px 40px rgba(15,23,42,0.22)' }}
        >
          Coming soon
        </Alert>
      </Snackbar>
    </AppBar>
  );
}

export default TopBar;
