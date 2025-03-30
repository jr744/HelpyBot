import os
import discord
import logging
from discord.ext import commands
from discord import app_commands

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ticket_bot')

# Create needed folders (mantido para compatibilidade)
os.makedirs('data', exist_ok=True)

# Inicializa os arquivos JSON
print("Sistema usando arquivos JSON para armazenamento")

# Initialize the bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Discord bot token from environment variable
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    logger.error("No Discord bot token found in environment variables!")
    exit(1)

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')
    print(f'Bot logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # Verificar e limpar tickets de canais que não existem mais
    try:
        print("Verificando tickets para canais inexistentes...")
        await verify_ticket_channels()
        print("Verificação de tickets concluída")
    except Exception as e:
        logger.error(f"Erro ao verificar tickets: {e}")
        print(f"Erro ao verificar tickets: {e}")
    
    # Load cogs
    try:
        print("Loading cogs...")
        await bot.load_extension("cogs.ticket_commands")
        print("- Ticket commands loaded")
        await bot.load_extension("cogs.ticket_buttons")
        print("- Ticket buttons loaded")
        await bot.load_extension("cogs.ticket_dropdowns")
        print("- Ticket dropdowns loaded")
        await bot.load_extension("cogs.ticket_modals")
        print("- Ticket modals loaded")
        logger.info("All cogs loaded successfully")
        print("All cogs loaded successfully")
    except Exception as e:
        logger.error(f"Error loading cogs: {e}")
        print(f"Error loading cogs: {e}")
    
    # Sync commands
    try:
        print("Syncing commands...")
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
        print(f"Failed to sync commands: {e}")

async def verify_ticket_channels():
    """Verifica se os canais de ticket ainda existem e remove os que não existem mais da base de dados"""
    from utils.db_manager import verify_ticket_channels as db_verify_ticket_channels
    
    # Contador de tickets removidos
    removed_count = 0
    
    # Verificar cada servidor que o bot está
    for guild in bot.guilds:
        try:
            # Verificar tickets deste servidor
            count = db_verify_ticket_channels(guild)
            removed_count += count
        except Exception as e:
            logger.error(f"Erro ao verificar tickets do servidor {guild.id}: {e}")
    
    if removed_count > 0:
        logger.info(f"Total de {removed_count} tickets removidos durante a verificação")
        print(f"Total de {removed_count} tickets removidos durante a verificação")

@bot.event
async def on_guild_join(guild):
    logger.info(f"Bot joined a new guild: {guild.name} (ID: {guild.id})")
    from utils.db_manager import initialize_guild_config
    initialize_guild_config(guild.id)

@bot.event
async def on_app_command_error(interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("Você não tem permissão para usar este comando!", ephemeral=True)
    else:
        logger.error(f"Command error: {error}")
        await interaction.response.send_message(f"Ocorreu um erro ao executar o comando: {error}", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)