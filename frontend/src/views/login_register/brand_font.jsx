import React, { useEffect, useState } from "react";
import { Box, Typography, Button, Dialog, DialogTitle, DialogContent, TextField, InputAdornment } from "@mui/material";
import { useNavigate } from "react-router-dom";
import useAppStore from "./constants";
import { contentEngineApi } from "./content_engine_api";
import { AmbientWorking } from "../../components/VoiceSparkUI";
const STYLES = [
  {
    id: "gauzy-portrait",
    name: "Gauzy Portrait",
    recommended: true,
    image: "https://images.unsplash.com/photo-1552058544-f2b08422138a?w=600&q=80",
    lighting: "Soft Wrapped",
    color: "Warm Natural",
    contrast: "Low",
    grain: "Subtle",
    focus: "Very Shallow",
  },
  {
    id: "golden-hour",
    name: "Golden Hour",
    recommended: false,
    image: "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=600&q=80",
    lighting: "Warm Wrapped",
    color: "Warm Teal",
    contrast: "Medium",
    grain: "Fine",
    focus: "Moderate",
  },
  {
    id: "dramatic-luxe",
    name: "Dramatic Luxe",
    recommended: false,
    image: "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=600&q=80",
    lighting: "Hard Directional",
    color: "Punchy Neutral",
    contrast: "High",
    grain: "Natural",
    focus: "Shallow",
  },
];

// Load Google Fonts
const fontLink = document.createElement("link");
fontLink.rel = "stylesheet";
fontLink.href = "https://fonts.googleapis.com/css2?family=Archivo:wght@400;700;800&family=Bebas+Neue&family=DM+Sans:wght@400;700&family=Hind+Siliguri:wght@400;600;700&family=Inter:wght@400;700;800&family=Lato:wght@400;700&family=Lexend:wght@400;700&family=Manrope:wght@400;700;800&family=Merriweather:wght@400;700&family=Montserrat:wght@400;700;800&family=Noto+Sans+Bengali:wght@400;700;800&family=Noto+Serif+Bengali:wght@400;700&family=Nunito:wght@400;700;800&family=Open+Sans:wght@400;700&family=Oswald:wght@400;700&family=Playfair+Display:wght@700&family=Poppins:wght@400;700;800&family=Raleway:wght@400;700;800&family=Roboto:wght@400;700&family=Rubik:wght@400;700;800&family=Source+Sans+3:wght@400;700;800&display=swap";
document.head.appendChild(fontLink);

const ALL_FONTS = [
  {
    id: "lexend",
    displayName: "Lexend",
    subLabel: "Lexend",
    fontFamily: "'Lexend', sans-serif",
    fontWeight: 400,
  },
  {
    id: "dm-sans",
    displayName: "DM Sans",
    subLabel: "Neue Haas Unica W1G",
    fontFamily: "'DM Sans', sans-serif",
    fontWeight: 400,
  },
  {
    id: "playfair-display",
    displayName: "Playfair",
    subLabel: "Playfair Display",
    fontFamily: "'Playfair Display', serif",
    fontWeight: 700,
  },
  { id: "inter", displayName: "Inter", subLabel: "Modern SaaS", fontFamily: "'Inter', sans-serif", fontWeight: 800 },
  { id: "poppins", displayName: "Poppins", subLabel: "Geometric Sans", fontFamily: "'Poppins', sans-serif", fontWeight: 800 },
  { id: "montserrat", displayName: "Montserrat", subLabel: "Editorial Sans", fontFamily: "'Montserrat', sans-serif", fontWeight: 800 },
  { id: "archivo", displayName: "Archivo", subLabel: "Bold Utility", fontFamily: "'Archivo', sans-serif", fontWeight: 800 },
  { id: "manrope", displayName: "Manrope", subLabel: "Clean Digital", fontFamily: "'Manrope', sans-serif", fontWeight: 800 },
  { id: "rubik", displayName: "Rubik", subLabel: "Friendly Product", fontFamily: "'Rubik', sans-serif", fontWeight: 800 },
  { id: "lato", displayName: "Lato", subLabel: "Humanist Sans", fontFamily: "'Lato', sans-serif", fontWeight: 700 },
  { id: "roboto", displayName: "Roboto", subLabel: "System UI", fontFamily: "'Roboto', sans-serif", fontWeight: 700 },
  { id: "open-sans", displayName: "Open Sans", subLabel: "Readable Sans", fontFamily: "'Open Sans', sans-serif", fontWeight: 700 },
  { id: "nunito", displayName: "Nunito", subLabel: "Rounded Friendly", fontFamily: "'Nunito', sans-serif", fontWeight: 800 },
  { id: "source-sans-3", displayName: "Source Sans", subLabel: "Content Sans", fontFamily: "'Source Sans 3', sans-serif", fontWeight: 800 },
  { id: "raleway", displayName: "Raleway", subLabel: "Premium Display", fontFamily: "'Raleway', sans-serif", fontWeight: 800 },
  { id: "oswald", displayName: "Oswald", subLabel: "Condensed Impact", fontFamily: "'Oswald', sans-serif", fontWeight: 700 },
  { id: "bebas-neue", displayName: "Bebas", subLabel: "Poster Display", fontFamily: "'Bebas Neue', sans-serif", fontWeight: 400 },
  { id: "merriweather", displayName: "Merri", subLabel: "Trust Serif", fontFamily: "'Merriweather', serif", fontWeight: 700 },
  { id: "noto-sans-bengali", displayName: "Noto Bangla", subLabel: "Bengali Sans", fontFamily: "'Noto Sans Bengali', sans-serif", fontWeight: 800 },
  { id: "hind-siliguri", displayName: "Hind Siliguri", subLabel: "Bangla Modern", fontFamily: "'Hind Siliguri', sans-serif", fontWeight: 700 },
  { id: "noto-serif-bengali", displayName: "Noto Serif", subLabel: "Bengali Serif", fontFamily: "'Noto Serif Bengali', serif", fontWeight: 700 },
];
const FONTS = ALL_FONTS.slice(0, 3);

