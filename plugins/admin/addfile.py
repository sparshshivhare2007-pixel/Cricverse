from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from config import Config
from database.media import (
    add_media_file, remove_media_file, list_media_files,
    ALL_TYPES, TYPE_LABELS, has_uploaded, _MEDIA_CACHE,
)


def _help_text():
    return (
        "📁 <b>Media Manager — /addfile</b>\n\n"
        "<b>Add a file:</b>\n"
        "  Reply to a video/GIF → <code>/addfile &lt;type&gt;</code>\n\n"
        "<b>List files for a type:</b>\n"
        "  <code>/addfile list &lt;type&gt;</code>\n\n"
        "<b>Remove a file:</b>\n"
        "  <code>/addfile remove &lt;type&gt; &lt;file_id&gt;</code>\n\n"
        "<b>See upload status of all types:</b>\n"
        "  /files\n\n"
        "<b>Valid types:</b>\n"
        + "\n".join(f"  <code>{k}</code> — {v}" for k, v in TYPE_LABELS.items())
    )


@Client.on_message(filters.command("addfile"))
async def addfile_cmd(client: Client, message: Message):
    if message.from_user.id not in Config.OWNER_IDS:
        return

    args = message.command[1:]

    if not args:
        return await message.reply_text(_help_text(), parse_mode=ParseMode.HTML)

    sub = args[0].lower()

    if sub == "list":
        if len(args) < 2:
            return await message.reply_text(
                "Usage: <code>/addfile list &lt;type&gt;</code>", parse_mode=ParseMode.HTML
            )
        type_key = args[1].lower()
        if type_key not in ALL_TYPES:
            return await message.reply_text(
                f"❌ Unknown type: <code>{type_key}</code>", parse_mode=ParseMode.HTML
            )
        files = await list_media_files(type_key)
        label = TYPE_LABELS[type_key]
        if not files:
            return await message.reply_text(
                f"📂 <b>{label}</b>\n❌ No files uploaded yet.", parse_mode=ParseMode.HTML
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
        if type_key not in ALL_TYPES:
            return await message.reply_text(
                f"❌ Unknown type: <code>{type_key}</code>", parse_mode=ParseMode.HTML
            )
        await remove_media_file(type_key, file_id)
        return await message.reply_text(
            f"🗑 Removed from <b>{TYPE_LABELS[type_key]}</b>.", parse_mode=ParseMode.HTML
        )

    type_key = sub
    if type_key not in ALL_TYPES:
        return await message.reply_text(
            f"❌ Unknown type: <code>{type_key}</code>\n"
            "Send <code>/addfile</code> to see all valid types.",
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
    short_id = file_id[:45] + ("..." if len(file_id) > 45 else "")

    await message.reply_text(
        f"✅ <b>File added!</b>\n\n"
        f"📂 <b>Type:</b> {label}\n"
        f"🆔 <code>{short_id}</code>\n\n"
        "The video/GIF will now be used in the game immediately.",
        parse_mode=ParseMode.HTML,
    )


@Client.on_message(filters.command("files"))
async def files_status_cmd(client: Client, message: Message):
    if message.from_user.id not in Config.OWNER_IDS:
        return

    lines = []
    uploaded_count = 0
    for type_key, label in TYPE_LABELS.items():
        count = len(_MEDIA_CACHE.get(type_key, []))
        if count:
            lines.append(f"✅ <code>{type_key}</code> — {label} <b>({count} file{'s' if count > 1 else ''})</b>")
            uploaded_count += 1
        else:
            lines.append(f"❌ <code>{type_key}</code> — {label}")

    text = (
        f"📂 <b>Media Upload Status</b>\n"
        f"<i>{uploaded_count}/{len(ALL_TYPES)} types have files</i>\n\n"
        + "\n".join(lines)
        + "\n\n<i>Reply to a video/GIF with /addfile &lt;type&gt; to add files.</i>"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML)
