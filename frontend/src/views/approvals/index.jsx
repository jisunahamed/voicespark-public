import { useState, useEffect } from "react";
import axios from "axios";
import {
  Box,
  Typography,
  Button,
  Chip,
  IconButton,
  Stack,
  Menu,
  MenuItem,
  Divider,
  Card,
  CardContent,
  Skeleton,
  alpha,
  CircularProgress
} from "@mui/material";
import TopBar from "../../TopBar";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import TuneIcon from "@mui/icons-material/Tune";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import InstagramIcon from "@mui/icons-material/Instagram";
import FacebookIcon from "@mui/icons-material/Facebook";
import LinkedInIcon from "@mui/icons-material/LinkedIn";
import YouTubeIcon from "@mui/icons-material/YouTube";
import XIcon from "@mui/icons-material/X";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import FilterListIcon from "@mui/icons-material/FilterList";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import config from "../../config";
import { useNavigate } from "react-router-dom";
import api from "../login_register/axios_client";
import { workspaceStorage } from "../workspace/workSpaceAPi";

const platformIconMap = {
  instagram: <InstagramIcon sx={{ fontSize: 18, color: "#E1306C" }} />,
  facebook: <FacebookIcon sx={{ fontSize: 18, color: "#1877F2" }} />,
  linkedin: <LinkedInIcon sx={{ fontSize: 18, color: "#0A66C2" }} />,
  youtube: <YouTubeIcon sx={{ fontSize: 18, color: "#FF0000" }} />,
  twitter: <XIcon sx={{ fontSize: 16, color: "#000" }} />,
};

// ─── PostCard ────────────────────────────────────────────────────────────────

function PostCard({ key, post }) {
  const navigate = useNavigate()
  const isPosted = post.approval === "posted";
  
  // Normalise schedule_date → readable string
  const formattedDate = post.schedule_date
    ? new Date(post.schedule_date).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
    : "Unscheduled";

  const platforms = post.platforms ?? [];
  const postType = post.post_type ?? "Post";
  const caption = post.caption ?? "";

  const image_url = post.image;
  return (
    <Card
      elevation={0}
      onClick={()=>{navigate("/voice-spark-editor/"+post.id)}}
      sx={{
        border: isPosted ? "1.5px solid #22C55E" : "1px solid rgba(0,0,0,0.09)",
        borderRadius: 3,
        overflow: "hidden",
        transition: "box-shadow 0.2s, transform 0.2s",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: "0 8px 24px rgba(0,0,0,0.10)",
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 1.5,
          pt: 1.5,
          pb: 0.5,
        }}
      >
        <Stack direction="row" spacing={0.4} alignItems="center">
          {platforms.map((p) => (
            <Box key={p} sx={{ lineHeight: 0 }}>
              {platformIconMap[p] ?? null}
            </Box>
          ))}
          <Chip
            label={isPosted ? "Posted" : "Scheduled"}
            size="small"
            sx={{
              ml: 0.5,
              height: 18,
              fontSize: 10,
              bgcolor: isPosted ? alpha("#22C55E", 0.12) : alpha("#2563EB", 0.1),
              color: isPosted ? "#15803D" : "#2563EB",
              "& .MuiChip-label": { px: 1 },
            }}
          />
        </Stack>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontSize: 11 }}
        >
          {formattedDate}
        </Typography>
      </Box>

      {/* Media */}
      <Box
        sx={{
          mx: 1.5,
          borderRadius: 2,
          overflow: "hidden",
          height: 210,
          position: "relative",
          bgcolor: "#e5e7eb",
        }}
      >
        {image_url ? (
          <Box
            component="img"
            src={image_url}
            alt="post visual"
            sx={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
            }}
          />
        ) : (
          // Placeholder when no image_url
          <Box
            sx={{
              width: "100%",
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "#f3f4f6",
            }}
          >
            <Typography fontSize={12} color="text.disabled">
              No preview
            </Typography>
          </Box>
        )}

        {postType === "Video" && (
          <Box
            sx={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%,-50%)",
            }}
          >
            <PlayCircleOutlineIcon
              sx={{ fontSize: 44, color: "rgba(255,255,255,0.85)" }}
            />
          </Box>
        )}

        {isPosted && (
          <Box
            sx={{
              position: "absolute",
              top: 8,
              right: 8,
              bgcolor: "#22C55E",
              borderRadius: "50%",
              width: 26,
              height: 26,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <CheckCircleOutlineIcon sx={{ fontSize: 16, color: "white" }} />
          </Box>
        )}
      </Box>

      {/* Caption */}
      <CardContent sx={{ pt: 1, pb: 0.5, px: 1.5 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontSize: 11.5, lineHeight: 1.5 }}
        >
          {caption.length > 70 ? caption.slice(0, 70) + "…" : caption}{" "}
          {caption.length > 70 && (
            <Typography
              component="span"
              variant="caption"
              sx={{ color: "primary.main", cursor: "pointer", fontSize: 11.5 }}
            >
              more
            </Typography>
          )}
        </Typography>
      </CardContent>

      <Box sx={{ display: "flex", gap: 1, px: 1.5, pb: 1.5, pt: 1 }}>
        <Button fullWidth size="small" variant="outlined" sx={{ fontSize: 11, py: 0.5, borderRadius: 20, textTransform: "none" }}>
          Open
        </Button>
      </Box>
    </Card>
  );
}