function fontIdFromName(value = "") {
  const normalized = String(value || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return ALL_FONTS.find((font) => font.id === normalized || font.displayName.toLowerCase() === String(value || "").trim().toLowerCase())?.id;
}

function selectedFontList(selectedId) {
  const selectedFont = ALL_FONTS.find((font) => font.id === selectedId) || ALL_FONTS[0];
  const recommended = FONTS.filter((font) => font.id !== selectedFont.id);
  return [selectedFont, ...recommended].slice(0, 3);
}

function FontCard({ font, selected, onSelect }) {
  return (
    <Box
      onClick={onSelect}
      sx={{
        position: "relative",
        border: "1px solid #e8e8e8",
        borderRadius: "12px",
        px: 4,
        py: 3,
        cursor: "pointer",
        bgcolor: "#fff",
        transition: "border-color 0.15s",
        "&:hover": { borderColor: "#bbb" },
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 120,
      }}
    >
      {/* Checkbox */}
      <Box
        sx={{
          position: "absolute",
          top: 14,
          left: 14,
          width: 26,
          height: 26,
          borderRadius: "50%",
          bgcolor: selected ? "#111" : "transparent",
          border: selected ? "none" : "1.5px solid #ccc",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "all 0.2s",
        }}
      >
        {selected && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M5 13l4 4L19 7" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </Box>

      {/* Font display name */}
      <Typography
        sx={{
          fontFamily: font.fontFamily,
          fontWeight: font.fontWeight,
          fontSize: 48,
          color: "#111",
          lineHeight: 1.1,
          mb: 0.5,
        }}
      >
        {font.displayName}
      </Typography>

      {/* Sub label */}
      <Typography
        sx={{
          fontFamily: font.fontFamily,
          fontSize: 14,
          color: "#888",
          fontWeight: 400,
        }}
      >
        {font.subLabel}
      </Typography>
    </Box>
  );
}

function InstagramPreview({ fontFamily }) {
  const { visualStyle, setVisualStyle } = useAppStore();
  return (
    <Box
      sx={{
        width: 300,
        borderRadius: "16px",
        overflow: "hidden",
        bgcolor: "#1a1a1a",
        boxShadow: "0 24px 60px rgba(0,0,0,0.5)",
      }}
    >
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.5, bgcolor: "#1a1a1a" }}>
        <Box sx={{ width: 32, height: 32, borderRadius: "50%", bgcolor: "#555", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Typography sx={{ color: "#fff", fontSize: 12, fontWeight: 600 }}>S</Typography>
        </Box>
        <Box>
          <Typography sx={{ fontSize: 13, fontWeight: 600, color: "#fff", lineHeight: 1.2 }}>Samiul Ehsan</Typography>
          <Typography sx={{ fontSize: 10, color: "#888" }}>Just now</Typography>
        </Box>
      </Box>

      {/* Image with overlay text */}
      <Box sx={{ position: "relative" }}>
        <Box
          component="img"
          // src="https://images.unsplash.com/photo-1552058544-f2b08422138a?w=600&q=80"
          src={STYLES.find(s => s.id === visualStyle)?.image}
          alt="Post"
          sx={{ width: "100%", height: 300, objectFit: "cover", display: "block" }}
        />
        {/* Text overlay */}
        <Box
          sx={{
            position: "absolute",
            bottom: 24,
            left: 16,
            bgcolor: "#111",
            borderRadius: "8px",
            px: 1.5,
            py: 1,
            maxWidth: "75%",
          }}
        >
          <Typography
            sx={{
              fontFamily: fontFamily,
              fontSize: 16,
              fontWeight: 700,
              color: "#fff",
              lineHeight: 1.3,
            }}
          >
            How to Master A Stand Out Brand
          </Typography>
        </Box>
      </Box>

      {/* Actions */}
      <Box sx={{ bgcolor: "#1a1a1a", px: 2, py: 1.5 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
          <Box sx={{ display: "flex", gap: 1.5 }}>
            {/* Heart */}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
            {/* Comment */}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            {/* Share */}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </Box>
          {/* Bookmark */}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.5"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
        </Box>
        <Typography sx={{ fontSize: 12, fontWeight: 600, color: "#fff", mb: 0.5 }}>Samiul Ehsan</Typography>
        <Box sx={{ height: 6, bgcolor: "#333", borderRadius: 1, width: "60%" }} />
      </Box>
    </Box>
  );
}

export default function BrandFontPage({ onBack, onContinue }) {
  const [selected, setSelected] = useState("lexend");
  const [browseOpen, setBrowseOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  const setBrandFont = useAppStore((state) => state.setBrandFont);

  useEffect(() => {
    let mounted = true;
    contentEngineApi.fetchBrandStyle()
      .then(({ data }) => {
        const fonts = data?.brand_style?.fonts || [];
        const titleFont = fonts.find((font) => font.role === "title") || fonts[0];
        const savedId = fontIdFromName(titleFont?.family);
        if (mounted && savedId) setSelected(savedId);
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  const selectedFont = ALL_FONTS.find((f) => f.id === selected) || ALL_FONTS[0];
  const visibleFonts = selectedFontList(selected);
  const saveAndContinue = async () => {
    setSaving(true);
    try {
      const font = {
        ...selectedFont,
        family: selectedFont.displayName,
        weight: String(selectedFont.fontWeight || 700),
      };
      setBrandFont(font);
      await contentEngineApi.saveBrand({ font });
      await contentEngineApi.updateBrandStyle({
        fonts: [
          { role: "title", family: font.displayName, weight: font.weight },
          { role: "body", family: font.displayName, weight: "Regular" },
        ],
      });
      navigate('/content-plan-register');
    } finally {
      setSaving(false);
    }
  };
  const filteredFonts = ALL_FONTS.filter((font) => `${font.displayName} ${font.subLabel}`.toLowerCase().includes(search.toLowerCase()));

  return (
    <Box className="voice-onboarding-page" sx={{ display: "flex", minHeight: "100vh", overflow: "hidden" }}>

      {/* LEFT */}
      <Box
        sx={{
          width: { xs: "100%", md: "52%" },
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          px: { xs: 4, md: 8 },
          pt: 6,
          pb: "80px",
        }}
      >
        {/* Heading */}
        <Typography sx={{ fontSize: 26, fontWeight: 600, color: "#111", mb: 0.5, textAlign: "center" }}>
          Select a brand font
        </Typography>
        <Typography sx={{ fontSize: 14, color: "#aaa", mb: 4, textAlign: "center" }}>
          Based on your brand, we recommend:
        </Typography>

        {/* Font cards */}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, width: "100%", maxWidth: 640 }}>
          {visibleFonts.map((font) => (
            <FontCard
              key={font.id}
              font={font}
              selected={selected === font.id}
              onSelect={() => setSelected(font.id)}
            />
          ))}
        </Box>

        {/* Browse all fonts */}
        <Button
          variant="outlined"
          onClick={() => setBrowseOpen(true)}
          sx={{
            mt: 3,
            textTransform: "none",
            fontSize: 13,
            color: "#555",
            borderColor: "#ddd",
            borderRadius: "20px",
            px: 2.5,
            "&:hover": { borderColor: "#aaa", bgcolor: "transparent" },
          }}
        >
          Browse all
        </Button>
      </Box>

      {/* RIGHT — dark bg with preview */}
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          width: "48%",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #2a2a2a 0%, #111 100%)",
          position: "relative",
        }}
      >
        {/* Subtle radial glow */}
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            background: "radial-gradient(ellipse at 50% 50%, rgba(80,80,80,0.3) 0%, transparent 70%)",
          }}
        />
        <Box sx={{ position: "relative" }}>
          <InstagramPreview fontFamily={selectedFont?.fontFamily || "'Lexend', sans-serif"} />
        </Box>
      </Box>

      {/* FOOTER — only left side */}
      <Box
        sx={{
          position: "fixed", bottom: 0, left: 0,
          width: { xs: "100%", md: "52%" },
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
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
          onClick={saveAndContinue}
          sx={{
            ml:'auto',
            bgcolor: "#111", color: "#fff",
            textTransform: "none", borderRadius: "8px",
            fontWeight: 500, fontSize: 14, px: 3,
            "&:hover": { bgcolor: "#333" },
          }}
        >
          Looks good
        </Button>
      </Box>
      <Dialog open={browseOpen} onClose={() => setBrowseOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Browse all fonts</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            size="small"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search fonts"
            sx={{ mb: 2 }}
            InputProps={{ startAdornment: <InputAdornment position="start">Font</InputAdornment> }}
          />
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.5, maxHeight: 520, overflow: "auto", pr: 1 }}>
            {filteredFonts.map((font) => (
              <FontCard
                key={font.id}
                font={font}
                selected={selected === font.id}
                onSelect={() => {
                  setSelected(font.id);
                  setBrowseOpen(false);
                }}
              />
            ))}
          </Box>
        </DialogContent>
      </Dialog>
      <AmbientWorking active={saving} title="Saving brand font" detail="Voice Spark will use this font direction in future generated visuals." />
    </Box>
  );
}
