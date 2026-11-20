/* Cavli Module Assistant: embeddable chat widget (PoC).
   Embed:  <script src="https://<assistant-host>/static/widget.js" data-api="https://<assistant-host>" defer></script>
   Everything lives in a Shadow DOM, so the host site's CSS cannot break it and it cannot leak styles into the site. */
(function () {
  const me = document.currentScript;
  const API = ((me && me.dataset.api) || '').replace(/\/$/, '');
  const host = document.createElement('div');
  host.id = 'cavli-assistant-root';
  document.body.appendChild(host);
  const root = host.attachShadow({ mode: 'open' });

  const CSS = `
  :host{all:initial}
  *{box-sizing:border-box}
  .w{--bg:#ffffff;--surface:#f1f3f8;--text:#1b2433;--muted:#6b778a;--line:#e3e8ef;--acc:#1b5fd6;--acc-h:#164fb3;--accfg:#fff;--accsoft:#e8f0fe;
     --warn:#8a5300;--warnbg:#fff6e3;--inf:#3b4a5c;--infbg:#eef3f8;--ok:#22a06b;--shadow:0 16px 48px rgba(20,32,54,.22);
     font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--text)}
  @media (prefers-color-scheme:dark){.w{--bg:#161d29;--surface:#222c3b;--text:#e9eef6;--muted:#9aa8bb;--line:#2c394b;--acc:#4f8ef7;--acc-h:#6ba0f9;--accfg:#0b1220;--accsoft:#1d2b45;
     --warn:#ffcf85;--warnbg:#3a2d14;--inf:#c5d2e0;--infbg:#1f2c3b;--shadow:0 16px 48px rgba(0,0,0,.6)}}
  button{font:inherit;color:inherit}
  .fab{position:fixed;right:24px;bottom:24px;width:60px;height:60px;border-radius:50%;border:0;cursor:pointer;z-index:2147483000;
       background:var(--acc);color:var(--accfg);box-shadow:var(--shadow);display:grid;place-items:center;transition:transform .15s ease,background .15s}
  .fab:hover{transform:scale(1.06);background:var(--acc-h)}
  .fab:focus-visible,.btn:focus-visible,.chip:focus-visible,.ic:focus-visible,.fb button:focus-visible{outline:3px solid var(--acc);outline-offset:2px}
  .fab svg{width:28px;height:28px}
  .tip{position:fixed;right:96px;bottom:36px;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:12px;padding:9px 14px;
       box-shadow:var(--shadow);font-size:14px;z-index:2147483000;animation:fade .4s ease}
  .panel{position:fixed;right:24px;bottom:96px;width:clamp(380px,36vw,540px);height:min(82vh,760px);background:var(--bg);border:1px solid var(--line);
         border-radius:16px;box-shadow:var(--shadow);display:none;flex-direction:column;overflow:hidden;z-index:2147483001}
  .panel.open{display:flex;animation:pop .18s ease-out}
  @keyframes pop{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:none}}
  @keyframes fade{from{opacity:0}to{opacity:1}}
  @media (max-width:640px){.panel{right:0;bottom:0;left:0;top:0;width:auto;height:auto;border-radius:0;border:0}.fab{right:16px;bottom:16px}.tip{display:none}}
  header{display:flex;align-items:center;gap:12px;padding:14px 14px 14px 16px;background:var(--bg);border-bottom:1px solid var(--line)}
  .av{flex:none;width:36px;height:36px;border-radius:50%;background:var(--acc);color:var(--accfg);display:grid;place-items:center}
  .av svg{width:20px;height:20px}
  header h2{margin:0;font-size:15.5px;line-height:1.25;font-weight:650}
  header p{margin:1px 0 0;font-size:12.5px;color:var(--muted);display:flex;align-items:center;gap:6px}
  header p i{width:8px;height:8px;border-radius:50%;background:var(--ok);display:inline-block}
  .grow{flex:1;min-width:0}
  .ic{border:0;background:transparent;color:var(--muted);cursor:pointer;border-radius:8px;width:34px;height:34px;display:grid;place-items:center}
  .ic:hover{background:var(--surface);color:var(--text)}.ic svg{width:19px;height:19px}
  .body{flex:1;overflow-y:auto;padding:18px 16px 8px;display:flex;flex-direction:column;gap:16px;scroll-behavior:smooth;background:var(--bg)}
  .row{display:flex;gap:10px;align-items:flex-start}.row.u{justify-content:flex-end}
  .row .av{width:30px;height:30px;margin-top:2px}.row .av svg{width:17px;height:17px}
  .col{min-width:0;max-width:calc(100% - 42px)}
  .bub{border-radius:16px;padding:10px 14px;overflow-wrap:anywhere}
  .u .bub{background:var(--acc);color:var(--accfg);border-bottom-right-radius:4px;max-width:88%}
  .a .bub{background:var(--surface);border-top-left-radius:4px}
  .a .bub.nv{background:var(--warnbg);color:var(--text)}
  .bub p{margin:0 0 8px}.bub p:last-child{margin-bottom:0}
  .bub ul{margin:4px 0 8px;padding-left:22px}.bub li{margin:3px 0}
  a.cite{display:inline-block;min-width:19px;text-align:center;font-size:11.5px;font-weight:600;line-height:17px;border-radius:9px;padding:0 5px;margin:0 2px;
         background:var(--acc);color:var(--accfg);text-decoration:none;vertical-align:1px}
  a.cite:hover{background:var(--acc-h)}
  .note{margin-top:10px;padding:8px 10px;border-radius:10px;font-size:13.5px}
  .note.inf{background:var(--infbg);color:var(--inf)}.note.warn{background:var(--warnbg);color:var(--warn);border:1px solid rgba(217,154,43,.35)}
  .note b{font-weight:650}
  .q{margin-top:10px;font-weight:600}
  .srcs{margin-top:8px}
  .srcs .t{font-size:11.5px;color:var(--muted);margin:0 0 5px 2px}
  .chipsrow{display:flex;flex-wrap:wrap;gap:6px}
  .src{display:inline-flex;gap:6px;align-items:center;max-width:100%;font-size:12.5px;color:var(--text);text-decoration:none;background:var(--bg);
       border:1px solid var(--line);border-radius:999px;padding:3px 10px 3px 4px}
  .src:hover{border-color:var(--acc);background:var(--accsoft)}
  .src .n{flex:none;min-width:20px;height:20px;text-align:center;border-radius:10px;background:var(--acc);color:var(--accfg);font-size:11.5px;font-weight:600;line-height:20px;padding:0 4px}
  .src .n.o{background:var(--surface);color:var(--muted)}
  .src .l{flex:none;max-width:62%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .src small{min-width:0;color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .meta{margin-top:6px;display:flex;align-items:center;gap:10px;color:var(--muted);font-size:11.5px;padding-left:2px}
  .fb{display:flex;gap:2px;align-items:center}
  .fb button{border:0;background:transparent;border-radius:6px;cursor:pointer;padding:2px 6px;font-size:14px;opacity:.65}
  .fb button:hover{opacity:1;background:var(--surface)}
  .reading{margin-top:6px;color:var(--muted);font-size:12.5px}
  .dots{display:inline-flex;gap:4px;padding:6px 0 4px}.dots i{width:7px;height:7px;border-radius:50%;background:var(--muted);animation:b 1.2s infinite}
  .dots i:nth-child(2){animation-delay:.15s}.dots i:nth-child(3){animation-delay:.3s}
  @keyframes b{0%,60%,100%{opacity:.3;transform:none}30%{opacity:1;transform:translateY(-3px)}}
  .chips{display:flex;flex-wrap:wrap;gap:8px;margin:2px 0 0 40px}
  .chip{text-align:left;border:1px solid var(--acc);background:var(--bg);color:var(--acc);border-radius:999px;padding:7px 13px;font-size:13.5px;cursor:pointer}
  .chip:hover{background:var(--accsoft)}
  footer{padding:10px 14px 8px;background:var(--bg)}
  form{display:flex;gap:8px;align-items:flex-end;border:1px solid var(--line);background:var(--bg);border-radius:24px;padding:5px 5px 5px 14px}
  form:focus-within{border-color:var(--acc);box-shadow:0 0 0 3px var(--accsoft)}
  textarea{flex:1;resize:none;border:0;background:transparent;color:var(--text);padding:8px 0;font:inherit;max-height:120px;min-height:36px;outline:none}
  .btn{flex:none;width:38px;height:38px;border-radius:50%;border:0;background:var(--acc);color:var(--accfg);cursor:pointer;display:grid;place-items:center}
  .btn:hover:not(:disabled){background:var(--acc-h)}
  .btn:disabled{opacity:.4;cursor:default}.btn svg{width:18px;height:18px}
  .fine{margin:7px 6px 0;color:var(--muted);font-size:11px;line-height:1.4;text-align:center}
  `;

  const ICON_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-5.4A8 8 0 1 1 21 12z"/></svg>';
  const ICON_X = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
  const ICON_SEND = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.4 20.4l17.5-7.5a1 1 0 0 0 0-1.8L3.4 3.6a1 1 0 0 0-1.4 1.2L4 11l9 1-9 1-2 6.2a1 1 0 0 0 1.4 1.2z"/></svg>';
  const ICON_NEW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>';
  const ICON_BOT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/></svg>';
  const EXAMPLES = ['What speed does the C16QS support?', 'Compare the operating temperature of the CQ16 and the C16QS',
    'I need a module for a battery-powered smart meter with GNSS', 'Which module supports 5G?'];
  const WELCOME = "Hi, I'm the Cavli module assistant. Ask me about Cavli IoT modules such as C16QS, CQM220, CQS315 or AQ62, or tell me what you need and I'll suggest options.";

  root.innerHTML = `<style>${CSS}</style><div class="w">
    <div class="tip" id="tip">Ask about Cavli IoT modules</div>
    <button class="fab" id="fab" aria-label="Open Cavli module assistant" aria-expanded="false">${ICON_CHAT}</button>
    <section class="panel" id="panel" role="dialog" aria-label="Cavli module assistant">
      <header><div class="av" aria-hidden="true">${ICON_BOT}</div>
        <div class="grow"><h2>Cavli Module Assistant</h2><p><i></i>Answers only from approved public sources</p></div>
        <button class="ic" id="new" aria-label="Start a new chat" title="New chat">${ICON_NEW}</button>
        <button class="ic" id="close" aria-label="Close assistant" title="Close">${ICON_X}</button></header>
      <div class="body" id="body" aria-live="polite"></div>
      <footer><form id="f"><textarea id="q" rows="1" maxlength="500" placeholder="Type your question…" aria-label="Your question"></textarea>
        <button class="btn" id="send" aria-label="Send">${ICON_SEND}</button></form>
        <p class="fine">AI answers can contain mistakes. Check the numbered sources, and please don't enter personal information.</p></footer>
    </section></div>`;

  const $ = (id) => root.getElementById(id);
  const h = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  const panel = $('panel'), body = $('body'), q = $('q'), send = $('send'), fab = $('fab');
  let busy = false;

  function botRow() {
    const r = h('div', 'row a'), av = h('div', 'av'), col = h('div', 'col'), bub = h('div', 'bub');
    av.innerHTML = ICON_BOT; col.appendChild(bub); r.append(av, col); body.appendChild(r);
    return { r, col, bub };
  }
  function welcome() {
    body.textContent = '';
    botRow().bub.textContent = WELCOME;
    const chips = h('div', 'chips', null); chips.id = 'chips';
    EXAMPLES.forEach((t) => { const b = h('button', 'chip', t); b.onclick = () => ask(t); chips.appendChild(b); });
    body.appendChild(chips);
  }
  welcome();

  function toggle(open) {
    panel.classList.toggle('open', open);
    fab.setAttribute('aria-expanded', open);
    fab.innerHTML = open ? ICON_X : ICON_CHAT;
    $('tip').style.display = 'none';
    if (open) setTimeout(() => q.focus(), 50);
  }
  fab.onclick = () => toggle(!panel.classList.contains('open'));
  $('close').onclick = () => toggle(false);
  $('new').onclick = () => { if (!busy) welcome(); };
  root.addEventListener('keydown', (e) => { if (e.key === 'Escape') toggle(false); });
  setTimeout(() => { const t = $('tip'); if (t && !panel.classList.contains('open')) t.style.display = 'none'; }, 9000);

  q.addEventListener('input', () => { q.style.height = 'auto'; q.style.height = Math.min(q.scrollHeight, 120) + 'px'; });
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('f').requestSubmit(); } });
  $('f').onsubmit = (e) => { e.preventDefault(); const t = q.value.trim(); if (t && !busy) { q.value = ''; q.style.height = 'auto'; ask(t); } };

  // ---- safe rich text: **bold**, lists, [n] source links (DOM nodes only, never innerHTML) ----
  function inline(parent, text, cites) {
    text.split(/(\*\*[^*]+\*\*|\[\d+\])/).forEach((p) => {
      if (!p) return;
      const k = p.match(/^\[(\d+)\]$/);
      if (p.startsWith('**') && p.endsWith('**') && p.length > 4) parent.appendChild(h('strong', '', p.slice(2, -2)));
      else if (k && cites[+k[1]]) {
        const a = h('a', 'cite', k[1]); a.href = cites[+k[1]].url; a.target = '_blank'; a.rel = 'noopener';
        a.title = cites[+k[1]].title + (cites[+k[1]].section ? ' › ' + cites[+k[1]].section : ''); parent.appendChild(a);
      } else parent.appendChild(document.createTextNode(p));
    });
  }
  function rich(node, text, cites) {
    node.textContent = ''; let list = null;
    text.split('\n').forEach((line) => {
      const m = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/);
      if (m) { if (!list) { list = h('ul'); node.appendChild(list); } const li = h('li'); inline(li, m[1], cites); list.appendChild(li); }
      else { list = null; if (!line.trim()) return; const p = h('p'); inline(p, line, cites); node.appendChild(p); }
    });
  }
  const label = (c) => c.title.split('|')[0].trim();

  function srcChip(c, numbered) {
    const a = h('a', 'src'); a.href = c.url; a.target = '_blank'; a.rel = 'noopener';
    a.title = label(c) + (c.section ? ' › ' + c.section : '');
    a.appendChild(h('span', 'n' + (numbered ? '' : ' o'), numbered ? String(c.n) : '↗'));
    a.appendChild(h('span', 'l', label(c) + (c.page ? ` (p.${c.page})` : '')));
    if (c.section && numbered) a.appendChild(h('small', '', '› ' + c.section));
    return a;
  }

  function finish(col, bub, d) {
    bub.querySelector('.dots') && bub.querySelector('.dots').remove();
    const by = {}; d.citations.forEach((c) => (by[c.n] = c));
    let ans = bub.querySelector('.ans'); if (!ans) { ans = h('div', 'ans'); bub.prepend(ans); }
    rich(ans, d.answer, by);
    bub.classList.toggle('nv', !d.supported && ['not_verified', 'out_of_scope'].includes(d.kind));
    const rd = bub.querySelector('.reading'); if (rd) rd.remove();
    if (d.inference) { const n = h('div', 'note inf'); n.appendChild(h('b', '', 'Inference: ')); n.append(d.inference + ' (not stated in the sources)'); bub.appendChild(n); }
    if (d.unverified && d.unverified.length) { const n = h('div', 'note warn'); n.appendChild(h('b', '', 'Not verified in sources: ')); n.append(d.unverified.join(', ')); bub.appendChild(n); }
    if (d.follow_up_question) bub.appendChild(h('div', 'q', d.follow_up_question));
    if (d.citations.length || d.links.length) {
      const s = h('div', 'srcs'); s.appendChild(h('div', 't', d.citations.length ? 'Sources' : 'Helpful links'));
      const row = h('div', 'chipsrow');
      d.citations.forEach((c) => row.appendChild(srcChip(c, true)));
      d.links.forEach((c) => row.appendChild(srcChip({ title: c.title, url: c.url }, false)));
      s.appendChild(row); col.appendChild(s);
    }
    const L = d.latency_ms || {}, meta = h('div', 'meta');
    if (L.total) meta.appendChild(h('span', '', (L.total / 1000).toFixed(1) + ' s' + (L.first_token ? ` · first word ${(L.first_token / 1000).toFixed(1)} s` : '')));
    if (['answer', 'not_verified', 'out_of_scope'].includes(d.kind)) {
      const fb = h('span', 'fb');
      [['👍', 1], ['👎', -1]].forEach(([t, v]) => { const b = h('button', '', t); b.setAttribute('aria-label', v > 0 ? 'Helpful' : 'Not helpful');
        b.onclick = async () => { try { await fetch(API + '/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ request_id: d.request_id, rating: v }) }); } catch (e) {} fb.textContent = 'Thanks for your feedback'; }; fb.appendChild(b); });
      meta.appendChild(fb);
    }
    col.appendChild(meta);
  }

  async function ask(text) {
    if (busy) return; busy = true; send.disabled = true;
    const chips = $('chips'); if (chips) chips.remove();
    const u = h('div', 'row u'); u.appendChild(h('div', 'bub', text)); body.appendChild(u);
    const { col, bub } = botRow();
    const ans = h('div', 'ans'); const dots = h('div', 'dots'); dots.innerHTML = '<i></i><i></i><i></i>';
    bub.append(ans, dots); const reading = h('div', 'reading'); bub.appendChild(reading);
    const down = () => { body.scrollTop = body.scrollHeight; }; down();
    let acc = '', cites = {}, first = true;
    try {
      const resp = await fetch(API + '/api/chat/stream', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: text }) });
      if (!resp.ok) { const d = await resp.json().catch(() => ({})); dots.remove(); ans.textContent = (d.detail && d.detail.message) || 'Something went wrong. Please try again.'; return; }
      const rd = resp.body.getReader(), dec = new TextDecoder(); let buf = '';
      for (;;) {
        const { done, value } = await rd.read(); if (done) break;
        buf += dec.decode(value, { stream: true }); let i;
        while ((i = buf.indexOf('\n\n')) >= 0) {
          const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2); if (!line) continue;
          const ev = JSON.parse(line);
          if (ev.type === 'sources') reading.textContent = 'Reading: ' + ev.sources.map((s) => label(s)).filter((v, k, a) => a.indexOf(v) === k).join(' · ');
          else if (ev.type === 'cite') cites[ev.n] = ev;
          else if (ev.type === 'token') { if (first) { first = false; dots.remove(); } acc += ev.text; rich(ans, acc, cites); down(); }
          else if (ev.type === 'error') { dots.remove(); ans.textContent = ev.message; }
          else if (ev.type === 'final') { finish(col, bub, ev); down(); }
        }
      }
    } catch (err) { dots.remove(); ans.textContent = 'Could not reach the assistant. Please check your connection and try again.'; }
    finally { busy = false; send.disabled = false; q.focus(); }
  }
})();
