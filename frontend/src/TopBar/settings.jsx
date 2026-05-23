import { useEffect, useState } from "react";
import {
    Dialog,
    DialogContent,
    Box,
    Typography,
    TextField,
    Switch,
    Divider,
    Avatar,
    IconButton,
    Button,
    Tooltip,
    CircularProgress
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import PersonAddAltIcon from "@mui/icons-material/PersonAddAlt";
import CameraAltOutlinedIcon from "@mui/icons-material/CameraAltOutlined";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import SendIcon from "@mui/icons-material/Send";
import api from "../views/login_register/axios_client";
import { workspaceApi, workspaceStorage } from "../views/workspace/workSpaceAPi";

// ── color swatches ──────────────────────────────────────────────
const INTERFACE_COLORS = [
    { value: "default", color: "#e0e0e0" },
    { value: "emerald", color: "#22c55e" },
    { value: "blue", color: "#3b82f6" },
    { value: "green", color: "#16a34a" },
    { value: "yellow", color: "#eab308" },
    { value: "red", color: "#ef4444" },
    { value: "pink", color: "#ec4899" },
    { value: "indigo", color: "#6366f1" },
    { value: "slate", color: "#94a3b8" },
];

// ── sidebar nav items ───────────────────────────────────────────
const MY_ACCOUNT_ITEMS = ["Profile"];
const WORKSPACE_ITEMS = ["General"];

// ── reusable section label ──────────────────────────────────────
const SectionLabel = ({ children }) => (
    <Typography
        sx={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "text.disabled",
            mb: 0.5,
            mt: 2,
        }}
    >
        {children}
    </Typography>
);

// ── sidebar nav link ────────────────────────────────────────────
const NavItem = ({ label, active, onClick }) => (
    <Box
        onClick={onClick}
        sx={{
            px: 1.5,
            py: 0.75,
            borderRadius: 1.5,
            cursor: "pointer",
            fontSize: 14,
            fontWeight: active ? 600 : 400,
            color: active ? "text.primary" : "text.secondary",
            bgcolor: active ? "action.selected" : "transparent",
            "&:hover": { bgcolor: "action.hover" },
            transition: "background 0.15s",
            userSelect: "none",
        }}
    >
        {label}
    </Box>
);

// ── toggle row ──────────────────────────────────────────────────
const ToggleRow = ({ label, description, checked, onChange, disabled }) => (
    <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 2 }}>
        <Box>
            <Typography fontSize={14} fontWeight={500} color={disabled ? "text.disabled" : "text.primary"}>
                {label}
            </Typography>
            {description && (
                <Typography fontSize={12} color="text.disabled" mt={0.25}>
                    {description}
                </Typography>
            )}
        </Box>
        <Switch
            checked={checked}
            onChange={onChange}
            disabled={disabled}
            size="small"
            sx={{ flexShrink: 0, mt: 0.25 }}
        />
    </Box>
);

