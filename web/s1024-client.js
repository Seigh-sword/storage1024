class Storage1024 {
    constructor(config) {
        this.projectId = config.projectId;
        this.token = config.token;
        this.apiBase = config.apiBase || 'http://127.0.0.1:8000/api';
    }

    /**
     * Uploads a file to the project.
     * Note: This requires the bridge.py to be running.
     */
    async uploadFile(file, alias) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('alias', alias);

        const response = await fetch(`${this.apiBase}/projects/${this.projectId}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`
            },
            body: formData
        });

        return await response.json();
    }

    /**
     * Gets a Global Variable value by alias.
     */
    async getGV(alias) {
        const response = await fetch(`${this.apiBase}/projects/${this.projectId}/gv/${alias}`, {
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
        return await response.json();
    }

    /**
     * Stores a Global Variable.
     */
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

// Export for usage
window.Storage1024 = Storage1024;
