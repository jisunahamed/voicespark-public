import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Box, Stack, Typography, Chip, Button, IconButton, Avatar,
  Card, CardContent, CardMedia, Skeleton, Checkbox, CircularProgress,

} from '@mui/material';
import {
  ChevronLeft, ChevronRight, Add, Autorenew, AutoFixHigh,
  PostAddRounded, ImageOutlined as ImageOutlinedIcon
} from '@mui/icons-material';

import { useNavigate } from 'react-router-dom';
import { Link, useLocation } from "react-router-dom";
import config from '../../config';
import axios from 'axios';
import api from "../login_register/axios_client";

import {

  Dialog,
  DialogContent,
  DialogTitle,
  DialogActions,
  TextField,
  Popover,
  Menu,
  MenuItem,
  Divider,
  ToggleButton,
  ToggleButtonGroup

} from "@mui/material";
import TopBar from '../../TopBar';
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CloseIcon from "@mui/icons-material/Close";


import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import AccessTimeIcon from "@mui/icons-material/AccessTime"
import AppsIcon from "@mui/icons-material/Apps";
import CheckIcon from "@mui/icons-material/Check";
import CalendarViewWeekIcon from "@mui/icons-material/CalendarViewWeek";
import ViewListIcon from "@mui/icons-material/ViewList";
import ViewWeekIcon from "@mui/icons-material/ViewWeek";
import { LocalizationProvider, DateCalendar } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import dayjs from "dayjs";

import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { workspaceStorage } from "../workspace/workSpaceAPi";

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function postWithRetry(url, payload, attempts = 3) {
  let lastError;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await api.post(url, payload);
    } catch (error) {
      lastError = error;
      const status = error?.response?.status;
      if (attempt === attempts - 1 || (status && status < 500 && status !== 408 && status !== 429)) {
        throw error;
      }
      await wait(900 * (attempt + 1));
    }
  }
  throw lastError;
}

function apiErrorMessage(error, fallback = "Request failed. Please try again.") {
  return error?.response?.data?.error
    || error?.response?.data?.detail
    || error?.message
    || fallback;
}

async function waitForGenerationJob(jobId, { timeoutMs = 420000, intervalMs = 2500 } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const response = await api.get(`/nano-banana/generation-job/${jobId}/`);
    const data = response.data || {};
    if (data.is_terminal && data.status === "completed") return data.result || {};
    if (data.is_terminal && data.status === "failed") {
      throw new Error(data.error || data.result?.error || "Generation failed.");
    }
    await wait(intervalMs);
  }
  throw new Error("Generation is still running. The calendar will keep checking in the background.");
}

async function postGeneration(url, payload, options = {}) {
  const response = await postWithRetry(url, payload);
  if (response.data?.job_id) {
    options.onJobStart?.(response.data);
    return waitForGenerationJob(response.data.job_id);
  }
  return response.data || {};
}

const SHORT_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const hasPublishFailure = (meta = {}) => {
  if (meta?.publish_error) return true;
  const statusMap = meta?.platform_publish_status || {};
  return Object.values(statusMap).some((item) => ["failed", "skipped"].includes(item?.status));
};

const statusMeta = (approval, meta = {}) => {
  if (hasPublishFailure(meta)) return { label: "Failed", bg: "#FEE2E2", color: "#991B1B" };
  if (approval === "posted") return { label: "Posted", bg: "#DCFCE7", color: "#166534" };
  if (approval === "approved") return { label: "Scheduled", bg: "#DBEAFE", color: "#1D4ED8" };
  return { label: "Need Review", bg: "#FEF3C7", color: "#92400E" };
};