// ══════════════════════════════════════════════════════════════════
// PROFILE PANEL
// ══════════════════════════════════════════════════════════════════
function ProfilePanel() {
    const user = JSON.parse(localStorage.getItem('user'));
    const [firstName, setFirstName] = useState(user.first_name);
    const [lastName, setLastName] = useState(user.last_name);
    const [jobTitle, setJobTitle] = useState("");

    return (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="h6" fontWeight={700} fontSize={18}>
                Profile
            </Typography>

            {/* avatar */}
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Box sx={{ position: "relative" }}>
                    <Avatar
                        sx={{
                            width: 72,
                            height: 72,

                            fontSize: 28,
                            fontWeight: 700,
                        }}
                    >
                        {user.first_name?.charAt(0).toUpperCase()}
                    </Avatar>
                    {/* <Tooltip title="Change photo">
                        <IconButton
                            size="small"
                            sx={{
                                position: "absolute",
                                bottom: -4,
                                right: -4,
                                bgcolor: "background.paper",
                                border: "1.5px solid",
                                borderColor: "divider",
                                width: 24,
                                height: 24,
                                "&:hover": { bgcolor: "action.hover" },
                            }}
                        >
                            <CameraAltOutlinedIcon sx={{ fontSize: 13 }} />
                        </IconButton>
                    </Tooltip> */}
                </Box>
                <Box>
                    <Typography fontWeight={600} fontSize={15}>
                        {firstName} {lastName}
                    </Typography>
                    <Typography fontSize={12} color="text.secondary">
                        {user.email}
                    </Typography>
                </Box>
            </Box>

            <Divider />

            {/* name fields */}
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
                <Box>
                    <Typography fontSize={13} fontWeight={500} mb={0.75} color="text.secondary">
                        First name
                    </Typography>
                    <TextField
                        size="small"
                        fullWidth
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        sx={{ "& .MuiOutlinedInput-root": { borderRadius: 1.5 } }}
                    />
                </Box>
                <Box>
                    <Typography fontSize={13} fontWeight={500} mb={0.75} color="text.secondary">
                        Last name
                    </Typography>
                    <TextField
                        size="small"
                        fullWidth
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        sx={{ "& .MuiOutlinedInput-root": { borderRadius: 1.5 } }}
                    />
                </Box>
            </Box>

            {/* <Box>
        <Typography fontSize={13} fontWeight={500} mb={0.75} color="text.secondary">
          Job title
        </Typography>
        <TextField
          size="small"
          fullWidth
          placeholder="e.g. Marketing Manager"
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          sx={{ "& .MuiOutlinedInput-root": { borderRadius: 1.5 } }}
        />
      </Box> */}

            <Divider />

            {/* <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
        <Button
          variant="contained"
          size="small"
          disableElevation
          sx={{
            borderRadius: 1.5,
            textTransform: "none",
            fontWeight: 600,
            fontSize: 13,
            px: 2.5,
            bgcolor: "#111",
            "&:hover": { bgcolor: "#333" },
          }}
        >
          Save changes
        </Button>
      </Box> */}
        </Box>
    );
}

