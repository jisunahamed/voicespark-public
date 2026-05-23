import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Button,
  Divider,
  Alert,
  Skeleton,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Stack,
  Chip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import LanguageIcon from "@mui/icons-material/Language";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import axios from "axios";
import config from "../../config";
import { workspaceStorage } from "../workspace/workSpaceAPi";
import { contentEngineApi } from "../login_register/content_engine_api";
import { AmbientWorking } from "../../components/VoiceSparkUI";

export default function SourceMaterialsPage() {
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [error, setError] = useState("");
  const user = JSON.parse(localStorage.getItem('user'));
  const workspaceId = workspaceStorage.getActiveId();
  const loadSources = async () => {
    try {
      const { data } = await contentEngineApi.fetchSourceMatrix();
      const nextSources = (data.sources || []).filter((source) => source.source_type === "my_website");
      setSources(nextSources);
      return nextSources;
    } catch {
      setSources([]);
      return [];
    }
  };

  useEffect(() => {
    axios
      .post(config.API_SERVER+"auth/user/get-website/",{
        user_id:user.id,
        workspace_id:workspaceId
      })
      .then((res) => {
        setWebsiteUrl(res.data.website_url);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load source materials.");
        setLoading(false);
      });
    loadSources();
  }, []);

  const addSource = async () => {
    if (!newUrl.trim()) return;
    setAnalyzing(true);
    setError("");
    try {
      await contentEngineApi.analyzeSourceMatrix({ url: newUrl.trim(), source_type: "my_website" });
      setDialogOpen(false);
      setNewUrl("");
      await loadSources();
    } catch (err) {
      const latestSources = await loadSources();
      const normalizedUrl = newUrl.trim().replace(/^https?:\/\//i, "").replace(/\/$/, "");
      const savedSource = latestSources.find((source) => (
        (source.url || "").replace(/^https?:\/\//i, "").replace(/\/$/, "") === normalizedUrl
      ));
      if (savedSource && savedSource.status === "analyzed") {
        setDialogOpen(false);
        setNewUrl("");
        setError("");
      } else {
        setError(err.response?.data?.error || "Source analysis failed.");
      }
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 960, mx: "auto", px: { xs: 2, md: 4 }, py: 5 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 0.5 }}>
        <Typography variant="h5" fontWeight={700}>Source Materials</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setDialogOpen(true)}
          sx={{
            bgcolor: "#111", color: "#fff", fontWeight: 600,
            borderRadius: "8px", textTransform: "none", px: 2.5,
            "&:hover": { bgcolor: "#333" },
          }}
        >
          Add Source Material
        </Button>
      </Box>

      <Divider sx={{ my: 2.5 }} />

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 600 }}>
        Add website pages, product pages, lookbooks, landing pages, or other brand source URLs.
            Voice Spark will analyze the pages, extract useful images, and use the material in future content.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Divider />

      {loading ? (
        <Box sx={{ display: "flex", alignItems: "center", py: 2, gap: 2 }}>
          <Skeleton variant="circular" width={28} height={28} />
          <Skeleton width="50%" height={16} />
        </Box>
      ) : websiteUrl ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 1, py: 1.75 }}>
          <Box sx={{
            width: 28, height: 28, borderRadius: "50%",
            bgcolor: "#e0e7ff", display: "flex", alignItems: "center",
            justifyContent: "center", flexShrink: 0,
          }}>
            <LanguageIcon sx={{ fontSize: 15, color: "#4338ca" }} />
          </Box>

          <Typography
            variant="body2"
            fontWeight={500}
            sx={{ color: "primary.main", cursor: "pointer", "&:hover": { textDecoration: "underline" } }}
            onClick={() => window.open(websiteUrl, "_blank")}
          >
            {websiteUrl}
          </Typography>

          <Tooltip title="Open link">
            <IconButton size="small" onClick={() => window.open(websiteUrl, "_blank")} sx={{ p: 0.25 }}>
              <OpenInNewIcon sx={{ fontSize: 13, color: "text.disabled" }} />
            </IconButton>
          </Tooltip>
        </Box>
      ) : (
        <Box sx={{ py: 8, textAlign: "center" }}>
          <Typography color="text.secondary">No source materials yet.</Typography>
        </Box>
      )}

      {!!sources.length && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>Analyzed Sources</Typography>
          <Stack spacing={1}>
            {sources.map((source) => (
              <Box key={source.id} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, border: "1px solid", borderColor: "divider", borderRadius: 1.5, p: 1.25 }}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography noWrap fontSize={14} fontWeight={600}>{source.url}</Typography>
                  <Typography color="text.secondary" fontSize={12}>{source.last_analyzed_at ? new Date(source.last_analyzed_at).toLocaleString() : "Not analyzed yet"}</Typography>
                </Box>
                <Chip size="small" label={source.status} color={source.status === "analyzed" ? "success" : source.status === "failed" ? "error" : "default"} />
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      <Dialog open={dialogOpen} onClose={() => !analyzing && setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Source Material</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Add a website URL. Voice Spark will analyze the pages, pull images into Media Library, and update brand intelligence.
          </Typography>
          <TextField fullWidth label="Website URL" placeholder="https://example.com" value={newUrl} onChange={(event) => setNewUrl(event.target.value)} />
          {analyzing && (
            <Stack direction="row" gap={1} sx={{ mt: 2 }} flexWrap="wrap">
              {["Identifying your brand", "Pulling photos & media", "Analyzing competitors"].map((label) => <Chip key={label} label={label} size="small" />)}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={analyzing}>Cancel</Button>
          <Button onClick={addSource} disabled={analyzing || !newUrl.trim()} variant="contained" sx={{ bgcolor: "#111", textTransform: "none", "&:hover": { bgcolor: "#333" } }}>
            {analyzing ? "Analyzing..." : "Analyze Source"}
          </Button>
        </DialogActions>
      </Dialog>
      <AmbientWorking active={analyzing} title="Analyzing source material" detail="Voice Spark is reading the URL and updating brand intelligence in the background." />
    </Box>
  );
}
