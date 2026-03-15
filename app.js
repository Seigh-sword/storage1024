const API_BASE = 'https://storage1024.onrender.com/api';

function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${type === 'success' ? '✅' : '❌'}</span> ${msg}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function checkHoliday() {
    const now = new Date();
    const month = now.getMonth() + 1;
    const day = now.getDate();
    const body = document.body;
    const logoImg = document.querySelector('.logo img');

    if (month === 2) {
        body.classList.add('finance-month');
        if (logoImg) logoImg.src = '/assets/finance.svg';
    } 
    else if (month === 3 && day === 15) {
        body.classList.add('birthday');
        if (logoImg) logoImg.src = '/assets/birthday.svg';
    }
    else if (month === 4 && day === 1) {
        body.classList.add('april-fools');
        if (logoImg) logoImg.src = '/assets/fools.svg';
        showToast("CRITICAL ERROR: Connection to Render cluster lost. System offline.", "error");
        setTimeout(() => showToast("Attempting failover to secondary node...", "error"), 5000);
    }
    else if (month === 3 && day === 27) {
        body.classList.add('user-birthday');
        if (logoImg) logoImg.src = '/assets/user_birthday.svg';
    }
    else if (month === 6) {
        body.classList.add('pride');
    }
    else if (month === 10) {
        body.classList.add('halloween');
        if (logoImg) logoImg.src = '/assets/halloween.svg';
    }
    else if (month === 12) {
        body.classList.add('christmas');
    }
}

function checkTrace() {
    if (localStorage.getItem('s1024_trace')) {
        const signupBtn = document.getElementById('signup-btn');
        if (signupBtn) {
            signupBtn.disabled = true;
            signupBtn.innerText = "Account limit reached";
            signupBtn.title = "Only one account per device is allowed.";
        }
        return true;
    }
    return false;
}

function copyToken(elementId) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
        showToast("Token copied to clipboard!");
    });
}

function setAppState(state) {
    const login = document.getElementById('login-state');
    const dashboard = document.getElementById('dashboard-state');
    const nav = document.getElementById('nav-actions');

    if (state === 'dashboard') {
        login.style.display = 'none';
        dashboard.style.display = 'flex';
        nav.innerHTML = '<button id="logout-btn" class="btn-secondary">Logout</button>';
        document.getElementById('logout-btn').onclick = logout;
    } else {
        login.style.display = 'flex';
        dashboard.style.display = 'none';
        nav.innerHTML = '';
    }
}

async function fetchAccountData() {
    const token = localStorage.getItem('s1024_token');
    if (!token) return setAppState('login');

    try {
        const res = await fetch(`${API_BASE}/index`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.status === 401 || res.status === 403) {
            return logout();
        }

        const data = await res.json();
        if (data && data.projects) {
            const [id, p] = Object.entries(data.projects)[0];
            renderDashboard(id, p);
            setAppState('dashboard');
        }
    } catch (err) {
        showToast("Connection lost. Retrying...", "error");
    }
}

function logout() {
    localStorage.removeItem('s1024_token');
    window.location.reload();
}

async function authenticatedFetch(path, options = {}) {
    const token = localStorage.getItem('s1024_token');
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    if (response.status === 401) logout();
    return response;
}

async function fetchAccountData() {
    try {
        const res = await authenticatedFetch('/index');
        const data = await res.json();
        renderDashboard(data.projects);
    } catch (err) {
        showToast("Error syncing dashboard. Check connection.", "error");
    }
}

function renderDashboard(projects) {
    const projectEntries = Object.entries(projects);
    if (projectEntries.length === 0) return logout();

    const [id, p] = projectEntries[0];
    document.getElementById('user-name').innerText = p.name;
    document.getElementById('project-id-display').innerText = `Account ID: ${id}`;
    document.getElementById('login-state').style.display = 'none';
    document.getElementById('dashboard-state').style.display = 'block';

    renderFiles(id, p.files);
    renderGVs(id, p.global_vars);
    renderTokens(id, p.tokens);
    renderStats(p);

    document.getElementById('generate-token-btn').onclick = () => generateNewToken(id);
}

