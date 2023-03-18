import asyncio
from datetime import datetime, timedelta
import os
import pymongo
from pyrogram import Client, filters, enums
from pyrogram.types import *
from signal import SIGINT, SIGTERM

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
    user = message.from_user
    await message.reply(f"Hi {user.first_name},\n\nI'm KickBot, kicks group members after given time. Boom!")


@app.on_message(filters.command("kick", prefixes=COMMAND_PREFIX) & filters.group)
async def kick_command(client: Client, message: Message):
    # Check if the user is a group admin
    if message.from_user.id not in (await message.chat.get_administrators()).user_ids:
        await message.reply("You must be a group admin to use this command!")
        return

    # Parse the command arguments
    args = message.text.split()[1:]
    if len(args) not in (1, 2):
        await message.reply(f"Usage:\n{COMMAND_PREFIX}kick [user_id] [kick_time]")
        return

    user_id = args[0]
    if not user_id.isdigit() or not (9 <= len(user_id) <= 11):
        await message.reply("Invalid user ID! Please provide a valid user ID.")
        return

    kick_time_str = args[1].lower() if len(args) == 2 else f"{DEFAULT_KICK_TIME}m"
    if not kick_time_str[:-1].isdigit() or kick_time_str[-1] not in ("m", "h", "d"):
        await message.reply("Invalid kick time format! Please provide kick time in the format of [number][m/h/d].")
        return

    kick_time = {
        "m": timedelta(minutes=int(kick_time_str[:-1])),
        "h": timedelta(hours=int(kick_time_str[:-1])),
        "d": timedelta(days=int(kick_time_str[:-1])),
    }.get(kick_time_str[-1])

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
                await app.ban_chat_member(chat_id, user_id)
                await app.unban_chat_member(chat_id, user_id)
            except Exception as e:
                print(f"Error kicking user {user_id} from chat {chat_id}: {e}")

            col.delete_one({"_id": kick["_id"]})

async def check_kicks_periodic():
    while True:
        # Check the kicks database
        await check_kicks()
        # Wait for 1 minute before checking again
        await asyncio.sleep(60)

async def run_forever():
    # Start the periodic kicks checker
    asyncio.create_task(check_kicks_periodic())
    # Start the bot
    await app.start()

if __name__ == "__main__":
    asyncio.run(run_forever())
    # notify
    print("started vroom vroom •••")
