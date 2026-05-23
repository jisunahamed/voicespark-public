import React from 'react';
import { Typography } from '@mui/material';
import { LegalList, LegalSection, LegalShell, PlatformLinks } from './LegalLayout';

const effectiveDate = 'May 8, 2026';

export default function TermsAndConditions() {
  return (
    <LegalShell
      eyebrow="Terms and Conditions"
      title="Terms and Conditions"
      subtitle="These terms govern your use of Voice Spark AI, including onboarding, brand kit management, AI-assisted content generation, social account connections, approvals, scheduling, and publishing."
      updatedAt={effectiveDate}
    >
      <LegalSection title="Acceptance">
        <Typography>
          By accessing or using Voice Spark AI, creating an account, connecting a social platform, or inviting a team member, you agree to these Terms and our Privacy Policy. If you use Voice Spark AI for a company, agency, client, or other organization, you represent that you have authority to bind that organization.
        </Typography>
      </LegalSection>

      <LegalSection title="The Service">
        <Typography>
          Voice Spark AI helps teams analyze business information, build a brand profile, maintain a brand kit, plan campaigns, generate draft topics, captions, visuals, blogs, and social posts, and publish or schedule approved content to connected social accounts.
        </Typography>
        <LegalList
          items={[
            'AI-generated content is a draft aid. You are responsible for reviewing, editing, approving, and verifying accuracy before publishing.',
            'The service may rely on third-party AI providers, hosting providers, storage services, and social platform APIs.',
            'Features may change as platform permissions, API rules, model availability, app review status, or technical requirements change.',
          ]}
        />
      </LegalSection>

      <LegalSection title="Accounts And Workspace Responsibilities">
        <LegalList
          items={[
            'You must provide accurate account and workspace information and keep login credentials secure.',
            'You are responsible for all activity under your account, workspace, connected accounts, and invited team members.',
            'You must have the legal right to upload logos, product images, fonts, brand materials, website content, customer data, source materials, and social account credentials or permissions.',
            'You must not use another person or organization’s social account, assets, or platform permissions without authorization.',
          ]}
        />
      </LegalSection>

      <LegalSection title="Social Platform Integrations">
        <Typography>
          When you connect Facebook, Instagram, LinkedIn, X, or another social platform, you authorize Voice Spark AI to use the approved permission scopes to provide the connected features you select, such as account selection, content publishing, scheduling, post status checks, and permitted analytics.
        </Typography>
        <LegalList
          items={[
            'You must comply with the applicable platform terms, developer policies, automation rules, content rules, and brand guidelines.',
            'We are not affiliated with, endorsed by, sponsored by, or officially partnered with Meta, Facebook, Instagram, LinkedIn, or X unless expressly stated in writing.',
            'Platform access can be limited, suspended, revoked, delayed, or changed by the platform provider, and we are not responsible for platform API outages, app review delays, or permission changes.',
            'You must provide any required notices and obtain any required consents from your users, customers, employees, clients, or audiences before publishing content or processing their information.',
          ]}
        />
        <PlatformLinks />
      </LegalSection>

      <LegalSection title="Publishing And Approval">
        <LegalList
          items={[
            'You are responsible for the final content that is posted, including claims, pricing, promotions, images, logos, fonts, links, hashtags, disclosures, and targeting decisions.',
            'Before publishing, you should check that each post is accurate, lawful, non-infringing, not misleading, and compliant with each destination platform’s rules.',
            'If you schedule content, you authorize us to submit that content to the selected platform at the scheduled time, subject to platform availability, permissions, rate limits, and technical conditions.',
            'We may block, pause, or remove content or connected features if we reasonably believe they violate these Terms, law, platform rules, security requirements, or the rights of others.',
          ]}
        />
      </LegalSection>

      <LegalSection title="Prohibited Uses">
        <LegalList
          items={[
            'Using the service for spam, platform manipulation, fake engagement, deceptive activity, impersonation, phishing, malware, scraping, surveillance, or unauthorized automation.',
            'Publishing unlawful, infringing, defamatory, discriminatory, harassing, sexually exploitative, violent, misleading, or otherwise harmful content.',
            'Making medical, financial, legal, employment, political, or regulated product claims without required review, substantiation, licensing, disclosures, and approvals.',
            'Selling, transferring, exporting, combining, or using platform data in a way that violates platform rules or a person’s reasonable privacy expectations.',
            'Attempting to bypass rate limits, access controls, app review restrictions, subscription limits, security protections, or connected platform permission scopes.',
          ]}
        />
      </LegalSection>

      <LegalSection title="User Content And Intellectual Property">
        <Typography>
          You retain ownership of the materials you upload and the content you create through your workspace. You grant Voice Spark AI a limited license to host, process, reproduce, modify, display, and transmit that content as needed to operate the service, generate drafts, provide previews, publish approved posts, troubleshoot issues, and comply with your instructions.
        </Typography>
        <Typography>
          Voice Spark AI, including its software, workflows, interface, templates, and product names, remains owned by us or our licensors. You may not copy, resell, reverse engineer, or misuse the service except as allowed by law or agreed in writing.
        </Typography>
      </LegalSection>

      <LegalSection title="Plans, Trials, And Billing">
        <Typography>
          If a paid plan, usage limit, free trial, or subscription applies, the plan terms shown at signup, checkout, invoice, or in the app also apply. You are responsible for approved charges, applicable taxes, and keeping billing information current. We may suspend or limit access for unpaid amounts, abuse, excessive usage, or policy violations.
        </Typography>
      </LegalSection>

      <LegalSection title="Third-Party Services">
        <Typography>
          The service can include links, integrations, APIs, models, storage, and data from third parties. Your use of those third-party services may be governed by their own terms and policies. We are not responsible for third-party services, platform review decisions, API changes, outages, or content removal decisions.
        </Typography>
      </LegalSection>

      <LegalSection title="Disclaimers And Liability">
        <Typography>
          Voice Spark AI is provided on an “as is” and “as available” basis. We do not guarantee that AI outputs will be accurate, complete, unique, lawful for your use, or accepted by any social platform. To the maximum extent permitted by law, we disclaim implied warranties and will not be liable for indirect, incidental, special, consequential, exemplary, or punitive damages, or for lost profits, lost data, lost goodwill, platform penalties, or publication errors.
        </Typography>
      </LegalSection>

      <LegalSection title="Indemnity">
        <Typography>
          You agree to defend, indemnify, and hold Voice Spark AI harmless from claims, losses, liabilities, damages, costs, and expenses arising from your content, connected accounts, workspace activity, breach of these Terms, violation of law, or violation of a third-party or platform right.
        </Typography>
      </LegalSection>

      <LegalSection title="Termination And Changes">
        <Typography>
          You may stop using the service at any time. We may suspend or terminate access if you violate these Terms, create risk, fail to pay, or if a platform or legal requirement requires us to do so. We may update these Terms from time to time, and continued use after an update means you accept the updated Terms.
        </Typography>
      </LegalSection>

      <LegalSection title="Contact">
        <Typography>
          Questions about these Terms, connected platform permissions, account deletion, or policy compliance can be sent to support@voicesparkai.com.
        </Typography>
      </LegalSection>
    </LegalShell>
  );
}