function renderFiles(projectId, files) {
    const list = document.getElementById('file-list');
    const entries = Object.entries(files || {});
    list.innerHTML = entries.length > 0 ? '' : '<p class="meta">No files uploaded yet.</p>';
    
    entries.forEach(([alias, f]) => {
        const msgId = typeof f === 'object' ? f.id : f;
        const size = typeof f === 'object' ? `${f.size.toFixed(1)}MB` : 'Legacy';
        const row = document.createElement('div');
        row.className = 'item-row';
        row.innerHTML = `
            <div class="item-info">
                <span class="item-name">${alias}</span>
                <span class="item-meta">ID: ${msgId} | ${size}</span>
            </div>
            <div class="item-actions">
                <button class="btn-secondary" onclick="copyLink('${alias}')">🔗</button>
                <button class="btn-secondary" onclick="deleteFile('${projectId}', '${alias}')">🗑️</button>
            </div>
        `;
        list.appendChild(row);
    });
}

function renderGVs(projectId, gvs) {
    const list = document.getElementById('gv-list');
    const entries = Object.entries(gvs || {});
    list.innerHTML = entries.length > 0 ? '' : '<p class="meta">No variables set.</p>';
    
    entries.forEach(([alias, msgId]) => {
        const row = document.createElement('div');
        row.className = 'item-row';
        row.innerHTML = `
            <div class="item-info">
                <span class="item-name">${alias}</span>
                <span class="item-meta">ID: ${msgId}</span>
            </div>
            <div class="item-actions">
                <button class="btn-secondary" onclick="showEditGVModal('${projectId}', '${alias}')">📝</button>
                <button class="btn-secondary" onclick="deleteGV('${projectId}', '${alias}')">🗑️</button>
            </div>
        `;
        list.appendChild(row);
    });
}

function renderTokens(projectId, tokens = { private: [], public: [] }) {
    const list = document.getElementById('token-list');
    list.innerHTML = '';
    
    const all = [
        ...tokens.private.map(t => ({ t, type: 'Private' })),
        ...tokens.public.map(t => ({ t, type: 'Public' }))
    ];

    all.forEach(({ t, type }) => {
        const isCurrent = t === localStorage.getItem('s1024_token');
        const row = document.createElement('div');
        row.className = 'item-row';
        row.innerHTML = `
            <div class="item-info">
                <span class="item-name">${type} Token</span>
                <span class="item-meta">${t.slice(0, 10)}...${t.slice(-8)} ${isCurrent ? '(Active)' : ''}</span>
            </div>
            <div class="item-actions">
                <button class="btn-secondary" onclick="copyText('${t}')">📋</button>
                ${!isCurrent ? `<button class="btn-secondary" onclick="revokeToken('${projectId}', '${t}')">🚫</button>` : ''}
            </div>
        `;
        list.appendChild(row);
    });
}

function renderStats(p) {
    const files = Object.values(p.files || {});
    const fileCount = files.length;
    const gvCount = Object.keys(p.global_vars || {}).length;
    
    // Calculate total size in MB (handle legacy strings vs new objects)
    const totalSize = files.reduce((acc, f) => acc + (f.size || 0), 0);
    const quotaUsed = Math.min(totalSize, 1024);
    const pct = (quotaUsed / 1024) * 100;

    document.getElementById('file-stats').innerHTML = `
        <div style="font-size: 2.5rem; font-weight: 700;">${fileCount}</div> Files
        <div style="font-size: 2.5rem; font-weight: 700; margin-top: 1rem;">${gvCount}</div> GVs
    `;
    
    document.getElementById('quota-text').innerText = `${totalSize.toFixed(1)} / 1024 MB`;
    document.getElementById('quota-fill').style.width = `${pct}%`;
    
    // Color coding for storage pressure
    const fill = document.getElementById('quota-fill');
    if (pct > 90) fill.style.background = '#ef4444';
    else if (pct > 70) fill.style.background = '#f59e0b';
    else fill.style.background = 'linear-gradient(90deg, var(--primary) 0%, #3b82f6 100%)';
}

async function deleteFile(id, alias) {
    if (!confirm(`Delete ${alias}?`)) return;
    const res = await authenticatedFetch(`/projects/${id}/files/${alias}`, { method: 'DELETE' });
    if (res.ok) { showToast("File deleted"); fetchAccountData(); }
}

