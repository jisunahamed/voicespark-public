import React, { useEffect, useState, useRef } from "react";
import { Box, Typography, Button, TextField, Collapse } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { useNavigate } from "react-router-dom";
import useAppStore from "./constants";
import { contentEngineApi } from "./content_engine_api";
import { AmbientWorking } from "../../components/VoiceSparkUI";
const MAX_TOPIC_POLL_ATTEMPTS = 40;

const voiceSparkError = (message, fallback = "Voice Spark AI generation failed. Please retry.") => {
  const text = String(message || fallback);
  return text
    .replaceAll("GEMINI_API_KEY", "Voice Spark AI key")
    .replaceAll("GOOGLE_API_KEY", "Voice Spark AI key")
    .replaceAll("Gemini", "Voice Spark AI")
    .replaceAll("gemini", "Voice Spark AI");
};
// ─── Icons ────────────────────────────────────────────────────────────────────

const HeartIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#333" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
);

const PenIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#333" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
  </svg>
);

// ─── Topic Item ───────────────────────────────────────────────────────────────

function TopicItem({ text, onChange, onDelete, isLink }) {
  const [editing, setEditing] = useState(false);

  return (
    <Box
      sx={{
        border: "1px solid #e8e8e8",
        borderRadius: "10px",
        px: 2,
        py: 1.2,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        bgcolor: "#fff",
        "&:hover .delete-btn": { opacity: 1 },
        cursor: "text",
      }}
      onClick={() => setEditing(true)}
    >
      {editing ? (
        <TextField
          value={text}
          onChange={(e) => onChange(e.target.value)}
          onBlur={() => setEditing(false)}
          autoFocus
          variant="standard"
          fullWidth
          InputProps={{ disableUnderline: true }}
          sx={{ "& input": { fontSize: 14, color: "#333", p: 0 } }}
        />
      ) : (
        <Typography
          sx={{
            fontSize: 14,
            color: isLink ? "#4a6fa5" : "#333",
            lineHeight: 1.5,
            flex: 1,
          }}
        >
          {text}
        </Typography>
      )}
      <Box
        className="delete-btn"
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        sx={{
          opacity: 0, ml: 1, cursor: "pointer", flexShrink: 0,
          color: "#bbb", fontSize: 16, lineHeight: 1,
          "&:hover": { color: "#888" },
          transition: "opacity 0.15s",
        }}
      >
        ✕
      </Box>
    </Box>
  );
}

// ─── Topic Section ────────────────────────────────────────────────────────────

