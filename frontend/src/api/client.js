// In production, Vercel rewrites /api/* to the Render backend (no CORS needed)
// In development, fall back to localhost
const API_BASE = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api';

export const apiClient = {
  async request(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // If body is FormData (for file uploads), remove Content-Type so browser sets it with boundary
    if (options.body instanceof FormData) {
      delete headers['Content-Type'];
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Unauthorized - clear token and maybe redirect
      localStorage.removeItem('token');
      window.dispatchEvent(new Event('unauthorized'));
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let errMsg = 'API request failed';
      if (typeof errorData.detail === 'string') {
        errMsg = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errMsg = errorData.detail.map(e => e.msg).join(', ');
      } else if (errorData.message) {
        errMsg = errorData.message;
      }
      throw new Error(errMsg);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return null;
    }

    // Sometimes responses are not JSON (like file downloads), handle that
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }
    
    return response.blob();
  },

  get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  },

  post(endpoint, data) {
    const isFormData = data instanceof FormData;
    return this.request(endpoint, {
      method: 'POST',
      body: isFormData ? data : JSON.stringify(data),
    });
  },

  postForm(endpoint, formData) {
    const data = new URLSearchParams();
    for (const pair of formData) {
      data.append(pair[0], pair[1]);
    }
    return this.request(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: data.toString()
    });
  },

  put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
};
