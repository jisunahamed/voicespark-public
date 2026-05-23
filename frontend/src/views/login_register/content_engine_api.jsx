import api from './axios_client';
import { workspaceStorage } from '../workspace/workSpaceAPi';

export const currentUserId = () => JSON.parse(localStorage.getItem('user') || 'null')?.id;

export const workspacePayload = (extra = {}) => ({
  user_id: currentUserId(),
  workspace_id: workspaceStorage.getActiveId(),
  ...extra,
});

export const contentEngineApi = {
  fetchBusinessProfile: () => api.get('/content-engine/business-profile/', { params: workspacePayload() }),
  businessProfile: (payload, requestConfig = {}) => api.post('/content-engine/business-profile/', workspacePayload(payload), {
    timeout: 120000,
    ...requestConfig,
  }),
  updateBusinessProfile: (payload) => api.patch('/content-engine/business-profile/', workspacePayload(payload)),
  fetchOnboardingState: () => api.get('/content-engine/onboarding-state/', { params: workspacePayload() }),
  saveOnboardingState: (payload) => api.post('/content-engine/onboarding-state/', workspacePayload(payload)),
  saveBrand: (payload) => api.post('/content-engine/brand-settings/', workspacePayload(payload)),
  updateBrandStyle: (brandStyle) => api.post('/auth/user/update-brand-style/', workspacePayload({ brand_style: brandStyle })),
  fetchBrandStyle: () => api.post('/auth/user/fetch-brand-style/', workspacePayload()),
  fetchContentPreferences: () => api.post('/auth/user/fetch-content-preferences/', workspacePayload()),
  updateContentPreferences: (contentPreferences) => api.post('/auth/user/update-content-preferences/', workspacePayload({ content_preferences: contentPreferences })),
  recommendedStyles: (visualStyle) => api.get('/content-engine/recommended-visual-styles/', {
    params: workspacePayload({ visual_style: visualStyle }),
  }),
  fetchContentPlan: () => api.get('/content-engine/content-plan/', { params: workspacePayload() }),
  saveContentPlan: (payload) => api.post('/content-engine/content-plan/', workspacePayload(payload)),
  generateTopics: (payload = {}) => api.post('/content-engine/topics/', workspacePayload(payload)),
  blogEmailPlan: (payload = {}) => api.post('/content-engine/blog-email-plan/', workspacePayload(payload)),
  generateFirstWeek: () => api.post('/content-engine/generate-first-week/', workspacePayload()),
  fetchCampaignPlan: () => api.get('/content-engine/campaign-plan/', { params: workspacePayload() }),
  generateCampaignPlan: () => api.post('/content-engine/campaign-plan/', workspacePayload()),
  saveCampaignPlan: (weeks) => api.post('/content-engine/campaign-plan/', workspacePayload({ weeks })),
  createCampaignBatch: (count) => api.post('/content-engine/campaign-plan/create-batch/', workspacePayload({ count })),
  reorderCampaignPlan: (orderedIds) => api.post('/content-engine/campaign-plan/reorder/', workspacePayload({ ordered_ids: orderedIds })),
  updateCampaignWeek: (weekId, payload) => api.patch(`/content-engine/campaign-plan/${weekId}/`, workspacePayload(payload)),
  deleteCampaignWeek: (weekId) => api.delete(`/content-engine/campaign-plan/${weekId}/`, { data: workspacePayload() }),
  approveCampaignWeek: (weekId) => api.post(`/content-engine/campaign-plan/${weekId}/approve/`, workspacePayload()),
  generateCampaignWeek: (weekId) => api.post(`/content-engine/campaign-plan/${weekId}/generate/`, workspacePayload()),
  regenerateCampaignWeek: (weekId, instruction) => api.post(`/content-engine/campaign-plan/${weekId}/regenerate/`, workspacePayload({ instruction })),
  regenerateCampaignPrompt: (weekId, promptId, instruction) => api.post(`/content-engine/campaign-plan/${weekId}/prompt-regenerate/`, workspacePayload({ prompt_id: promptId, instruction })),
  fetchMediaLibrary: () => api.post('/auth/user/get-data/', workspacePayload()),
  uploadMedia: (formData) => api.post('/auth/user/media-upload/', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  fetchSourceMatrix: () => api.get('/content-engine/source-matrix/', { params: workspacePayload() }),
  addSourceMatrix: (payload) => api.post('/content-engine/source-matrix/', workspacePayload(payload)),
  analyzeSourceMatrix: (payload) => api.post('/content-engine/source-matrix/analyze/', workspacePayload(payload)),
  fetchCompetitors: () => api.get('/content-engine/competitors/', { params: workspacePayload() }),
  addCompetitor: (payload) => api.post('/content-engine/competitors/', workspacePayload(payload)),
  updateCompetitor: (id, payload) => api.patch(`/content-engine/competitors/${id}/`, workspacePayload(payload)),
  deleteCompetitor: (id) => api.delete(`/content-engine/competitors/${id}/`, { data: workspacePayload() }),
  reanalyzeCompetitor: (id) => api.post(`/content-engine/competitors/${id}/reanalyze/`, workspacePayload()),
  fetchChannelVoice: () => api.get('/content-engine/channel-voice/', { params: workspacePayload() }),
  updateChannelVoice: (payload) => api.patch('/content-engine/channel-voice/', workspacePayload(payload)),
  fetchAudienceProfiles: () => api.get('/content-engine/audience-profiles/', { params: workspacePayload() }),
  addAudienceProfile: (payload) => api.post('/content-engine/audience-profiles/', workspacePayload(payload)),
  updateAudienceProfile: (id, payload) => api.patch(`/content-engine/audience-profiles/${id}/`, workspacePayload(payload)),
  deleteAudienceProfile: (id) => api.delete(`/content-engine/audience-profiles/${id}/`, { data: workspacePayload() }),
  fetchManualData: () => api.get('/content-engine/manual-data/', { params: workspacePayload() }),
  updateManualData: (payload) => api.patch('/content-engine/manual-data/', workspacePayload(payload)),
};
