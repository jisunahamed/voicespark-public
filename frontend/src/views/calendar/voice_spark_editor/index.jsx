import { useState, useEffect, useRef, useMemo } from "react";
import {
    Box,
    Typography,
    IconButton,
    Button,
    Avatar,
    Chip,
    Divider,
    TextField,
    InputAdornment,
    Paper,
    Stack,
    Tooltip,
    Select,
    MenuItem,
    FormControl,
    CircularProgress,
    Alert,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Checkbox,
} from "@mui/material";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import LockIcon from "@mui/icons-material/Lock";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import SendIcon from "@mui/icons-material/Send";
import ImageIcon from "@mui/icons-material/Image";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import RepeatIcon from "@mui/icons-material/Repeat";
import FavoriteBorderIcon from "@mui/icons-material/FavoriteBorder";
import BarChartIcon from "@mui/icons-material/BarChart";
import BookmarkBorderIcon from "@mui/icons-material/BookmarkBorder";
import IosShareIcon from "@mui/icons-material/IosShare";
import CloseIcon from "@mui/icons-material/Close";
import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";
import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";
import BrushIcon from "@mui/icons-material/Brush";
import ClosedCaptionIcon from "@mui/icons-material/ClosedCaption";
import StyleIcon from "@mui/icons-material/Style";
import RefreshIcon from "@mui/icons-material/Refresh";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import EditIcon from "@mui/icons-material/Edit";
import TextFieldsIcon from "@mui/icons-material/TextFields";
import PaletteIcon from "@mui/icons-material/Palette";
import SubtitlesIcon from "@mui/icons-material/Subtitles";
import PostAddIcon from "@mui/icons-material/PostAdd";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import NotificationsNoneIcon from "@mui/icons-material/NotificationsNone";
import VideoLabelIcon from "@mui/icons-material/VideoLabel";
import { Link, useLocation } from "react-router-dom";
import { useNavigate } from 'react-router-dom';
import { useParams } from 'react-router-dom';
import config from "../../../config";
import axios from "axios";
import { Instagram, Facebook, X, LinkedIn, Google } from "@mui/icons-material";
/////

// import { useState } from "react";
import {

    Popover, ToggleButton, ToggleButtonGroup
} from "@mui/material";
// import { Delete, Send } from "@mui/icons-material";
import {
    Delete,
    Send,
    KeyboardArrowDown,
    OpenInNew,
    Link as LinkIcon,
    FileDownload,
    DeleteOutline,
} from "@mui/icons-material";
import { LocalizationProvider, DateCalendar } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import dayjs from "dayjs";



import { Menu } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import CreditCardIcon from '@mui/icons-material/CreditCard';
import PeopleIcon from '@mui/icons-material/People';

import GroupsIcon from '@mui/icons-material/Groups';
import CardGiftcardIcon from '@mui/icons-material/CardGiftcard';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import NotificationsIcon from '@mui/icons-material/Notifications';
import LogoutIcon from '@mui/icons-material/Logout';

import { useAuth } from "../../login_register/auth_context";
import api from "../../login_register/axios_client";
import { MenuItemsSign } from "../../../TopBar";
import { workspaceStorage } from "../../workspace/workSpaceAPi";

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
        if (data.status === "completed") return data.result || {};
        if (data.status === "failed") {
            throw new Error(data.error || data.result?.error || "Generation failed.");
        }
        await wait(intervalMs);
    }
    throw new Error("Generation is still running. Please refresh this editor in a moment.");
}

async function postGeneration(url, payload) {
    const response = await postWithRetry(url, payload);
    if (response.data?.job_id) {
        return waitForGenerationJob(response.data.job_id);
    }
    return response.data || {};
}

// function MenuItemsSign({ open, handleClose, anchorEl }) {
//     const navigate = useNavigate();
//     const { logout } = useAuth();
//     const handleSignOut = async () => {
//         handleClose();
//         await logout();
//         navigate('/login');

//     }
//     const user = JSON.parse(localStorage.getItem('user'));
//     return (
//         <Menu
//             anchorEl={anchorEl}
//             open={open}
//             onClose={handleClose}
//             anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
//             transformOrigin={{ vertical: 'top', horizontal: 'right' }}
//             PaperProps={{ sx: { width: 240, borderRadius: 2, mt: 1 } }}
//         >
//             {/* Header */}
//             <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
//                 <Avatar sx={{ width: 36, height: 36, bgcolor: '#7c3aed', fontSize: 14 }}>S</Avatar>
//                 <Box>
//                     <Typography fontWeight={600} fontSize={14}>{user.first_name} {user.last_name}</Typography>
//                     <Typography fontSize={12} color="text.secondary">{user.email}</Typography>
//                 </Box>
//             </Box>

//             <Divider />

//             {/* Credits */}
//             <Box sx={{ mx: 2, my: 1, bgcolor: '#f5f3ff', borderRadius: 2, py: 0.8, display: 'flex', justifyContent: 'center' }}>
//                 <Typography fontSize={13} fontWeight={500} color="#7c3aed">✦ 142 credits</Typography>
//             </Box>

//             <Divider />

//             <MenuItem onClick={handleClose}><SettingsIcon sx={{ mr: 1.5, fontSize: 18 }} /> Settings</MenuItem>
//             <MenuItem onClick={handleClose}><CreditCardIcon sx={{ mr: 1.5, fontSize: 18 }} /> Your Billing</MenuItem>

//             <Divider />

//             <MenuItem onClick={handleClose}><PeopleIcon sx={{ mr: 1.5, fontSize: 18 }} /> Switch Workspace <ChevronRightIcon sx={{ ml: 'auto' }} /></MenuItem>

//             <Divider />

//             <MenuItem onClick={handleClose}><GroupsIcon sx={{ mr: 1.5, fontSize: 18 }} /> Join Our Community</MenuItem>
//             <MenuItem onClick={handleClose}><CardGiftcardIcon sx={{ mr: 1.5, fontSize: 18 }} /> Refer & Earn</MenuItem>
//             <MenuItem onClick={handleClose}><MenuBookIcon sx={{ mr: 1.5, fontSize: 18 }} /> Help Center</MenuItem>
//             <MenuItem onClick={handleClose}><NotificationsIcon sx={{ mr: 1.5, fontSize: 18 }} /> Support</MenuItem>

//             <Divider />
const SHORT_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const CAPTION_LIMITS = {
    instagram: 2200,
    facebook: 30000,
    linkedin: 3000,
    twitter: 280,
};

const getPlatformCaption = (imageData, platform) => (
    imageData?.platform_captions?.[platform] || imageData?.title || ""
);

const publishStatusMessage = (meta = {}) => {
    if (meta?.publish_error) return meta.publish_error;
    const statusMap = meta?.platform_publish_status || {};
    const failed = Object.entries(statusMap).find(([, item]) => ["failed", "skipped"].includes(item?.status));
    if (!failed) return "";
    const [platform, item] = failed;
    return item?.error || `${platform} publish failed.`;
};

// ── Separate Calendar Popover Component ──
function ScheduleCalendarPopover({ anchorEl, onClose, onUpdate, id, imageData, onPostNow }) {
    const initialDate = imageData?.scheduled_at ? dayjs(imageData.scheduled_at) : dayjs().add(1, 'hour').startOf('hour');
    const [selectedDate, setSelectedDate] = useState(initialDate);
    const [hour, setHour] = useState(parseInt(initialDate.format('h'), 10));
    const [minute, setMinute] = useState(initialDate.minute());
    const [ampm, setAmpm] = useState(initialDate.format('A'));
    const [posting, setPosting] = useState(false);
    const [postError, setPostError] = useState("");
    const [postSuccess, setPostSuccess] = useState("");

    const open = Boolean(anchorEl);

    function handleUpdate() {
        const hour24 = ampm === "PM" ? (hour % 12) + 12 : hour % 12;
        const selectedDateTime = selectedDate.hour(hour24).minute(minute).second(0).millisecond(0);
        if (selectedDateTime.isBefore(dayjs())) {
            setPostError("Schedule time must be in the future. Use Post Now to publish immediately.");
            return;
        }
        const dayName = SHORT_DAYS[selectedDate.day()];
        const monthName = SHORT_MONTHS[selectedDate.month()];
        const mm = minute.toString().padStart(2, "0");
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        onUpdate(`${dayName}, ${monthName} ${selectedDate.date()} ${hour}:${mm}${ampm} ${timezone}`, selectedDateTime.toISOString());
        onClose();
    }

    const handlePost = async () => {
        if (onPostNow) {
            setPosting(true);
            setPostError("");
            try {
                await onPostNow();
                onClose();
            } catch (error) {
                setPostError(apiErrorMessage(error, "Post Now failed."));
            } finally {
                setPosting(false);
            }
        }
    };


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
                            GMT+6
                        </Typography>
                    </Box>
                </Box>
            </Box>

            <Box sx={{ px: 1.5, pb: 1.5, display: "flex", flexDirection: "column", gap: 1 }}>
                {postError && (
                    <Alert severity="error" sx={{ py: 0, fontSize: 12 }}>
                        {postError}
                    </Alert>
                )}
                {postSuccess && (
                    <Alert severity="success" sx={{ py: 0, fontSize: 12 }}>
                        {postSuccess}
                    </Alert>
                )}
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
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                    <Button
                        startIcon={<Delete fontSize="small" />}
                        onClick={onClose}
                        sx={{ fontSize: 12, textTransform: "none", color: "text.secondary" }}
                    >
                        Remove date
                    </Button>
                    <Button
                        startIcon={<Send fontSize="small" />}
                        onClick={handlePost}
                        disabled={posting}
                        sx={{ fontSize: 12, textTransform: "none", color: "text.secondary" }}
                    >
                        {posting ? "Posting..." : "Post Now"}
                    </Button>
                </Box>
            </Box>
        </Popover>
    );
}



