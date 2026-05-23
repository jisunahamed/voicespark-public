import { Box } from "@mui/material";

export default function LandingPage() {
  return (
    <Box
      component="iframe"
      title="Voice Spark AI"
      src="/landing/index.html"
      sx={{
        width: "100%",
        height: "100vh",
        display: "block",
        border: 0,
        bgcolor: "#0A0A12",
      }}
    />
  );
}
