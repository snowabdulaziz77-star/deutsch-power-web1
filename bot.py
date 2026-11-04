import datetime as dt, difflib, html, json, logging, random, re
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import (BotCommand, InlineKeyboardButton as B, InlineKeyboardMarkup as KB,
                      MenuButtonWebApp, WebAppInfo)
from telegram.error import BadRequest, Forbidden
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, MessageHandler,
                          PollAnswerHandler, filters)

import config as C, database as db

try:
    from openai import AsyncOpenAI
    AI = AsyncOpenAI(api_key=C.OPENAI_API_KEY) if C.OPENAI_API_KEY else None
except ImportError:
    AI = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
VOCAB = json.loads((Path(__file__).parent / "webapp" / "vocab.json").read_text("utf-8"))
SYS = ("You are DeutschPower AI, a friendly German tutor for CEFR level {lvl}. Reply mainly in simple German "
       "suited to that level, gently correct mistakes and explain each correction briefly in Uzbek. "
       "End with a short follow-up question to keep the conversation going.")
WSYS = ("You are a strict but kind German writing examiner for CEFR level {lvl}. Reply in Uzbek with German examples. "
        "Format: 1) Ball: X/10; 2) Xatolar va to'g'ri variantlari (ro'yxat); 3) Tuzatilgan to'liq matn; 4) Lug'at va uslub bo'yicha 2 ta maslahat.")
WEB = B("🚀 DeutschPower App", web_app=WebAppInfo(url=C.WEBAPP_URL))
BACK = [B("🏠 Bosh menyu", callback_data="home")]
bar = lambda p, n=10: "▰" * round(p * n) + "▱" * (n - round(p * n))


def home_kb():
    return KB([[WEB],
               [B("📚 Kun so'zi", callback_data="word"), B("🎯 Quiz", callback_data="quiz")],
               [B("🔁 Takrorlash", callback_data="review"), B("📖 Grammatika", callback_data="gram")],
               [B("🧩 Grammatika testi", callback_data="gq")],
               [B("🎙 Talaffuz", callback_data="say"), B("✍️ Schreiben", callback_data="write")],
               [B("🤖 AI Ustoz", callback_data="ai"), B("🏆 Reyting", callback_data="top")],
               [B("📊 Natijam", callback_data="stats"), B("🌐 Daraja", callback_data="levels")],
               [B("👥 Do'stlar", callback_data="invite"), B("💬 Yordam", callback_data="help")]])


async def show(u, text, kb=None):
    """Tugmadan kelsa xabarni tahrirlaydi, aks holda yangi xabar yuboradi."""
    cq = u.callback_query
    if cq:
        await cq.answer()
        try:
            return await cq.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except BadRequest as e:
            if "not modified" in str(e):
                return
    await u.effective_chat.send_message(text, reply_markup=kb, parse_mode="HTML")


def me_of(u):
    usr = u.effective_user
    db.touch(usr.id, usr.first_name)
    return db.get(usr.id)


async def start(u, ctx):
    ctx.user_data["ai"] = False
    usr = u.effective_user
    new = db.touch(usr.id, usr.first_name)
    if new and ctx.args and ctx.args[0].startswith("ref_"):      # referal havola orqali kelgan
        try:
            ref = int(ctx.args[0][4:])
        except ValueError:
            ref = 0
        if ref and ref != usr.id and db.q("SELECT 1 FROM users WHERE id=?", (ref,)):
            db.q("UPDATE users SET ref=? WHERE id=?", (ref, usr.id))
            db.add_xp(ref, 50)
            db.add_xp(usr.id, 20)
            try:
                await ctx.bot.send_message(ref, f"🎉 Do'stingiz <b>{html.escape(usr.first_name)}</b> qo'shildi! +50 XP", parse_mode="HTML")
            except Exception:
                pass
    me = db.get(usr.id)
    await show(u, f"👋 <b>{html.escape(usr.first_name)}</b>, <b>DeutschPower</b>ga xush kelibsiz! 🇩🇪\n\n"
                  f"{db.rank(me['xp'])}  •  ⭐ {me['xp']} XP  •  🔥 {me['streak']} kun  •  🎓 {me['level']}\n\n"
                  "Bugun nimani o'rganamiz?", home_kb())


async def word(u, ctx):
    me = me_of(u)
    de, uz, ex = random.choice(VOCAB[me["level"]])
    db.add_xp(me["id"], 2)
    await show(u, f"📚 <b>{me['level']} • So'z kartasi</b>\n\n🇩🇪 <b>{de}</b>\n🇺🇿 <tg-spoiler>{uz}</tg-spoiler>\n\n"
                  f"💬 <i>{ex}</i>\n\n<i>Tarjimani ko'rish uchun bosing • +2 XP</i>",
               KB([[B("➡️ Keyingi so'z", callback_data="word")], BACK]))


