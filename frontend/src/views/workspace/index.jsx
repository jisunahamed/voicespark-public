import { useState, useEffect } from 'react';
import {
  Box, Typography, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, CircularProgress, Alert,
  Card, CardActionArea, CardContent, Chip, Divider, Avatar,
  IconButton, Tooltip
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WorkspacesIcon from '@mui/icons-material/Workspaces';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { workspaceApi, workspaceStorage } from './workSpaceAPi';
import { useNavigate } from 'react-router-dom';
import useAppStore from '../login_register/constants';
import { contentEngineApi } from '../login_register/content_engine_api';
import { AmbientWorking, BrandMark } from '../../components/VoiceSparkUI';

// ── Colour palette for workspace avatars ─────────────────────────────────────
const AVATAR_COLORS = [
  { bg: '#E1F5EE', text: '#7e22ce' },
  { bg: '#E6F1FB', text: '#185FA5' },
  { bg: '#EEEDFE', text: '#3C3489' },
  { bg: '#FAEEDA', text: '#854F0B' },
  { bg: '#FBEAF0', text: '#72243E' },
  { bg: '#FAECE7', text: '#712B13' },
];

function avatarColor(name = '') {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function initials(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map(w => w[0]?.toUpperCase()).join('');
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function WorkspaceSelectPage({ onWorkspaceSelected }) {
  const [workspaces, setWorkspaces]     = useState([]);
  const [activeId, setActiveId]         = useState(null);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState('');
  const [dialogOpen, setDialogOpen]     = useState(false);
  const [newName, setNewName]           = useState('');
  const [websiteUrl, setWebsiteUrl]     = useState('');
  const [creating, setCreating]         = useState(false);
  const [createError, setCreateError]   = useState('');
  const [copied, setCopied]             = useState('');
  const setWebsiteLink = useAppStore((state) => state.setWebsiteLink);
  const setMarkdown = useAppStore((state) => state.setMarkdown);
  const setImageUrls = useAppStore((state) => state.setImageUrls);
  const setBrandStyle = useAppStore((state) => state.setBrandStyle);
  const navigate = useNavigate();
  // ── On mount: check localStorage first, then fetch from server ────────────
  useEffect(() => {
    const local = workspaceStorage.getAll();
    const savedActiveId = workspaceStorage.getActiveId();

    if (local.length) {
      setWorkspaces(local);
      setActiveId(savedActiveId);
      setLoading(false);
      // If active workspace already saved, auto-proceed
      if (savedActiveId) {
        onWorkspaceSelected?.(savedActiveId);
        return;
      }
    }

    // No local data — fetch from server
    workspaceApi.list()
      .then((data) => {
        setWorkspaces(data);
        const aid = workspaceStorage.getActiveId();
        setActiveId(aid);
        // Auto-open create dialog if user has no workspaces at all
        if (!data.length) setDialogOpen(true);
      })
      .catch(() => setError('Failed to load workspaces. Please refresh.'))
      .finally(() => setLoading(false));
  }, []);

  const handleSelect = (id) => {
    workspaceStorage.setActiveId(id);
    setActiveId(id);
    onWorkspaceSelected?.(id);
    navigate('/home');
  };

  const handleCreate = async () => {
    const name = newName.trim();
    const link = websiteUrl.trim();
    if (!name) { setCreateError('Workspace name is required.'); return; }
    if (!link) { setCreateError('Website URL is required.'); return; }
    const dupe = workspaces.find(w => w.name.toLowerCase() === name.toLowerCase());
    if (dupe)  { setCreateError('A workspace with this name already exists.'); return; }

    setCreating(true);
    setCreateError('');
    try {
      const ws = await workspaceApi.create(name);
      setWorkspaces(prev => [ws, ...prev]);
      workspaceStorage.setActiveId(ws.id);
      setActiveId(ws.id);
      onWorkspaceSelected?.(ws.id);
      setWebsiteLink({ website_link: link });
      try {
        await contentEngineApi.saveOnboardingState({ website_url: link });
      } catch (stateError) {
        console.warn('Workspace onboarding draft could not be saved.', stateError);
      }
      setMarkdown('');
      setImageUrls([]);
      setBrandStyle({
        visual_identity: '',
        colors: [],
        logos: [],
        fonts: [],
      });
      setDialogOpen(false);
      setNewName('');
      setWebsiteUrl('');
      navigate('/business-profile-builder', { replace: true });
    } catch (err) {
      const status = err.response?.status;
      if (status === 401) {
        setCreateError('Your session expired. Please sign in again.');
      } else {
        setCreateError(err.response?.data?.error || err.response?.data?.detail || err.message || 'Failed to create workspace. Try again.');
      }
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = (id) => {
    navigator.clipboard.writeText(id).catch(() => {});
    setCopied(id);
    setTimeout(() => setCopied(''), 1500);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <Box className="voice-onboarding-page" sx={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      p: 2,
      fontFamily: "'DM Sans', sans-serif",
    }}>
      <Box sx={{ width: '100%', maxWidth: 560 }}>

        {/* Header */}
        <Box sx={{ mb: 4, textAlign: 'center' }}>
          <Box sx={{ display: 'inline-flex', mb: 2 }}><BrandMark size={52} /></Box>
          <Typography sx={{
            fontSize: 30, fontWeight: 900, color: '#1f2328',
            fontFamily: "'DM Sans', sans-serif", letterSpacing: '-0.5px',
          }}>
            Choose a workspace
          </Typography>
          <Typography sx={{ color: '#6B6B6B', fontSize: 14, mt: 0.5 }}>
            Select an existing workspace or create a new one to continue.
          </Typography>
        </Box>

        {/* Error banner */}
        {error && <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>{error}</Alert>}

        {/* Loading */}
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress sx={{ color: '#7e22ce' }} />
          </Box>
        ) : (
          <>
            {/* Workspace list */}
            {workspaces.length > 0 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 3 }}>
                {workspaces.map((ws) => {
                  const color   = avatarColor(ws.name);
                  const isActive = ws.id === activeId;
                  return (
                    <Card key={ws.id} elevation={0} sx={{
                      border: isActive ? '2px solid #a855f7' : '1.5px solid rgba(17,24,39,0.08)',
                      borderRadius: 5,
                      bgcolor: isActive ? '#f3e8ff' : 'rgba(255,255,255,0.80)',
                      transition: 'border-color 0.15s, background 0.15s',
                      '&:hover': { borderColor: isActive ? '#a855f7' : 'rgba(168,85,247,0.38)' },
                    }}>
                      <CardActionArea onClick={() => handleSelect(ws.id)} sx={{ borderRadius: 3 }}>
                        <CardContent sx={{
                          display: 'flex', alignItems: 'center', gap: 2, py: 1.75, px: 2.5,
                          '&:last-child': { pb: 1.75 },
                        }}>
                          {/* Avatar */}
                          <Avatar sx={{
                            bgcolor: color.bg, color: color.text,
                            fontWeight: 700, fontSize: 14, width: 42, height: 42,
                            borderRadius: 2, fontFamily: "'DM Sans', sans-serif",
                          }}>
                            {initials(ws.name)}
                          </Avatar>

                          {/* Info */}
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography sx={{
                              fontWeight: 600, fontSize: 15, color: '#1A1A1A',
                              fontFamily: "'DM Sans', sans-serif",
                            }}>
                              {ws.name}
                            </Typography>
                            <Typography sx={{
                              fontSize: 11, color: '#9E9E9E',
                              fontFamily: 'monospace',
                              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                            }}>
                              {ws.id}
                            </Typography>
                          </Box>

                          {/* Actions */}
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }} onClick={e => e.stopPropagation()}>
                            <Tooltip title={copied === ws.id ? 'Copied!' : 'Copy ID'}>
                              <IconButton size="small" onClick={() => handleCopy(ws.id)} sx={{ color: '#BDBDB5' }}>
                                <ContentCopyIcon sx={{ fontSize: 16 }} />
                              </IconButton>
                            </Tooltip>
                            {isActive && (
                              <Chip
                                icon={<CheckCircleIcon sx={{ fontSize: '14px !important', color: '#7e22ce !important' }} />}
                                label="Active"
                                size="small"
                                sx={{
                                  bgcolor: '#f3e8ff', color: '#7e22ce',
                                  fontWeight: 600, fontSize: 11,
                                  fontFamily: "'DM Sans', sans-serif",
                                  height: 24, border: 'none',
                                }}
                              />
                            )}
                          </Box>
                        </CardContent>
                      </CardActionArea>
                    </Card>
                  );
                })}
              </Box>
            )}

            {/* No workspaces message */}
            {workspaces.length === 0 && (
              <Box sx={{
                textAlign: 'center', py: 5, px: 3,
                border: '1.5px dashed #D5D3CC', borderRadius: 3, mb: 3,
              }}>
                <Typography sx={{ color: '#9E9E9E', fontSize: 14 }}>
                  You don't have any workspaces yet.
                </Typography>
              </Box>
            )}

            {/* Divider */}
            {workspaces.length > 0 && (
              <Divider sx={{ mb: 3, borderColor: '#E5E3DC' }}>
                <Typography sx={{ color: '#BDBDB5', fontSize: 12, px: 1 }}>or</Typography>
              </Divider>
            )}

            {/* Create new button */}
            <Button
              fullWidth
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => { setDialogOpen(true); setCreateError(''); setNewName(''); setWebsiteUrl(''); }}
              sx={{
                borderColor: '#D5D3CC', color: '#1A1A1A',
                fontFamily: "'DM Sans', sans-serif", fontWeight: 600,
                fontSize: 14, py: 1.4, borderRadius: 2.5,
                textTransform: 'none', letterSpacing: 0,
                '&:hover': { borderColor: '#a855f7', color: '#7e22ce', bgcolor: '#f3e8ff' },
              }}
            >
              Create new workspace
            </Button>
          </>
        )}
      </Box>

      {/* ── Create workspace dialog ─────────────────────────────────────────── */}
      <Dialog
        open={dialogOpen}
        onClose={() => !creating && setDialogOpen(false)}
        PaperProps={{
          sx: {
            borderRadius: 3, p: 1, minWidth: 360,
            fontFamily: "'DM Sans', sans-serif",
          }
        }}
      >
        <DialogTitle sx={{
          fontFamily: "'DM Sans', sans-serif", fontWeight: 700,
          fontSize: 18, pb: 0.5,
        }}>
          New workspace
        </DialogTitle>
        <DialogContent sx={{ pt: '12px !important' }}>
          <Typography sx={{ color: '#6B6B6B', fontSize: 13, mb: 2 }}>
            Give your workspace a name and website URL. The website will be analyzed for this workspace.
          </Typography>
          <TextField
            autoFocus
            fullWidth
            size="small"
            placeholder="e.g. Nike Project"
            value={newName}
            onChange={(e) => { setNewName(e.target.value); setCreateError(''); }}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            inputProps={{ maxLength: 60 }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                fontFamily: "'DM Sans', sans-serif",
                '&.Mui-focused fieldset': { borderColor: '#a855f7' },
              },
            }}
          />
          <TextField
            fullWidth
            size="small"
            placeholder="https://example.com"
            value={websiteUrl}
            onChange={(e) => { setWebsiteUrl(e.target.value); setCreateError(''); }}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            error={!!createError}
            helperText={createError}
            sx={{
              mt: 1.5,
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                fontFamily: "'DM Sans', sans-serif",
                '&.Mui-focused fieldset': { borderColor: '#a855f7' },
              },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
          <Button
            onClick={() => setDialogOpen(false)}
            disabled={creating}
            sx={{
              color: '#6B6B6B', textTransform: 'none',
              fontFamily: "'DM Sans', sans-serif", fontWeight: 500,
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={creating || !newName.trim() || !websiteUrl.trim()}
            variant="contained"
            sx={{
              bgcolor: '#1f2328', fontFamily: "'DM Sans', sans-serif",
              fontWeight: 600, textTransform: 'none', borderRadius: 2,
              px: 3, boxShadow: 'none',
              '&:hover': { bgcolor: '#7e22ce', boxShadow: 'none' },
              '&:disabled': { bgcolor: '#c4b5fd', color: '#fff' },
            }}
          >
            {creating ? <CircularProgress size={18} sx={{ color: '#fff' }} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
      <AmbientWorking active={creating} title="Building workspace" detail="Website analysis starts in the background after this step." />
    </Box>
  );
}
