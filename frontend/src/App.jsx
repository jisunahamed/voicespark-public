import React, { useState, lazy, Suspense } from 'react'; // ← Added lazy, Suspense
import { useEffect } from 'react';
// import './App.css';
import { useMemo } from 'react';
import TopBar from './TopBar';
import {
  Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText,
  Typography, AppBar, Toolbar, IconButton, Avatar, Chip, Card, CardContent,
  Button, Divider, Badge, LinearProgress, Stack, Paper, Tooltip, CircularProgress, // ← Added CircularProgress
} from '@mui/material';
import {
  Home, CalendarToday, CheckCircle, Article,
  Campaign, BarChart, Palette, Tune, Extension,
  Login
} from '@mui/icons-material';
import SideBar from './SideBar';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline, StyledEngineProvider } from '@mui/material';
import theme from './themes';
import { BrowserRouter, Routes, Route, useLocation, useNavigate, Navigate, HashRouter } from "react-router-dom";
import { Outlet } from "react-router-dom";
import { AuthProvider } from './views/login_register/auth_context';
import PrivateRoute from './views/login_register/private_route';
import { contentEngineApi } from './views/login_register/content_engine_api';
import { workspaceStorage } from './views/workspace/workSpaceAPi';
// import BusinessProfileBuilder from './views/login_register/profile_setup';
// import ConnectAccountsPage from './views/connect_accounts';

// Lazy load your pages - only import them once
const HomePage = lazy(() => import("./views/homepage"));
const LandingPage = lazy(() => import("./views/landing"));
const CalendarPage = lazy(() => import("./views/calendar"));
const ContentPlanPage = lazy(() => import("./views/content_plan"));
const CampaignDetailPage = lazy(() => import("./views/content_plan/detail"));
const InsightsPage = lazy(() => import('./views/insights'));
const ConnectAccountsPage = lazy(() => import('./views/connect_accounts'));
const LoginPage = lazy(() => import('./views/login_register/login'));
const RegisterPage = lazy(() => import('./views/login_register/register'));
const VoiceSparkEditor = lazy(() => import('./views/calendar/voice_spark_editor'));
const BusinessProfileBuilder = lazy(() => import('./views/login_register/profile_setup'));
const RecommendedVisualStyle = lazy(() => import('./views/login_register/recommended_visual_style'));
const BrandFontPage = lazy(() => import('./views/login_register/brand_font'));
const ContentPlanRegister = lazy(() => import('./views/login_register/content_plan'));
const CampaignPlannerPage = lazy(() => import('./views/login_register/campaign_planner'));
const ReviewTopicsPage = lazy(() => import('./views/login_register/review_topic'));
const ContentPreferences = lazy(() => import('./views/content_preference'));
const BrandKitPage = lazy(() => import('./views/brank_kit'));
const ApprovalsPage = lazy(() => import('./views/approvals'));
const Workspace = lazy(() => import('./views/workspace'));
const PrivacyPolicyPage = lazy(() => import('./views/legal/PrivacyPolicy'));
const TermsAndConditionsPage = lazy(() => import('./views/legal/TermsAndConditions'));
// // Placeholder for other pages (you can lazy load these too when you create them)
// const ApprovalsPage = lazy(() => import("./views/approvals"));
// const PaidAdsPage = lazy(() => import("./views/paid-ads"));
// const InsightsPage = lazy(() => import("./views/insights"));
// const BrandKitPage = lazy(() => import("./views/brand-kit"));
// const HomePage = lazy(() => import("./views/homepage"));
// const CalendarPage = lazy(() => import("./views/calendar"));
// // const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
// const ContentPlanPage = lazy(() => import("./views/content_plan"));

// ── HOME PAGE ─────────────────────────────────────────────────────────────────

// ── PLACEHOLDER PAGE ──────────────────────────────────────────────────────────
function PlaceholderPage({ title, emoji, description }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 400, textAlign: 'center' }}>
      <Typography fontSize={64} mb={2}>{emoji}</Typography>
      <Typography variant="h5" fontWeight={700} color="#1e1b4b" mb={1}>{title}</Typography>
      <Typography variant="body2" color="text.secondary" maxWidth={400}>{description}</Typography>
      <Button variant="contained" sx={{ mt: 3, background: '#7c3aed', borderRadius: 8, textTransform: 'none', fontWeight: 600, px: 4, boxShadow: 'none' }}>
        Get Started
      </Button>
    </Box>
  );
}


// ── PAGE ROUTER ───────────────────────────────────────────────────────────────
function getPageConfig(page) {
  const map = {
    'home': { title: 'Home', component: null },
    'calendar': { title: 'Calendar', component: null },
    'approvals': { title: 'Approvals', component: null },
    'content-plan': { title: 'Content Plan', component: <PlaceholderPage title="Content Plan" emoji="📋" description="Plan and schedule your content strategy for the weeks and months ahead." /> },
    'paid-ads': { title: 'Paid Ads', component: null },
    'insights': { title: 'Insights', component: null },
    'brand-kit': { title: 'Brand Kit', component: null },
    'content-prefs': { title: 'Content Preferences', component: <PlaceholderPage title="Content Preferences" emoji="⚙️" description="Customize how Voice Spark generates content to match your brand voice and goals." /> },
    'integrations': { title: 'Integrations', component: <PlaceholderPage title="Integrations" emoji="🔗" description="Connect your social media accounts, Google Drive, and more to unlock the full power of Voice Spark." /> },
  };
  return map[page] || map['home'];
}