async def quiz(u, ctx):
    if u.callback_query:
        await u.callback_query.answer()
    me = me_of(u)
    words = VOCAB[me["level"]]
    de, uz, ex = random.choice(words)
    opts = [uz] + [w[1] for w in random.sample([w for w in words if w[1] != uz], 3)]
    random.shuffle(opts)
    right = opts.index(uz)
    m = await u.effective_chat.send_poll(
        f"🇩🇪 «{de}» — o'zbekchasi?", opts, type="quiz", correct_option_id=right, is_anonymous=False,
        explanation=f"💬 {ex}",
        reply_markup=KB([[B("➡️ Keyingi savol", callback_data="quiz")], BACK]))
    ctx.bot_data[m.poll.id] = (right, de, uz, ex)


async def poll_answer(u, ctx):
    a = u.poll_answer
    info = ctx.bot_data.pop(a.poll_id, None)
    if info is None:
        return
    right, de, uz, ex = info
    db.touch(a.user.id, a.user.first_name)
    ok = bool(a.option_ids) and a.option_ids[0] == right
    db.add_xp(a.user.id, 10 if ok else 1, ok)
    if not ok and de:
        db.add_mistake(a.user.id, de, uz, ex)      # xato so'z takrorlash daftariga tushadi


async def stats(u, ctx):
    me = me_of(u)
    acc = round(me["correct"] / me["total"] * 100) if me["total"] else 0
    p, hi = db.progress(me["xp"])
    await show(u, f"📊 <b>Sizning natijangiz</b>\n\n{db.rank(me['xp'])}\n{bar(p)} {round(p*100)}%"
                  f"{f' (keyingi daraja: {hi} XP)' if hi else ''}\n\n⭐ XP: <b>{me['xp']}</b>\n"
                  f"🔥 Streak: <b>{me['streak']} kun</b>\n🎓 Daraja: <b>{me['level']}</b>\n"
                  f"🎯 Quiz aniqligi: <b>{acc}%</b> ({me['correct']}/{me['total']})", KB([BACK]))


async def top(u, ctx):
    cq = u.callback_query
    if cq and cq.data == "topall":
        rows = db.q("SELECT name, xp AS p, streak FROM users ORDER BY xp DESC LIMIT 10")
        head = "🏆 <b>Barcha vaqtdagi reyting</b>"
    else:
        rows = db.q("SELECT name, wxp AS p, streak FROM users WHERE wk=? ORDER BY wxp DESC LIMIT 10", (db.week(),))
        head = "🔥 <b>Haftalik musobaqa</b> (har dushanba yangilanadi)"
    medals = ["🥇", "🥈", "🥉"] + ["▫️"] * 7
    lines = [f"{medals[i]} <b>{html.escape(r['name'] or '?')}</b> — {r['p']} XP  🔥{r['streak']}" for i, r in enumerate(rows)]
    await show(u, head + "\n\n" + ("\n".join(lines) or "Hali hech kim yo'q — birinchi bo'ling!"),
               KB([[B("📅 Haftalik", callback_data="top"), B("🏆 Hammasi", callback_data="topall")], BACK]))


async def levels(u, ctx):
    await show(u, "🌐 <b>Darajangizni tanlang:</b>",
               KB([[B(f"🎓 {l}", callback_data=f"lvl_{l}") for l in VOCAB], BACK]))


async def setlvl(u, ctx):
    lvl = u.callback_query.data.split("_")[1]
    me_of(u)
    db.q("UPDATE users SET level=? WHERE id=?", (lvl, u.effective_user.id))
    await start(u, ctx)


async def ai_on(u, ctx):
    ctx.user_data.update(ai="chat", hist=[])
    await show(u, "🤖 <b>AI Ustoz yoqildi!</b>\n\nMenga nemis tilida yozing — xatolaringizni tuzataman va "
                  "o'zbekcha tushuntiraman. Masalan: <i>Hallo! Ich heiße Ali.</i>",
               KB([[B("❌ Chiqish", callback_data="home")]]))


async def write_on(u, ctx):
    ctx.user_data.update(ai="write", hist=[])
    await show(u, "✍️ <b>Schreiben tekshiruvi</b>\n\nNemis tilida matn yozing (3–8 gap). Men uni baholayman: ball (10 dan), xatolar, "
                  "tuzatilgan variant va maslahatlar.\n\nMasalan: <i>Ich wohne in Taschkent. Ich lerne seit einem Jahr Deutsch...</i>",
               KB([[B("❌ Chiqish", callback_data="home")]]))


