// api/workspaceApi.js
import api from "../login_register/axios_client";

const WORKSPACES_KEY       = 'blaze_workspaces';
const ACTIVE_WORKSPACE_KEY = 'blaze_active_workspace_id';

// ── localStorage helpers ──────────────────────────────────────────────────────
export const workspaceStorage = {
  getAll: () => {
    try { return JSON.parse(localStorage.getItem(WORKSPACES_KEY)) || []; }
    catch { return []; }
  },
  save: (workspaces) => {
    localStorage.setItem(WORKSPACES_KEY, JSON.stringify(workspaces));
  },
  getActiveId: () => localStorage.getItem(ACTIVE_WORKSPACE_KEY),
  setActiveId: (id) => {
    if (id) localStorage.setItem(ACTIVE_WORKSPACE_KEY, id);
    else    localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
  },
  getActive: () => {
    const all      = workspaceStorage.getAll();
    const activeId = workspaceStorage.getActiveId();
    return all.find(ws => String(ws.id) === String(activeId)) || null;
  },
  clear: () => {
    localStorage.removeItem(WORKSPACES_KEY);
    localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
  },
};

// ── Workspace API ─────────────────────────────────────────────────────────────
export const workspaceApi = {
  list: async () => {
    const { data } = await api.get('/workspace/workspaces/');
    workspaceStorage.save(data);
    const activeId = workspaceStorage.getActiveId();
    const activeExists = data.some((workspace) => String(workspace.id) === String(activeId));
    if ((!activeId || !activeExists) && data.length) {
      workspaceStorage.setActiveId(data[0].id);
    }
    return data;
  },
  create: async (name) => {
    const { data } = await api.post('/workspace/workspaces/', { name });
    const existing = workspaceStorage.getAll();
    workspaceStorage.save([data, ...existing]);
    workspaceStorage.setActiveId(data.id);
    return data;
  },
  delete: async (id) => {
    await api.delete(`/workspace/workspaces/${id}/`);
    const updated = workspaceStorage.getAll().filter(ws => ws.id !== id);
    workspaceStorage.save(updated);
    if (workspaceStorage.getActiveId() === id) {
      workspaceStorage.setActiveId(updated[0]?.id || null);
    }
  },
  update: async (id, name) => {
    const { data } = await api.patch(`/workspace/workspaces/${id}/`, { name });
    const updated  = workspaceStorage.getAll().map(ws => String(ws.id) === String(id) ? data : ws);
    workspaceStorage.save(updated);
    window.dispatchEvent(new CustomEvent('workspace-updated', { detail: data }));
    return data;
  },
  get: (id) => api.get(`/workspace/workspaces/${id}/`),
};

// ── Membership ────────────────────────────────────────────────────────────────
export const membershipApi = {
  list:   (workspaceId)              => api.get(`/workspace/workspaces/${workspaceId}/members/`),
  invite: (workspaceId, email, role) => api.post(`/workspace/workspaces/${workspaceId}/members/`, { email, role }),
  remove: (workspaceId, userId)      => api.delete(`/workspace/workspaces/${workspaceId}/members/${userId}/`),
  update: (workspaceId, userId, role)=> api.patch(`/workspace/workspaces/${workspaceId}/members/${userId}/`, { role }),
};
