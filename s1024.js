const s1024 = {
    apiBase: 'https://storage1024.onrender.com/api',
    token: null,
    userID: null,

    set_token(token) {
        this.token = token;
    },

    set_userID(id) {
        this.userID = id;
    },

    async get_gv(name) {
        if (!this.token || !this.userID) throw new Error("Credentials missing. Use set_token() and set_userID()");
        const res = await fetch(`${this.apiBase}/projects/${this.userID}/gv/${name}`, {
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
        if (!res.ok) throw new Error(`Failed to fetch GV: ${res.statusText}`);
        const data = await res.json();
        return data.value;
    },

    async add_gv(name, value) {
        if (!this.token || !this.userID) throw new Error("Credentials missing. Use set_token() and set_userID()");
        const res = await fetch(`${this.apiBase}/projects/${this.userID}/gv`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ alias: name, value })
        });
        if (!res.ok) throw new Error(`Failed to add GV: ${res.statusText}`);
        return await res.json();
    },

    async gv_json() {
        if (!this.token || !this.userID) throw new Error("Credentials missing");
        const res = await fetch(`${this.apiBase}/projects/${this.userID}/gv`, {
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
        if (!res.ok) throw new Error(`Failed to fetch GVs: ${res.statusText}`);
        return await res.json();
    },

    async upload_file(fileAlias, fileBlob) {
        if (!this.token || !this.userID) throw new Error("Credentials missing");
        const formData = new FormData();
        formData.append('file', fileBlob);
        formData.append('alias', fileAlias);
        const res = await fetch(`${this.apiBase}/projects/${this.userID}/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.token}` },
            body: formData
        });
        if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
        return await res.json();
    },

    async create_project(name) {
        const res = await fetch(`${this.apiBase}/projects/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (!res.ok) throw new Error(`Failed to create project: ${res.statusText}`);
        const data = await res.json();
        return data; // Returns {project_id, tokens: {private, public}}
    },

    async create_token(name, type = 'public') {
        if (!this.token || !this.userID) throw new Error("Credentials missing");
        const res = await fetch(`${this.apiBase}/projects/${this.userID}/tokens`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({ name, type })
        });
        if (!res.ok) throw new Error(`Failed to create token: ${res.statusText}`);
        const data = await res.json();
        return data.token;
    },

    async revoke_token(tokenToRevoke) {
        if (!this.token || !this.userID) throw new Error("Credentials missing");
        const res = await fetch(`${this.apiBase}/projects/${this.userID}/tokens/revoke`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({ token: tokenToRevoke })
        });
        if (!res.ok) throw new Error(`Failed to revoke token: ${res.statusText}`);
        return await res.json();
    }
};
