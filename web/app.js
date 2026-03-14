const API_BASE = 'https://storage1024.onrender.com/api';

// --- UI Helpers ---
function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${type === 'success' ? '✅' : '❌'}</span> ${msg}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
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

// --- Auth Operations ---
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

// --- Dashboard Logic ---
function renderDashboard(id, p) {
    document.getElementById('user-name').innerText = p.name || "User";
    document.getElementById('project-id-display').innerText = `Account ID: ${id}`;
    
    // Stats
    const fileCount = Object.keys(p.files || {}).length;
    const gvCount = Object.keys(p.global_vars || {}).length;
    document.getElementById('file-stats').innerHTML = `
        <div style="font-size: 2rem; font-weight: 700;">${fileCount}</div> Files Stored
        <div style="font-size: 2rem; font-weight: 700; margin-top: 1rem;">${gvCount}</div> Global Variables
    `;

    // Token Gen Logic
    document.getElementById('generate-token-btn').onclick = () => generateNewToken(id);
}

async function generateNewToken(projectId) {
    const alias = document.getElementById('token-alias').value;
    const isPrivate = document.getElementById('token-is-private').checked;
    const token = localStorage.getItem('s1024_token');

    if (!alias) return showToast("Please name your token!", "error");

    try {
        const res = await fetch(`${API_BASE}/projects/${projectId}/tokens`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name: alias, type: isPrivate ? 'private' : 'public' })
        });
        
        const data = await res.json();
        if (res.status === 200) {
            showToast(`Generated ${isPrivate ? 'Private' : 'Public'} Token!`);
            // Show result temporarily or log to console for user to copy
            console.log("New Token:", data.token);
            prompt("Successfully generated token. Copy it now:", data.token);
        } else {
            showToast(data.detail || "Failed to generate token", "error");
        }
    } catch (err) {
        showToast("Error generating token", "error");
    }
}

// --- Account Creation (Sign Up) ---
document.getElementById('signup-btn').onclick = async () => {
    const name = document.getElementById('signup-name-input').value;
    if (!name) return showToast("Enter a name for your account!", "error");

    try {
        const res = await fetch(`${API_BASE}/projects/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        const data = await res.json();
        if (res.status === 200) {
            document.getElementById('modal').style.display = 'flex';
            document.getElementById('modal-success').style.display = 'block';
            document.getElementById('success-priv').innerText = data.tokens.private;
            
            document.getElementById('apply-token-btn').onclick = () => {
                localStorage.setItem('s1024_token', data.tokens.private);
                window.location.reload();
            };
        }
    } catch (err) {
        showToast("Signup failed. Server offline?", "error");
    }
};

// --- Login Flow ---
document.getElementById('login-btn').onclick = () => {
    const token = document.getElementById('login-token-input').value;
    if (!token) return showToast("Enter your token!", "error");
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

// Initial Load
fetchAccountData();
