/* Storage1024 dashboard.
 * Uses relative API URLs so the same build works on Render, localhost and
 * preview hosts. Never interpolate server data into HTML without escaping.
 */
const API_BASE = '/api';

let currentProjectId = null;

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
}

function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = document.createElement('span');
    icon.textContent = type === 'success' ? '✅' : '❌';
    toast.appendChild(icon);
    toast.appendChild(document.createTextNode(' ' + msg));
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4500);
}

function setAppState(state) {
    const login = document.getElementById('login-state');
    const dashboard = document.getElementById('dashboard-state');
    const logoutBtn = document.getElementById('logout-btn');
    const isDashboard = state === 'dashboard';
    login.style.display = isDashboard ? 'none' : 'flex';
    dashboard.style.display = isDashboard ? 'block' : 'none';
    logoutBtn.style.display = isDashboard ? 'inline-block' : 'none';
}

async function errorDetail(res) {
    try {
        const data = await res.json();
        return data.detail || data.message || JSON.stringify(data);
    } catch (_) {
        return `${res.status} ${res.statusText}`;
    }
}

async function apiFetch(path, options = {}) {
    const token = localStorage.getItem('s1024_token');
    const headers = { ...(options.headers || {}) };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (options.body !== undefined && !(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }
    return fetch(`${API_BASE}${path}`, { ...options, headers });
}

function logout() {
    localStorage.removeItem('s1024_token');
    currentProjectId = null;
    window.location.reload();
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
    } else if (month === 3 && day === 15) {
        body.classList.add('birthday');
        if (logoImg) logoImg.src = '/assets/birthday.svg';
    } else if (month === 4 && day === 1) {
        body.classList.add('april-fools');
        if (logoImg) logoImg.src = '/assets/fools.svg';
        showToast('April Fools! Your data is completely fine.', 'success');
    } else if (month === 3 && day === 27) {
        body.classList.add('user-birthday');
        if (logoImg) logoImg.src = '/assets/user_birthday.svg';
    } else if (month === 6) {
        body.classList.add('pride');
    } else if (month === 10) {
        body.classList.add('halloween');
        if (logoImg) logoImg.src = '/assets/halloween.svg';
    } else if (month === 12) {
        body.classList.add('christmas');
    }
}

function copyText(text) {
    if (!text) return showToast('Nothing to copy', 'error');
    if (!navigator.clipboard) return showToast('Clipboard unavailable in this browser', 'error');
    navigator.clipboard.writeText(text)
        .then(() => showToast('Copied to clipboard!'))
        .catch(() => showToast('Could not copy', 'error'));
}

function copyToken(elementId) {
    copyText(document.getElementById(elementId)?.textContent.trim());
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
}

function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'flex';
}

async function fetchAccountData() {
    const token = localStorage.getItem('s1024_token');
    if (!token) return setAppState('login');

    try {
        const res = await apiFetch('/index');
        if (res.status === 401 || res.status === 403) return logout();
        if (!res.ok) throw new Error(await errorDetail(res));
        const data = await res.json();
        const entries = Object.entries(data.projects || {});
        if (entries.length === 0) return logout();

        const [id, project] = entries[0];
        currentProjectId = id;
        renderAccount(id, project);
        setAppState('dashboard');

        const gvRes = await apiFetch(`/projects/${encodeURIComponent(id)}/gv`);
        renderGVs(gvRes.ok ? await gvRes.json() : {});
    } catch (err) {
        showToast(`Connection lost: ${err.message}`, 'error');
    }
}

function renderAccount(id, project) {
    document.getElementById('user-name').textContent = project.name || 'User';
    document.getElementById('project-id-display').textContent = `Account ID: ${id}`;
    renderFiles(project.files || {});
    renderTokens(project.tokens || {});
    renderStats(project);
}

function row(inner) {
    const div = document.createElement('div');
    div.className = 'item-row';
    div.innerHTML = inner;
    return div;
}

function renderFiles(files) {
    const list = document.getElementById('file-list');
    const entries = Object.entries(files || {});
    list.innerHTML = '';
    if (!entries.length) {
        list.innerHTML = '<p class="meta">No files uploaded yet.</p>';
        return;
    }
    entries.forEach(([alias, f]) => {
        const size = typeof f === 'object' && f.bytes ? `${(f.bytes / 1024).toFixed(1)} KB` : '';
        list.appendChild(row(`
            <div class="item-info">
                <span class="item-name">${escapeHtml(alias)}</span>
                <span class="item-meta">${escapeHtml(f && f.name ? f.name : 'file')} ${escapeHtml(size)}</span>
            </div>
            <div class="item-actions">
                <button class="btn-secondary small" data-action="download" data-alias="${escapeHtml(alias)}">Download</button>
                <button class="btn-secondary small" data-action="copy-link" data-alias="${escapeHtml(alias)}">Copy link</button>
                <button class="btn-secondary small danger" data-action="delete-file" data-alias="${escapeHtml(alias)}">Delete</button>
            </div>
        `));
    });
}

