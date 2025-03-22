import logging
from utils import load_cogs

import discord
from discord.ext import commands

from settings import settings

logger = logging.getLogger('bot')

BOT_TOKEN = settings.BOT_SECRET_TOKEN

# Intents (permissions)
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    logger.info('Bot is ready - logged in as %s', bot.user)

# Load cogs dynamically
@bot.event
async def setup_hook():
    logger.info("🔧 Running setup_hook...")
    await load_cogs(bot)


bot.run(BOT_TOKEN)
