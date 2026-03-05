from pyrogram import Client, filters
from database.restrictions import restrict_user, unrestrict_user, get_all_restricted_users
from config import Config
from html import escape


@Client.on_message(filters.command("restrict") & filters.user(list(Config.OWNER_IDS)))
async def restrict_cmd(client, message):
    args = message.command
    target_user = None
    reason = ""

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if len(args) > 1:
            reason = message.text.split(maxsplit=1)[1]
        else:
            return await message.reply_text(
                "⚠️ <b>Format:</b> Reply to a user and type <code>/restrict &lt;reason&gt;</code>",
                parse_mode="HTML"
            )

    else:
        if len(args) < 3:
            return await message.reply_text(
                "⚠️ <b>Format:</b> <code>/restrict &lt;User_ID or @Username&gt; &lt;reason&gt;</code>\n"
                "Or reply to a user's message with <code>/restrict &lt;reason&gt;</code>",
                parse_mode="HTML"
            )

        user_identifier = args[1]
        reason = message.text.split(maxsplit=2)[2]

        wait_msg = await message.reply_text("🔍 Fetching user details...")

        try:
            if user_identifier.isdigit() or (user_identifier.startswith("-") and user_identifier[1:].isdigit()):
                user_identifier = int(user_identifier)

            target_user = await client.get_users(user_identifier)
            await wait_msg.delete()

        except Exception as e:
            return await wait_msg.edit_text(
                f"❌ <b>Error:</b> User not found.\n<code>{escape(str(e))}</code>",
                parse_mode="HTML"
            )

    if not target_user:
        return await message.reply_text("❌ Could not determine the user.")

    await restrict_user(target_user.id, reason, message.from_user.id)

    name = escape(target_user.first_name)
    reason = escape(reason)

    await message.reply_text(
        f"⛔ <b>User Restricted</b>\n\n"
        f"👤 <b>{name}</b> [<code>{target_user.id}</code>]\n"
        f"📌 <b>Reason:</b> {reason}",
        parse_mode="HTML"
    )


@Client.on_message(filters.command("unrestrict") & filters.user(list(Config.OWNER_IDS)))
async def unrestrict_cmd(client, message):
    args = message.command
    target_user = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user

    else:
        if len(args) < 2:
            return await message.reply_text(
                "⚠️ <b>Format:</b> <code>/unrestrict &lt;User_ID or @Username&gt;</code>\n"
                "Or reply to a user's message with <code>/unrestrict</code>",
                parse_mode="HTML"
            )

        user_identifier = args[1]

        wait_msg = await message.reply_text("🔍 Fetching user details...")

        try:
            if user_identifier.isdigit() or (user_identifier.startswith("-") and user_identifier[1:].isdigit()):
                user_identifier = int(user_identifier)

            target_user = await client.get_users(user_identifier)
            await wait_msg.delete()

        except Exception as e:
            return await wait_msg.edit_text(
                f"❌ <b>Error:</b> User not found.\n<code>{escape(str(e))}</code>",
                parse_mode="HTML"
            )

    if not target_user:
        return await message.reply_text("❌ Could not determine the user.")

    await unrestrict_user(target_user.id)

    name = escape(target_user.first_name)

    await message.reply_text(
        f"✅ <b>User Unrestricted</b>\n\n"
        f"👤 <b>{name}</b> [<code>{target_user.id}</code>] can now play and host matches again.",
        parse_mode="HTML"
    )


@Client.on_message(filters.command("restricted") & filters.user(list(Config.OWNER_IDS)))
async def restricted_list_cmd(client, message):

    users = await get_all_restricted_users()

    if not users:
        return await message.reply_text(
            "✅ <b>No users are currently restricted.</b>",
            parse_mode="HTML"
        )

    text = "⛔ <b>Restricted Users</b>\n\n"

    for i, user in enumerate(users, start=1):
        user_id = user.get("user_id")
        reason = escape(user.get("reason", "No reason"))

        text += f"{i}. <code>{user_id}</code>\n"
        text += f"   📌 Reason: {reason}\n\n"

    await message.reply_text(text, parse_mode="HTML")
