import {S} from './store.js';
import {ready} from './data.js';
import {render as home} from './home.js';

const tg = window.Telegram && window.Telegram.WebApp;
if (tg) { tg.ready(); tg.expand(); }
if (S.theme) document.documentElement.dataset.theme = S.theme; else if (tg && tg.colorScheme) document.documentElement.dataset.theme = tg.colorScheme;

const soon = (title, day) => el => { el.innerHTML = `<div class="pop card" style="text-align:center;margin-top:40px"><div style="font-size:54px">🚧</div><h2>${title}</h2><p class="mute">${day}-kunda yangilanadi</p></div>`; };
const TABS = [['home','🏠','Bosh',home],['learn','📚','O‘rganish',soon('O‘rganish', 2)],['game','🎮','O‘yin',soon('O‘yin', 3)],['vocab','🔤','Lug‘at',soon('Lug‘at', 5)],['me','👤','Profil',soon('Profil', 7)]];
let tab = 'home';
function go(t) { tab = t;
  document.getElementById('nav').innerHTML = TABS.map(x => `<button class="${x[0] === t ? 'on' : ''}" data-t="${x[0]}" aria-label="${x[2]}"><span>${x[1]}</span>${x[2]}</button>`).join('');
  TABS.find(x => x[0] === t)[3](document.getElementById('view')); window.scrollTo(0, 0); }
document.getElementById('nav').onclick = e => { const b = e.target.closest('[data-t]'); if (b) go(b.dataset.t); };
addEventListener('go', e => go(e.detail));
go('home'); ready.then(() => { if (tab === 'home') go('home'); });
