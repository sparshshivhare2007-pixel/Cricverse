from functools import wraps
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import Message, CallbackQuery
from config import Config
from database.games import get_active_game
from plugins.game.team.init import ACTIVE_MATCHES



def admin_only(func):
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        """
        update can be:
        - Message
        - CallbackQuery
        """

        # ── Identify update type ──
        if isinstance(update, CallbackQuery):
            chat = update.message.chat if update.message else None
            user = update.from_user
            reply = update.message.reply_text if update.message else None
            answer = update.answer
        elif isinstance(update, Message):
            chat = update.chat
            user = update.from_user
            reply = update.reply_text
            answer = None
        else:
            return

        # ── Group only ──
        if not chat or chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return

        # ── Anonymous admin / channel ──
        if isinstance(update, CallbackQuery) and update.message.sender_chat:
            await answer(
                "Anonymous admins cannot use this.",
                show_alert=True
            )
            return

        if isinstance(update, Message) and update.sender_chat:
            await reply(
                "**𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗**\n"
                "`Anonymous admins cannot use this command.`"
            )
            return

        if not user:
            return

        # ── Owner override ──
        if user.id in Config.OWNER_IDS:
            return await func(client, update, *args, **kwargs)

        # ── Admin check ──
        try:
            member = await client.get_chat_member(chat.id, user.id)
        except Exception:
            if answer:
                await answer("Could not verify permissions.", show_alert=True)
            elif reply:
                await reply(
                    "**𝗘𝗥𝗥𝗢𝗥**\n"
                    "`Could not verify permissions.`"
                )
            return

        if member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        ):
            return await func(client, update, *args, **kwargs)

        # ── Access denied ──
        if answer:
            await answer("Admins only.", show_alert=True)
        elif reply:
            await reply(
                "**𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗**\n"
                "`Admins only.`"
            )

    return wrapper


def host_only(func):
    """
    Allows only the current LIVE match host to use the command.
    RAM > DB (always).
    """

    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # 🧠 1. Prefer LIVE match (RAM)
        match = ACTIVE_MATCHES.get(chat_id)
        if match:
            host_id = match.get("host_id")

        else:
            # 🗄️ 2. Fallback to DB (pre-match only)
            game = await get_active_game(chat_id)
            if not game:
                return await message.reply_text(
                    "😴 No match running right now.\nStart one first."
                )
            host_id = game.get("host_id")

        # 👑 Permission check
        if user_id != host_id:
            return await message.reply_text(
                "👑 Host privilege only.\n"
                "Sit tight or convince the host 😌"
            )

        # ✅ Allowed
        return await func(client, message, *args, **kwargs)

    return wrapper