// Platform icons as colored circles
const PlatformIcon = ({ platform, size = 28, selected = false, onClick }) => {
    const configs = {
        instagram: { bg: "linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)", label: "IG", icon: <Instagram /> },
        facebook: { bg: "#1877F2", label: "f", icon: <Facebook /> },
        linkedin: { bg: "#0A66C2", label: "in", icon: <LinkedIn /> },
        twitter: { bg: "#000", label: "𝕏", icon: <X /> },
        google: { bg: "#fff", label: "G", border: "1px solid #ddd", icon: <Google /> },
    };
    const c = configs[platform];

    return (
        <Box
            onClick={onClick}  // ← moved here
            sx={{
                width: size,
                height: size,
                borderRadius: "50%",
                background: c.bg,
                border: selected ? "2.5px solid #7C3AED" : c.border || "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: platform === "google" ? "#EA4335" : "#fff",
                fontSize: size * 0.45,
                fontWeight: 700,
                cursor: "pointer",
                boxSizing: "border-box",
                flexShrink: 0,
            }}
        >
            {c.icon}
        </Box>
    );
};

function EditCaptionsDialog({
    open,
    onClose,
    onSave,
    onRegenerateCaption,
    imageData,
    saving,
    error,
    connectedAccounts,
    selectedConnections,
}) {
    const baseCaption = imageData?.title || "";
    const [captions, setCaptions] = useState({
        instagram: "",
        facebook: "",
        linkedin: "",
        twitter: "",
    });
    const [regeneratingPlatform, setRegeneratingPlatform] = useState("");

    useEffect(() => {
        if (!open) return;
        setCaptions({
            instagram: getPlatformCaption(imageData, "instagram"),
            facebook: getPlatformCaption(imageData, "facebook"),
            linkedin: getPlatformCaption(imageData, "linkedin"),
            twitter: getPlatformCaption(imageData, "twitter"),
        });
    }, [open, imageData]);

    const facebookPageName = connectedAccounts?.facebook_pages?.[0]?.name;
    const platforms = [
        {
            key: "instagram",
            label: "Instagram",
            icon: <Instagram sx={{ fontSize: 22, color: "#E4405F" }} />,
            description: "Conversational, expressive, uses emojis and short sentences",
            connected: selectedConnections.insta,
        },
        {
            key: "facebook",
            label: "Facebook",
            icon: <Facebook sx={{ fontSize: 22, color: "#1877F2" }} />,
            description: "Balanced between personal and informative; encourages comments",
            connected: selectedConnections.fb,
            accountName: facebookPageName,
        },
        {
            key: "linkedin",
            label: "LinkedIn",
            icon: <LinkedIn sx={{ fontSize: 22, color: "#0A66C2" }} />,
            description: "Formal but human; focus on expertise, leadership, and value",
            connected: selectedConnections.linkedin,
        },
        {
            key: "twitter",
            label: "X/Twitter",
            icon: <X sx={{ fontSize: 22, color: "#111" }} />,
            description: "Short, punchy language",
            connected: selectedConnections.x,
        },
    ];

    const handleChange = (key, value) => {
        setCaptions((prev) => ({ ...prev, [key]: value }));
    };

    const handleRegenerate = async (platform) => {
        if (!onRegenerateCaption || regeneratingPlatform) return;
        setRegeneratingPlatform(platform);
        try {
            const nextCaption = await onRegenerateCaption(platform, captions);
            if (nextCaption) {
                handleChange(platform, nextCaption);
            }
        } finally {
            setRegeneratingPlatform("");
        }
    };

    return (
        <Dialog
            open={open}
            onClose={saving ? undefined : onClose}
            maxWidth={false}
            PaperProps={{
                sx: {
                    width: "min(1060px, calc(100vw - 48px))",
                    borderRadius: 3,
                    boxShadow: "0 18px 60px rgba(15,23,42,0.16)",
                },
            }}
        >
            <DialogTitle sx={{ px: 4, pt: 3.5, pb: 1.5, display: "flex", alignItems: "center" }}>
                <Typography fontSize={28} fontWeight={500}>Edit Captions</Typography>
                <IconButton size="small" onClick={onClose} disabled={saving} sx={{ ml: "auto" }}>
                    <CloseIcon fontSize="small" />
                </IconButton>
            </DialogTitle>
            <DialogContent sx={{ px: 4, pb: 3 }}>
                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                )}
                <Box
                    sx={{
                        display: "flex",
                        gap: 2.5,
                        overflowX: "auto",
                        pb: 1.5,
                        scrollSnapType: "x proximity",
                    }}
                >
                    {platforms.map((platform) => {
                        const value = captions[platform.key] || "";
                        const limit = CAPTION_LIMITS[platform.key];
                        const overLimit = value.length > limit;
                        return (
                            <Box
                                key={platform.key}
                                sx={{
                                    flex: "0 0 280px",
                                    scrollSnapAlign: "start",
                                }}
                            >
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5, minHeight: 34 }}>
                                    {platform.icon}
                                    <Typography fontSize={18}>{platform.label}</Typography>
                                    <Button
                                        size="small"
                                        variant="outlined"
                                        disabled
                                        sx={{
                                            ml: "auto",
                                            minWidth: 70,
                                            color: platform.connected ? "#166534" : "#111827",
                                            borderColor: platform.connected ? "#BBF7D0" : "#E5E7EB",
                                            bgcolor: platform.connected ? "#F0FDF4" : "#fff",
                                            textTransform: "none",
                                        }}
                                    >
                                        {platform.connected ? "Connected" : "Connect"}
                                    </Button>
                                </Box>
                                {platform.accountName && (
                                    <Typography fontSize={12} color="text.secondary" sx={{ mb: 0.75 }}>
                                        {platform.accountName}
                                    </Typography>
                                )}
                                <Typography fontSize={14} color="text.secondary" sx={{ lineHeight: 1.35, minHeight: 40, mb: 1 }}>
                                    {platform.description}
                                </Typography>
                                <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 0.5, mb: 1 }}>
                                    <Tooltip title="Regenerate this platform caption">
                                        <span>
                                            <IconButton
                                                size="small"
                                                onClick={() => handleRegenerate(platform.key)}
                                                disabled={saving || regeneratingPlatform === platform.key}
                                            >
                                                {regeneratingPlatform === platform.key ? (
                                                    <CircularProgress size={18} />
                                                ) : (
                                                    <RefreshIcon sx={{ fontSize: 18 }} />
                                                )}
                                            </IconButton>
                                        </span>
                                    </Tooltip>
                                    <Tooltip title="Reset from main caption">
                                        <span>
                                            <IconButton
                                                size="small"
                                                onClick={() => handleChange(platform.key, baseCaption)}
                                                disabled={saving || regeneratingPlatform === platform.key}
                                            >
                                                <ClosedCaptionIcon sx={{ fontSize: 18 }} />
                                            </IconButton>
                                        </span>
                                    </Tooltip>
                                </Box>
                                <TextField
                                    fullWidth
                                    multiline
                                    minRows={13}
                                    value={value}
                                    onChange={(event) => handleChange(platform.key, event.target.value)}
                                    error={overLimit}
                                    sx={{
                                        "& .MuiOutlinedInput-root": {
                                            alignItems: "flex-start",
                                            borderRadius: 1,
                                            fontSize: 14,
                                            bgcolor: "#fff",
                                        },
                                    }}
                                />
                                <Typography
                                    fontSize={12}
                                    color={overLimit ? "error.main" : "text.secondary"}
                                    sx={{ mt: 1, textAlign: "right" }}
                                >
                                    Character Count: {value.length}/{limit}
                                </Typography>
                            </Box>
                        );
                    })}
                </Box>
            </DialogContent>
            <DialogActions sx={{ px: 3, py: 2, borderTop: "1px solid #F3F4F6" }}>
                <Button onClick={onClose} disabled={saving} sx={{ color: "#111827", textTransform: "none" }}>
                    Cancel
                </Button>
                <Box sx={{ flex: 1 }} />
                <Button
                    variant="outlined"
                    onClick={() => onSave(captions)}
                    disabled={saving}
                    sx={{ textTransform: "none", borderColor: "#E5E7EB", color: "#111827" }}
                >
                    {saving ? "Saving..." : "Save Captions"}
                </Button>
            </DialogActions>
        </Dialog>
    );
}

