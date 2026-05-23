from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from config import Config
from database.media import add_media_file, remove_media_file, list_media_files, TYPE_MAP, TYPE_LABELS

VALID_TYPES = list(TYPE_MAP.keys())


def _types_list_text():
    lines = "\n".join(f"  <code>{k}</code> — {v}" for k, v in TYPE_LABELS.items())
    return (
        "📁 <b>AddFile — Owner Media Manager</b>\n\n"
        "<b>Usage:</b> Reply to a video/GIF with:\n"
        "<code>/addfile &lt;type&gt;</code>\n\n"
        "<b>To list existing files for a type:</b>\n"
        "<code>/addfile list &lt;type&gt;</code>\n\n"
        "<b>To remove a file:</b>\n"
        "<code>/addfile remove &lt;type&gt; &lt;file_id&gt;</code>\n\n"
        f"<b>Available types:</b>\n{lines}"
    )


@Client.on_message(filters.command("addfile"))
async def addfile_cmd(client: Client, message: Message):
    if message.from_user.id not in Config.OWNER_IDS:
        return

    args = message.command[1:]

    if not args:
        return await message.reply_text(_types_list_text(), parse_mode=ParseMode.HTML)

    sub = args[0].lower()

    if sub == "list":
        if len(args) < 2:
            return await message.reply_text(
                "Usage: <code>/addfile list &lt;type&gt;</code>", parse_mode=ParseMode.HTML
            )
        type_key = args[1].lower()
        if type_key not in TYPE_MAP:
            return await message.reply_text(
                f"❌ Unknown type: <code>{type_key}</code>", parse_mode=ParseMode.HTML
            )
        files = await list_media_files(type_key)
        label = TYPE_LABELS[type_key]
        if not files:
            return await message.reply_text(
                f"📂 <b>{label}</b>\nNo custom files saved yet.", parse_mode=ParseMode.HTML
            )
        ids_text = "\n".join(f"<code>{f}</code>" for f in files)
        return await message.reply_text(
            f"📂 <b>{label}</b> — {len(files)} file(s):\n\n{ids_text}",
            parse_mode=ParseMode.HTML,
        )

    if sub == "remove":
        if len(args) < 3:
            return await message.reply_text(
                "Usage: <code>/addfile remove &lt;type&gt; &lt;file_id&gt;</code>",
                parse_mode=ParseMode.HTML,
            )
        type_key = args[1].lower()
        file_id = args[2]
        if type_key not in TYPE_MAP:
            return await message.reply_text(
                f"❌ Unknown type: <code>{type_key}</code>", parse_mode=ParseMode.HTML
            )
        await remove_media_file(type_key, file_id)
        return await message.reply_text(
            f"🗑 Removed from <b>{TYPE_LABELS[type_key]}</b>.", parse_mode=ParseMode.HTML
        )

    type_key = sub
    if type_key not in TYPE_MAP:
        return await message.reply_text(
            f"❌ Unknown type: <code>{type_key}</code>\n"
            "Use <code>/addfile</code> without args to see all valid types.",
            parse_mode=ParseMode.HTML,
        )

    reply = message.reply_to_message
    if not reply:
        return await message.reply_text(
            "⚠️ <b>Reply to a video or GIF</b> with this command.",
            parse_mode=ParseMode.HTML,
        )

    file_id = None
    if reply.video:
        file_id = reply.video.file_id
    elif reply.animation:
        file_id = reply.animation.file_id
    elif reply.document and reply.document.mime_type and "video" in reply.document.mime_type:
        file_id = reply.document.file_id

    if not file_id:
        return await message.reply_text(
            "⚠️ The replied message must contain a <b>video or GIF</b>.",
            parse_mode=ParseMode.HTML,
        )

    await add_media_file(type_key, file_id)
    label = TYPE_LABELS[type_key]
    short_id = file_id[:40] + ("..." if len(file_id) > 40 else "")

    await message.reply_text(
        f"✅ <b>File added!</b>\n\n"
        f"📂 <b>Type:</b> {label}\n"
        f"🆔 <code>{short_id}</code>\n\n"
        "The video/GIF will now appear in the game immediately.",
        parse_mode=ParseMode.HTML,
    )
