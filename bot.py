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

# Default kick time in hours
DEFAULT_KICK_TIME_HOURS = int(os.getenv("DEFAULT_KICK_TIME_HOURS", "720"))  # 30 days in hours

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

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply("Hi,\nI'm KickBot And I can Kick Members, From Your Group, After Given Time")


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
            await message.reply(f"Usage:\n{COMMAND_PREFIX}kick [user_id] [kick_time_in_hours]")
            return

        user_id = args[0]
        kick_time = args[1] if len(args) == 2 else DEFAULT_KICK_TIME_HOURS

        # Save the user ID and kick time to the database
        kick_time = int(kick_time)
        kick_datetime = datetime.utcnow() + timedelta(hours=kick_time)
        col.insert_one({"chat_id": message.chat.id, "user_id": int(user_id), "kick_time": kick_datetime})

        await message.reply(f"User {user_id} will be kicked in {kick_time} hours.")


async def check_kicks():
    # Check the database for any kicks that need to be performed
    now = datetime.utcnow()
    for kick in col.find({"kick_time": {"$lte": now}}):
        chat_id = kick["chat_id"]
        user_id = kick["user_id"]

        try:
            await app.kick_chat_member(chat_id, user_id)
            await app.unban_chat_member(chat_id, user_id)
        except Exception as e:
            print(f"Error kicking user {user_id} from chat {chat_id}: {e}")

        col.delete_one({"_id": kick["_id"]})

if __name__ == "__main__":
    # Start the Pyrogram client
    app.run()
