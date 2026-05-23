import React, { useEffect, useState } from "react";
import { Box, Button, Chip, MenuItem, Select, Skeleton, TextField, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { contentEngineApi } from "./content_engine_api";
import { AmbientWorking } from "../../components/VoiceSparkUI";

const GOALS = ["awareness", "engagement", "conversion", "retention"];
const MAX_POLL_ATTEMPTS = 40;

const voiceSparkError = (message, fallback = "Voice Spark AI generation failed. Please retry.") => {
  const text = String(message || fallback);
  return text
    .replaceAll("GEMINI_API_KEY", "Voice Spark AI key")
    .replaceAll("GOOGLE_API_KEY", "Voice Spark AI key")
    .replaceAll("Gemini", "Voice Spark AI")
    .replaceAll("gemini", "Voice Spark AI");
};

const emptyWeek = (index) => ({
  week_number: index + 1,
  theme: "",
  funnel_goal: GOALS[index] || "awareness",
  status: index === 0 ? "approved" : "draft",
  item_plan: {},
});

function CampaignPlanLoading() {
  return (
    <Box sx={{ border: "1px solid #E5E7EB", bgcolor: "#fff", borderRadius: 3, p: { xs: 3, md: 4 }, overflow: "hidden" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <Box
          sx={{
            width: 42,
            height: 42,
            borderRadius: "50%",
            border: "3px solid #E5E7EB",
            borderTopColor: "#111",
            animation: "voiceSpin 1s linear infinite",
            "@keyframes voiceSpin": { to: { transform: "rotate(360deg)" } },
          }}
        />
        <Box>
          <Typography sx={{ fontSize: 20, fontWeight: 900, color: "#111" }}>
            VoiceSpark is creating your 4-week content plan.
          </Typography>
          <Typography sx={{ fontSize: 14, color: "#6B7280", mt: 0.5 }}>
            Analyzing your brand, audience, and campaign goals...
          </Typography>
        </Box>
      </Box>
      <Typography sx={{ fontSize: 13, color: "#6B7280", mb: 2 }}>
        Preparing Week 1 topics first. Weeks 2-4 will stay editable for review.
      </Typography>
      <Box sx={{ display: "grid", gap: 1.25 }}>
        {[0, 1, 2, 3].map((item) => (
          <Skeleton key={item} variant="rounded" height={58} sx={{ borderRadius: 2 }} />
        ))}
      </Box>
    </Box>
  );
}

export default function CampaignPlannerPage() {
  const navigate = useNavigate();
  const [weeks, setWeeks] = useState(Array.from({ length: 4 }, (_, index) => emptyWeek(index)));
  const [initialLoading, setInitialLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    let pollTimer;
    let attempts = 0;
    let generationRequested = false;
    const load = async () => {
      if (attempts === 0) {
        setInitialLoading(true);
      } else {
        setPolling(true);
      }
      try {
        let { data } = await contentEngineApi.fetchCampaignPlan();
        if (!active) return;
        if ((!Array.isArray(data?.weeks) || !data.weeks.length) && !generationRequested) {
          generationRequested = true;
          const started = await contentEngineApi.generateCampaignPlan();
          data = started.data;
        }
        const nextWeeks = Array.isArray(data?.weeks) && data.weeks.length
          ? data.weeks
          : Array.from({ length: 4 }, (_, index) => emptyWeek(index));
        const mapped = nextWeeks.map((week, index) => ({
          ...emptyWeek(index),
          ...week,
          week_number: index + 1,
          status: index === 0 && week.status !== "generated" ? "approved" : (week.status || "draft"),
        }));
        setWeeks(mapped);
        const pending = mapped.some((week) => ["queued", "running"].includes(week.item_plan?.generation_status));
        const firstWeekPending = ["queued", "running"].includes(mapped[0]?.item_plan?.generation_status);
        const failed = mapped.find((week) => week.item_plan?.generation_status === "failed");
        setGeneratingPlan(firstWeekPending);
        if (failed) {
          setError(voiceSparkError(failed.item_plan?.generation_error, "Voice Spark AI campaign plan generation failed. Please retry."));
        } else if (pending && attempts >= MAX_POLL_ATTEMPTS) {
          setGeneratingPlan(false);
          setError("Campaign generation is taking longer than expected. Please retry or come back later.");
        } else {
          setError("");
        }
        if (pending && active && attempts < MAX_POLL_ATTEMPTS) {
          attempts += 1;
          pollTimer = setTimeout(load, 3500);
        }
      } catch (err) {
        if (active) setError(err.response?.data?.error || "Campaign plan could not be loaded.");
      } finally {
        if (active) {
          setInitialLoading(false);
          setPolling(false);
        }
      }
    };
    load();
    return () => {
      active = false;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [reloadKey]);

  const retryGeneration = async () => {
    setError("");
    setGeneratingPlan(true);
    setPolling(true);
    try {
      const { data } = await contentEngineApi.generateCampaignPlan();
      const nextWeeks = Array.isArray(data?.weeks) && data.weeks.length
        ? data.weeks
        : Array.from({ length: 4 }, (_, index) => emptyWeek(index));
      setWeeks(nextWeeks.map((week, index) => ({
        ...emptyWeek(index),
        ...week,
        week_number: index + 1,
        status: index === 0 && week.status !== "generated" ? "approved" : (week.status || "draft"),
      })));
      setReloadKey((value) => value + 1);
    } catch (err) {
      setError(err.response?.data?.error || "Campaign generation could not be started.");
    } finally {
      setPolling(false);
    }
  };

  const updateWeek = (index, patch) => {
    setWeeks((prev) => prev.map((week, itemIndex) => itemIndex === index ? { ...week, ...patch } : week));
  };

  const saveAndContinue = async () => {
    setSaving(true);
    setError("");
    try {
      const payload = weeks.map((week, index) => ({
        ...week,
        week_number: index + 1,
        status: index === 0 && week.status !== "generated" ? "approved" : week.status,
        item_plan: {
          ...(week.item_plan || {}),
          summary: week.item_plan?.summary || week.theme,
        },
      }));
      if (generatingPlan) {
        setError("Voice Spark AI is still creating your campaign plan. Please wait until it finishes.");
        return;
      }
      const firstWeek = payload[0];
      if (!firstWeek?.theme && !firstWeek?.item_plan?.title) {
        setError("Week 1 campaign plan is not ready yet. Retry generation before continuing.");
        return;
      }
      const { data } = await contentEngineApi.saveCampaignPlan(payload);
      const savedFirstWeek = data?.weeks?.find((week) => week.week_number === 1);
      if (savedFirstWeek?.id) {
        const approvalResponse = await contentEngineApi.approveCampaignWeek(savedFirstWeek.id);
        const generationStatus = approvalResponse?.data?.generation_status;
        if (!generationStatus) {
          // approval endpoint returned success but no explicit status; still continue safely
        }
      }
      navigate("/review-topic");
    } catch (err) {
      setError(err.response?.data?.error || "Campaign plan could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const hasPlanContent = weeks.some((week) => (
    week.theme
    || week.item_plan?.title
    || week.item_plan?.summary
    || week.item_plan?.topics?.length
  ));
  const hasQueuedPlan = weeks.some((week) => ["queued", "running"].includes(week.item_plan?.generation_status));
  const showPlanLoading = !error && !hasPlanContent && (initialLoading || polling || generatingPlan || hasQueuedPlan);

  return (
    <Box className="voice-onboarding-page" sx={{ minHeight: "100vh", px: { xs: 3, md: 12 }, py: 6, pb: 12 }}>
      <Box sx={{ maxWidth: 920, mx: "auto" }}>
        <Typography sx={{ fontSize: { xs: 28, md: 34 }, fontWeight: 800, color: "#111", mb: 1 }}>
          Plan your next 4 weeks
        </Typography>
        <Typography sx={{ fontSize: 15, color: "#6B7280", maxWidth: 680, lineHeight: 1.6, mb: 4 }}>
          Shape the campaign themes first. Week 1 will generate now; the next 3 weeks stay editable in Content Planner.
        </Typography>

        {error && (
          <Box sx={{ mb: 3, border: "1px solid #FECACA", bgcolor: "#FEF2F2", color: "#991B1B", borderRadius: 2, p: 2 }}>
            <Typography sx={{ fontSize: 14 }}>{error}</Typography>
            <Button onClick={retryGeneration} disabled={initialLoading || polling || generatingPlan} sx={{ mt: 1, p: 0, minWidth: 0, color: "#111", textTransform: "none", fontWeight: 700 }}>
              Retry campaign generation
            </Button>
          </Box>
        )}

        {showPlanLoading ? (
          <CampaignPlanLoading />
        ) : !hasPlanContent ? (
          <Box sx={{ border: "1px solid #E5E7EB", borderRadius: 3, p: 3, bgcolor: "#fff" }}>
            <Typography sx={{ fontWeight: 900, color: "#111", mb: 1 }}>Campaign plan is not ready yet.</Typography>
            <Typography sx={{ fontSize: 14, color: "#6B7280", mb: 2 }}>Retry generation to create the first editable week.</Typography>
            <Button variant="contained" onClick={retryGeneration} disabled={initialLoading || polling || generatingPlan} sx={{ bgcolor: "#111", textTransform: "none" }}>
              Retry campaign generation
            </Button>
          </Box>
        ) : (
          <Box sx={{ display: "grid", gap: 2 }}>
            {weeks.map((week, index) => (
              <Box key={week.id || index} sx={{ border: "1px solid #E5E7EB", borderRadius: 3, p: 2.5, bgcolor: "#fff" }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
                  <Chip label={`Week ${index + 1}`} sx={{ bgcolor: "#111", color: "#fff", fontWeight: 700 }} />
                  <Select
                    size="small"
                    value={week.funnel_goal || GOALS[index] || "awareness"}
                    onChange={(event) => updateWeek(index, { funnel_goal: event.target.value })}
                    sx={{ minWidth: 150, borderRadius: 2 }}
                  >
                    {GOALS.map((goal) => <MenuItem key={goal} value={goal}>{goal}</MenuItem>)}
                  </Select>
                  <Chip
                    label={
                      week.item_plan?.generation_status === "queued" ? "Queued"
                      : week.item_plan?.generation_status === "running" ? "Generating"
                      : week.item_plan?.generation_status === "failed" ? "Failed"
                      : index === 0 ? "Approved for first week" : week.status
                    }
                    size="small"
                    sx={{ ml: "auto", bgcolor: week.status === "generated" ? "#DCFCE7" : index === 0 || week.status === "approved" ? "#DBEAFE" : "#F3F4F6", color: "#111", textTransform: "capitalize" }}
                  />
                </Box>
                <TextField
                  fullWidth
                  label="Campaign theme"
                  value={week.theme}
                  onChange={(event) => updateWeek(index, { theme: event.target.value })}
                  sx={{ mb: 2 }}
                />
                <TextField
                  fullWidth
                  multiline
                  minRows={2}
                  label="What this week should cover"
                  value={week.item_plan?.summary || ""}
                  onChange={(event) => updateWeek(index, { item_plan: { ...(week.item_plan || {}), summary: event.target.value } })}
                />
              </Box>
            ))}
          </Box>
        )}
      </Box>

      <Box sx={{ position: "fixed", bottom: 0, left: 0, right: 0, borderTop: "1px solid #E5E7EB", bgcolor: "#fff", px: 4, py: 2, display: "flex" }}>
        <Button
          variant="contained"
          onClick={saveAndContinue}
          disabled={saving || initialLoading || generatingPlan}
          sx={{ ml: "auto", bgcolor: "#111", color: "#fff", textTransform: "none", borderRadius: 2, px: 3, "&:hover": { bgcolor: "#333" } }}
        >
          {saving ? "Saving..." : "Review first week topics"}
        </Button>
      </Box>
      <AmbientWorking
        active={showPlanLoading || saving}
        title={showPlanLoading ? "Creating campaign plan" : "Saving campaign plan"}
        detail={showPlanLoading ? "Blank week fields stay hidden until real plan data is ready." : "Saving your campaign plan."}
      />
    </Box>
  );
}
