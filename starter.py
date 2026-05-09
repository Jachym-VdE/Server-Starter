import discord, asyncio, dotenv, configparser, socket, os
from datetime import datetime, timezone, timedelta


# Ensure an event loop is available, it doesn't work otherwise :(
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

dotenv.load_dotenv()

config = configparser.ConfigParser()
config.read("config.ini")


# --- FEATURES ---
RESPONSIBLE_USER_ENABLED = config.getboolean("features", "enable_responsible_user", fallback=False)
BOT_CHANNEL_ENABLED = config.getboolean("features", "enable_bot_channel", fallback=False)

# --- DISCORD ---
BOT_NAME = config.get("discord", "bot_name", fallback="Server Starter")
RESPONSIBLE_USER = config.get("discord", "responsible_user", fallback=None)

# --- IDS ---
BOT_CHANNEL_ID = config.getint("discord.ids", "bot_channel_id")
ROLE_ID = config.getint("discord.ids", "bot_user_role_id")

# --- NETWORK ---
SERVER_MAC = config.get("network", "mc_server_mac")
BROADCAST_IP = config.get("network", "broadcast_ip")


bot = discord.Bot()

def _send_magic_packet(mac_address: str, broadcast: str = "192.168.1.255", port: int = 9):
    # Clean and validate MAC address
    mac = mac_address.replace(":", "").replace("-", "").replace(".", "")
    if len(mac) != 12 or not all(c in "0123456789abcdefABCDEF" for c in mac):
        raise ValueError(f"Invalid MAC address: {mac_address}")
 
    # Build the magic packet: 6x 0xFF + MAC repeated 16 times
    mac_bytes = bytes.fromhex(mac)
    packet = b"\xff" * 6 + mac_bytes * 16
 
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (broadcast, port))
 
    print(f"Magic packet sent to {mac_address} via {broadcast}:{port}")


# ----------------------------- Events -----------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="/help"
        )
    )


@bot.event
async def on_message(message: discord.Message):
    if BOT_CHANNEL_ENABLED and message.channel.id == BOT_CHANNEL_ID and not message.author.bot and not message.content.startswith("/"):
        await message.delete()


# ----------------------------- Public Commands -----------------------------
@bot.slash_command(name="help", description="Show all available commands.")
async def help(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title=f"{BOT_NAME} — Help",
        description="Here's a list of all available commands:",
        color=discord.Color.blurple()
    )

    embed.add_field(name="/help", value="Show this help message.", inline=False)
    embed.add_field(name="/ping", value="Check the bot's latency.", inline=False)
    embed.add_field(name="/wake", value="Send a Wake-on-LAN magic packet to start the server.", inline=False)
    embed.add_field(name="More features are coming!", value="More features are planned and will be added periodically.", inline=False)

    embed.set_author(name=BOT_NAME, icon_url=bot.user.display_avatar.url if bot.user else None)
    await ctx.respond(embed=embed, ephemeral=True)


@bot.slash_command(name="ping", description="Check the bot's latency.")
async def ping(ctx: discord.ApplicationContext):
    latency = bot.latency * 1000
    await ctx.respond(f"🏓 Pong! **Latency:** {latency:.2f} ms", ephemeral=True)


@bot.slash_command(name="wake", description="Send a magic packet to wake up the server.")
async def wake(ctx: discord.ApplicationContext):
    try:
        if not SERVER_MAC:
            await ctx.respond("Internal server error: MAC address not configured. Please set the MAC_ADDRESS environment variable.", ephemeral=True)
            return
        
        _send_magic_packet(SERVER_MAC, BROADCAST_IP)
        
        embed = discord.Embed(
            title=f"Magic Packet Sent Successfully!",
            color=discord.Color.green()
        )

        embed.add_field(name="Awoken by: ", value=str(ctx.author.mention), inline=False)
        cest = timezone(timedelta(hours=2))
        midnight_cest = (datetime.now(cest) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        embed.add_field(name="Awoken until: ", value=discord.utils.format_dt(midnight_cest, style="t"), inline=False)
        embed.set_author(name=BOT_NAME, icon_url=bot.user.display_avatar.url if bot.user else None)
        
        if RESPONSIBLE_USER_ENABLED and RESPONSIBLE_USER is not None:
            embed.set_footer(text=f"If the server fails to start, ping @{RESPONSIBLE_USER} for support.")

        await ctx.respond(embed=embed, ephemeral=False)
    except Exception as e:
        await ctx.respond(f"Error: {e}", ephemeral=True)


token = os.getenv("TOKEN")
if not token:
    raise ValueError("TOKEN not found in environment variables.")

bot.run(token)
