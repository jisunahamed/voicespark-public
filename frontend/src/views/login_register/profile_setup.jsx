import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  Typography,
  Button,
  Divider,
  CircularProgress,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Stack,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import useAppStore from './constants';
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { marked } from "marked";
import TurndownService from "turndown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNavigate } from 'react-router-dom';
import { Link, useLocation } from "react-router-dom";
import config from "../../config";
import axios from "axios";
import { workspaceStorage } from "../workspace/workSpaceAPi";
import { contentEngineApi } from "./content_engine_api";
import { AmbientWorking } from "../../components/VoiceSparkUI";

const turndown = new TurndownService();
const businessProfileRequests = new Map();

const PROFILE_SECTIONS = [
  "Business Name",
  "Business Overview & Positioning",
  "Market Positioning",
  "Direct Competitors",
  "Competitive Advantages",
  "Primary Customer Segments",
  "Top Revenue Generators (based on website prominence)",
  "Emerging Growth Areas",
  "Primary Value Drivers",
  "Emotional Benefits",
  "Brand Story",
  "Brand Personality",
];

const normalizeProfileTitle = (value) => String(value || "").replace(/^#+\s*/, "").trim();

const PROFILE_SECTION_ALIASES = new Map([
  ["business overview and positioning", "Business Overview & Positioning"],
  ["business overview & positioning", "Business Overview & Positioning"],
  ["market positioning", "Market Positioning"],
  ["direct competitors", "Direct Competitors"],
  ["competitive advantages", "Competitive Advantages"],
  ["primary customer segments", "Primary Customer Segments"],
  ["customer demographics and psychographics", "Primary Customer Segments"],
  ["core offer areas", "Top Revenue Generators (based on website prominence)"],
  ["top revenue generators", "Top Revenue Generators (based on website prominence)"],
  ["top revenue generators (based on website prominence)", "Top Revenue Generators (based on website prominence)"],
  ["emerging growth areas", "Emerging Growth Areas"],
  ["primary value drivers", "Primary Value Drivers"],
  ["emotional benefits", "Emotional Benefits"],
  ["brand story", "Brand Story"],
  ["brand personality", "Brand Personality"],
]);

function profileSectionForHeading(rawTitle) {
  const title = normalizeProfileTitle(rawTitle);
  const lower = title.toLowerCase();
  if (PROFILE_SECTIONS.includes(title)) return title;
  if (PROFILE_SECTION_ALIASES.has(lower)) return PROFILE_SECTION_ALIASES.get(lower);
  if (/^the\s+.+\s+brand story$/i.test(title)) return "Brand Story";
  if (/\bbusiness profile$/i.test(title)) return "Business Name";
  return undefined;
}

function parseProfileSections(markdown) {
  const sections = PROFILE_SECTIONS.map((title) => ({ title, body: "" }));
  const byTitle = new Map(sections.map((section) => [section.title.toLowerCase(), section]));
  let current = null;
  for (const line of String(markdown || "").split(/\r?\n/)) {
    const heading = /^(#{1,4})\s+(.+?)\s*$/.exec(line);
    if (heading) {
      const mapped = profileSectionForHeading(heading[2]);
      current = mapped ? byTitle.get(mapped.toLowerCase()) || null : null;
      continue;
    }
    if (current) current.body = `${current.body}${current.body ? "\n" : ""}${line}`;
  }
  if (!sections[0].body.trim()) {
    const title = /^#\s+(.+?)(?:'s Business Profile| Business Profile)?\s*$/m.exec(String(markdown || ""));
    if (title?.[1]) sections[0].body = title[1].trim();
  }
  if (!sections.some((section) => section.body.trim()) && markdown) {
    sections[1].body = String(markdown).replace(/^#\s+.+$/m, "").trim();
  }
  return sections.map((section) => ({ ...section, body: section.body.trim() }));
}

function serializeProfileSections(sections) {
  return sections
    .map((section) => `## ${section.title}\n\n${String(section.body || "").trim()}`)
    .join("\n\n")
    .trim();
}

const CheckCircleIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="11" fill="#2e7d32" />
    <path
      d="M7 12.5l3.5 3.5 6.5-7"
      stroke="white"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const GrayCircleIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="11" fill="#e0e0e0" />
  </svg>
);

// \u2500\u2500\u2500 Sidebar (shared between both views) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

const sideChecks = [
  "Core identity is accurate",
  "Market positioning makes sense",
  "Competitive advantages are complete",
];

function Sidebar() {
  return (
    <Box
      sx={{
        width: 280,
        borderLeft: "1px solid #e0e0e0",
        p: 3,
        position: "sticky",
        top: 0,
        height: "fit-content",
        bgcolor: "#fff",
        flexShrink: 0,
      }}
    >
      <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 0.5 }}>
        Does this look right?
      </Typography>
      <Typography sx={{ fontSize: 13, color: "#757575", mb: 2 }}>
        We built this from your website. Fix anything that's off.
      </Typography>
      <Divider sx={{ mb: 2 }} />
      <Typography sx={{ fontWeight: 700, fontSize: 13, mb: 1 }}>
        What to check:
      </Typography>
      {sideChecks.map((check, i) => (
        <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.8 }}>
          <CheckCircleIcon />
          <Typography sx={{ fontSize: 13 }}>{check}</Typography>
        </Box>
      ))}
      <Divider sx={{ my: 2 }} />
      <Typography sx={{ fontWeight: 700, fontSize: 13, mb: 0.5 }}>
        Need to add or edit?
      </Typography>
      <Typography sx={{ fontSize: 13, color: "#757575", mb: 2 }}>
        Click any section to edit.
      </Typography>
      <Divider sx={{ mb: 2 }} />
      <Typography sx={{ fontWeight: 700, fontSize: 13, mb: 0.5 }}>
        Why this matters:
      </Typography>
      <Typography sx={{ fontSize: 13, color: "#757575" }}>
        The more accurate this is, the better your content will be.
      </Typography>
    </Box>
  );
}

