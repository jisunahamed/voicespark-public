import { useEffect, useRef, useState } from "react";
import {
  Box,
  Typography,
  Button,
  Card,
  Grid2 as Grid,
  Select,
  MenuItem,
  FormControl,
  Divider,
  IconButton,
  Tooltip,
  TextField,
  CircularProgress,
  Alert,
  Stack,
} from "@mui/material";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import AddIcon from "@mui/icons-material/Add";
import SaveIcon from "@mui/icons-material/Save";
import CheckIcon from "@mui/icons-material/Check";
import axios from "axios";
import config from "../../config";
import { workspaceStorage } from "../workspace/workSpaceAPi";
import { contentEngineApi } from "../login_register/content_engine_api";
import { VISUAL_STYLE_OPTIONS as CONTENT_STYLE_OPTIONS } from "../login_register/visual_style_options";

const FONT_OPTIONS = [
  "Inter", "DM Sans", "Lexend", "Poppins", "Montserrat", "Archivo", "Manrope", "Rubik",
  "Roboto", "Open Sans", "Lato", "Nunito", "Source Sans 3", "Raleway", "Oswald",
  "Bebas Neue", "Playfair Display", "Merriweather", "Neue Haas Unica Paneuropean",
  "Noto Sans", "Noto Serif", "Noto Sans Bengali", "Hind Siliguri", "Anek Bangla",
  "Tiro Bangla", "Baloo Da 2", "Mukta", "Karla", "Work Sans", "Plus Jakarta Sans",
  "Space Grotesk", "Sora", "Urbanist", "Outfit", "IBM Plex Sans", "Libre Franklin",
  "Cormorant Garamond", "Fraunces", "Cinzel", "Josefin Sans", "Quicksand", "Cabin",
  "Figtree", "Geist", "Aptos", "Arial", "Helvetica", "Georgia", "Times New Roman"
];
const WEIGHT_OPTIONS = ["Thin", "Light", "Regular", "Medium", "Semi Bold", "Bold", "Extra Bold"];
const EMPTY_STYLE = {
  logos: [],
  colors: [],
  fonts: [
    { role: "title", family: "Inter", weight: "Bold" },
    { role: "body", family: "Inter", weight: "Regular" },
  ],
  visual_identity: "",
  visual_style: { id: "", label: "Website Inspired", name: "Website Inspired", image_url: "", description: "", prompt: "" },
};

function getFont(style, role) {
  return style.fonts?.find((font) => font.role === role) || EMPTY_STYLE.fonts.find((font) => font.role === role);
}

function SectionCard({ children, sx = {} }) {
  return (
    <Card
      variant="outlined"
      sx={{
        borderRadius: 3,
        p: 2.5,
        height: "100%",
        borderColor: "#e4e7ec",
        boxShadow: "0 12px 34px rgba(17,24,39,0.05)",
        ...sx,
      }}
    >
      {children}
    </Card>
  );
}

