// ── Top-level additions ───────────────────────────────────────────────────────
import { useState, useEffect } from "react";
import axios from "axios";

import {
  Box,
  Typography,
  Divider,
  TextField,
  Chip,
  Tooltip,
  CircularProgress,
  Alert,
  Button,


} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import config from "../../config";
import { workspaceStorage } from "../workspace/workSpaceAPi";
// ── Replace INITIAL_STATE with null, add loading state ───────────────────────
function SectionLabel({ label }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1 }}>
      <Typography fontWeight={600} fontSize={14}>
        {label}
      </Typography>
      <Tooltip title={`Your brand's ${label.toLowerCase()}`}>
        <HelpOutlineIcon sx={{ fontSize: 15, color: "text.disabled", cursor: "pointer" }} />
      </Tooltip>
    </Box>
  );
}

// ── TextArea section (Purpose / Audience) ─────────────────────────────────────
function TextAreaSection({ label, value, onChange }) {
  return (
    <Box sx={{ mb: 3.5 }}>
      <SectionLabel label={label} />
      <TextField
        multiline
        minRows={2}
        fullWidth
        value={value}
        onChange={(e) => onChange(e.target.value)}
        sx={{
          "& .MuiOutlinedInput-root": {
            borderRadius: 2,
            fontSize: 14,
            color: "#1e40af",
            "& fieldset": { borderColor: "divider" },
            "&:hover fieldset": { borderColor: "text.secondary" },
          },
        }}
      />
    </Box>
  );
}

// ── Tags section ──────────────────────────────────────────────────────────────
function TagsSection({ label, tags, onChange }) {
  const [inputVisible, setInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState("");

  const handleDelete = (index) => {
    onChange(tags.filter((_, i) => i !== index));
  };

  const handleAdd = () => {
    const trimmed = inputValue.trim();
    if (trimmed) onChange([...tags, trimmed]);
    setInputValue("");
    setInputVisible(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleAdd();
    if (e.key === "Escape") {
      setInputVisible(false);
      setInputValue("");
    }
  };
  console.log(tags);
  const isAccented = (tag) =>
    tag.toLowerCase().includes("bullet") ||
    tag.toLowerCase().includes("incorporate");

  return (
    <Box sx={{ mb: 3.5 }}>
      <SectionLabel label={label} />
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        {tags.map((tag, i) => (
          <Chip
            key={i}
            label={tag}
            onDelete={() => handleDelete(i)}
            size="small"
            sx={{
              borderRadius: 2,
              border: "1px solid",
              fontSize: 13,
              height: 32,
              bgcolor: "transparent",
              borderColor: isAccented(tag) ? "#f97316" : "rgba(0,0,0,0.15)",
              color: isAccented(tag) ? "#f97316" : "text.primary",
              "& .MuiChip-deleteIcon": {
                fontSize: 14,
                color: isAccented(tag) ? "#f97316" : "text.secondary",
                "&:hover": { color: "text.primary" },
              },
            }}
          />
        ))}

        {inputVisible ? (
          <TextField
            autoFocus
            size="small"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleAdd}
            placeholder="Type and press Enter"
            sx={{
              width: 220,
              "& .MuiOutlinedInput-root": {
                borderRadius: 2,
                fontSize: 13,
                height: 32,
              },
            }}
          />
        ) : (
          <Chip
            label="+ Add"
            onClick={() => setInputVisible(true)}
            size="small"
            sx={{
              borderRadius: 2,
              border: "1px solid rgba(0,0,0,0.15)",
              bgcolor: "transparent",
              fontSize: 13,
              height: 32,
              cursor: "pointer",
              color: "text.secondary",
              "&:hover": { borderColor: "text.primary", color: "text.primary", bgcolor: "transparent" },
            }}
          />
        )}
      </Box>
    </Box>
  );
}



export default function BrandVoiceContent() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const user = JSON.parse(localStorage.getItem('user'));
  const workspaceId = workspaceStorage.getActiveId();
  const fetchBrandVoice = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await axios.post(config.API_SERVER + "auth/user/fetch-brand-voice/", {
        user_id: user.id,
        workspace_id:workspaceId
      });
      setData(res.data.data);
    } catch (error) {
      console.error(error);
      setData(null);
      setError(error.response?.data?.error || 'Brand voice is not ready yet.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBrandVoice();
  }, []);
  console.log(data);

  const update = (key) => (val) =>
    setData((prev) => ({ ...prev, [key]: val }));

  // ── Spinner while fetching ──────────────────────────────────────────────────
  if (loading) {
    return (
      <Box
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: 300,
          gap: 2,
        }}
      >
        <CircularProgress size={48} thickness={4} />
        <Typography fontSize={14} color="text.secondary">
          Loading brand voice…
        </Typography>
      </Box>
    );
  }

  if (!data) {
    return (
      <Box sx={{ flex: 1, p: 3, maxWidth: 720 }}>
        <Alert severity="info" sx={{ mb: 2 }}>
          {error || 'Brand voice is not ready yet.'}
        </Alert>
        <Button variant="outlined" onClick={fetchBrandVoice} sx={{ textTransform: 'none' }}>
          Retry
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, p: 3, maxWidth: 900 }}>
      <Typography variant="h6" fontWeight={700} fontSize={20} mb={1}>
        Brand Voice
      </Typography>
      <Divider sx={{ mb: 3 }} />

      <TextAreaSection label="Purpose" value={data.purpose} onChange={update("purpose")} />
      <TextAreaSection label="Audience" value={data.audience} onChange={update("audience")} />
      <TagsSection label="Tone" tags={data.tone} onChange={update("tone")} />
      <TagsSection label="Emotion" tags={data.emotion} onChange={update("emotion")} />
      <TagsSection label="Character" tags={data.character} onChange={update("character")} />
      <TagsSection label="Syntax" tags={data.syntax} onChange={update("syntax")} />
      <TagsSection label="Language" tags={data.language} onChange={update("language")} />
    </Box>
  );
}
