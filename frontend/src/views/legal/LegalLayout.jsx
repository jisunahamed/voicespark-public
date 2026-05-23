import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Chip,
  Container,
  Divider,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';

const cardSx = {
  p: { xs: 2.5, sm: 3.5, md: 4 },
  border: '1px solid rgba(255,255,255,0.11)',
  borderRadius: '28px',
  background: 'linear-gradient(145deg, rgba(255,255,255,0.09), rgba(255,255,255,0.045))',
  boxShadow: '0 24px 80px rgba(0,0,0,0.22)',
  backdropFilter: 'blur(18px)',
};

export function LegalShell({ eyebrow, title, subtitle, updatedAt, children }) {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        color: '#f8fbff',
        background:
          'radial-gradient(circle at 12% 8%, rgba(168,85,247,0.42), transparent 32%), radial-gradient(circle at 88% 12%, rgba(59,130,246,0.32), transparent 30%), linear-gradient(135deg, #080813 0%, #121124 48%, #080813 100%)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          opacity: 0.35,
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
          maskImage: 'linear-gradient(to bottom, rgba(0,0,0,0.9), transparent 72%)',
          pointerEvents: 'none',
        }}
      />
      <Container maxWidth="lg" sx={{ position: 'relative', py: { xs: 3, md: 5 } }}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          justifyContent="space-between"
          sx={{ mb: { xs: 5, md: 8 } }}
        >
          <Link component={RouterLink} to="/" underline="none" sx={{ color: 'inherit' }}>
            <Stack direction="row" spacing={1.25} alignItems="center">
              <Box
                sx={{
                  width: 42,
                  height: 42,
                  borderRadius: '15px',
                  display: 'grid',
                  placeItems: 'center',
                  fontWeight: 900,
                  color: '#fff',
                  background: 'linear-gradient(135deg, #8b5cf6, #4f46e5)',
                  boxShadow: '0 18px 44px rgba(139,92,246,0.38)',
                }}
              >
                VS
              </Box>
              <Typography sx={{ fontWeight: 900, letterSpacing: 0, fontSize: 19 }}>
                Voice Spark AI
              </Typography>
            </Stack>
          </Link>
          <Button
            component={RouterLink}
            to="/"
            startIcon={<ArrowBackRoundedIcon />}
            sx={{
              color: '#f8fbff',
              border: '1px solid rgba(255,255,255,0.18)',
              borderRadius: '999px',
              px: 2.25,
              textTransform: 'none',
              background: 'rgba(255,255,255,0.07)',
              '&:hover': { background: 'rgba(255,255,255,0.13)' },
            }}
          >
            Back to Home
          </Button>
        </Stack>

        <Stack spacing={2.25} sx={{ maxWidth: 860, mb: { xs: 4, md: 6 } }}>
          <Chip
            label={eyebrow}
            sx={{
              width: 'fit-content',
              color: '#efe7ff',
              borderColor: 'rgba(196,181,253,0.45)',
              background: 'rgba(139,92,246,0.18)',
              fontWeight: 800,
            }}
            variant="outlined"
          />
          <Typography
            component="h1"
            sx={{
              fontSize: { xs: 40, md: 72 },
              lineHeight: 0.95,
              fontWeight: 950,
              letterSpacing: 0,
            }}
          >
            {title}
          </Typography>
          <Typography sx={{ color: 'rgba(248,251,255,0.76)', fontSize: { xs: 16, md: 19 }, maxWidth: 780 }}>
            {subtitle}
          </Typography>
          <Typography sx={{ color: 'rgba(248,251,255,0.56)', fontSize: 13 }}>
            Effective date: {updatedAt}
          </Typography>
        </Stack>

        <Stack spacing={2.5}>{children}</Stack>
      </Container>
    </Box>
  );
}

export function LegalSection({ title, children }) {
  return (
    <Box component="section" sx={cardSx}>
      <Typography component="h2" sx={{ fontSize: { xs: 22, md: 28 }, fontWeight: 900, mb: 2, letterSpacing: 0 }}>
        {title}
      </Typography>
      <Stack spacing={1.4} sx={{ color: 'rgba(248,251,255,0.78)', fontSize: 15.5, lineHeight: 1.75 }}>
        {children}
      </Stack>
    </Box>
  );
}

export function LegalList({ items }) {
  return (
    <Box component="ul" sx={{ pl: 2.6, m: 0 }}>
      {items.map((item) => (
        <Typography component="li" key={item} sx={{ mb: 0.8, color: 'rgba(248,251,255,0.78)', lineHeight: 1.75 }}>
          {item}
        </Typography>
      ))}
    </Box>
  );
}

export function PlatformLinks() {
  return (
    <Stack direction="row" useFlexGap flexWrap="wrap" spacing={1.2} sx={{ pt: 0.5 }}>
      {[
        ['Meta Privacy Policy', 'https://www.facebook.com/privacy/policy/'],
        ['LinkedIn Marketing API rules', 'https://learn.microsoft.com/en-us/linkedin/marketing/restricted-use-cases'],
        ['X Developer Policy', 'https://docs.x.com/developer-terms/policy'],
      ].map(([label, href]) => (
        <Button
          key={href}
          href={href}
          target="_blank"
          rel="noreferrer"
          sx={{
            color: '#f4edff',
            border: '1px solid rgba(196,181,253,0.34)',
            borderRadius: '999px',
            textTransform: 'none',
            px: 1.8,
            background: 'rgba(255,255,255,0.06)',
          }}
        >
          {label}
        </Button>
      ))}
    </Stack>
  );
}

export function LegalDivider() {
  return <Divider sx={{ borderColor: 'rgba(255,255,255,0.11)' }} />;
}