function LogoCard({ logos, onUpload, onDelete, uploading }) {
  const inputRef = useRef(null);
  return (
    <SectionCard>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography fontWeight={600} fontSize={15}>Logo</Typography>
        <Button
          size="small"
          startIcon={uploading ? <CircularProgress size={12} /> : <AddIcon sx={{ fontSize: 14 }} />}
          sx={{ fontSize: 12, color: "text.secondary", textTransform: "none" }}
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
        >
          Add More
        </Button>
        <input ref={inputRef} type="file" accept="image/*" multiple hidden onChange={onUpload} />
      </Box>

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
        {logos.map((logo, index) => (
          <Box
            key={`${logo.url}-${index}`}
            sx={{
              width: 96,
              height: 96,
              position: "relative",
              borderRadius: 2,
              border: "1px solid",
              borderColor: "divider",
              bgcolor: "#fafafa",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Box component="img" src={logo.url} alt="Brand logo" sx={{ maxWidth: "82%", maxHeight: "82%", objectFit: "contain" }} />
            <IconButton
              size="small"
              onClick={() => onDelete(index)}
              sx={{ position: "absolute", top: 4, right: 4, bgcolor: "#fff", p: 0.25, "&:hover": { bgcolor: "#fee2e2", color: "#991b1b" } }}
            >
              <DeleteOutlineIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Box>
        ))}
        {!logos.length && (
          <Button
            variant="outlined"
            size="small"
            startIcon={<CloudUploadOutlinedIcon sx={{ fontSize: 16 }} />}
            onClick={() => inputRef.current?.click()}
            sx={{ fontSize: 12, textTransform: "none", borderRadius: 2, borderColor: "divider", color: "text.secondary", px: 2, py: 1 }}
          >
            Upload
          </Button>
        )}
      </Box>
    </SectionCard>
  );
}

function FontsCard({ style, onChange }) {
  const titleFont = getFont(style, "title");
  const bodyFont = getFont(style, "body");
  const updateFont = (role, field, value) => {
    const next = [...(style.fonts || EMPTY_STYLE.fonts)];
    const index = next.findIndex((font) => font.role === role);
    const current = index >= 0 ? next[index] : { role, family: "Inter", weight: "Regular" };
    const updated = { ...current, [field]: value };
    if (index >= 0) next[index] = updated;
    else next.push(updated);
    onChange({ fonts: next });
  };

  const SelectField = ({ value, options, onChange }) => (
    <FormControl size="small" fullWidth>
      <Select value={value} onChange={(event) => onChange(event.target.value)} sx={{ fontSize: 13, borderRadius: 1.5 }}>
        {options.map((option) => <MenuItem key={option} value={option} sx={{ fontSize: 13 }}>{option}</MenuItem>)}
      </Select>
    </FormControl>
  );

  return (
    <SectionCard>
      <Typography fontWeight={600} fontSize={15} mb={2}>Fonts</Typography>
      <Box sx={{ bgcolor: "#f9fafb", borderRadius: 2, p: 2.5, mb: 2, textAlign: "center" }}>
        <Typography sx={{ fontFamily: titleFont.family, fontSize: 32, fontWeight: 700, color: "text.primary" }}>
          {titleFont.family}
        </Typography>
        <Typography sx={{ fontFamily: bodyFont.family, fontSize: 14, color: "text.secondary" }}>
          {bodyFont.family}
        </Typography>
      </Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 7 }}>
          <Typography fontSize={11} color="text.secondary" mb={0.5}>Title font</Typography>
          <SelectField value={titleFont.family} options={FONT_OPTIONS} onChange={(value) => updateFont("title", "family", value)} />
        </Grid>
        <Grid size={{ xs: 5 }}>
          <Typography fontSize={11} color="text.secondary" mb={0.5}>Weight</Typography>
          <SelectField value={titleFont.weight} options={WEIGHT_OPTIONS} onChange={(value) => updateFont("title", "weight", value)} />
        </Grid>
        <Grid size={{ xs: 7 }}>
          <Typography fontSize={11} color="text.secondary" mb={0.5}>Body font</Typography>
          <SelectField value={bodyFont.family} options={FONT_OPTIONS} onChange={(value) => updateFont("body", "family", value)} />
        </Grid>
        <Grid size={{ xs: 5 }}>
          <Typography fontSize={11} color="text.secondary" mb={0.5}>Weight</Typography>
          <SelectField value={bodyFont.weight} options={WEIGHT_OPTIONS} onChange={(value) => updateFont("body", "weight", value)} />
        </Grid>
      </Grid>
    </SectionCard>
  );
}

