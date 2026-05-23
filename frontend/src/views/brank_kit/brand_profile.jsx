import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import config from "../../config";
import axios from "axios";
import { workspaceStorage } from "../workspace/workSpaceAPi";

const FIXED_SECTIONS = [
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

const normalizeTitle = (value) => String(value || "").replace(/^#+\s*/, "").trim();

const SECTION_ALIASES = new Map([
  ["business overview and positioning", "Business Overview & Positioning"],
  ["business overview & positioning", "Business Overview & Positioning"],
  ["market positioning", "Market Positioning"],
  ["direct competitors", "Direct Competitors"],
  ["competitive advantages", "Competitive Advantages"],
  ["primary customer segments", "Primary Customer Segments"],
  ["customer demographics and psychographics", null],
  ["most popular products and services", null],
  ["core offer areas", "Top Revenue Generators (based on website prominence)"],
  ["top revenue generators", "Top Revenue Generators (based on website prominence)"],
  ["top revenue generators (based on website prominence)", "Top Revenue Generators (based on website prominence)"],
  ["emerging growth areas", "Emerging Growth Areas"],
  ["why customers choose", null],
  ["primary value drivers", "Primary Value Drivers"],
  ["emotional benefits", "Emotional Benefits"],
  ["brand tone and communication style", null],
  ["brand story", "Brand Story"],
  ["brand personality", "Brand Personality"],
]);

function sectionForHeading(rawTitle) {
  const title = normalizeTitle(rawTitle);
  const lower = title.toLowerCase();
  if (FIXED_SECTIONS.includes(title)) return title;
  if (SECTION_ALIASES.has(lower)) return SECTION_ALIASES.get(lower);
  if (/^the\s+.+\s+brand story$/i.test(title)) return "Brand Story";
  if (/\bbusiness profile$/i.test(title)) return "Business Name";
  if (/^why customers choose\b/i.test(title)) return null;
  return undefined;
}

function parseSections(markdown) {
  const sections = FIXED_SECTIONS.map((title) => ({ title, body: "" }));
  const byTitle = new Map(sections.map((section) => [section.title.toLowerCase(), section]));
  let current = null;
  for (const line of String(markdown || "").split(/\r?\n/)) {
    const heading = /^(#{1,4})\s+(.+?)\s*$/.exec(line);
    if (heading) {
      const mapped = sectionForHeading(heading[2]);
      if (mapped === null) {
        current = null;
        continue;
      }
      if (mapped) {
        current = byTitle.get(mapped.toLowerCase()) || null;
        continue;
      }
      continue;
    }
    if (current) {
      current.body = `${current.body}${current.body ? "\n" : ""}${line}`;
    }
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

function serializeSections(sections) {
  return sections
    .map((section) => `## ${section.title}\n\n${String(section.body || "").trim()}`)
    .join("\n\n")
    .trim();
}

export default function BrandProfile() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [sections, setSections] = useState(() => parseSections(""));
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState("");
  const user = JSON.parse(localStorage.getItem("user") || "null");
  const workspaceId = workspaceStorage.getActiveId();

  useEffect(() => {
    if (!user?.id || !workspaceId) {
      setError("Failed to load profile.");
      setLoading(false);
      return;
    }
    axios.post(`${config.API_SERVER}auth/user/get-markdown/`, {
      user_id: user.id,
      workspace_id: workspaceId,
    })
      .then((res) => setSections(parseSections(res.data.markdown || "")))
      .catch(() => setError("Failed to load profile."))
      .finally(() => setLoading(false));
  }, [user?.id, workspaceId]);

  const saveMarkdown = async (nextSections = sections) => {
    setSaving(true);
    setSaveSuccess(false);
    setError("");
    try {
      await axios.post(`${config.API_SERVER}auth/user/update-markdown/`, {
        user_id: user.id,
        markdown: serializeSections(nextSections),
        workspace_id: workspaceId,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      setError("Failed to save changes.");
    } finally {
      setSaving(false);
    }
  };

  const openEditor = (index) => {
    setEditing(index);
    setDraft(sections[index]?.body || "");
  };

  const saveSection = async () => {
    const nextSections = sections.map((section, index) => (
      index === editing ? { ...section, body: draft } : section
    ));
    setSections(nextSections);
    setEditing(null);
    setDraft("");
    await saveMarkdown(nextSections);
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 900, mx: "auto", px: 3, py: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 2, mb: 2 }}>
        {saveSuccess && <Alert severity="success" sx={{ py: 0 }}>Saved successfully!</Alert>}
        {error && <Alert severity="error" sx={{ py: 0 }}>{error}</Alert>}
      </Box>

      {sections.map((section, index) => (
        <Box key={section.title} sx={{ borderBottom: "1px solid #E5E7EB", py: 2.25 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, mb: 1 }}>
            <Typography sx={{ fontSize: 15, fontWeight: 700, color: "#111827" }}>{section.title}</Typography>
            <Button
              size="small"
              startIcon={<EditOutlinedIcon sx={{ fontSize: 14 }} />}
              onClick={() => openEditor(index)}
              sx={{ textTransform: "none", minWidth: 0, color: "#111827", fontSize: 12 }}
            >
              Edit
            </Button>
          </Box>
          <Box
            sx={{
              color: "#111827",
              fontSize: 13,
              lineHeight: 1.7,
              "& p": { mt: 0, mb: 1 },
              "& ul, & ol": { pl: 3, my: 1 },
              "& li": { mb: 0.25 },
              "& strong": { fontWeight: 800 },
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {section.body || "No analysis yet."}
            </ReactMarkdown>
          </Box>
        </Box>
      ))}

      <Dialog open={editing !== null} onClose={() => setEditing(null)} maxWidth="md" fullWidth>
        <DialogTitle>{editing !== null ? sections[editing]?.title : "Edit"}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            minRows={10}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)} disabled={saving}>Cancel</Button>
          <Button onClick={saveSection} disabled={saving} variant="contained">
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
