import React, { useEffect, useRef, useState } from "react";
import { Box, Button, CircularProgress, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";

import { contentEngineApi } from "./content_engine_api";

export default function GenerateFirstWeekPage() {
  const navigate = useNavigate();
  const started = useRef(false);
  const [status, setStatus] = useState("Generating your first week...");
  const [posts, setPosts] = useState([]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    contentEngineApi.generateFirstWeek()
      .then(({ data }) => {
        setPosts(data.posts || []);
        setStatus("First week generated successfully.");
      })
      .catch((error) => setStatus(error.response?.data?.error || "Generation failed. Please try again."));
  }, []);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#fff", px: { xs: 3, md: 10 }, py: 6 }}>
      <Typography sx={{ fontSize: 28, fontWeight: 700, mb: 1 }}>Generate first week</Typography>
      <Typography sx={{ color: "#777", mb: 4 }}>{status}</Typography>
      {!posts.length && status.includes("Generating") && <CircularProgress />}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, gap: 2 }}>
        {posts.map((post) => (
          <Box key={post.id} sx={{ border: "1px solid #e5e7eb", borderRadius: 2, overflow: "hidden", bgcolor: "#fff" }}>
            {post.image_url && <Box component="img" src={post.image_url} sx={{ width: "100%", aspectRatio: "1 / 1", objectFit: "cover", display: "block" }} />}
            <Box sx={{ p: 2 }}>
              <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 1 }}>{post.topic}</Typography>
              <Typography sx={{ color: "#777", fontSize: 12 }}>{post.status}</Typography>
            </Box>
          </Box>
        ))}
      </Box>
      {posts.length > 0 && (
        <Button variant="contained" onClick={() => navigate('/home')} sx={{ mt: 4, bgcolor: "#111", textTransform: "none", borderRadius: 2 }}>
          Go to dashboard
        </Button>
      )}
    </Box>
  );
}
