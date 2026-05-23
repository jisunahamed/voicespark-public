import React from 'react';
import { Typography } from '@mui/material';
import { LegalList, LegalSection, LegalShell, PlatformLinks } from './LegalLayout';

const effectiveDate = 'May 8, 2026';

export default function PrivacyPolicy() {
  return (
    <LegalShell
      eyebrow="Privacy Policy"
      title="Privacy Policy"
      subtitle="This policy explains how Voice Spark AI handles account, workspace, brand, content, and connected social platform data when teams plan, generate, approve, schedule, and publish social content."
      updatedAt={effectiveDate}
    >
      <LegalSection title="Who We Are">
        <Typography>
          Voice Spark AI provides content planning, AI-assisted creative generation, scheduling, approval, analytics, and publishing tools for businesses and agencies. This policy applies when you use our website, app, onboarding flow, workspace tools, brand kit, media library, campaign planner, or connected social publishing features.
        </Typography>
      </LegalSection>

      <LegalSection title="Information We Collect">
        <LegalList
          items={[
            'Account and workspace information, such as name, email address, business name, role, workspace settings, team membership, and authentication details.',
            'Brand and source materials, including website URLs, business descriptions, brand voice, logo, fonts, colors, product photos, reference images, competitor/source materials, and content preferences you upload or approve.',
            'Generated and planned content, including campaign topics, captions, images, media references, draft status, schedules, approvals, publishing history, and performance notes.',
            'Connected social account data, such as authorized Facebook Page, Instagram Business or Professional account, LinkedIn profile or Page, and X account identifiers, access tokens, permission scopes, selected destinations, publishing status, and permitted analytics returned by those platforms.',
            'Usage, device, log, and security information, including browser type, IP-derived location, app actions, errors, API events, and audit records needed to run and protect the service.',
          ]}
        />
      </LegalSection>

      <LegalSection title="Social Platform Permissions">
        <Typography>
          We request only the permissions needed for the features you choose. Connecting a social account does not give us your social platform password, and we do not publish to a destination unless you select that destination and create, approve, or schedule content through Voice Spark AI.
        </Typography>
        <LegalList
          items={[
            'For Facebook and Instagram, we may request permissions to identify the Pages, Instagram Business or Professional accounts, media, publishing destinations, post status, and insights that you authorize through Meta.',
            'For LinkedIn, we may request permissions to identify authorized profiles or organization Pages, create or manage posts, retrieve publishing status, and read permitted Page or post analytics.',
            'For X, we may request permissions to connect your account, prepare and publish posts you approve, read account or post metadata where authorized, and maintain publishing status.',
          ]}
        />
        <PlatformLinks />
      </LegalSection>

      <LegalSection title="How We Use Information">
        <LegalList
          items={[
            'To create and secure your account, workspace, onboarding flow, connected accounts, and team access.',
            'To analyze your business website, brand kit, media library, and preferences so content plans, post topics, captions, visuals, blogs, and campaigns are specific to your brand.',
            'To generate draft content and reference image instructions using your approved brand assets, logo, product imagery, fonts, tone, and campaign goals.',
            'To publish, schedule, update, or check the status of content only for the social accounts and destinations you authorize.',
            'To provide customer support, diagnose errors, maintain audit logs, prevent abuse, comply with law, and improve product reliability using aggregated or de-identified usage patterns where appropriate.',
          ]}
        />
      </LegalSection>

      <LegalSection title="How We Share Information">
        <Typography>
          We do not sell your connected social platform data. We share information only as needed to provide the service, follow your instructions, and meet legal or security obligations.
        </Typography>
        <LegalList
          items={[
            'With Facebook, Instagram, LinkedIn, X, and other connected services when you ask us to authenticate, publish, schedule, retrieve status, or access permitted analytics.',
            'With service providers that host infrastructure, store media, process AI requests, monitor errors, send email, or provide support, under confidentiality and data protection obligations.',
            'With your workspace members according to the roles and permissions configured in your workspace.',
            'When required to comply with law, enforce our terms, protect users, prevent abuse, or respond to valid legal requests.',
          ]}
        />
      </LegalSection>

      <LegalSection title="Your Controls">
        <LegalList
          items={[
            'You can edit or delete brand profile fields, source materials, media assets, generated drafts, campaign topics, and scheduled posts inside the product where the feature is available.',
            'You can disconnect social accounts in Voice Spark AI and can also revoke app access directly from Facebook, Instagram, LinkedIn, or X account settings.',
            'You can review generated content before publishing and can cancel or change scheduled content before it is sent, subject to platform timing and API limits.',
            'You may request access, correction, export, or deletion of personal information by contacting us.',
          ]}
        />
      </LegalSection>

      <LegalSection title="Retention And Deletion">
        <Typography>
          We keep information for as long as needed to provide the service, maintain accurate workspace records, comply with legal obligations, resolve disputes, prevent fraud, and support security. Connected social tokens are retained only while the account remains connected or as otherwise required for security and audit purposes. If you delete a workspace or request deletion, we will remove or de-identify related data unless retention is required by law, security, billing, backups, or platform compliance obligations.
        </Typography>
      </LegalSection>

      <LegalSection title="Security">
        <Typography>
          We use administrative, technical, and organizational safeguards designed to protect account data, connected platform tokens, media assets, and workspace content. No online service can guarantee absolute security, so you should protect your login credentials, use strong passwords, and promptly disconnect accounts or notify us if you suspect unauthorized access.
        </Typography>
      </LegalSection>

      <LegalSection title="Children And Sensitive Content">
        <Typography>
          Voice Spark AI is intended for business users and is not directed to children under 13. Do not upload sensitive personal information, regulated data, or confidential third-party materials unless you have the right and a lawful basis to do so.
        </Typography>
      </LegalSection>

      <LegalSection title="Changes And Contact">
        <Typography>
          We may update this policy as our product, integrations, laws, or platform requirements change. If changes are material, we will provide notice through the app or another reasonable channel. For privacy questions, account deletion, or platform permission questions, contact us at support@voicesparkai.com.
        </Typography>
      </LegalSection>
    </LegalShell>
  );
}
