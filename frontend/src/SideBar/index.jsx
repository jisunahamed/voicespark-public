
import {
  Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText,
  Typography, AppBar, Toolbar, IconButton, Avatar, Chip, Card, CardContent,
  Button, Divider, Badge, LinearProgress, Stack, Paper, Tooltip,
  useMediaQuery, useTheme, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Alert, CircularProgress,
} from '@mui/material';
import { useState, useEffect } from 'react';
import {
  Home, CalendarToday, CheckCircle, Article,
  Campaign, BarChart, Palette, Tune, Extension
} from '@mui/icons-material';
import WorkspacesOutlinedIcon from '@mui/icons-material/WorkspacesOutlined';
import { Link, useLocation, useNavigate } from "react-router-dom";
import FolderIcon from '@mui/icons-material/Folder';
import MenuIcon from '@mui/icons-material/Menu';
import { AddTopicMediaModal } from '../views/calendar';


import {
  Menu,
  MenuItem,
  Popper, ClickAwayListener, Grow
} from '@mui/material';
import { Settings as SettingsIcon } from '@mui/icons-material';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import LogoutIcon from '@mui/icons-material/Logout';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import { useAuth } from '../views/login_register/auth_context';
import CheckIcon from '@mui/icons-material/Check';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { workspaceApi, workspaceStorage } from '../views/workspace/workSpaceAPi';
import { AmbientWorking } from '../components/VoiceSparkUI';
const DRAWER_WIDTH = 232;

export function UserDropdown({ open, handleClose, anchorEl }) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleSignOut = async () => {
    handleClose();
    await logout();
    navigate('/login');
  };

  const user = JSON.parse(localStorage.getItem('user'));
  const [workspaces, setWorkspaces] = useState([]);
  const activeId = workspaceStorage.getActiveId();

  useEffect(() => {
    workspaceApi.list().then(setWorkspaces).catch(() => {
      setWorkspaces(workspaceStorage.getAll());
    });
  }, []);

  const handleSwitchWorkspace = (id) => {
    workspaceStorage.setActiveId(id);
    handleClose();
    window.location.reload(); // or trigger a context update if you have one
  };

  return (
    <Menu
      anchorEl={anchorEl}
      open={open}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'top', horizontal: 'left' }}
      transformOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      PaperProps={{ sx: { width: 240, borderRadius: 2, mb: 1 } }}
    >
      {/* My Workspaces label */}
      <Typography sx={{ px: 2, pt: 1.5, pb: 0.5, fontSize: 12, color: 'text.secondary', fontWeight: 600 }}>
        My Workspaces
      </Typography>

      {/* Current workspace */}
      {workspaces.map((ws) => (
        <MenuItem key={ws.id} onClick={() => handleSwitchWorkspace(ws.id)} sx={{ gap: 1.5 }}>
          <Avatar sx={{ width: 28, height: 28, bgcolor: '#7c3aed', fontSize: 12 }}>
            {ws.name?.[0]?.toUpperCase()}
          </Avatar>
          <Typography fontSize={14} fontWeight={500} sx={{ flex: 1 }} noWrap>
            {ws.name}
          </Typography>
          {ws.id === activeId && <CheckIcon sx={{ fontSize: 16, color: '#7c3aed' }} />}
        </MenuItem>
      ))}

      <Divider />

      {/* Create workspace */}
      <MenuItem onClick={() => navigate('/workspace')} sx={{ gap: 1.5 }}>
        <AddCircleOutlineIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
        <Typography fontSize={14}>Create workspace</Typography>
      </MenuItem>

      {/* Sign out */}
      <MenuItem onClick={handleSignOut} sx={{ gap: 1.5 }}>
        <LogoutIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
        <Typography fontSize={14}>Sign out</Typography>
      </MenuItem>
    </Menu>
  );
}


const NAV_ITEMS = [
  { label: 'Home', icon: <Home fontSize="small" />, page: 'home', path: '/home' },
  { label: 'Calendar', icon: <CalendarToday fontSize="small" />, page: 'calendar', path: '/calendar' },
  { label: 'Integrations', icon: <Extension fontSize="small" />, page: 'integrations', path: '/integrations' },
  { label: 'Approvals', icon: <CheckCircle fontSize="small" />, page: 'approvals', path: '/approvals' },
  { label: 'Content Planner', icon: <Article fontSize="small" />, page: 'content-plan', path: "/content-plan" },
  // { label: 'Paid Ads',            icon: <Campaign fontSize="small" />,      page: 'paid-ads' },
  { label: 'Insights', icon: <BarChart fontSize="small" />, page: 'insights', path: '/insights' },
  { label: 'Brand Kit', icon: <Palette fontSize="small" />, page: 'brand-kit', path: "/brand-kit" },
  { label: 'Content Preferences', icon: <Tune fontSize="small" />, page: 'content-prefs', path: "/content-preference" },

];

