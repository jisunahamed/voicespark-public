import { create } from 'zustand';

const useAppStore = create((set) => ({
  markdown: '',
  setMarkdown: (val) => set({ markdown: val }),

  creds: { username: '', email: '', password: '', password2: '' },
  setCreds: (val) => set((state) => ({ creds: { ...state.creds, ...val } })),

  websiteLink: { website_link: ''},
  setWebsiteLink: (val) => set((state) => ({ websiteLink: { ...state.websiteLink, ...val } })),

  image_urls: [],
  addImageUrls: (urls) => set((state) => ({ image_urls: [...state.image_urls, ...urls] })),
  setImageUrls: (urls) => set({ image_urls: urls || [] }),

  brandStyle: {},
  setBrandStyle: (val) => set({ brandStyle: val || {} }),

  visualStyle: "gauzy-portrait",
  setVisualStyle: (val) => set({ visualStyle: val }),

  recommendedVisualStyle: null,
  setRecommendedVisualStyle: (val) => set({ recommendedVisualStyle: val }),

  brandFont: { id: 'lexend', displayName: 'Lexend', family: 'Lexend', weight: '700' },
  setBrandFont: (val) => set({ brandFont: val }),

  contentPlan: { platforms: ['facebook', 'instagram', 'linkedin', 'x'], posts_per_week: 5, blog_posts_per_week: 0, emails_per_week: 0 },
  setContentPlan: (val) => set((state) => ({ contentPlan: { ...state.contentPlan, ...val } })),

  weeklyTopics: [],
  setWeeklyTopics: (val) => set({ weeklyTopics: val || [] }),

  blogEmailPlan: null,
  setBlogEmailPlan: (val) => set({ blogEmailPlan: val }),
}));

export default useAppStore;
