import React, { useEffect, useMemo, useState } from "react";
import { Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, TextField, Typography } from "@mui/material";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import AddIcon from "@mui/icons-material/Add";
import TopBar from "../../TopBar";
import { contentEngineApi } from "../login_register/content_engine_api";
import { useNavigate } from "react-router-dom";
import { AmbientWorking } from "../../components/VoiceSparkUI";

const formatWeekRange = (week) => {
  const timing = week?.item_plan?.timing || {};
  if (timing.range_label) return timing.range_label;
  return `Week ${week.week_number}`;
};

const statusLabel = (week) => {
  if (week.status === "generated") return "Posting";
  if (week.item_plan?.status_label) return week.item_plan.status_label;
  return week.status === "approved" ? "Ready to generate" : "Draft";
};

const statusSx = (week) => {
  if (week.status === "generated") return { bgcolor: "#E0F2FE", color: "#0369A1", borderColor: "#BAE6FD" };
  if (week.status === "approved") return { bgcolor: "#F3F4F6", color: "#374151", borderColor: "#E5E7EB" };
  return { bgcolor: "#F9FAFB", color: "#6B7280", borderColor: "#E5E7EB" };
};

export default function ContentPlanPage() {
  const navigate = useNavigate();
  const [weeks, setWeeks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [createCount, setCreateCount] = useState(1);
  const [customCount, setCustomCount] = useState("");
  const [draggedId, setDraggedId] = useState("");
  const [error, setError] = useState("");

  const sortedWeeks = useMemo(
    () => [...weeks].sort((a, b) => (a.week_number || 0) - (b.week_number || 0)),
    [weeks],
  );

  const loadCampaigns = () => {
    setLoading(true);
    setError("");
    return contentEngineApi.fetchCampaignPlan()
      .then(({ data }) => setWeeks(data?.weeks || []))
      .catch((err) => setError(err.response?.data?.error || "Content planner could not be loaded."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    contentEngineApi.fetchCampaignPlan()
      .then(({ data }) => {
        if (active) setWeeks(data?.weeks || []);
      })
      .catch((err) => {
        if (active) setError(err.response?.data?.error || "Content planner could not be loaded.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const selectedCreateCount = createCount === "custom" ? Number(customCount || 0) : Number(createCount || 1);

  const createCampaigns = async () => {
    if (!selectedCreateCount || selectedCreateCount < 1) return;
    setCreating(true);
    setError("");
    try {
      await contentEngineApi.createCampaignBatch(selectedCreateCount);
      setCreateOpen(false);
      setCreateCount(1);
      setCustomCount("");
      await loadCampaigns();
    } catch (err) {
      setError(err.response?.data?.error || "Campaigns could not be created.");
    } finally {
      setCreating(false);
    }
  };

  const moveCampaign = async (targetId) => {
    if (!draggedId || draggedId === targetId) return;
    const current = [...sortedWeeks];
    const from = current.findIndex((week) => String(week.id) === String(draggedId));
    const to = current.findIndex((week) => String(week.id) === String(targetId));
    if (from < 0 || to < 0) return;
    const [item] = current.splice(from, 1);
    current.splice(to, 0, item);
    setWeeks(current);
    setDraggedId("");
    try {
      const { data } = await contentEngineApi.reorderCampaignPlan(current.map((week) => week.id));
      setWeeks(data?.weeks || current);
    } catch (err) {
      setError(err.response?.data?.error || "Campaign order could not be saved.");
      loadCampaigns();
    }
  };

  return (
    <Box>
      <TopBar title="Content Planner" />
      <Box sx={{ maxWidth: 980, mx: "auto", pt: 1 }}>
        <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
          <Button
            startIcon={<AddIcon />}
            onClick={() => setCreateOpen(true)}
            variant="contained"
            sx={{ bgcolor: "#111", textTransform: "none", borderRadius: 1.5, "&:hover": { bgcolor: "#333" } }}
          >
            Create New
          </Button>
        </Box>
        {error && (
          <Box sx={{ mb: 2, border: "1px solid #FECACA", bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: 2, p: 2 }}>
            <Typography sx={{ fontSize: 14 }}>{error}</Typography>
          </Box>
        )}

        {loading ? (
          <Box sx={{ py: 12, display: "flex", justifyContent: "center" }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ bgcolor: "#fff", borderRadius: 2, px: 2, py: 2 }}>
            <Box sx={{ display: "grid", gridTemplateColumns: "1.5fr 0.65fr 0.55fr 40px", gap: 2, px: 1, pb: 2 }}>
              <Typography sx={{ fontSize: 13, color: "#9CA3AF" }}>Campaign</Typography>
              <Typography sx={{ fontSize: 13, color: "#9CA3AF" }}>Timing</Typography>
              <Typography sx={{ fontSize: 13, color: "#9CA3AF" }}>Status</Typography>
              <Box />
            </Box>

            {sortedWeeks.map((week) => {
              const itemPlan = week.item_plan || {};
              const title = itemPlan.title || week.theme || `Week ${week.week_number} campaign`;
              const type = itemPlan.campaign_type || "Thought Leadership";
              return (
                <Box
                  key={week.id}
                  draggable
                  onDragStart={() => setDraggedId(week.id)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => moveCampaign(week.id)}
                  onClick={() => navigate(`/content-plan/${week.id}`)}
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "1.5fr 0.65fr 0.55fr 40px",
                    gap: 2,
                    alignItems: "center",
                    px: 1,
                    py: 1.25,
                    borderRadius: 2,
                    cursor: "pointer",
                    "&:hover": { bgcolor: "#F9FAFB" },
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2, minWidth: 0 }}>
                    <Box
                      component="img"
                      src={itemPlan.thumbnail_url}
                      alt=""
                      sx={{ width: 74, height: 74, objectFit: "cover", borderRadius: 1.25, bgcolor: "#F3F4F6", flexShrink: 0 }}
                    />
                    <Box sx={{ minWidth: 0 }}>
                      <Typography noWrap sx={{ fontSize: 16, fontWeight: 800, color: "#111827", maxWidth: 360 }}>
                        {title}
                      </Typography>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mt: 0.35 }}>
                        <ChatBubbleOutlineIcon sx={{ fontSize: 15, color: "#A78BFA" }} />
                        <Typography sx={{ color: "#6B7280", fontSize: 14 }}>{type}</Typography>
                      </Box>
                    </Box>
                  </Box>
                  <Typography sx={{ color: "#4B5563", fontSize: 14 }}>{formatWeekRange(week)}</Typography>
                  <Chip
                    label={statusLabel(week)}
                    size="small"
                    variant="outlined"
                    sx={{ justifySelf: "start", height: 26, fontWeight: 600, ...statusSx(week) }}
                  />
                  <IconButton size="small" sx={{ color: "#C4C4C4" }}>
                    <ChevronRightIcon />
                  </IconButton>
                </Box>
              );
            })}
          </Box>
        )}
      </Box>
      <Dialog open={createOpen} onClose={() => !creating && setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontSize: 26, fontWeight: 500, pb: 1 }}>Create New Campaign</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontWeight: 800, mb: 2 }}>How many campaigns do you want to create?</Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 1.25 }}>
            {[1, 2, 3, 4, 5].map((count) => (
              <Button
                key={count}
                variant={createCount === count ? "outlined" : "contained"}
                onClick={() => setCreateCount(count)}
                sx={{ bgcolor: createCount === count ? "#fff" : "#F9FAFB", color: "#111", borderColor: "#111", boxShadow: "none", textTransform: "none", "&:hover": { bgcolor: "#fff" } }}
              >
                {count}
              </Button>
            ))}
            <Button
              variant={createCount === "custom" ? "outlined" : "contained"}
              onClick={() => setCreateCount("custom")}
              sx={{ bgcolor: createCount === "custom" ? "#fff" : "#F9FAFB", color: "#111", borderColor: "#111", boxShadow: "none", textTransform: "none", "&:hover": { bgcolor: "#fff" } }}
            >
              Custom
            </Button>
          </Box>
          {createCount === "custom" && (
            <TextField
              fullWidth
              type="number"
              label="Custom campaign count"
              value={customCount}
              onChange={(event) => setCustomCount(event.target.value)}
              inputProps={{ min: 1, max: 24 }}
              sx={{ mt: 2 }}
            />
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={() => setCreateOpen(false)} disabled={creating} sx={{ color: "#111", textTransform: "none" }}>Cancel</Button>
          <Button onClick={createCampaigns} disabled={creating || selectedCreateCount < 1} variant="contained" sx={{ bgcolor: "#111", textTransform: "none", "&:hover": { bgcolor: "#333" } }}>
            {creating ? "Generating..." : "Generate Campaigns"}
          </Button>
        </DialogActions>
      </Dialog>
      <AmbientWorking active={creating} title="Generating campaigns" detail="You can keep reviewing the planner while campaigns are created." />
    </Box>
  );
}
