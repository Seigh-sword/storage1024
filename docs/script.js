const contentDiv = document.getElementById('doc-content');

async function loadDoc(lang, btn) {
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
    if (btn) btn.classList.add('active');

    try {
        const path = lang === 'story' ? 'story.md' : `langs/${lang}.md`;
        const response = await fetch(path);
        if (!response.ok) throw new Error('Doc not found');
        
        const markdown = await response.text();
        contentDiv.innerHTML = marked.parse(markdown);
        
        window.history.pushState(null, null, `#${lang}`);
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
    } catch (err) {
        contentDiv.innerHTML = `<h2>Error</h2><p>Could not load documentation for <strong>${lang}</strong>.</p>`;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    const hash = window.location.hash.slice(1) || 'story';
    const targetBtn = Array.from(document.querySelectorAll('.sidebar-link'))
                           .find(b => b.getAttribute('onclick')?.includes(`'${hash}'`));
    loadDoc(hash, targetBtn);
});

window.addEventListener('popstate', () => {
    const hash = window.location.hash.slice(1) || 'story';
    loadDoc(hash);
});
