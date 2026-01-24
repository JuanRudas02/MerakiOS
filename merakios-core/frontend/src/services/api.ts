import axios from 'axios';

const API_URL = 'http://localhost:8001/api';

export interface Project {
    id: string;
    name: string;
    niche: string;
    status: 'draft' | 'analyzing' | 'audited' | 'designing' | 'completed';
    audit_data?: any;
    funnel_structure?: any;
}

export const api = {
    // Projects
    createProject: async (name: string, niche: string) => {
        const response = await axios.post(`${API_URL}/projects/`, {
            name,
            niche
        }, getAuthHeader());
        return response.data;
    },

    getProject: async (id: string) => {
        const response = await axios.get(`${API_URL}/projects/${id}`);
        return response.data;
    },

    // AI Triggers
    triggerGenesis: async (projectId: string) => {
        const response = await axios.post(`${API_URL}/run/genesis/${projectId}`, {}, getAuthHeader());
        return response.data;
    },

    triggerBlueprint: async (projectId: string) => {
        const response = await axios.post(`${API_URL}/run/blueprint/${projectId}`, {}, getAuthHeader());
        return response.data;
    },

    // Auth
    login: async (username, password) => {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        const response = await axios.post(`${API_URL}/auth/login`, formData);
        return response.data;
    }
};

function getAuthHeader() {
    const session = localStorage.getItem('meraki_session');
    if (!session) return {};
    const { access_token } = JSON.parse(session);
    return { headers: { Authorization: `Bearer ${access_token}` } };
}
