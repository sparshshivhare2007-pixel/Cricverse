import os
import asyncio
from git import Repo, GitCommandError, InvalidGitRepositoryError
from pyrogram import Client, filters
from config import Config

OWNER = filters.user(Config.OWNER_IDS)


@Client.on_message(filters.command(["gitpull", "update"]) & OWNER)
async def update_bot(client, message):
    msg = await message.reply_text("⚡ <b>Checking for updates...</b>")

    try:
        repo = Repo()
    except GitCommandError:
        return await msg.edit("❌ <b>Git command error.</b>")
    except InvalidGitRepositoryError:
        return await msg.edit("❌ <b>Invalid repository.</b>")

    try:
        repo.create_remote("upstream", Config.UPSTREAM_REPO)
    except:
        pass

    os.system("git fetch upstream")
    await asyncio.sleep(3)

    commits = list(repo.iter_commits("HEAD..upstream/main"))

    if not commits:
        return await msg.edit("🌺 <b>Bot is already up to date.</b>")

    text = "<b>📦 New Updates Available</b>\n\n"

    for c in commits[:10]:
        text += f"• {c.summary} — <i>{c.author}</i>\n"

    if len(text) > 4096:
        text = "<b>📦 Updates detected.</b>\nPulling latest code..."

    await msg.edit(text, disable_web_page_preview=True)

    await asyncio.sleep(2)
    await msg.edit("🚀 <b>Pulling latest updates...</b>")

    os.system("git stash && git pull upstream main")

    await asyncio.sleep(2)
    await msg.edit("♻️ <b>Restarting bot...</b>")

    os.system("pip3 install -r requirements.txt")

    os.system(f"kill -9 {os.getpid()} && bash start")