function TopBar({ id, imageData }) {
    const [anchorEl, setAnchorEl] = useState(null);
    const [postMenuAnchor, setPostMenuAnchor] = useState(null);
    const open = Boolean(anchorEl);
    const postMenuOpen = Boolean(postMenuAnchor);

    const handleOpen = (e) => setAnchorEl(e.currentTarget);
    const handleClose = () => setAnchorEl(null);
    const handlePostMenuOpen = (e) => setPostMenuAnchor(e.currentTarget);
    const handlePostMenuClose = () => setPostMenuAnchor(null);
    const navigate = useNavigate();
    const user = JSON.parse(localStorage.getItem('user'));
    const avatar = user.first_name?.[0]?.toUpperCase() ?? ""

    const copyText = async (text) => {
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
        } catch (error) {
            const textarea = document.createElement("textarea");
            textarea.value = text;
            textarea.style.position = "fixed";
            textarea.style.opacity = "0";
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
        }
    };

    const handleExportDesign = async () => {
        if (!id) return;
        try {
            const response = await axios.post(
                config.API_SERVER + "nano-banana/download-image/",
                {
                    user_id: user.id,
                    nano_banana_id: id,
                },
                { responseType: "blob" }
            );
            const contentDisposition = response.headers["content-disposition"] || "";
            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
            const filename = filenameMatch?.[1] || `voice-spark-design-${id}.png`;
            const blob = new Blob([response.data], { type: response.headers["content-type"] || "image/png" });
            const objectUrl = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = objectUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(objectUrl);
        } catch (error) {
            console.error(error);
        }
    };

    const handleDeletePost = async () => {
        if (!window.confirm("Delete this design?")) return;
        try {
            await axios.post(config.API_SERVER + "nano-banana/delete-image/", {
                user_id: user.id,
                nano_banana_id: id,
            });
            navigate("/calendar");
        } catch (error) {
            console.error(error);
        }
    };

    const menuAction = async (action) => {
        handlePostMenuClose();
        if (action === "open") {
            window.open(window.location.href, "_blank", "noopener,noreferrer");
        }
        if (action === "copy-link") {
            await copyText(window.location.href);
        }
        if (action === "export") {
            await handleExportDesign();
        }
        if (action === "delete") {
            await handleDeletePost();
        }
    };

    return (
        <Box
            sx={{
                height: 52,
                bgcolor: "#fff",
                borderBottom: "1px solid #E5E7EB",
                display: "flex",
                alignItems: "center",
                px: 2,
                gap: 1,
            }}
        >
            <IconButton size="small"
                component={Link}
                to={'/calendar'}
            ><ArrowBackIcon fontSize="small" /></IconButton>
            <IconButton size="small"><CalendarTodayIcon fontSize="small" /></IconButton>

            {/* Center */}
            <Box sx={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center", gap: 1 }}>
                <PlatformIcon platform="linkedin" size={30} />
                <PlatformIcon platform="twitter" size={30} />
                <Typography variant="body2" fontWeight={600} sx={{ mx: 0.5 }}>
                    Enhancing Speed and User Journey
                </Typography>
                <Chip label="Draft" size="small" sx={{ bgcolor: "#E5E7EB", color: "#374151", fontSize: 11, height: 22 }} />
                <IconButton size="small" onClick={handlePostMenuOpen}><MoreHorizIcon fontSize="small" /></IconButton>
            </Box>

            {/* Right */}
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Avatar sx={{ width: 30, height: 30, fontSize: 13 }} onClick={handleOpen}>{avatar}</Avatar>
            </Box>

            <MenuItemsSign
                open={open}
                handleClose={handleClose}
                anchorEl={anchorEl}
            />
            <Menu
                anchorEl={postMenuAnchor}
                open={postMenuOpen}
                onClose={handlePostMenuClose}
                anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                transformOrigin={{ vertical: "top", horizontal: "right" }}
                PaperProps={{ sx: { width: 245, borderRadius: 2, mt: 1, boxShadow: "0 14px 35px rgba(15,23,42,0.14)" } }}
            >
                <MenuItem onClick={() => menuAction("open")} sx={{ fontSize: 14, gap: 1.5 }}>
                    <OpenInNew sx={{ fontSize: 18 }} /> Open in new tab
                </MenuItem>
                <MenuItem onClick={() => menuAction("copy-link")} sx={{ fontSize: 14, gap: 1.5 }}>
                    <LinkIcon sx={{ fontSize: 18 }} /> Copy Link
                </MenuItem>
                <Divider />
                <MenuItem onClick={() => menuAction("export")} sx={{ fontSize: 14, gap: 1.5 }}>
                    <FileDownload sx={{ fontSize: 18 }} /> Export Design
                </MenuItem>
                <MenuItem onClick={() => menuAction("delete")} sx={{ fontSize: 14, gap: 1.5, color: "#991B1B" }}>
                    <DeleteOutline sx={{ fontSize: 18 }} /> Delete
                </MenuItem>
            </Menu>
        </Box>
    );
}