// ══════════════════════════════════════════════════════════════════
// GENERAL PANEL
// ══════════════════════════════════════════════════════════════════
function GeneralPanel({ onWorkspaceUpdated }) {
    const user = JSON.parse(localStorage.getItem('user') || 'null') || {};
    const activeWorkspace = workspaceStorage.getActive();
    const workspaceId = workspaceStorage.getActiveId();
    const [workspaceName, setWorkspaceName] = useState(activeWorkspace?.name || `${user.first_name || ""} ${user.last_name || ""}`.trim() || "Workspace");
    const [workspaceSaving, setWorkspaceSaving] = useState(false);
    const [workspaceMessage, setWorkspaceMessage] = useState("");
    const [workspaceError, setWorkspaceError] = useState("");
    // const [selectedColor, setSelectedColor] = useState("blue");
    // const [autopilot, setAutopilot] = useState(true);
    // const [autoContent, setAutoContent] = useState(true);
    // const [autoPublish, setAutoPublish] = useState(true);
    // const [approveBeforePost, setApproveBeforePost] = useState(false);
    const [approvalsToggle, setApprovalsToggle] = useState(true);
    const [toggleLoading, setToggleLoading] = useState(false);
    const [toggleError, setToggleError] = useState("");

    useEffect(() => {
        const latest = workspaceStorage.getActive();
        setWorkspaceName(latest?.name || `${user.first_name || ""} ${user.last_name || ""}`.trim() || "Workspace");
    }, [workspaceId, user.first_name, user.last_name]);

    useEffect(() => {
        const fetchToggle = async () => {
            if (!user?.id || !workspaceId) return;
            setToggleLoading(true);
            setToggleError("");
            try {
            const response = await api.post('/auth/user/get-toggle/', {
                user_id: user.id,
                workspace_id: workspaceId,
            });
            if (response.status === 200) {
                setApprovalsToggle(response.data.approval_toggle);
            }
            } catch (error) {
                setToggleError(error.response?.data?.error || "Could not load approval settings.");
            }
            setToggleLoading(false);
        };
        fetchToggle();
    }, [user?.id, workspaceId]);

    const handleToggle = async () => {
        if (!user?.id || !workspaceId) return;
        setToggleLoading(true);
        setToggleError("");
        try {
        const response = await api.post('/auth/user/change-toggle/', {
            user_id: user.id,
            workspace_id: workspaceId,
            toggle:!approvalsToggle,
        });
        if (response.status === 200) {
            setApprovalsToggle(response.data.approval_toggle);
        }
        } catch (error) {
            setToggleError(error.response?.data?.error || "Could not update approval settings.");
        }
        setToggleLoading(false);
    };

    const handleSaveWorkspace = async () => {
        const name = workspaceName.trim();
        if (!workspaceId || !name) {
            setWorkspaceError("Workspace name is required.");
            return;
        }
        setWorkspaceSaving(true);
        setWorkspaceError("");
        setWorkspaceMessage("");
        try {
            const updated = await workspaceApi.update(workspaceId, name);
            setWorkspaceName(updated.name);
            setWorkspaceMessage("Workspace name saved.");
            window.dispatchEvent(new CustomEvent("workspace-updated", { detail: updated }));
            onWorkspaceUpdated?.(updated);
        } catch (error) {
            setWorkspaceError(error.response?.data?.name?.[0] || error.response?.data?.error || error.response?.data?.detail || "Could not save workspace name.");
        } finally {
            setWorkspaceSaving(false);
        }
    };
    return (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="h6" fontWeight={700} fontSize={18} color="primary">
                General
            </Typography>

            {/* workspace name */}
            <Box>
                <Typography fontSize={15} fontWeight={600} mb={1.5}>
                    Workspace name
                </Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Avatar sx={{ bgcolor: "#3b82f6", width: 40, height: 40, fontWeight: 700 }}>S</Avatar>
                    <TextField
                        size="small"
                        fullWidth
                        value={workspaceName}
                        onChange={(e) => setWorkspaceName(e.target.value)}
                        sx={{ "& .MuiOutlinedInput-root": { borderRadius: 1.5 } }}
                    />
                    <Button
                        variant="contained"
                        disabled={workspaceSaving || !workspaceName.trim()}
                        onClick={handleSaveWorkspace}
                        sx={{ textTransform: "none", bgcolor: "#111", "&:hover": { bgcolor: "#333" }, minWidth: 86 }}
                    >
                        {workspaceSaving ? <CircularProgress size={16} color="inherit" /> : "Save"}
                    </Button>
                </Box>
                {workspaceMessage && <Typography sx={{ mt: 1, color: "#166534", fontSize: 12 }}>{workspaceMessage}</Typography>}
                {workspaceError && <Typography sx={{ mt: 1, color: "#b91c1c", fontSize: 12 }}>{workspaceError}</Typography>}
            </Box>

            {/* <Divider /> */}

            {/* interface color */}
            {/* <Box>
        <Typography fontSize={15} fontWeight={600} mb={0.5}>
          Interface Color
        </Typography>
        <Typography fontSize={12} color="text.secondary" mb={1.5}>
                    Changing this color would affect how Voice Spark looks like to everyone in this workspace.
        </Typography>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {INTERFACE_COLORS.map(({ value, color }) => (
            <Box
              key={value}
              onClick={() => setSelectedColor(value)}
              sx={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                bgcolor: color,
                cursor: "pointer",
                border: selectedColor === value ? "2.5px solid #111" : "2.5px solid transparent",
                outline: selectedColor === value ? "2px solid #fff" : "none",
                outlineOffset: "-4px",
                transition: "transform 0.15s, border 0.15s",
                "&:hover": { transform: "scale(1.12)" },
              }}
            />
          ))}
        </Box>
      </Box> */}

            {/* <Divider /> */}

            {/* white label */}
            {/* <Box
                sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 2,
                    opacity: 0.5,
                }}
            >
                <Box>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Typography fontSize={14} fontWeight={500} color="text.disabled">
                            White Label
                        </Typography>
                        <Box
                            sx={{
                                px: 0.8,
                                py: 0.1,
                                bgcolor: "#f3e8ff",
                                color: "#7c3aed",
                                fontSize: 10,
                                fontWeight: 700,
                                borderRadius: 1,
                                letterSpacing: "0.04em",
                            }}
                        >
                            Add-on
                        </Box>
                    </Box>
                    <Typography fontSize={12} color="text.disabled" mt={0.25}>
                    Replace Voice Spark branding with your own across workspace header and emails.
                    </Typography>
                    <Typography fontSize={12} color="text.disabled">
                        An active subscription is required to enable white label.
                    </Typography>
                </Box>
                <Switch size="small" disabled sx={{ flexShrink: 0, mt: 0.25 }} />
            </Box> */}

            {/* upgrade notice */}
            {/* <Box
                sx={{
                    bgcolor: "#fffbeb",
                    border: "1px solid #fde68a",
                    borderRadius: 2,
                    p: 1.5,
                    display: "flex",
                    gap: 1,
                }}
            >
                <Typography fontSize={18} lineHeight={1}>⚠️</Typography>
                <Typography fontSize={12} color="#92400e">
                    Workspace logo updates are now part of our paid White Label feature. To upload a new logo,
                    please upgrade to the White Label add-on.
                </Typography>
            </Box>

            <Divider /> */}

            {/* autopilot */}
            {/* <Box>
                <ToggleRow
                    label="Autopilot"
                    description="Voice Spark automatically generates and publishes your content. Turn off to pause both automated actions."
                    checked={autopilot}
                    onChange={(e) => setAutopilot(e.target.checked)}
                />
                {autopilot && (
                    <Box
                        sx={{
                            mt: 1.5,
                            ml: 1.5,
                            pl: 1.5,
                            borderLeft: "2px solid",
                            borderColor: "divider",
                            display: "flex",
                            flexDirection: "column",
                            gap: 1.5,
                        }}
                    >
                        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                                <AutorenewIcon />
                                <Typography fontSize={13} >
                                    Auto Content Generation
                                </Typography>
                            </Box>
                            <Switch
                                size="small"
                                checked={autoContent}
                                onChange={(e) => setAutoContent(e.target.checked)}
                            />
                        </Box>
                        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                                <SendIcon />
                                <Typography fontSize={13}>
                                    Auto Publishing
                                </Typography>
                            </Box>
                            <Switch
                                size="small"
                                checked={autoPublish}
                                onChange={(e) => setAutoPublish(e.target.checked)}
                            />
                        </Box>
                        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <Typography fontSize={13} fontWeight={500}>
                                Approve content before auto-posting
                            </Typography>
                            <Switch
                                size="small"
                                checked={approveBeforePost}
                                onChange={(e) => setApproveBeforePost(e.target.checked)}
                            />
                        </Box>
                    </Box>
                )}
            </Box> */}

            <Divider />

            {/* approvals */}
            <ToggleRow
                label="Approvals"
                description="Require your review on all of your content before it automatically publishes"
                checked={approvalsToggle}
                onChange={handleToggle}
                disabled={toggleLoading}
            />
            {toggleLoading && <CircularProgress size={16} sx={{ ml: 1 }} />}
            {toggleError && <Typography sx={{ color: "#b91c1c", fontSize: 12 }}>{toggleError}</Typography>}
            <Box component="ul" sx={{ mt: 1, pl: 2.5, fontSize: 13 }}>
                {["Nothing posts without your approval", "Easily make quick revisions", "Move content to Draft to revisit later"].map((item) => (
                    <Typography key={item} component="li" fontSize={13} sx={{ mb: 0.5 }}>
                        {item}
                    </Typography>
                ))}
            </Box>
        </Box>
    );
}

