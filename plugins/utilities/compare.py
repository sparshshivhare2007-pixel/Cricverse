import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from database.connection import db

SEARCH_FRAMES = [
    "🔍 Scanning scorecards…",
    "📊 Crunching numbers…",
    "⚔️ Analyzing rivalry…",
    "🔥 Almost there…"
]

@Client.on_message(filters.command("compare"))
async def head2head_cmd(client, message):
    args = message.command[1:]
    users = []

    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            users = [message.from_user, message.reply_to_message.from_user]
        elif len(args) == 1:
            u2 = await client.get_users(args[0])
            users = [message.from_user, u2]
        elif len(args) >= 2:
            u1 = await client.get_users(args[0])
            u2 = await client.get_users(args[1])
            users = [u1, u2]
        else:
            return await message.reply_text("❌ Use `/compare @user` or reply to someone", parse_mode=ParseMode.HTML)
    except Exception:
        return await message.reply_text("❌ Invalid user(s). Try username or user_id.")

    u1, u2 = users
    uid1, uid2 = u1.id, u2.id

    loading = await message.reply_text("🔍 Initializing comparison…")
    for frame in SEARCH_FRAMES:
        await asyncio.sleep(0.6)
        try:
            await loading.edit_text(frame)
        except:
            pass

    async with db.pool.acquire() as conn:
        s1 = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id=$1", uid1)
        s2 = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id=$1", uid2)

    if not s1 or not s2:
        return await loading.edit_text("⚠️ One or both players have no stats yet.\nAsk them to play some matches 🏏")

    def safe(v): return v or 0

    def batting_avg(s):
        outs = max(1, s["matches"] - safe(s.get("not_outs")))
        return s["runs"] / outs

    def strike_rate(s):
        return (s["runs"] / s["balls_faced"] * 100) if s["balls_faced"] > 0 else 0

    def economy(s):
        return (s["runs_conceded"] / (s["balls_bowled"] / 6)) if s["balls_bowled"] > 0 else 99

    def win_rate(s):
        return (s["wins"] / s["matches"] * 100) if s["matches"] > 0 else 0

    fields = [
        ("🏃 Runs", s1["runs"], s2["runs"], True),
        ("⚾ Wickets", s1["wickets"], s2["wickets"], True),
        ("📈 Avg", batting_avg(s1), batting_avg(s2), True),
        ("⚡ Strike Rate", strike_rate(s1), strike_rate(s2), True),
        ("🎯 Economy", economy(s1), economy(s2), False),
        ("🎩 Hat-Tricks", s1["hat_tricks"], s2["hat_tricks"], True),
        ("🏅 MOMs", s1["moms"], s2["moms"], True),
        ("🦆 Ducks", s1["ducks"], s2["ducks"], False),
        ("🎮 Matches", s1["matches"], s2["matches"], True),
        ("🧑‍✈️ Win Rate", win_rate(s1), win_rate(s2), True),
    ]

    score1 = score2 = 0
    lines = []

    for name, v1, v2, higher_better in fields:
        if abs(v1 - v2) < 0.01:
            mark = "➖"
        elif (v1 > v2 and higher_better) or (v1 < v2 and not higher_better):
            score1 += 1
            mark = "✅"
        else:
            score2 += 1
            mark = "❌"

        val1 = f"{v1:.1f}%" if "Rate" in name else f"{v1:.2f}" if isinstance(v1, float) else v1
        val2 = f"{v2:.1f}%" if "Rate" in name else f"{v2:.2f}" if isinstance(v2, float) else v2

        lines.append(f"• {name:<14}:  {val1}  {'>' if mark=='✅' else '<' if mark=='❌' else '='}  {val2}  {mark}")

    if score1 > score2:
        verdict = f"{u1.first_name} dominates overall —\n{u2.first_name} needs a comeback arc 😤"
    elif score2 > score1:
        verdict = f"{u2.first_name} takes the edge —\n{u1.first_name} under pressure 😬"
    else:
        verdict = "Too close to call — this rivalry is 🔥"

    text = (
        "⚔️ <b>𝗛𝗘𝗔𝗗 𝗧𝗢 𝗛𝗘𝗔𝗗 𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦</b>\n\n"
        f"👤 {u1.first_name}  <b>{score1}</b> 🆚 <b>{score2}</b>  👤 {u2.first_name}\n"
        "───┈┄┄╌╌╌╌┄┄┈────\n\n"
        "📊 <b>𝗦𝗧𝗔𝗧 𝗖𝗢𝗠𝗣𝗔𝗥𝗜𝗦𝗢𝗡</b>\n"
        + "\n".join(lines) +
        "\n\n───┈┄┄╌╌╌╌┄┄┈────\n\n"
        f"🔥 <b>𝗩𝗘𝗥𝗗𝗜𝗖𝗧</b>\n{verdict}\n\n"
        "#Rivalry #StatsDontLie"
    )

    await loading.edit_text(text, parse_mode=ParseMode.HTML)
    
