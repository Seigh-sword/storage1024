const API_BASE = 'https://storage1024.onrender.com/api';

function getToken() {
    let token = localStorage.getItem('s1024_token');
    if (!token) {
        token = prompt("Please enter your Storage1024 Token (Private or Public):");
        if (token) localStorage.setItem('s1024_token', token);
    }
    return token;
}

async function fetchIndex() {
    const token = getToken();
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/index`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.status === 401 || res.status === 403) {
            localStorage.removeItem('s1024_token');
            alert("Invalid Token. Please refresh and try again.");
            return;
        }

        const data = await res.json();
        if (data && data.projects) {
            renderProjects(data.projects);
        } else {
            console.error("Invalid data format:", data);
            document.getElementById('projects-grid').innerHTML = '<div class="error">Invalid data returned from server.</div>';
        }
    } catch (err) {
        console.error("Failed to fetch index:", err);
        document.getElementById('projects-grid').innerHTML = '<div class="error">Error connecting to cloud. Is your bridge running?</div>';
    }
}

function renderProjects(projects) {
    const grid = document.getElementById('projects-grid');
    if (!projects) return;
    grid.innerHTML = '';

    Object.entries(projects).forEach(([id, p]) => {
        const card = document.createElement('div');
        card.className = 'project-card';
        card.innerHTML = `
            <div class="meta">#${id}</div>
            <h3>${p.name || 'Unnamed Project'}</h3>
            <div class="meta">Tokens: ${(p.tokens.private?.length || 0) + (p.tokens.public?.length || 0)}</div>
            <div class="token-list">
                Private: ${p.tokens.private?.[0] || 'N/A'}<br>
                Public: ${p.tokens.public?.[0] || 'N/A'}
            </div>
            <div class="meta" style="margin-top: 15px">
                Files: ${Object.keys(p.files || {}).length} | GVs: ${Object.keys(p.global_vars || {}).length}
            </div>
        `;
        grid.appendChild(card);
    });

    if (Object.keys(projects).length === 0) {
        grid.innerHTML = '<div class="meta">No projects found. Create one to get started!</div>';
    }
}

// Modal Logic
const modal = document.getElementById('modal');
const createBtn = document.getElementById('create-project-btn');
const closeBtn = document.getElementById('close-modal');
const confirmBtn = document.getElementById('confirm-create');

createBtn.onclick = () => modal.style.display = 'flex';
closeBtn.onclick = () => {
    modal.style.display = 'none';
    document.getElementById('project-name-input').value = '';
};

confirmBtn.onclick = async () => {
    const name = document.getElementById('project-name-input').value;
    if (!name) return;

    confirmBtn.disabled = true;
    confirmBtn.innerText = 'Creating...';

    try {
        const res = await fetch(`${API_BASE}/projects/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        const data = await res.json();
        if (res.status !== 200) {
            alert("Error: " + (data.detail || "Failed to create project"));
        } else {
            // Show success state
            document.getElementById('modal-form').style.display = 'none';
            document.getElementById('modal-success').style.display = 'block';
            document.getElementById('success-priv').innerText = data.tokens.private;
            document.getElementById('success-pub').innerText = data.tokens.public;
            
            // Setup apply button
            document.getElementById('apply-token-btn').onclick = () => {
                localStorage.setItem('s1024_token', data.tokens.private);
                window.location.reload();
            };
        }
    } catch (err) {
        alert("Network error. Failed to create project.");
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerText = 'Create';
    }
};

// Initial Load
fetchIndex();
