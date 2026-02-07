from pyrogram import Client
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import ChatAdminRequired, ChatWriteForbidden
from database.groups import add_group, total_groups
from config import Config


OWNER_ID = 8084629653
OWNER_NAME = "𝑲𝑰𝑵𝑮 ˹𐩃𝑲˼║ ツ"


@Client.on_chat_member_updated()
async def chat_member_handler(client: Client, update: ChatMemberUpdated):
    try:
        chat = update.chat
        chat_id = chat.id

        old = update.old_chat_member
        new = update.new_chat_member

        if not old or not new:
            return

        user = new.user
        if not user:
            return

        # ─── OWNER JOINED ───
        if user.id == OWNER_ID and new.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            try:
                await client.send_message(
                    chat_id,
                    f"ɢʀᴇᴇᴛɪɴɢs, ᴏᴡɴᴇʀ! "
                    f"ɢʟᴀᴅ ʏᴏᴜ’ᴠᴇ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ᴄᴏɴᴠᴇʀsᴀᴛɪᴏɴ, {OWNER_NAME}!"
                )
            except Exception:
                pass

        # ─── OWNER LEFT ───
        if user.id == OWNER_ID and new.status in (
            ChatMemberStatus.LEFT,
            ChatMemberStatus.BANNED,
        ):
            try:
                await client.send_message(
                    chat_id,
                    f"ᴏᴜʀ ᴏᴡɴᴇʀ {OWNER_NAME} "
                    f"ʜᴀs ʟᴇғᴛ ᴛʜᴇ ᴄʜᴀᴛ. "
                    f"sᴀᴅ ᴛᴏ sᴇᴇ ʏᴏᴜ ɢᴏ."
                )
            except Exception:
                pass

        # ─── BOT ADDED TO GROUP ───
        if new.user.is_self:
            inviter = update.from_user

            # Save group (DB failure should not crash)
            try:
                is_new_group = await add_group(chat.id, chat.title or "Unknown")
            except Exception:
                is_new_group = False

            # Group greeting
            try:
                await client.send_message(
                    chat.id,
                    "🏏 **Cricket Arena is now active!**\n\n"
                    "• Start solo or team matches\n"
                    "• Live commentary & stats\n"
                    "• Competitive cricket fun\n\n"
                    f"📢 Updates: {Config.PLAY_ZONE_INFO}"
                )
            except ChatWriteForbidden:
                pass
            except Exception:
                pass

            # DM inviter
            if inviter:
                try:
                    await client.send_message(
                        inviter.id,
                        "✅ **Thanks for adding Cricket Arena!**\n\n"
                        "You can now start matches directly in your group.\n"
                        f"📢 Updates: {Config.PLAY_ZONE_INFO}"
                    )
                except Exception:
                    pass

            # Invite link (admin-only)
            invite_link = "Not available"
            try:
                invite_link = await client.export_chat_invite_link(chat.id)
            except ChatAdminRequired:
                pass
            except Exception:
                pass

            # Log new group
            if is_new_group:
                try:
                    groups_count = await total_groups()
                except Exception:
                    groups_count = "N/A"

                log_text = (
                    "➕ **New Group Added**\n\n"
                    f"📌 Group: {chat.title}\n"
                    f"🆔 Chat ID: `{chat.id}`\n"
                    f"👤 Added by: {inviter.first_name if inviter else 'Unknown'}\n"
                    f"👤 User ID: `{inviter.id if inviter else 'N/A'}`\n"
                    f"🔗 Invite: {invite_link}\n\n"
                    f"📊 Total Groups: {groups_count}"
                )

                try:
                    await client.send_message(Config.LOG_CHANNEL, log_text)
                except Exception:
                    pass

    except Exception:
        # ABSOLUTE FAIL-SAFE: NOTHING escapes this handler
        pass
