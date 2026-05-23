import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import RefreshIcon from "@mui/icons-material/Refresh";
import SaveIcon from "@mui/icons-material/Save";
import { contentEngineApi } from "../login_register/content_engine_api";
import { AmbientWorking } from "../../components/VoiceSparkUI";

const SOURCE_TYPES = [
  { value: "my_website", label: "My Website" },
  { value: "competitor", label: "Competitor Website" },
];

const CHANNELS = [
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "x", label: "X" },
];

function listToText(value) {
  if (Array.isArray(value)) return value.map((item) => listToText(item)).join("\n");
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, nested]) => {
        const label = key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
        const body = listToText(nested);
        return body ? `${label}:\n${body}` : label;
      })
      .filter(Boolean)
      .join("\n\n");
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try {
        return listToText(JSON.parse(trimmed));
      } catch {
        return value;
      }
    }
  }
  return value || "";
}

function textToList(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function updateNestedList(item, parent, field, value) {
  return {
    [parent]: {
      ...(item[parent] || {}),
      [field]: textToList(value),
    },
  };
}

function normalizeCompetitorUrl(value = "") {
  const trimmed = String(value || "").trim();
  if (!trimmed) return "";
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function competitorUrlError(value = "") {
  const raw = String(value || "").trim();
  if (!raw) return "A valid competitor website URL is required.";
  if (/^(website|url|competitor\.com|https?:\/\/competitor\.com)$/i.test(raw)) {
    return "A real competitor website URL is required.";
  }
  try {
    const parsed = new URL(normalizeCompetitorUrl(raw));
    const host = parsed.hostname.replace(/^www\./i, "").toLowerCase();
    if (!host || !host.includes(".") || ["competitor.com", "example.com", "example.org", "example.net"].includes(host)) {
      return "A real competitor website URL is required.";
    }
    return "";
  } catch {
    return "A valid competitor website URL is required.";
  }
}

function SectionShell({ title, subtitle, children, actions }) {
  return (
    <Box sx={{ flex: 1, px: 4, pt: 3, pb: 6 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2} mb={2}>
        <Box>
          <Typography variant="h6" fontWeight={800}>{title}</Typography>
          {subtitle && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{subtitle}</Typography>}
        </Box>
        {actions}
      </Stack>
      <Divider sx={{ mb: 3 }} />
      {children}
    </Box>
  );
}

export function SourceMatrixContent() {
  const [sources, setSources] = useState([]);
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] = useState("my_website");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    contentEngineApi.fetchSourceMatrix()
      .then(({ data }) => setSources(data.sources || []))
      .catch((err) => setError(err.response?.data?.error || "Source Matrix could not be loaded."))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const analyze = async () => {
    if (!url.trim()) return;
    setAnalyzing(true);
    setError("");
    try {
      await contentEngineApi.analyzeSourceMatrix({ url, source_type: sourceType });
      setUrl("");
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <SectionShell title="Source Matrix" subtitle="Track every website source analyzed for this workspace.">
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Card variant="outlined" sx={{ p: 2, borderRadius: 2, mb: 3 }}>
        <Typography fontWeight={700} mb={1}>Add source</Typography>
        <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
          <TextField size="small" fullWidth placeholder="https://example.com" value={url} onChange={(event) => setUrl(event.target.value)} />
          <Select size="small" value={sourceType} onChange={(event) => setSourceType(event.target.value)} sx={{ minWidth: 190 }}>
            {SOURCE_TYPES.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}
          </Select>
          <Button variant="contained" onClick={analyze} disabled={analyzing} sx={{ bgcolor: "#111", textTransform: "none" }}>
            {analyzing ? "Analyzing..." : "Analyze"}
          </Button>
        </Stack>
        {analyzing && (
          <Stack direction="row" gap={1} sx={{ mt: 2, color: "text.secondary" }} flexWrap="wrap">
            {["Identifying your brand", "Pulling photos & media", "Analyzing competitors"].map((label) => <Chip key={label} label={label} size="small" />)}
          </Stack>
        )}
      </Card>
      {loading ? <CircularProgress size={24} /> : (
        <Stack spacing={1.5}>
          {sources.map((source) => (
            <Card key={source.id} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" gap={2}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography fontWeight={700} noWrap>{source.url}</Typography>
                  <Stack direction="row" gap={1} sx={{ mt: 0.75 }}>
                    <Chip size="small" label={source.source_type === "competitor" ? "Competitor" : "My Website"} />
                    <Chip size="small" color={source.status === "failed" ? "error" : source.status === "analyzed" ? "success" : "default"} label={source.status} />
                    {source.last_analyzed_at && <Chip size="small" label={new Date(source.last_analyzed_at).toLocaleString()} />}
                  </Stack>
                  {source.error && <Typography color="error" variant="body2" sx={{ mt: 1 }}>{source.error}</Typography>}
                </Box>
                <Button size="small" startIcon={<RefreshIcon />} onClick={() => {
                  setUrl(source.url);
                  setSourceType(source.source_type);
                }} sx={{ textTransform: "none" }}>Reuse</Button>
              </Stack>
            </Card>
          ))}
        </Stack>
      )}
      <AmbientWorking active={analyzing} title="Analyzing source" detail="You can keep editing other brand intelligence while this finishes." />
    </SectionShell>
  );
}

export function CompetitorAnalysisContent() {
  const [items, setItems] = useState([]);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pendingSources, setPendingSources] = useState([]);
  const [needsReview, setNeedsReview] = useState([]);

  const load = async () => {
    try {
      const { data } = await contentEngineApi.fetchCompetitors();
      const nextItems = data.competitors || [];
      setItems(nextItems);
      setNeedsReview(data.needs_review || []);
      return nextItems;
    } catch (err) {
      setError(err.response?.data?.error || "Competitors could not be loaded.");
      return [];
    }
  };

  const loadSourceState = async () => {
    try {
      const { data } = await contentEngineApi.fetchSourceMatrix();
      const pending = (data.sources || []).filter((entry) => (
        entry.source_type === "competitor" && ["pending", "analyzing"].includes(entry.status)
      ));
      setPendingSources(pending);
      return pending;
    } catch {
      return [];
    }
  };

  useEffect(() => {
    load();
    loadSourceState();
  }, []);

  useEffect(() => {
    if (!pendingSources.length) return undefined;
    const timer = window.setInterval(async () => {
      const pending = await loadSourceState();
      await load();
      if (!pending.length) window.clearInterval(timer);
    }, 6000);
    return () => window.clearInterval(timer);
  }, [pendingSources.length]);

  const add = async () => {
    const validationError = competitorUrlError(url);
    if (validationError) {
      setError(validationError);
      return;
    }
    setBusy(true);
    setError("");
    try {
      await contentEngineApi.addCompetitor({ website_url: normalizeCompetitorUrl(url) });
      setUrl("");
      await load();
      await loadSourceState();
    } catch (err) {
      const latestItems = await load();
      const normalizedUrl = url.trim().replace(/^https?:\/\//i, "").replace(/\/$/, "");
      const savedCompetitor = latestItems.find((item) => (
        (item.website_url || "").replace(/^https?:\/\//i, "").replace(/\/$/, "") === normalizedUrl
      ));
      if (savedCompetitor) {
        setUrl("");
        setError("");
      } else {
        setError(err.response?.data?.error || "Competitor analysis failed.");
      }
    } finally {
      setBusy(false);
    }
  };

  const update = async (item, patch) => {
    const next = { ...item, ...patch };
    if ("website_url" in patch) {
      const validationError = competitorUrlError(patch.website_url);
      if (validationError) {
        setError(validationError);
        return;
      }
      next.website_url = normalizeCompetitorUrl(patch.website_url);
    }
    if ("name" in patch && !String(patch.name || "").trim()) {
      setError("Competitor name is required.");
      return;
    }
    setError("");
    setItems((prev) => prev.map((row) => row.id === item.id ? next : row));
    try {
      await contentEngineApi.updateCompetitor(item.id, next);
    } catch (err) {
      setError(err.response?.data?.error || "Competitor could not be updated.");
      await load();
    }
  };

  const remove = async (id) => {
    await contentEngineApi.deleteCompetitor(id);
    setItems((prev) => prev.filter((row) => row.id !== id));
    setNeedsReview((prev) => prev.filter((row) => row.id !== id));
  };

  const reanalyze = async (id) => {
    setBusy(true);
    try {
      await contentEngineApi.reanalyzeCompetitor(id);
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionShell title="Competitor Analysis" subtitle="Generated and manual competitor intelligence for the active workspace.">
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {pendingSources.length > 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Competitor analysis is still running. This can take a few minutes while we crawl and compare sources.
        </Alert>
      )}
      <Card variant="outlined" sx={{ p: 2, borderRadius: 2, mb: 3 }}>
        <Typography fontWeight={700} mb={1}>Analyze competitor URL</Typography>
        <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
          <TextField size="small" fullWidth placeholder="https://www.realcompetitor.com" value={url} onChange={(event) => setUrl(event.target.value)} />
          <Button variant="contained" disabled={busy} onClick={add} sx={{ bgcolor: "#111", textTransform: "none" }}>
            {busy ? "Analyzing..." : "Add Competitor"}
          </Button>
        </Stack>
      </Card>
      <Stack spacing={2}>
        {items.map((item) => (
          <Card key={item.id} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
              <Box sx={{ flex: 1 }}>
                <TextField variant="standard" fullWidth value={item.name || ""} onChange={(event) => update(item, { name: event.target.value })} sx={{ mb: 1 }} inputProps={{ style: { fontWeight: 800, fontSize: 18 } }} />
                <TextField size="small" fullWidth label="Website" value={item.website_url || ""} onChange={(event) => update(item, { website_url: event.target.value })} sx={{ mb: 1.5 }} />
                <TextField size="small" fullWidth multiline minRows={2} label="Pricing model" value={item.pricing_model || ""} onChange={(event) => update(item, { pricing_model: event.target.value })} sx={{ mb: 1.5 }} />
                <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
                  <TextField size="small" fullWidth multiline minRows={4} label="Key features" value={listToText(item.key_features)} onChange={(event) => update(item, { key_features: textToList(event.target.value) })} />
                  <TextField size="small" fullWidth multiline minRows={4} label="Differentiators" value={listToText(item.differentiators)} onChange={(event) => update(item, { differentiators: textToList(event.target.value) })} />
                </Stack>
                <Box sx={{ mt: 2 }}>
                  <Typography fontWeight={800} sx={{ mb: 1 }}>SWOT</Typography>
                  <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
                    {[
                      ["strengths", "Strengths"],
                      ["weaknesses", "Weaknesses"],
                      ["opportunities", "Opportunities"],
                      ["threats", "Threats"],
                    ].map(([field, label]) => (
                      <TextField
                        key={field}
                        size="small"
                        fullWidth
                        multiline
                        minRows={4}
                        label={label}
                        value={listToText(item.swot?.[field])}
                        onChange={(event) => update(item, updateNestedList(item, "swot", field, event.target.value))}
                      />
                    ))}
                  </Stack>
                </Box>
                <Box sx={{ mt: 2 }}>
                  <Typography fontWeight={800} sx={{ mb: 1 }}>Objection Handling</Typography>
                  <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
                    <TextField
                      size="small"
                      fullWidth
                      multiline
                      minRows={4}
                      label="Why buyers choose them"
                      value={listToText(item.objection_handling?.why_users_choose_them)}
                      onChange={(event) => update(item, updateNestedList(item, "objection_handling", "why_users_choose_them", event.target.value))}
                    />
                    <TextField
                      size="small"
                      fullWidth
                      multiline
                      minRows={4}
                      label="Counter positioning"
                      value={listToText(item.objection_handling?.counter_positioning)}
                      onChange={(event) => update(item, updateNestedList(item, "objection_handling", "counter_positioning", event.target.value))}
                    />
                  </Stack>
                </Box>
              </Box>
              <Stack>
                <IconButton onClick={() => reanalyze(item.id)}><RefreshIcon /></IconButton>
                <IconButton color="error" onClick={() => remove(item.id)}><DeleteOutlineIcon /></IconButton>
              </Stack>
            </Stack>
          </Card>
        ))}
      </Stack>
      {needsReview.length > 0 && (
        <Card variant="outlined" sx={{ p: 2, borderRadius: 2, mt: 2, bgcolor: "#FFF7ED", borderColor: "#FDBA74" }}>
          <Typography fontWeight={800} mb={1}>Needs manual review</Typography>
          <Stack spacing={1}>
            {needsReview.map((item) => (
              <Stack key={item.id} direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ xs: "flex-start", sm: "center" }} justifyContent="space-between">
                <Box>
                  <Typography sx={{ fontWeight: 700 }}>{item.name || "Unnamed competitor"}</Typography>
                  <Typography sx={{ fontSize: 13, color: "#9A3412" }}>{item.review_reason || "Missing real competitor website URL."}</Typography>
                </Box>
                <IconButton color="error" onClick={() => remove(item.id)}><DeleteOutlineIcon /></IconButton>
              </Stack>
            ))}
          </Stack>
        </Card>
      )}
      <AmbientWorking active={busy || pendingSources.length > 0} title="Analyzing competitor" detail="Competitor research continues without freezing the page." />
    </SectionShell>
  );
}

export function ChannelVoiceContent() {
  const [channels, setChannels] = useState([]);
  const [active, setActive] = useState("facebook");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    contentEngineApi.fetchChannelVoice().then(({ data }) => setChannels(data.channels || []));
  }, []);

  const current = useMemo(() => channels.find((item) => item.platform === active) || { platform: active }, [channels, active]);
  const setField = (field, value) => setChannels((prev) => {
    const exists = prev.some((item) => item.platform === active);
    const next = prev.map((item) => item.platform === active ? { ...item, [field]: value } : item);
    return exists ? next : [...next, { platform: active, [field]: value }];
  });
  const save = async () => {
    const { data } = await contentEngineApi.updateChannelVoice(current);
    setChannels((prev) => prev.map((item) => item.platform === active ? data.channel : item));
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  };

  return (
    <SectionShell title="Brand Voice" subtitle="Each channel can have its own tone, emotion, character, syntax, and language." actions={<Button startIcon={<SaveIcon />} variant="contained" onClick={save} sx={{ bgcolor: "#111", textTransform: "none" }}>Save</Button>}>
      {saved && <Alert severity="success" sx={{ mb: 2 }}>Saved.</Alert>}
      <Stack direction="row" gap={1} flexWrap="wrap" mb={3}>
        {CHANNELS.map((item) => <Chip key={item.value} label={item.label} onClick={() => setActive(item.value)} color={active === item.value ? "primary" : "default"} />)}
      </Stack>
      <Stack spacing={2} sx={{ maxWidth: 820 }}>
        {["tone", "emotion", "character", "syntax", "language"].map((field) => (
          <TextField key={field} label={field.replace("_", " ").replace(/^\w/, (c) => c.toUpperCase())} multiline minRows={2} value={current[field] || ""} onChange={(event) => setField(field, event.target.value)} helperText={`Example: ${field === "tone" ? "Professional but human" : field === "syntax" ? "Short clear sentences, strong hooks" : "Brand-specific guidance"}`} />
        ))}
      </Stack>
    </SectionShell>
  );
}

