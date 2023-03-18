import asyncio
from datetime import datetime, timedelta
import os
from pyrogram import Client, filters
import motor.motor_asyncio


# MongoDB variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ryme:ryme@cluster0.32cpya3.mongodb.net/?retryWrites=true&w=majority")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "mydatabase")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "kicks")

# Pyrogram variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")

# Command prefix
COMMAND_PREFIX = os.getenv("PREFIX", ".")

# Default kick time in minutes
DEFAULT_KICK_TIME = int(os.getenv("DEFAULT_KICK_TIME", "43200"))  # 30 days in minutes


# Set up the MongoDB client and database
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
col = db[MONGO_COLLECTION_NAME]


# Set up the Pyrogram client
app = Client(
    "kickbot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
)


async def start_command(client: Client, message: filters.Message):
    user = message.from_user
    await message.reply(f"Hi {user.first_name},\n\nI'm KickBot, kicks group members after a given time. Boom!")


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
    await col.insert_one({"chat_id": message.chat.id, "user_id": int(user_id), "kick_time": kick_datetime})

    await message.reply(f"User {user_id} will be kicked in {kick_time_str}.")


async def check_kicks():
    # Check the database for any kicks that need to be performed
    now = datetime.utcnow()
    async for kick in col.find({"kick_time": {"$lte": now}}):
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

            await col.delete_one({"_id": kick["_id"]})


async def check_kicks_periodic():
    while True:
        # Check the kicks database
        await check_kicks()
        # Wait for 1 minute before checking again
        await asyncio.sleep(60)

if __name__ == "__main__":
    # Start the bot
    asyncio.get_event_loop().run_until_complete(app.start())
    asyncio.get_event_loop().create_task(check_kicks_periodic())
    asyncio.get_event_loop().run_forever()