function GenerationState() {
  return (
    <Box
      sx={{
        width: "100%",
        minHeight: 420,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        px: 2,
      }}
    >
      <Box sx={{ textAlign: "center", maxWidth: 360 }}>
        <Box
          sx={{
            width: 190,
            height: 190,
            mx: "auto",
            mb: 2,
            borderRadius: 3,
            bgcolor: "#F5F3FF",
            border: "1px solid #E9D5FF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <Skeleton variant="rounded" width={150} height={120} sx={{ borderRadius: 2, bgcolor: "#EDE9FE" }} />
          <PostAddRounded sx={{ position: "absolute", fontSize: 48, color: "#7C3AED" }} />
          <CircularProgress size={28} sx={{ position: "absolute", bottom: 18, color: "#7C3AED" }} />
        </Box>
        <Typography fontWeight={700} color="#1F2937">
          Generating your first calendar posts
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Brand-aligned images and captions are being prepared.
        </Typography>
      </Box>
    </Box>
  );
}

// ── Separate Calendar Popover Component ──
function ScheduleCalendarPopover({ anchorEl, onClose, onUpdate, id, imageData, minDate, maxDate }) {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone; // e.g. "Asia/Dhaka"
  const offset = dayjs().format("Z");
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [hour, setHour] = useState(11);
  const [minute, setMinute] = useState(0);
  const [ampm, setAmpm] = useState("AM");

  const open = Boolean(anchorEl);

  function handleUpdate() {
    const h24 = ampm === "PM" ? (hour === 12 ? 12 : hour + 12) : (hour === 12 ? 0 : hour);
    const dateTime = selectedDate
      .hour(h24)
      .minute(minute)
      .second(0);
    onUpdate(dateTime.toISOString()); // returns proper ISO string
    onClose();
  }

  return (
    <Popover
      open={open}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      transformOrigin={{ vertical: "top", horizontal: "left" }}
      PaperProps={{ sx: { borderRadius: 3, width: 320, overflow: "hidden" } }}
    >
      <LocalizationProvider dateAdapter={AdapterDayjs}>
        <DateCalendar
          value={selectedDate}
          onChange={(newVal) => setSelectedDate(newVal)}
          sx={{
            width: "100%",
            "& .MuiPickersDay-root.Mui-selected": {
              bgcolor: "#111",
              "&:hover": { bgcolor: "#333" },
            },
            "& .MuiPickersDay-today": {
              borderColor: "#E5E7EB",
            },
          }}
          minDate={minDate}
          maxDate={maxDate}
        />
      </LocalizationProvider>

      <Divider />

      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", px: 2, py: 1.5, gap: 1 }}>
        <Box>
          <Typography fontSize={10} color="text.disabled" sx={{ textTransform: "uppercase", letterSpacing: 0.5, mb: 0.5 }}>
            Selected date
          </Typography>
          <Typography fontSize={13} fontWeight={600}>
            {SHORT_DAYS[selectedDate.day()]}, {SHORT_MONTHS[selectedDate.month()]} {selectedDate.date()}
          </Typography>
        </Box>
        <Box>
          <Typography fontSize={10} color="text.disabled" sx={{ textTransform: "uppercase", letterSpacing: 0.5, mb: 0.5 }}>
            Time of day
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap" }}>
            <Box
              component="input"
              type="number"
              value={hour}
              min={1} max={12}
              onChange={(e) => setHour(Math.max(1, Math.min(12, +e.target.value)))}
              sx={{ width: 28, border: "none", fontSize: 12, fontWeight: 600, p: 0, outline: "none", textAlign: "center" }}
            />
            <Typography fontSize={12} fontWeight={600}>:</Typography>
            <Box
              component="input"
              type="number"
              value={minute.toString().padStart(2, "0")}
              min={0} max={59}
              onChange={(e) => setMinute(Math.max(0, Math.min(59, +e.target.value)))}
              sx={{ width: 28, border: "none", fontSize: 12, fontWeight: 600, p: 0, outline: "none", textAlign: "center" }}
            />
            <ToggleButtonGroup
              value={ampm}
              exclusive
              onChange={(_, val) => val && setAmpm(val)}
              size="small"
            >
              {["AM", "PM"].map((v) => (
                <ToggleButton
                  key={v}
                  value={v}
                  sx={{
                    fontSize: 10, px: 0.75, py: 0.25, lineHeight: 1.5,
                    "&.Mui-selected": { bgcolor: "#111 !important", color: "#fff" },
                  }}
                >
                  {v}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
            <Typography fontSize={10} color="text.disabled" sx={{ border: "1px solid #E5E7EB", borderRadius: 0.5, px: 0.5 }}>
              GMT{offset}
            </Typography>
          </Box>
        </Box>
      </Box>

      <Box sx={{ px: 1.5, pb: 1.5, display: "flex", flexDirection: "column", gap: 1 }}>
        <Button
          fullWidth
          variant="contained"
          onClick={handleUpdate}
          sx={{
            bgcolor: "#111", color: "#fff", borderRadius: 2,
            textTransform: "none", fontWeight: 600, fontSize: 13,
            "&:hover": { bgcolor: "#333" },
          }}
        >
          Update Date
        </Button>
      </Box>
    </Popover>
  );
}


export function AddTopicMediaModal({ open, onClose, onRegenerate, onLoadingChange, onGenerationStarted }) {
  const [step, setStep] = useState(1);
  const [topic, setTopic] = useState("");
  const [numPosts, setNumPosts] = useState(1);
  const [contentType, setContentType] = useState("social");
  const [dateMode, setDateMode] = useState("specific"); // "specific" | "range"
  const [submitError, setSubmitError] = useState("");
  const [fromAnchorEl, setFromAnchorEl] = useState(null);
  const [toAnchorEl, setToAnchorEl] = useState(null);
  const [specificAnchorEl, setSpecificAnchorEl] = useState(null);
  const [fromDate, setFromDate] = useState(null);
  const [toDate, setToDate] = useState(null);
  const [specificDate, setSpecificDate] = useState(null);
  const [referenceImageUrl, setReferenceImageUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user'));
  const workspaceId = workspaceStorage.getActiveId();
  const toApiDate = (value) => (value ? dayjs(value).toISOString() : "");

  const handleUploadReference = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setSubmitError("");
    try {
      const formData = new FormData();
      formData.append("image", file);
      formData.append("user_id", user.id);
      formData.append("workspace_id", workspaceId);

      const res = await axios.post(
        config.API_SERVER + "auth/user/media-upload/",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );
      setReferenceImageUrl(res.data.image);
    } catch (err) {
      console.error("Upload failed:", err);
      setSubmitError("Failed to upload reference image.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleGenerate = async () => {
    setSubmitError("");
    if (!user?.id || !workspaceId) {
      setSubmitError("Please refresh and select a workspace before generating content.");
      return;
    }
    if (dateMode === "range" && (!fromDate || !toDate)) {
      setSubmitError("Select both start and end dates for a date range.");
      return;
    }
    if (dateMode === "range" && dayjs(toDate).isBefore(dayjs(fromDate))) {
      setSubmitError("End date must be after the start date.");
      return;
    }

    onLoadingChange(true);
    try {
      await postGeneration("/nano-banana/create-new-post/", {
        user_id: user.id,
        from_date: toApiDate(fromDate),
        to_date: toApiDate(toDate),
        specific_date: toApiDate(specificDate),
        type_post: dateMode,
        no_of_post: numPosts,
        topic: topic,
        workspace_id: workspaceId,
        content_type: contentType,
        reference_image_url: referenceImageUrl,
      }, {
        onJobStart: onGenerationStarted,
      });
      onRegenerate();
      onClose();
    } catch (error) {
      const message = apiErrorMessage(error, "Could not generate content. Please try again.");
      setSubmitError(message);
    } finally {
      onLoadingChange(false);
    }
  };
  useEffect(() => {
    if (!open) {
      setStep(1);
      setTopic("");
      setNumPosts(1);
      setContentType("social");
      setDateMode("specific");
      setSubmitError("");
      setFromDate(null);
      setToDate(null);
      setSpecificDate(null);
      setReferenceImageUrl("");
      setUploading(false);
    }
  }, [open]);

  const handleClose = () => {
    setStep(1);
    setTopic("");
    setNumPosts(1);
    setContentType("social");
    setDateMode("specific");
    setSubmitError("");
    setFromDate(null);
    setToDate(null);
    setSpecificDate(null);
    setReferenceImageUrl("");
    setUploading(false);
    onClose();
  };

  const isStep1Valid =
    dateMode === "specific" ? true : !!fromDate && !!toDate && !dayjs(toDate).isBefore(dayjs(fromDate));

  const labelSx = { display: "flex", alignItems: "center", height: 40 };

  // Reusable radio option card
  const RadioCard = ({ value, label, selected: selectedProp, onClick, description }) => {
    const selected = selectedProp ?? dateMode === value;
    return (
      <Box
        onClick={onClick || (() => setDateMode(value))}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          px: 2,
          py: 1.25,
          borderRadius: 2,
          border: "1.5px solid",
          borderColor: selected ? "#111" : "divider",
          bgcolor: selected ? "grey.50" : "transparent",
          cursor: "pointer",
          flex: 1,
          transition: "all 0.15s ease",
        }}
      >
        {/* Circle indicator */}
        <Box
          sx={{
            width: 18,
            height: 18,
            borderRadius: "50%",
            border: "2px solid",
            borderColor: selected ? "#111" : "grey.400",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            transition: "all 0.15s ease",
          }}
        >
          {selected && (
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                bgcolor: "#111",
              }}
            />
          )}
        </Box>
        <Box>
          <Typography variant="body2" fontWeight={selected ? 700 : 500}>
            {label}
          </Typography>
          {description && (
            <Typography variant="caption" color="text.secondary">
              {description}
            </Typography>
          )}
        </Box>
      </Box>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullWidth
      PaperProps={{ sx: { borderRadius: 3, px: 1 } }}
    >
      {/* Header */}
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2, pt: 2, pb: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {step === 2 && (
            <IconButton size="small" onClick={() => setStep(1)} sx={{ color: "text.primary" }}>
              <ArrowBackIcon fontSize="small" />
            </IconButton>
          )}
          <Typography variant="subtitle1" fontWeight={600}>
            {step === 1 ? "Create Content" : "Generate Content"}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Step {step} of 2
          </Typography>
          <IconButton size="small" onClick={handleClose} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
      </DialogTitle>

      <Box sx={{ borderTop: "1px solid", borderColor: "divider", mx: 2 }} />

      <DialogContent sx={{ px: 3, pt: 3, pb: 4 }}>

        {/* ── Step 1 ── */}
        {step === 1 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>

            <Box>
              <Typography variant="body2" fontWeight={700} sx={{ mb: 1 }}>
                What do you want to create?
              </Typography>
              <Box sx={{ display: "flex", gap: 1.5 }}>
                <RadioCard
                  value="social"
                  label="Post"
                  description="Create social media content"
                  selected={contentType === "social"}
                  onClick={() => setContentType("social")}
                />
                <RadioCard
                  value="blog"
                  label="Blog"
                  description="Create a long-form calendar item"
                  selected={contentType === "blog"}
                  onClick={() => setContentType("blog")}
                />
              </Box>
            </Box>

            <Box>
              <Typography variant="body2" fontWeight={700} sx={{ mb: 1 }}>
                Schedule
              </Typography>
              <Box sx={{ display: "flex", gap: 1.5 }}>
                <RadioCard value="specific" label="Specific Date" />
                <RadioCard value="range" label="Date Range" />
              </Box>
            </Box>

            {/* Specific Date — revealed when selected */}
            {dateMode === "specific" && (
              <Box sx={{ display: "flex", gap: 4 }}>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 110, pt: 0.5 }}>
                  <Box sx={labelSx}>
                    <Typography variant="body2" fontWeight={600}>Date</Typography>
                  </Box>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    startIcon={<CalendarTodayIcon fontSize="small" />}
                    onClick={(e) => setSpecificAnchorEl(e.currentTarget)}
                    sx={{
                      justifyContent: "flex-start",
                      borderRadius: 1.5,
                      textTransform: "none",
                      color: specificDate ? "text.primary" : "text.secondary",
                      borderColor: "divider",
                      height: 40,
                    }}
                  >
                    {specificDate
                      ? dayjs(specificDate).format("ddd, MMM D · h:mmA")
                      : "Select date & time"}
                  </Button>
                  <ScheduleCalendarPopover
                    anchorEl={specificAnchorEl}
                    onClose={() => setSpecificAnchorEl(null)}
                    onUpdate={(val) => { setSpecificDate(val); setSpecificAnchorEl(null); }}
                  />
                </Box>
              </Box>
            )}

            {/* Date Range — revealed when selected */}
            {dateMode === "range" && (
              <Box sx={{ display: "flex", gap: 4 }}>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 110, pt: 0.5 }}>
                  <Box sx={labelSx}>
                    <Typography variant="body2" fontWeight={600}>From</Typography>
                  </Box>
                  <Box sx={labelSx}>
                    <Typography variant="body2" fontWeight={600}>To</Typography>
                  </Box>
                </Box>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 3, flex: 1 }}>
                  {/* From */}
                  <Box>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<CalendarTodayIcon fontSize="small" />}
                      onClick={(e) => setFromAnchorEl(e.currentTarget)}
                      sx={{
                        justifyContent: "flex-start",
                        borderRadius: 1.5,
                        textTransform: "none",
                        color: fromDate ? "text.primary" : "text.secondary",
                        borderColor: "divider",
                        height: 40,
                      }}
                    >
                      {fromDate
                        ? dayjs(fromDate).format("ddd, MMM D · h:mmA")
                        : "Select start date & time"}
                    </Button>
                    <ScheduleCalendarPopover
                      anchorEl={fromAnchorEl}
                      onClose={() => setFromAnchorEl(null)}
                      onUpdate={(val) => { setFromDate(val); setFromAnchorEl(null); }}
                    />
                  </Box>
                  {/* To */}
                  <Box>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<CalendarTodayIcon fontSize="small" />}
                      onClick={(e) => setToAnchorEl(e.currentTarget)}
                      sx={{
                        justifyContent: "flex-start",
                        borderRadius: 1.5,
                        textTransform: "none",
                        color: toDate ? "text.primary" : "text.secondary",
                        borderColor: "divider",
                        height: 40,
                      }}
                    >
                      {toDate
                        ? dayjs(toDate).format("ddd, MMM D · h:mmA")
                        : "Select end date & time"}
                    </Button>
                    <ScheduleCalendarPopover
                      anchorEl={toAnchorEl}
                      onClose={() => setToAnchorEl(null)}
                      onUpdate={(val) => { setToDate(val); setToAnchorEl(null); }}
                      minDate={fromDate ? dayjs(fromDate) : undefined}
                      maxDate={fromDate ? dayjs(fromDate).add(3, "day") : undefined}
                    />
                  </Box>
                </Box>
              </Box>
            )}

            {dateMode === "specific" && (
              <Box sx={{ display: "flex", gap: 4 }}>
                <Box sx={{ display: "flex", flexDirection: "column", minWidth: 110, pt: 0.5 }}>
                  <Box sx={labelSx}>
                    <Typography variant="body2" fontWeight={600}>Quantity</Typography>
                  </Box>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <TextField
                    fullWidth
                    type="number"
                    size="small"
                    value={numPosts}
                    onChange={(e) => setNumPosts(Math.max(1, parseInt(e.target.value) || 1))}
                    inputProps={{ min: 1 }}
                    sx={{
                      "& .MuiOutlinedInput-root": { borderRadius: 1.5, fontSize: "0.875rem" },
                    }}
                  />
                </Box>
              </Box>
            )}

          </Box>
        )}

        {/* ── Step 2 ── */}
        {step === 2 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Box
              sx={{
                p: 2, borderRadius: 2,
                border: "1px solid", borderColor: "divider", bgcolor: "grey.50",
              }}
            >
              <Typography variant="caption" color="text.secondary">Summary</Typography>
              <Typography variant="body2" mt={0.5}>
                {dateMode === "specific"
                  ? specificDate
                    ? dayjs(specificDate).format("ddd, MMM D · h:mmA")
                    : "No date selected"
                  : fromDate && toDate
                    ? `${dayjs(fromDate).format("MMM D")} → ${dayjs(toDate).format("MMM D")}`
                    : "No dates selected"}
                {" · "}{numPosts} {contentType === "blog" ? "blog" : "post"}{numPosts > 1 ? "s" : ""}
              </Typography>
            </Box>
            <Typography variant="body2" fontWeight={600}>
              Describe what to generate
            </Typography>
            <TextField
              fullWidth
              multiline
              minRows={4}
              variant="outlined"
              placeholder="Briefly describe a topic to focus the content on..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              size="small"
              sx={{
                "& .MuiOutlinedInput-root": { borderRadius: 1.5, fontSize: "0.875rem" },
              }}
            />
            
            <Box>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                Optional: Reference Image
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {referenceImageUrl ? (
                   <Box sx={{ position: 'relative' }}>
                      <Box component="img" src={referenceImageUrl} sx={{ width: 80, height: 80, borderRadius: 2, objectFit: 'cover', border: '1px solid #ddd' }} />
                      <IconButton 
                        size="small" 
                        onClick={() => setReferenceImageUrl("")}
                        sx={{ position: 'absolute', top: -8, right: -8, bgcolor: 'white', border: '1px solid #ddd', '&:hover': { bgcolor: '#f5f5f5' }, width: 20, height: 20 }}
                      >
                        <CloseIcon sx={{ fontSize: 14 }} />
                      </IconButton>
                   </Box>
                ) : (
                  <Button
                    variant="outlined"
                    component="label"
                    disabled={uploading}
                    startIcon={uploading ? <CircularProgress size={16} /> : <ImageOutlinedIcon />}
                    sx={{ textTransform: 'none', borderRadius: 2, borderColor: 'divider', color: 'text.primary' }}
                  >
                    {uploading ? 'Uploading...' : 'Upload Reference'}
                    <input type="file" hidden accept="image/*" onChange={handleUploadReference} />
                  </Button>
                )}
                <Typography variant="caption" color="text.secondary" sx={{ maxWidth: 200 }}>
                  Use this to provide a specific visual anchor for this post.
                </Typography>
              </Box>
            </Box>
          </Box>
        )}

      </DialogContent>

      {submitError && (
        <Box sx={{ mx: 3, mb: 2, p: 1.5, borderRadius: 2, bgcolor: "#FEF2F2", border: "1px solid #FECACA" }}>
          <Typography variant="body2" color="#B91C1C">
            {submitError}
          </Typography>
        </Box>
      )}

      <DialogActions sx={{ px: 3, pb: 3 }}>
        {step === 1 ? (
          <Button
            variant="contained"
            disableElevation
            fullWidth
            disabled={!isStep1Valid}
            onClick={() => setStep(2)}
            endIcon={<ArrowForwardIcon />}
          >
            Next
          </Button>
        ) : (
          <Button
            variant="contained"
            disableElevation
            fullWidth
            // disabled={!topic.trim()}
            onClick={handleGenerate}
          >
            Generate
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

const PLATFORM_COLORS = {
  X: { bg: '#000', label: 'X' },
  IG: { bg: 'linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)', label: 'IG' },
  FB: { bg: '#1877f2', label: 'f' },
  LI: { bg: '#0a66c2', label: 'in' },
};

const PLATFORM_LABELS = {
  twitter: "X",
  x: "X",
  instagram: "IG",
  facebook: "FB",
  linkedin: "LI",
};

const contentTypeLabel = (type) => {
  if (type === "blog") return "Blog Post";
  if (type === "email") return "Email";
  return "Post";
};

const normalizePostPlatforms = (item) => {
  const contentType = item.content_type || item.meta?.content_type || "social";
  if (contentType === "blog" || contentType === "email") return [];
  const platforms = Array.isArray(item.platforms) ? item.platforms : [];
  const normalized = platforms.map((platform) => PLATFORM_LABELS[String(platform).toLowerCase()]).filter(Boolean);
  return normalized.length ? normalized : ["X", "IG", "FB", "LI"];
};

function PlatformBadges({ platforms }) {
  if (!platforms?.length) return null;
  return (
    <Stack direction="row" spacing={0.3}>
      {platforms.map(p => (
        <Box key={p} sx={{
          width: 18, height: 18, borderRadius: '50%',
          background: PLATFORM_COLORS[p]?.bg || '#999',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 9, color: '#fff', fontWeight: 700, flexShrink: 0,
        }}>
          {PLATFORM_COLORS[p]?.label}
        </Box>
      ))}
    </Stack>
  );
}

function TruncatedText({ text, limit = 120, variant = "caption", color = "text.secondary", sx = {} }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = text?.length > limit;

  return (
    <Typography variant={variant} color={color} sx={{ lineHeight: 1.5, ...sx }}>
      {isLong && !expanded ? text.slice(0, limit) + "..." : text}
      {isLong && (
        <Typography
          component="span"
          variant={variant}
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          sx={{ color: "#7c3aed", cursor: "pointer", ml: 0.3, fontWeight: 600 }}
        >
          {expanded ? " see less" : " see more"}
        </Typography>
      )}
    </Typography>
  );
}

function PostCard({ post, selectedPosts, setSelectedPosts, hasConnectedPlatform }) {
  const navigate = useNavigate();
  const [hovered, setHovered] = useState(false);
  const [checked, setChecked] = useState(false);

  const isChecked = selectedPosts.includes(post.path);
  useEffect(() => {
    if (!isChecked) setChecked(false);
  }, [isChecked]);


  const handleToggle = (e) => {
    e.stopPropagation();

    if (isChecked) {
      setChecked(e.target.checked);
      setSelectedPosts(prev => prev.filter(p => p !== post.path));
    } else {
      setChecked(e.target.checked);
      setSelectedPosts(prev => [...prev, post.path]);
    }
  };
  const [approving, setApproving] = useState(false);
  const id = post.path.split("/").pop();
  const [approval, setApproval] = useState(post.approval);
  const currentStatus = statusMeta(approval, post.meta);
  const requiresConnectedPlatform = post.contentType === "social";

  const handleApproval = async () => {
    if (requiresConnectedPlatform && !hasConnectedPlatform) return;
    setApproving(true);
    // await axios.post(...);
    const user = JSON.parse(localStorage.getItem('user'));
    const response = await postWithRetry('/nano-banana/change-approval/', {
      user_id: user.id,
      nano_banana_id: id,


    })
    if (response.status === 200) {
      setApproval('approved')
    }
    // console.log(post.path);
    setApproving(false);
  };
  return (
    <Box
      sx={{ mb: 2, position: "relative" }}
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData("text/plain", post.id);
        event.dataTransfer.effectAllowed = "move";
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={(e) => {
        // Don't hide if moving to a child (e.g. the checkbox)
        if (!(e.relatedTarget instanceof Node) || !e.currentTarget.contains(e.relatedTarget)) {
          setHovered(false);
        }
      }
      }
    >
      {(hovered || checked) && (
        <Checkbox
          checked={checked}
          onChange={handleToggle}
          // onChange={(e) => {
          //   // e.stopPropagation();
          //   // setChecked(e.target.checked);
          //   handleToggle();
          // }}
          onClick={(e) => { e.stopPropagation(); }}
          size="small"
          sx={{
            position: "absolute",
            top: 6,
            left: 6,
            zIndex: 10,
            backgroundColor: "white",
            borderRadius: 1,
            p: 0.2,
            "&:hover": { backgroundColor: "white" },
          }}
        />
      )}
      <Card
        onClick={() => navigate(post.path)}
        sx={{
          borderRadius: 2,
          overflow: "hidden",
          boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
          border: "1.5px solid #d600ff",
          filter: (hovered || isChecked) ? "brightness(0.92) grayscale(20%)" : "none", // ✅ stays grey when checked
          "&:hover": {
            boxShadow: "0 4px 16px rgba(124,58,237,0.10)",
            filter: "brightness(0.92) grayscale(20%)",
          },
          transition: "box-shadow .2s, filter .2s",
          cursor: "pointer",
          opacity: hovered ? 0.96 : 1,
        }}
      >
        {/* Card Header */}
        <Box sx={{ px: 1.5, pt: 1.5, pb: 1, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <PlatformBadges platforms={post.platforms} />
            <Chip
              label={post.type}
              size="small"
              sx={{ fontSize: 10, height: 18, background: "#f3f4f6", color: "#6b7280", fontWeight: 500 }}
            />
            <Chip
              label={currentStatus.label}
              size="small"
              sx={{ fontSize: 10, height: 18, background: currentStatus.bg, color: currentStatus.color, fontWeight: 700 }}
            />
          </Stack>
          <Typography variant="caption" color="text.secondary" fontWeight={500}>
            {post.time}
          </Typography>


        </Box>
        {/* Title ABOVE the card */}
        {post.title && (
          <Typography
            variant="subtitle1"
            fontWeight={700}
            color="#1e1b4b"
            sx={{ mb: 0.75, px: 0.5, fontSize: 15, lineHeight: 1.4 }}
          >
            <TruncatedText text={post.title} limit={80} variant="h6" color="inherit" sx={{ fontWeight: 700 }} />
          </Typography>
        )}
        {/* Image Post */}
        {post.image && (
          <Box sx={{ position: "relative" }}>
            <CardMedia
              component="img"
              image={post.image}
              alt={post.title}
              sx={{ width: "100%", objectFit: "cover", aspectRatio: "4/5" }}
            />
            <Box sx={{
              position: "absolute", bottom: 0, left: 0, right: 0,
              background: "linear-gradient(transparent, rgba(0,0,0,0.85))",
              p: 1.5,
            }}>
              {post.subtitle && (
                <TruncatedText text={post.subtitle} limit={80} variant="caption" color="rgba(255,255,255,0.8)" sx={{ mt: 0.5, display: "block" }} />
              )}
              {post.author && (
                <Typography variant="caption" color="rgba(255,255,255,0.6)" sx={{ mt: 0.3, display: "block", fontSize: 10 }}>
                  {post.author}
                </Typography>
              )}
            </Box>

            {approval === 'not_approved' && (!requiresConnectedPlatform || hasConnectedPlatform) && (
              <Box
                onClick={(e) => e.stopPropagation()}
                sx={{ position: "absolute", bottom: 8, left: 8, display: "flex", alignItems: "center", gap: 0.5 }}
              >
                <Button
                  size="small"
                  variant="contained"
                  onClick={handleApproval}
                  disabled={approving}
                  sx={{
                    bgcolor: "rgba(0,0,0,0.55)", color: "#f59e0b",
                    textTransform: "none", fontSize: 11, fontWeight: 600,
                    px: 1, py: 0.25, minWidth: 0, borderRadius: 1.5,
                    backdropFilter: "blur(4px)",
                    "&:hover": { bgcolor: "rgba(0,0,0,0.75)" },
                    "&.Mui-disabled": { bgcolor: "rgba(0,0,0,0.4)", color: "#f59e0b" },
                  }}
                >
                  Approve
                </Button>
                {approving && <CircularProgress size={12} sx={{ color: "#f59e0b" }} />}
              </Box>
            )}


          </Box>
        )}

        {/* Excerpt */}
        {/* {post.excerpt && (
          <Box sx={{ px: 1.5, pb: 1 }}>
            <TruncatedText text={post.excerpt} limit={120} />
          </Box>
        )} */}

        {/* Connect CTA */}
        {/* {!post.connected && (
          <Box sx={{ px: 1.5, pb: 1.5 }}>
            <Button
              size="small"
              variant="text"
              onClick={(e) => e.stopPropagation()}
              sx={{ color: "#f59e0b", textTransform: "none", fontSize: 12, fontWeight: 600, p: 0, minWidth: 0, "&:hover": { background: "transparent", textDecoration: "underline" } }}
            >
              Connect
            </Button>
          </Box>
        )} */}

      </Card>
      {/* {post.approval === 'not_approved' && (
        <Box sx={{ px: 1.5, pb: 1.5, display: "flex", alignItems: "center", gap: 1 }}>
          <Button
            size="small"
            variant="text"
            onClick={handleApproval}
            disabled={approving}
            sx={{ color: "#f59e0b", textTransform: "none", fontSize: 12, fontWeight: 600, p: 0, minWidth: 0, "&:hover": { background: "transparent", textDecoration: "underline" } }}
          >
            Approve
          </Button>
          {approving && <CircularProgress size={12} sx={{ color: "#f59e0b" }} />}
        </Box>
      )} */}
    </Box>
  );
}

function DayColumn({ dateLabel, dateKey, posts, selectedPosts, setSelectedPosts, hasConnectedPlatform, minWidth = 0, onDropPost }) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    const postId = event.dataTransfer.getData("text/plain");
    if (postId) onDropPost(postId, dateKey);
  };

  return (
    <Box
      onDragOver={(event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      sx={{
        flex: "0 0 270px",
        minWidth: minWidth || 270,
        maxWidth: 300,
        borderRadius: 2,
        outline: dragOver ? "2px dashed #7c3aed" : "2px solid transparent",
        outlineOffset: 4,
        transition: "outline-color .15s, background .15s",
        background: dragOver ? "rgba(124,58,237,0.04)" : "transparent",
      }}
    >
      {/* Day Header */}
      <Typography variant="caption" color="text.secondary" fontWeight={600}
        sx={{ display: 'block', textAlign: 'center', mb: 2, letterSpacing: 0.3 }}>
        {dateLabel}
      </Typography>

      {/* Posts */}
      {posts && posts.map(post => (
        <PostCard key={post.id} post={post}
          selectedPosts={selectedPosts}
          setSelectedPosts={setSelectedPosts}
          hasConnectedPlatform={hasConnectedPlatform}
        />
      ))}

      {/* Empty state */}
      {(!posts || posts.length === 0) && (
        <Box sx={{
          border: '2px dashed #e5e7eb', borderRadius: 2, p: 3,
          textAlign: 'center', cursor: 'pointer',
          '&:hover': { borderColor: '#7c3aed', background: '#faf5ff' },
          transition: 'all .2s',
        }}>
          <Typography variant="caption" color="text.secondary">No posts scheduled</Typography>
        </Box>
      )}
    </Box>
  );
}

function ListPostRow({ post, selectedPosts, setSelectedPosts }) {
  const navigate = useNavigate();
  const isChecked = selectedPosts.includes(post.path);
  const currentStatus = statusMeta(post.approval, post.meta);

  const handleToggle = (event) => {
    event.stopPropagation();
    setSelectedPosts((prev) => (
      event.target.checked
        ? [...prev, post.path]
        : prev.filter((path) => path !== post.path)
    ));
  };

  return (
    <Card
      onClick={() => navigate(post.path)}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        p: 1,
        borderRadius: 2,
        border: "1px solid #f0eeff",
        boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
        cursor: "pointer",
        "&:hover": { boxShadow: "0 4px 16px rgba(124,58,237,0.10)" },
      }}
    >
      <Checkbox
        checked={isChecked}
        onChange={handleToggle}
        onClick={(event) => event.stopPropagation()}
        size="small"
        sx={{ p: 0.5 }}
      />
      {post.image && (
        <CardMedia
          component="img"
          image={post.image}
          alt={post.title}
          sx={{ width: 72, height: 72, borderRadius: 1.5, objectFit: "cover", flexShrink: 0 }}
        />
      )}
      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
          <PlatformBadges platforms={post.platforms} />
          <Chip
            label={post.type}
            size="small"
            sx={{ fontSize: 10, height: 18, background: "#f3f4f6", color: "#6b7280", fontWeight: 500 }}
          />
          <Chip
            label={currentStatus.label}
            size="small"
            sx={{ fontSize: 10, height: 18, background: currentStatus.bg, color: currentStatus.color, fontWeight: 700 }}
          />
          <Typography variant="caption" color="text.secondary">{post.time}</Typography>
        </Stack>
        <Typography noWrap fontWeight={700} color="#1e1b4b" fontSize={14}>
          {post.title}
        </Typography>
      </Box>
    </Card>
  );
}

function NavButtons({ rangeLabel }) {
  const todayLabel = dayjs().format("MMM D, YYYY");
  return (
    <Stack direction="row" alignItems="center" spacing={1}>
      <Button
        size="small"
        variant="outlined"
        sx={{
        borderColor: '#e5e7eb', color: '#374151', textTransform: 'none',
        borderRadius: 1.5, fontWeight: 500, fontSize: 13,
      }}>
        Today
      </Button>
      <Typography variant="body2" fontWeight={600} color="#374151" sx={{ ml: 1 }}>
        {todayLabel}
      </Typography>
      {rangeLabel && (
        <Typography variant="body2" fontWeight={600} color="#6b7280" sx={{ ml: 1 }}>
          {rangeLabel}
        </Typography>
      )}
    </Stack>
  );
}

function ActionButtons({ open, setOpen, selectedPosts, onRegenerate, onGenerationStarted }) {
  const navigate = useNavigate();
  const [regenerating, setRegenerating] = useState(false);
  const [loading, setLoading] = useState(false);
  const postIds = selectedPosts.map(p => p.replace('/blaze-editor/', ''));
  const user = JSON.parse(localStorage.getItem('user'));
  const workspaceId = workspaceStorage.getActiveId();
  const handleRegenerate = async () => {

    try {
      setRegenerating(true);
      await postGeneration("/nano-banana/regenerate-image/", {
        user_id: user.id,
        nano_banana_ids: postIds,
        workspace_id: workspaceId,
        target_platform: "multi-platform",
        image_size: "1:1",
      });

    } catch (err) {
      console.error("Failed to regenerate:", err);
      alert(apiErrorMessage(err, "Regenerate failed. Please try again."));
    } finally {
      setRegenerating(false);
      onRegenerate();

    }
  };
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Button
        startIcon={loading ? <CircularProgress size={14} sx={{ color: '#374151' }} /> : <Add fontSize="small" />}
        size="small"
        sx={{
          color: '#374151', textTransform: 'none', fontWeight: 500, fontSize: 13,
          '&:hover': { background: '#f3f4f6' },
        }}
        onClick={() => setOpen(true)}
      >
        {loading ? "Generating..." : "Create"}
      </Button>
      <AddTopicMediaModal open={open} onClose={() => setOpen(false)} onRegenerate={onRegenerate} onLoadingChange={setLoading} onGenerationStarted={onGenerationStarted} />
      {selectedPosts.length > 0 && (
        <Button
          onClick={handleRegenerate}
          disabled={regenerating}
          startIcon={
            regenerating
              ? <CircularProgress size={14} thickness={5} sx={{ color: '#374151' }} />
              : <Autorenew fontSize="small" />
          }
          size="small"
          sx={{
            color: '#374151', textTransform: 'none', fontWeight: 500, fontSize: 13,
            '&:hover': { background: '#f3f4f6' },
          }}
        >
          {regenerating ? 'Regenerating...' : `Regenerate (${selectedPosts.length})`}
        </Button>
      )}
      {/* <Button startIcon={<Autorenew fontSize="small" />} size="small" sx={{
        color: '#374151', textTransform: 'none', fontWeight: 500, fontSize: 13,
        '&:hover': { background: '#f3f4f6' },
      }}>
        Regenerate
      </Button> */}
      <Button
        startIcon={<AutoFixHigh fontSize="small" />}
        size="small"
        onClick={() => navigate("/brand-kit", { state: { notice: "improve-content" } })}
        sx={{
          color: '#374151', textTransform: 'none', fontWeight: 500, fontSize: 13,
          '&:hover': { background: '#f3f4f6' },
        }}
      >
        Improve
      </Button>
    </Stack>
  );
}

const VIEW_OPTIONS = [
  { value: "list", label: "List View", icon: <ViewListIcon sx={{ fontSize: 18 }} /> },
  { value: "week", label: "Week View", icon: <CalendarViewWeekIcon sx={{ fontSize: 18 }} /> },
  { value: "five-day", label: "5 Day View", icon: <ViewWeekIcon sx={{ fontSize: 18 }} /> },
  { value: "compact", label: "Compact View", icon: <AppsIcon sx={{ fontSize: 18 }} /> },
];

function ViewToggleButtons({ selectedView, setSelectedView }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const activeOption = VIEW_OPTIONS.find((option) => option.value === selectedView) ?? VIEW_OPTIONS[3];

  const handleSelect = (value) => {
    setSelectedView(value);
    setAnchorEl(null);
  };

  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Button
        size="small"
        variant="outlined"
        onClick={(event) => setAnchorEl(event.currentTarget)}
        sx={{
        borderColor: '#e5e7eb', color: '#374151', textTransform: 'none',
        borderRadius: 1.5, fontWeight: 500, fontSize: 13,
      }}>
        {activeOption.label.replace(" View", "")} ▾
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        PaperProps={{ sx: { width: 178, borderRadius: 2, mt: 0.75, boxShadow: "0 12px 32px rgba(15,23,42,0.14)" } }}
      >
        {VIEW_OPTIONS.map((option) => (
          <MenuItem
            key={option.value}
            onClick={() => handleSelect(option.value)}
            selected={selectedView === option.value}
            sx={{ fontSize: 14, gap: 1.25, minHeight: 38 }}
          >
            {option.icon}
            <Typography fontSize={14} fontWeight={selectedView === option.value ? 700 : 400} sx={{ flex: 1 }}>
              {option.label}
            </Typography>
            {selectedView === option.value && <CheckIcon sx={{ fontSize: 17, color: "#111827" }} />}
          </MenuItem>
        ))}
      </Menu>
    </Stack>
  );
}

