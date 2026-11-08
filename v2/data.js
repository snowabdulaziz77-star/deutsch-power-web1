// So'zlar bazasi. Keyinchalik shu yerdan serverga ulanish mumkin.
export let V = {A1: [['das Wasser','Suv','Ich trinke Wasser.'],['das Brot','Non','Das Brot ist frisch.'],['das Haus','Uy','Das Haus ist groß.']]};
export const ready = fetch('vocab.json').then(r => r.json()).then(j => { V = j; }).catch(() => {});
