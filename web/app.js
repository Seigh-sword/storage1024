const API_BASE = 'http://127.0.0.1:8000/api';

async function fetchIndex() {
    try {
        const res = await fetch(`${API_BASE}/index`);
        const data = await res.json();
        renderProjects(data.projects);
    } catch (err) {
        console.error("Failed to fetch index:", err);
        document.getElementById('projects-grid').innerHTML = '<div class="error">Error connecting to Telegram. Is bridge.py running?</div>';
    }
}

function renderProjects(projects) {
    const grid = document.getElementById('projects-grid');
    grid.innerHTML = '';

    Object.entries(projects).forEach(([id, p]) => {
        const card = document.createElement('div');
        card.className = 'project-card';
        card.innerHTML = `
            <div class="meta">#${id}</div>
            <h3>${p.name}</h3>
            <div class="meta">Tokens: ${p.tokens.private.length + p.tokens.public.length}</div>
            <div class="token-list">
                Private: ${p.tokens.private[0]}<br>
                Public: ${p.tokens.public[0]}
            </div>
            <div class="meta" style="margin-top: 15px">
                Files: ${Object.keys(p.files).length} | GVs: ${Object.keys(p.global_vars).length}
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
closeBtn.onclick = () => modal.style.display = 'none';

confirmBtn.onclick = async () => {
    const name = document.getElementById('project-name-input').value;
    if (!name) return;

    confirmBtn.disabled = true;
    confirmBtn.innerText = 'Creating...';

    try {
        await fetch(`${API_BASE}/projects/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        modal.style.display = 'none';
        document.getElementById('project-name-input').value = '';
        fetchIndex();
    } catch (err) {
        alert("Failed to create project.");
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerText = 'Create';
    }
};

// Initial Load
fetchIndex();
