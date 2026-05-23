import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CircularProgress,
  Divider,
  FormControl,
  Grid2 as Grid,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import CheckIcon from "@mui/icons-material/Check";
import EditIcon from "@mui/icons-material/Edit";
import TopBar from "../../TopBar";
import { contentEngineApi } from "../login_register/content_engine_api";
import { useNavigate } from "react-router-dom";
import { VISUAL_STYLE_OPTIONS as CONTENT_STYLE_OPTIONS } from "../login_register/visual_style_options";

const LANGUAGES = [
  ["en", "English"],
  ["bn", "Bangla"],
  ["hi", "Hindi"],
  ["ur", "Urdu"],
  ["ar", "Arabic"],
  ["es", "Spanish"],
  ["fr", "French"],
  ["de", "German"],
  ["it", "Italian"],
  ["pt", "Portuguese"],
  ["nl", "Dutch"],
  ["sv", "Swedish"],
  ["no", "Norwegian"],
  ["da", "Danish"],
  ["fi", "Finnish"],
  ["pl", "Polish"],
  ["tr", "Turkish"],
  ["ru", "Russian"],
  ["uk", "Ukrainian"],
  ["fa", "Persian"],
  ["he", "Hebrew"],
  ["id", "Indonesian"],
  ["ms", "Malay"],
  ["th", "Thai"],
  ["vi", "Vietnamese"],
  ["zh", "Chinese"],
  ["ja", "Japanese"],
  ["ko", "Korean"],
  ["ta", "Tamil"],
  ["te", "Telugu"],
  ["mr", "Marathi"],
  ["gu", "Gujarati"],
  ["pa", "Punjabi"],
  ["ne", "Nepali"],
  ["si", "Sinhala"],
  ["my", "Burmese"],
  ["sw", "Swahili"],
  ["am", "Amharic"],
  ["yo", "Yoruba"],
  ["ha", "Hausa"],
  ["zu", "Zulu"],
  ["el", "Greek"],
  ["ro", "Romanian"],
  ["cs", "Czech"],
  ["hu", "Hungarian"],
  ["sk", "Slovak"],
  ["bg", "Bulgarian"],
  ["hr", "Croatian"],
  ["sr", "Serbian"],
  ["sl", "Slovenian"],
  ["et", "Estonian"],
  ["lv", "Latvian"],
  ["lt", "Lithuanian"],
];

const FALLBACK_TIMEZONES = [
  "Asia/Dhaka",
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
];

const TIMEZONES = typeof Intl.supportedValuesOf === "function"
  ? Intl.supportedValuesOf("timeZone")
  : FALLBACK_TIMEZONES;

