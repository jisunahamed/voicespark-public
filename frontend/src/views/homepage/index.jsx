import React, { useEffect, useMemo, useState } from 'react';
import {
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  LinearProgress,
  Paper,
  Stack,
  Typography,
  Grid2 as Grid,
} from '@mui/material';
import {
  ArrowForward,
  AutoAwesome,
  CalendarToday,
  Facebook,
  Image,
  Instagram,
  LinkedIn,
  X,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import TopBar from '../../TopBar';
import api from '../login_register/axios_client';
import { workspaceStorage } from '../workspace/workSpaceAPi';
import { AddTopicMediaModal } from '../calendar';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';

const formatDateTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
};

const platformIconSx = { fontSize: 18 };
const platformIcons = [
  { label: 'Facebook', icon: <Facebook sx={{ ...platformIconSx, color: '#1877f2' }} /> },
  { label: 'Instagram', icon: <Instagram sx={{ ...platformIconSx, color: '#c13584' }} /> },
  { label: 'LinkedIn', icon: <LinkedIn sx={{ ...platformIconSx, color: '#0a66c2' }} /> },
  { label: 'X', icon: <X sx={{ ...platformIconSx, color: '#111827' }} /> },
];

function MetricCard({ label, value, helper, accent, route }) {
  const navigate = useNavigate();
  return (
    <Paper
      elevation={0}
      onClick={() => navigate(route)}
      sx={{
        p: 2.25,
        minHeight: 128,
        borderRadius: 1,
        border: '1px solid rgba(17,24,39,0.09)',
        bgcolor: 'rgba(255,255,255,0.92)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        boxShadow: '0 18px 44px rgba(17,24,39,0.06)',
        transition: 'box-shadow .18s ease, transform .18s ease, border-color .18s ease',
        '&:hover': { boxShadow: '0 22px 56px rgba(17,24,39,0.1)', transform: 'translateY(-2px)', borderColor: 'rgba(124,58,237,0.25)' },
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Typography sx={{ fontSize: 13, fontWeight: 800, color: '#667085' }}>{label}</Typography>
        <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: accent }} />
      </Stack>
      <Box>
        <Typography sx={{ fontSize: 34, lineHeight: 1, fontWeight: 950, color: '#1f2328' }}>{value}</Typography>
        <Typography sx={{ mt: 0.7, fontSize: 12, color: '#7b8190' }}>{helper}</Typography>
      </Box>
    </Paper>
  );
}