function LeftPanel({ id, imageData, setImageData }) {
    const navigate = useNavigate();

    const user = JSON.parse(localStorage.getItem('user'));
    const workspaceId = workspaceStorage.getActiveId();
    const [aiPrompt, setAiPrompt] = useState("");
    const [changeImage, setChangeImage] = useState(false);
    const [showCaption, setShowCaption] = useState(false);
    const [messages, setMessages] = useState([]);
    const messagesEndRef = useRef(null);

    const [loading, setLoading] = useState(false);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, [messages, loading]);

    const getWorkingLabel = () => {
        if (changeImage && showCaption) return "Recreating image and caption";
        if (changeImage) return "Recreating image";
        if (showCaption) return "Updating caption";
        return "Working on your requested changes";
    };

    const handleSend = async () => {
        const prompt = aiPrompt.trim();
        if (!prompt || loading) return;

        const requestId = `${Date.now()}`;
        const workingLabel = getWorkingLabel();
        setMessages((prev) => [
            ...prev,
            { id: `${requestId}-user`, role: "user", text: prompt },
            { id: requestId, role: "agent", text: workingLabel, status: "loading" },
        ]);
        setAiPrompt("");
        setLoading(true);

        try {
            const currentImageUrl =
                imageData?.imageurl ||
                imageData?.image_url ||
                imageData?.picture_url ||
                imageData?.imageUrl ||
                "";
            const result = await postGeneration('/nano-banana/edit-generated-image/', {
                user_id: user.id,
                prompt,
                nano_banana_id: id,
                change_caption: showCaption,
                change_image: changeImage,
                workspace_id: workspaceId,
                target_platform: "multi-platform",
                image_size: "1:1",
                image_urls: currentImageUrl ? [currentImageUrl] : [],
            })
            if (result?.data) {
                setImageData((prev) => ({ ...(prev || {}), ...result.data }));
            } else if (result?.imageUrl) {
                setImageData((prev) => ({ ...prev, imageurl: result.imageUrl }));
            }
            setMessages((prev) =>
                prev.map((message) =>
                    message.id === requestId
                        ? { ...message, text: "Created successfully", status: "success" }
                        : message
                )
            );
        } catch (e) {
            console.error(e);
            setMessages((prev) =>
                prev.map((message) =>
                    message.id === requestId
                        ? {
                            ...message,
                            text: apiErrorMessage(e, "Could not complete the change. Please try again."),
                            status: "error",
                        }
                        : message
                )
            );
        } finally {
            setLoading(false);
        }
    };



    /////
    //   const [scheduleTime, setScheduleTime] = useState("Mon, Apr 6  11:00AM GMT+6");



    /////
    return (
        <Box
            sx={{
                width: 270,
                bgcolor: "#fff",
                borderRight: "1px solid #E5E7EB",
                display: "flex",
                flexDirection: "column",
                p: 1.5,
                gap: 1,
            }}
        >
            {/* <Divider sx={{ my: 0.5 }} /> */}
            <Box
                sx={{
                    flex: 1,
                    minHeight: 0,
                    overflowY: "auto",
                    display: "flex",
                    flexDirection: "column",
                    gap: 1,
                    pr: 0.5,
                }}
            >
                {messages.length === 0 ? (
                    <Box sx={{ flex: 1 }} />
                ) : (
                    messages.map((message) => (
                        <Box
                            key={message.id}
                            sx={{
                                alignSelf: message.role === "user" ? "flex-end" : "flex-start",
                                maxWidth: "92%",
                            }}
                        >
                            <Paper
                                elevation={0}
                                sx={{
                                    px: 1.25,
                                    py: 1,
                                    borderRadius: 2,
                                    border: "1px solid",
                                    borderColor:
                                        message.role === "user"
                                            ? "#DDD6FE"
                                            : message.status === "success"
                                                ? "#BBF7D0"
                                                : message.status === "error"
                                                    ? "#FECACA"
                                                    : "#E5E7EB",
                                    bgcolor:
                                        message.role === "user"
                                            ? "#F5F3FF"
                                            : message.status === "success"
                                                ? "#F0FDF4"
                                                : message.status === "error"
                                                    ? "#FEF2F2"
                                                    : "#F9FAFB",
                                }}
                            >
                                <Stack direction="row" spacing={1} alignItems="center">
                                    {message.status === "loading" && <CircularProgress size={14} sx={{ color: "#7C3AED" }} />}
                                    {message.status === "success" && <CheckCircleOutlineIcon sx={{ fontSize: 15, color: "#16A34A" }} />}
                                    {message.role === "agent" && !message.status && <AutoFixHighIcon sx={{ fontSize: 15, color: "#7C3AED" }} />}
                                    <Typography
                                        fontSize={12}
                                        color={message.status === "error" ? "#991B1B" : "#111827"}
                                        sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}
                                    >
                                        {message.text}
                                        {message.status === "loading" ? "..." : ""}
                                    </Typography>
                                </Stack>
                            </Paper>
                        </Box>
                    ))
                )}
                <Box ref={messagesEndRef} />
            </Box>

            {/* Image action buttons */}
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {[
                    { icon: <ImageIcon sx={{ fontSize: 14 }} />, label: "Change Image", onClick: () => setChangeImage(!changeImage), active: changeImage },
                    { icon: <SubtitlesIcon sx={{ fontSize: 14 }} />, label: "Change Caption", onClick: () => setShowCaption(!showCaption), active: showCaption },
                ].map((btn) => (
                    <Button
                        key={btn.label}
                        size="small"
                        variant="outlined"
                        startIcon={btn.icon}
                        onClick={btn.onClick}
                        sx={{
                            fontSize: 11,
                            borderColor: btn.active ? "#7C3AED" : "#E5E7EB",
                            color: btn.active ? "#7C3AED" : "#374151",
                            backgroundColor: btn.active ? "#F5F3FF" : "transparent",
                            py: 0.5,
                            px: 1,
                            "&:hover": { borderColor: "#7C3AED", color: "#7C3AED" },
                        }}
                    >
                        {btn.label}
                    </Button>
                ))}
            </Stack>

            <TextField
                fullWidth
                    placeholder={loading ? `${getWorkingLabel()}...` : "Ask Voice Spark to change something..."}
                size="medium"
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                multiline
                minRows={2}
                disabled={loading}
                onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                    }
                }}
                InputProps={{
                    startAdornment: (
                        <InputAdornment
                            position="start"
                            sx={{
                                position: "absolute",
                                bottom: 6,
                                left: 8,
                            }}
                        >
                            {/* <Button
                                size="small"
                                startIcon={<AttachFileIcon sx={{ fontSize: 14 }} />}
                                sx={{
                                    color: "#6B7280",
                                    fontSize: 11,
                                    textTransform: "none",
                                    minWidth: 0,
                                    padding: 0,
                                }}
                                disabled={loading}
                            >
                                Attach
                            </Button> */}
                        </InputAdornment>
                    ),
                    endAdornment: (
                        <InputAdornment
                            position="end"
                            sx={{
                                position: "absolute",
                                bottom: 6,
                                right: 8,
                            }}
                        >
                            <IconButton
                                size="small"
                                onClick={handleSend}
                                disabled={loading || !aiPrompt.trim()}
                                sx={{
                                    bgcolor: "#7C3AED",
                                    color: "#fff",
                                    width: 26,
                                    height: 26,
                                    "&:hover": { bgcolor: "#6D28D9" },
                                }}
                            >
                                {loading ? (
                                    <CircularProgress size={14} sx={{ color: "#fff" }} />
                                ) : (
                                    <SendIcon sx={{ fontSize: 14 }} />
                                )}
                            </IconButton>
                        </InputAdornment>
                    ),
                }}
                sx={{
                    "& .MuiOutlinedInput-root": {
                        alignItems: "flex-start",
                        fontSize: 12,
                        borderRadius: 2,
                        bgcolor: "#F9FAFB",
                        paddingTop: "8px",
                        paddingBottom: "32px",
                        paddingLeft: "8px",
                        paddingRight: "8px",
                    },
                    "& textarea": {
                        padding: 0,
                        margin: 2,
                    },
                }}
            />

        </Box>
    );
}
function RightPanel({ scheduleTime, setScheduleTime, id, imageData, x, fb, insta, linkedin, setImageData, connectedAccounts, selectedPlatform }) {




    const navigate = useNavigate();
    /////
    //   const [scheduleTime, setScheduleTime] = useState("Mon, Apr 6  11:00AM GMT+6");
    const [anchorEl, setAnchorEl] = useState(null);

    function openCalendar(e) {
        setAnchorEl(e.currentTarget);
    }

    function closeCalendar() {
        setAnchorEl(null);
    }
    const user = JSON.parse(localStorage.getItem('user'));
    const facebookPageName = connectedAccounts?.facebook_pages?.[0]?.name;

    const [approving, setApproving] = useState(false);
    const [approval, setApproval] = useState(null);
    const [regenerating, setRegenerating] = useState(false);
    const [regenerateError, setRegenerateError] = useState("");
    const [captionDialogOpen, setCaptionDialogOpen] = useState(false);
    const [captionSaving, setCaptionSaving] = useState(false);
    const [captionError, setCaptionError] = useState("");
    const [approvalError, setApprovalError] = useState("");
    const [selectedApprovalPlatforms, setSelectedApprovalPlatforms] = useState([]);
    const contentType = imageData?.content_type || imageData?.meta?.content_type || "social";
    const isSocialContent = contentType === "social";
    const liveConnections = useMemo(() => ({
        instagram: Boolean(connectedAccounts?.instagram),
        facebook: Boolean(connectedAccounts?.facebook),
        linkedin: Boolean(connectedAccounts?.linkedin),
        twitter: Boolean(connectedAccounts?.twitter),
    }), [connectedAccounts]);

    const approvalPlatforms = [
        { key: "instagram", label: "Instagram", connect: liveConnections.instagram },
        { key: "facebook", label: facebookPageName || "Facebook", connect: liveConnections.facebook },
        { key: "linkedin", label: "LinkedIn", connect: liveConnections.linkedin },
        { key: "twitter", label: "X", connect: liveConnections.twitter },
    ];
    const connectedApprovalPlatforms = approvalPlatforms.filter((platform) => platform.connect).map((platform) => platform.key);
    const selectedConnectedPlatforms = selectedApprovalPlatforms.filter((platform) => connectedApprovalPlatforms.includes(platform));

    useEffect(() => {
        if (imageData) {
            setApproval(imageData.approval);
        }
    }, [imageData])

    useEffect(() => {
        const approved = Array.isArray(imageData?.approved_platforms) ? imageData.approved_platforms : [];
        const approvedConnected = approved.filter((platform) => connectedApprovalPlatforms.includes(platform));
        setSelectedApprovalPlatforms(approvedConnected.length ? approvedConnected : connectedApprovalPlatforms);
    }, [imageData?.nano_banana_id, liveConnections.instagram, liveConnections.facebook, liveConnections.linkedin, liveConnections.twitter])

    const toggleApprovalPlatform = (platform) => {
        setApprovalError("");
        setSelectedApprovalPlatforms((prev) =>
            prev.includes(platform)
                ? prev.filter((item) => item !== platform)
                : [...prev, platform]
        );
    };

    const refreshPostData = async () => {
        const freshResponse = await postWithRetry("/nano-banana/get-image-id/", {
            nano_banana_id: id,
        });
        const freshData = freshResponse.data?.data;
        if (freshData) {
            setImageData(freshData);
            setApproval(freshData.approval);
            return freshData;
        }
        return null;
    };

    const waitForPublishResult = async () => {
        for (let attempt = 0; attempt < 8; attempt += 1) {
            await wait(1500);
            const freshData = await refreshPostData();
            if (!freshData) continue;
            const message = publishStatusMessage(freshData.meta);
            if (message) {
                setApprovalError(message);
                return freshData;
            }
            if (freshData.approval === "posted") {
                setApprovalError("");
                return freshData;
            }
        }
        return null;
    };

    const handleApproval = async (postNow = false) => {
        setApprovalError("");
        if (isSocialContent && !selectedConnectedPlatforms.length) {
            setApprovalError("Connect and select at least one platform before approving.");
            return;
        }
        setApproving(true);
        try {
            const response = await postWithRetry('/nano-banana/change-approval/', {
                user_id: user.id,
                nano_banana_id: id,
                approved_platforms: isSocialContent ? selectedConnectedPlatforms : [],
                post_now: postNow,
            });
            if (response.status === 200) {
                setApproval(response.data?.data?.approval || 'approved');
                if (response.data?.data) setImageData(response.data.data);
                if (postNow) {
                    await waitForPublishResult();
                }
            }
        } catch (error) {
            setApprovalError(error.response?.data?.error || "Approval failed. Please check connected platforms.");
        } finally {
            setApproving(false);
        }
    };

    const handleReject = async () => {
        setApprovalError("");
        setApproving(true);
        try {
            await postWithRetry('/nano-banana/change-approval/', {
                user_id: user.id,
                nano_banana_id: id,
                action: 'rejected',
            });
            navigate('/calendar');
        } catch (error) {
            setApprovalError(error.response?.data?.error || "Reject failed. Please try again.");
        } finally {
            setApproving(false);
        }
    };

    const handleRegenerate = async () => {
        setRegenerating(true);
        setRegenerateError("");
        try {
            const result = await postGeneration('/nano-banana/regenerate-image/', {
                user_id: user.id,
                nano_banana_ids: [id],
                workspace_id: workspaceStorage.getActiveId(),
                target_platform: selectedPlatform,
                image_size: "1:1",
            });
            if (result?.data) {
                const freshResponse = await postWithRetry("/nano-banana/get-image-id/", {
                    nano_banana_id: id,
                });
                const freshData = freshResponse.data?.data || result.data;
                setImageData(freshData);
                if (freshData.scheduled_at) {
                    setScheduleTime(new Date(freshData.scheduled_at).toLocaleString("en-US", {
                        weekday: "short",
                        month: "short",
                        day: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                        hour12: true,
                    }));
                }
            }
        } catch (error) {
            console.error(error);
            setRegenerateError(apiErrorMessage(error, "Regenerate failed. Please try again."));
        } finally {
            setRegenerating(false);
        }
    };

    const handleSaveCaptions = async (captions) => {
        setCaptionSaving(true);
        setCaptionError("");
        try {
            const response = await postWithRetry('/nano-banana/save-platform-captions/', {
                user_id: user.id,
                nano_banana_id: id,
                workspace_id: workspaceStorage.getActiveId(),
                captions,
            });
            if (response.data?.data) {
                setImageData(response.data.data);
            }
            setCaptionDialogOpen(false);
        } catch (error) {
            console.error(error);
            setCaptionError(error.response?.data?.error || "Captions could not be saved. Please try again.");
        } finally {
            setCaptionSaving(false);
        }
    };

    const handleRegenerateCaption = async (platform, captions) => {
        setCaptionError("");
        try {
            const response = await postWithRetry('/nano-banana/save-platform-captions/', {
                user_id: user.id,
                nano_banana_id: id,
                workspace_id: workspaceStorage.getActiveId(),
                captions,
                regenerate_platform: platform,
                instruction: `Regenerate the ${platform} caption for this post using the saved brand voice and business profile.`,
            });
            if (response.data?.data) {
                setImageData(response.data.data);
                return getPlatformCaption(response.data.data, platform);
            }
            return "";
        } catch (error) {
            console.error(error);
            setCaptionError(error.response?.data?.error || "Caption could not be regenerated. Please try again.");
            return "";
        }
    };

    function handleUpdate(newTime, scheduleTimeIso) {
        setScheduleTime(newTime);

        try {
            postWithRetry('/nano-banana/change-schedule-time/', {
                user_id: user.id,
                schedule_time: newTime,
                schedule_time_iso: scheduleTimeIso,
                nano_banana_id: id,
            })
                .then(response => {
                    if (response.data?.data) {
                        setImageData(response.data.data);
                    }
                })
                .catch(error => {
                    console.error(error);
                    setApprovalError(error.response?.data?.error || "Schedule time could not be updated.");
                });
        } catch (e) {
            console.error(e);
        }

    }
    const [nano_banana_id, setNanoBananaId] = useState('');
    const [navLoading, setNavLoading] = useState(null);
    const workspaceId = workspaceStorage.getActiveId();
    const handleNext = async (see) => {
        setNavLoading(see);
        const response = await axios.post(config.API_SERVER + 'nano-banana/return-id/', {
            user_id: user.id,
            nano_banana_id: id,
            workspace_id:workspaceId,
            see: see
        });
        if (response.status === 200) {
            const nextId = response.data.nano_banana_id;
            if (nextId && nextId !== null) {
                navigate('/voice-spark-editor/' + nextId);
            }
        }
        setNavLoading(null);
    };

    const publishMessage = publishStatusMessage(imageData?.meta);

    /////
    return (
        <>
        <Box
            sx={{
                width: 260,
                bgcolor: "#fff",
                borderLeft: "1px solid #E5E7EB",
                display: "flex",
                flexDirection: "column",
                overflow: "auto",
            }}
            >
            {/* Navigation */}
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", px: 2, py: 1.5, borderBottom: "1px solid #F3F4F6" }}>
                <Button
                    size="small"
                    onClick={() => handleNext('previous')}
                    startIcon={navLoading === 'previous' ? <CircularProgress size={14} /> : <ChevronLeftIcon />}
                    disabled={navLoading !== null}
                    sx={{ color: "#374151", fontSize: 12 }}
                >
                    Previous
                </Button>
                <Button
                    size="small"
                    onClick={() => handleNext('next')}
                    endIcon={navLoading === 'next' ? <CircularProgress size={14} /> : <ChevronRightIcon />}
                    disabled={navLoading !== null}
                    sx={{ color: "#374151", fontSize: 12 }}
                >
                    See Next
                </Button>
            </Box>

            {publishMessage && approval !== 'posted' && (
                <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid #F3F4F6" }}>
                    <Alert severity="error" sx={{ py: 0, fontSize: 12 }}>
                        {publishMessage}
                    </Alert>
                </Box>
            )}

            {/* Review actions */}
            {approval === 'not_approved' && (
                <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid #F3F4F6" }}>
                    <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5, fontSize: 10 }}>
                        Post to post
                    </Typography>
                    {approvalError && (
                        <Alert severity="error" sx={{ mt: 1, py: 0, fontSize: 12 }}>
                            {approvalError}
                        </Alert>
                    )}
                    {isSocialContent ? (
                        <Stack spacing={0.75} mt={1}>
                            {approvalPlatforms.map((platform) => (
                                <Box
                                    key={platform.key}
                                    onClick={() => platform.connect && toggleApprovalPlatform(platform.key)}
                                    sx={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 1,
                                        p: 0.75,
                                        borderRadius: 1.5,
                                        border: "1px solid",
                                        borderColor: selectedApprovalPlatforms.includes(platform.key) ? "#111827" : "#E5E7EB",
                                        bgcolor: platform.connect ? "#fff" : "#F9FAFB",
                                        opacity: 1,
                                        cursor: platform.connect ? "pointer" : "default",
                                    }}
                                >
                                    <Checkbox
                                        size="small"
                                        checked={selectedApprovalPlatforms.includes(platform.key)}
                                        disabled={!platform.connect}
                                        onChange={() => toggleApprovalPlatform(platform.key)}
                                        onClick={(event) => event.stopPropagation()}
                                        sx={{ p: 0.2 }}
                                    />
                                    <PlatformIcon platform={platform.key} size={24} />
                                    <Box sx={{ minWidth: 0, flex: 1 }}>
                                        <Typography fontSize={12} fontWeight={700} noWrap>{platform.label}</Typography>
                                        <Typography fontSize={10} color="text.secondary">{platform.connect ? "Connected" : "Not connected"}</Typography>
                                    </Box>
                                    {!platform.connect && (
                                        <Button
                                            size="small"
                                            variant="outlined"
                                            onClick={(event) => {
                                                event.stopPropagation();
                                                navigate("/integrations");
                                            }}
                                            sx={{ minWidth: 64, py: 0.25, fontSize: 11, textTransform: "none", borderRadius: 1 }}
                                        >
                                            Connect
                                        </Button>
                                    )}
                                </Box>
                            ))}
                        </Stack>
                    ) : (
                        <Typography fontSize={12} color="text.secondary" sx={{ mt: 1 }}>
                            {contentType === "blog" ? "Blog content" : "Email content"} can be approved without selecting social platforms.
                        </Typography>
                    )}
                    <Stack direction="row" spacing={1} mt={1.5}>
                        <Button
                            size="small"
                            variant="contained"
                            onClick={() => handleApproval(false)}
                            disabled={approving || (isSocialContent && !selectedConnectedPlatforms.length)}
                            sx={{ flex: 1, bgcolor: "#111", textTransform: "none", borderRadius: 1.5, "&:hover": { bgcolor: "#333" } }}
                        >
                            {approving ? "Working..." : "Approve"}
                        </Button>
                        <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            onClick={handleReject}
                            disabled={approving}
                            sx={{ flex: 1, textTransform: "none", borderRadius: 1.5 }}
                        >
                            Reject
                        </Button>
                    </Stack>
                    {isSocialContent && (
                        <Button
                            fullWidth
                            size="small"
                            variant="outlined"
                            onClick={() => handleApproval(true)}
                            disabled={approving || !selectedConnectedPlatforms.length}
                            sx={{ mt: 1, textTransform: "none", borderRadius: 1.5 }}
                        >
                            Post now
                        </Button>
                    )}
                </Box>
            )}
            <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid #F3F4F6" }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5, fontSize: 10 }}>
                    Improve
                </Typography>
                {regenerateError && (
                    <Alert severity="error" sx={{ mt: 1, py: 0, fontSize: 12 }}>
                        {regenerateError}
                    </Alert>
                )}
                <Stack spacing={0.5} mt={1}>
                    {[
                        ...(isSocialContent ? [{ icon: <ClosedCaptionIcon sx={{ fontSize: 15 }} />, label: "Captions", onClick: () => setCaptionDialogOpen(true) }] : []),
                        { icon: <StyleIcon sx={{ fontSize: 15 }} />, label: "Brand", onClick: () => navigate("/brand-kit") },
                        {
                            icon: regenerating ? <CircularProgress size={15} /> : <RefreshIcon sx={{ fontSize: 15 }} />,
                            label: regenerating ? "Regenerating..." : "Regenerate",
                            onClick: handleRegenerate,
                            disabled: regenerating,
                        },
                    ].map((item) => (
                        <Button
                            key={item.label}
                            size="small"
                            startIcon={item.icon}
                            onClick={item.onClick}
                            disabled={item.disabled}
                            sx={{
                                justifyContent: "flex-start",
                                color: "#374151",
                                fontSize: 12,
                                px: 1,
                                py: 0.6,
                                borderRadius: 1.5,
                                "&:hover": { bgcolor: "#F5F3FF", color: "#7C3AED" },
                            }}
                        >
                            {item.label}
                        </Button>
                    ))}
                </Stack>
            </Box>

            {/* Posting on */}
            {isSocialContent && <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid #F3F4F6" }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5, fontSize: 10 }}>
                    Posting on
                </Typography>
                <Box
                    onClick={openCalendar}
                    sx={{
                        mt: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        px: 1.5,
                        py: "8.5px",
                        fontSize: 12,
                        bgcolor: "#F9FAFB",
                        border: "1px solid rgba(0,0,0,0.23)",
                        borderRadius: 1,
                        cursor: "pointer",
                        "&:hover": { border: "1px solid rgba(0,0,0,0.87)" },
                    }}
                >
                    <Typography fontSize={12} color="text.primary">{scheduleTime}</Typography>
                    <KeyboardArrowDown sx={{ fontSize: 18, color: "text.secondary" }} />
                </Box>
            </Box>}
            <ScheduleCalendarPopover
                anchorEl={anchorEl}
                onClose={closeCalendar}
                onUpdate={handleUpdate}
                id={id}
                imageData={imageData}
                onPostNow={() => handleApproval(true)}
            />

        </Box>
        <EditCaptionsDialog
            open={captionDialogOpen}
            onClose={() => setCaptionDialogOpen(false)}
            onSave={handleSaveCaptions}
            onRegenerateCaption={handleRegenerateCaption}
            imageData={imageData}
            saving={captionSaving}
            error={captionError}
            connectedAccounts={connectedAccounts}
            selectedConnections={{
                x: liveConnections.twitter,
                fb: liveConnections.facebook,
                insta: liveConnections.instagram,
                linkedin: liveConnections.linkedin,
            }}
        />
        </>
    );
}


