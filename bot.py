import asyncio
from datetime import datetime, timedelta
import os
import pymongo
from pyrogram import Client, filters, enums
from pyrogram.types import *

# MongoDB variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ryme:ryme@cluster0.32cpya3.mongodb.net/?retryWrites=true&w=majority")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "mydatabase")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "kicks")

# Pyrogram variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "6214533661:AAHi_Op06eO6ms0HIiP1EqBVCU1xmKEoqVo")
API_ID = int(os.getenv("API_ID", "11948995"))
API_HASH = os.getenv("API_HASH", "cdae9279d0105638165415bf2769730d")

# Command prefix
COMMAND_PREFIX = os.getenv("PREFIX", ".")

# Default kick time in minutes
DEFAULT_KICK_TIME = int(os.getenv("DEFAULT_KICK_TIME", "43200"))  # 30 days in minutes

# Set up the MongoDB client and database
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
col = db[MONGO_COLLECTION_NAME]

# Set up the Pyrogram client
app = Client(
    "kickbot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
)

@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    user=message.from_user
    await message.reply(f"**Hi** {user.first_name},\nI'm KickBot, kicks group members after given time. Boom!")


@app.on_message(filters.command("kick", prefixes=COMMAND_PREFIX) & filters.group)
async def kick_command(client: Client, message: Message):
    # Check if the user is a group admin
    administrators = []
    async for m in app.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        administrators.append(m.user.id)

    if message.from_user.id not in administrators:
        await message.reply("You must be a group admin to use this command!")
        return

    else:
        # Parse the command arguments
        args = message.text.split()[1:]
        if len(args) < 1 or len(args) > 2:
            await message.reply(f"**Usage**:\n\n{COMMAND_PREFIX}kick [user_id] [kick_time_in_minutes]")
            return

        if len(args[0]) < 9 or len(args[0]) > 11:
            await message.reply("Invalid user ID! Please provide correct user ID.")
            return

        try:
            user_id = int(args[0])
            kick_time_str = args[1] if len(args) == 2 else str(DEFAULT_KICK_TIME)
        except ValueError:
            await message.reply("User ID and kick time must be integers!")
            return

        # Convert kick time string to datetime.timedelta
        kick_time_str = kick_time_str.lower()
        if kick_time_str.endswith("m"):
            kick_time = timedelta(minutes=int(kick_time_str[:-1]))
        elif kick_time_str.endswith("h"):
            kick_time = timedelta(hours=int(kick_time_str[:-1]))
        elif kick_time_str.endswith("d"):
            kick_time = timedelta(days=int(kick_time_str[:-1]))
        else:
            await message.reply("Invalid kick time format! Please provide kick time in the format of [number][m/h/d].")
            return

        # Save the user ID and kick time to the database
        kick_datetime = datetime.utcnow() + kick_time
        col.insert_one({"chat_id": message.chat.id, "user_id": int(user_id), "kick_time": kick_datetime})

        await message.reply(f"User {user_id} will be kicked in {kick_time_str}.")


async def check_kicks():
    # Check the database for any kicks that need to be performed
    now = datetime.utcnow()
    for kick in col.find({"kick_time": {"$lte": now}}):
        chat_id = kick["chat_id"]
        user_id = kick["user_id"]
        kick_time = kick["kick_time"]
        time_diff = kick_time - now

        if time_diff.total_seconds() <= 0:
            try:
                await app.kick_chat_member(chat_id, user_id)
                await app.unban_chat_member(chat_id, user_id)
            except Exception as e:
                print(f"Error kicking user {user_id} from chat {chat_id}: {e}")

            col.delete_one({"_id": kick["_id"]})


if __name__ == "__main__":
    # start message in terminal
    print("Bot Started 🤩")
    # Start the Pyrogram client
    app.run()

