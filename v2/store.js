// Holat va saqlash. Hamma bo'limlar faqat shu fayl orqali XP, streak va topshiriqlarni o'zgartiradi.
// 7-kunda sync() ichiga bot serveriga yuborish qo'shiladi, boshqa fayllarga tegmaymiz.
import {V} from './data.js';
const KEY = 'dp6';
const DEF = {xp:0, streak:0, last:'', freeze:1, level:'A1', goal:50, hist:{}, known:{}, mist:{}, quest:{day:'', p:{}, got:{}}, exam:'', theme:''};
const dstr = (ago = 0) => new Date(Date.now() - ago * 864e5).toLocaleDateString('sv');
export const today = () => dstr(0);
export const QUESTS = [
  {id:'words', ic:'📚', t:'5 ta so‘z o‘rgan', n:5},
  {id:'quiz',  ic:'🎮', t:'1 ta quiz yech',   n:1},
  {id:'rev',   ic:'🔁', t:'3 ta so‘z takrorla', n:3},
];
export const RANKS = [[0,'🌱 Anfänger'],[100,'🔍 Entdecker'],[500,'⚡ Profi'],[1500,'👑 Meister']];
export const rank = x => RANKS.filter(r => x >= r[0]).pop()[1];

let S;
try { S = Object.assign({}, DEF, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) { S = Object.assign({}, DEF); }
export {S};
export const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} /* sync() 7-kunda */ };
export const words = () => V[S.level] || V.A1;
export const dxp = () => S.hist[today()] || 0;
export const due = () => Object.values(S.mist).filter(m => m.due <= today()).length;

// Kun almashganda: o'tkazib yuborilgan 1 kunni Freeze qoplaydi
(function rollover() {
  const t = today();
  if (S.last && S.last !== t) {
    const gap = Math.round((Date.parse(t) - Date.parse(S.last)) / 864e5);
    if (gap === 2 && S.freeze > 0) { S.freeze--; S.last = dstr(1); }
    else if (gap > 1) S.streak = 0;
  }
  if (S.quest.day !== t) S.quest = {day: t, p: {}, got: {}};
  save();
})();

export function addXp(n) {
  const t = today(), before = dxp();
  S.xp += n; S.hist[t] = before + n;
  let first = false;
  if (S.last !== t) { S.last = t; S.streak++; first = true; if (S.streak % 7 === 0) S.freeze++; }
  save();
  return {first, goalHit: before < S.goal && S.hist[t] >= S.goal};
}
export function bump(id, by = 1) {          // topshiriq progressi
  const q = QUESTS.find(x => x.id === id), p = S.quest.p;
  p[id] = Math.min((p[id] || 0) + by, q.n);
  let bonus = 0;
  if (p[id] >= q.n && !S.quest.got[id]) { S.quest.got[id] = 1; bonus = 10; addXp(10); }
  save();
  return bonus;
}
export function week() {                    // oxirgi 7 kun
  return [6,5,4,3,2,1,0].map(a => { const k = dstr(a), d = new Date(Date.now() - a * 864e5);
    return {k, l:['Ya','Du','Se','Ch','Pa','Ju','Sh'][d.getDay()], xp:S.hist[k] || 0, today:a === 0}; });
}
