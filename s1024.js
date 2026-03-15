const s1024 = {
    token: null,
    apiBase: 'https://storage1024.onrender.com/api',

    set_token(token) {
        this.token = token;
    },

    async get_gv(name) {
        if (!this.token) throw new Error("Token not set. Use s1024.set_token(token)");
        const res = await fetch(`${this.apiBase}/gv/${name}`, {
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
        if (!res.ok) throw new Error(`Failed to fetch GV: ${res.statusText}`);
        const data = await res.json();
        return data.value;
    },

    async gv_json() {
        if (!this.token) throw new Error("Token not set. Use s1024.set_token(token)");
        const res = await fetch(`${this.apiBase}/index`, {
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
        if (!res.ok) throw new Error(`Failed to fetch Index: ${res.statusText}`);
        const data = await res.json();
        const project = Object.values(data.projects)[0];
        return project.global_vars || {};
    },

    async upload_file(fileAlias, fileBlob) {
        if (!this.token) throw new Error("Token not set. Use s1024.set_token(token)");
        const formData = new FormData();
        formData.append('file', fileBlob);
        const res = await fetch(`${this.apiBase}/upload?alias=${fileAlias}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.token}` },
            body: formData
        });
        if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
        return await res.json();
    },

    async get_file(id) {
        const res = await fetch(`${this.apiBase}/files/${id}`);
        if (!res.ok) throw new Error(`Failed to fetch file: ${res.statusText}`);
        return res;
    }
};
