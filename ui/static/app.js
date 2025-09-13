document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('rl-form');
  const result = document.getElementById('result');
  const verdict = document.getElementById('verdict');
  const hLimit = document.getElementById('h-limit');
  const hRemain = document.getElementById('h-remaining');
  const hReset = document.getElementById('h-reset');
  const hRetry = document.getElementById('h-retry');
  const jsonEl = document.getElementById('json');
  const curlEl = document.getElementById('curl');
  const copyCurlBtn = document.getElementById('copy-curl');
  const meterFill = document.getElementById('meter-fill');
  const meterText = document.getElementById('meter-text');
  const healthBadge = document.getElementById('health-badge');
  const themeToggle = document.getElementById('theme-toggle');
  const revealKeyBtn = document.getElementById('reveal-key');
  const checkBtn = document.getElementById('check-btn');
  const history = document.getElementById('history');

  // Theme
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'light') document.body.classList.add('light');
  themeToggle?.addEventListener('click', () => {
    document.body.classList.toggle('light');
    localStorage.setItem('theme', document.body.classList.contains('light') ? 'light' : 'dark');
  });

  // Health ping
  (async () => {
    try {
      const r = await fetch('/v1/health');
      if (r.ok) {
        const body = await r.json();
        healthBadge.textContent = `Online v${body.version || ''}`.trim();
        healthBadge.classList.remove('muted');
        healthBadge.classList.add('ok');
      } else {
        healthBadge.textContent = 'Degraded';
      }
    } catch {
      healthBadge.textContent = 'Offline';
    }
  })();

  // Examples (pills)
  document.querySelectorAll('[data-example-resource]')?.forEach(el => {
    el.addEventListener('click', () => {
      document.getElementById('resource').value = el.getAttribute('data-example-resource');
    });
  });
  document.querySelectorAll('[data-example-subject]')?.forEach(el => {
    el.addEventListener('click', () => {
      document.getElementById('subject').value = el.getAttribute('data-example-subject');
    });
  });

  // Reveal key
  revealKeyBtn?.addEventListener('click', () => {
    const el = document.getElementById('api_key');
    el.type = el.type === 'password' ? 'text' : 'password';
    revealKeyBtn.textContent = el.type === 'password' ? 'Show' : 'Hide';
  });

  // Copy curl
  copyCurlBtn?.addEventListener('click', async () => {
    if (!curlEl?.textContent) return;
    try { await navigator.clipboard.writeText(curlEl.textContent); copyCurlBtn.textContent = 'Copied!'; setTimeout(()=>copyCurlBtn.textContent='Copy curl', 1200); } catch {}
  });

  // History helpers
  const addHistory = ({ allowed, remaining, limit, subject }) => {
    if (!history) return;
    const item = document.createElement('div');
    item.className = 'item';
    const now = new Date();
    const time = now.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit', second:'2-digit' });
    item.innerHTML = `<span>${time}</span><span>${subject}</span><span>${remaining}/${limit}</span><strong class="${allowed ? 'ok' : 'no'}">${allowed ? 'ALLOWED' : 'BLOCKED'}</strong>`;
    history.prepend(item);
    // Keep up to 10
    while (history.children.length > 10) history.removeChild(history.lastChild);
  };

  // Submit handler
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const apiKey = document.getElementById('api_key').value.trim();
    const resource = document.getElementById('resource').value.trim();
    const subject = document.getElementById('subject').value.trim();
    const cost = parseInt(document.getElementById('cost').value || '1', 10);
    if (!apiKey) { alert('API key is required'); return; }
    const payload = { resource, subject, cost };

    // curl snippet
    const origin = window.location.origin;
    const curl = [
      'curl -i -X POST',
      `${origin}/v1/check`,
      `-H "X-API-Key: ${apiKey}"`,
      "-H 'Content-Type: application/json'",
      `-d '${JSON.stringify(payload)}'`
    ].join(' \\n+  ');
    curlEl.textContent = curl;

    try {
      verdict.className = 'verdict pending';
      verdict.textContent = 'Checking…';
      checkBtn.classList.add('loading');

      const res = await fetch('/v1/check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify(payload),
      });

      const limit = Number(res.headers.get('X-RateLimit-Limit')) || 0;
      const remaining = Number(res.headers.get('X-RateLimit-Remaining')) || 0;
      const reset = res.headers.get('X-RateLimit-Reset');
      const retry = res.headers.get('Retry-After');

      let body;
      try { body = await res.json(); } catch (_) { body = { error: `HTTP ${res.status}` }; }

      hLimit.textContent = String(limit || body?.limit || '-');
      hRemain.textContent = String(remaining || body?.remaining || '-');
      hReset.textContent = reset ?? String(body?.reset_at ?? '-');
      hRetry.textContent = retry ?? (body?.retry_after_ms != null ? Math.ceil(body.retry_after_ms/1000) : '-');
      jsonEl.textContent = JSON.stringify(body, null, 2);

      // Meter
      const lim = body?.limit ?? limit;
      const rem = body?.remaining ?? remaining;
      if (lim && rem != null) {
        const pct = Math.max(0, Math.min(100, Math.round((rem/lim)*100)));
        meterFill.style.width = pct + '%';
        meterText.textContent = `Remaining ${rem}/${lim}`;
      } else {
        meterFill.style.width = '0%';
        meterText.textContent = 'Remaining —';
      }

      result.classList.remove('hidden');
      if (res.ok && body && body.allowed) {
        verdict.className = 'verdict allowed';
        verdict.textContent = 'ALLOWED';
      } else if (res.status === 429) {
        verdict.className = 'verdict blocked';
        verdict.textContent = 'BLOCKED';
      } else if (res.ok) {
        verdict.className = 'verdict blocked';
        verdict.textContent = 'BLOCKED';
      } else {
        verdict.className = 'verdict error';
        verdict.textContent = `ERROR ${res.status}`;
      }

      // History
      if (body && typeof body.allowed === 'boolean') {
        addHistory({ allowed: body.allowed, remaining: body.remaining, limit: body.limit, subject });
      }
    } catch (err) {
      result.classList.remove('hidden');
      verdict.className = 'verdict error';
      verdict.textContent = 'NETWORK ERROR';
      jsonEl.textContent = String(err);
      meterFill.style.width = '0%';
      meterText.textContent = 'Remaining —';
    } finally {
      checkBtn.classList.remove('loading');
    }
  });
});
