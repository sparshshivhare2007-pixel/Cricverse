import os
import asyncio
import shutil
from git import Repo, exc
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from config import Config

OWNER = filters.user(list(Config.OWNER_IDS))

@Client.on_message(filters.command(["gitpull", "update"]) & OWNER)
async def update_bot(client, message):

    msg = await message.reply_text(
        "⚙ <b>Update System</b>\n\nChecking repository...",
        parse_mode=ParseMode.HTML
    )

    if not shutil.which("git"):
        return await msg.edit(
            "❌ <b>CRITICAL ERROR:</b> <code>git</code> is not installed on your VPS/Server.\n"
            "Please install git first using <code>apt install git</code>.",
            parse_mode=ParseMode.HTML
        )

    if not os.path.exists(".git"):
        await msg.edit("📦 <b>Initializing git repository...</b>", parse_mode=ParseMode.HTML)
        os.system("git init")
        os.system(f"git remote add origin {Config.UPSTREAM_REPO}")
        os.system("git fetch origin")
        os.system("git reset --hard origin/main")

    try:
        repo = Repo()
    except exc.InvalidGitRepositoryError:
        return await msg.edit(
            "❌ <b>Git Setup Failed!</b>\n"
            "The repository could not be initialized properly. Please clone the bot directly using git.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        return await msg.edit(f"❌ <b>Error:</b> {e}", parse_mode=ParseMode.HTML)

    try:
        repo.create_remote("upstream", Config.UPSTREAM_REPO)
    except:
        pass

    await msg.edit(
        "🔎 <b>Checking for updates...</b>",
        parse_mode=ParseMode.HTML
    )

    try:
        repo.remotes.upstream.fetch()
        commits = list(repo.iter_commits("HEAD..upstream/main"))
    except Exception as e:
        return await msg.edit(f"❌ <b>Fetch Error:</b> Check if UPSTREAM_REPO is correct.\n{e}", parse_mode=ParseMode.HTML)

    if not commits:
        return await msg.edit(
            "✅ <b>Bot is already up to date.</b>",
            parse_mode=ParseMode.HTML
        )

    text = "<b>📦 New Updates Available</b>\n\n"

    for c in commits[:10]:
        text += f"• {c.summary} — <i>{c.author}</i>\n"

    if len(text) > 4096:
        text = "<b>📦 Updates detected.</b>\nPulling latest code..."

    await msg.edit(text, parse_mode=ParseMode.HTML)

    await asyncio.sleep(2)

    await msg.edit(
        "🚀 <b>Pulling latest updates...</b>",
        parse_mode=ParseMode.HTML
    )

    os.system("git stash")
    os.system("git pull upstream main")

    await asyncio.sleep(2)

    await msg.edit(
        "♻️ <b>Update complete. Restarting bot...</b>",
        parse_mode=ParseMode.HTML
    )

    os.system("pip3 install -r requirements.txt")
    os.system(f"kill -9 {os.getpid()}")
    