function ColorsCard({ colors, onChange }) {
  const inputRef = useRef(null);
  const [editingIndex, setEditingIndex] = useState(null);
  const editColor = (index) => {
    setEditingIndex(index);
    inputRef.current?.click();
  };
  const updateColor = (event) => {
    if (editingIndex === null) return;
    const next = [...colors];
    next[editingIndex] = event.target.value;
    onChange(next);
    setEditingIndex(null);
  };

  return (
    <SectionCard>
      <Typography fontWeight={600} fontSize={15} mb={2}>Colors</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
        {colors.map((color, index) => (
          <Tooltip key={`${color}-${index}`} title={color}>
            <Box sx={{ position: "relative" }}>
              <Box
                onClick={() => editColor(index)}
                sx={{ width: 82, height: 82, borderRadius: 2, bgcolor: color, border: "1px solid", borderColor: "divider", cursor: "pointer" }}
              />
              <IconButton
                size="small"
                onClick={() => onChange(colors.filter((_, colorIndex) => colorIndex !== index))}
                sx={{ position: "absolute", top: 3, right: 3, bgcolor: "#fff", p: 0.2, "&:hover": { bgcolor: "#fee2e2", color: "#991b1b" } }}
              >
                <DeleteOutlineIcon sx={{ fontSize: 15 }} />
              </IconButton>
            </Box>
          </Tooltip>
        ))}
        <Box
          onClick={() => onChange([...colors, "#ffffff"])}
          sx={{ width: 82, height: 82, borderRadius: 2, border: "1.5px dashed", borderColor: "divider", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "text.secondary" }}
        >
          <AddIcon sx={{ fontSize: 22 }} />
        </Box>
      </Box>
      <input ref={inputRef} type="color" hidden onChange={updateColor} />
    </SectionCard>
  );
}

