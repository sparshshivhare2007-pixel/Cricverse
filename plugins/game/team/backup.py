import json
import os
import uuid
from pyrogram import Client, filters
from plugins.game.team import ACTIVE_MATCHES
from utils.permissions import host_only 

class MatchEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return str(obj)

@Client.on_message(filters.command("savegame") & filters.group)
@host_only
async def save_game_cmd(client, message):
    chat_id = message.chat.id
    match = ACTIVE_MATCHES.get(chat_id)

    if not match:
        return await message.reply_text("⚠️ No active match running to save.")

    safe_match = {}
    for key, val in match.items():
        if key in ["client", "timeouts"]: 
            continue
        safe_match[key] = val

    file_name = f"match_save_{chat_id}.json"
    with open(file_name, "w") as f:
        json.dump(safe_match, f, indent=4, cls=MatchEncoder)

    caption = (
        "💾 **𝗠𝗔𝗧𝗖𝗛 𝗦𝗔𝗩𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!**\n"
        "──┈┄┄╌╌╌╌┄┄┈──\n"
        "If the bot glitches or a wrong player steps in, "
        "reply to this file with `/restore` to undo."
    )
    await message.reply_document(document=file_name, caption=caption)
    
    os.remove(file_name)

@Client.on_message(filters.command("restore") & filters.group)
@host_only
async def restore_game_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("⚠️ Please reply to a **.json** Save File first!")

    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".json"):
        return await message.reply_text("⚠️ Invalid file! Only `.json` match files are supported.")

    chat_id = message.chat.id

    wait_msg = await message.reply_text("🔄 **Downloading and restoring match data...**")

    try:
        file_path = await message.reply_to_message.download()
        with open(file_path, "r") as f:
            backup_data = json.load(f)
        os.remove(file_path)

        backup_data["client"] = client
        backup_data["timeouts"] = {
            "bowler": {"fails": 0, "task": None},
            "batter": {"fails": 0, "task": None},
        }
        
        backup_data["announced_achievements"] = {
            "batting": {}, "bowling": {}, "partnerships": set()
        }

        ACTIVE_MATCHES[chat_id] = backup_data

        await wait_msg.edit_text(
            f"✅ **𝗠𝗔𝗧𝗖𝗛 𝗥𝗘𝗦𝗧𝗢𝗥𝗘𝗗!**\n"
            f"──┈┄┄╌╌╌╌┄┄┈──\n"
            f"Game state loaded perfectly. \n"
            f"Phase: **{backup_data.get('phase', 'LIVE')}**\n\n"
            f"Batting Team Runs: **{backup_data.get('teams', {}).get(backup_data.get('batting_team', 'A'), {}).get('runs', 0)}**\n\n"
            f"▶️ Use `/fixmatch` or send the next command to resume."
        )

    except Exception as e:
        await wait_msg.edit_text(f"❌ **Restoration Failed:** Data file is corrupted or incompatible.\nError: `{e}`")
      
