import os
import logging
import importlib
import inspect
from discord.ext import commands

logger = logging.getLogger('bot')

async def load_cogs(bot: commands.Bot) -> commands.Bot:
    """Load all cogs in the cogs directory."""
    logger.info("🕔 Loading cogs...")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_path = f"cogs.{filename[:-3]}"
            try:
                module = importlib.import_module(module_path)
                has_cog = any(
                    issubclass(obj, commands.Cog) and obj is not commands.Cog
                    for _, obj in inspect.getmembers(module, inspect.isclass)
                )
                if has_cog:
                    await bot.load_extension(module_path)
                    logger.info(f"✅ Loaded: {module_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load {module_path}: {e}")

    return bot