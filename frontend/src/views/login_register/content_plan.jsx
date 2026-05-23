import React, { useEffect, useMemo, useState } from "react";
import {
  Box, Typography, Button, Checkbox, Divider,
  Select, MenuItem,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import { useNavigate } from "react-router-dom";
import { Instagram, Facebook, LinkedIn, X } from "@mui/icons-material";
import useAppStore from "./constants";
import { contentEngineApi } from "./content_engine_api";
import { AmbientWorking } from "../../components/VoiceSparkUI";

const InstagramIcon = () => (
  <Box sx={{ width: 22, height: 22, borderRadius: "6px", background: "radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%,#d6249f 60%,#285AEB 90%)", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="5"/><circle cx="17.5" cy="6.5" r="1.5" fill="white" stroke="none"/></svg>
  </Box>
);

const FacebookIcon = () => (
  <Box sx={{ width: 22, height: 22, borderRadius: "50%", bgcolor: "#1877f2", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <Typography sx={{ color: "#fff", fontSize: 13, fontWeight: 700, lineHeight: 1 }}>f</Typography>
  </Box>
);

const LinkedInIcon = () => (
  <Box sx={{ width: 22, height: 22, borderRadius: "4px", bgcolor: "#0077b5", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <Typography sx={{ color: "#fff", fontSize: 10, fontWeight: 700, lineHeight: 1 }}>in</Typography>
  </Box>
);

const XIcon = () => (
  <Box sx={{ width: 22, height: 22, borderRadius: "50%", bgcolor: "#000", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <Typography sx={{ color: "#fff", fontSize: 11, fontWeight: 700, lineHeight: 1 }}>\U0001d54f</Typography>
  </Box>
);

const GoogleIcon = () => (
  <Box sx={{ width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center" }}>
    <svg width="18" height="18" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
  </Box>
);

const TikTokIcon = () => (
  <Box sx={{ width: 22, height: 22, borderRadius: "6px", bgcolor: "#000", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <Typography sx={{ color: "#fff", fontSize: 11, fontWeight: 700 }}>\u266a</Typography>
  </Box>
);

const YouTubeIcon = () => (
  <Box sx={{ width: 22, height: 22, borderRadius: "4px", bgcolor: "#ff0000", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <svg width="12" height="12" viewBox="0 0 24 24" fill="white"><polygon points="5,3 19,12 5,21"/></svg>
  </Box>
);

const MetaIcon = () => (
  <Box sx={{ width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center" }}>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="#0082fb"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15l-4-4 1.41-1.41L11 14.17l6.59-6.59L19 9l-8 8z"/></svg>
  </Box>
);

const WordPressIcon = () => (
  <Box sx={{ width: 22, height: 22, borderRadius: "50%", bgcolor: "#21759b", display: "flex", alignItems: "center", justifyContent: "center" }}>
    <Typography sx={{ color: "#fff", fontSize: 10, fontWeight: 700 }}>W</Typography>
  </Box>
);

// \u2500\u2500\u2500 Counter \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

function Counter({ value, onChange, min = 0, label = "Posts/week" }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Typography sx={{ fontSize: 13, color: "#aaa", mr: 0.5 }}>{label}</Typography>
      <Box
        onClick={() => onChange(Math.max(min, value - 1))}
        sx={{ width: 26, height: 26, borderRadius: "6px", border: "1px solid #ddd", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", "&:hover": { bgcolor: "#f5f5f5" } }}
      >
        <RemoveIcon sx={{ fontSize: 14, color: "#555" }} />
      </Box>
      <Typography sx={{ fontSize: 15, fontWeight: 500, minWidth: 20, textAlign: "center" }}>{value}</Typography>
      <Box
        onClick={() => onChange(value + 1)}
        sx={{ width: 26, height: 26, borderRadius: "6px", border: "1px solid #ddd", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", "&:hover": { bgcolor: "#f5f5f5" } }}
      >
        <AddIcon sx={{ fontSize: 14, color: "#555" }} />
      </Box>
    </Box>
  );
}

// \u2500\u2500\u2500 Section \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

function Section({ title, credit, children, counter, divider = true }) {
  return (
    <Box sx={{ mb: 3 }}>
      {divider && <Divider sx={{ mb: 3 }} />}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 1 }}>
          <Typography sx={{ fontSize: 17, fontWeight: 600, color: "#111" }}>{title}</Typography>
          <Typography sx={{ fontSize: 12, color: "#aaa" }}>{credit}</Typography>
        </Box>
        {counter}
      </Box>
      {children}
    </Box>
  );
}

// \u2500\u2500\u2500 Platform Checkbox Item \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

function PlatformItem({ icon, label, checked, onChange, dropdown }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Checkbox
        checked={checked}
        onChange={onChange}
        size="small"
        sx={{
          p: 0.5,
          color: "#ccc",
          "&.Mui-checked": { color: "#111" },
          "& .MuiSvgIcon-root": { fontSize: 18 },
        }}
      />
      {icon}
      {dropdown ? (
        <Select
          value={label}
          variant="standard"
          disableUnderline
          sx={{ fontSize: 13, color: "#333", fontWeight: 500, ".MuiSelect-select": { p: 0 } }}
        >
          <MenuItem value={label} sx={{ fontSize: 13 }}>{label}</MenuItem>
        </Select>
      ) : (
        <Typography sx={{ fontSize: 13, color: "#333", fontWeight: 500 }}>{label}</Typography>
      )}
    </Box>
  );
}

// \u2500\u2500\u2500 Main \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

export default function ContentPlanPage({ onBack, onContinue }) {
  const setContentPlan = useAppStore((state) => state.setContentPlan);
  const navigate = useNavigate();
  const [socialCount, setSocialCount] = useState(5);
  const [blogCount, setBlogCount] = useState(0);
  const [contentStyle, setContentStyle] = useState(() => {
    const stored = useAppStore.getState?.()?.recommendedVisualStyle;
    return stored?.id ? stored : null;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [platforms, setPlatforms] = useState({
    instagram: true,
    facebook: true,
    linkedin: true,
    x: true,
  });

  const selectedCount = useMemo(() => Object.values(platforms).filter(Boolean).length, [platforms]);
  const allSelected = selectedCount === Object.keys(platforms).length;

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      contentEngineApi.fetchContentPlan(),
      contentEngineApi.fetchContentPreferences(),
      contentEngineApi.fetchBrandStyle?.(),
    ]).then(([planResult, preferencesResult, brandStyleResult]) => {
      if (!active) return;
      const plan = planResult.status === "fulfilled" ? planResult.value.data?.content_plan : null;
      if (plan) {
        const selected = new Set(plan.platforms || []);
        setPlatforms({
          instagram: selected.has("instagram"),
          facebook: selected.has("facebook"),
          linkedin: selected.has("linkedin"),
          x: selected.has("x"),
        });
        setSocialCount(Math.max(1, Number(plan.posts_per_week || 5)));
        setBlogCount(Math.max(0, Number(plan.blog_posts_per_week ?? 0)));
        setContentPlan(plan);
      }
      const prefs = preferencesResult.status === "fulfilled" ? preferencesResult.value.data?.data : null;
      const brandStyle = brandStyleResult?.status === "fulfilled" ? brandStyleResult.value.data?.data : null;
      const style =
        (prefs?.content_style?.id ? prefs.content_style : null) ||
        (brandStyle?.visual_style?.id ? brandStyle.visual_style : null) ||
        useAppStore.getState?.()?.recommendedVisualStyle ||
        null;
      if (style?.id) setContentStyle(style);
    });
    return () => {
      active = false;
    };
  }, [setContentPlan]);

  const toggle = (key) => setPlatforms((prev) => ({ ...prev, [key]: !prev[key] }));
  const toggleAll = () => {
    const nextValue = !allSelected;
    setPlatforms({ instagram: nextValue, facebook: nextValue, linkedin: nextValue, x: nextValue });
  };

  const saveAndContinue = async () => {
    setSaving(true);
    setError("");
    const selectedPlatforms = Object.keys(platforms).filter((key) => platforms[key] && ["facebook", "instagram", "linkedin", "x"].includes(key));
    const payload = {
      platforms: selectedPlatforms.length ? selectedPlatforms : ["facebook", "instagram", "linkedin", "x"],
      posts_per_week: Math.max(1, Number(socialCount || 5)),
      blog_posts_per_week: Math.max(0, Number(blogCount || 0)),
      emails_per_week: 0,
    };
    try {
      setContentPlan(payload);
      await contentEngineApi.saveContentPlan(payload);
      navigate("/campaign-planner");
    } catch (err) {
      setError(err.response?.data?.error || "Content plan could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box className="voice-onboarding-page" sx={{ display: "flex", minHeight: "100vh", m: { xs: 0, md: 4 } }}>
      <Box sx={{ flex: 1, px: { xs: 3, md: 14 }, pt: 6, pb: "80px", maxWidth: 800, mx: "auto" }}>

        {/* Header */}
        <Typography sx={{ fontSize: 26, fontWeight: 600, color: "#111", mb: 0.5 }}>
          Set your Content Plan
        </Typography>
        <Typography sx={{ fontSize: 14, color: "#aaa", mb: 4, maxWidth: 580 }}>
          Select the platforms you want to generate content for, and how much content you'd like to generate per week.
        </Typography>
        {error && (
          <Box sx={{ mb: 3, border: "1px solid #ffd6d6", bgcolor: "#fff7f7", color: "#9b1c1c", borderRadius: 2, p: 2 }}>
            <Typography sx={{ fontSize: 14 }}>{error}</Typography>
          </Box>
        )}
        {contentStyle && (
          <Box sx={{ mb: 3, border: "1px solid #E5E7EB", borderRadius: 2, p: 2, bgcolor: "#FAFAFA" }}>
            <Typography sx={{ fontSize: 12, color: "#777", textTransform: "uppercase", letterSpacing: 0.5 }}>Content style</Typography>
            <Typography sx={{ fontSize: 15, fontWeight: 700 }}>{contentStyle.label || contentStyle.name || "Ultra Realistic"}</Typography>
            <Typography sx={{ fontSize: 13, color: "#777", mt: 0.5 }}>Managed in Content Preferences and applied to all generated images.</Typography>
          </Box>
        )}

        {/* Social Media */}
        <Section
          title="Social Media"
          credit="~3 credits/post"
          divider={false}
          counter={<Counter value={socialCount} onChange={setSocialCount} />}
        >
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
            <Typography sx={{ fontSize: 13, color: "#777" }}>{selectedCount} selected</Typography>
            <Button onClick={toggleAll} sx={{ textTransform: "none", color: "#111", fontWeight: 700, fontSize: 13, p: 0, minWidth: 0 }}>
              {allSelected ? "Clear all" : "Select all"}
            </Button>
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr", gap: "10px 32px" }}>
            <PlatformItem icon={<Instagram />} label="Instagram Posts" checked={platforms.instagram} onChange={() => toggle("instagram")} />
            <PlatformItem icon={<LinkedIn />} label="LinkedIn Posts" checked={platforms.linkedin} onChange={() => toggle("linkedin")} />
            <PlatformItem icon={<Facebook />} label="Facebook Posts" checked={platforms.facebook} onChange={() => toggle("facebook")} />
            <PlatformItem icon={<X />} label="X Posts" checked={platforms.x} onChange={() => toggle("x")} />
            {/* <PlatformItem icon={<GoogleIcon />} label="Business Profile Updates" checked={platforms.businessProfile} onChange={() => toggle("businessProfile")} /> */}
          </Box>
        </Section>

        <Section
          title="Blog"
          credit="~9 credits per post"
          counter={<Counter value={blogCount} onChange={setBlogCount} min={0} label="Blogs/week" />}
        >
          <Typography sx={{ fontSize: 13, color: "#777" }}>
            Blog posts are generated for your calendar as editable long-form content. Social channel selection does not apply to blog publishing.
          </Typography>
        </Section>

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
        {/* <Button onClick={onBack} sx={{ color: "#555", textTransform: "none", fontWeight: 400, fontSize: 14 }}>Back</Button> */}
        <Button
          variant="contained"
          onClick={saveAndContinue}
          disabled={saving}
          sx={{ml:'auto', bgcolor: "#111", color: "#fff", textTransform: "none", borderRadius: "8px", fontWeight: 500, fontSize: 14, px: 3, "&:hover": { bgcolor: "#333" } }}
        >
          {saving ? "Saving..." : "Next, review topics"}
        </Button>
      </Box>
      <AmbientWorking active={saving} title="Saving content plan" detail="Voice Spark is keeping the rest of the setup available." />
    </Box>
  );
}
