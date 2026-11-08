export const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tg = window.Telegram && window.Telegram.WebApp;
export const hap = t => { try { if (!tg || !tg.HapticFeedback) return; t === 'ok' ? tg.HapticFeedback.notificationOccurred('success') : tg.HapticFeedback.impactOccurred('light'); } catch (e) {} };
export const speak = t => { try { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.lang = 'de-DE'; u.rate = .9; speechSynthesis.speak(u); } catch (e) {} };
export function toast(t) { const d = document.createElement('div'); d.className = 'toast'; d.textContent = t; document.body.append(d); setTimeout(() => d.remove(), 2200); }
export function confetti() { hap('ok');
  for (let i = 0; i < 28; i++) { const e = document.createElement('div'); e.className = 'conf'; e.textContent = ['🎉','⭐','🥨','✨'][i % 4];
    e.style.left = Math.random() * 100 + 'vw'; e.style.animationDelay = Math.random() * .5 + 's'; document.body.append(e); setTimeout(() => e.remove(), 2600); } }
// Brezel 🥨 maskoti: kayfiyati o'zgaradi (happy | cheer | sleep)
export function mascot(mood = 'happy', s = 84) {
  const eyes = mood === 'sleep' ? '<path d="M42 70h12M66 70h12" stroke="#4a2a0a" stroke-width="4" stroke-linecap="round"/>'
    : mood === 'cheer' ? '<path d="M42 72q6-9 12 0M66 72q6-9 12 0" fill="none" stroke="#4a2a0a" stroke-width="4" stroke-linecap="round"/>'
    : '<circle cx="48" cy="70" r="5" fill="#4a2a0a"/><circle cx="72" cy="70" r="5" fill="#4a2a0a"/>';
  const mouth = mood === 'cheer' ? '<path d="M50 80q10 16 20 0z" fill="#4a2a0a"/>' : mood === 'sleep' ? '<path d="M56 84h8" stroke="#4a2a0a" stroke-width="4" stroke-linecap="round"/>' : '<path d="M50 82q10 9 20 0" fill="none" stroke="#4a2a0a" stroke-width="4" stroke-linecap="round"/>';
  return `<svg width="${s}" height="${s}" viewBox="0 0 120 120" aria-hidden="true"><path d="M28 90C6 62 24 22 60 42c36-20 54 20 32 48-8 10-20 18-32 18S36 100 28 90Z" fill="#d9923b" stroke="#a9651b" stroke-width="5" stroke-linejoin="round"/><path d="M44 52c8 14 24 14 32 0" fill="none" stroke="#f3c47a" stroke-width="6" stroke-linecap="round" opacity=".7"/>${eyes}${mouth}${mood === 'sleep' ? '<text x="88" y="38" font-size="18" fill="#7a77a0" font-weight="800">z</text>' : ''}</svg>`;
}