// ══════════════════════════════════════════════════════════════════
// MAIN MODAL
// ══════════════════════════════════════════════════════════════════
export default function SettingsModal({ open = true, onClose }) {
    const [activeTab, setActiveTab] = useState("Profile");
    const [workspaceLabel, setWorkspaceLabel] = useState(() => workspaceStorage.getActive()?.name || "Workspace");

    useEffect(() => {
        const refreshLabel = () => setWorkspaceLabel(workspaceStorage.getActive()?.name || "Workspace");
        refreshLabel();
        window.addEventListener("workspace-updated", refreshLabel);
        return () => window.removeEventListener("workspace-updated", refreshLabel);
    }, [open]);

    const renderPanel = () => {
        if (activeTab === "Profile") return <ProfilePanel />;
        if (activeTab === "General") return <GeneralPanel onWorkspaceUpdated={(workspace) => setWorkspaceLabel(workspace.name)} />;
        return null;
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth={false}
            PaperProps={{
                sx: {
                    width: 860,
                    maxWidth: "95vw",
                    height: 600,
                    maxHeight: "90vh",
                    borderRadius: 3,
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                },
            }}
        >
            {/* ── header ── */}
            <Box
                sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    px: 3,
                    py: 1.5,
                    borderBottom: "1px solid",
                    borderColor: "divider",
                    flexShrink: 0,
                }}
            >
                <Typography fontWeight={700} fontSize={15}>
                    Settings
                </Typography>
                {/* <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Button
                        size="small"
                        startIcon={<PersonAddAltIcon fontSize="small" />}
                        variant="outlined"
                        sx={{
                            textTransform: "none",
                            borderRadius: 2,
                            fontSize: 13,
                            fontWeight: 500,
                            borderColor: "divider",
                            color: "text.primary",
                            "&:hover": { borderColor: "text.secondary" },
                        }}
                    >
                        Invite members
                    </Button>
                    <IconButton size="small" onClick={onClose}>
                        <CloseIcon fontSize="small" />
                    </IconButton>
                </Box> */}
            </Box>

            {/* ── body ── */}
            <Box sx={{ display: "flex", flex: 1, overflow: "hidden" }}>
                {/* sidebar */}
                <Box
                    sx={{
                        width: 200,
                        flexShrink: 0,
                        borderRight: "1px solid",
                        borderColor: "divider",
                        px: 1.5,
                        py: 2,
                        overflowY: "auto",
                    }}
                >
                    <SectionLabel>My Account</SectionLabel>
                    {MY_ACCOUNT_ITEMS.map((item) => (
                        <NavItem
                            key={item}
                            label={item}
                            active={activeTab === item && ["Account", "Profile", "Notifications"].includes(item)}
                            onClick={() => setActiveTab(item)}
                        />
                    ))}

                    <SectionLabel>{workspaceLabel}</SectionLabel>
                    {WORKSPACE_ITEMS.map((item) => (
                        <NavItem
                            key={item}
                            label={item}
                            active={activeTab === item}
                            onClick={() => setActiveTab(item)}
                        />
                    ))}

                    {/* <Box sx={{ mt: 2 }}>
            <NavItem label="Danger Zone" active={false} onClick={() => setActiveTab("Danger Zone")} />
          </Box> */}
                </Box>

                {/* content */}
                <Box sx={{ flex: 1, overflowY: "auto", px: 4, py: 3 }}>
                    {activeTab === "Profile" || activeTab === "General" ? (
                        renderPanel()
                    ) : (
                        <Box
                            sx={{
                                height: "100%",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                color: "text.disabled",
                            }}
                        >
                            <Typography fontSize={14}>{activeTab} settings coming soon</Typography>
                        </Box>
                    )}
                </Box>
            </Box>
        </Dialog>
    );
}