function VisualStyleCard({ selectedStyle, onChange }) {
  const currentId = selectedStyle?.id;
  return (
    <SectionCard>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography fontWeight={600} fontSize={15}>Content Style</Typography>
        <Typography fontSize={12} color="text.secondary">Affects future images</Typography>
      </Box>
      <Grid container spacing={1.5}>
        {CONTENT_STYLE_OPTIONS.map((option) => {
          const selected = currentId === option.id || selectedStyle?.label === option.name || selectedStyle?.name === option.name;
          return (
            <Grid size={{ xs: 12, sm: 6 }} key={option.id}>
              <Box
                onClick={() => onChange({ visual_style: { ...option, label: option.name } })}
                sx={{
                  position: "relative",
                  height: 170,
                  borderRadius: 2,
                  overflow: "hidden",
                  cursor: "pointer",
                  border: "2px solid",
                  borderColor: selected ? "#111" : "transparent",
                  boxShadow: selected ? "0 0 0 2px rgba(17,17,17,0.08)" : "none",
                }}
              >
                <Box component="img" src={option.image_url || option.image} alt={option.name} sx={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: option.imagePosition || "center", display: "block" }} />
                <Box sx={{ position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(0,0,0,.78), rgba(0,0,0,.1) 62%, rgba(0,0,0,.05))" }} />
                <Box sx={{ position: "absolute", top: 10, left: 10, width: 26, height: 26, borderRadius: 1, bgcolor: selected ? "#fff" : "rgba(255,255,255,.22)", border: selected ? "none" : "1px solid rgba(255,255,255,.65)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {selected && <CheckIcon sx={{ fontSize: 18, color: "#111" }} />}
                </Box>
                <Box sx={{ position: "absolute", left: 14, right: 14, bottom: 12 }}>
                  <Typography sx={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>{option.name}</Typography>
                  <Typography sx={{ color: "rgba(255,255,255,.78)", fontSize: 12, lineHeight: 1.35, mt: 0.5 }}>{option.description}</Typography>
                </Box>
              </Box>
            </Grid>
          );
        })}
      </Grid>
    </SectionCard>
  );
}

export default function BrandStyleContent() {
  const [style, setStyle] = useState(EMPTY_STYLE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const user = JSON.parse(localStorage.getItem("user") || "{}");
  const workspaceId = workspaceStorage.getActiveId();

  useEffect(() => {
    let active = true;
    const fetchStyle = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await axios.post(config.API_SERVER + "auth/user/fetch-brand-style/", {
          user_id: user.id,
          workspace_id: workspaceId,
        });
        if (active) setStyle({ ...EMPTY_STYLE, ...response.data.data });
      } catch (err) {
        if (active) setError(err.response?.data?.error || "Brand style could not be loaded.");
      } finally {
        if (active) setLoading(false);
      }
    };
    fetchStyle();
    return () => {
      active = false;
    };
  }, [user.id, workspaceId]);

  const patchStyle = (patch) => setStyle((prev) => ({ ...prev, ...patch }));

  const saveStyle = async (nextStyle = style) => {
    setSaving(true);
    setError("");
    try {
      const response = await axios.post(config.API_SERVER + "auth/user/update-brand-style/", {
        user_id: user.id,
        workspace_id: workspaceId,
        brand_style: nextStyle,
      });
      if (Array.isArray(nextStyle.fonts) && nextStyle.fonts.length) {
        const titleFont = nextStyle.fonts.find((font) => font.role === "title") || nextStyle.fonts[0];
        await contentEngineApi.saveBrand({
          font: {
            id: String(titleFont.family || "Inter").toLowerCase().replace(/[^a-z0-9]+/g, "-"),
            displayName: titleFont.family || "Inter",
            family: titleFont.family || "Inter",
            weight: titleFont.weight || "Bold",
          },
        });
      }
      if (nextStyle.visual_style) {
        await contentEngineApi.saveBrand({ recommended_visual_style: nextStyle.visual_style });
      }
      setStyle({ ...EMPTY_STYLE, ...response.data.data });
    } catch (err) {
      setError(err.response?.data?.error || "Brand style could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const uploadLogos = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setUploading(true);
    setError("");
    try {
      let latestStyle = style;
      for (const file of files) {
        const formData = new FormData();
        formData.append("image", file);
        formData.append("user_id", user.id);
        formData.append("workspace_id", workspaceId);
        const response = await axios.post(config.API_SERVER + "auth/user/upload-brand-style-logo/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        latestStyle = { ...EMPTY_STYLE, ...response.data.data };
      }
      setStyle(latestStyle);
    } catch (err) {
      setError(err.response?.data?.error || "Logo upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const deleteLogo = (index) => {
    const next = { ...style, logos: style.logos.filter((_, logoIndex) => logoIndex !== index) };
    setStyle(next);
    saveStyle(next);
  };

  if (loading) {
    return (
      <Box sx={{ flex: 1, p: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, width: "100%", p: { xs: 2, md: 2.5 } }}>
      <Stack direction={{ xs: "column", sm: "row" }} alignItems={{ xs: "flex-start", sm: "center" }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h6" fontWeight={900} fontSize={22} color="#1f2328">Brand Style</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.4 }}>
            Keep logo, typography, colors, and visual identity aligned for generated posts.
          </Typography>
        </Box>
        <Button
          variant="contained"
          size="small"
          startIcon={saving ? <CircularProgress size={14} sx={{ color: "#fff" }} /> : <SaveIcon sx={{ fontSize: 16 }} />}
          onClick={() => saveStyle()}
          disabled={saving}
          sx={{ bgcolor: "#111", textTransform: "none", borderRadius: 1.5, "&:hover": { bgcolor: "#333" } }}
        >
          {saving ? "Saving..." : "Save"}
        </Button>
      </Stack>
      <Divider sx={{ my: 2 }} />
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 3 }}>
          <LogoCard logos={style.logos || []} onUpload={uploadLogos} onDelete={deleteLogo} uploading={uploading} />
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <FontsCard style={style} onChange={patchStyle} />
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <ColorsCard colors={style.colors || []} onChange={(colors) => patchStyle({ colors })} />
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <SectionCard sx={{ minHeight: 292 }}>
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ xs: "flex-start", sm: "center" }} spacing={1} sx={{ mb: 1.5 }}>
              <Box>
                <Typography fontWeight={900} fontSize={16} color="#1f2328">Visual Identity Description</Typography>
                <Typography fontSize={12.5} color="text.secondary" sx={{ mt: 0.25 }}>
                  Describe the visual direction, spacing, materials, lighting, and brand mood.
                </Typography>
              </Box>
              <Typography fontSize={12} color="text.secondary">
                {(style.visual_identity || "").length} characters
              </Typography>
            </Stack>
            <TextField
              fullWidth
              multiline
              minRows={8}
              value={style.visual_identity || ""}
              onChange={(event) => patchStyle({ visual_identity: event.target.value })}
              placeholder="Describe the brand's visual identity."
              sx={{
                "& .MuiOutlinedInput-root": {
                  borderRadius: 2,
                  alignItems: "flex-start",
                  bgcolor: "#fbfcff",
                  fontSize: 14,
                  lineHeight: 1.65,
                },
              }}
            />
          </SectionCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <VisualStyleCard selectedStyle={style.visual_style} onChange={patchStyle} />
        </Grid>
      </Grid>
    </Box>
  );
}
