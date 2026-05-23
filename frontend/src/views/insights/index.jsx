import { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  Avatar,
  Stack,
} from "@mui/material";
import CalendarTodayOutlinedIcon from "@mui/icons-material/CalendarTodayOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import LinkedInIcon from "@mui/icons-material/LinkedIn";
import PersonAddAltIcon from "@mui/icons-material/PersonAddAlt";

import IconX from "@mui/icons-material/X";

import FacebookIcon from "@mui/icons-material/Facebook";
import { Instagram  } from "@mui/icons-material";
import TopBar from "../../TopBar";
import config from "../../config";
import { workspaceStorage } from "../workspace/workSpaceAPi";
import api from "../login_register/axios_client";
import { useNavigate } from "react-router-dom";
// ── Data ──────────────────────────────────────────────────────────────────────

const steps = [
  { id: 1, label: "Connect your social media accounts to get started", action: "Connect Accounts", active: true, path: "/integrations" },
  { id: 2, label: "Add Content Preferences to improve your content", action: "Review Preferences", active: false, path: "/content-preference" },
  { id: 3, label: "Add source materials & sync Google Drive", action: "Open Source Materials", active: false, path: "/brand-kit" },
  // { id: 4, label: "Upload brand images & videos", action: "Upload Assets", active: false },
];

const metrics = ["Impressions", "Impressions", "Impressions"];
const handleXConnect = () => {
    // Just redirect to Django which handles the OAuth flow
    // window.location.href = config.API_SERVER+"/auth/x/login/";
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const params = new URLSearchParams({ user_id: user.id, workspace_id:workspaceId });
    window.open(
    config.API_SERVER + "auth/x/login/?" + params.toString(),
    "X Login",
    "width=600,height=700,scrollbars=yes,resizable=yes"
    );
};
const handleLinkedInConnect = () => {
    // Just redirect to Django which handles the OAuth flow
    // window.location.href = config.API_SERVER+"/auth/x/login/";
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const params = new URLSearchParams({ user_id: user.id, workspace_id:workspaceId });
    window.open(
    config.API_SERVER + "auth/linkedin/login/?" + params.toString(),
    "X Login",
    "width=600,height=700,scrollbars=yes,resizable=yes"
    );
};
const handleFacebookConnect = () => {
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const params = new URLSearchParams({ platform: "facebook", user_id: user.id, workspace_id:workspaceId });
    window.open(
    config.API_SERVER + "auth/fb/login/?" + params.toString(),
    "X Login",
    "width=600,height=700,scrollbars=yes,resizable=yes"
    );
};

const handleInstagramConnect = () => {
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const params = new URLSearchParams({ platform: "instagram", user_id: user.id, workspace_id:workspaceId });
    window.open(
        config.API_SERVER + "auth/fb/login/?" + params.toString(),
        "X Login",
        "width=600,height=700,scrollbars=yes,resizable=yes"
    );
};

const platforms = [
  {
    key: "x",
    title: "X Performance",
    icon: <IconX sx={{ fontSize: 28, color: "#fff" }} />,
    avatarBg: "#000",
    connectLabel: "Connect X",
    handleConnect: handleXConnect,
    metrics: ["Impressions", "Engagements", "Followers"],
  },
  {
    key: "linkedin",
    title: "LinkedIn Performance",
    icon: <LinkedInIcon sx={{ fontSize: 28, color: "#fff" }} />,
    avatarBg: "#0a66c2",
    connectLabel: "Connect LinkedIn",
    handleConnect: handleLinkedInConnect,
    metrics: ["Views", "Reactions", "Connections"],
  },

  {
    key: "facebook",
    title: "Facebook Performance",
    icon: <FacebookIcon sx={{ fontSize: 28, color: "#fff" }} />,
    avatarBg: "#1877f2",
    connectLabel: "Connect Facebook",
    handleConnect: handleFacebookConnect,
    metrics: ["Reach", "Likes", "Followers"],
    },
      {
    key: "instagram",
    title: "Instagram Performance",
    icon: <Instagram sx={{ fontSize: 28, color: "#fff" }} />,
    avatarBg: "#e1306c",
    connectLabel: "Connect Instagram",
    handleConnect: handleInstagramConnect,
    metrics: ["Reach", "Likes", "Followers"],
  },
];

