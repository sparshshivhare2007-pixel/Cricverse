from pyrogram import Client, filters
from database.restrictions import restrict_user, unrestrict_user
from config import Config 

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
            return await message.reply_text("⚠️ **Format:** Reply to a user and type `/restrict <reason>`")
            
    else:
        if len(args) < 3:
            return await message.reply_text(
                "⚠️ **Format:** `/restrict <User_ID or @Username> <reason>`\n"
                "Or simply reply to a user's message with `/restrict <reason>`"
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
            return await wait_msg.edit_text(f"❌ **Error:** User not found. Make sure they have started the bot.\n`{e}`")

    if not target_user:
        return await message.reply_text("❌ Could not determine the user.")

    await restrict_user(target_user.id, reason, message.from_user.id)
    
    await message.reply_text(
        f"⛔ **{target_user.first_name}** (`{target_user.id}`) has been restricted from playing.\n"
        f"📌 **Reason:** {reason}"
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
                "⚠️ **Format:** `/unrestrict <User_ID or @Username>`\n"
                "Or simply reply to a user's message with `/unrestrict`"
            )
        
        user_identifier = args[1]
        
        wait_msg = await message.reply_text("🔍 Fetching user details...")
        try:
            if user_identifier.isdigit() or (user_identifier.startswith("-") and user_identifier[1:].isdigit()):
                user_identifier = int(user_identifier)
                
            target_user = await client.get_users(user_identifier)
            await wait_msg.delete()
        except Exception as e:
            return await wait_msg.edit_text(f"❌ **Error:** User not found.\n`{e}`")

    if not target_user:
        return await message.reply_text("❌ Could not determine the user.")

    await unrestrict_user(target_user.id)
    
    await message.reply_text(
        f"✅ **{target_user.first_name}** (`{target_user.id}`) is now free to play and host matches again!"
    )
    
