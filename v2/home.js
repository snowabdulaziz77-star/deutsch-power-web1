import {S, today, dxp, due, rank, week, words, save, QUESTS} from './store.js';
import {esc, mascot, speak, hap} from './ui.js';

export function render(el) {
  const d = dxp(), goal = S.goal, p = Math.min(d / goal, 1), w = words();
  const dw = w[+today().replace(/-/g, '') % w.length], wk = week(), max = Math.max(goal, ...wk.map(x => x.xp));
  const left = S.exam ? Math.ceil((Date.parse(S.exam) - Date.parse(today())) / 864e5) : null;
  const mood = p >= 1 ? 'cheer' : d === 0 ? 'sleep' : 'happy';
  const msg = p >= 1 ? 'Bugungi maqsad bajarildi! 🎉' : d === 0 ? 'Bugun hali o‘qimadingiz, boshlaymizmi?' : `Yana ${goal - d} XP qoldi, zo‘r ketyapsiz!`;
  const name = (window.Telegram?.WebApp?.initDataUnsafe?.user?.first_name) || 'Do‘st';
  const dark = document.documentElement.dataset.theme === 'dark' || (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches);
  el.innerHTML = `<div class="pop">
  <div class="top"><div class="grow"><div class="mute">Salom 👋</div><h1 style="font-size:22px">${esc(name)}</h1></div>
    <div class="pill" title="Streak">🔥 ${S.streak}</div><div class="pill" title="Streak Freeze">🧊 ${S.freeze}</div><div class="pill" title="XP">⭐ ${S.xp}</div>
    <button class="icon" data-a="theme" aria-label="Rejim">${dark ? '☀️' : '🌙'}</button></div>
  <div class="hello">${mascot(mood)}<div class="bubble">${msg}</div></div>
  <div class="card hero"><h2 style="margin:0 0 4px">⚡ Tezkor dars</h2><p class="mute" style="margin-bottom:14px">5 daqiqa: takrorlash, yangi so‘zlar va quiz</p><button class="btn" data-a="go" data-t="learn">BOSHLASH</button></div>
  <div class="card"><div class="row" style="margin-bottom:8px"><b class="grow">Kunlik maqsad</b><span class="mute">${Math.min(d, goal)} / ${goal} XP</span></div>
    <div class="bar acc"><i style="width:${p * 100}%"></i></div>
    <div class="row" style="margin-top:12px">${[20, 50, 100].map(g => `<button class="chip ${g === goal ? 'on' : ''}" data-a="goal" data-g="${g}">${g === 20 ? '🌱' : g === 50 ? '⚡' : '🔥'} ${g}</button>`).join('')}</div></div>
  <div class="card"><b>Bugungi topshiriqlar</b>${QUESTS.map(q => { const v = S.quest.p[q.id] || 0, done = v >= q.n;
    return `<div class="q ${done ? 'done' : ''}"><div class="ic">${done ? '✅' : q.ic}</div><div class="grow"><div style="font-weight:800">${q.t}</div><div class="bar" style="height:8px;margin-top:6px"><i style="width:${v / q.n * 100}%"></i></div></div><small>${v}/${q.n}</small></div>`; }).join('')}</div>
  <div class="card"><div class="row" style="margin-bottom:12px"><b class="grow">Bu hafta</b><span class="mute">🔥 ${S.streak} kun</span></div>
    <div class="week">${wk.map(x => `<div class="day ${x.xp > 0 ? 'on' : ''} ${x.today ? 'today' : ''}"><i>${x.xp > 0 ? '✓' : ''}</i>${x.l}</div>`).join('')}</div></div>
  <div class="row"><div class="card grow" style="cursor:pointer" data-a="go" data-t="learn"><div style="font-size:26px">🔁</div><b>Takrorlash</b><div class="mute">${due()} ta so‘z kutyapti</div></div>
    <div class="card grow" id="exam"><div style="font-size:26px">🎓</div><b>Goethe B2</b>${left === null ? `<input class="date" type="date" data-a="exam" aria-label="Imtihon sanasi">` : `<div class="mute">${left > 0 ? left + ' kun qoldi' : left === 0 ? 'Bugun imtihon! 💪' : 'Imtihon o‘tdi'}</div>`}</div></div>
  <h2>Kun so‘zi</h2><div class="card row"><div class="grow"><div style="font-size:22px;font-weight:800">${esc(dw[0])}</div><div style="color:var(--pri);font-weight:800">${esc(dw[1])}</div><div class="mute"><i>${esc(dw[2])}</i></div></div><button class="icon" data-a="say" data-w="${esc(dw[0])}" aria-label="Talaffuz">🔊</button></div>
  <h2>Haftalik XP</h2><div class="card"><div class="chart">${wk.map(x => `<div><b style="height:${x.xp / max * 100}%"></b>${x.l}</div>`).join('')}</div></div></div>`;
  el.onclick = e => { const b = e.target.closest('[data-a]'); if (!b) return; hap(); const a = b.dataset.a;
    if (a === 'go') dispatchEvent(new CustomEvent('go', {detail: b.dataset.t}));
    if (a === 'say') speak(b.dataset.w);
    if (a === 'goal') { S.goal = +b.dataset.g; save(); render(el); }
    if (a === 'theme') { document.documentElement.dataset.theme = dark ? 'light' : 'dark'; S.theme = document.documentElement.dataset.theme; save(); render(el); } };
  el.onchange = e => { if (e.target.dataset.a === 'exam' && e.target.value) { S.exam = e.target.value; save(); render(el); } };
}
