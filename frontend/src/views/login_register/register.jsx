import { useState, useRef } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Box, Button, TextField, Typography, Link,
  InputAdornment, IconButton, Alert, CircularProgress,
  Grid2 as Grid, Paper, FormControl,

  MenuItem, Select, InputLabel, FormHelperText,

} from '@mui/material';
import { Visibility, VisibilityOff, PersonAddOutlined } from '@mui/icons-material';
import { useAuth } from './auth_context';
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import config from '../../config';
import axios from 'axios';
import useAppStore from './constants';
import { workspaceApi, workspaceStorage } from '../workspace/workSpaceAPi';
import { contentEngineApi } from './content_engine_api';
import { AmbientWorking, BrandMark } from '../../components/VoiceSparkUI';

const INITIAL = {
  first_name: '',
  last_name: '',
  username: '',
  email: '',
  password: '',
  password2: '',
};

const inputSx = {
  mb: 2.5,
  '& .MuiOutlinedInput-root': {
    borderRadius: '10px',
    bgcolor: '#f0f4ff',
    fontSize: '0.9rem',
    '& fieldset': { borderColor: 'transparent' },
    '&:hover fieldset': { borderColor: '#93c5fd' },
    '&.Mui-focused fieldset': { borderColor: '#3b82f6', borderWidth: '2px', bgcolor: 'transparent' },
  },
  '& .MuiInputLabel-root': { display: 'none' },
  '& .MuiOutlinedInput-input': { py: 1.5 },
};
 
const selectSx = {
  borderRadius: '10px',
  bgcolor: '#f8fafc',
  fontSize: '0.9rem',
  '& fieldset': { borderColor: '#e2e8f0' },
  '&:hover fieldset': { borderColor: '#94a3b8' },
  '&.Mui-focused fieldset': { borderColor: '#3b82f6', borderWidth: '2px' },
};
 
const CATEGORIES = [
  'E-commerce / Retail',
  'Food & Beverage',
  'Health & Wellness',
  'Technology / SaaS',
  'Real Estate',
  'Education',
  'Finance',
  'Agency / Consulting',
  'Other',
];
 