function HomePage() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const activeWorkspace = workspaceStorage.getActive();
  const workspaceId = workspaceStorage.getActiveId();
  const workspaceName =
    activeWorkspace?.name ||
    [user.first_name, user.last_name].filter(Boolean).join(' ') ||
    'your workspace';

  const [insights, setInsights] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addMediaOpen, setAddMediaOpen] = useState(false);

  const todayLabel = useMemo(
    () =>
      new Intl.DateTimeFormat('en-US', {
        weekday: 'long',
        month: 'short',
        day: 'numeric',
      }).format(new Date()),
    []
  );

  useEffect(() => {
    let cancelled = false;

    const loadHomeData = async () => {
      if (!user?.id || !workspaceId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const [insightsResponse, postsResponse] = await Promise.allSettled([
          api.post('/auth/user/social-insights/', {
            user_id: user.id,
            workspace_id: workspaceId,
          }),
          api.post('/nano-banana/get-generated-image/', {
            user_id: user.id,
            workspace_id: workspaceId,
          }),
        ]);

        if (cancelled) return;

        if (insightsResponse.status === 'fulfilled') {
          setInsights(insightsResponse.value.data?.data || {});
        }
        if (postsResponse.status === 'fulfilled') {
          setPosts(postsResponse.value.data?.data || []);
        }
      } catch (error) {
        console.error('Failed to load home data:', error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadHomeData();
    window.addEventListener('focus', loadHomeData);
    return () => {
      cancelled = true;
      window.removeEventListener('focus', loadHomeData);
    };
  }, [user?.id, workspaceId]);

  const platforms = Object.entries(insights || {});
  const connectedPlatforms = platforms.filter(([, item]) => item?.connected);
  const connectedCount = connectedPlatforms.length;
  const metrics = platforms[0]?.[1]?.metrics || {};
  const scheduledCount =
    metrics.Scheduled ?? posts.filter((post) => post.approval === 'approved').length;
  const reviewCount =
    metrics['Need Review'] ??
    posts.filter((post) => ['not_approved', 'ready'].includes(post.approval)).length;
  const approvedCount = Math.max(posts.length - reviewCount, 0);
  const nextPost = [...posts]
    .filter((post) => post.scheduled_at)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))[0];
  const upcoming = posts.slice(0, 4);
  const focusItems = [
    {
      label: 'Review drafts',
      detail: reviewCount ? `${reviewCount} post${reviewCount === 1 ? '' : 's'} waiting` : 'No drafts waiting',
      route: '/approvals',
    },
    {
      label: 'Prepare calendar',
      detail: nextPost ? `Next post ${formatDateTime(nextPost.scheduled_at)}` : 'No scheduled item yet',
      route: '/calendar',
    },
    {
      label: 'Check channels',
      detail: `${connectedCount}/4 publishing channels connected`,
      route: '/integrations',
    },
  ];

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f7f8f4' }}>
      <TopBar title="Home" />
      <Box
        sx={{
          width: '100%',
          maxWidth: 1560,
          mx: 'auto',
          px: { xs: 2, md: 4 },
          py: { xs: 2.5, md: 4 },
          minHeight: 'calc(100vh - 68px)',
        }}
      >
        <Paper
          elevation={0}
          sx={{
            p: { xs: 2, md: 3 },
            mb: 2.5,
            borderRadius: 1,
            border: '1px solid rgba(17,24,39,0.08)',
            bgcolor: 'rgba(255,255,255,0.92)',
            display: 'flex',
            alignItems: { xs: 'flex-start', md: 'center' },
            justifyContent: 'space-between',
            gap: 2,
            flexDirection: { xs: 'column', md: 'row' },
            boxShadow: '0 16px 46px rgba(17,24,39,0.05)',
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ fontSize: { xs: 30, md: 38 }, fontWeight: 950, letterSpacing: 0, color: '#1f2328', lineHeight: 1.05 }}>
              Home
            </Typography>
            <Typography sx={{ color: '#667085', fontSize: 14, mt: 0.7, maxWidth: 780 }}>
              {todayLabel}. Manage {workspaceName}'s content engine, publishing channels, approvals, and upcoming posts from one clear view.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
            <Button
              variant="outlined"
              onClick={() => navigate('/brand-kit')}
              startIcon={<Image />}
              sx={{ borderRadius: 1, textTransform: 'none', fontWeight: 800, borderColor: '#d7dce5', color: '#344054', minHeight: 40, px: 2.25 }}
            >
              Brand Kit
            </Button>
            <Button
              variant="contained"
              disableElevation
              startIcon={<AddCircleOutlineIcon />}
              onClick={() => setAddMediaOpen(true)}
              sx={{
                borderRadius: 1,
                bgcolor: '#111827',
                color: '#fff',
                fontSize: 14,
                fontWeight: 800,
                px: 2.75,
                minHeight: 40,
                '&:hover': { bgcolor: '#374151' },
              }}
            >
              Create Now
            </Button>
            <Button
              variant="outlined"
              onClick={() => navigate('/content-plan')}
              sx={{
                borderRadius: 1,
                borderColor: 'rgba(17,24,39,0.12)',
                color: '#111827',
                fontSize: 14,
                fontWeight: 800,
                px: 2.75,
                minHeight: 40,
                '&:hover': { bgcolor: 'rgba(17,24,39,0.04)', borderColor: '#111827' },
              }}
            >
              Plan Campaign
            </Button>
          </Stack>
        </Paper>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 8 }}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 4 }}>
                <MetricCard label="Scheduled" value={loading ? '-' : scheduledCount} helper="Approved or queued posts" accent="#7c3aed" route="/calendar" />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <MetricCard label="Need Review" value={loading ? '-' : reviewCount} helper="Drafts waiting approval" accent="#f97316" route="/approvals" />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <MetricCard label="Connected" value={loading ? '-' : `${connectedCount}/4`} helper="Publishing channels" accent="#10b981" route="/integrations" />
              </Grid>

              <Grid size={{ xs: 12, md: 7 }}>
                <Paper elevation={0} sx={{ p: 2.25, minHeight: 250, borderRadius: 1, border: '1px solid rgba(17,24,39,0.08)', bgcolor: '#fff', boxShadow: '0 16px 42px rgba(17,24,39,0.04)' }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
                    <Box>
                      <Typography sx={{ fontSize: 18, fontWeight: 900, color: '#1f2328' }}>Workspace progress</Typography>
                      <Typography sx={{ color: '#667085', fontSize: 13 }}>Brand setup, channels, and content readiness.</Typography>
                    </Box>
                    {loading && <CircularProgress size={20} />}
                  </Stack>
                  {[
                    ['Generated content', posts.length, Math.min(100, posts.length * 12), '/calendar'],
                    ['Approved content', approvedCount, posts.length ? Math.round((approvedCount / posts.length) * 100) : 0, '/approvals'],
                    ['Connected channels', connectedCount, connectedCount * 25, '/integrations'],
                  ].map(([label, value, percent, route]) => (
                    <Box key={label} onClick={() => navigate(route)} sx={{ mb: 1.25, cursor: 'pointer' }}>
                      <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.6 }}>
                        <Typography sx={{ fontSize: 13, fontWeight: 800, color: '#344054' }}>{label}</Typography>
                        <Typography sx={{ fontSize: 13, color: '#667085' }}>{loading ? '-' : value}</Typography>
                      </Stack>
                      <LinearProgress
                        variant="determinate"
                        value={percent}
                        sx={{ height: 8, borderRadius: 99, bgcolor: '#edf0f5', '& .MuiLinearProgress-bar': { bgcolor: '#7c3aed', borderRadius: 99 } }}
                      />
                    </Box>
                  ))}
                </Paper>
              </Grid>

              <Grid size={{ xs: 12, md: 5 }}>
                <Paper elevation={0} sx={{ p: 2.25, minHeight: 250, borderRadius: 1, border: '1px solid rgba(17,24,39,0.08)', bgcolor: '#fff', boxShadow: '0 16px 42px rgba(17,24,39,0.04)' }}>
                  <Typography sx={{ fontSize: 18, fontWeight: 900, color: '#1f2328', mb: 0.5 }}>Channels</Typography>
                  <Typography sx={{ color: '#667085', fontSize: 13, mb: 1.4 }}>Use real platform destinations for publishing.</Typography>
                  <Stack spacing={0.85}>
                    {platformIcons.map((platform) => (
                      <Stack key={platform.label} direction="row" alignItems="center" justifyContent="space-between" sx={{ py: 0.8, px: 1, border: '1px solid #eef0f5', borderRadius: 1 }}>
                        <Stack direction="row" alignItems="center" spacing={1.2}>
                          <Avatar sx={{ width: 30, height: 30, bgcolor: '#f6f7fb' }}>{platform.icon}</Avatar>
                          <Typography sx={{ fontSize: 13, fontWeight: 800, color: '#344054' }}>{platform.label}</Typography>
                        </Stack>
                        <Chip
                          size="small"
                          label={connectedPlatforms.some(([key]) => key.toLowerCase().includes(platform.label.toLowerCase())) ? 'Connected' : 'Not connected'}
                          sx={{ height: 22, fontSize: 11, bgcolor: '#f6f7fb', color: '#667085', fontWeight: 700 }}
                        />
                      </Stack>
                    ))}
                  </Stack>
                </Paper>
              </Grid>

              <Grid size={{ xs: 12 }}>
                <Paper elevation={0} sx={{ p: 2.25, borderRadius: 1, border: '1px solid rgba(17,24,39,0.08)', bgcolor: '#fff', boxShadow: '0 16px 42px rgba(17,24,39,0.04)' }}>
                  <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} spacing={1.5} sx={{ mb: 1.5 }}>
                    <Box>
                      <Typography sx={{ fontSize: 18, fontWeight: 900, color: '#1f2328' }}>Today's focus</Typography>
                      <Typography sx={{ color: '#667085', fontSize: 13 }}>The next operational steps for this workspace.</Typography>
                    </Box>
                    <Chip size="small" label={loading ? 'Syncing' : 'Live workspace data'} sx={{ bgcolor: '#ecfdf3', color: '#027a48', fontWeight: 800 }} />
                  </Stack>
                  <Grid container spacing={1.25}>
                    {focusItems.map((item) => (
                      <Grid key={item.label} size={{ xs: 12, md: 4 }}>
                        <Paper
                          elevation={0}
                          onClick={() => navigate(item.route)}
                          sx={{
                            p: 1.5,
                            borderRadius: 1,
                            border: '1px solid #eef0f5',
                            bgcolor: '#fbfcff',
                            cursor: 'pointer',
                            minHeight: 86,
                            '&:hover': { borderColor: '#d7dce5', bgcolor: '#fff' },
                          }}
                        >
                          <Typography sx={{ fontSize: 13, fontWeight: 900, color: '#1f2328' }}>{item.label}</Typography>
                          <Typography sx={{ fontSize: 12, color: '#667085', mt: 0.6 }}>{loading ? 'Loading workspace state...' : item.detail}</Typography>
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                </Paper>
              </Grid>
            </Grid>
          </Grid>

          <Grid size={{ xs: 12, lg: 4 }}>
            <Paper elevation={0} sx={{ p: 2.25, minHeight: { xs: 430, lg: 558 }, borderRadius: 1, border: '1px solid rgba(17,24,39,0.08)', bgcolor: '#fff', display: 'flex', flexDirection: 'column', boxShadow: '0 16px 42px rgba(17,24,39,0.04)' }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.2 }}>
                <Box>
                  <Typography sx={{ fontSize: 18, fontWeight: 900, color: '#1f2328' }}>Upcoming posts</Typography>
                  <Typography sx={{ color: '#667085', fontSize: 13 }}>Next scheduled item: {nextPost ? formatDateTime(nextPost.scheduled_at) : 'none'}</Typography>
                </Box>
                <Button size="small" onClick={() => navigate('/calendar')} endIcon={<ArrowForward />} sx={{ textTransform: 'none', fontWeight: 800, color: '#7c3aed' }}>
                  Calendar
                </Button>
              </Stack>

              <Stack spacing={0.85} sx={{ flex: 1, minHeight: 0 }}>
                {(upcoming.length ? upcoming : [
                  { title: 'Create a content campaign', approval: 'Start in Calendar' },
                  { title: 'Review generated drafts', approval: 'Approvals' },
                  { title: 'Connect publishing channels', approval: 'Integrations' },
                ]).map((post, index) => (
                  <Paper
                    key={`${post.id || post.title}-${index}`}
                    elevation={0}
                    onClick={() => navigate('/calendar')}
                    sx={{ p: 1.35, borderRadius: 1, bgcolor: '#f8fafc', border: '1px solid #eef0f5', cursor: 'pointer' }}
                  >
                    <Stack direction="row" spacing={1.3} alignItems="center">
                      <Avatar sx={{ width: 36, height: 36, bgcolor: index === 0 ? '#ede9fe' : '#eef2f7', color: '#7c3aed' }}>
                        {index === 0 ? <AutoAwesome fontSize="small" /> : <CalendarToday fontSize="small" />}
                      </Avatar>
                      <Box sx={{ minWidth: 0, flex: 1 }}>
                        <Typography sx={{ fontSize: 13, fontWeight: 850, color: '#1f2328', lineHeight: 1.25 }} noWrap>
                          {post.title || `Post ${index + 1}`}
                        </Typography>
                        <Typography sx={{ fontSize: 12, color: '#667085' }} noWrap>
                          {post.scheduled_at ? formatDateTime(post.scheduled_at) : post.approval || 'Draft'}
                        </Typography>
                      </Box>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            </Paper>
          </Grid>

        </Grid>
      </Box>
      <AddTopicMediaModal open={addMediaOpen} onClose={() => setAddMediaOpen(false)} />
    </Box>
  );
}

export default HomePage;
