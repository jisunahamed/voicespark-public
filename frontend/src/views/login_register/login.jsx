import { useState } from 'react';
import { Link as RouterLink, useNavigate, useLocation } from 'react-router-dom';
import {
  Box, Button, TextField, Typography, Link,
  InputAdornment, IconButton, Alert, CircularProgress,
  Divider, Paper,
} from '@mui/material';
import {
  Visibility, VisibilityOff, LockOutlined,
} from '@mui/icons-material';
import { useAuth } from './auth_context';
import { workspaceApi, workspaceStorage } from '../workspace/workSpaceAPi';
import { contentEngineApi } from './content_engine_api';
import { AmbientWorking, AuthVisualPanel, BrandMark } from '../../components/VoiceSparkUI';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const from = location.state?.from?.pathname || '/home';

  const [form, setForm] = useState({ email: '', password: '' });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form.email, form.password);
      try {
        const workspaces = await workspaceApi.list();
        if (!workspaceStorage.getActiveId() && workspaces?.[0]?.id) {
          workspaceStorage.setActiveId(workspaces[0].id);
        }
        const state = await contentEngineApi.fetchOnboardingState();
        navigate(state.data?.onboarding?.route || from, { replace: true });
      } catch {
        navigate(from, { replace: true });
      }
    } catch (err) {
      const data = err.response?.data;
      const msg =
        data?.detail ||
        (Array.isArray(data) ? data[0] : null) ||
        data?.non_field_errors?.[0] ||
        'Invalid email or password.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="voice-auth-page">
      <Box className="voice-auth-panel">
        <Box className="voice-auth-card">
          <Box display="flex" justifyContent="center" mb={2}>
            <BrandMark />
          </Box>

          <Typography variant="h4" fontWeight={900} textAlign="center" mb={0.75} color="#1f2328">
            Welcome back
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center" mb={3}>
            Sign in to continue building with Voice Spark.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2, borderRadius: 3 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} noValidate>
            <TextField
              fullWidth
              label="Email"
              name="email"
              value={form.email}
              onChange={handleChange}
              margin="normal"
              required
              autoComplete="email"
              autoFocus
            />

            <TextField
              fullWidth
              label="Password"
              name="password"
              type={showPw ? 'text' : 'password'}
              value={form.password}
              onChange={handleChange}
              margin="normal"
              required
              autoComplete="current-password"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPw((v) => !v)}
                      edge="end"
                      aria-label="toggle password"
                    >
                      {showPw ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{ mt: 3, mb: 2, py: 1.45, fontWeight: 900 }}
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </Button>

            <Divider sx={{ my: 2 }}>
              <Typography variant="caption" color="text.secondary">
                OR
              </Typography>
            </Divider>

            <Typography variant="body2" textAlign="center">
              Don&apos;t have an account?{' '}
              <Link component={RouterLink} to="/register" fontWeight={800} color="#7e22ce">
                Create one
              </Link>
            </Typography>
          </Box>
        </Box>
      </Box>
      <AuthVisualPanel />
      <AmbientWorking active={loading} title="Signing you in" detail="Checking your workspace and onboarding state." />
    </Box>
  );
}
