const contentDiv = document.getElementById('doc-content');

/* The docs used to depend on a CDN for marked. If that CDN is blocked the
 * whole page showed an error; fall back to a small built-in renderer. */
function renderMarkdown(markdown) {
    if (typeof marked !== 'undefined' && marked.parse) {
        return marked.parse(markdown);
    }
    const esc = s => s.replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
    const inline = s => esc(s)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    const lines = markdown.split('\n');
    const out = [];
    let inCode = false;
    for (const line of lines) {
        if (line.startsWith('```')) {
            out.push(inCode ? '</code></pre>' : '<pre><code>');
            inCode = !inCode;
            continue;
        }
        if (inCode) { out.push(esc(line) + '\n'); continue; }
        if (/^#{1,4}\s/.test(line)) {
            const level = line.match(/^#+/)[0].length;
            out.push(`<h${level}>${inline(line.slice(level).trim())}</h${level}>`);
        } else if (line.startsWith('> ')) {
            out.push(`<blockquote>${inline(line.slice(2))}</blockquote>`);
        } else if (line.startsWith('- ')) {
            out.push(`<li>${inline(line.slice(2))}</li>`);
        } else if (line.startsWith('|')) {
            out.push(`<p>${inline(line)}</p>`);
        } else if (line.trim() === '') {
            out.push('');
        } else {
            out.push(`<p>${inline(line)}</p>`);
        }
    }
    if (inCode) out.push('</code></pre>');
    return out.join('\n');
}

async function loadDoc(lang, btn) {
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
    if (btn) btn.classList.add('active');

    // Only known docs are fetched - no path traversal from the URL hash.
    const allowed = new Set(['story', 'api', 'hosting', 'nocard', 'python', 'go', 'rust', 'php', 'js', 'node',
        'ts', 'cpp', 'csharp', 'java', 'ruby', 'curl', 'bash', 'powershell', 'kotlin']);
    if (!allowed.has(lang)) lang = 'story';

    try {
        const path = lang === 'story' ? '/docs/story.md' : `/docs/langs/${lang}.md`;
        const response = await fetch(path);
        if (!response.ok) throw new Error('Doc not found');
        const markdown = await response.text();
        contentDiv.innerHTML = renderMarkdown(markdown);
        window.history.pushState(null, '', `#${lang}`);
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
    loadDoc(window.location.hash.slice(1) || 'story');
});