async def chat(u, ctx):
    if not ctx.user_data.get("ai"):
        return await u.message.reply_text("Menyudan tanlang 👇", reply_markup=home_kb())
    if not AI:
        return await u.message.reply_text("🤖 AI Ustoz hali yoqilmagan (OPENAI_API_KEY sozlanmagan).")
    me = me_of(u)
    await u.effective_chat.send_chat_action("typing")
    hist = ctx.user_data.setdefault("hist", [])
    hist.append({"role": "user", "content": u.message.text})
    try:
        r = await AI.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "system", "content": (WSYS if ctx.user_data.get("ai") == "write" else SYS).format(lvl=me["level"])}] + hist[-8:])
        ans = r.choices[0].message.content
    except Exception:
        logging.exception("AI xatosi")
        return await u.message.reply_text("⚠️ AI hozir band, birozdan so'ng urinib ko'ring.")
    hist.append({"role": "assistant", "content": ans})
    db.add_xp(me["id"], 15 if ctx.user_data.get("ai") == "write" else 3)
    await u.message.reply_text(ans, reply_markup=KB([[B("❌ Chiqish", callback_data="home")]]))


async def help_(u, ctx):
    await show(u, f"💬 <b>Yordam</b>\n\n/start — bosh menyu\n/word — so'z kartasi\n/quiz — quiz\n/stats — natijam\n"
                  f"/top — reyting\n\nSavollar uchun: {C.ADMIN}", KB([BACK]))


GRAM = json.loads((Path(__file__).parent / "grammar.json").read_text("utf-8"))


async def review(u, ctx):
    uid = me_of(u)["id"]
    w = db.due_word(uid)
    if not w:
        return await show(u, "🔁 <b>Takrorlash</b>\n\nHozircha takrorlanadigan so'z yo'q. Quizda xato qilgan so'zlaringiz shu yerga tushadi 👏", KB([BACK]))
    ctx.user_data["rv"] = w["de"]
    await show(u, f"🔁 <b>Takrorlash</b> • navbatda: {db.due_count(uid)} ta\n\n🇩🇪 <b>{w['de']}</b>\n🇺🇿 <tg-spoiler>{w['uz']}</tg-spoiler>\n\n"
                  f"💬 <i>{w['ex']}</i>\n\nEsladingizmi?",
               KB([[B("✅ Esladim", callback_data="rv_1"), B("❌ Yana takror", callback_data="rv_0")], BACK]))


async def review_ans(u, ctx):
    ok = u.callback_query.data == "rv_1"
    de = ctx.user_data.pop("rv", None)
    if de:
        db.review(u.effective_user.id, de, ok)
        db.add_xp(u.effective_user.id, 5 if ok else 1)
    await review(u, ctx)


async def gram(u, ctx):
    lvl = me_of(u)["level"]
    await show(u, f"📖 <b>Grammatika • {lvl}</b>\n\nDarsni tanlang:",
               KB([[B(t, callback_data=f"g_{i}")] for i, (t, _) in enumerate(GRAM.get(lvl, []))] + [BACK]))


async def gram_item(u, ctx):
    t, body = GRAM[me_of(u)["level"]][int(u.callback_query.data[2:])]
    await show(u, f"📖 <b>{t}</b>\n\n{body}", KB([[B("⬅️ Darslar", callback_data="gram")], BACK]))


async def say(u, ctx):
    de, uz, ex = random.choice(VOCAB[me_of(u)["level"]])
    ctx.user_data["say"] = ex
    await show(u, f"🎙 <b>Talaffuz mashqi</b>\n\nQuyidagi gapni <b>ovozli xabar</b> bilan ayting:\n\n🇩🇪 <b>{ex}</b>\n🇺🇿 <i>{de} — {uz}</i>",
               KB([[B("➡️ Boshqa gap", callback_data="say")], BACK]))


async def voice(u, ctx):
    target = ctx.user_data.get("say")
    if not target:
        return await u.message.reply_text("Avval menyudan 🎙 Talaffuz ni tanlang.", reply_markup=home_kb())
    if not AI:
        return await u.message.reply_text("🎙 Bu funksiya uchun OPENAI_API_KEY sozlanishi kerak.")
    await u.effective_chat.send_chat_action("typing")
    try:
        f = await (await ctx.bot.get_file(u.message.voice.file_id)).download_as_bytearray()
        r = await AI.audio.transcriptions.create(model="whisper-1", file=("voice.ogg", bytes(f)), language="de")
    except Exception:
        logging.exception("Whisper xatosi")
        return await u.message.reply_text("⚠️ Ovozni tahlil qilib bo'lmadi, qayta urinib ko'ring.")
    norm = lambda t: re.sub(r"[^\w\s]", "", t.lower()).strip()
    p = round(difflib.SequenceMatcher(None, norm(target), norm(r.text)).ratio() * 100)
    db.add_xp(me_of(u)["id"], 15 if p >= 85 else 8 if p >= 60 else 2)
    verdict = "🏆 Ajoyib!" if p >= 85 else "👍 Yaxshi, yana urinib ko'ring" if p >= 60 else "💪 Sekinroq va aniqroq ayting"
    await u.message.reply_html(f"{verdict}\n\nAniqlik: <b>{p}%</b>\n🎯 Kerak: <i>{html.escape(target)}</i>\n👂 Eshitildi: <i>{html.escape(r.text)}</i>",
                               reply_markup=KB([[B("➡️ Keyingi gap", callback_data="say")], BACK]))