// ─── PostCard Skeleton ────────────────────────────────────────────────────────

function PostCardSkeleton() {

  return (
    <Card
      elevation={0}
      sx={{ border: "1px solid rgba(0,0,0,0.09)", borderRadius: 3, overflow: "hidden" }}
    >
      <Box sx={{ px: 1.5, pt: 1.5, pb: 0.5, display: "flex", justifyContent: "space-between" }}>
        <Skeleton variant="rounded" width={100} height={18} />
        <Skeleton variant="rounded" width={70} height={14} />
      </Box>
      <Box sx={{ mx: 1.5 }}>
        <Skeleton variant="rounded" height={210} />
      </Box>
      <CardContent sx={{ pt: 1, pb: 0.5, px: 1.5 }}>
        <Skeleton variant="text" width="90%" />
        <Skeleton variant="text" width="60%" />
      </CardContent>
      <Box sx={{ display: "flex", gap: 1, px: 1.5, pb: 1.5, pt: 1 }}>
        <Skeleton variant="rounded" height={30} sx={{ flex: 1, borderRadius: 20 }} />
        <Skeleton variant="rounded" height={30} sx={{ flex: 1, borderRadius: 20 }} />
      </Box>
    </Card>
  );
}


function PostsSection({ posts }) {
  const [collapsed, setCollapsed] = useState(false);
  const pendingCount = posts.length;

  return (
    <Box sx={{ mb: 4 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2.5, flexWrap: "wrap" }}>
        <IconButton
          size="small"
          onClick={() => setCollapsed(!collapsed)}
          sx={{ transform: collapsed ? "rotate(-90deg)" : "rotate(0)", transition: "transform 0.2s" }}
        >
          <KeyboardArrowDownIcon fontSize="small" />
        </IconButton>
        <Typography variant="h6" sx={{ fontWeight: 700, fontSize: 20 }}>
          Approved for Publishing
        </Typography>
        <Divider orientation="vertical" flexItem sx={{ height: 18, alignSelf: "center" }} />
        {/* <Button
          size="small"
          startIcon={<CheckCircleOutlineIcon sx={{ fontSize: 15 }} />}
          sx={{
            fontSize: 13, fontWeight: 600, px: 1.5, borderRadius: 20,
            color: "primary.main", border: "1px solid", borderColor: alpha("#2563EB", 0.3),
            bgcolor: alpha("#2563EB", 0.04), "&:hover": { bgcolor: alpha("#2563EB", 0.1) },
          }}
        >
          Approve All
        </Button> */}
        <Button
          size="small"
          startIcon={<ErrorOutlineIcon sx={{ fontSize: 15 }} />}
          sx={{
            fontSize: 13, fontWeight: 600, px: 1.5, borderRadius: 20,
            color: "text.secondary", border: "1px solid rgba(0,0,0,0.12)",
            "&:hover": { bgcolor: "rgba(0,0,0,0.05)" },
          }}
        >
          {pendingCount} scheduled/posted
        </Button>
      </Box>

      {!collapsed && (
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: 2 }}>
          {posts.map((post) => (
            <PostCard
              key={post.nano_banana_id}
              post={{
                id: post.nano_banana_id,
                image: post.imageurl || post.image_url,
                time: new Date(post.scheduled_at).toLocaleString(),
                caption: post.title || post.caption,
                platforms: post.platforms || post.approved_platforms || [],
                approval: post.approval,
                schedule_date: post.scheduled_at,
              }}
            />
          ))}
        </Box>
      )}
    </Box>
  );
}

// ─── ApprovalsPage ────────────────────────────────────────────────────────────