export function AudienceProfilesContent() {
  const [items, setItems] = useState([]);
  useEffect(() => { contentEngineApi.fetchAudienceProfiles().then(({ data }) => setItems(data.audiences || [])); }, []);
  const add = async () => {
    const { data } = await contentEngineApi.addAudienceProfile({ name: "New ICP" });
    setItems((prev) => [...prev, data.audience]);
  };
  const update = async (item, patch) => {
    const next = { ...item, ...patch };
    setItems((prev) => prev.map((row) => row.id === item.id ? next : row));
    await contentEngineApi.updateAudienceProfile(item.id, next);
  };
  const remove = async (id) => {
    await contentEngineApi.deleteAudienceProfile(id);
    setItems((prev) => prev.filter((item) => item.id !== id));
  };
  return (
    <SectionShell title="Audience Profiles" subtitle="Create multiple editable ICPs. AI can use these, but you can manage them manually." actions={<Button startIcon={<AddIcon />} variant="contained" onClick={add} sx={{ bgcolor: "#111", textTransform: "none" }}>Add ICP</Button>}>
      <Stack spacing={2}>
        {items.map((item) => (
          <Card key={item.id} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
            <Stack direction="row" justifyContent="space-between" gap={2}>
              <TextField variant="standard" label="Name" value={item.name || ""} onChange={(event) => update(item, { name: event.target.value })} sx={{ flex: 1 }} />
              <IconButton color="error" onClick={() => remove(item.id)}><DeleteOutlineIcon /></IconButton>
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} gap={1.5} sx={{ mt: 2 }}>
              {["age_range", "location", "occupation", "awareness_level"].map((field) => (
                <TextField key={field} size="small" fullWidth label={field.replace("_", " ")} value={item[field] || ""} onChange={(event) => update(item, { [field]: event.target.value })} />
              ))}
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} gap={1.5} sx={{ mt: 1.5 }}>
              {["pain_points", "frustrations", "goals", "behaviors", "buying_patterns"].map((field) => (
                <TextField key={field} size="small" fullWidth multiline minRows={3} label={field.replace("_", " ")} value={listToText(item[field])} onChange={(event) => update(item, { [field]: textToList(event.target.value) })} />
              ))}
            </Stack>
          </Card>
        ))}
      </Stack>
    </SectionShell>
  );
}