function renderGVs(gvs) {
    const list = document.getElementById('gv-list');
    const entries = Object.entries(gvs || {});
    list.innerHTML = '';
    if (!entries.length) {
        list.innerHTML = '<p class="meta">No variables set.</p>';
        return;
    }
    entries.forEach(([alias, value]) => {
        const preview = String(value ?? '').slice(0, 80);
        list.appendChild(row(`
            <div class="item-info">
                <span class="item-name">${escapeHtml(alias)}</span>
                <span class="item-meta">${escapeHtml(preview) || '(empty)'}</span>
            </div>
            <div class="item-actions">
                <button class="btn-secondary small" data-action="edit-gv" data-alias="${escapeHtml(alias)}">Edit</button>
                <button class="btn-secondary small" data-action="copy-gv" data-value="${escapeHtml(value ?? '')}">Copy value</button>
                <button class="btn-secondary small danger" data-action="delete-gv" data-alias="${escapeHtml(alias)}">Delete</button>
            </div>
        `));
    });
}

function renderTokens(tokens = {}) {
    const list = document.getElementById('token-list');
    const current = localStorage.getItem('s1024_token');
    const all = [
        ...(tokens.private || []).map(t => ({ t, type: 'Private' })),
        ...(tokens.public || []).map(t => ({ t, type: 'Public' })),
    ];
    list.innerHTML = '';
    if (!all.length) {
        list.innerHTML = '<p class="meta">No tokens.</p>';
        return;
    }
    all.forEach(({ t, type }) => {
        const isCurrent = t === current;
        list.appendChild(row(`
            <div class="item-info">
                <span class="item-name">${type} Token ${isCurrent ? '(Active)' : ''}</span>
                <span class="item-meta">${escapeHtml(t.slice(0, 14))}...${escapeHtml(t.slice(-8))}</span>
            </div>
            <div class="item-actions">
                <button class="btn-secondary small" data-action="copy-token" data-token="${escapeHtml(t)}">Copy</button>
                ${isCurrent ? '' : `<button class="btn-secondary small danger" data-action="revoke-token" data-token="${escapeHtml(t)}">Revoke</button>`}
            </div>
        `));
    });
}

function renderStats(project) {
    const fileCount = Object.keys(project.files || {}).length;
    const gvCount = Object.keys(project.global_vars || {}).length;
    const infoCard = document.getElementById('project-info');
    infoCard.querySelector('.stat-summary')?.remove();
    const statBox = document.createElement('div');
    statBox.className = 'stat-summary meta';
    statBox.textContent = `${fileCount} Files | ${gvCount} GVs`;
    infoCard.appendChild(statBox);
}

function projectPath(suffix) {
    return `/projects/${encodeURIComponent(currentProjectId)}${suffix}`;
}

async function downloadFile(alias) {
    const project = await apiFetch('/index');
    if (!project.ok) return showToast(await errorDetail(project), 'error');
    const data = await project.json();
    const record = (Object.values(data.projects || {})[0]?.files || {})[alias];
    const url = record?.url;
    const res = await fetch(url || `${API_BASE}${projectPath(`/files/${encodeURIComponent(alias)}`)}`, {
        headers: url ? {} : { 'Authorization': `Bearer ${localStorage.getItem('s1024_token')}` }
    });
    if (!res.ok) return showToast(await errorDetail(res), 'error');
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = record?.name || alias;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 30000);
}

