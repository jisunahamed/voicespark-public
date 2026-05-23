import React from "react";
import { Box, CircularProgress, Stack, Typography } from "@mui/material";
import BoltIcon from "@mui/icons-material/Bolt";

export function BrandMark({ size = 44 }) {
  return (
    <Box
      sx={{
        width: size,
        height: size,
        borderRadius: "50%",
        bgcolor: "#1f2328",
        color: "#a855f7",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 18px 40px rgba(31,35,40,0.18)",
      }}
    >
      <BoltIcon sx={{ fontSize: size * 0.52 }} />
    </Box>
  );
}

export function AmbientWorking({ active, title = "Working on it", detail = "You can keep using the page." }) {
  if (!active) return null;
  return (
    <Box
      sx={{
        position: "fixed",
        right: { xs: 16, md: 28 },
        bottom: { xs: 16, md: 24 },
        zIndex: 2200,
        width: { xs: "calc(100% - 32px)", sm: 340 },
        border: "1px solid rgba(168,85,247,0.28)",
        bgcolor: "rgba(255,255,255,0.88)",
        backdropFilter: "blur(18px)",
        borderRadius: 5,
        p: 1.5,
        boxShadow: "0 24px 70px rgba(31,35,40,0.18)",
      }}
    >
      <Stack direction="row" spacing={1.5} alignItems="center">
        <Box sx={{ position: "relative", width: 42, height: 42, display: "grid", placeItems: "center" }}>
          <CircularProgress size={42} thickness={3.5} sx={{ color: "#a855f7", position: "absolute" }} />
          <BrandMark size={26} />
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ fontSize: 14, fontWeight: 900, color: "#1f2328" }}>{title}</Typography>
          <Typography sx={{ fontSize: 12.5, color: "#667085", lineHeight: 1.35 }}>{detail}</Typography>
        </Box>
      </Stack>
    </Box>
  );
}

export function AuthVisualPanel() {
  return (
    <Box className="voice-auth-visual">
      <Box className="voice-orbit" />
      <Box className="voice-preview-card voice-preview-card-a">
        <Typography sx={{ fontSize: 12, fontWeight: 900, color: "#667085" }}>Campaigns ready</Typography>
        <Typography sx={{ fontSize: 38, fontWeight: 900, color: "#1f2328", lineHeight: 1 }}>24</Typography>
      </Box>
      <Box className="voice-preview-card voice-preview-card-b">
        <Typography sx={{ fontSize: 13, fontWeight: 900, color: "#1f2328" }}>Voice Spark</Typography>
        <Box className="voice-meter"><span /></Box>
        <Typography sx={{ fontSize: 12, color: "#667085" }}>Brand-aligned content engine</Typography>
      </Box>
    </Box>
  );
}