export default function VoiceSparkEditor() {
    const { id } = useParams();
    const navigate = useNavigate();
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const [imageData, setImageData] = useState(null);
    const [connectedAccounts, setConnectedAccounts] = useState({
        facebook_pages: [],
        instagram_connected: false,
    });
    const [visualFeedback, setVisualFeedback] = useState(null);
    const [feedbackSaving, setFeedbackSaving] = useState(false);
    const [showFeedbackBar, setShowFeedbackBar] = useState(true);

    const [x, setX] = useState(false);
    const [fb, setFb] = useState(false);
    const [insta, setInsta] = useState(false);
    const [linkedin, setLinkedin] = useState(false);

    const hasFetched = useRef(false);
    const [scheduleTime, setScheduleTime] = useState("Tue, Apr 7  10:00am");
    const formatScheduleTime = (dateStr) =>
        new Date(dateStr).toLocaleString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
            hour12: true,
        });

    useEffect(() => {

        const fetchImage = async () => {
            const response = await axios.post(config.API_SERVER + "nano-banana/get-image-id/", {
                nano_banana_id: id,
            });
            setImageData(response.data.data);  // ← .data.data because axios wraps in .data and Django returns {"data": {...}}
            setScheduleTime(formatScheduleTime(response.data.data.scheduled_at));
            setX(response.data.social_media.x);
            setFb(response.data.social_media.fb);
            setInsta(response.data.social_media.insta);
            setLinkedin(response.data.social_media.linkedin);
        };

        fetchImage();
    }, [id]);

    useEffect(() => {
        if (!user.id) return;
        let active = true;
        axios.post(config.API_SERVER + 'auth/fb/connected-accounts/', {
            user_id: user.id,
            workspace_id: workspaceStorage.getActiveId(),
        })
            .then((response) => {
                if (active) {
                    setConnectedAccounts(response.data);
                }
            })
            .catch((error) => {
                console.error(error);
            });
        return () => {
            active = false;
        };
    }, [user.id]);





    /////
    //   const [scheduleTime, setScheduleTime] = useState("Mon, Apr 6 � 11:00AM GMT+6");
    const [anchorEl, setAnchorEl] = useState(null);

    function openCalendar(e) {
        setAnchorEl(e.currentTarget);
    }

    function closeCalendar() {
        setAnchorEl(null);
    }

    function handleUpdate(newTime) {
        setScheduleTime(newTime);
    }
    /////




    // const [postText] = useState(
    //     imageData?.title
    // );
    const char = user.first_name?.charAt(0).toUpperCase() || "";
    const facebookPage = connectedAccounts.facebook_pages?.[0];
    const facebookPageName = facebookPage?.name || `${user.first_name || ""} ${user.last_name || ""}`.trim();
    const facebookPagePicture = facebookPage?.picture_url;
    // console.log(user);
    const [selectedPlatform, setSelectedPlatform] = useState('twitter');
    const previewPlatforms = useMemo(() => {
        const saved = Array.isArray(imageData?.approved_platforms) ? imageData.approved_platforms : [];
        const candidates = [
            { key: "instagram", enabled: insta || saved.includes("instagram") },
            { key: "facebook", enabled: fb || saved.includes("facebook") },
            { key: "linkedin", enabled: linkedin || saved.includes("linkedin") },
            { key: "twitter", enabled: x || saved.includes("twitter") || saved.includes("x") },
        ];
        const enabled = candidates.filter((platform) => platform.enabled).map((platform) => platform.key);
        return enabled.length ? enabled : candidates.map((platform) => platform.key);
    }, [imageData?.approved_platforms, insta, fb, linkedin, x]);

    useEffect(() => {
        if (previewPlatforms.length && !previewPlatforms.includes(selectedPlatform)) {
            setSelectedPlatform(previewPlatforms[0]);
        }
    }, [previewPlatforms, selectedPlatform]);

    const platformCaption = getPlatformCaption(imageData, selectedPlatform);
    const contentType = imageData?.content_type || imageData?.meta?.content_type || "social";
    const isSocialContent = contentType === "social";
    const imageAssets = imageData?.meta?.image_assets || [];
    const inlineImage = imageAssets.find((item) => item.slot === "inline")?.url;
    const documentTitle = imageData?.content_title || imageData?.meta?.title || "";
    const documentBody = imageData?.platform_captions?.[contentType]?.caption || imageData?.title || "";

    const handleVisualFeedback = async (reaction) => {
        setFeedbackSaving(true);
        try {
            await axios.post(config.API_SERVER + 'nano-banana/visual-feedback/', {
                user_id: user.id,
                workspace_id: workspaceStorage.getActiveId(),
                nano_banana_id: id,
                reaction,
            });
            setVisualFeedback(reaction);
        } catch (error) {
            console.error(error);
        } finally {
            setFeedbackSaving(false);
        }
    };
    return (

        <Box sx={{ display: "flex", flexDirection: "column", height: "100vh", bgcolor: "#F3F4F6", fontFamily: "'DM Sans', sans-serif" }}>
            {/* ── Top Bar ── */}
            <TopBar id={id} imageData={imageData} />

            {/* ── Main Content ── */}
            <Box sx={{ flex: 1, display: "flex", overflow: "hidden" }}>

                {/* Left panel — AI editor */}
                <LeftPanel id={id} imageData={imageData} setImageData={setImageData} />


                <Box
                    sx={{
                        flex: 1,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "space-between",
                        overflow: "auto",
                        py: 3,
                        px: 2,
                        // position: "relative",
                    }}
                >

                    <Box sx={{ position: "relative", display: "inline-flex", alignItems: "center", margin: 5, }}>
                        {!isSocialContent ? (
                            <Paper elevation={0} sx={{ width: "min(760px, calc(100vw - 360px))", border: "1px solid #E5E7EB", borderRadius: 3, overflow: "hidden", bgcolor: "#fff" }}>
                                {contentType === "blog" && imageData?.imageurl && (
                                    <Box component="img" src={imageData.imageurl} alt={documentTitle} sx={{ width: "100%", aspectRatio: contentType === "blog" ? "16/9" : "3/1", objectFit: "cover", display: "block" }} />
                                )}
                                <Box sx={{ p: 4 }}>
                                    <Chip
                                        label={contentType === "blog" ? "Blog Post" : "Email"}
                                        size="small"
                                        sx={{ mb: 2, bgcolor: "#F3F4F6", color: "#374151", fontWeight: 700 }}
                                    />
                                    <TextField
                                        fullWidth
                                        variant="standard"
                                        label={contentType === "email" ? "Subject" : undefined}
                                        value={documentTitle}
                                        InputProps={{ disableUnderline: true }}
                                        sx={{ "& input": { fontSize: 28, fontWeight: 800, color: "#111827", lineHeight: 1.2 } }}
                                    />
                                    {contentType === "email" && imageData?.meta?.preheader && (
                                        <TextField
                                            fullWidth
                                            label="Preheader"
                                            value={imageData.meta.preheader}
                                            variant="standard"
                                            sx={{ mt: 2 }}
                                        />
                                    )}
                                    <TextField
                                        fullWidth
                                        multiline
                                        minRows={contentType === "blog" ? 18 : 10}
                                        value={documentBody}
                                        variant="outlined"
                                        sx={{
                                            mt: 3,
                                            "& .MuiOutlinedInput-root": { borderRadius: 2, fontSize: 15, lineHeight: 1.7, alignItems: "flex-start" },
                                        }}
                                    />
                                    {contentType === "blog" && inlineImage && (
                                        <Box sx={{ mt: 3 }}>
                                            <Typography fontSize={12} fontWeight={700} color="text.secondary" sx={{ mb: 1, textTransform: "uppercase", letterSpacing: 0.5 }}>
                                                Inline Image
                                            </Typography>
                                            <Box component="img" src={inlineImage} alt="Blog inline visual" sx={{ width: "100%", borderRadius: 2, aspectRatio: "4/3", objectFit: "cover" }} />
                                        </Box>
                                    )}
                                    {contentType === "email" && imageData?.meta?.cta && (
                                        <Typography sx={{ mt: 3, fontWeight: 700, color: "#111827" }}>
                                            CTA: {imageData.meta.cta}
                                        </Typography>
                                    )}
                                </Box>
                            </Paper>
                        ) : (
                        <>
                        <Box
                            sx={{
                                position: "absolute",
                                left: -48,           // ← sits just outside the card's left edge
                                top: "50%",
                                transform: "translateY(-50%)",
                                display: "flex",
                                flexDirection: "column",
                                gap: 1,
                                alignItems: "center",
                                zIndex: 2,
                            }}
                        >
                            <Typography variant="caption" color="text.secondary" sx={{ writingMode: "vertical-rl", transform: "rotate(180deg)", mb: 1, fontSize: 10 }}>
                                View as
                            </Typography>
                            {previewPlatforms.map((p) => (
                                <Tooltip key={p} title={`Preview as ${p === "twitter" ? "X" : p.charAt(0).toUpperCase() + p.slice(1)}`} placement="left">
                                    <Box>
                                        <PlatformIcon
                                            platform={p}
                                            size={36}
                                            selected={p === selectedPlatform}
                                            onClick={() => setSelectedPlatform(p)}
                                        />
                                    </Box>
                                </Tooltip>
                            ))}
                        </Box>



                        {selectedPlatform === 'twitter' && (
                            <Paper elevation={0} sx={{ maxWidth: 500, border: "1px solid #E5E7EB", borderRadius: 3, overflow: "hidden", bgcolor: "#fff" }}>
                                {/* Tweet header */}
                                <Box sx={{ p: 2, pb: 1, display: "flex", gap: 1.5, alignItems: "flex-start" }}>
                                    <Avatar sx={{ width: 38, height: 38, bgcolor: "#E5E7EB", color: "#9CA3AF", fontSize: 14 }}>{char}</Avatar>
                                    <Box sx={{ flex: 1 }}>
                                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                            <Typography variant="body2" fontWeight={700} fontSize={13}>{user.first_name} {user.last_name}</Typography>
                                            <Typography variant="caption" color="text.secondary">@{user.username}</Typography>
                                        </Box>
                                        <Typography variant="body2" color="text.primary" fontSize={13} sx={{ mt: 0.5, lineHeight: 1.5 }}>
                                            {platformCaption}
                                        </Typography>
                                    </Box>
                                </Box>
                                <Box sx={{ mx: 2, mb: 1.5, borderRadius: 2, overflow: "hidden", bgcolor: "#1a1a2e", aspectRatio: '1/1' }}>
                                    <Box component="img" src={imageData?.imageurl} alt="Post visual" sx={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.85 }} />
                                </Box>
                                {/* Tweet actions */}
                                <Box sx={{ px: 2, pb: 1.5, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                    {[
                                        { icon: <ChatBubbleOutlineIcon sx={{ fontSize: 16 }} />, count: "44" },
                                        { icon: <RepeatIcon sx={{ fontSize: 16 }} />, count: "1.7K" },
                                        { icon: <FavoriteBorderIcon sx={{ fontSize: 16 }} />, count: "31K" },
                                        { icon: <BarChartIcon sx={{ fontSize: 16 }} />, count: "1.4M" },
                                    ].map((a, i) => (
                                        <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 0.4, color: "#6B7280", cursor: "pointer" }}>
                                            {a.icon}
                                            <Typography variant="caption" fontSize={12}>{a.count}</Typography>
                                        </Box>
                                    ))}
                                    <Box sx={{ display: "flex", gap: 1, color: "#6B7280" }}>
                                        <BookmarkBorderIcon sx={{ fontSize: 16, cursor: "pointer" }} />
                                        <IosShareIcon sx={{ fontSize: 16, cursor: "pointer" }} />
                                    </Box>
                                </Box>
                            </Paper>
                        )}

                        {selectedPlatform === 'instagram' && (
                            <Paper elevation={0} sx={{ maxWidth: 500, border: "1px solid #E5E7EB", borderRadius: 3, overflow: "hidden", bgcolor: "#fff" }}>
                                {/* IG Header */}
                                <Box sx={{ p: 1.5, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                        <Avatar sx={{ width: 38, height: 38, bgcolor: "#E5E7EB", color: "#9CA3AF", fontSize: 14 }}>{char}</Avatar>
                                        <Box>
                                            <Typography fontSize={13} fontWeight={700}>{user.username}</Typography>

                                        </Box>
                                    </Box>
                                    <MoreHorizIcon sx={{ fontSize: 18, color: "#6B7280" }} />
                                </Box>
                                {/* Square image */}
                                <Box sx={{ width: "100%", aspectRatio: "1/1", bgcolor: "#1a1a2e" }}>
                                    <Box component="img" src={imageData?.imageurl} alt="Post visual" sx={{ width: "100%", height: "100%", objectFit: "cover" }} />
                                </Box>
                                {/* IG actions */}
                                <Box sx={{ px: 2, pt: 1.5, pb: 1 }}>
                                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                                        <Box sx={{ display: "flex", gap: 1.5, color: "#374151" }}>
                                            <FavoriteBorderIcon sx={{ fontSize: 22, cursor: "pointer" }} />
                                            <ChatBubbleOutlineIcon sx={{ fontSize: 22, cursor: "pointer" }} />
                                            <IosShareIcon sx={{ fontSize: 22, cursor: "pointer" }} />
                                        </Box>
                                        <BookmarkBorderIcon sx={{ fontSize: 22, color: "#374151", cursor: "pointer" }} />
                                    </Box>
                                    <Typography fontSize={13} fontWeight={700}>31,482 likes</Typography>
                                    <Typography fontSize={13} sx={{ mt: 0.5 }}>
                                        <strong>{user.username}</strong> {platformCaption}
                                    </Typography>
                                </Box>
                            </Paper>
                        )}

                        {selectedPlatform === 'linkedin' && (
                            <Paper elevation={0} sx={{ maxWidth: 500, border: "1px solid #E5E7EB", borderRadius: 3, overflow: "hidden", bgcolor: "#fff" }}>
                                {/* LI Header */}
                                <Box sx={{ p: 2, display: "flex", alignItems: "flex-start", gap: 1.5 }}>
                                    <Avatar sx={{ width: 38, height: 38, bgcolor: "#E5E7EB", color: "#9CA3AF", fontSize: 14 }}>{char}</Avatar>
                                    <Box>
                                        <Typography fontSize={14} fontWeight={700}>{user.first_name} {user.last_name}</Typography>
                                        <Typography fontSize={12} color="text.secondary">Software Engineer • 1st</Typography>
                                        <Typography fontSize={11} color="text.secondary">Just now • 🌐</Typography>
                                    </Box>
                                    <MoreHorizIcon sx={{ fontSize: 18, color: "#6B7280", ml: "auto" }} />
                                </Box>
                                <Typography fontSize={13} sx={{ px: 2, pb: 1.5 }}>{platformCaption}</Typography>
                                <Box sx={{ width: "100%", aspectRatio: '1/1', bgcolor: "#1a1a2e" }}>
                                    <Box component="img" src={imageData?.imageurl} alt="Post visual" sx={{ width: "100%", height: "100%", objectFit: "cover" }} />
                                </Box>
                                {/* LI actions */}
                                <Box sx={{ px: 2, py: 1.5, display: "flex", justifyContent: "space-around", borderTop: "1px solid #E5E7EB" }}>
                                    {[
                                        { icon: <ThumbUpAltOutlinedIcon sx={{ fontSize: 18 }} />, label: "Like" },
                                        { icon: <ChatBubbleOutlineIcon sx={{ fontSize: 18 }} />, label: "Comment" },
                                        { icon: <RepeatIcon sx={{ fontSize: 18 }} />, label: "Repost" },
                                        { icon: <IosShareIcon sx={{ fontSize: 18 }} />, label: "Send" },
                                    ].map((a) => (
                                        <Box key={a.label} sx={{ display: "flex", alignItems: "center", gap: 0.5, color: "#6B7280", cursor: "pointer", fontSize: 13 }}>
                                            {a.icon}
                                            <Typography fontSize={13}>{a.label}</Typography>
                                        </Box>
                                    ))}
                                </Box>
                            </Paper>
                        )}

                        {selectedPlatform === 'facebook' && (
                            <Paper elevation={0} sx={{ maxWidth: 500, border: "1px solid #E5E7EB", borderRadius: 3, overflow: "hidden", bgcolor: "#fff" }}>
                                {/* FB Header */}
                                <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
                                    <Avatar src={facebookPagePicture} sx={{ width: 38, height: 38, bgcolor: "#E5E7EB", color: "#9CA3AF", fontSize: 14 }}>
                                        {facebookPageName?.charAt(0) || char}
                                    </Avatar>
                                    <Box>
                                        <Typography fontSize={14} fontWeight={700}>{facebookPageName || `${user.first_name} ${user.last_name}`}</Typography>
                                        <Typography fontSize={11} color="text.secondary">Just now · 🌐</Typography>
                                    </Box>
                                    <MoreHorizIcon sx={{ fontSize: 18, color: "#6B7280", ml: "auto" }} />
                                </Box>
                                <Typography fontSize={13} sx={{ px: 2, pb: 1.5 }}>{platformCaption}</Typography>
                                <Box sx={{ width: "100%", aspectRatio: '1/1', bgcolor: "#1a1a2e" }}>
                                    <Box component="img" src={imageData?.imageurl} alt="Post visual" sx={{ width: "100%", height: "100%", objectFit: "cover" }} />
                                </Box>
                                {/* FB reactions */}
                                <Box sx={{ px: 2, py: 1, borderTop: "1px solid #E5E7EB", display: "flex", justifyContent: "space-around" }}>
                                    {[
                                        { icon: <ThumbUpAltOutlinedIcon sx={{ fontSize: 18 }} />, label: "Like" },
                                        { icon: <ChatBubbleOutlineIcon sx={{ fontSize: 18 }} />, label: "Comment" },
                                        { icon: <IosShareIcon sx={{ fontSize: 18 }} />, label: "Share" },
                                    ].map((a) => (
                                        <Box key={a.label} sx={{ display: "flex", alignItems: "center", gap: 0.5, color: "#6B7280", cursor: "pointer" }}>
                                            {a.icon}
                                            <Typography fontSize={13}>{a.label}</Typography>
                                        </Box>
                                    ))}
                                </Box>
                            </Paper>
                        )}
                        </>
                        )}



                    </Box>
                    {/* Bottom feedback bar */}
                    {showFeedbackBar && (
                        <Box
                            sx={{
                                mt: 3,
                                display: "flex",
                                alignItems: "center",
                                gap: 1.5,
                                bgcolor: "#fff",
                                border: "1px solid #E5E7EB",
                                borderRadius: 3,
                                px: 2.5,
                                py: 1,
                            }}
                        >
                            <Typography variant="body2" color="text.secondary" fontSize={13}>
                                Do you like the result?
                            </Typography>
                            <IconButton
                                size="small"
                                disabled={feedbackSaving}
                                onClick={() => handleVisualFeedback("dislike")}
                                sx={{ color: visualFeedback === "dislike" ? "#DC2626" : "#6B7280" }}
                            >
                                <ThumbDownAltOutlinedIcon fontSize="small" />
                            </IconButton>
                            <IconButton
                                size="small"
                                disabled={feedbackSaving}
                                onClick={() => handleVisualFeedback("like")}
                                sx={{ color: visualFeedback === "like" ? "#16A34A" : "#6B7280" }}
                            >
                                <ThumbUpAltOutlinedIcon fontSize="small" />
                            </IconButton>
                            {visualFeedback && (
                                <Typography fontSize={12} color="text.secondary">
                                    {visualFeedback === "like" ? "Saved as preferred" : "Saved to avoid"}
                                </Typography>
                            )}
                            <Button
                                size="small"
                                variant="outlined"
                                onClick={() => setShowFeedbackBar(false)}
                                sx={{ borderColor: "#E5E7EB", color: "#374151", fontSize: 12, ml: 1 }}
                            >
                                Close
                            </Button>
                        </Box>
                    )}
                </Box>

                <RightPanel
                    setScheduleTime={setScheduleTime}
                    scheduleTime={scheduleTime}
                    id={id}
                    imageData={imageData}
                    insta={insta}
                    fb={fb}
                    linkedin={linkedin}
                    x={x}
                    setImageData={setImageData}
                    connectedAccounts={connectedAccounts}
                    selectedPlatform={selectedPlatform}
                />
            </Box>
        </Box>

    );
}
