import os
import asyncio
from git import Repo, GitCommandError, InvalidGitRepositoryError
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from config import Config

OWNER = filters.user(list(Config.OWNER_IDS))


@Client.on_message(filters.command(["gitpull", "update"]) & OWNER)
async def update_bot(client, message):

    msg = await message.reply_text(
        "⚙ <b>Update System</b>\n\nChecking for updates...",
        parse_mode=ParseMode.HTML
    )

    try:
        repo = Repo()
    except InvalidGitRepositoryError:
        return await msg.edit(
            "❌ <b>This directory is not a valid git repository.</b>",
            parse_mode=ParseMode.HTML
        )
    except GitCommandError:
        return await msg.edit(
            "❌ <b>Git command error occurred.</b>",
            parse_mode=ParseMode.HTML
        )

    try:
        repo.create_remote("upstream", Config.UPSTREAM_REPO)
    except Exception:
        pass

    try:
        repo.remotes.upstream.fetch()
    except Exception as e:
        return await msg.edit(
            f"❌ <b>Failed to fetch updates.</b>\n<code>{e}</code>",
            parse_mode=ParseMode.HTML
        )

    commits = list(repo.iter_commits("HEAD..upstream/main"))

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

    await msg.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    await asyncio.sleep(2)

    await msg.edit(
        "🚀 <b>Pulling latest updates...</b>",
        parse_mode=ParseMode.HTML
    )

    try:
        repo.git.stash()
        repo.git.pull("upstream", "main")
    except Exception as e:
        return await msg.edit(
            f"❌ <b>Update failed.</b>\n<code>{e}</code>",
            parse_mode=ParseMode.HTML
        )

    await asyncio.sleep(2)

    await msg.edit(
        "♻️ <b>Update complete. Restarting bot...</b>",
        parse_mode=ParseMode.HTML
    )

    os.system("pip3 install -r requirements.txt")

    os.system(f"kill -9 {os.getpid()}")
