/* Storage1024 browser client (class based).
 * Include either /web/cdn.js or /web/s1024-client.js - they are identical.
 * The default API host is the page's own origin, so it works on any deploy.
 */
(function (root) {
    'use strict';

    class Storage1024 {
        constructor(config = {}) {
            this.projectId = config.projectId || null;
            this.token = config.token || null;
            this.apiBase = (config.apiBase || defaultApiBase()).replace(/\/$/, '');
        }

        setProjectId(id) { this.projectId = id; }
        setToken(token) { this.token = token; }

        _headers(extra) {
            if (!this.token) throw new Error('Storage1024: call setToken() first');
            return Object.assign({ 'Authorization': `Bearer ${this.token}` }, extra || {});
        }

        _path(suffix) {
            if (!this.projectId) throw new Error('Storage1024: call setProjectId() first');
            return `${this.apiBase}/projects/${encodeURIComponent(this.projectId)}${suffix}`;
        }

        async _request(suffix, options = {}) {
            const res = await fetch(this._path(suffix), {
                ...options,
                headers: this._headers(options.headers)
            });
            if (!res.ok) {
                let detail = res.statusText;
                try { const body = await res.json(); detail = body.detail || JSON.stringify(body); } catch (_) {}
                throw new Error(`Storage1024 ${res.status}: ${detail}`);
            }
            return res;
        }

        async uploadFile(file, alias) {
            const form = new FormData();
            form.append('file', file);
            form.append('alias', alias);
            const res = await this._request('/upload', { method: 'POST', body: form });
            return await res.json();
        }

        async getGV(alias) {
            const res = await this._request(`/gv/${encodeURIComponent(alias)}`);
            const data = await res.json();
            return data.value;
        }

        async listGVs() {
            const res = await this._request('/gv');
            return await res.json();
        }

        async setGV(alias, value) {
            const res = await this._request('/gv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ alias, value: String(value) })
            });
            return await res.json();
        }

        async deleteGV(alias) {
            const res = await this._request(`/gv/${encodeURIComponent(alias)}`, { method: 'DELETE' });
            return await res.json();
        }

        async listFiles() {
            const res = await this._request('/files');
            const data = await res.json();
            return data.files || {};
        }

        async getFile(alias) {
            const res = await this._request(`/files/${encodeURIComponent(alias)}`);
            return new Uint8Array(await res.arrayBuffer());
        }
    }

    function defaultApiBase() {
        try {
            if (typeof location !== 'undefined' && /^https?:$/.test(location.protocol)) {
                return location.origin + '/api';
            }
        } catch (_) {}
        return 'https://storage1024.onrender.com/api';
    }

    root.Storage1024 = Storage1024;
})(typeof window !== 'undefined' ? window : globalThis);
