import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import ImageOutlinedIcon from "@mui/icons-material/ImageOutlined";
import UploadOutlinedIcon from "@mui/icons-material/UploadOutlined";
import TopBar from "../../TopBar";
import { contentEngineApi, currentUserId, workspacePayload } from "../login_register/content_engine_api";
import { useNavigate, useParams } from "react-router-dom";
import { AmbientWorking } from "../../components/VoiceSparkUI";

const CONTENT_TYPES = [
  ["social", "Still Image"],
  ["blog", "Blog"],
];

const GOALS = ["awareness", "engagement", "conversion", "retention"];

const emptyItemPlan = (week) => ({
  title: week?.theme || "Campaign",
  campaign_type: "Thought Leadership",
  theme: "",
  call_to_action: "",
  audience: "",
  timing: { duration: "1 week" },
  status_label: "",
  generate_on: "",
  thumbnail_url: "",
  reference_media: [],
  post_prompts: [],
  ...(week?.item_plan || {}),
});

const contentLabel = (type) => CONTENT_TYPES.find(([value]) => value === type)?.[1] || "Post";

const uniqueImages = (items = []) => {
  const seen = new Set();
  return items.filter((src) => {
    const value = String(src || "").trim();
    if (!value || seen.has(value)) return false;
    seen.add(value);
    return true;
  });
};

const toDateTimeLocal = (value) => {
  if (!value) return "";
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return `${text}T09:00`;
  if (text.includes("T")) return text.slice(0, 16);
  return "";
};

const goalLabel = (value = "") => String(value || "").replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());

const statusTone = (status = "") => {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "generated") return { bgcolor: "#ECFDF3", color: "#047857", borderColor: "#A7F3D0" };
  if (normalized === "approved") return { bgcolor: "#EFF6FF", color: "#1D4ED8", borderColor: "#BFDBFE" };
  if (normalized === "failed") return { bgcolor: "#FEF2F2", color: "#B91C1C", borderColor: "#FECACA" };
  return { bgcolor: "#F8FAFC", color: "#475569", borderColor: "#E2E8F0" };
};

function SectionCard({ title, subtitle, action, children, sx }) {
  return (
    <Box sx={{ border: "1px solid #E4E7EC", borderRadius: 2, bgcolor: "#fff", boxShadow: "0 12px 34px rgba(15,23,42,0.045)", overflow: "hidden", ...sx }}>
      <Box sx={{ px: { xs: 2, sm: 2.5 }, py: 2, borderBottom: "1px solid #EEF2F7", display: "flex", alignItems: { xs: "flex-start", sm: "center" }, justifyContent: "space-between", gap: 1.5, flexDirection: { xs: "column", sm: "row" } }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ fontWeight: 900, color: "#111827", lineHeight: 1.15 }}>{title}</Typography>
          {subtitle && <Typography sx={{ color: "#64748B", fontSize: 13, mt: 0.25 }}>{subtitle}</Typography>}
        </Box>
        {action}
      </Box>
      <Box sx={{ p: { xs: 2, sm: 2.5 } }}>{children}</Box>
    </Box>
  );
}

