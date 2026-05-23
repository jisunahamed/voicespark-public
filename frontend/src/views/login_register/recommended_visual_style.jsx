import React, { useEffect, useState } from "react";
import { Box, Typography, Button, Checkbox } from "@mui/material";
import { useNavigate } from "react-router-dom";
import useAppStore from "./constants";
import { contentEngineApi } from "./content_engine_api";
import { AmbientWorking } from "../../components/VoiceSparkUI";
import { VISUAL_STYLE_OPTIONS as STYLES } from "./visual_style_options";

const normalizeStyleId = (value = "") => String(value || "")
  .trim()
  .toLowerCase()
  .replace(/cartoon[-_\s/]+animated/g, "cartoon_animated")
  .replace(/product[-_\s]+studio/g, "product_studio")
  .replace(/editorial[-_\s]+lifestyle/g, "editorial_lifestyle")
  .replace(/ultra[-_\s]+realistic/g, "ultra_realistic")
  .replace(/-/g, "_")
  .replace(/\s+/g, "_");

function StyleCard({ style, selected, onSelect }) {
  return (
    <Box
      onClick={onSelect}
      sx={{
        position: "relative",
        flex: "1 1 220px",
        minWidth: 0,
        minHeight: 390,
        borderRadius: "12px",
        overflow: "hidden",
        cursor: "pointer",
        border: selected ? "2px solid #111" : "1px solid rgba(17,24,39,0.12)",
        boxShadow: selected ? "0 18px 42px rgba(17,24,39,0.18)" : "0 12px 28px rgba(17,24,39,0.08)",
        transition: "border 0.2s, transform 0.2s, box-shadow 0.2s",
        "&:hover": {
          transform: "translateY(-3px)",
          border: selected ? "2px solid #111" : "1px solid rgba(17,24,39,0.35)",
        },
      }}
    >
      {/* Image */}
      <Box
        component="img"
        src={style.image || style.image_url}
        alt={style.name}
        sx={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: style.imagePosition || "center", display: "block", minHeight: 390 }}
      />

      {/* Gradient overlay at bottom */}
      <Box
        sx={{
          position: "absolute",
          bottom: 0, left: 0, right: 0,
          height: "68%",
          background: "linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.55) 42%, rgba(0,0,0,0) 100%)",
        }}
      />

      {/* Checkbox top left */}
      <Box
        sx={{
          position: "absolute", top: 12, left: 12,
          width: 28, height: 28,
          borderRadius: "6px",
          bgcolor: selected ? "#111" : "rgba(255,255,255,0.25)",
          border: selected ? "none" : "1.5px solid rgba(255,255,255,0.6)",
          display: "flex", alignItems: "center", justifyContent: "center",
          transition: "all 0.2s",
        }}
      >
        {selected && (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M5 13l4 4L19 7" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </Box>

      {/* Recommended badge top right */}
      {style.recommended && (
        <Box
          sx={{
            position: "absolute", top: 12, right: 12,
            bgcolor: "#fff", backdropFilter: "blur(4px)",
            borderRadius: "999px", px: 1.5, py: 0.5,
          }}
        >
          <Typography sx={{ fontSize: 11, color: "#111", fontWeight: 800 }}>Recommended</Typography>
        </Box>
      )}

      {/* Bottom content */}
      <Box sx={{ position: "absolute", bottom: 0, left: 0, right: 0, p: 2 }}>
        <Typography sx={{ fontSize: 23, fontWeight: 900, color: "#fff", mb: 1, letterSpacing: 0, textShadow: "0 3px 14px rgba(0,0,0,0.45)" }}>
          {style.name}
        </Typography>
        <Typography sx={{ fontSize: 12, color: "rgba(255,255,255,0.86)", lineHeight: 1.35, mb: 1.5 }}>
          {style.description}
        </Typography>

        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 12px" }}>
          {[
            { label: "Subject", value: style.subject },
            { label: "Output", value: style.output },
            { label: "Tone", value: style.tone },
          ].map((meta) => (
            <Box key={meta.label}>
              <Typography sx={{ fontSize: 9, color: "rgba(255,255,255,0.55)", lineHeight: 1.2, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                {meta.label}
              </Typography>
              <Typography sx={{ fontSize: 12, color: "#fff", fontWeight: 700, lineHeight: 1.4 }}>
                {meta.value}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
}

export default function VisualStyleSelectorPage({ onBack, onApply, onBrowse }) {
  const { visualStyle, recommendedVisualStyle, setRecommendedVisualStyle } = useAppStore();
  const navigate = useNavigate();
  const [styles, setStyles] = useState(STYLES);
  const [loadingStyles, setLoadingStyles] = useState(true);
  const [savingStyle, setSavingStyle] = useState(false);
  const selected = normalizeStyleId(recommendedVisualStyle?.id || styles[0]?.id);

  useEffect(() => {
    setLoadingStyles(true);
    Promise.allSettled([
      contentEngineApi.recommendedStyles(visualStyle),
      contentEngineApi.fetchBrandStyle(),
    ]).then(([stylesResult, brandResult]) => {
      const data = stylesResult.status === "fulfilled" ? stylesResult.value.data : {};
      if (data.styles?.length) setStyles(data.styles.map((item, index) => {
        const fallback = STYLES[index % STYLES.length];
        return ({
        id: normalizeStyleId(item.id),
        name: item.name,
        image: fallback.image,
        image_url: fallback.image,
        recommended: index === 0,
        description: item.description || fallback.description,
        prompt: item.prompt || fallback.prompt,
        subject: item.name.includes("Realistic") ? "Real Human" : item.name.includes("Infographic") ? "Data" : item.name.includes("Cartoon") ? "Characters" : "Brand",
        output: item.name.includes("Infographic") ? "Graphic" : item.name.includes("Cartoon") ? "Illustration" : "Photo",
        tone: "Brand aligned",
      });
      }));
      const brandStyle = brandResult.status === "fulfilled" ? brandResult.value.data?.brand_style : null;
      const savedStyle = brandStyle?.visual_style;
      if (savedStyle?.id) {
        setRecommendedVisualStyle({
          ...savedStyle,
          id: normalizeStyleId(savedStyle.id),
          name: savedStyle.name || savedStyle.label || savedStyle.id,
        });
      }
    }).catch(() => {}).finally(() => setLoadingStyles(false));
  }, [visualStyle]);

  const saveAndContinue = async () => {
    setSavingStyle(true);
    try {
      const style = styles.find((item) => normalizeStyleId(item.id) === selected) || styles[0];
      const normalizedStyle = { ...style, id: normalizeStyleId(style.id) };
      setRecommendedVisualStyle(normalizedStyle);
      await contentEngineApi.saveBrand({ recommended_visual_style: normalizedStyle });
      await contentEngineApi.updateBrandStyle({
        visual_style: {
          id: normalizedStyle.id,
          label: normalizedStyle.name,
          name: normalizedStyle.name,
          image_url: normalizedStyle.image || normalizedStyle.image_url || "",
          description: normalizedStyle.description || "",
          prompt: normalizedStyle.prompt || "",
        },
      });
      navigate('/brand-font', { replace: true });
    } finally {
      setSavingStyle(false);
    }
  };
  return (
    <Box className="voice-onboarding-page" sx={{ display: "flex", flexDirection: "column", minHeight: "100vh", px: { xs: 2, md: 4 }, pt: 4, pb: "80px" }}>

      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography sx={{ fontSize: { xs: 24, md: 30 }, fontWeight: 900, color: "#111", mb: 0.5, letterSpacing: 0 }}>
          Here's your recommended visual styles
        </Typography>
        <Typography sx={{ fontSize: 14, color: "#aaa" }}>
          Applied to all your content automatically. Change it anytime.
        </Typography>
      </Box>

      {/* Cards */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))", lg: "repeat(5, minmax(0, 1fr))" },
          gap: 2,
          flex: 1,
          alignItems: "stretch",
        }}
      >
        {styles.map((style) => (
          <StyleCard
            key={style.id}
            style={style}
            selected={selected === normalizeStyleId(style.id)}
            onSelect={() => setRecommendedVisualStyle({ ...style, id: normalizeStyleId(style.id) })}
          />
        ))}
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
        {/* <Button
          onClick={onBack}
          sx={{ color: "#555", textTransform: "none", fontWeight: 400, fontSize: 14 }}
        >
          Back
        </Button> */}

        {/* <Button
          onClick={onBrowse}
          sx={{ color: "#555", textTransform: "none", fontWeight: 400, fontSize: 14 }}
        >
          Browse all styles
        </Button> */}

        <Button
          variant="contained"
          onClick={saveAndContinue}
          disabled={savingStyle}
          sx={{
            ml: "auto",
            bgcolor: "#111", color: "#fff",
            textTransform: "none", borderRadius: "8px",
            fontWeight: 500, fontSize: 14, px: 3,
            "&:hover": { bgcolor: "#333" },
          }}
        >
          Apply this style
        </Button>
      </Box>
      <AmbientWorking
        active={loadingStyles || savingStyle}
        title={loadingStyles ? "Finding visual styles" : "Saving visual style"}
        detail="Recommendations are generated from your brand profile."
      />
    </Box>
  );
}
