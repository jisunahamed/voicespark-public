import React, { useEffect, useState } from "react";
import { Box, Button, CircularProgress, TextField, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";

import useAppStore from "./constants";
import { contentEngineApi } from "./content_engine_api";

export default function BlogEmailPlanPage() {
  const navigate = useNavigate();
  const { blogEmailPlan, setBlogEmailPlan } = useAppStore();
  const [plan, setPlan] = useState(blogEmailPlan);
  const [loading, setLoading] = useState(!blogEmailPlan);

  useEffect(() => {
    if (blogEmailPlan) return;
    contentEngineApi.blogEmailPlan().then(({ data }) => {
      setPlan(data);
      setBlogEmailPlan(data);
    }).finally(() => setLoading(false));
  }, []);

  const updateBlogTitle = (title) => setPlan((prev) => ({ ...prev, blog_plan: { ...(prev?.blog_plan || {}), title } }));
  const updateEmailSubject = (subject) => setPlan((prev) => ({ ...prev, email_plan: { ...(prev?.email_plan || {}), subject } }));
  const continueFlow = async () => {
    setBlogEmailPlan(plan);
    await contentEngineApi.blogEmailPlan({ plan });
    navigate('/generate-first-week');
  };

  if (loading) {
    return <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}><CircularProgress /></Box>;
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#fff", px: { xs: 3, md: 12 }, py: 6, pb: 12 }}>
      <Typography sx={{ fontSize: 28, fontWeight: 700, mb: 1 }}>Review blog and email plan</Typography>
      <Typography sx={{ color: "#777", mb: 4 }}>Edit the plan before the first week is generated.</Typography>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
        <Box sx={{ border: "1px solid #e5e7eb", borderRadius: 2, p: 3 }}>
          <Typography sx={{ fontWeight: 700, mb: 2 }}>Blog Plan</Typography>
          <TextField fullWidth label="Title" value={plan?.blog_plan?.title || ""} onChange={(e) => updateBlogTitle(e.target.value)} sx={{ mb: 2 }} />
          {(plan?.blog_plan?.outline || []).map((item, index) => (
            <Typography key={index} sx={{ fontSize: 14, mb: 1 }}>- {item}</Typography>
          ))}
          <Typography sx={{ mt: 2, fontSize: 13, color: "#666" }}>Images: cover and inline placement included.</Typography>
        </Box>

        <Box sx={{ border: "1px solid #e5e7eb", borderRadius: 2, p: 3 }}>
          <Typography sx={{ fontWeight: 700, mb: 2 }}>Email Plan</Typography>
          <TextField fullWidth label="Subject" value={plan?.email_plan?.subject || ""} onChange={(e) => updateEmailSubject(e.target.value)} sx={{ mb: 2 }} />
          {(plan?.email_plan?.structure || []).map((item, index) => (
            <Typography key={index} sx={{ fontSize: 14, mb: 1 }}>- {item}</Typography>
          ))}
          <Typography sx={{ mt: 2, fontSize: 13, color: "#666" }}>CTA: {plan?.email_plan?.cta}</Typography>
        </Box>
      </Box>

      <Box sx={{ position: "fixed", bottom: 0, left: 0, right: 0, px: 4, py: 2, borderTop: "1px solid #e5e7eb", bgcolor: "#fff", display: "flex", justifyContent: "flex-end" }}>
        <Button variant="contained" onClick={continueFlow} sx={{ bgcolor: "#111", textTransform: "none", borderRadius: 2 }}>Generate first week</Button>
      </Box>
    </Box>
  );
}