// \u2500\u2500\u2500 Website Preview Card \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

function WebsiteCard({ screenshot }) {
  const websiteLink = useAppStore((state) => state.websiteLink);
  return (
    <Box
      sx={{
        border: "1px solid #e0e0e0",
        borderRadius: "8px",
        overflow: "hidden",
        width: "100%",
        maxWidth: 380,
        ml: 2,
        mt: 1,
        mb: 1,
        bgcolor: "#fafafa",
      }}
    >
      <Box
        sx={{
          bgcolor: "#f5f5f5",
          p: 1,
          borderBottom: "1px solid #e0e0e0",
          display: "flex",
          gap: 0.5,
        }}
      >
        {["#f44336", "#ff9800", "#4caf50"].map((c, i) => (
          <Box key={i} sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: c }} />
        ))}
      </Box>
      {/* <Box sx={{ p: 2, display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}> */}
        {/* <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: "50%",
            bgcolor: "#2e7d32",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography sx={{ color: "white", fontSize: 14, fontWeight: 600 }}>N</Typography>
        </Box>
        <Typography variant="caption" sx={{ fontWeight: 500 }}>Nathan Chase</Typography>
        <Typography variant="caption" sx={{ color: "#757575", fontSize: 10, textAlign: "center" }}>
          Web Developer | Statistician | Bot Automation
        </Typography>
        <Box sx={{ mt: 1, width: "100%", bgcolor: "#e8f5e9", borderRadius: 1, p: 1 }}>
          <Typography sx={{ fontSize: 9, color: "#555", lineHeight: 1.5 }}>
            I'm a passionate Python developer with strong skills in web development and web
            automation/scraping, and a keen interest in statistics and data analysis.
          </Typography>
        </Box> */}
      {/* </Box> */}
      {screenshot ? (
        <Box
          component="img"
          src={screenshot}
          alt="Website hero preview"
          sx={{ width: "100%", height: 200, objectFit: "cover", objectPosition: "top", display: "block" }}
        />
      ) : (
        <Box sx={{ height: 200, bgcolor: "#f5f5fa", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <CircularProgress size={24} sx={{ color: "#9e9e9e" }} />
        </Box>
      )}

    </Box>
  );
}

// \u2500\u2500\u2500 Edit Dialog \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

function EditDialog({ open, onClose, title, value, onSave }) {
  const [draft, setDraft] = useState(value);
  useEffect(() => { setDraft(value); }, [value]);
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ fontSize: 16, fontWeight: 600 }}>{title}</DialogTitle>
      <DialogContent>
        <TextField
          multiline
          minRows={4}
          fullWidth
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          sx={{ mt: 1 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} sx={{ textTransform: "none", color: "#555" }}>Cancel</Button>
        <Button
          onClick={() => { onSave(draft); onClose(); }}
          variant="contained"
          sx={{ textTransform: "none", bgcolor: "#111", "&:hover": { bgcolor: "#333" } }}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function SectionHeader({ title, onEdit, compact = false }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
      <Typography sx={{ fontSize: compact ? 15 : 17, fontWeight: 700, color: "#111" }}>{title}</Typography>
      <Button
        startIcon={<EditIcon sx={{ fontSize: 14 }} />}
        onClick={onEdit}
        sx={{
          textTransform: "none",
          fontSize: 13,
          color: "#888",
          fontWeight: 400,
          "&:hover": { color: "#111", bgcolor: "transparent" },
          minWidth: 0,
          p: 0,
        }}
      >
        Edit
      </Button>
    </Box>
  );
}

