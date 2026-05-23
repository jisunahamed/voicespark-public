import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Button,
  Chip,
  Divider,
  IconButton,
  Avatar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
  Link,
} from "@mui/material";
import TopBar from "../../TopBar";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import CalendarTodayOutlinedIcon from "@mui/icons-material/CalendarTodayOutlined";
import SyncAltIcon from "@mui/icons-material/SyncAlt";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BarChartIcon from "@mui/icons-material/BarChart";
import LinkedInIcon from "@mui/icons-material/LinkedIn";
import FacebookIcon from "@mui/icons-material/Facebook";
import YouTubeIcon from "@mui/icons-material/YouTube";
import InstagramIcon from "@mui/icons-material/Instagram";
import XIcon from "@mui/icons-material/X";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import ArticleIcon from "@mui/icons-material/Article";
import config from "../../config";
import { workspaceStorage } from "../workspace/workSpaceAPi";
import api from "../login_register/axios_client";
import { contentEngineApi } from "../login_register/content_engine_api";

// -- Platform icon helpers ----------------------------------------------
const GoogleAnalyticsIcon = () => (
  <Box
    sx={{
      width: 28,
      height: 28,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <BarChartIcon sx={{ color: "#F9AB00", fontSize: 22 }} />
  </Box>
);

const TikTokIcon = () => (
  <Box
    sx={{
      width: 28,
      height: 28,
      bgcolor: "#000",
      borderRadius: "6px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <Typography sx={{ fontSize: 14, color: "#fff", fontWeight: 700, lineHeight: 1 }}>
      T
    </Typography>
  </Box>
);

const BlogIcon = () => (
  <Box
    sx={{
      width: 28,
      height: 28,
      bgcolor: "#21759b", // WordPress blue
      borderRadius: "6px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <ArticleIcon sx={{ color: "#fff", fontSize: 18 }} />
  </Box>
);

const MailchimpIcon = () => (
  <Box
    sx={{
      width: 28,
      height: 28,
      bgcolor: "#FFE01B",
      borderRadius: "6px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <Typography sx={{ fontSize: 12, color: "#000", fontWeight: 700 }}>M</Typography>
  </Box>
);

const GoogleIcon = () => (
  <Box
    sx={{
      width: 28,
      height: 28,
      border: "1.5px solid #e0e0e0",
      borderRadius: "6px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      bgcolor: "#fff",
    }}
  >
    <Typography sx={{ fontSize: 13, fontWeight: 700, color: "#4285F4" }}>G</Typography>
  </Box>
);

// -- Step badge -------------------------------------------------------- 
const StepBadge = ({ n }) => (
  <Box
    sx={{
      width: 26,
      height: 26,
      borderRadius: "50%",
      bgcolor: "#111",
      color: "#fff",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 12,
      fontWeight: 700,
      flexShrink: 0,
    }}
  >
    {n}
  </Box>
);

// -- Platform row ------------------------------------------------------ 
const PlatformRow = ({ step, icon, name, tag, error, actions }) => (
  <Box
    sx={{
      display: "flex",
      alignItems: "center",
      gap: 1.5,
      py: 1.5,
      px: 0,
    }}
  >
    <StepBadge n={step} />
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1, minWidth: 0 }}>
      {icon}
      <Box sx={{ minWidth: 0 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography sx={{ fontSize: 14, fontWeight: 500, color: "#111" }}>{name}</Typography>
          {tag && (
            <Typography sx={{ fontSize: 12, color: error ? "#b45309" : "#888" }}>{tag}</Typography>
          )}
        </Box>
        {error && (
          <Typography sx={{ fontSize: 11, color: "#b45309", maxWidth: 360, lineHeight: 1.35 }}>
            {error}
          </Typography>
        )}
      </Box>
    </Box>
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>{actions}</Box>
  </Box>
);

// -- Connect button ---------------------------------------------------- 
const ConnectBtn = ({ dark, onClick, connected = false, reconnect = false }) => (
  <Button
    variant={connected || dark ? "contained" : "outlined"}
    size="small"
    startIcon={<SyncAltIcon sx={{ fontSize: 14 }} />}
    onClick={onClick}
    sx={{
      textTransform: "none",
      fontSize: 13,
      fontWeight: 600,
      borderRadius: "8px",
      px: 2,
      py: 0.75,
      ...(connected
        ? {
          bgcolor: "#16a34a",
          color: "#fff",
          "&:hover": { bgcolor: "#15803d" },
          boxShadow: "none",
        }
        : dark
        ? {
          bgcolor: "#111",
          color: "#fff",
          "&:hover": { bgcolor: "#333" },
          boxShadow: "none",
        }
        : {
          borderColor: "#d1d5db",
          color: "#111",
          "&:hover": { borderColor: "#999", bgcolor: "#fafafa" },
        }),
    }}
  >
    {reconnect ? "Reconnect" : connected ? "Connected" : "Connect"}
  </Button>
);

// -- Switch Platform button -------------------------------------------- 
const SwitchBtn = () => (
  <Button
    variant="outlined"
    size="small"
    endIcon={<span style={{ fontSize: 10 }}>v</span>}
    sx={{
      textTransform: "none",
      fontSize: 13,
      fontWeight: 500,
      borderRadius: "8px",
      px: 2,
      py: 0.75,
      borderColor: "#d1d5db",
      color: "#111",
      "&:hover": { borderColor: "#999", bgcolor: "#fafafa" },
    }}
  >
    Switch Platform
  </Button>
);

// -- Small pill chip for available platforms ----------------------------
const PlatformChip = ({ icon, label, onClick }) => (
  <Chip
    icon={icon}
    label={label}
    onClick={onClick}
    variant="outlined"
    sx={{
      borderRadius: "8px",
      borderColor: "#e0e0e0",
      fontSize: 13,
      fontWeight: 500,
      color: "#111",
      bgcolor: "#fff",
      px: 0.5,
      "& .MuiChip-icon": { ml: "6px" },
      "&:hover": { bgcolor: "#f5f5f5", borderColor: "#bbb" },
      cursor: "pointer",
    }}
  />
);

// -- Section label ------------------------------------------------------
const SectionLabel = ({ children }) => (
  <Typography
    sx={{ fontSize: 12, fontWeight: 600, color: "#888", letterSpacing: "0.04em", mb: 1 }}
  >
    {children}
  </Typography>
);
// -- Main page ----------------------------------------------------------
export default function ConnectAccountsPage() {
  const [connected, setConnected] = useState({});
  const [connectionErrors, setConnectionErrors] = useState({});
  const [selectedPlatforms, setSelectedPlatforms] = useState(["facebook", "instagram", "linkedin", "x"]);
  const [wpModalOpen, setWpModalOpen] = useState(false);
  const [wpForm, setWpForm] = useState({ site_url: "", username: "", password: "" });
  const [wpLoading, setWpLoading] = useState(false);
  const [wpError, setWpError] = useState("");
  const [liPagesModalOpen, setLiPagesModalOpen] = useState(false);
  const [linkedinPages, setLinkedinPages] = useState([]);
  const [liLoading, setLiLoading] = useState(false);

  const handleXConnect = () => {
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const params = new URLSearchParams({ user_id: user.id, workspace_id: workspaceId });
    window.open(
      config.API_SERVER + "auth/x/login/?" + params.toString(),
      "X Login",
      "width=600,height=700,scrollbars=yes,resizable=yes"
    );
  };

  const handleLinkedInConnect = () => {
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const params = new URLSearchParams({ user_id: user.id, workspace_id: workspaceId });
    window.open(
      config.API_SERVER + "auth/linkedin/login/?" + params.toString(),
      "LinkedIn Login",
      "width=600,height=700,scrollbars=yes,resizable=yes"
    );
  };

  const handleFacebookConnect = () => {
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const params = new URLSearchParams({ platform: "facebook", user_id: user.id, workspace_id: workspaceId });
    window.open(
      config.API_SERVER + "auth/fb/login/?" + params.toString(),
      "Facebook Login",
      "width=600,height=700,scrollbars=yes,resizable=yes"
    );
  };

  const handleInstagramConnect = () => {
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const params = new URLSearchParams({ platform: "instagram", user_id: user.id, workspace_id: workspaceId });
    window.open(
      config.API_SERVER + "auth/fb/login/?" + params.toString(),
      "Instagram Login",
      "width=600,height=700,scrollbars=yes,resizable=yes"
    );
  };


  const handleWpSubmit = async () => {
    setWpLoading(true);
    setWpError("");
    const workspaceId = workspaceStorage.getActiveId();
    try {
      await api.post("/auth/wordpress/connect/", {
        ...wpForm,
        workspace_id: workspaceId
      });
      setWpModalOpen(false);
      refreshConnectedAccounts();
    } catch (error) {
      setWpError(error.response?.data?.error || "Failed to connect to WordPress");
    } finally {
      setWpLoading(false);
    }
  };

  const handleDownloadPlugin = () => {
    window.open(config.API_SERVER + "auth/wordpress/download-plugin/", "_blank");
  };

  const fetchLinkedinPages = async () => {
    const workspaceId = workspaceStorage.getActiveId();
    if (!workspaceId) return;
    try {
      const { data } = await api.get(`/auth/linkedin/pages/?workspace_id=${workspaceId}`);
      setLinkedinPages(data.pages || []);
      // If LinkedIn is connected but no page is selected, prompt user
      const isConnected = connected.linkedin;
      if (isConnected && data.pages?.length > 0 && !data.pages.some(p => p.is_selected)) {
        setLiPagesModalOpen(true);
      }
    } catch (error) {
      console.error("Failed to fetch LinkedIn pages:", error);
    }
  };

  const handleSelectLiPage = async (pageId) => {
    setLiLoading(true);
    const workspaceId = workspaceStorage.getActiveId();
    try {
      await api.post("/auth/linkedin/select-page/", { page_id: pageId, workspace_id: workspaceId });
      setLiPagesModalOpen(false);
      refreshConnectedAccounts();
      fetchLinkedinPages();
    } catch (error) {
      console.error("Failed to select LinkedIn page:", error);
    } finally {
      setLiLoading(false);
    }
  };

  const refreshConnectedAccounts = async () => {
    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    if (!user?.id || !workspaceId) return;
    try {
      const { data } = await api.post("/auth/user/social-insights/", {
        user_id: user.id,
        workspace_id: workspaceId,
      });
      const next = {};
      const errors = {};
      Object.entries(data.data || {}).forEach(([key, value]) => {
        next[key] = Boolean(value?.connected);
        if (value?.error) errors[key] = value.error;
      });

      try {
        const metaRes = await api.post("/auth/fb/connected-accounts/", {
          user_id: user.id,
          workspace_id: workspaceId,
        });
        next.facebook = Boolean(metaRes.data?.facebook);
        next.instagram = Boolean(metaRes.data?.instagram);
        next.twitter = Boolean(metaRes.data?.twitter);
        next.linkedin = Boolean(metaRes.data?.linkedin);
        Object.assign(errors, metaRes.data?.connection_errors || {});
      } catch (e) {
        console.error("Meta connected account validation failed", e);
      }

      // Also check WP status
      try {
        const wpRes = await api.post("/auth/wordpress/status/", { workspace_id: workspaceId });
        next["wordpress"] = Boolean(wpRes.data?.connected);
      } catch (e) {
        console.error("WP status check failed", e);
      }

      setConnected(next);
      setConnectionErrors(errors);
      if (next.linkedin) {
        fetchLinkedinPages();
      }
    } catch (error) {
      console.error("Failed to refresh connected accounts:", error);
    }
  };

  useEffect(() => {
    refreshConnectedAccounts();
    contentEngineApi.fetchContentPlan()
      .then(({ data }) => {
        const platforms = data?.content_plan?.platforms;
        if (Array.isArray(platforms) && platforms.length) setSelectedPlatforms(platforms);
      })
      .catch((error) => console.error("Failed to fetch content plan:", error));
    const handleMessage = (event) => {
      if ([
        "fb_login_success",
        "linkedin_login_success",
        "x_oauth1_success",
        "x_login_success",
      ].includes(event.data)) {
        refreshConnectedAccounts();
        if (event.data === "linkedin_login_success") {
            setTimeout(fetchLinkedinPages, 1000); // Give backend a moment to process ACLs
        }
      }
    };
    window.addEventListener("message", handleMessage);
    window.addEventListener("focus", refreshConnectedAccounts);
    return () => {
      window.removeEventListener("message", handleMessage);
      window.removeEventListener("focus", refreshConnectedAccounts);
    };
  }, []);

  const platformConnected = (key) => {
    if (key === "x") return Boolean(connected.x || connected.twitter);
    return Boolean(connected[key]);
  };
  const platformConnectionError = (key) => {
    if (key === "x") return connectionErrors.x || connectionErrors.twitter || "";
    return connectionErrors[key] || "";
  };
  const selectedConnectedCount = selectedPlatforms.filter(platformConnected).length;
  const totalCount = selectedPlatforms.length || 4;
  const allSocialRows = [
    { key: "linkedin", name: "LinkedIn", icon: <LinkedInIcon sx={{ color: "#0a66c2" }} />, connect: handleLinkedInConnect },
    { key: "facebook", name: "Facebook", icon: <FacebookIcon sx={{ color: "#1877f2" }} />, connect: handleFacebookConnect },
    { key: "instagram", name: "Instagram", icon: <InstagramIcon sx={{ color: "#E4405F" }} />, connect: handleInstagramConnect },
    { key: "x", name: "X/Twitter", icon: <XIcon sx={{ color: "#111" }} />, connect: handleXConnect },
  ];
  const socialRows = allSocialRows.filter((row) => selectedPlatforms.includes(row.key));
  const availableRows = allSocialRows.filter((row) => !selectedPlatforms.includes(row.key));

  return (
    <Box>
      <TopBar title={'Integrations'} />
      <Box
        sx={{
          maxWidth: 680,
          mx: "auto",
          py: 5,
          px: { xs: 2, sm: 4 },
          fontFamily: "'DM Sans', sans-serif",
        }}
      >
        {/* -- Header -- */}
        <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 3 }}>
          <Box>
            <Typography
              sx={{ fontSize: 22, fontWeight: 700, color: "#111", letterSpacing: "-0.3px", mb: 0.5 }}
            >
              Connect your accounts to automate your marketing
            </Typography>
            <Typography sx={{ fontSize: 14, color: "#666" }}>
                Voice Spark posts your content, learns from performance, and generates content based on those insights.
            </Typography>
          </Box>
          {/* Progress badge */}
          <Box
            sx={{
              width: 52,
              height: 52,
              borderRadius: "50%",
              border: "2.5px solid #22c55e",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              ml: 3,
            }}
          >
            <Typography sx={{ fontSize: 13, fontWeight: 700, color: "#22c55e" }}>
              {selectedConnectedCount}/{totalCount}
            </Typography>
          </Box>
        </Box>


        {/* -- In your Content Plan -- */}
        <Typography sx={{ fontSize: 16, fontWeight: 700, color: "#111", mb: 0.5 }}>
          In your Content Plan
        </Typography>
        <Typography sx={{ fontSize: 13, color: "#888", mb: 2 }}>
          Autopilot will create and autopost content for these channels
        </Typography>

        <Box
          sx={{
            px: 2.5,
            mb: 4,
          }}
        >
          {/* Social Media */}
          <SectionLabel>Social Media</SectionLabel>
          {socialRows.map((row, index) => (
            <React.Fragment key={row.key}>
              <PlatformRow
                step={index + 1}
                icon={row.icon}
                name={row.name}
                tag={
                  platformConnectionError(row.key)
                    ? "Reconnect required"
                    :
                  platformConnected(row.key) 
                    ? (row.key === "linkedin" && linkedinPages.find(p => p.is_selected))
                      ? `Connected to ${linkedinPages.find(p => p.is_selected).name}`
                      : "Connected" 
                    : `0 connected / 1 selected`
                }
                error={platformConnectionError(row.key)}
                actions={
                  <Box sx={{ display: "flex", gap: 1 }}>
                    {row.key === "linkedin" && platformConnected("linkedin") && (
                      <Button 
                        size="small" 
                        variant="text" 
                        onClick={() => setLiPagesModalOpen(true)}
                        sx={{ textTransform: "none", fontSize: 12 }}
                      >
                        Change Page
                      </Button>
                    )}
                    <ConnectBtn
                      onClick={row.connect}
                      connected={platformConnected(row.key)}
                      reconnect={Boolean(platformConnectionError(row.key))}
                    />
                  </Box>
                }
              />
              {index < socialRows.length - 1 && <Divider sx={{ borderColor: "#f0f0f0" }} />}
            </React.Fragment>
          ))}

          {!socialRows.length && (
            <Typography sx={{ fontSize: 13, color: "#888", py: 2 }}>No social platforms selected in your content plan.</Typography>
          )}

          {/* Blog Integration */}
          <Box sx={{ mt: 3 }}>
            <SectionLabel>Blog Integration</SectionLabel>
          </Box>
          <PlatformRow
            step={socialRows.length + 1}
            icon={<BlogIcon />}
            name="WordPress"
            tag={connected.wordpress ? "Connected" : "Self-hosted WordPress site"}
            actions={
              <>
                <Button
                  size="small"
                  variant="text"
                  startIcon={<CloudDownloadIcon />}
                  onClick={handleDownloadPlugin}
                  sx={{ textTransform: "none", fontSize: 13, mr: 1 }}
                >
                  Plugin
                </Button>
                <ConnectBtn 
                  onClick={() => connected.wordpress ? api.post("/auth/wordpress/disconnect/", { workspace_id: workspaceStorage.getActiveId() }).then(refreshConnectedAccounts) : setWpModalOpen(true)} 
                  connected={connected.wordpress} 
                />
              </>
            }
          />
          <Divider sx={{ borderColor: "#f0f0f0" }} />
        </Box>

        {/* -- Available to add -- */}
        <Typography sx={{ fontSize: 16, fontWeight: 700, color: "#111", mb: 2 }}>
          Available to add to your Content Plan
        </Typography>

        <SectionLabel>Social media</SectionLabel>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 3 }}>
          {availableRows.map((row) => (
            <Button
              key={row.key}
              variant="outlined"
              startIcon={row.icon}
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
              onClick={row.connect}
            >
              {platformConnected(row.key) ? `${row.name} Connected` : row.name}
            </Button>
          ))}
          {!availableRows.length && (
            <Typography sx={{ fontSize: 13, color: "#888" }}>All supported social platforms are already in this content plan.</Typography>
          )}

        </Box>
      </Box>

      {/* WordPress Connection Modal */}
      <Dialog open={wpModalOpen} onClose={() => !wpLoading && setWpModalOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Connect WordPress Site</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 13, color: "#555", mb: 1.5, lineHeight: 1.45 }}>
            Enter your WordPress admin login URL and an application password for the admin user that will publish posts.
          </Typography>
          <Box sx={{ mb: 2, p: 1.5, bgcolor: "#f8fafc", border: "1px solid #e5e7eb", borderRadius: 1.5 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#111", mb: 0.75 }}>
              How to create the password
            </Typography>
            <Typography component="ol" sx={{ pl: 2, m: 0, color: "#60646c", fontSize: 11.5, lineHeight: 1.55 }}>
              <li>Open your WordPress admin panel, usually <b>your-site.com/wp-admin</b>.</li>
              <li>Log in with the WordPress admin username you want VoiceSpark to use.</li>
              <li>Go to <b>Users</b>, open that user profile, then find <b>Application Passwords</b>.</li>
              <li>Create a new application password, then paste that generated password here.</li>
            </Typography>
          </Box>
          
          <TextField
            fullWidth
            label="WordPress admin URL"
            placeholder="https://your-site.com/wp-admin"
            variant="outlined"
            size="small"
            margin="dense"
            value={wpForm.site_url}
            onChange={(e) => setWpForm({ ...wpForm, site_url: e.target.value })}
            disabled={wpLoading}
            helperText="You can paste /wp-admin or /wp-login.php; VoiceSpark will save the base site URL."
          />
          <TextField
            fullWidth
            label="Admin username"
            placeholder="admin"
            variant="outlined"
            size="small"
            margin="dense"
            value={wpForm.username}
            onChange={(e) => setWpForm({ ...wpForm, username: e.target.value })}
            disabled={wpLoading}
            helperText="Use the WordPress username for the account that created the application password."
          />
          <TextField
            fullWidth
            label="Application password"
            type="password"
            variant="outlined"
            size="small"
            margin="dense"
            value={wpForm.password}
            onChange={(e) => setWpForm({ ...wpForm, password: e.target.value })}
            disabled={wpLoading}
            helperText="Paste the generated application password, not your normal WordPress login password."
          />

          {wpError && (
            <Typography sx={{ color: "error.main", fontSize: 12, mt: 1 }}>
              {wpError}
            </Typography>
          )}

          <Box sx={{ mt: 2, p: 1.5, bgcolor: "#f8f9fa", borderRadius: 1 }}>
            <Typography sx={{ fontSize: 11.5, color: "#666", lineHeight: 1.45 }}>
              Need the latest plugin? <Link component="button" onClick={handleDownloadPlugin} sx={{ fontSize: 11.5, fontWeight: 700 }}>Download VoiceSpark plugin</Link>, then upload the ZIP in WordPress under <b>Plugins &gt; Add New &gt; Upload Plugin</b> and activate it.
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={() => setWpModalOpen(false)} disabled={wpLoading} sx={{ textTransform: "none" }}>
            Cancel
          </Button>
          <Button 
            onClick={handleWpSubmit} 
            variant="contained" 
            disabled={wpLoading || !wpForm.site_url || !wpForm.username || !wpForm.password}
            sx={{ 
              textTransform: "none", 
              bgcolor: "#111", 
              "&:hover": { bgcolor: "#333" },
              minWidth: 100
            }}
          >
            {wpLoading ? <CircularProgress size={20} color="inherit" /> : "Connect Site"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* LinkedIn Page Selection Modal */}
      <Dialog open={liPagesModalOpen} onClose={() => !liLoading && setLiPagesModalOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Select LinkedIn Page</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 13, color: "#666", mb: 2 }}>
            Choose the LinkedIn Company Page you want to publish content to. 
            You must be an administrator of the page.
          </Typography>
          
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {linkedinPages.length === 0 && (
              <Typography sx={{ fontSize: 14, color: "#888", textAlign: "center", py: 3 }}>
                No managed LinkedIn pages found. Make sure you are an admin of at least one Company Page.
              </Typography>
            )}
            {linkedinPages.map((page) => (
              <Box 
                key={page.id}
                onClick={() => handleSelectLiPage(page.id)}
                sx={{ 
                  p: 2, 
                  border: "1.5px solid",
                  borderColor: page.is_selected ? "#0a66c2" : "#e0e0e0",
                  borderRadius: "12px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  bgcolor: page.is_selected ? "#f0f7ff" : "transparent",
                  "&:hover": { borderColor: "#0a66c2", bgcolor: "#f0f7ff" },
                  transition: "all 0.2s"
                }}
              >
                <Avatar src={page.logo_url} sx={{ width: 40, height: 40 }}>{page.name[0]}</Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography sx={{ fontSize: 14, fontWeight: 600, color: "#111" }}>{page.name}</Typography>
                  <Typography sx={{ fontSize: 12, color: "#666" }}>Role: {page.role.replace(/_/g, ' ')}</Typography>
                </Box>
                {page.is_selected && (
                  <Chip label="Selected" size="small" sx={{ bgcolor: "#0a66c2", color: "#fff", fontWeight: 600, height: 20, fontSize: 10 }} />
                )}
              </Box>
            ))}
          </Box>
          {liLoading && (
            <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
              <CircularProgress size={24} />
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={() => setLiPagesModalOpen(false)} disabled={liLoading} sx={{ textTransform: "none" }}>
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