export default function CampaignDetailPage() {
  const { weekId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [week, setWeek] = useState(null);
  const [itemPlan, setItemPlan] = useState(null);
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState("");
  const [imagePicker, setImagePicker] = useState(null);
  const [addAnchor, setAddAnchor] = useState(null);
  const [regenTarget, setRegenTarget] = useState(null);
  const [regenInstruction, setRegenInstruction] = useState("");

  const promptCountText = useMemo(() => {
    const prompts = itemPlan?.post_prompts || [];
    const social = prompts.filter((prompt) => prompt.type === "social").length;
    const blog = prompts.filter((prompt) => prompt.type === "blog").length;
    return `${social} stills, ${blog} blog will generate${itemPlan?.generate_on ? ` on ${itemPlan.generate_on}` : ""}`;
  }, [itemPlan]);

  const loadCampaign = () => {
    setLoading(true);
    setError("");
    return contentEngineApi.fetchCampaignPlan()
      .then(({ data }) => {
        const found = (data?.weeks || []).find((item) => String(item.id) === String(weekId));
        if (!found) {
          setError("Campaign was not found.");
          return;
        }
        setWeek(found);
        setItemPlan(emptyItemPlan(found));
      })
      .catch((err) => setError(err.response?.data?.error || "Campaign could not be loaded."))
      .finally(() => setLoading(false));
  };

  const loadMedia = () => {
    setMediaLoading(true);
    return contentEngineApi.fetchMediaLibrary()
      .then(({ data }) => {
        const items = Array.isArray(data?.data) ? data.data : [];
        setMedia(items.map((item) => ({ id: item.id, src: item.src })));
      })
      .catch(() => setMedia([]))
      .finally(() => setMediaLoading(false));
  };

  useEffect(() => {
    loadCampaign();
    loadMedia();
  }, [weekId]);

  const patchItemPlan = (patch) => setItemPlan((prev) => ({ ...(prev || {}), ...patch }));
  const patchTiming = (patch) => patchItemPlan({ timing: { ...(itemPlan?.timing || {}), ...patch } });
  const updatePrompt = (index, patch) => {
    patchItemPlan({
      post_prompts: (itemPlan?.post_prompts || []).map((prompt, itemIndex) => itemIndex === index ? { ...prompt, ...patch } : prompt),
    });
  };

  const save = async () => {
    if (!week || !itemPlan) return null;
    setSaving(true);
    setError("");
    try {
      const { data } = await contentEngineApi.updateCampaignWeek(week.id, {
        theme: itemPlan.title,
        funnel_goal: week.funnel_goal,
        item_plan: itemPlan,
        status: week.status,
      });
      setWeek(data.week);
      setItemPlan(emptyItemPlan(data.week));
      return data.week;
    } catch (err) {
      setError(err.response?.data?.error || "Campaign could not be saved.");
      return null;
    } finally {
      setSaving(false);
    }
  };

  const generate = async () => {
    const saved = await save();
    if (!saved) return;
    setGenerating(true);
    try {
      await contentEngineApi.generateCampaignWeek(saved.id);
      navigate("/calendar");
    } catch (err) {
      setError(err.response?.data?.error || "Campaign generation could not start.");
    } finally {
      setGenerating(false);
    }
  };

  const deleteCampaign = async () => {
    if (!week || !window.confirm("Delete this campaign?")) return;
    setSaving(true);
    try {
      await contentEngineApi.deleteCampaignWeek(week.id);
      navigate("/content-plan");
    } catch (err) {
      setError(err.response?.data?.error || "Campaign could not be deleted.");
      setSaving(false);
    }
  };

  const addPrompt = (type = "social") => {
    const prompts = itemPlan?.post_prompts || [];
    const isSocial = type === "social";
    patchItemPlan({
      post_prompts: [
        ...prompts,
        {
          id: `draft-${Date.now()}`,
          type,
          topic: "",
          platforms: isSocial ? ["facebook", "instagram", "linkedin", "x"] : [],
          accounts: isSocial ? 0 : 0,
          connected_accounts: 0,
          connected_platforms: [],
          scheduled_at: itemPlan?.timing?.start_date || "",
          reference_image: "",
          status: "not_approved",
          position: prompts.length + 1,
        },
      ],
    });
    setAddAnchor(null);
  };

  const removePrompt = (index) => {
    patchItemPlan({ post_prompts: (itemPlan?.post_prompts || []).filter((_, itemIndex) => itemIndex !== index) });
  };

  const openImagePicker = (target) => {
    setImagePicker(target);
    if (!media.length) loadMedia();
  };

  const selectImage = (src) => {
    if (!imagePicker || !src) return;
    if (imagePicker.type === "campaign") {
      patchItemPlan({
        thumbnail_url: src,
        reference_media: Array.from(new Set([...(itemPlan?.reference_media || []), src])),
      });
    } else if (imagePicker.type === "prompt") {
      const prompt = (itemPlan?.post_prompts || [])[imagePicker.index] || {};
      const referenceImages = uniqueImages([src, ...(prompt.reference_images || []), ...(prompt.reference_media || [])]);
      updatePrompt(imagePicker.index, {
        reference_image: src,
        reference_images: referenceImages,
        reference_media: referenceImages,
      });
    }
    setImagePicker(null);
  };

  const uploadImage = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const preview = { id: `temp-${Date.now()}`, src: URL.createObjectURL(file), uploading: true };
    setMedia((prev) => [preview, ...prev]);
    try {
      const formData = new FormData();
      formData.append("image", file);
      formData.append("user_id", currentUserId());
      formData.append("workspace_id", workspacePayload().workspace_id);
      const { data } = await contentEngineApi.uploadMedia(formData);
      const saved = { id: data.id, src: data.image };
      setMedia((prev) => prev.map((item) => item.id === preview.id ? saved : item));
      selectImage(saved.src);
    } catch (err) {
      setMedia((prev) => prev.filter((item) => item.id !== preview.id));
      setError(err.response?.data?.error || "Image upload failed.");
    }
  };

  const runRegenerate = async () => {
    if (!regenInstruction.trim() || !regenTarget || !week) return;
    setRegenerating(true);
    setError("");
    try {
      const request = regenTarget.type === "campaign"
        ? contentEngineApi.regenerateCampaignWeek(week.id, regenInstruction.trim())
        : contentEngineApi.regenerateCampaignPrompt(week.id, regenTarget.promptId, regenInstruction.trim());
      const { data } = await request;
      setWeek(data.week);
      setItemPlan(emptyItemPlan(data.week));
      setRegenTarget(null);
      setRegenInstruction("");
    } catch (err) {
      setError(err.response?.data?.error || "Regeneration failed.");
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return <Box><TopBar title="Content Planner" /><Box sx={{ py: 12, display: "flex", justifyContent: "center" }}><CircularProgress /></Box></Box>;
  }

  if (!week || !itemPlan) {
    return <Box><TopBar title="Content Planner" /><Typography color="error">{error || "Campaign was not found."}</Typography></Box>;
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#F6F8FB", overflowX: "hidden" }}>
      <TopBar title="Content Planner" />
      <Box sx={{ width: "100%", maxWidth: 1440, mx: "auto", px: { xs: 1.5, sm: 2, lg: 3 }, py: { xs: 1.5, md: 2.5 } }}>
        <Box
          sx={{
            p: { xs: 2, sm: 2.5, md: 3 },
            color: "#fff",
            minHeight: { xs: 300, md: 260 },
            borderRadius: 2.5,
            overflow: "hidden",
            position: "relative",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            boxShadow: "0 24px 70px rgba(15,23,42,0.18)",
            background: "linear-gradient(135deg, #0F172A 0%, #1E293B 52%, #155E75 100%)",
          }}
        >
          <Stack direction={{ xs: "column", sm: "row" }} alignItems={{ xs: "flex-start", sm: "center" }} justifyContent="space-between" spacing={1.5} sx={{ mb: 3, position: "relative", zIndex: 1 }}>
            <Button
              onClick={() => navigate("/content-plan")}
              startIcon={<ArrowBackIcon />}
              sx={{ color: "#fff", textTransform: "none", px: 0, fontWeight: 700, "&:hover": { bgcolor: "transparent", textDecoration: "underline" } }}
            >
              Back to planner
            </Button>
            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", justifyContent: { xs: "flex-start", sm: "flex-end" }, rowGap: 1, maxWidth: "100%" }}>
              <Chip label={itemPlan.campaign_type || "Thought Leadership"} size="small" sx={{ bgcolor: "rgba(255,255,255,.13)", color: "#fff", border: "1px solid rgba(255,255,255,.24)", backdropFilter: "blur(10px)", fontWeight: 800 }} />
              <Chip label={goalLabel(week.funnel_goal || "awareness")} size="small" sx={{ bgcolor: "#F8FAFC", color: "#0F172A", fontWeight: 900 }} />
            </Stack>
          </Stack>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) 260px" }, gap: { xs: 2.5, md: 3 }, alignItems: "end", position: "relative", zIndex: 1 }}>
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ color: "#67E8F9", fontSize: 12, fontWeight: 900, letterSpacing: 0, textTransform: "uppercase", mb: 1 }}>
                Week {week.week_number || ""} Campaign
              </Typography>
              <TextField
                fullWidth
                multiline
                maxRows={3}
                variant="standard"
                value={itemPlan.title || ""}
                onChange={(event) => patchItemPlan({ title: event.target.value })}
                placeholder="Campaign title"
                InputProps={{
                  disableUnderline: true,
                  sx: {
                    color: "#fff",
                    alignItems: "flex-start",
                    "& textarea": {
                      color: "#fff",
                      fontSize: { xs: 28, sm: 36, lg: 46 },
                      fontWeight: 950,
                      letterSpacing: 0,
                      lineHeight: 1.06,
                      p: 0,
                      textShadow: "0 3px 20px rgba(0,0,0,.36)",
                    },
                  },
                }}
              />
              <Typography sx={{ color: "rgba(255,255,255,.86)", fontSize: { xs: 13, md: 14 }, mt: 1.5, maxWidth: 760, lineHeight: 1.55 }}>
                Shape the weekly plan, reference images, post topics, and schedule before sending it to Calendar.
              </Typography>
            </Box>
            <Box
              sx={{
                display: { xs: itemPlan.thumbnail_url ? "block" : "none", md: "block" },
                justifySelf: { xs: "stretch", md: "end" },
                width: { xs: "100%", md: 250 },
                border: "1px solid rgba(255,255,255,.18)",
                borderRadius: 2,
                p: 1,
                bgcolor: "rgba(255,255,255,.08)",
                boxShadow: "0 18px 48px rgba(0,0,0,.22)",
              }}
            >
              <Box
                component={itemPlan.thumbnail_url ? "img" : "div"}
                src={itemPlan.thumbnail_url || undefined}
                alt=""
                sx={{
                  width: "100%",
                  aspectRatio: { xs: "16 / 8", md: "4 / 3" },
                  borderRadius: 1.5,
                  objectFit: "cover",
                  display: "block",
                  bgcolor: "rgba(255,255,255,.12)",
                  background: itemPlan.thumbnail_url ? undefined : "linear-gradient(135deg, rgba(255,255,255,.18), rgba(255,255,255,.04))",
                }}
              />
            </Box>
          </Box>
        </Box>

        <Box sx={{ py: 3 }}>
          {error && <Box sx={{ mb: 2, border: "1px solid #FECACA", bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: 2, p: 2, fontWeight: 700 }}>{error}</Box>}

          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 330px", xl: "minmax(0, 1fr) 350px" }, gap: { xs: 2, lg: 2.5 }, alignItems: "start" }}>
            <Stack spacing={2.5}>
              <SectionCard
                title="Campaign Details"
                subtitle="Edit the core strategy and buyer angle for this week."
                action={<Typography sx={{ color: "#94A3B8", fontSize: 12 }}>Auto-saves only when you click Save</Typography>}
              >
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "150px minmax(0, 1fr)" }, gap: { xs: 1.25, md: 2 }, alignItems: "start" }}>
                  <Typography sx={{ color: "#64748B", fontSize: 13, pt: 1 }}>Theme</Typography>
                  <TextField multiline minRows={4} value={itemPlan.theme || ""} onChange={(e) => patchItemPlan({ theme: e.target.value })} size="small" placeholder="What this week is about..." sx={{ minWidth: 0 }} />
                  <Typography sx={{ color: "#64748B", fontSize: 13, pt: 1 }}>Call to Action</Typography>
                  <TextField value={itemPlan.call_to_action || ""} onChange={(e) => patchItemPlan({ call_to_action: e.target.value })} size="small" placeholder="Example: Book a consultation" sx={{ minWidth: 0 }} />
                  <Typography sx={{ color: "#64748B", fontSize: 13, pt: 1 }}>Audience</Typography>
                  <TextField value={itemPlan.audience || ""} onChange={(e) => patchItemPlan({ audience: e.target.value })} size="small" placeholder="Primary customer segment" sx={{ minWidth: 0 }} />
                  <Typography sx={{ color: "#64748B", fontSize: 13, pt: 1 }}>Funnel Goal</Typography>
                  <Select size="small" value={week.funnel_goal || "awareness"} onChange={(e) => setWeek((prev) => ({ ...prev, funnel_goal: e.target.value }))} sx={{ minWidth: 0 }}>
                    {GOALS.map((goal) => <MenuItem value={goal} key={goal}>{goalLabel(goal)}</MenuItem>)}
                  </Select>
                </Box>
              </SectionCard>

              <SectionCard
                title="Images"
                subtitle="Use campaign and prompt-level reference images for better visual output."
                action={
                  <Button size="small" variant="outlined" startIcon={<ImageOutlinedIcon />} onClick={() => openImagePicker({ type: "campaign" })} sx={{ textTransform: "none", borderRadius: 2 }}>
                    Change image
                  </Button>
                }
              >
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", sm: "repeat(3, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))", xl: "repeat(6, minmax(0, 1fr))" }, gap: 1.5 }}>
                  {uniqueImages([itemPlan.thumbnail_url, ...(itemPlan.reference_media || [])]).map((src, index) => (
                    <Box key={`${src}-${index}`} component="img" src={src} sx={{ width: "100%", aspectRatio: "16 / 10", borderRadius: 2, objectFit: "cover", border: "1px solid #E5E7EB", bgcolor: "#F8FAFC" }} />
                  ))}
                  <Button onClick={() => openImagePicker({ type: "campaign" })} sx={{ width: "100%", aspectRatio: "16 / 10", border: "1px dashed #CBD5E1", borderRadius: 2, color: "#64748B", bgcolor: "#F8FAFC" }}>
                    <AddIcon />
                  </Button>
                </Box>
              </SectionCard>

              <SectionCard
                title="Post Topics"
                subtitle="Review each planned post before generation."
                action={
                  <Button size="small" variant="contained" startIcon={<AddIcon />} onClick={(e) => setAddAnchor(e.currentTarget)} sx={{ bgcolor: "#111827", textTransform: "none", borderRadius: 2, "&:hover": { bgcolor: "#334155" } }}>
                    Add Post
                  </Button>
                }
              >
                <Stack spacing={1.75}>
                  {(itemPlan.post_prompts || []).map((prompt, index) => {
                    const needsAccount = prompt.type !== "blog";
                    return (
                      <Box
                        key={prompt.id || index}
                        sx={{
                          display: "grid",
                          gridTemplateColumns: { xs: "1fr", sm: "84px minmax(0, 1fr)", xl: "96px minmax(0, 1fr) auto" },
                          gap: 1.5,
                          alignItems: "start",
                          border: "1px solid #E5E7EB",
                          borderRadius: 2,
                          p: 1.5,
                          bgcolor: "#FCFCFD",
                        }}
                      >
                        <Button
                          onClick={() => openImagePicker({ type: "prompt", index })}
                          sx={{ width: { xs: "100%", sm: 84 }, height: { xs: 140, sm: 84 }, borderRadius: 2, bgcolor: "#F1F5F9", color: "#94A3B8", overflow: "hidden", p: 0, border: "1px dashed #CBD5E1" }}
                        >
                          {prompt.reference_image ? <Box component="img" src={prompt.reference_image} sx={{ width: "100%", height: "100%", objectFit: "cover" }} /> : <AddIcon />}
                        </Button>
                        <Box>
                          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: "wrap", rowGap: 1 }}>
                            <Chip label={`Post ${index + 1}`} size="small" sx={{ bgcolor: "#111827", color: "#fff", fontWeight: 800 }} />
                            <Chip label={contentLabel(prompt.type)} size="small" variant="outlined" />
                            <Chip label={prompt.status || "not_approved"} size="small" variant="outlined" />
                          </Stack>
                          <TextField fullWidth multiline minRows={2} size="small" value={prompt.topic || ""} onChange={(e) => updatePrompt(index, { topic: e.target.value })} placeholder="Post topic or blog idea" />
                          <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: "wrap", rowGap: 1, "& > *": { maxWidth: "100%" } }}>
                            <Select size="small" value={prompt.type || "social"} onChange={(e) => updatePrompt(index, { type: e.target.value })} sx={{ minWidth: 130 }}>
                              {CONTENT_TYPES.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
                            </Select>
                            <TextField size="small" type="datetime-local" value={toDateTimeLocal(prompt.scheduled_at)} onChange={(e) => updatePrompt(index, { scheduled_at: e.target.value })} sx={{ minWidth: { xs: "100%", sm: 210 } }} />
                            <Chip label={needsAccount ? `${prompt.connected_accounts ?? prompt.accounts ?? 0} account${Number(prompt.connected_accounts ?? prompt.accounts ?? 0) === 1 ? "" : "s"} connected` : "No social account needed"} size="small" sx={{ alignSelf: "center", bgcolor: "#F8FAFC" }} />
                          </Stack>
                        </Box>
                        <Stack direction="row" justifyContent="flex-end" sx={{ gridColumn: { xs: "1", sm: "2", xl: "auto" } }}>
                          <IconButton size="small" onClick={() => setRegenTarget({ type: "prompt", promptId: prompt.id })}><AutorenewIcon fontSize="small" /></IconButton>
                          <IconButton size="small" onClick={() => removePrompt(index)}><DeleteOutlineIcon fontSize="small" /></IconButton>
                        </Stack>
                      </Box>
                    );
                  })}
                  {!(itemPlan.post_prompts || []).length && (
                    <Box sx={{ border: "1px dashed #CBD5E1", borderRadius: 2, p: 4, textAlign: "center", color: "#64748B", bgcolor: "#F8FAFC" }}>
                      No post topics yet. Add a post to start building this week.
                    </Box>
                  )}
                </Stack>
              </SectionCard>
            </Stack>
            <Box sx={{ position: { lg: "sticky" }, top: { lg: 88 } }}>
              <SectionCard title="Week Controls" subtitle="Save changes before generating.">
                <Stack spacing={1.25}>
                  <Chip label={itemPlan.status_label || week.status} size="small" variant="outlined" sx={{ justifyContent: "center", fontWeight: 800, ...statusTone(itemPlan.status_label || week.status) }} />
                  <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "1fr" }, gap: 1 }}>
                    <TextField label="Starts on" type="date" size="small" value={itemPlan.timing?.start_date || ""} onChange={(e) => patchTiming({ start_date: e.target.value })} InputLabelProps={{ shrink: true }} />
                    <TextField label="Runs for" size="small" value={itemPlan.timing?.duration || "1 week"} onChange={(e) => patchTiming({ duration: e.target.value })} />
                  </Box>
                  <Box sx={{ border: "1px solid #EEF2F7", borderRadius: 2, p: 1.5, bgcolor: "#F8FAFC" }}>
                    <Typography sx={{ color: "#64748B", fontSize: 12 }}>Content count</Typography>
                    <Typography sx={{ fontWeight: 800, color: "#111827", mt: 0.25 }}>{promptCountText}</Typography>
                  </Box>
                  <Button onClick={() => setRegenTarget({ type: "campaign" })} startIcon={<AutorenewIcon />} variant="outlined" sx={{ textTransform: "none", borderRadius: 2 }}>
                    Regenerate campaign
                  </Button>
                  <Button onClick={save} disabled={saving || generating} variant="outlined" sx={{ textTransform: "none", borderRadius: 2, color: "#111827", borderColor: "#CBD5E1" }}>Save changes</Button>
                  <Button onClick={generate} disabled={saving || generating} variant="contained" sx={{ bgcolor: "#111827", textTransform: "none", borderRadius: 2, py: 1.1, "&:hover": { bgcolor: "#334155" } }}>
                    {generating ? "Starting..." : "Generate Campaign"}
                  </Button>
                  <Divider />
                  <Button onClick={deleteCampaign} color="error" variant="text" sx={{ textTransform: "none" }}>
                    Delete this campaign
                  </Button>
                </Stack>
              </SectionCard>
            </Box>
          </Box>
        </Box>
      </Box>

      <Menu anchorEl={addAnchor} open={Boolean(addAnchor)} onClose={() => setAddAnchor(null)}>
        {CONTENT_TYPES.map(([value, label]) => (
          <MenuItem key={value} onClick={() => addPrompt(value)}>{label}</MenuItem>
        ))}
      </Menu>

      <Dialog open={Boolean(imagePicker)} onClose={() => setImagePicker(null)} maxWidth="md" fullWidth>
        <DialogTitle>Select Image</DialogTitle>
        <DialogContent>
          <input ref={fileInputRef} type="file" accept="image/*" hidden onChange={uploadImage} />
          <Button startIcon={<UploadOutlinedIcon />} onClick={() => fileInputRef.current?.click()} variant="outlined" sx={{ mb: 2, textTransform: "none" }}>
            Upload image
          </Button>
          {mediaLoading ? (
            <Box sx={{ py: 5, display: "flex", justifyContent: "center" }}><CircularProgress /></Box>
          ) : (
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 1.5 }}>
              {media.map((item) => (
                <Button key={item.id} onClick={() => selectImage(item.src)} sx={{ p: 0, borderRadius: 1.5, overflow: "hidden", border: "1px solid #E5E7EB" }}>
                  <Box component="img" src={item.src} sx={{ width: "100%", height: 110, objectFit: "cover" }} />
                </Button>
              ))}
              {!media.length && (
                <Box sx={{ border: "1px dashed #CBD5E1", borderRadius: 1.5, p: 4, textAlign: "center", color: "#64748B" }}>
                  No images yet. Upload one to use it in this campaign.
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions><Button onClick={() => setImagePicker(null)}>Cancel</Button></DialogActions>
      </Dialog>

      <Dialog open={Boolean(regenTarget)} onClose={() => !regenerating && setRegenTarget(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{regenTarget?.type === "campaign" ? "Regenerate campaign" : "Regenerate prompt"}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            minRows={4}
            value={regenInstruction}
            onChange={(event) => setRegenInstruction(event.target.value)}
            placeholder="Describe how you want this changed..."
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegenTarget(null)} disabled={regenerating}>Cancel</Button>
          <Button onClick={runRegenerate} disabled={regenerating || !regenInstruction.trim()} variant="contained" sx={{ bgcolor: "#111", textTransform: "none", "&:hover": { bgcolor: "#333" } }}>
            {regenerating ? "Regenerating..." : "Regenerate"}
          </Button>
        </DialogActions>
      </Dialog>
      <AmbientWorking
        active={generating || regenerating || saving || mediaLoading}
        title={generating ? "Generating campaign" : regenerating ? "Regenerating post" : saving ? "Saving campaign" : "Loading media"}
        detail="Voice Spark is working in the background so the planner stays usable."
      />
    </Box>
  );
}