export default function ApprovalsPage() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterAnchor, setFilterAnchor] = useState(null);
  const user = JSON.parse(localStorage.getItem('user'));
  const workspaceId = workspaceStorage.getActiveId();
  useEffect(() => {
    let cancelled = false;
    const fetchApprovals = async () => {
      try {
        setLoading(true);
        setError(null);
        const { data } = await api.post("/nano-banana/get-approval-post/", {
          user_id: user.id,
          workspace_id:workspaceId
        });
        const nextPosts = Array.isArray(data.data) ? data.data : [];
        if (!cancelled) setPosts(nextPosts);
      } catch (err) {
        console.error("Failed to fetch approvals:", err);
        if (!cancelled) setError("Failed to load approvals. Please try again.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchApprovals();
    return () => {
      cancelled = true;
    };
  }, [user?.id, workspaceId]);

  const totalPending = posts.length;

  return (
    <Box>
      <TopBar title="Approvals" />
      <Box
        sx={{ minHeight: "100vh", px: { xs: 2, md: 4 }, py: 3 }}
      >
        {/* Page header */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 4,
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Typography
            variant="h4"
            sx={{
              fontWeight: 800,
              fontSize: { xs: 26, md: 34 },
              letterSpacing: -0.5,
            }}
          >
            Approvals
          </Typography>
          <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap">
            {/* <Button
              variant="outlined"
              size="small"
              startIcon={<TuneIcon fontSize="small" />}
              endIcon={<KeyboardArrowDownIcon fontSize="small" />}
              onClick={(e) => setFilterAnchor(e.currentTarget)}
              sx={{
                fontSize: 13,
                color: "text.secondary",
                borderColor: "rgba(0,0,0,0.15)",
                bgcolor: "background.paper",
                borderRadius: 20,
              }}
            >
              Filters
            </Button> */}
            {/* <Menu
              anchorEl={filterAnchor}
              open={Boolean(filterAnchor)}
              onClose={() => setFilterAnchor(null)}
              PaperProps={{ sx: { borderRadius: 2, mt: 1, minWidth: 150 } }}
            >
              {["All", "Videos", "Posts", "Pending", "Approved"].map((f) => (
                <MenuItem
                  key={f}
                  onClick={() => setFilterAnchor(null)}
                  sx={{ fontSize: 13 }}
                >
                  {f}
                </MenuItem>
              ))}
            </Menu> */}
            {/* <Button
              variant="outlined"
              size="small"
              startIcon={<FolderOpenIcon fontSize="small" />}
              sx={{
                fontSize: 13,
                color: "text.secondary",
                borderColor: "rgba(0,0,0,0.15)",
                bgcolor: "background.paper",
                borderRadius: 20,
              }}
            >
              Select Files
            </Button> */}
            {/* <Button
              variant="outlined"
              size="small"
              startIcon={<CheckCircleOutlineIcon fontSize="small" />}
              sx={{
                fontSize: 13,
                color: "primary.main",
                borderColor: alpha("#2563EB", 0.4),
                bgcolor: alpha("#2563EB", 0.04),
                borderRadius: 20,
                "&:hover": { bgcolor: alpha("#2563EB", 0.1) },
              }}
            >
              Approve All
            </Button> */}
            {/* <Button
              variant="outlined"
              size="small"
              startIcon={<ErrorOutlineIcon fontSize="small" />}
              sx={{
                fontSize: 13,
                color: "text.secondary",
                borderColor: "rgba(0,0,0,0.15)",
                bgcolor: "background.paper",
                borderRadius: 20,
              }}
            >
              {totalPending} to Review
            </Button> */}
          </Stack>
        </Box>

        {/* Loading skeletons */}
        {loading && (
          <Box>
            {[1, 2].map((section) => (
              <Box key={section} sx={{ mb: 4 }}>
                <Skeleton variant="rounded" width={200} height={28} sx={{ mb: 2.5 }} />
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))",
                    gap: 2,
                  }}
                >
                  {[1, 2, 3, 4].map((i) => (
                    <PostCardSkeleton key={i} />
                  ))}
                </Box>
              </Box>
            ))}
          </Box>
        )}

        {/* Error state */}
        {!loading && error && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "40vh",
              gap: 2,
            }}
          >
            <ErrorOutlineIcon sx={{ fontSize: 40, color: "#EF4444" }} />
            <Typography fontWeight={600} color="error">
              {error}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={() => window.location.reload()}
              sx={{ borderRadius: 20 }}
            >
              Retry
            </Button>
          </Box>
        )}

        {/* Empty state */}
        {!loading && !error && totalPending === 0 && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "50vh",
              gap: 2,
            }}
          >
            <Box
              sx={{
                width: 56,
                height: 56,
                borderRadius: "50%",
                bgcolor: "#dcfce7",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CheckCircleOutlineIcon sx={{ fontSize: 28, color: "#16a34a" }} />
            </Box>
            <Typography fontWeight={700} fontSize={22} color="text.primary">
              No approved posts yet.
            </Typography>
            <Typography color="text.secondary" fontSize={14}>
              Approve posts from Calendar and they will appear here for publishing status.
            </Typography>
            <Stack direction="row" spacing={1.5}>
              <Button
                variant="outlined"
                size="small"
                startIcon={<CalendarTodayIcon fontSize="small" />}
                onClick={() => window.location.assign("/calendar")}
                sx={{
                  fontSize: 13,
                  color: "text.secondary",
                  borderColor: "rgba(0,0,0,0.2)",
                  borderRadius: 20,
                  bgcolor: "background.paper",
                  textTransform: "none",
                }}
              >
                Go to Calendar
              </Button>
            </Stack>
          </Box>
        )}

        {/* Campaign sections */}
        {!loading && !error && totalPending !== 0 && (
          <PostsSection posts={posts} />
        )}
      </Box>
    </Box>
  );
}