export function SideBar() {
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [open, setOpen] = useState(false);
  const user = JSON.parse(localStorage.getItem('user'));
  const [loading, setLoading] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [addMediaOpen, setAddMediaOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteText, setDeleteText] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [workspaceVersion, setWorkspaceVersion] = useState(0);
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const open2 = Boolean(anchorEl);
  const handleOpen2 = (e) => setAnchorEl(e.currentTarget);
  const handleClose2 = () => setAnchorEl(null);
  const activeWorkspace = workspaceStorage.getActive();
  const canDeleteWorkspace = Boolean(activeWorkspace?.id);
  const deleteMatches = deleteText.trim() === (activeWorkspace?.name || '').trim();
  useEffect(() => {
    if (workspaceStorage.getAll().length === 0) {
      navigate('/workspace');
    }
  }, []);
  useEffect(() => {
    const refreshWorkspace = () => setWorkspaceVersion((value) => value + 1);
    window.addEventListener('workspace-updated', refreshWorkspace);
    return () => window.removeEventListener('workspace-updated', refreshWorkspace);
  }, []);

  const handleDeleteWorkspace = async () => {
    if (!activeWorkspace?.id || !deleteMatches) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await workspaceApi.delete(activeWorkspace.id);
      const nextId = workspaceStorage.getActiveId();
      setDeleteOpen(false);
      setDeleteText('');
      if (nextId) {
        window.location.href = '/home';
      } else {
        window.location.href = '/workspace';
      }
    } catch (error) {
      setDeleteError(error.response?.data?.error || 'Failed to delete this workspace.');
    } finally {
      setDeleting(false);
    }
  };
  const drawerContent = (
    <>
      {/* Logo */}
      <Box onClick={handleOpen2} sx={{ mx: 1.5, my: 1.5, px: 1.5, py: 1.35, display: 'flex', alignItems: 'center', gap: 1.2, cursor: 'pointer', borderRadius: 4, background: 'rgba(255,255,255,0.74)', border: '1px solid rgba(17,24,39,0.08)' }}>
        <Box sx={{
          width: 24,
          height: 24,
          color: '#6d28d9',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16,
        }}><WorkspacesOutlinedIcon sx={{ fontSize: 20 }} /></Box>
        <Typography fontWeight={800} sx={{ fontSize: 12, lineHeight: 1.2, color: '#1f2328' }}>
          {activeWorkspace?.name ?? `${user.first_name} ${user.last_name}`}'s Workspace
        </Typography>
      </Box>

      {/* <Box sx={{ mt: 'auto' }}> */}
      <UserDropdown open={open2} handleClose={handleClose2} anchorEl={anchorEl} />
      {/* </Box> */}



      <List dense>
        {NAV_ITEMS.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              component={Link}
              to={item.path}
              selected={location.pathname === item.path}
              onClick={() => isMobile && setOpen(false)}
              sx={{
                mx: 1.25,
                my: 0.3,
                borderRadius: 999,
                minHeight: 44,
                px: 1.5,
                '&.Mui-selected': {
                  bgcolor: '#ede9fe',
                  color: '#4c1d95',
                  boxShadow: 'inset 0 0 0 1px rgba(124,58,237,0.14)',
                  '&:hover': { bgcolor: '#e9d5ff' },
                },
              }}
            >
              <ListItemIcon sx={{ color: location.pathname === item.path ? '#7c3aed' : '#667085', minWidth: 34 }}>
                {item.icon}
              </ListItemIcon>
              <Typography sx={{ fontSize: 13, fontWeight: 800, color: 'inherit' }}>{item.label}</Typography>
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      <Divider sx={{ my: 1.25, mx: 2, borderColor: 'rgba(17,24,39,0.08)' }} />

      <Typography variant="caption" sx={{ px: 3, color: '#8b928f', fontWeight: 900, letterSpacing: 0, mb: 0.5 }}>
        FILES & PROJECTS
      </Typography>
      <List dense>
        {['Create Now', 'Media Library'].map(label => (
          <ListItem key={label} disablePadding>
            <ListItemButton onClick={() => {
              if (label === 'Create Now') setAddMediaOpen(true);
              isMobile && setOpen(false);
              if (label === "Media Library") navigate("/brand-kit");
            }} sx={{ mx: 1.25, borderRadius: 999, minHeight: 40 }}>
              <ListItemIcon sx={{ minWidth: 34 }}>
                <FolderIcon sx={{ fontSize: 17, color: '#667085' }} />
              </ListItemIcon>
              <Typography sx={{ fontSize: 13, fontWeight: 700, color: '#475467' }}>{label}</Typography>
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      <Box sx={{ flex: 1 }} />

      <Box sx={{ px: 1.25, pb: 1.5 }}>
        <Divider sx={{ mb: 1.25, borderColor: 'rgba(17,24,39,0.08)' }} />
        <ListItemButton
          disabled={!canDeleteWorkspace}
          onClick={() => {
            setDeleteError('');
            setDeleteText('');
            setDeleteOpen(true);
          }}
          sx={{
            borderRadius: 2,
            minHeight: 40,
            color: '#b42318',
            '&:hover': { bgcolor: '#fff1f0' },
            '&.Mui-disabled': { opacity: 0.45 },
          }}
        >
          <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>
            <DeleteOutlineIcon sx={{ fontSize: 18 }} />
          </ListItemIcon>
          <Typography sx={{ fontSize: 13, fontWeight: 800, color: 'inherit' }}>
            Delete this workspace
          </Typography>
        </ListItemButton>
      </Box>


      <AddTopicMediaModal open={addMediaOpen} onClose={() => setAddMediaOpen(false)} onRegenerate={() => setReloadKey(k => k + 1)} onLoadingChange={setLoading} />
      <AmbientWorking active={loading} title="Adding material" detail="Upload and analysis can continue while you use the CRM." />
      <Dialog open={deleteOpen} onClose={() => !deleting && setDeleteOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 900 }}>Delete workspace</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This permanently deletes the workspace and its related content. This action cannot be undone.
          </Alert>
          <Typography sx={{ fontSize: 13, color: '#475467', mb: 1 }}>
            Type <b>{activeWorkspace?.name}</b> to confirm.
          </Typography>
          <TextField
            fullWidth
            size="small"
            value={deleteText}
            onChange={(event) => setDeleteText(event.target.value)}
            disabled={deleting}
            placeholder={activeWorkspace?.name || 'Workspace name'}
          />
          {deleteError && (
            <Typography sx={{ mt: 1, color: '#b42318', fontSize: 12 }}>
              {deleteError}
            </Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setDeleteOpen(false)} disabled={deleting} sx={{ textTransform: 'none' }}>
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleDeleteWorkspace}
            disabled={deleting || !deleteMatches}
            sx={{ textTransform: 'none', fontWeight: 800 }}
          >
            {deleting ? <CircularProgress size={18} color="inherit" /> : 'Delete workspace'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );

  return (
    <>
      {/* Hamburger — only visible on mobile when drawer is closed */}
      {isMobile && !open && (
        <IconButton
          onClick={() => setOpen(true)}
          sx={{ position: 'fixed', top: 12, left: 12, zIndex: 1300, bgcolor: '#fff', boxShadow: 1 }}
        >
          <MenuIcon />
        </IconButton>
      )}

      {isMobile ? (
        <Drawer
          variant="temporary"
          open={open}
          onClose={() => setOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
              borderRight: '1px solid rgba(17,24,39,0.08)',
              background: 'rgba(251,252,248,0.86)',
              backdropFilter: 'blur(18px)',
              display: 'flex',
              flexDirection: 'column',
            },
          }}
        >
          {/* Close button inside drawer */}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', px: 1, pt: 1 }}>
            <IconButton onClick={() => setOpen(false)}>
              <MenuIcon />
            </IconButton>
          </Box>

          {drawerContent}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
              borderRight: '1px solid rgba(17,24,39,0.08)',
              background: 'rgba(251,252,248,0.86)',
              backdropFilter: 'blur(18px)',
              display: 'flex',
              flexDirection: 'column',
            },
          }}
        >
          {drawerContent}
        </Drawer>
      )}
    </>
  );
}
export default SideBar