function TopicSection({ icon, title, topics, setTopics, loading = false, emptyText = "No topics planned." }) {
  const [showAll, setShowAll] = useState(false);
  const [addingNew, setAddingNew] = useState(false);
  const [newTopic, setNewTopic] = useState("");

  const visibleTopics = showAll ? topics : topics.slice(0, 5);
  const hiddenCount = topics.length - 5;

  const handleAdd = () => {
    if (newTopic.trim()) {
      setTopics([...topics, newTopic.trim()]);
      setNewTopic("");
    }
    setAddingNew(false);
  };

  const handleDelete = (idx) => {
    setTopics(topics.filter((_, i) => i !== idx));
  };

  const handleChange = (idx, val) => {
    const updated = [...topics];
    updated[idx] = val;
    setTopics(updated);
  };

  return (
    <Box sx={{ mb: 4 }}>
      {/* Section header */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {icon}
          <Typography sx={{ fontSize: 18, fontWeight: 600, color: "#111" }}>{title}</Typography>
        </Box>
        <Button
          startIcon={<AddIcon sx={{ fontSize: 14 }} />}
          onClick={() => setAddingNew(true)}
          sx={{
            textTransform: "none", fontSize: 13, color: "#555", fontWeight: 400,
            "&:hover": { bgcolor: "transparent", color: "#111" }, p: 0, minWidth: 0,
          }}
        >
          Add Topic
        </Button>
      </Box>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {!topics.length && (
          <Box sx={{ border: "1px dashed #E5E7EB", borderRadius: "10px", px: 2, py: 2, bgcolor: "#FAFAFA" }}>
            <Typography sx={{ fontSize: 13, color: "#777" }}>{loading ? "Generating topics..." : emptyText}</Typography>
          </Box>
        )}
        {visibleTopics.map((topic, idx) => (
          <TopicItem
            key={idx}
            text={topic}
            isLink={title === "Blog"}
            onChange={(val) => handleChange(idx, val)}
            onDelete={() => handleDelete(idx)}
          />
        ))}

        {/* New topic input */}
        {addingNew && (
          <Box sx={{ border: "1.5px solid #111", borderRadius: "10px", px: 2, py: 1.2 }}>
            <TextField
              placeholder="Enter a topic..."
              value={newTopic}
              onChange={(e) => setNewTopic(e.target.value)}
              onBlur={handleAdd}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              autoFocus
              variant="standard"
              fullWidth
              InputProps={{ disableUnderline: true }}
              sx={{ "& input": { fontSize: 14, color: "#333", p: 0 } }}
            />
          </Box>
        )}
      </Box>

      {/* Show more / less */}
      {topics.length > 5 && (
        <Box
          onClick={() => setShowAll(!showAll)}
          sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0.5, mt: 1.5, cursor: "pointer" }}
        >
          <Typography sx={{ fontSize: 13, color: "#555" }}>
            {showAll ? "Show Less" : `Show ${hiddenCount} More`}
          </Typography>
          {showAll
            ? <KeyboardArrowUpIcon sx={{ fontSize: 16, color: "#555" }} />
            : <KeyboardArrowDownIcon sx={{ fontSize: 16, color: "#555" }} />
          }
        </Box>
      )}
    </Box>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function ReviewTopicsPage({ onBack, onGenerate }) {
  const { setWeeklyTopics, blogEmailPlan, setBlogEmailPlan } = useAppStore();
  const [socialTopics, setSocialTopics] = useState([]);
  const [blogTopics, setBlogTopics] = useState([]);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [topicError, setTopicError] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const loadTopics = React.useCallback(async (cancelledRef = { current: false }) => {
    setLoadingTopics(true);
    setTopicError("");
    for (let attempt = 0; attempt <= MAX_TOPIC_POLL_ATTEMPTS; attempt += 1) {
      try {
        const { data } = await contentEngineApi.generateTopics();
        if (cancelledRef.current) return;
        if (["queued", "running"].includes(data?.generation_status)) {
          if (attempt >= MAX_TOPIC_POLL_ATTEMPTS) {
            setTopicError("Topic generation is taking longer than expected. Please retry or add topics manually.");
            if (!cancelledRef.current) setLoadingTopics(false);
            return { pending: false, timedOut: true };
          }
          await new Promise((resolve) => window.setTimeout(resolve, 3500));
          continue;
        }
        const allTopics = data.content_plan?.topics || [];
        const social = allTopics.filter((item) => item.kind === "social").map((item) => item.title);
        const blog = allTopics.filter((item) => item.kind === "blog").map((item) => item.title);
        setSocialTopics(social);
        setBlogTopics(blog);
        if (!social.length && !blog.length) {
          setTopicError("No social topics were generated. Try again or add topics manually.");
        }
        if (!cancelledRef.current) setLoadingTopics(false);
        return { pending: false };
      } catch (error) {
        if (cancelledRef.current) return;
        const message = voiceSparkError(error?.response?.data?.error, "Topic generation failed. Please try again.");
        setTopicError(message);
        if (!cancelledRef.current) setLoadingTopics(false);
        return { pending: false, failed: true };
      }
    }
    if (!cancelledRef.current) setLoadingTopics(false);
    return { pending: false };
  }, []);

  useEffect(() => {
    const cancelledRef = { current: false };
    const topicsPromise = loadTopics(cancelledRef);
    topicsPromise.then((result) => {
      if (result?.pending) return Promise.resolve({ data: null });
      return contentEngineApi.blogEmailPlan();
    })
      .then(({ data }) => {
        if (cancelledRef.current || !data) return;
        setBlogEmailPlan(data);
        const blogItems = data?.blog_plan?.items || (data?.blog_plan?.title ? [data.blog_plan] : []);
        setBlogTopics((prev) => prev.length ? prev : blogItems.map((item) => item.title).filter(Boolean));
      })
      .catch((error) => {
        if (cancelledRef.current) return;
        const message = voiceSparkError(error?.response?.data?.error, "Blog plan generation failed. Please try again.");
        setTopicError((previous) => previous || message);
      });

    return () => {
      cancelledRef.current = true;
    };
  }, [loadTopics, setBlogEmailPlan]);

  const hasFetched = useRef(false);
  const user = JSON.parse(localStorage.getItem('user'));
  const handleNavigate = async () => {
    if (hasFetched.current) return;
    hasFetched.current = true;
    setSaving(true);
    try {
      const topics = [
        ...socialTopics.map((title, index) => ({ title, position: index + 1, kind: "social", week_number: 1 })),
        ...blogTopics.map((title, index) => ({ title, position: index + 1, kind: "blog", week_number: 1 })),
      ];
      setWeeklyTopics(topics);
      await contentEngineApi.generateTopics({ topics });

      const { data: generatedBlogPlan } = await contentEngineApi.blogEmailPlan();
      setBlogEmailPlan(generatedBlogPlan);
      contentEngineApi.generateFirstWeek().catch((error) => {
        console.error("First week generation failed:", error);
      });
      navigate('/home', { replace: true });
    } catch (error) {
      console.error("Failed to start first week generation:", error);
      hasFetched.current = false;
      setSaving(false);
    }
  };


  return (
    <Box className="voice-onboarding-page" sx={{ display: "flex", minHeight: "100vh" }}>
      <Box sx={{ flex: 1, px: { xs: 3, md: 14 }, pt: 6, pb: "80px", maxWidth: 800, mx: "auto" }}>

        {/* Header */}
        <Typography sx={{ fontSize: { xs: 22, md: 28 }, fontWeight: 700, color: "#111", mb: 0.5, letterSpacing: "-0.5px" }}>
          Review topics for your first week
        </Typography>
        <Typography sx={{ fontSize: 14, color: "#aaa", mb: 4, maxWidth: 580, lineHeight: 1.6 }}>
          {loadingTopics ? "Generating AI topics from your business profile, brand style, platforms, and content plan..." : "Make sure these topics reflect your business goals and themes. Then generate and track the posts in Calendar."}
        </Typography>
        {loadingTopics && (
          <Box sx={{ mb: 3, border: "1px solid #EDE9FE", bgcolor: "#F5F3FF", borderRadius: 2, p: 2 }}>
            <Typography sx={{ fontSize: 14, fontWeight: 700, color: "#4C1D95" }}>Generating...</Typography>
            <Typography sx={{ fontSize: 13, color: "#6D28D9", mt: 0.5 }}>
              Creating social and blog topics from your business profile. You can add or edit topics while this runs.
            </Typography>
          </Box>
        )}
        {topicError && (
          <Box sx={{ mb: 3, border: "1px solid #ffd6d6", bgcolor: "#fff7f7", color: "#9b1c1c", borderRadius: 2, p: 2 }}>
            <Typography sx={{ fontSize: 14, mb: 1 }}>{topicError}</Typography>
            <Button
              onClick={() => loadTopics()}
              disabled={loadingTopics}
              sx={{ textTransform: "none", color: "#111", p: 0, minWidth: 0, fontWeight: 600 }}
            >
              Retry topic generation
            </Button>
          </Box>
        )}

        {/* Social Media */}
        <TopicSection
          icon={<HeartIcon />}
          title="Social Media"
          topics={socialTopics}
          setTopics={setSocialTopics}
          loading={loadingTopics}
          emptyText="No social topics planned."
        />

        <Box sx={{ height: "1px", bgcolor: "#f0f0f0", mb: 4 }} />

        {/* Blog */}
        <TopicSection
          icon={<PenIcon />}
          title="Blog"
          topics={blogTopics}
          setTopics={setBlogTopics}
          loading={loadingTopics}
          emptyText="No blog planned this week."
        />

        <Box sx={{ height: "1px", bgcolor: "#f0f0f0", mb: 4 }} />

      </Box>

      {/* Footer */}
      <Box
        sx={{
          position: "fixed", bottom: 0, left: 0, right: 0,
          display: "flex", justifyContent: "space-between", alignItems: "center",
          px: 4, py: 2,
          borderTop: "1px solid #e0e0e0",
          bgcolor: "#fff",
        }}
      >
        {/* <Button onClick={onBack} sx={{ color: "#555", textTransform: "none", fontWeight: 400, fontSize: 14 }}>
          Back
        </Button> */}
        <Button
          variant="contained"
          onClick={handleNavigate}
          disabled={saving}
          // component={Link} 
          // to='/home'
          sx={{
            ml:"auto",
            bgcolor: "#111", color: "#fff", textTransform: "none",
            borderRadius: "8px", fontWeight: 500, fontSize: 14, px: 3,
            "&:hover": { bgcolor: "#333" },
            "&.Mui-disabled": { bgcolor: "#333", color: "#fff" },
          }}
        >
          {saving ? "Starting generation..." : "Generate my first week of content"}
        </Button>
      </Box>
      <AmbientWorking
        active={loadingTopics || saving}
        title={loadingTopics ? "Generating topics" : "Starting first week generation"}
        detail="This runs without blocking the rest of your workflow."
      />
    </Box>
  );
}