export default function CalendarPage() {
  const navigate = useNavigate();

  // Generate days based on offset (showing 2 days like screenshot)
  // const baseDates = ['Mar 28', 'Mar 29'];
  // const days = baseDates; // simplified; in real app, compute from weekOffset

  // const dateRangeLabel = 'Mar 28 – 29';
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedPosts, setSelectedPosts] = useState([]);
  // const [imageData, setImageData] = useState(null);
  const [imageData, setImageData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generationNotice, setGenerationNotice] = useState("");
  const [generationError, setGenerationError] = useState("");
  const [hasConnectedPlatform, setHasConnectedPlatform] = useState(false);
  const hasFetched = useRef(false);
  const user = JSON.parse(localStorage.getItem('user'));
  const location = useLocation();
  const workspaceId = workspaceStorage.getActiveId();
  useEffect(() => {
    const fetchConnections = async () => {
      try {
        if (!user?.id || !workspaceId) return;
        const { data } = await api.post("/auth/user/social-insights/", {
          user_id: user.id,
          workspace_id: workspaceId,
        });
        const platforms = Object.values(data.data || {});
        setHasConnectedPlatform(platforms.some((platform) => platform?.connected));
      } catch (error) {
        console.error("Failed to fetch connected platforms:", error);
        setHasConnectedPlatform(false);
      }
    };
    fetchConnections();
  }, [user?.id, workspaceId]);
  // useEffect(() => {
  //   if (hasFetched.current) return;
  //   hasFetched.current = true;

  //   const fetchImage = async () => {
  //     const response = await axios.post(config.API_SERVER + "nano-banana/get-generated-image/", {
  //       user_id: user.id,
  //     });
  //     setImageData(response.data.data);  // ← .data.data because axios wraps in .data and Django returns {"data": {...}}
  //   };

  //   fetchImage();
  // }, []);
  useEffect(() => {
    // if (hasFetched.current) return;
    // hasFetched.current = true;
    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 60;

    const fetchImage = async () => {
      try {
        const response = await postWithRetry("/nano-banana/get-generated-image/", {
          user_id: user.id,
          workspace_id:workspaceId,
        });
        // setImageData(response.data.data ?? []);

        const data = response.data.data ?? [];
        const activeJobs = response.data.active_generation_jobs || [];
        const failedJobs = response.data.recent_failed_generation_jobs || [];

        if (failedJobs.length && !activeJobs.length) {
          setGenerationError(failedJobs[0].error || "Generation failed. Please try again.");
        } else {
          setGenerationError("");
        }

        if (data.length > 0 && !cancelled) {
          setImageData(data);
        }
        if (activeJobs.length) {
          attempts += 1;
          if (!cancelled) {
            setGenerationNotice("Generating content. Calendar will update automatically when it finishes.");
            setLoading(data.length === 0);
          }
          if (!cancelled && attempts < maxAttempts) {
            setTimeout(fetchImage, 5000);
          } else if (!cancelled) {
            setGenerationNotice("");
            setGenerationError("Generation is taking longer than expected. Try again or refresh in a moment.");
            setLoading(false);
          }
        } else if (data.length === 0) {
          attempts += 1;
          if (!cancelled && attempts < maxAttempts) {
            setTimeout(fetchImage, 5000);
          } else if (!cancelled) {
            setImageData((prev) => (Array.isArray(prev) && prev.length ? prev : []));
            setGenerationNotice("");
            setLoading(false);
          }
        } else {
          if (!cancelled) {
            setGenerationNotice("");
            setLoading(false);
            setImageData(data);
          }
        }



      } catch (err) {
        console.error("Failed to fetch images:", err);
        attempts += 1;
        if (!cancelled && attempts < maxAttempts) {
          setTimeout(fetchImage, 5000);
        } else if (!cancelled) {
          setImageData((prev) => (Array.isArray(prev) && prev.length ? prev : []));
          setGenerationNotice("");
          setGenerationError(apiErrorMessage(err, "Could not refresh generated posts."));
          setLoading(false);
        }
      }
      // finally {
      //   setLoading(false);
      // }
    };
    setLoading(true);
    setGenerationNotice("");
    setGenerationError("");
    setSelectedPosts([]);
    fetchImage();

    return () => {
      cancelled = true;
    };
  }, [reloadKey, user?.id, workspaceId]);


  const [open, setOpen] = useState(false);

  // const POSTS = imageData?.reduce((acc, item, index) => {
  //   const rawDate = new Date(item.scheduled_at);
  //   const date = rawDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); // "Mar 28"

  //   if (!acc[date]) acc[date] = [];

  //   acc[date].push({
  //     id: index + 1,
  //     type: 'Post',
  //     time: '3:00pm',
  //     platforms: ['X', 'IG', 'FB', 'LI'],
  //     image: item.imageurl,
  //     title: item.title,
  //     subtitle: '',
  //     author: '',
  //     excerpt: '',
  //     connected: false,
  //     path: `/blaze-editor/${item.nano_banana_id}`,
  //   });

  //   return acc;
  // }, {});
  const POSTS = useMemo(() => {
    if (!imageData.length) return {};
    return imageData.reduce((acc, item, index) => {
      const scheduledAt = dayjs(item.scheduled_at);
      const safeDate = scheduledAt.isValid() ? scheduledAt : dayjs();
      const date = safeDate.format("YYYY-MM-DD");
      if (!acc[date]) acc[date] = [];
      const contentType = item.content_type || item.meta?.content_type || "social";
      const contentTitle = item.content_title || item.meta?.title || item.title;
      acc[date].push({
        id: item.nano_banana_id ?? index + 1,
        type: contentTypeLabel(contentType),
        time: safeDate.format('h:mma'),
        platforms: normalizePostPlatforms(item),
        contentType,
        image: item.imageurl,
        title: contentTitle || item.title,
        subtitle: '',
        author: '',
        excerpt: item.meta?.excerpt || item.meta?.preheader || '',
        meta: item.meta || {},
        approval: item.approval,
        scheduledAt: safeDate.toISOString(),
        connected: false,
        path: `/blaze-editor/${item.nano_banana_id}`,
      });
      return acc;
    }, {});
  }, [imageData]);
  const visibleDays = useMemo(() => {
    const today = dayjs().startOf("day");
    const dates = imageData
      .map((item) => dayjs(item.scheduled_at).startOf("day"))
      .filter((date) => date.isValid());
    const earliest = dates.reduce((current, date) => (date.isBefore(current) ? date : current), today);
    const latestBase = today.add(6, "day");
    const latest = dates.reduce((current, date) => (date.isAfter(current) ? date : current), latestBase);
    const totalDays = Math.min(Math.max(latest.diff(earliest, "day") + 1, 7), 31);
    return Array.from({ length: totalDays }, (_, index) => earliest.add(index, "day"));
  }, [imageData]);
  const rangeLabel = `${visibleDays[0].format("MMM D")} - ${visibleDays[visibleDays.length - 1].format("MMM D, YYYY")}`;
  const handleDropPost = async (postId, targetDateKey) => {
    const currentItem = imageData.find((item) => String(item.nano_banana_id) === String(postId));
    if (!currentItem) return;

    const currentDate = dayjs(currentItem.scheduled_at);
    const targetDate = dayjs(targetDateKey);
    const nextDate = targetDate
      .hour(currentDate.isValid() ? currentDate.hour() : 9)
      .minute(currentDate.isValid() ? currentDate.minute() : 0)
      .second(0)
      .millisecond(0);
    const previousData = imageData;

    setImageData((prev) => prev.map((item) => (
      String(item.nano_banana_id) === String(postId)
        ? { ...item, scheduled_at: nextDate.toISOString() }
        : item
    )));

    try {
      await postWithRetry("/nano-banana/change-schedule-time/", {
        user_id: user.id,
        nano_banana_id: postId,
        schedule_time_iso: nextDate.toISOString(),
        workspace_id: workspaceId,
      });
    } catch (error) {
      console.error("Failed to move calendar post:", error);
      setImageData(previousData);
    }
  };
  const allPosts = visibleDays.flatMap((day) => (
    (POSTS?.[day.format("YYYY-MM-DD")] ?? []).map((post) => ({ ...post, dateLabel: day.format("MMM D ddd") }))
  ));

  return (
    <Box>
      <TopBar
        title="Calendar"
        leftContent={
          <NavButtons rangeLabel={rangeLabel} />
        }
        centerContent={
          <ActionButtons
            open={open}
            setOpen={setOpen}
            selectedPosts={selectedPosts}
            onRegenerate={() => setReloadKey(k => k + 1)}
            onGenerationStarted={() => setReloadKey(k => k + 1)}
          />
        }
        rightContent={null}
      />
      <Box sx={{ height: '100%' }}>
        {(generationNotice || generationError) && (
          <Box
            sx={{
              px: 2,
              py: 1.25,
              bgcolor: generationError ? "#FEF2F2" : "#EEF2FF",
              borderBottom: "1px solid",
              borderColor: generationError ? "#FECACA" : "#C7D2FE",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 2,
            }}
          >
            <Typography sx={{ fontSize: 14, color: generationError ? "#991B1B" : "#3730A3" }}>
              {generationError || generationNotice}
            </Typography>
            {generationError && (
              <Button
                size="small"
                onClick={() => {
                  setGenerationError("");
                  setOpen(true);
                }}
                sx={{ textTransform: "none", fontWeight: 800, color: "#111" }}
              >
                Retry
              </Button>
            )}
          </Box>
        )}
        {!hasConnectedPlatform && (
          <Box
            sx={{
              px: 2,
              py: 1.5,
              bgcolor: "#FFF7E6",
              borderBottom: "1px solid #FDECC8",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 2,
            }}
          >
            <Typography sx={{ fontSize: 14, color: "#5F4320" }}>
              Your posts are ready, but they cannot be approved or scheduled until you connect at least one platform.
            </Typography>
            <Button
              variant="contained"
              size="small"
              onClick={() => navigate("/integrations")}
              sx={{ bgcolor: "#111", color: "#fff", textTransform: "none", borderRadius: 1.5, "&:hover": { bgcolor: "#333" } }}
            >
              Connect
            </Button>
          </Box>
        )}
        {/* ── Top Bar ── */}


        {/* ── Day Columns ── */}
        {/* <Stack direction="row" spacing={3} alignItems="flex-start">
          {days.map(day => (
            <DayColumn
              key={day}
              dateLabel={`${day} ${day === 'Mar 28' ? 'Sat' : 'Sun'}`}
              posts={POSTS?.[day] ?? []}
            />
          ))}
        </Stack> */}
        <Stack
          direction="row"
          spacing={3}
          alignItems="flex-start"
          sx={{ overflowX: "auto", pb: 2, px: 2, pt: 2 }}
        >
          {loading ? (
            <GenerationState />
          ) : imageData.length === 0 ? (
            // Empty state
            <Typography color="text.secondary">No posts scheduled.</Typography>
          ) : (
            visibleDays.map(day => {
              const dateKey = day.format("YYYY-MM-DD");
              return (
                <DayColumn
                  key={dateKey}
                  dateKey={dateKey}
                  dateLabel={day.format("MMM D ddd")}
                  posts={POSTS?.[dateKey] ?? []}
                  selectedPosts={selectedPosts}
                  setSelectedPosts={setSelectedPosts}
                  hasConnectedPlatform={hasConnectedPlatform}
                  minWidth={270}
                  onDropPost={handleDropPost}
                />
              );
            })
          )}
        </Stack>
      </Box>
    </Box>
  );
}