export function ManualDataContent() {
  const [data, setData] = useState({});
  const [saved, setSaved] = useState(false);
  useEffect(() => { contentEngineApi.fetchManualData().then(({ data }) => setData(data.manual_data || {})); }, []);
  const save = async () => {
    const res = await contentEngineApi.updateManualData(data);
    setData(res.data.manual_data || {});
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  };
  return (
    <SectionShell title="Manual Business Data" subtitle="Compliance and operations context that AI should respect." actions={<Button startIcon={<SaveIcon />} variant="contained" onClick={save} sx={{ bgcolor: "#111", textTransform: "none" }}>Save</Button>}>
      {saved && <Alert severity="success" sx={{ mb: 2 }}>Saved.</Alert>}
      <Stack spacing={2} sx={{ maxWidth: 900 }}>
        {[
          ["processes", "Processes", "Example: lead comes from Messenger, team qualifies, then books a call."],
          ["methodology", "Methodology", "Example: audit, strategy, implementation, optimization."],
          ["deliverables", "Deliverables", "Example: chatbot setup, automation flows, monthly reports."],
          ["pricing", "Pricing", "Example: starter package, monthly retainer, custom plan."],
          ["onboarding", "Onboarding", "Example: kickoff call, access collection, launch checklist."],
        ].map(([key, label, helper]) => (
          <TextField key={key} label={label} helperText={helper} multiline minRows={4} value={data[key] || ""} onChange={(event) => setData((prev) => ({ ...prev, [key]: event.target.value }))} />
        ))}
      </Stack>
    </SectionShell>
  );
}