// import { useSelector } from 'react-redux';



// // routing
// import Routes from './routes';

// // defaultTheme
// import theme from './themes';

// // project imports
// import NavigationScroll from './layout/NavigationScroll';

const LoadingFallback = () => (
  <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "400px" }}>
    <CircularProgress />
  </Box>
);


function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState('home');
  const config = getPageConfig(currentPage);

  useEffect(() => {
    let cancelled = false;
    const syncTimezone = async () => {
      const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const workspaceId = workspaceStorage.getActiveId();
      const user = JSON.parse(localStorage.getItem('user') || 'null');
      if (!browserTimezone || !workspaceId || !user?.id) return;
      const syncKey = `timezone_synced_${workspaceId}_${browserTimezone}`;
      if (sessionStorage.getItem(syncKey)) return;
      try {
        const { data } = await contentEngineApi.fetchContentPreferences();
        if (cancelled) return;
        const preferences = data?.data || {};
        if (preferences.timezone === browserTimezone) {
          sessionStorage.setItem(syncKey, '1');
          return;
        }
        await contentEngineApi.updateContentPreferences({
          ...preferences,
          timezone: browserTimezone,
        });
        sessionStorage.setItem(syncKey, '1');
      } catch (error) {
        console.warn("Timezone sync skipped", error);
      }
    };
    syncTimezone();
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  useEffect(() => {
    let cancelled = false;
    const guardOnboarding = async () => {
      const workspaceId = workspaceStorage.getActiveId();
      const user = JSON.parse(localStorage.getItem('user') || 'null');
      if (!workspaceId || !user?.id) return;
      try {
        const { data } = await contentEngineApi.fetchOnboardingState();
        if (cancelled) return;
        const onboarding = data?.onboarding;
        if (onboarding && !onboarding.complete && onboarding.route) {
          navigate(onboarding.route, { replace: true });
        }
      } catch (error) {
        console.warn("Onboarding guard skipped", error);
      }
    };
    guardOnboarding();
    return () => {
      cancelled = true;
    };
  }, [location.pathname, navigate]);

  return (
    <Box className="crm-refresh-shell" sx={{ display: 'flex', maxWidth: '100%', minHeight: '100vh', overflow: 'hidden' }}>
      <SideBar />
      {/* <TopBar title={config.title} /> */}
      <Box component="main" sx={{
        flexGrow: 1,
        px: { xs: 2, sm: 3, lg: 5 },
        py: { xs: 2.5, md: 4 },
        // margin:10,
        mt: '56px',
        minHeight: '100vh',
        background:
          'radial-gradient(circle at 82% 0%, rgba(168,85,247,0.24) 0, rgba(168,85,247,0) 24%), linear-gradient(135deg,#f7faf8 0%,#f5f1e8 52%,#edf7f4 100%)',
        maxWidth: '100%',
        overflow: 'auto',
      }}>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Navigate to="/home" replace />} />
            <Route path="/VoiceSpark" element={<Navigate to="/home" replace />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/integrations" element={<ConnectAccountsPage />} />
            <Route path="/content-plan" element={<ContentPlanPage />} />
            <Route path="/content-plan/:weekId" element={<CampaignDetailPage />} />
            <Route path="/insights" element={<InsightsPage />} />
            <Route path="/content-preference" element={<ContentPreferences />} />
            <Route path="/brand-kit" element={<BrandKitPage />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
          </Routes>
        </Suspense>
      </Box>
    </Box>
  );
}





function App() {
  const appTheme = useMemo(() => theme({}), []);
  
  return (
    <StyledEngineProvider>
      <ThemeProvider theme={appTheme}>
        <CssBaseline />
        <AuthProvider>
          <BrowserRouter basename='/'>
            <Routes>
              {/* Standalone routes — no sidebar/topbar */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/landing" element={<LandingPage />} />
              <Route path="/privacy" element={<PrivacyPolicyPage />} />
              <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
              <Route path="/terms" element={<TermsAndConditionsPage />} />
              <Route path="/terms-and-conditions" element={<TermsAndConditionsPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/business-profile-builder" element={<BusinessProfileBuilder />} />
              <Route path="/visual-style" element={<Navigate to="/recommended-visual-style" replace />} />
              <Route path="/recommended-visual-style" element={<RecommendedVisualStyle />} />
              <Route path="/brand-font" element={<BrandFontPage />} />
              <Route path="/content-plan-register" element={<ContentPlanRegister />} />
              <Route path="/campaign-planner" element={<CampaignPlannerPage />} />
              <Route path="/review-topic" element={<ReviewTopicsPage />} />
              <Route path="/blog-email-plan" element={<Navigate to="/review-topic" replace />} />
              <Route path="/generate-first-week" element={<Navigate to="/home" replace />} />

              <Route element={<PrivateRoute />}>
                <Route path="/workspace" element={<Workspace />} />
                <Route path="/voice-spark-editor/:id" element={<VoiceSparkEditor />} />

                {/* Shell routes — with sidebar/topbar */}
                <Route path="/*" element={<AppShell />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </StyledEngineProvider>
  );
}



// const App = () => {
//     const customization = useSelector((state) => state.customization);

//     return (

//         <StyledEngineProvider injectFirst>
//             <ThemeProvider theme={theme(customization)}>
//                 <CssBaseline />
//                 <NavigationScroll>
//                     <Routes />
//                 </NavigationScroll>
//             </ThemeProvider>
//         </StyledEngineProvider>
//     );
// };

export default App
