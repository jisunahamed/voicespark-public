import React, { useState, useRef, useEffect } from "react";
import {
  Box,
  Typography,
  Button,
  Stack,
  Divider,
  Checkbox,
  Chip,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Snackbar,
  Alert,
  Dialog,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import CloseIcon from "@mui/icons-material/Close";
import ImageOutlinedIcon from "@mui/icons-material/ImageOutlined";
import PaletteOutlinedIcon from "@mui/icons-material/PaletteOutlined";
import RecordVoiceOverOutlinedIcon from "@mui/icons-material/RecordVoiceOverOutlined";
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import QueryStatsOutlinedIcon from "@mui/icons-material/QueryStatsOutlined";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import FolderCopyOutlinedIcon from "@mui/icons-material/FolderCopyOutlined";
import TopBar from "../../TopBar";
import BrandStyleContent from './brand_style';
import axios from "axios";
import config from "../../config";
import BrandProfile from "./brand_profile";
import SourceMaterialsPage from "./source_material";
import {
  AudienceProfilesContent,
  ChannelVoiceContent,
  CompetitorAnalysisContent,
} from './intelligence';
import { workspaceStorage } from "../workspace/workSpaceAPi";
import { useLocation } from "react-router-dom";
// ── Sidebar nav items ─────────────────────────────────────────────────────────
const NAV_ITEMS = [
  "Media Library",
  "Brand Style",
  "Brand Voice",
  "Brand Profile",
  "Competitor Analysis",
  "Audience Profiles",
  "Source Materials",
];
const NAV_META = {
  "Media Library": { icon: <ImageOutlinedIcon fontSize="small" />, hint: "Visual assets" },
  "Brand Style": { icon: <PaletteOutlinedIcon fontSize="small" />, hint: "Color, logo, font" },
  "Brand Voice": { icon: <RecordVoiceOverOutlinedIcon fontSize="small" />, hint: "Tone and channels" },
  "Brand Profile": { icon: <BadgeOutlinedIcon fontSize="small" />, hint: "Company analysis" },
  "Competitor Analysis": { icon: <QueryStatsOutlinedIcon fontSize="small" />, hint: "Market context" },
  "Audience Profiles": { icon: <GroupsOutlinedIcon fontSize="small" />, hint: "Customer segments" },
  "Source Materials": { icon: <FolderCopyOutlinedIcon fontSize="small" />, hint: "Research inputs" },
};
const NAV_CONTENT = {
  "Media Library": <MediaContent />,
  "Brand Style": <BrandStyleContent />,
  "Brand Voice": <ChannelVoiceContent />,
  "Brand Profile": <BrandProfile />,
  "Competitor Analysis": <CompetitorAnalysisContent />,
  "Audience Profiles": <AudienceProfilesContent />,
  "Source Materials": <SourceMaterialsPage />,
};

function Sidebar({ active, onSelect }) {
  return (
    <Box
      sx={{
        width: 248,
        flexShrink: 0,
        height: "100%",
        overflow: "hidden",
        p: 1.15,
        borderRight: "1px solid rgba(17,24,39,0.08)",
        bgcolor: "rgba(255,255,255,0.86)",
      }}
    >
      <List dense disablePadding>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item}
            selected={active === item}
            onClick={() => onSelect(item)}
            sx={{
              borderRadius: 2.5,
              px: 1.4,
              py: 0.95,
              mb: 0.4,
              gap: 1.2,
              color: active === item ? "#4c1d95" : "#475467",
              bgcolor: active === item ? "#ede9fe" : "transparent",
              boxShadow: active === item ? "inset 0 0 0 1px rgba(124,58,237,0.14)" : "none",
              "&.Mui-selected": { bgcolor: "#ede9fe" },
              "&.Mui-selected:hover": { bgcolor: "#e9d5ff" },
              "&:hover": { bgcolor: active === item ? "#e9d5ff" : "#f3f4f8" },
            }}
          >
            <Box sx={{ width: 26, height: 26, borderRadius: 1.5, display: "grid", placeItems: "center", bgcolor: active === item ? "#fff" : "#f2f4f7", color: active === item ? "#7c3aed" : "#667085", flexShrink: 0 }}>
              {NAV_META[item]?.icon}
            </Box>
            <ListItemText
              primary={item}
              secondary={NAV_META[item]?.hint}
              primaryTypographyProps={{
                fontSize: 13,
                fontWeight: 850,
                color: "inherit",
                noWrap: true,
              }}
              secondaryTypographyProps={{
                fontSize: 11,
                color: active === item ? "#6d28d9" : "#98a2b3",
                noWrap: true,
              }}
            />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}

// ── Media card ────────────────────────────────────────────────────────────────
function normalizeMediaKey(src) {
  try {
    const url = new URL(String(src || ""), window.location.origin);
    const ignored = new Set(["w", "width", "h", "height", "q", "quality", "fit", "crop", "auto", "format", "fm", "ixlib", "dpr", "resize", "size", "s", "ssl", "tr", "transform", "v"]);
    [...url.searchParams.keys()].forEach((key) => {
      if (ignored.has(key.toLowerCase()) || key.toLowerCase().startsWith("utm_")) url.searchParams.delete(key);
    });
    url.hash = "";
    url.pathname = url.pathname
      .replace(/[-_](?:\d{2,5}x\d{2,5}|\d{2,5}w|\d{2,5}h|scaled|copy)(?=\.)/gi, "")
      .replace(/@\d+x(?=\.)/gi, "")
      .replace(/\/+$/, "");
    return `${url.origin}${url.pathname}${url.search}`.toLowerCase();
  } catch {
    return String(src || "")
      .split("#")[0]
      .split("?")[0]
      .replace(/[-_](?:\d{2,5}x\d{2,5}|\d{2,5}w|\d{2,5}h|scaled|copy)(?=\.)/gi, "")
      .replace(/@\d+x(?=\.)/gi, "")
      .replace(/\/+$/, "")
      .toLowerCase();
  }
}

function dedupeMediaItems(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = normalizeMediaKey(item.src);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function MediaCard({ src, name, date, type, used, selected, onSelect, onDelete, onOpen }) {
  const [hovered, setHovered] = useState(false);

  return (
    <Box
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onOpen}
      sx={{ width: 142, cursor: "zoom-in" }}
    >
      <Box
        sx={{
          position: "relative",
          width: 142,
          height: 142,
          borderRadius: 3,
          overflow: "hidden",
          border: selected ? "2px solid" : "1px solid",
          borderColor: selected ? "#7c3aed" : "#e4e7ec",
          boxShadow: "0 14px 32px rgba(17,24,39,0.06)",
          bgcolor: "#f8fafc",
        }}
      >
        {/* Thumbnail */}
        <Box
          component="img"
          src={src}
          alt={name}
          sx={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
        />

        {/* Checkbox top-left */}
        {(hovered || selected) && (
          <Box sx={{ position: "absolute", top: 4, left: 4 }}>
            <Checkbox
              checked={selected}
              onChange={onSelect}
              onClick={(event) => event.stopPropagation()}
              size="small"
              sx={{
                p: 0,
                bgcolor: "background.paper",
                borderRadius: 0.5,
                "&:hover": { bgcolor: "background.paper" },
              }}
            />
          </Box>
        )}

        {/* "Used" badge */}
        {used && (
          <Chip
            label="Used"
            size="small"
            sx={{
              position: "absolute",
              bottom: 8,
              left: 8,
              fontSize: 11,
              height: 22,
              bgcolor: "background.paper",
              border: "1px solid",
              borderColor: "divider",
              fontWeight: 500,
            }}
          />
        )}
        {hovered && (
          <IconButton
            size="small"
            onClick={(event) => {
              event.stopPropagation();
              onDelete();
            }}
            sx={{
              position: "absolute",
              top: 4,
              right: 4,
              bgcolor: "background.paper",
              borderRadius: 1,
              p: 0.3,
              "&:hover": { bgcolor: "#fee2e2", color: "#991b1b" },
            }}
          >
            <DeleteOutlineIcon sx={{ fontSize: 17 }} />
          </IconButton>
        )}
      </Box>

      {/* Caption */}
      {/* <Box sx={{ mt: 0.8 }}>
        <Typography variant="body2" fontWeight={500} fontSize={13}>
          {name}
        </Typography>
        <Typography variant="caption" color="text.secondary" fontSize={12}>
          {type} · {date}
        </Typography>
      </Box> */}
    </Box>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
const SAMPLE_MEDIA = [
  // {
  //   id: 1,
  //   src: "https://via.placeholder.com/160x160/4a7c59/ffffff?text=IMG",
  //   name: "image",
  //   date: "2026-04-07",
  //   type: "Image",
  //   used: true,
  // },
];

function MediaContent() {
  const [media, setMedia] = useState(SAMPLE_MEDIA);
  const [selected, setSelected] = useState([]);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [previewMedia, setPreviewMedia] = useState(null);
  const fileInputRef = useRef(null);

  const imageCount = media.filter((m) => m.type === "Image").length;
  const videoCount = media.filter((m) => m.type === "Video").length;
  const user = JSON.parse(localStorage.getItem('user'));
  // const hasFetched = useRef(false);
  const workspaceId = workspaceStorage.getActiveId();
  useEffect(() => {

    const fetchMedia = async () => {
      // if (hasFetched.current) return;
      // hasFetched.current = true;
      try {
        const response = await axios.post(config.API_SERVER + "auth/user/get-data/",
          {
            // whatever your backend expects, e.g:
            user_id: user.id,
            workspace_id:workspaceId,
          }
        );
        const data = response.data.data
        setMedia(dedupeMediaItems(data.map((item) => ({
          id: item.id,
          src: item.src,
          name: item.name || item.metadata?.label || item.metadata?.alt || "image",
          date: item.created_at?.slice?.(0, 10) || item.updated_at?.slice?.(0, 10) || "",
          type: "Image",
          used: Boolean(item.used || item.is_used || item.in_campaign || Number(item.reference_count || 0) > 0),
          metadata: item.metadata || {},
        }))));
      } catch (err) {
        console.error("Failed to fetch media:", err);
      }
    };

    fetchMedia();
  }, [user?.id, workspaceId]);

  function toggleSelect(id) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function handleDeleteMedia(id) {
    const target = media.find((item) => item.id === id);
    if (!target || !window.confirm("Delete this media?")) return;
    setMedia((prev) => prev.filter((item) => item.id !== id));
    setSelected((prev) => prev.filter((itemId) => itemId !== id));
    try {
      await axios.post(config.API_SERVER + "auth/user/delete-media/", {
        user_id: user.id,
        workspace_id: workspaceId,
        media_id: id,
      });
    } catch (err) {
      console.error("Delete failed:", err);
      setMedia((prev) => dedupeMediaItems([...prev, target]));
    }
  }
  async function handleDeleteSelected() {
    const targets = media.filter((item) => selected.includes(item.id));
    if (!targets.length) return;
    if (!window.confirm(`Delete ${targets.length} selected media item${targets.length === 1 ? "" : "s"}?`)) return;
    setBulkDeleting(true);
    const previous = media;
    setMedia((prev) => prev.filter((item) => !selected.includes(item.id)));
    setSelected([]);
    try {
      await Promise.all(targets.map((item) =>
        axios.post(config.API_SERVER + "auth/user/delete-media/", {
          user_id: user.id,
          workspace_id: workspaceId,
          media_id: item.id,
        })
      ));
    } catch (err) {
      console.error("Bulk delete failed:", err);
      setMedia(previous);
    } finally {
      setBulkDeleting(false);
    }
  }
  const token = localStorage.getItem('access_token');

  async function handleFileChange(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    for (const file of files) {
      // Optimistic UI — show preview immediately
      const tempId = `temp-${Date.now()}-${Math.random()}`;
      const preview = {
        id: tempId,
        src: URL.createObjectURL(file),
        name: file.name.replace(/\.[^.]+$/, ""),
        date: new Date().toISOString().slice(0, 10),
        type: file.type.startsWith("video") ? "Video" : "Image",
        used: false,
        uploading: true,
      };
      setMedia((prev) => dedupeMediaItems([...prev, preview]));
      const workspaceId = workspaceStorage.getActiveId();
      try {
        const formData = new FormData();
        formData.append("image", file);
        formData.append("user_id", user.id);
        formData.append("workspace_id", workspaceId);


        const res = await axios.post(
          config.API_SERVER + "auth/user/media-upload/",
          formData,
          {
            headers: {
              "Content-Type": "multipart/form-data",
              // "Authorization": `Bearer ${token}`,
            },
          }
        );

        // Replace temp entry with real saved record
        setMedia((prev) =>
          dedupeMediaItems(prev.map((m) =>
            m.id === tempId
              ? {
                id: res.data.id,
                src: res.data.image,   // S3 URL from Django
                name: file.name.replace(/\.[^.]+$/, ""),
                date: res.data.updated_at?.slice(0, 10) ?? preview.date,
                type: preview.type,
                used: false,
                uploading: false,
              }
              : m
          ))
        );
      } catch (err) {
        console.error("Upload failed:", err);
        // Remove the failed preview
        setMedia((prev) => prev.filter((m) => m.id !== tempId));
      }
    }

    e.target.value = "";
  }
  return (
    <Box sx={{ flex: 1, p: { xs: 2, md: 2.5 } }}>
      {/* Header row */}
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ xs: "flex-start", sm: "center" }} spacing={2}>
        <Box>
          <Typography variant="h6" fontWeight={900} fontSize={20} color="#1f2328">
            Media Library
          </Typography>
          <Typography variant="body2" color="text.secondary" fontSize={13} sx={{ mt: 0.35, maxWidth: 760 }}>
            Product, logo, hero, team, and website images are used as brand-safe source references for campaigns.
          </Typography>
        </Box>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          onChange={handleFileChange}
        />

        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
          {selected.length > 0 && (
            <>
              <Chip
                label={`${selected.length} selected`}
                size="small"
                sx={{ bgcolor: "#ede9fe", color: "#5b21b6", fontWeight: 800 }}
              />
              <Button
                variant="outlined"
                color="error"
                disabled={bulkDeleting}
                startIcon={<DeleteOutlineIcon />}
                onClick={handleDeleteSelected}
                sx={{ textTransform: "none", borderRadius: 999, fontWeight: 800, fontSize: 13 }}
              >
                {bulkDeleting ? "Deleting..." : "Delete selected"}
              </Button>
              <Button
                variant="text"
                onClick={() => setSelected([])}
                disabled={bulkDeleting}
                sx={{ textTransform: "none", borderRadius: 999, fontWeight: 700, fontSize: 13, color: "#667085" }}
              >
                Clear
              </Button>
            </>
          )}
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => fileInputRef.current?.click()}
            sx={{
              textTransform: "none",
              fontWeight: 600,
              fontSize: 13,
              bgcolor: "text.primary",
              color: "background.paper",
              borderRadius: 999,
              px: 2,
              "&:hover": { bgcolor: "text.secondary" },
              whiteSpace: "nowrap",
            }}
          >
            Add New Media
          </Button>
        </Stack>
      </Stack>

      <Divider sx={{ my: 1.8, borderColor: "#eef0f5" }} />

      {/* Section title */}
      <Stack direction="row" alignItems="baseline" spacing={1} sx={{ mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={900} fontSize={15} color="#344054">
          Assets
        </Typography>
        <Typography variant="body2" color="text.secondary" fontSize={13}>
          {imageCount} {imageCount === 1 ? "image" : "images"}
        </Typography>
      </Stack>

      {/* Grid */}
      {media.length === 0 ? (
        <Box
          sx={{
            mt: 6,
            textAlign: "center",
            border: "2px dashed",
            borderColor: "divider",
            borderRadius: 4,
            bgcolor: "#fbfcff",
            py: 8,
            px: 4,
            cursor: "pointer",
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <Typography variant="body1" color="text.secondary" fontWeight={500}>
            No media yet
          </Typography>
          <Typography variant="body2" color="text.secondary" fontSize={13} sx={{ mt: 0.5 }}>
            Click to upload your first image
          </Typography>
        </Box>
      ) : (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
          {media.map((item) => (
            <MediaCard
              key={item.id}
              {...item}
              selected={selected.includes(item.id)}
              onSelect={() => toggleSelect(item.id)}
              onDelete={() => handleDeleteMedia(item.id)}
              onOpen={() => setPreviewMedia(item)}
            />
          ))}
        </Box>
      )}
      <Dialog open={Boolean(previewMedia)} onClose={() => setPreviewMedia(null)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pr: 1 }}>
          <Typography fontWeight={700} fontSize={16}>{previewMedia?.name || "Media preview"}</Typography>
          <IconButton onClick={() => setPreviewMedia(null)} size="small">
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ bgcolor: "#0f1117", p: 0, display: "flex", justifyContent: "center" }}>
          {previewMedia?.src && (
            <Box
              component="img"
              src={previewMedia.src}
              alt={previewMedia.name || "Media preview"}
              sx={{ maxWidth: "100%", maxHeight: "76vh", objectFit: "contain" }}
            />
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
}


export default function BrandKitPage() {
  const [activeNav, setActiveNav] = useState("Media Library");
  const location = useLocation();
  const [noticeOpen, setNoticeOpen] = useState(false);

  useEffect(() => {
    if (location.state?.tab && NAV_ITEMS.includes(location.state.tab)) {
      setActiveNav(location.state.tab);
    }
    if (location.state?.notice) {
      setNoticeOpen(true);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);


  return (
    <Box>
      <TopBar title={'Brand Kit'} />
      <Snackbar
        open={noticeOpen}
        autoHideDuration={3600}
        onClose={() => setNoticeOpen(false)}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        sx={{ mt: 7 }}
      >
        <Alert
          severity="info"
          variant="filled"
          onClose={() => setNoticeOpen(false)}
          sx={{ borderRadius: 2, fontWeight: 700, boxShadow: "0 16px 40px rgba(15,23,42,0.22)" }}
        >
          Change your brand information to improve your content.
        </Alert>
      </Snackbar>

      <Box sx={{ px: { xs: 1.5, md: 2 }, py: { xs: 1.5, md: 2 } }}>
        <Box
          sx={{
            display: "flex",
            height: "calc(100vh - 96px)",
            border: "1px solid rgba(17,24,39,0.08)",
            borderRadius: 4,
            bgcolor: "rgba(255,255,255,0.82)",
            overflow: "hidden",
            boxShadow: "0 20px 60px rgba(17,24,39,0.06)",
          }}
        >
          <Sidebar active={activeNav} onSelect={setActiveNav} />
          <Box sx={{ flex: 1, minWidth: 0, bgcolor: "#fff", height: "100%", overflowY: "auto", overflowX: "hidden" }}>
            {NAV_CONTENT[activeNav]}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
