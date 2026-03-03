from pyrogram import Client
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ParseMode, ChatMemberStatus

LOG_GROUP_ID = -1003692127639


async def send_match_log(client, action_title, match, extra_text=""):
    """Function to send match-related logs to the bot's private group"""
    if not LOG_GROUP_ID:
        return

    # Handle if match is UUID or dict
    if isinstance(match, dict):
        game_id = match.get("game_id", "Unknown")
        chat_id = match.get("chat_id", "Unknown")
        host_name = match.get("host_name", "Unknown")
    else:
        game_id = match
        chat_id = "Unknown"
        host_name = "Unknown"

    text = (
        f"📝 **{action_title}**\n"
        f"──┈┄┄╌╌╌╌┄┄┈──\n"
        f"🆔 **Match ID:** `{game_id}`\n"
        f"👤 **Host:** {host_name}\n"
        f"💬 **Group ID:** `{chat_id}`\n\n"
        f"{extra_text}"
    )

    try:
        await client.send_message(
            chat_id=LOG_GROUP_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"❌ Error while sending match log: {e}")

@Client.on_chat_member_updated()
async def bot_tracking_log(client, update: ChatMemberUpdated):
    """Automatically tracks when the bot is added or removed from groups"""
    if not LOG_GROUP_ID:
        return

    if update.chat.type.name not in ["GROUP", "SUPERGROUP"]:
        return
        
    me = await client.get_me()
    
    new_member = update.new_chat_member
    old_member = update.old_chat_member
    
    if new_member and new_member.user.id == me.id:
        status = new_member.status
        chat = update.chat
        
        action_by = update.from_user.mention if update.from_user else "Unknown"

        if status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
            if not old_member or old_member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
                text = (
                    f"✅ **𝗕𝗢𝗧 𝗔𝗗𝗗𝗘𝗗 𝗧𝗢 𝗚𝗥𝗢𝗨𝗣**\n"
                    f"──┈┄┄╌╌╌╌┄┄┈──\n"
                    f"💬 **Group Name:** {chat.title}\n"
                    f"🆔 **Group ID:** `{chat.id}`\n"
                    f"👤 **Added By:** {action_by}\n\n"
                    f"Bot is ready to host matches here!"
                )
                try:
                    await client.send_message(LOG_GROUP_ID, text)
                except Exception as e:
                    print(f"Log Error: {e}")

        elif status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED]:
            if old_member and old_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
                text = (
                    f"❌ **𝗕𝗢𝗧 𝗥𝗘𝗠𝗢𝗩𝗘𝗗 / 𝗞𝗜𝗖𝗞𝗘𝗗**\n"
                    f"──┈┄┄╌╌╌╌┄┄┈──\n"
                    f"💬 **Group Name:** {chat.title}\n"
                    f"🆔 **Group ID:** `{chat.id}`\n"
                    f"👤 **Removed By:** {action_by}\n\n"
                    f"Data tracking stopped for this group."
                )
                try:
                    await client.send_message(LOG_GROUP_ID, text)
                except Exception as e:
                    print(f"Log Error: {e}")
                    