export default function InsightsPage() {
    const navigate = useNavigate();
    const [period, setPeriod] = useState("7days");
    const [insights, setInsights] = useState({});
    const [loadingInsights, setLoadingInsights] = useState(true);

    useEffect(() => {
      const fetchInsights = async () => {
        try {
          const user = JSON.parse(localStorage.getItem('user') || 'null');
          const workspaceId = workspaceStorage.getActiveId();
          if (!user?.id || !workspaceId) return;
          const { data } = await api.post("/auth/user/social-insights/", {
            user_id: user.id,
            workspace_id: workspaceId,
          });
          setInsights(data.data || {});
        } catch (error) {
          console.error("Failed to load social insights:", error);
        } finally {
          setLoadingInsights(false);
        }
      };
      fetchInsights();
    }, []);

  return (
    <Box>
      <TopBar title={'Insight'}/>
      <Box sx={{ bgcolor: "#f5f6f8", minHeight: "100vh", p: 4 }}>
        <Box sx={{ maxWidth: 860, mx: "auto", display: "flex", flexDirection: "column", gap: 3 }}>

          {/* ── Learning Loop Card ── */}
          <Card sx={{ borderRadius: 3, boxShadow: "0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" }}>
            <CardContent sx={{ p: 3.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2.5 }}>
                <Typography variant="h6" fontWeight={700} letterSpacing="-0.2px">
                  Enable the Learning Loop
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate("/calendar")}
                  startIcon={<CalendarTodayOutlinedIcon sx={{ fontSize: 16 }} />}
                  sx={{
                    textTransform: "none",
                    borderColor: "#e0e3e8",
                    color: "#444",
                    fontSize: 13,
                    fontWeight: 500,
                    borderRadius: 2,
                    "&:hover": { borderColor: "#c0c4cc", bgcolor: "#fafafa" },
                  }}
                >
                  Open Calendar
                </Button>
              </Box>

              <Stack divider={<Divider />}>
                {steps.map((step) => (
                  <Box key={step.id} sx={{ display: "flex", alignItems: "center", gap: 2, py: 1.75 }}>
                    <Avatar
                      sx={{
                        width: 28,
                        height: 28,
                        fontSize: 13,
                        fontWeight: 700,
                        bgcolor: step.active ? "#0f1117" : "#eaecf0",
                        color: step.active ? "#fff" : "#555",
                        flexShrink: 0,
                      }}
                    >
                      {step.id}
                    </Avatar>
                    <Typography sx={{ flex: 1, fontSize: 14, color: "text.primary" }}>
                      {step.label}
                    </Typography>
                    <Button
                      onClick={() => navigate(step.path)}
                      endIcon={<ArrowForwardIcon sx={{ fontSize: 15 }} />}
                      sx={{
                        textTransform: "none",
                        fontSize: 13,
                        fontWeight: 600,
                        color: "primary.main",
                        p: 0,
                        minWidth: "auto",
                        "&:hover": { background: "none", textDecoration: "underline" },
                      }}
                    >
                      {step.action}
                    </Button>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>

          {platforms.map(({ key, title, icon, avatarBg, connectLabel, handleConnect, metrics }) => {
            const platformInsight = insights[key] || {};
            const connected = Boolean(platformInsight.connected);
            const metricEntries = Object.entries(platformInsight.metrics || {});
            const visibleMetrics = connected && metricEntries.length
              ? metricEntries
              : metrics.map((label) => [label, loadingInsights ? "..." : 0]);
            return (
              <Card
                  key={key}
                  sx={{ borderRadius: 3, boxShadow: "0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)" }}
              >
                  <CardContent sx={{ p: 3.5 }}>
                  {/* Header */}
                  <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
                      <Typography variant="h6" fontWeight={700} letterSpacing="-0.2px">
                      {title}
                      </Typography>
                      <ToggleButtonGroup
                      value={period}
                      exclusive
                      onChange={(_, v) => v && setPeriod(v)}
                      size="small"
                      sx={{
                          bgcolor: "#f0f1f4",
                          borderRadius: "8px",
                          p: "3px",
                          "& .MuiToggleButtonGroup-grouped": { mx: 0 },
                      }}
                      >
                      {["7days", "30days"].map((val, i) => (
                          <ToggleButton
                          key={val}
                          value={val}
                          sx={{
                              textTransform: "none",
                              fontSize: 12,
                              fontWeight: 500,
                              border: "none",
                              borderRadius: "6px !important",
                              px: 1.5,
                              py: 0.5,
                              color: "#6b7280",
                              "&.Mui-selected": {
                              bgcolor: "#fff",
                              color: "#0f1117",
                              fontWeight: 700,
                              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                              "&:hover": { bgcolor: "#fff" },
                              },
                          }}
                          >
                          {i === 0 ? "7 Days" : "30 Days"}
                          </ToggleButton>
                      ))}
                      </ToggleButtonGroup>
                  </Box>

                  <Box sx={{ display: "flex", gap: 2, mb: 4, filter: connected ? "none" : "blur(4px)", pointerEvents: connected ? "auto" : "none", userSelect: connected ? "auto" : "none" }}>
                      {visibleMetrics.map(([label, value], i) => (
                      <Box key={i} sx={{ flex: 1, bgcolor: "#f8f9fb", borderRadius: 2.5, p: 2.5 }}>
                          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 0.5 }}>{label}</Typography>
                          <Typography sx={{ fontSize: 22, fontWeight: 700, color: "#22c55e" }}>{value}</Typography>
                      </Box>
                      ))}
                  </Box>

                  <Stack alignItems="center" spacing={1.5}>
                      <Avatar
                      variant="rounded"
                      sx={{ width: 48, height: 48, bgcolor: avatarBg, borderRadius: "10px" }}
                      >
                      {icon}
                      </Avatar>
                      <Typography sx={{ fontSize: 14, fontWeight: 500, color: "text.primary" }}>
                      {connected
                        ? `${platformInsight.account_name || title.split(" ")[0]} connected`
                        : `Connect ${title.split(" ")[0]} account to get insights`}
                      </Typography>
                      {!connected && (
                        <Button
                        variant="outlined"
                        startIcon={<PersonAddAltIcon sx={{ fontSize: 16 }} />}
                        sx={{
                            textTransform: "none",
                            borderColor: "#d1d5db",
                            color: "#0f1117",
                            fontSize: 13,
                            fontWeight: 600,
                            borderRadius: 2,
                            px: 2.5,
                            py: 1,
                            boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
                            "&:hover": { borderColor: "#9ca3af", bgcolor: "#fafafa" },
                        }}
                        onClick={handleConnect}
                        >
                        {connectLabel}
                        </Button>
                      )}
                  </Stack>
                  </CardContent>
              </Card>
              );
            })}
          
          
        </Box>
      </Box>
    </Box>
  );
}