async function onListAction(event) {
    const button = event.target.closest('button[data-action]');
    if (!button || !currentProjectId) return;
    const { action, alias, token, value } = button.dataset;

    try {
        if (action === 'download') return await downloadFile(alias);
        if (action === 'copy-link') {
            const res = await apiFetch(projectPath('/files'));
            if (!res.ok) return showToast(await errorDetail(res), 'error');
            const data = await res.json();
            return copyText(data.files?.[alias]?.url);
        }
        if (action === 'copy-token') return copyText(token);
        if (action === 'copy-gv') return copyText(value);
        if (action === 'edit-gv') return await showEditGVModal(alias);
        if (action === 'revoke-token') {
            if (!confirm('Revoke this token? Applications using it will break.')) return;
            const res = await apiFetch(projectPath('/tokens/revoke'), {
                method: 'POST', body: JSON.stringify({ token })
            });
            if (!res.ok) return showToast(await errorDetail(res), 'error');
            showToast('Token revoked');
            return fetchAccountData();
        }
        if (action === 'delete-file' || action === 'delete-gv') {
            const kind = action === 'delete-file' ? 'file' : 'variable';
            if (!confirm(`Delete ${kind} "${alias}"?`)) return;
            const suffix = action === 'delete-file'
                ? `/files/${encodeURIComponent(alias)}`
                : `/gv/${encodeURIComponent(alias)}`;
            const res = await apiFetch(projectPath(suffix), { method: 'DELETE' });
            if (!res.ok) return showToast(await errorDetail(res), 'error');
            showToast(`${kind} deleted`);
            return fetchAccountData();
        }
    } catch (err) {
        showToast(`Request failed: ${err.message}`, 'error');
    }
}

function showAddGVModal() {
    document.getElementById('gv-alias').value = '';
    document.getElementById('gv-value').value = '';
    document.getElementById('gv-alias').disabled = false;
    openModal('gv-modal');
}

async function showEditGVModal(alias) {
    const res = await apiFetch(projectPath(`/gv/${encodeURIComponent(alias)}`));
    if (!res.ok) return showToast(await errorDetail(res), 'error');
    const data = await res.json();
    document.getElementById('gv-alias').value = alias;
    document.getElementById('gv-alias').disabled = true;
    document.getElementById('gv-value').value = data.value ?? '';
    openModal('gv-modal');
}

document.getElementById('save-gv-btn').onclick = async () => {
    const alias = document.getElementById('gv-alias').value.trim();
    const value = document.getElementById('gv-value').value;
    if (!alias || !currentProjectId) return showToast('Variable name is required', 'error');
    const res = await apiFetch(projectPath('/gv'), {
        method: 'POST', body: JSON.stringify({ alias, value })
    });
    if (!res.ok) return showToast(await errorDetail(res), 'error');
    showToast('Variable saved');
    closeModal('gv-modal');
    await fetchAccountData();
};

async function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;
    const alias = prompt('File alias (the name your apps will use):', file.name);
    input.value = '';
    if (!alias || !currentProjectId) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('alias', alias);
    showToast(`Uploading ${file.name}...`);
    try {
        const res = await apiFetch(projectPath('/upload'), { method: 'POST', body: formData });
        if (!res.ok) return showToast(await errorDetail(res), 'error');
        showToast('Uploaded!');
        await fetchAccountData();
    } catch (err) {
        showToast(`Upload failed: ${err.message}`, 'error');
    }
}

async function generateNewToken() {
    const type = document.getElementById('token-type').value;
    const res = await apiFetch(projectPath('/tokens'), {
        method: 'POST',
        body: JSON.stringify({ name: document.getElementById('token-alias').value, type })
    });
    if (!res.ok) return showToast(await errorDetail(res), 'error');
    const data = await res.json();
    document.getElementById('generated-token').textContent = data.token;
    openModal('token-modal');
    document.getElementById('token-alias').value = '';
    await fetchAccountData();
}

document.getElementById('signup-btn').onclick = async () => {
    const name = document.getElementById('signup-name-input').value.trim();
    if (!name) return showToast('Account name?', 'error');
    try {
        const res = await fetch(`${API_BASE}/projects/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (!res.ok) return showToast(await errorDetail(res), 'error');
        const data = await res.json();
        document.getElementById('success-priv').textContent = data.tokens.private;
        document.getElementById('success-pub').textContent = data.tokens.public;
        openModal('modal');
        document.getElementById('apply-token-btn').onclick = () => {
            localStorage.setItem('s1024_token', data.tokens.private);
            window.location.reload();
        };
    } catch (err) {
        showToast(`Could not create account: ${err.message}`, 'error');
    }
};

document.getElementById('login-btn').onclick = () => {
    const token = document.getElementById('login-token-input').value.trim();
    if (!token.endsWith(';qi=')) return showToast('The dashboard needs a Private token (;qi=)', 'error');
    localStorage.setItem('s1024_token', token);
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

document.getElementById('generate-token-btn').onclick = generateNewToken;
['file-list', 'gv-list', 'token-list'].forEach(id => {
    document.getElementById(id).addEventListener('click', onListAction);
});
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', event => {
        if (event.target === modal) closeModal(modal.id);
    });
});

checkHoliday();
if (localStorage.getItem('s1024_token')) fetchAccountData();
else setAppState('login');
