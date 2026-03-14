/**
 * Storage1024 CDN Client
 * Load this via: <script src="https://raw.githubusercontent.com/Seigh-sword/storage1024/main/web/cdn.js"></script>
 */
const Storage1024 = (function() {
    class Client {
        constructor(config) {
            this.projectId = config.projectId;
            this.token = config.token;
            this.apiBase = config.apiBase || 'https://storage1024.onrender.com/api';
        }

        async uploadFile(file, alias) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('alias', alias);
            const response = await fetch(`${this.apiBase}/projects/${this.projectId}/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${this.token}` },
                body: formData
            });
            return await response.json();
        }

        async getGV(alias) {
            const response = await fetch(`${this.apiBase}/projects/${this.projectId}/gv/${alias}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            return await response.json();
        }

        async setGV(alias, value) {
            const response = await fetch(`${this.apiBase}/projects/${this.projectId}/gv`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({ alias, value })
            });
            return await response.json();
        }
    }
    return Client;
})();

window.Storage1024 = Storage1024;
console.log("Storage1024 CDN Loaded 🚀");