async def invite(u, ctx):
    me = me_of(u)
    n = db.q("SELECT COUNT(*) c FROM users WHERE ref=?", (me["id"],))[0]["c"]
    await show(u, "👥 <b>Do'stlarni taklif qiling</b>\n\nHar bir do'stingiz uchun <b>+50 XP</b>, do'stingizga esa <b>+20 XP</b>!\n\n"
                  f"🔗 Sizning havolangiz:\nhttps://t.me/{ctx.bot.username}?start=ref_{me['id']}\n\nTaklif qilinganlar: <b>{n}</b>", KB([BACK]))


DRILLS = json.loads((Path(__file__).parent / "grammar_drills.json").read_text("utf-8"))


async def gquiz(u, ctx):
    if u.callback_query:
        await u.callback_query.answer()
    me_of(u)
    p, opts, right, why = random.choice(DRILLS)
    m = await u.effective_chat.send_poll(f"Qaysi variant to'g'ri?\n\n{p}", opts, type="quiz", correct_option_id=right, is_anonymous=False,
                                         explanation=why, reply_markup=KB([[B("➡️ Keyingi", callback_data="gq")], BACK]))
    ctx.bot_data[m.poll.id] = (right, None, None, None)


async def daily(ctx):
    for r in db.q("SELECT id, level FROM users WHERE remind=1"):
        de, uz, ex = random.choice(VOCAB.get(r["level"], VOCAB["A1"]))
        try:
            await ctx.bot.send_message(r["id"], f"☀️ <b>Xayrli tong!</b> Bugungi so'z:\n\n🇩🇪 <b>{de}</b> — {uz}\n"
                                                f"💬 <i>{ex}</i>\n\n🔥 Streak'ni yo'qotmang!" + (f"\n🔁 Takrorlash kutyapti: {db.due_count(r['id'])} ta so'z" if db.due_count(r["id"]) else ""),
                                       parse_mode="HTML", reply_markup=KB([[WEB]]))
        except Exception:
            pass


async def on_error(update, ctx):
    if isinstance(ctx.error, Forbidden):      # foydalanuvchi botni bloklagan, bu normal holat
        return
    logging.error("Kutilmagan xato", exc_info=ctx.error)


async def post_init(app):
    await app.bot.set_my_commands([BotCommand("start", "Bosh menyu"), BotCommand("word", "So'z kartasi"),
                                   BotCommand("quiz", "Quiz"), BotCommand("stats", "Natijam"), BotCommand("top", "Reyting")])
    await app.bot.set_chat_menu_button(menu_button=MenuButtonWebApp("🚀 App", WebAppInfo(url=C.WEBAPP_URL)))


def main():
    if not C.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env.example faylini .env ga nusxalab, tokenni yozing.")
    db.init()
    app = Application.builder().token(C.BOT_TOKEN).post_init(post_init).build()
    for cmd, fn in [("start", start), ("word", word), ("quiz", quiz), ("stats", stats), ("top", top)]:
        app.add_handler(CommandHandler(cmd, fn))
    for pat, fn in [("home", start), ("word", word), ("quiz", quiz), ("stats", stats), ("top", top),
                    ("levels", levels), ("ai", ai_on), ("write", write_on), ("help", help_), ("topall", top), ("review", review),
                    ("rv_1", review_ans), ("rv_0", review_ans), ("gram", gram), ("say", say), ("invite", invite), ("gq", gquiz)]:
        app.add_handler(CallbackQueryHandler(fn, pattern=f"^{pat}$"))
    app.add_handler(CallbackQueryHandler(setlvl, pattern="^lvl_"))
    app.add_handler(CallbackQueryHandler(gram_item, pattern=r"^g_\d+$"))
    app.add_error_handler(on_error)
    app.add_handler(PollAnswerHandler(poll_answer))
    app.add_handler(MessageHandler(filters.VOICE, voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    if app.job_queue:
        app.job_queue.run_daily(daily, time=dt.time(9, 0, tzinfo=ZoneInfo("Asia/Tashkent")))
    print("🇩🇪 DeutschPower bot ishga tushdi!")
    app.run_polling(allowed_updates=["message", "callback_query", "poll_answer"])


if __name__ == "__main__":
    main()