function StyleCard({ option, selected, onSelect }) {
  return (
    <Card
      onClick={onSelect}
      variant="outlined"
      sx={{
        position: "relative",
        overflow: "hidden",
        borderRadius: 3,
        cursor: "pointer",
        borderColor: selected ? "#111827" : "#E5E7EB",
        boxShadow: selected ? "0 16px 42px rgba(17,24,39,0.14)" : "0 10px 26px rgba(17,24,39,0.06)",
      }}
    >
      <Box component="img" src={option.image_url || option.image} alt={option.name} sx={{ width: "100%", height: 190, objectFit: "cover", objectPosition: option.imagePosition || "center", display: "block" }} />
      <Box sx={{ position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(0,0,0,.84), rgba(0,0,0,.08) 58%)" }} />
      <Box
        sx={{
          position: "absolute",
          top: 12,
          left: 12,
          width: 28,
          height: 28,
          borderRadius: 1,
          bgcolor: selected ? "#fff" : "rgba(255,255,255,.22)",
          border: selected ? "none" : "1px solid rgba(255,255,255,.65)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {selected && <CheckIcon sx={{ fontSize: 18, color: "#111827" }} />}
      </Box>
      <Box sx={{ position: "absolute", left: 16, right: 16, bottom: 14 }}>
        <Typography sx={{ color: "#fff", fontWeight: 900, fontSize: 18, textShadow: "0 2px 12px rgba(0,0,0,0.45)" }}>{option.name}</Typography>
        <Typography sx={{ color: "rgba(255,255,255,.82)", fontSize: 12, lineHeight: 1.35, mt: 0.5 }}>
          {option.description}
        </Typography>
      </Box>
    </Card>
  );
}

export default function ContentPreferences() {
  const navigate = useNavigate();
  const [languageCode, setLanguageCode] = useState("en");
  const [contentStyle, setContentStyle] = useState(CONTENT_STYLE_OPTIONS[0]);
  const [timezoneName, setTimezoneName] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Dhaka");
  const [defaultScheduleTime, setDefaultScheduleTime] = useState("09:00");
  const [smartCaptions, setSmartCaptions] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [channelVoices, setChannelVoices] = useState([]);

  const selectedLanguage = useMemo(
    () => LANGUAGES.find(([code]) => code === languageCode) || LANGUAGES[0],
    [languageCode]
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    contentEngineApi.fetchContentPreferences()
      .then(({ data }) => {
        if (!active) return;
        const preferences = data?.data || {};
        if (preferences.language?.code) setLanguageCode(preferences.language.code);
        if (preferences.content_style?.id) {
          const matched = CONTENT_STYLE_OPTIONS.find((item) => item.id === preferences.content_style.id);
          setContentStyle({ ...(matched || CONTENT_STYLE_OPTIONS[0]), ...preferences.content_style });
        }
        if (preferences.timezone) setTimezoneName(preferences.timezone);
        if (preferences.default_schedule_time) setDefaultScheduleTime(preferences.default_schedule_time);
        if (preferences.smart_captions) setSmartCaptions(preferences.smart_captions.enabled !== false);
      })
      .catch((err) => {
        if (active) setError(err.response?.data?.error || "Content preferences could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    contentEngineApi.fetchChannelVoice()
      .then(({ data }) => {
        if (active) setChannelVoices(data.channels || []);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await contentEngineApi.updateContentPreferences({
        language: { code: selectedLanguage[0], label: selectedLanguage[1] },
        content_style: { ...contentStyle, label: contentStyle.name || contentStyle.label },
        timezone: timezoneName,
        default_schedule_time: defaultScheduleTime,
        smart_captions: { enabled: smartCaptions },
      });
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err.response?.data?.error || "Content preferences could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box>
      <TopBar title="Content Preference" />
      <Box sx={{ maxWidth: 1040, mx: "auto", py: 4, px: 3 }}>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ xs: "flex-start", sm: "center" }} gap={2} mb={3}>
          <Box>
            <Typography variant="h5" fontWeight={800}>Content Preferences</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              These settings control captions, blog posts, and image-generation prompts for future content.
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={14} sx={{ color: "#fff" }} /> : <SaveIcon />}
            onClick={handleSave}
            disabled={loading || saving}
            sx={{ bgcolor: "#111", borderRadius: 1.5, textTransform: "none", "&:hover": { bgcolor: "#333" } }}
          >
            {saving ? "Saving..." : "Save changes"}
          </Button>
        </Stack>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {saved && <Alert severity="success" sx={{ mb: 2 }}>Preferences saved.</Alert>}

        {loading ? (
          <Box sx={{ py: 8, display: "flex", justifyContent: "center" }}>
            <CircularProgress size={26} />
          </Box>
        ) : (
          <>
            <Card variant="outlined" sx={{ borderRadius: 2, p: 2.5, mb: 3 }}>
              <Typography fontWeight={700} mb={0.75}>Content Language</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Captions, blog posts, and any intentional image text will be generated in this language.
              </Typography>
              <FormControl size="small" sx={{ minWidth: 300 }}>
                <Select value={languageCode} onChange={(event) => setLanguageCode(event.target.value)} sx={{ fontSize: 14 }}>
                  {LANGUAGES.map(([code, label]) => (
                    <MenuItem key={code} value={code} sx={{ fontSize: 14 }}>{label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Card>

            <Card variant="outlined" sx={{ borderRadius: 2, p: 2.5, mb: 3 }}>
              <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2}>
                <Box>
                  <Typography fontWeight={700} mb={0.75}>Schedule Settings</Typography>
                  <Typography variant="body2" color="text.secondary">
                    New calendar content uses this timezone and default review schedule time.
                  </Typography>
                </Box>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <FormControl size="small" sx={{ minWidth: 240 }}>
                    <Select value={timezoneName} onChange={(event) => setTimezoneName(event.target.value)} sx={{ fontSize: 14 }}>
                      {TIMEZONES.map((item) => (
                        <MenuItem key={item} value={item} sx={{ fontSize: 14 }}>{item}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <TextField
                    type="time"
                    size="small"
                    label="Default time"
                    value={defaultScheduleTime}
                    onChange={(event) => setDefaultScheduleTime(event.target.value || "09:00")}
                    inputProps={{ step: 300 }}
                    sx={{ width: 150 }}
                  />
                </Stack>
              </Stack>
            </Card>

            <Card variant="outlined" sx={{ borderRadius: 2, p: 2.5, mb: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
                <Box>
                  <Typography variant="h6" fontWeight={800}>Smart Captions</Typography>
                  <Typography fontWeight={700} sx={{ mt: 2 }}>
                    Smart Captions are {smartCaptions ? "ON" : "OFF"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 620 }}>
                    Tailored captions per platform. Each social media platform gets optimized captions that match its unique style and audience expectations.
                  </Typography>
                </Box>
                <Stack direction="row" alignItems="center" gap={1}>
                  <Button
                    size="small"
                    startIcon={<EditIcon />}
                    onClick={() => navigate("/brand-kit", { state: { tab: "Brand Voice", notice: "Edit channel voice to control Smart Captions." } })}
                    sx={{ textTransform: "none", color: "#111827" }}
                  >
                    Edit
                  </Button>
                  <Switch checked={smartCaptions} onChange={(event) => setSmartCaptions(event.target.checked)} />
                </Stack>
              </Stack>
              <Box sx={{ border: "1px solid #E5E7EB", borderRadius: 2, p: 2, mt: 3 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  With Smart Captions, your posts will automatically adapt to each platform:
                </Typography>
                <Stack spacing={2}>
                  {[
                    ["instagram", "Instagram"],
                    ["facebook", "Facebook"],
                    ["linkedin", "LinkedIn"],
                    ["x", "X/Twitter"],
                  ].map(([key, name]) => {
                    const voice = channelVoices.find((item) => item.platform === key) || {};
                    const copy = [voice.tone, voice.syntax].filter(Boolean).join(" ");
                    return (
                      <Box key={name}>
                        <Typography fontWeight={700}>{name}</Typography>
                        <Typography variant="body2" color="text.secondary">{copy || "Configured in Brand Kit -> Brand Voice."}</Typography>
                      </Box>
                    );
                  })}
                </Stack>
              </Box>
            </Card>

            <Divider sx={{ my: 3 }} />

            <Box sx={{ mb: 2 }}>
              <Typography fontWeight={700}>Content Style</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                This replaces the old Brand Style content-style selector and affects future image prompts.
              </Typography>
            </Box>
            <Grid container spacing={2}>
              {CONTENT_STYLE_OPTIONS.map((option) => (
                <Grid size={{ xs: 12, sm: 6, md: 4 }} key={option.id}>
                  <StyleCard
                    option={option}
                    selected={contentStyle?.id === option.id}
                    onSelect={() => setContentStyle(option)}
                  />
                </Grid>
              ))}
            </Grid>
          </>
        )}
      </Box>
    </Box>
  );
}
