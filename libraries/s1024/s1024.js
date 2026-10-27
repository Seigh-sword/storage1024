/* Storage1024 JS SDK - UMD (browser + Node 18+).
 * Served at /s1024.js. The API host defaults to the host that served this
 * script, so the same file works on Render, localhost and preview hosts.
 */
(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.s1024 = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    function defaultApiBase() {
        try {
            if (typeof document !== 'undefined' && document.currentScript && document.currentScript.src) {
                return new URL(document.currentScript.src).origin + '/api';
            }
            if (typeof location !== 'undefined' && /^https?:$/.test(location.protocol)) {
                return location.origin + '/api';
            }
        } catch (_) { /* ignore, use the public fallback */ }
        return 'https://storage1024.onrender.com/api';
    }

    const s1024 = {
        apiBase: defaultApiBase(),
        token: null,
        userID: null,

        set_api_base(url) {
            this.apiBase = String(url).replace(/\/$/, '');
            return this;
        },
        set_token(token) { this.token = token; return this; },
        set_userID(id) { this.userID = String(id); return this; },
        set_userid(id) { return this.set_userID(id); },

        _requireCredentials() {
            if (!this.token || !this.userID) {
                throw new Error('Credentials missing. Use set_token() and set_userID()');
            }
        },
        _headers(extra) {
            return Object.assign({ 'Authorization': `Bearer ${this.token}` }, extra || {});
        },
        async _fetch() {
            if (typeof fetch === 'function') return fetch;
            try {
                const mod = await import('node-fetch');
                return mod.default || mod;
            } catch (_) {
                throw new Error('No global fetch found. Use Node 18+ or install node-fetch.');
            }
        },
        async _request(path, options) {
            const fetchFn = await this._fetch();
            const res = await fetchFn(`${this.apiBase}${path}`, options);
            if (!res.ok) {
                let detail = res.statusText;
                try {
                    const body = await res.json();
                    detail = body.detail || JSON.stringify(body);
                } catch (_) { /* non-JSON error body */ }
                throw new Error(`Storage1024 ${res.status}: ${detail}`);
            }
            return res;
        },
        _projectPath(suffix) {
            this._requireCredentials();
            return `/projects/${encodeURIComponent(this.userID)}${suffix}`;
        },

        async get_gv(name) {
            this._requireCredentials();
            const res = await this._request(this._projectPath(`/gv/${encodeURIComponent(name)}`), {
                headers: this._headers()
            });
            const data = await res.json();
            return data.value;
        },

        async add_gv(name, value) {
            const res = await this._request(this._projectPath('/gv'), {
                method: 'POST',
                headers: this._headers({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ alias: name, value: String(value) })
            });
            return await res.json();
        },

        async delete_gv(name) {
            const res = await this._request(this._projectPath(`/gv/${encodeURIComponent(name)}`), {
                method: 'DELETE', headers: this._headers()
            });
            return await res.json();
        },

        async gv_json() {
            const res = await this._request(this._projectPath('/gv'), { headers: this._headers() });
            return await res.json();
        },

        async upload_file(fileAlias, fileBlob, filename) {
            this._requireCredentials();
            const formData = new FormData();
            let blob = fileBlob;
            if (typeof Buffer !== 'undefined' && typeof Buffer.isBuffer === 'function' && Buffer.isBuffer(blob)) {
                const bufferModule = await import('buffer');
                blob = new bufferModule.Blob([blob]);
            }
            const name = filename || blob.name || 'file';
            formData.append('file', blob, name);
            formData.append('alias', fileAlias);
            const res = await this._request(this._projectPath('/upload'), {
                method: 'POST', headers: this._headers(), body: formData
            });
            return await res.json();
        },

        async list_files() {
            const res = await this._request(this._projectPath('/files'), { headers: this._headers() });
            const data = await res.json();
            return data.files || {};
        },

        async get_file(name) {
            const res = await this._request(this._projectPath(`/files/${encodeURIComponent(name)}`), {
                headers: this._headers()
            });
            const buffer = await res.arrayBuffer();
            return new Uint8Array(buffer);
        },

        async download_file(name, filename) {
            const bytes = await this.get_file(name);
            if (typeof document === 'undefined') return bytes; // Node: return the bytes
            const url = URL.createObjectURL(new Blob([bytes]));
            const a = document.createElement('a');
            a.href = url;
            a.download = filename || name;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 30000);
            return bytes;
        },

        async delete_file(name) {
            const res = await this._request(this._projectPath(`/files/${encodeURIComponent(name)}`), {
                method: 'DELETE', headers: this._headers()
            });
            return await res.json();
        },

        async create_project(name) {
            const res = await this._request('/projects/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            return await res.json();
        },

        async create_token(name, type = 'public') {
            const res = await this._request(this._projectPath('/tokens'), {
                method: 'POST',
                headers: this._headers({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ name, type })
            });
            const data = await res.json();
            return data.token;
        },

        async revoke_token(tokenToRevoke) {
            const res = await this._request(this._projectPath('/tokens/revoke'), {
                method: 'POST',
                headers: this._headers({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ token: tokenToRevoke })
            });
            return await res.json();
        }
    };
    return s1024;
}));