async function deleteGV(id, alias) {
    if (!confirm(`Remove variable ${alias}?`)) return;
    const res = await authenticatedFetch(`/projects/${id}/gv/${alias}`, { method: 'DELETE' });
    if (res.ok) { showToast("GV removed"); fetchAccountData(); }
}

async function revokeToken(id, token) {
    if (!confirm("Revoke this token? Applications using it will break.")) return;
    const res = await authenticatedFetch(`/projects/${id}/tokens/revoke`, {
        method: 'POST',
        body: JSON.stringify({ token })
    });
    if (res.ok) { showToast("Token revoked"); fetchAccountData(); }
}

function showAddGVModal() {
    document.getElementById('gv-alias').value = '';
    document.getElementById('gv-value').value = '';
    document.getElementById('gv-alias').disabled = false;
    document.getElementById('gv-modal').style.display = 'flex';
}

async function showEditGVModal(id, alias) {
    const res = await authenticatedFetch(`/projects/${id}/gv/${alias}`);
    const data = await res.json();
    document.getElementById('gv-alias').value = alias;
    document.getElementById('gv-alias').disabled = true;
    document.getElementById('gv-value').value = data.value;
    document.getElementById('gv-modal').style.display = 'flex';
}

document.getElementById('save-gv-btn').onclick = async () => {
    const alias = document.getElementById('gv-alias').value;
    const value = document.getElementById('gv-value').value;
    const id = document.getElementById('project-id-display').innerText.split(': ')[1];
    if (!alias || !value) return showToast("Required fields missing", "error");
    
    const res = await authenticatedFetch(`/projects/${id}/gv`, {
        method: 'POST',
        body: JSON.stringify({ alias, value })
    });
    if (res.ok) { showToast("GV Saved"); closeModal('gv-modal'); fetchAccountData(); }
};

async function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;
    const alias = prompt("File Name:", file.name);
    if (!alias) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('alias', alias);
    
    const id = document.getElementById('project-id-display').innerText.split(': ')[1];
    const token = localStorage.getItem('s1024_token');
    
    showToast("Uploading...", "success");
    const res = await fetch(`${API_BASE}/projects/${id}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
    });
    if (res.ok) { showToast("Uploaded!"); fetchAccountData(); }
    else { showToast("Upload failed", "error"); }
    input.value = '';
}

async function generateNewToken(id) {
    const alias = document.getElementById('token-alias').value;
    const isPriv = document.getElementById('token-is-private').checked;
    if (!alias) return showToast("Token Name?", "error");
    
    const res = await authenticatedFetch(`/projects/${id}/tokens`, {
        method: 'POST',
        body: JSON.stringify({ type: isPriv ? 'private' : 'public' })
    });
    if (res.ok) { showToast("Token generated"); fetchAccountData(); }
}

function copyLink(alias) {
    copyText(`https://storage1024.onrender.com/files/${alias}`);
    showToast("Link copied!");
}

function copyText(text) {
    navigator.clipboard.writeText(text);
}

function closeModal(id) { document.getElementById(id).style.display = 'none'; }

document.getElementById('signup-btn').onclick = async () => {
    const name = document.getElementById('signup-name-input').value;
    if (!name) return showToast("Account name?", "error");
    const res = await fetch(`${API_BASE}/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    const data = await res.json();
    if (res.ok) {
        localStorage.setItem('s1024_trace', 'true');
        document.getElementById('modal').style.display = 'flex';
        document.getElementById('modal-success').style.display = 'block';
        document.getElementById('success-priv').innerText = data.tokens.private;
        document.getElementById('apply-token-btn').onclick = () => {
            localStorage.setItem('s1024_token', data.tokens.private);
            window.location.reload();
        };
    }
};

document.getElementById('login-btn').onclick = () => {
    const t = document.getElementById('login-token-input').value;
    if (!t.endsWith(";qi=")) return showToast("Private Tokens Only", "error");
    localStorage.setItem('s1024_token', t);
    fetchAccountData();
};

document.getElementById('tab-login').onclick = () => {
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('signup-form').style.display = 'none';
};

document.getElementById('tab-signup').onclick = () => {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('signup-form').style.display = 'block';
};

checkHoliday();
checkTrace();
if (localStorage.getItem('s1024_token')) fetchAccountData();