function logoUrl(logo) {
  if (!logo) return "";
  return typeof logo === "string" ? logo : logo.url || logo.image_url || "";
}

function BrandSnapshot({ style, onUploadLogo, onDeleteLogo, onColorsChange, uploading }) {
  const colorInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const [editingColor, setEditingColor] = useState(null);
  const logos = Array.isArray(style?.logos) ? style.logos : [];
  const colors = Array.isArray(style?.colors) ? style.colors : [];
  const editColor = (index) => {
    setEditingColor(index);
    colorInputRef.current?.click();
  };
  const updateColor = (event) => {
    if (editingColor === null) return;
    const next = [...colors];
    next[editingColor] = event.target.value;
    onColorsChange(next);
    setEditingColor(null);
  };
  return (
    <Box
      sx={{
        mb: 2,
        p: 2,
        border: "1px solid #e4e7ec",
        borderRadius: 3,
        bgcolor: "rgba(255,255,255,0.92)",
        boxShadow: "0 16px 40px rgba(17,24,39,0.06)",
      }}
    >
      <Stack direction={{ xs: "column", md: "row" }} spacing={2.5} alignItems={{ xs: "stretch", md: "center" }}>
        <Box sx={{ minWidth: 220 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
            <Typography sx={{ fontSize: 13, fontWeight: 800, color: "#111827" }}>Brand Logo</Typography>
            <Button
              size="small"
              startIcon={uploading ? <CircularProgress size={12} /> : <CloudUploadOutlinedIcon sx={{ fontSize: 15 }} />}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              sx={{ textTransform: "none", color: "#111827", fontSize: 12 }}
            >
              Add
            </Button>
          </Box>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            {logos.map((logo, index) => {
              const src = logoUrl(logo);
              if (!src) return null;
              return (
                <Box
                  key={`${src}-${index}`}
                  sx={{ width: 76, height: 76, position: "relative", border: "1px solid #e5e7eb", borderRadius: 2, bgcolor: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}
                >
                  <Box component="img" src={src} alt="Brand logo" sx={{ maxWidth: "82%", maxHeight: "82%", objectFit: "contain" }} />
                  <IconButton
                    size="small"
                    onClick={() => onDeleteLogo(index)}
                    sx={{ position: "absolute", top: -8, right: -8, bgcolor: "#fff", border: "1px solid #e5e7eb", p: 0.25 }}
                  >
                    <DeleteOutlineIcon sx={{ fontSize: 15 }} />
                  </IconButton>
                </Box>
              );
            })}
            {!logos.length && (
              <Button
                variant="outlined"
                onClick={() => fileInputRef.current?.click()}
                sx={{ width: 76, height: 76, borderStyle: "dashed", borderColor: "#d0d5dd", color: "#667085", textTransform: "none", borderRadius: 2 }}
              >
                <AddIcon />
              </Button>
            )}
          </Box>
          <input ref={fileInputRef} type="file" accept="image/*" hidden multiple onChange={onUploadLogo} />
        </Box>

        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
            <Typography sx={{ fontSize: 13, fontWeight: 800, color: "#111827" }}>Brand Colors</Typography>
            <Button
              size="small"
              startIcon={<AddIcon sx={{ fontSize: 15 }} />}
              onClick={() => onColorsChange([...colors, "#111827"])}
              sx={{ textTransform: "none", color: "#111827", fontSize: 12 }}
            >
              Add color
            </Button>
          </Box>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            {colors.map((color, index) => (
              <Box key={`${color}-${index}`} sx={{ position: "relative" }}>
                <Box
                  onClick={() => editColor(index)}
                  sx={{ width: 58, height: 58, borderRadius: 2, bgcolor: color, border: "1px solid #d0d5dd", cursor: "pointer", boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.35)" }}
                />
                <IconButton
                  size="small"
                  onClick={() => onColorsChange(colors.filter((_, colorIndex) => colorIndex !== index))}
                  sx={{ position: "absolute", top: -8, right: -8, bgcolor: "#fff", border: "1px solid #e5e7eb", p: 0.2 }}
                >
                  <DeleteOutlineIcon sx={{ fontSize: 14 }} />
                </IconButton>
                <Typography sx={{ fontSize: 10, mt: 0.5, color: "#667085", textAlign: "center" }}>{color}</Typography>
              </Box>
            ))}
            {!colors.length && (
              <Typography sx={{ fontSize: 13, color: "#667085", alignSelf: "center" }}>No colors found yet. Add the main brand colors here.</Typography>
            )}
          </Box>
          <input ref={colorInputRef} type="color" hidden onChange={updateColor} />
        </Box>
      </Stack>
    </Box>
  );
}

function StructuredProfileReview({ sections, onEdit }) {
  return (
    <Box
      sx={{
        border: "1px solid #d0d7de",
        borderRadius: 3,
        bgcolor: "#fff",
        px: { xs: 2.5, md: 3 },
        py: 1.5,
        minHeight: 520,
        boxShadow: "0 18px 50px rgba(17,24,39,0.06)",
      }}
    >
      {sections.map((section, index) => (
        <Box key={section.title} sx={{ borderBottom: index === sections.length - 1 ? "none" : "1px solid #eef0f3", py: 2.25 }}>
          <SectionHeader title={section.title} compact onEdit={() => onEdit(index)} />
          <Box
            sx={{
              color: "#202124",
              fontSize: 14,
              lineHeight: 1.72,
              "& p": { mt: 0, mb: 1.2 },
              "& ul, & ol": { pl: 3, my: 1 },
              "& li": { mb: 0.35 },
              "& strong": { fontWeight: 800 },
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {section.body || "No analysis yet. Add details for this section."}
            </ReactMarkdown>
          </Box>
        </Box>
      ))}
    </Box>
  );
}

function EditableProfileDocument({ value, onChange }) {
  const lastExternalValue = useRef(value || "");
  const editor = useEditor({
    extensions: [StarterKit],
    content: marked.parse(value || ""),
    onUpdate: ({ editor }) => {
      const nextMarkdown = turndown.turndown(editor.getHTML());
      lastExternalValue.current = nextMarkdown;
      onChange(nextMarkdown);
    },
  });

  useEffect(() => {
    if (!editor) return;
    const nextValue = value || "";
    if (nextValue !== lastExternalValue.current) {
      lastExternalValue.current = nextValue;
      editor.commands.setContent(marked.parse(nextValue), false);
    }
  }, [editor, value]);

  return (
    <Box
      sx={{
        border: "1px solid #d0d7de",
        borderRadius: 2,
        bgcolor: "#fff",
        px: { xs: 2, md: 3 },
        py: 2.5,
        minHeight: 560,
        "& .tiptap": {
          outline: "none",
          cursor: "text",
          color: "#202124",
          fontSize: 14,
          lineHeight: 1.75,
          "& h1": { fontSize: 26, fontWeight: 700, mt: 0, mb: 2, color: "#111" },
          "& h2": { fontSize: 20, fontWeight: 700, mt: 3, mb: 1.25, color: "#111" },
          "& h3": { fontSize: 17, fontWeight: 700, mt: 2.25, mb: 1, color: "#111" },
          "& p": { mb: 1.4 },
          "& ul, & ol": { pl: 3, mb: 1.5 },
          "& li": { mb: 0.5 },
          "& strong": { fontWeight: 700 },
          "& blockquote": {
            borderLeft: "4px solid #111",
            pl: 2,
            ml: 0,
            color: "#4b5563",
            fontStyle: "italic",
          },
          "& code": {
            bgcolor: "rgba(0,0,0,0.06)",
            px: 0.75,
            py: 0.25,
            borderRadius: 1,
            fontFamily: "monospace",
            fontSize: "0.88em",
          },
        },
      }}
    >
      <EditorContent editor={editor} />
    </Box>
  );
}

// \u2500\u2500\u2500 Profile Data \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

const initialProfile = {
  name: "Samiul Ehsan",
  coreIdentity:
    "Samiul Ehsan is a freelancer specializing in web development and automation. With a strong foundation in Python and a keen interest in statistics and data analysis, Samiul partners with brands and agencies to deliver impactful, data-powered web and automation solutions.",
  marketPositioning: [
    { label: "Primary Positioning", text: '"Your go-to developer for data-driven web solutions" - emphasizing expertise in data analysis and web automation.' },
    { label: "Secondary Positioning", text: '"Crafting seamless user experiences through innovative design" - focusing on UX & UI design.' },
    { label: "Tertiary Positioning", text: '"Transforming ideas into exceptional app experiences" - highlighting capability in both web and mobile app development.' },
  ],
  localCompetitors: [
    "Independent web developers in the United States",
    "Small web development agencies",
  ],
  nationalCompetitors: [
    "Large freelance platforms like Upwork and Fiverr",
    "Established tech agencies specializing in ReactJS and automation",
  ],
  competitiveAdvantages: [
    { bold: "Expertise in Python", rest: " and data analysis for web automation" },
    { bold: "Comprehensive services", rest: " from UX/UI design to app development" },
    { bold: "Experience with cutting-edge technologies", rest: " like ReactJS, Material-UI, and Redux" },
  ],
};

const isThinProfile = (value = "") => {
  const text = value.trim();
  return (
    text.length < 1800 ||
    text.includes("Service details should be refined by the user.") ||
    !text.includes("Customer Demographics") ||
    !text.includes("Competitive Advantages")
  );
};

// \u2500\u2500\u2500 Main Component \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

export default function BusinessProfileFlow() {
  const markdown = useAppStore((state) => state.markdown);
  const setMarkdown = useAppStore((state) => state.setMarkdown);
  const websiteLink = useAppStore((state) => state.websiteLink);
  const image_urls = useAppStore((state) => state.image_urls);
  const setImageUrls = useAppStore((state) => state.setImageUrls);
  const brandStyle = useAppStore((state) => state.brandStyle);
  const setBrandStyle = useAppStore((state) => state.setBrandStyle);
  // Loading steps state
  const [analyse, setAnalyse] = useState(false);
  const [locating, setLocating] = useState(false);
  const [findingCompetitors, setFindingCompetitors] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [editableMarkdown, setEditableMarkdown] = useState(markdown || "");
  const [profileSections, setProfileSections] = useState(() => parseProfileSections(markdown || ""));
  const [websiteScreenshot, setWebsiteScreenshot] = useState("");
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [urlInput, setUrlInput] = useState(websiteLink?.website_link || "");
  const [forceFreshAnalysis, setForceFreshAnalysis] = useState(false);
  const analysisPromiseRef = useRef(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user'));
  const hasFetched = useRef(false);
  const workspaceId = workspaceStorage.getActiveId();

  // Profile state
  const [profile, setProfile] = useState(initialProfile);
  const [editOpen, setEditOpen] = useState(false);
  const [editField, setEditField] = useState(null);

  // useEffect(() => {
  //   const t1 = setTimeout(() => setLocating(true), 1000);
  //   const t2 = setTimeout(() => setFindingCompetitors(true), 2500);
  //   // Small delay after competitors done before fading in profile
  //   const t3 = setTimeout(() => setShowProfile(true), 3200);
  //   return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  // }, []);

  useEffect(() => {
    let cancelled = false;

    const applyBusinessProfile = (data = {}) => {
      const businessProfile = data.business_profile || {};
      if (!businessProfile.id && !businessProfile.markdown) return false;
      const brandStyleData = data.brand_style || data.brand?.brand_context?.brand_style || {};
      const nextMarkdown = businessProfile.markdown || "";
      if (businessProfile.website_url) {
        useAppStore.getState().setWebsiteLink({ website_link: businessProfile.website_url });
      }
      setMarkdown(nextMarkdown);
      setEditableMarkdown(nextMarkdown);
      setProfileSections(parseProfileSections(nextMarkdown));
      setImageUrls(data.images || []);
      setBrandStyle({
        visual_identity: brandStyleData.visual_identity || businessProfile.tone || "",
        colors: brandStyleData.colors || [],
        logos: brandStyleData.logos || [],
        fonts: brandStyleData.fonts || [],
      });
      setWebsiteScreenshot("");
      setAnalyse(true);
      setLocating(true);
      setFindingCompetitors(true);
      setShowProfile(true);
      setAnalysisError("");
      return true;
    };

    const loadExistingProfile = async () => {
      const response = await contentEngineApi.fetchBusinessProfile();
      if (cancelled) return false;
      return applyBusinessProfile(response.data);
    };

    const analyseWebsite = async () => {
      if (showUrlInput) return;
      setAnalysisError("");

      let currentWebsite = websiteLink?.website_link;
      if (!currentWebsite) {
        try {
          const stateResponse = await contentEngineApi.fetchOnboardingState();
          currentWebsite = stateResponse.data?.onboarding?.website_url || "";
          if (currentWebsite) {
            useAppStore.getState().setWebsiteLink({ website_link: currentWebsite });
          }
        } catch (stateError) {
          console.warn('Onboarding website lookup failed.', stateError);
        }
      }
      if (cancelled) return;
      if (!currentWebsite) {
        setAnalysisError("Website URL was not found. Please go back and enter your website URL.");
        setShowUrlInput(true);
        return;
      }
      if (!forceFreshAnalysis) {
        try {
          const existingResponse = await contentEngineApi.fetchBusinessProfile();
          if (cancelled) return;
          const existingWebsite = existingResponse.data?.business_profile?.website_url || "";
          if (existingWebsite && existingWebsite === currentWebsite && applyBusinessProfile(existingResponse.data)) return;
        } catch (profileError) {
          console.warn('Existing business profile lookup failed.', profileError);
        }
      }
      try {
        const storedUser = JSON.parse(localStorage.getItem('user') || 'null');
        if (!storedUser?.id) {
          throw new Error('Your session was not found. Please sign in again.');
        }
        const requestKey = `${storedUser.id}:${workspaceStorage.getActiveId()}:${currentWebsite}`;
        if (!businessProfileRequests.has(requestKey)) {
          const request = contentEngineApi.businessProfile({
            full_name: storedUser.username || storedUser.email || "",
            website_url: currentWebsite,
          }).finally(() => {
            setTimeout(() => businessProfileRequests.delete(requestKey), 5000);
          });
          businessProfileRequests.set(requestKey, request);
        }
        analysisPromiseRef.current = businessProfileRequests.get(requestKey);
        const response = await analysisPromiseRef.current;
        if (cancelled) return;
        if (response.data?.link) {
          useAppStore.getState().setWebsiteLink({ website_link: response.data.link });
        }
        if (!applyBusinessProfile(response.data)) {
          throw new Error("Voice Spark AI did not return a usable business profile.");
        }
        setForceFreshAnalysis(false);
        setShowUrlInput(false);
      } catch (error) {
        analysisPromiseRef.current = null;
        if (cancelled) return;
        try {
          if (forceFreshAnalysis) throw new Error('Fresh analysis failed.');
          if (await loadExistingProfile()) return;
        } catch (profileError) {
          console.warn('Business profile recovery lookup failed.', profileError);
        }
        const apiError = error.response?.data?.error || error.response?.data?.detail;
        const timeoutError = error.code === "ECONNABORTED";
        setAnalysisError(apiError || (timeoutError
          ? "Website analysis is taking longer than expected. If it finished in the background, retry will load the saved profile."
          : error.message || "Website analysis failed. Please check the URL and try again."));
      }
    };

    analyseWebsite();
    return () => {
      cancelled = true;
    };
  }, [forceFreshAnalysis, retryNonce, setBrandStyle, setImageUrls, setMarkdown, showUrlInput, websiteLink?.website_link]);

  const resetAnalysisState = () => {
    analysisPromiseRef.current = null;
    setAnalyse(false);
    setLocating(false);
    setFindingCompetitors(false);
    setShowProfile(false);
    setAnalysisError("");
    setEditableMarkdown("");
    setProfileSections(parseProfileSections(""));
    setImageUrls([]);
    setBrandStyle({ visual_identity: "", colors: [], logos: [], fonts: [] });
    setWebsiteScreenshot("");
  };

  const handleBackToUrl = () => {
    setUrlInput(websiteLink?.website_link || "");
    resetAnalysisState();
    setShowUrlInput(true);
  };

  const handleAnalyzeUrl = async () => {
    const nextUrl = urlInput.trim();
    if (!nextUrl) {
      setAnalysisError("Website URL is required.");
      return;
    }
    resetAnalysisState();
    useAppStore.getState().setWebsiteLink({ website_link: nextUrl });
    try {
      await contentEngineApi.saveOnboardingState({ website_url: nextUrl });
    } catch (error) {
      console.warn("Onboarding website draft could not be saved before re-analysis.", error);
    }
    setShowUrlInput(false);
    setForceFreshAnalysis(true);
    setRetryNonce((value) => value + 1);
  };

  const stepItems = [
    { label: "Analyzed your website", done: analyse, loading: !analysisError && !analyse },
    { label: "Locating business...", done: locating, loading: !analysisError && !locating },
    {
      label: "Looking for competitors",
      done: findingCompetitors,
      loading: !analysisError && locating && !findingCompetitors,
      muted: !locating,
    },
  ];

  const openEdit = (field, value) => { setEditField({ field, value }); setEditOpen(true); };
  const handleSave = (newVal) => {
    if (editField?.type === "section") {
      const nextSections = profileSections.map((section, index) => (
        index === editField.index ? { ...section, body: newVal } : section
      ));
      const nextMarkdown = serializeProfileSections(nextSections);
      setProfileSections(nextSections);
      setEditableMarkdown(nextMarkdown);
      setMarkdown(nextMarkdown);
      return;
    }
    setProfile((prev) => ({ ...prev, [editField.field]: newVal }));
  };
  const openSectionEdit = (index) => {
    const section = profileSections[index];
    setEditField({ type: "section", index, field: section.title, value: section.body || "" });
    setEditOpen(true);
  };
  const patchBrandStyle = (patch) => {
    setBrandStyle({ ...(brandStyle || {}), ...patch });
  };
  const uploadLogo = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setUploadingLogo(true);
    try {
      const storedUser = JSON.parse(localStorage.getItem("user") || "null");
      let latest = brandStyle || {};
      for (const file of files) {
        const formData = new FormData();
        formData.append("image", file);
        formData.append("user_id", storedUser?.id || user?.id);
        formData.append("workspace_id", workspaceId);
        const response = await axios.post(`${config.API_SERVER}auth/user/upload-brand-style-logo/`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        latest = response.data?.data || latest;
      }
      setBrandStyle(latest);
    } catch (error) {
      setAnalysisError(error.response?.data?.error || "Logo upload failed. Please try again.");
    } finally {
      setUploadingLogo(false);
      event.target.value = "";
    }
  };
  const deleteLogo = (index) => {
    const next = { ...(brandStyle || {}), logos: (brandStyle?.logos || []).filter((_, logoIndex) => logoIndex !== index) };
    setBrandStyle(next);
  };
  const handleNavigate = async () => {
    // mkae the axios call 
    if (hasFetched.current) return;
    hasFetched.current = true;
    try {
    const finalMarkdown = serializeProfileSections(profileSections);
    await contentEngineApi.updateBusinessProfile({
      markdown: finalMarkdown,
      website_url: websiteLink.website_link,
      brand_style: brandStyle,
    });
    try {
      await axios.post(config.SCRAPER_SERVER + 'auth/user/create-userprofile/', {
        image_urls:image_urls,
        user_id:user.id,
        markdown: finalMarkdown,
        website_url: websiteLink.website_link,
        brand_style: brandStyle,
        workspace_id:workspaceId
      });
    } catch (legacyError) {
      console.warn('Legacy profile sync failed; continuing with content engine profile.', legacyError);
    }
    navigate('/recommended-visual-style');
  } catch (error) {
    console.error('Error:', error);
    hasFetched.current = false;
  }
  };

  return (
    <Box className="voice-onboarding-page" sx={{ display: "flex", minHeight: "100vh", pb: "60px" }}>

      {/* \u2500\u2500 MAIN CONTENT \u2500\u2500 */}
      <Box sx={{ flex: 1, px: { xs: 3, md: 10 }, py: 6, position: "relative", overflow: "hidden" }}>

        {/* \u2500\u2500 STEP 1: LOADING VIEW \u2014 fades out when profile is ready \u2500\u2500 */}
        {showUrlInput && (
          <Box sx={{ maxWidth: 620, mb: 4 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1, fontSize: 26 }}>
              Analyze a website
            </Typography>
            <Typography sx={{ color: "#667085", fontSize: 14, mb: 2 }}>
              Enter the website you want Voice Spark to use for this workspace. Re-analyzing clears the previous temporary result on this screen.
            </Typography>
            <TextField
              fullWidth
              value={urlInput}
              onChange={(event) => {
                setUrlInput(event.target.value);
                if (analysisError) setAnalysisError("");
              }}
              placeholder="https://example.com"
              size="small"
              error={!!analysisError}
              helperText={analysisError}
              sx={{ mb: 2, "& .MuiOutlinedInput-root": { borderRadius: 2 } }}
            />
            <Stack direction="row" spacing={1.5}>
              <Button
                variant="contained"
                onClick={handleAnalyzeUrl}
                sx={{ bgcolor: "#111", textTransform: "none", borderRadius: 1.5, "&:hover": { bgcolor: "#333" } }}
              >
                Analyze website
              </Button>
              <Button
                variant="outlined"
                onClick={() => setShowUrlInput(false)}
                disabled={!editableMarkdown}
                sx={{ textTransform: "none", borderRadius: 1.5 }}
              >
                Cancel
              </Button>
            </Stack>
          </Box>
        )}
        <Box
          sx={{
            display: showUrlInput ? "none" : "block",
            position: showProfile ? "absolute" : "relative",
            top: showProfile ? 0 : "auto",
            left: showProfile ? 0 : "auto",
            right: showProfile ? 0 : "auto",
            px: showProfile ? { xs: 3, md: 10 } : 0,
            py: showProfile ? 6 : 0,
            opacity: showProfile ? 0 : 1,
            transform: showProfile ? "translateY(-16px)" : "translateY(0)",
            transition: "opacity 0.5s ease, transform 0.5s ease",
            pointerEvents: showProfile ? "none" : "auto",
          }}
        >
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 3, fontSize: 26 }}>
            Building your business profile
          </Typography>

          {stepItems.map((step, idx) => (
            <Box
              key={idx}
              sx={{ display: "flex", alignItems: "flex-start", gap: 1.5, mb: idx === 0 ? 0 : 1.5 }}
            >
              <Box sx={{ mt: "2px", flexShrink: 0 }}>
                {step.loading ? (
                  <CircularProgress size={20} thickness={5} sx={{ color: "#9e9e9e" }} />
                ) : step.done ? (
                  <CheckCircleIcon />
                ) : (
                  <GrayCircleIcon />
                )}
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography
                  sx={{
                    fontSize: 15,
                    fontWeight: step.done ? 500 : 400,
                    color: step.muted ? "#bdbdbd" : step.done ? "#2e7d32" : "#424242",
                    mt: "1px",
                  }}
                >
                  {step.label}
                </Typography>
                {idx === 0 && <WebsiteCard screenshot={websiteScreenshot} />}
              </Box>
            </Box>
          ))}
          {analysisError && (
            <Box sx={{ mt: 3 }}>
              <Typography sx={{ color: "#b91c1c", fontSize: 14, mb: 1 }}>
                {analysisError}
              </Typography>
              <Button
                variant="outlined"
                onClick={() => {
                  analysisPromiseRef.current = null;
                  setAnalyse(false);
                  setLocating(false);
                  setFindingCompetitors(false);
                  setShowProfile(false);
                  setRetryNonce((value) => value + 1);
                }}
                sx={{ textTransform: "none", borderRadius: "6px" }}
              >
                Retry analysis
              </Button>
            </Box>
          )}
        </Box>

        {/* \u2500\u2500 STEP 2: PROFILE VIEW \u2014 fades in when loading is done \u2500\u2500 */}
        <Box
          sx={{
            opacity: showProfile ? 1 : 0,
            transform: showProfile ? "translateY(0)" : "translateY(20px)",
            transition: "opacity 0.6s ease, transform 0.6s ease",
            pointerEvents: showProfile ? "auto" : "none",
          }}
        >
          <Typography sx={{ fontSize: 13, color: "#667085", mb: 1.5 }}>
            Review the brand profile, logo, and colors before continuing. These fields stay synced with Brand Kit.
          </Typography>
          <Button
            startIcon={<ArrowBackIcon sx={{ fontSize: 16 }} />}
            onClick={handleBackToUrl}
            sx={{ mb: 2, textTransform: "none", color: "#111", fontWeight: 700, p: 0, minWidth: 0 }}
          >
            Back to website URL
          </Button>
          <BrandSnapshot
            style={brandStyle || {}}
            uploading={uploadingLogo}
            onUploadLogo={uploadLogo}
            onDeleteLogo={deleteLogo}
            onColorsChange={(colors) => patchBrandStyle({ colors })}
          />
          <StructuredProfileReview sections={profileSections} onEdit={openSectionEdit} />
        </Box>
      </Box>

      {/* \u2500\u2500 SIDEBAR \u2500\u2500 */}
      <Sidebar />

      {/* \u2500\u2500 FOOTER \u2500\u2500 */}
      <Box
        sx={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          px: 4,
          py: 1.5,
          borderTop: "1px solid #e0e0e0",
          bgcolor: "#fff",
        }}
      >
        {/* <Button sx={{ color: "#555", textTransform: "none", fontWeight: 400 }}>Back</Button> */}
        <Button
          variant="contained"
          disabled={!showProfile || showUrlInput}
          // component={Link} 
          // to='/visual-style'
          onClick={handleNavigate}
          sx={{
            bgcolor: showProfile ? "#111" : "#bdbdbd",
            color: "#fff",
            textTransform: "none",
            borderRadius: "6px",
            fontWeight: 500,
            px: 3,
            "&:hover": { bgcolor: showProfile ? "#333" : "#bdbdbd" },
            "&.Mui-disabled": { bgcolor: "#bdbdbd", color: "#fff" },
          }}
        >
          Looks good
        </Button>
      </Box>

      {/* \u2500\u2500 EDIT DIALOG \u2500\u2500 */}
      <AmbientWorking
        active={!showProfile && !analysisError}
        title="Analyzing website"
        detail="Voice Spark is building the profile. The page will unlock as soon as the first analysis is ready."
      />

      {editField && (
        <EditDialog
          open={editOpen}
          onClose={() => setEditOpen(false)}
          title={`Edit ${editField.field}`}
          value={editField.value}
          onSave={handleSave}
        />
      )}
    </Box>
  );
}