// \u2500\u2500 Right panel: campaigns preview \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
function CampaignsPreview() {
  const campaigns = [
    { title: 'Founder Journey Q1',     sub: '\U0001f525 Founder Stories',        from: 'Thu, Mar 12', to: 'Wed, Mar 18', color: '#f97316' },
    { title: 'Valentine Product Reveal', sub: 'Product Highlights',      from: 'Fri, Mar 13', to: 'Thu, Mar 19', color: '#3b82f6' },
    { title: 'Success Stories Q1',     sub: 'Customer Testimonials',      from: 'Thu, Mar 19', to: 'Wed, Mar 25', color: '#22c55e' },
    { title: 'Tips & Tricks March',    sub: 'Educational Tips',           from: 'Fri, Mar 20', to: 'Thu, Mar 26', color: '#8b5cf6' },
    { title: 'Spring Sale 2026',       sub: 'Promotional Offers',         from: 'Thu, Mar 26', to: 'Wed, Apr 1',  color: '#6366f1' },
    { title: 'Spring Sale 2026',       sub: 'Customer Testimonials',      from: 'Fri, Mar 27', to: 'Thu, Apr 2',  color: '#f59e0b' },
    { title: 'Product updates Q1',     sub: 'Product Highlights',         from: 'Sat, Mar 28', to: 'Fri, Apr 3',  color: '#14b8a6' },
  ];
 
  return (
    <Box sx={{
      flex: 1, bgcolor: '#f8fafc',
      display: { xs: 'none', md: 'flex' },
      alignItems: 'flex-start', justifyContent: 'center',
      pt: 8, overflow: 'hidden',
    }}>
      <Box sx={{
        width: '84%', maxWidth: 560,
        bgcolor: '#fff', borderRadius: '14px 14px 0 0',
        boxShadow: '0 12px 48px rgba(0,0,0,0.10)',
        overflow: 'hidden', border: '1px solid #e8ecf0',
      }}>
        {/* titlebar */}
        <Box sx={{ bgcolor: '#18181b', px: 2.5, py: 1.2, display: 'flex', alignItems: 'center', gap: 1 }}>
          {['#ff5f57','#febc2e','#28c840'].map(c => (
            <Box key={c} sx={{ width: 11, height: 11, borderRadius: '50%', bgcolor: c }} />
          ))}
        </Box>
 
        <Box sx={{ p: 3 }}>
          {/* Header */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2.5 }}>
            <Typography sx={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>Content Plan</Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Box sx={{ bgcolor: '#f1f5f9', borderRadius: '7px', px: 1.5, py: 0.5, fontSize: '0.72rem', color: '#64748b', fontWeight: 500 }}>
                + Add Campaign
              </Box>
              <Box sx={{ bgcolor: '#f1f5f9', borderRadius: '7px', px: 1.5, py: 0.5, fontSize: '0.72rem', color: '#64748b', fontWeight: 500 }}>
                Ge...
              </Box>
            </Box>
          </Box>
 
          <Typography sx={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a', mb: 1.5 }}>Campaigns</Typography>
 
          {/* Column headers */}
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 80px', gap: 1, px: 0.5, mb: 1 }}>
            {['Campaign name & strategy', 'Start and end date', 'Stat'].map(h => (
              <Typography key={h} sx={{ fontSize: '0.68rem', color: '#94a3b8', fontWeight: 600 }}>{h}</Typography>
            ))}
          </Box>
 
          {/* Campaign rows */}
          {campaigns.map((c, i) => (
            <Box key={i} sx={{
              display: 'grid', gridTemplateColumns: '1fr 1fr 80px',
              gap: 1, alignItems: 'center',
              py: 1, px: 0.5,
              borderTop: '1px solid #f1f5f9',
              '&:hover': { bgcolor: '#fafbfc' },
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
                <Box sx={{ width: 32, height: 32, borderRadius: '8px', bgcolor: c.color + '22', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Box sx={{ width: 16, height: 16, borderRadius: '4px', bgcolor: c.color, opacity: 0.7 }} />
                </Box>
                <Box>
                  <Typography sx={{ fontSize: '0.75rem', fontWeight: 600, color: '#1e293b', lineHeight: 1.2 }}>{c.title}</Typography>
                  <Typography sx={{ fontSize: '0.65rem', color: '#94a3b8' }}>{c.sub}</Typography>
                </Box>
              </Box>
              <Typography sx={{ fontSize: '0.68rem', color: '#64748b' }}>
                {c.from} \u2013 {c.to}
              </Typography>
              <Box sx={{ width: 20, height: 20, borderRadius: '50%', bgcolor: c.color + '33',
                border: `2px solid ${c.color}`, flexShrink: 0 }} />
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
}
 
// \u2500\u2500 Main register page \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
export default function RegisterPage() {
  const navigate     = useNavigate();
  const { register } = useAuth();
 
  const [step, setStep] = useState(1); // Step 1: account creds | Step 2: onboarding
 
  // Step 1 fields
  const [creds, setCreds] = useState({email: '', password: '', password2: '' });
  // Step 2 fields
  const [profile, setProfile] = useState({ first_name: '', category: '' });
  
  // Step 3 fields
  // const [websiteLink, setWebsiteLink] = useState({ website_link: ''});
  const setWebsiteLink = useAppStore((state) => state.setWebsiteLink);
  const websiteLink = useAppStore((state) => state.websiteLink);
  
  // step 4
  // const [markdown, setMarkdown] = useState('')
  const setMarkdown = useAppStore((state) => state.setMarkdown);
  const addImageUrls = useAppStore((state) => state.addImageUrls);
  const setBrandStyle = useAppStore((state) => state.setBrandStyle);

  const [errors, setErrors]     = useState({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading]   = useState(false);
 
  const handleCredsChange = (e) => {
    setCreds(p => ({ ...p, [e.target.name]: e.target.value }));
    if (errors[e.target.name]) setErrors(p => ({ ...p, [e.target.name]: '' }));
  };
 
  const handleProfileChange = (e) => {
    setProfile(p => ({ ...p, [e.target.name]: e.target.value }));
    if (errors[e.target.name]) setErrors(p => ({ ...p, [e.target.name]: '' }));
  };

  // const handleWebsiteLinkChange = (e) => {
  //   setWebsiteLink(p => ({ ...p, [e.target.name]: e.target.value }));
  //   if (errors[e.target.name]) setErrors(p => ({ ...p, [e.target.name]: '' }));
  // };
  const handleWebsiteLinkChange = (e) => {
    setWebsiteLink({ [e.target.name]: e.target.value }); // Zustand merges it via spread internally
    if (errors[e.target.name]) setErrors(p => ({ ...p, [e.target.name]: '' }));
  };
  // Validate step 1
  const validateStep1 = () => {
    const errs = {};
    // if (!creds.username.trim())  errs.username  = 'Username is required.';
    if (!creds.email.trim())     errs.email     = 'Email is required.';
    else if (!/\S+@\S+\.\S+/.test(creds.email)) errs.email = 'Enter a valid email.';
    if (!creds.password)         errs.password  = 'Password is required.';
    else if (creds.password.length < 8) errs.password = 'Min 8 characters.';
    if (creds.password !== creds.password2) errs.password2 = 'Passwords do not match.';
    return errs;
  };
 
  // Validate step 2
  const validateStep2 = () => {
    const errs = {};
    if (!profile.first_name.trim()) errs.first_name = 'Your name is required.';
    if (!profile.category)          errs.category   = 'Please select a category.';
    return errs;
  };

  // Validate step 3
  const validateStep3 = () => {
    const errs = {};
    if (!websiteLink.website_link.trim()) errs.website_link = 'Website Link is required.';
    return errs;
  };
 
 
  const handleStep1Continue = () => {
    const errs = validateStep1();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setStep(2);
  };
 
  const handleStep2Continue = async () => {
    const errs = validateStep2();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setApiError('');
    setLoading(true);
 
    // Split full name for Django first_name / last_name
    const nameParts = profile.first_name.trim().split(' ');
    const first_name = nameParts[0] || '';
    const last_name  = nameParts.slice(1).join(' ') || '';
 
    try {
      await register({
        // username: creds.username,
        email: creds.email,
        password: creds.password,
        password2: creds.password2,
        first_name,
        last_name,
      });


      const workspace = await workspaceApi.create(`${profile.first_name.trim()}`);
      workspaceStorage.setActiveId(workspace.id);
      setStep(3);
      // navigate('/home', { replace: true });
    } catch (err) {
      // console.log('error');
      // console.log(err);
      const data = err.response?.data || {};
      const fieldErrors = {};
      ['email', 'password', 'password2', 'first_name', 'last_name'].forEach(f => {
        if (data[f]) fieldErrors[f] = Array.isArray(data[f]) ? data[f][0] : data[f];
      });
      if (Object.keys(fieldErrors).length) {
        setErrors(fieldErrors);
        // If the error is in step 1 fields, go back
        if (fieldErrors.username || fieldErrors.email || fieldErrors.password) setStep(1);
      } else {
        setApiError(data.detail || data.non_field_errors?.[0] || 'Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
      
    }
  };
  const user = JSON.parse(localStorage.getItem('user'));
  const hasFetched = useRef(false);

  const handleStep3Continue = async () => {
    const errs = validateStep3();

    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setApiError('');
    try {
      await contentEngineApi.saveOnboardingState({ website_url: websiteLink.website_link });
    } catch (error) {
      console.warn('Onboarding draft could not be saved.', error);
    }
    navigate('/business-profile-builder', { replace: true });
  };
 
  return (
    <Box className="voice-onboarding-page" sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* \u2500\u2500 Left panel \u2500\u2500 */}
      <Box sx={{
        width: { xs: '100%', md: '420px' }, flexShrink: 0,
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        px: { xs: 3, sm: 5.5 }, py: 6,
        bgcolor: 'rgba(255,255,255,0.78)',
        borderRight: { md: '1px solid rgba(17,24,39,0.08)' },
        backdropFilter: 'blur(18px)',
      }}>
 
        {/* Sign out / back link */}
        {/* <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 4 }}>
          {step === 1 ? (
            <Link component={RouterLink} to="/login" sx={{ fontSize: '0.85rem', color: '#64748b', textDecoration: 'none', '&:hover': { color: '#0f172a' } }}>
              Sign In
            </Link>
          ) : (
            <Link onClick={() => setStep(1)} sx={{ fontSize: '0.85rem', color: '#64748b', cursor: 'pointer', textDecoration: 'none', '&:hover': { color: '#0f172a' } }}>
              \u2190 Back
            </Link>
          )}
        </Box> */}
 
        <Box sx={{ mb: 3 }}>
          <BrandMark size={42} />
          <Typography sx={{ mt: 1.5, fontSize: 13, fontWeight: 900, color: '#7e22ce' }}>
            Voice Spark onboarding
          </Typography>
        </Box>

        {apiError && (
          <Alert severity="error" sx={{ mb: 2, borderRadius: '10px', fontSize: '0.84rem' }}>{apiError}</Alert>
        )}
 
        {/* \u2500\u2500 STEP 1: credentials \u2500\u2500 */}
        {step === 1 && (
          <>
            <Typography sx={{ fontWeight: 700, color: '#0f172a', fontSize: '1.6rem', letterSpacing: '-0.3px', mb: 0.5 }}>
              Create your account
            </Typography>
            <Typography sx={{ color: '#64748b', fontSize: '0.88rem', mb: 3.5 }}>
              Already have an account?{' '}
              <Link component={RouterLink} to="/login" sx={{ color: '#7e22ce', fontWeight: 800, textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>
                Sign in
              </Link>
            </Typography>
 
            {/* <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', mb: 0.4 }}>Username</Typography> */}
            {/* <TextField fullWidth name="username" placeholder="Username" value={creds.username}
              onChange={handleCredsChange} size="small" error={!!errors.username}
              helperText={errors.username} sx={inputSx} /> */}
 
            <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', mb: 0.4 }}>Email</Typography>
            <TextField fullWidth name="email" placeholder="Email" type="email" value={creds.email}
              onChange={handleCredsChange} size="small" error={!!errors.email}
              helperText={errors.email} sx={inputSx} />
 
            <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', mb: 0.4 }}>Password</Typography>
            <TextField fullWidth name="password" placeholder="Password (min 8 chars)" type="password"
              value={creds.password} onChange={handleCredsChange} size="small"
              error={!!errors.password} helperText={errors.password} sx={inputSx} />
 
            <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', mb: 0.4 }}>Confirm Password</Typography>
            <TextField fullWidth name="password2" placeholder="Confirm password" type="password"
              value={creds.password2} onChange={handleCredsChange} size="small"
              error={!!errors.password2} helperText={errors.password2} sx={{ ...inputSx, mb: 3 }} />
 
            <Button fullWidth onClick={handleStep1Continue} sx={{
              bgcolor: '#1f2328', color: '#fff', fontWeight: 900, fontSize: '0.92rem',
              py: 1.35, borderRadius: 999, textTransform: 'none',
              '&:hover': { bgcolor: '#111418' },
            }}>
              Continue
            </Button>
          </>
        )}
 
        {/* \u2500\u2500 STEP 2: onboarding \u2500\u2500 */}
        {step === 2 && (
          <>
            <Typography sx={{ fontWeight: 700, color: '#0f172a', fontSize: '1.75rem', letterSpacing: '-0.5px', lineHeight: 1.2, mb: 0.5 }}>
              Your content.{' '}
              <Box component="span" sx={{ display: 'block' }}>Every channel.</Box>
              <Box component="span" sx={{ display: 'block' }}>Starting today.</Box>
            </Typography>
            <Typography sx={{ color: '#64748b', fontSize: '0.88rem', mb: 4 }}>
              Let&apos;s personalize your experience.
            </Typography>
 
            {/* Full name */}
            <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', mb: 0.5 }}>
              Your full name
            </Typography>
            <TextField
              fullWidth
              name="first_name"
              placeholder="Your full name"
              value={profile.first_name}
              onChange={handleProfileChange}
              size="small"
              error={!!errors.first_name}
              helperText={errors.first_name}
              autoFocus
              sx={{
                mb: 2.5,
                '& .MuiOutlinedInput-root': {
                  borderRadius: '10px',
                  bgcolor: '#eef2ff',
                  fontSize: '0.9rem',
                  '& fieldset': { borderColor: '#c7d2fe' },
                  '&:hover fieldset': { borderColor: '#818cf8' },
                  '&.Mui-focused fieldset': { borderColor: '#6366f1', borderWidth: '2px' },
                },
                '& .MuiOutlinedInput-input': { py: 1.5 },
              }}
            />
 
            {/* Category */}
            <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', mb: 0.5 }}>
              Your business category
            </Typography>
            <FormControl fullWidth error={!!errors.category} sx={{ mb: 3.5 }}>
              <Select
                name="category"
                value={profile.category}
                onChange={handleProfileChange}
                onClose={() => {
                  window.requestAnimationFrame(() => {
                    if (document.activeElement instanceof HTMLElement) {
                      document.activeElement.blur();
                    }
                  });
                }}
                displayEmpty
                size="small"
                sx={selectSx}
                MenuProps={{
                  disableRestoreFocus: true,
                  MenuListProps: { autoFocusItem: false },
                }}
                renderValue={(val) => val || <Typography sx={{ color: '#94a3b8', fontSize: '0.9rem' }}>Select a category</Typography>}
              >
                {CATEGORIES.map(c => <MenuItem key={c} value={c} sx={{ fontSize: '0.88rem' }}>{c}</MenuItem>)}
              </Select>
              {errors.category && <FormHelperText>{errors.category}</FormHelperText>}
            </FormControl>
 
            <Button fullWidth onClick={handleStep2Continue} disabled={loading} sx={{
              bgcolor: '#1f2328', color: '#fff', fontWeight: 900,
              fontSize: '0.92rem', py: 1.35, borderRadius: 999, textTransform: 'none',
              '&:hover': { bgcolor: '#111418' },
            }}>
              {loading ? <CircularProgress size={19} sx={{ color: '#fff' }} /> : 'Continue'}
            </Button>
          </>
        )}

        {step === 3 && (
          <>
            <Typography sx={{ fontWeight: 700, color: '#0f172a', fontSize: '1.75rem', letterSpacing: '-0.5px', lineHeight: 1.2, mb: 0.5 }}>
              Your content.{' '}
              <Box component="span" sx={{ display: 'block' }}>Every channel.</Box>
              <Box component="span" sx={{ display: 'block' }}>Starting today.</Box>
            </Typography>
            <Typography sx={{ color: '#64748b', fontSize: '0.88rem', mb: 4 }}>
              Let&apos;s personalize your experience.
            </Typography>
 

            <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', mb: 0.5 }}>
              Insert Your Website Link
            </Typography>
            <TextField
              fullWidth
              name="website_link"
              placeholder="Website link"
              value={websiteLink.website_link}
              onChange={handleWebsiteLinkChange}
              size="small"
              error={!!errors.website_link}
              helperText={errors.website_link}
              autoFocus
              sx={{
                mb: 2.5,
                '& .MuiOutlinedInput-root': {
                  borderRadius: '10px',
                  bgcolor: '#eef2ff',
                  fontSize: '0.9rem',
                  '& fieldset': { borderColor: '#c7d2fe' },
                  '&:hover fieldset': { borderColor: '#818cf8' },
                  '&.Mui-focused fieldset': { borderColor: '#6366f1', borderWidth: '2px' },
                },
                '& .MuiOutlinedInput-input': { py: 1.5 },
              }}
            />
 
 
            <Button fullWidth onClick={handleStep3Continue} sx={{
              bgcolor: '#1f2328', color: '#fff', fontWeight: 900,
              fontSize: '0.92rem', py: 1.35, borderRadius: 999, textTransform: 'none',
              '&:hover': { bgcolor: '#111418' },
            }}>
              Continue
            </Button>
          </>
        )}
      </Box>
 
      {/* \u2500\u2500 Right panel \u2500\u2500 */}
      <CampaignsPreview />
      <AmbientWorking active={loading} title="Creating your workspace" detail="We are setting up your account. You can review the form while it runs." />
      {/* {step === 4 && (
          <>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {markdown}
          </ReactMarkdown>
          </>
        )} */}
    </Box>
  );
}
