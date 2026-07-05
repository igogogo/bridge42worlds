const SUPABASE_URL = 'https://gyfdyfbuolnciaqxgybx.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZmR5ZmJ1b2xuY2lhcXhneWJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3OTk0MzQsImV4cCI6MjA5ODM3NTQzNH0.rKsgWoj5ubRpkvElPfELOn-G9StW5RSOkxBbpvFyWc4';

let supabase = null;
let likeLock = false;

async function getSupabase() {
    if (supabase) return supabase;
    const { createClient } = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm');
    supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
    return supabase;
}

async function loadLikes(articleId) {
    const sb = await getSupabase();
    const { count } = await sb.from('likes').select('*', { count: 'exact', head: true }).eq('article_id', articleId);
    const el = document.getElementById(`like-count-${articleId}`);
    if (el) el.textContent = count || 0;
}

function hasLiked(articleId) {
    try { return localStorage.getItem(`liked_${articleId}`) === 'true'; } catch { return false; }
}

async function toggleLike(articleId) {
    if (likeLock) return;
    likeLock = true;

    const sb = await getSupabase();
    const btn = document.querySelector(`[data-article-id="${articleId}"] .like-btn`);

    if (hasLiked(articleId)) {
        localStorage.removeItem(`liked_${articleId}`);
        if (btn) btn.classList.remove('liked');
        loadLikes(articleId);
        setTimeout(() => { likeLock = false; }, 1000);
        return;
    }

    const { error } = await sb.from('likes').insert({ article_id: articleId });
    if (!error) {
        try { localStorage.setItem(`liked_${articleId}`, 'true'); } catch {}
        if (btn) btn.classList.add('liked');
        loadLikes(articleId);
    }
    setTimeout(() => { likeLock = false; }, 2000);
}

function shareArticle(title, url) {
    if (navigator.share) {
        navigator.share({ title, url });
    } else {
        navigator.clipboard.writeText(url).then(() => alert('Link copied!'));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-article-id]').forEach(el => {
        const id = el.dataset.articleId;
        loadLikes(id);
        if (hasLiked(id)) el.querySelector('.like-btn')?.classList.add('liked');
    });
});