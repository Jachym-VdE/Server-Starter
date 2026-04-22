import discord
import asyncio
import dotenv, socket, os


# Ensure an event loop is available, it doesn't work otherwise :(
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


dotenv.load_dotenv()

bot = discord.Bot()

mac_address = os.getenv("MAC_ADDRESS")
if not mac_address:
    raise ValueError("MAC_ADDRESS not found in environment variables.")


def send_magic_packet(mac_address: str, broadcast: str = "192.168.1.255", port: int = 9):
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



# ----------------------------- Public Commands -----------------------------
@bot.slash_command(name="ping", description="Check the bot's latency.")
async def ping(ctx: discord.ApplicationContext):
    latency = bot.latency * 1000
    await ctx.respond(f"🏓 Pong! **Latency:** {latency:.2f} ms")


@bot.slash_command(name="whois", description="Get information about a member.")
async def whois(ctx: discord.ApplicationContext, member: discord.Member):
    if member.joined_at is None:
        await ctx.respond("Please specify a valid member.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"User Info",
        color=discord.Color.green()
    )

    embed.add_field(name="User ID: ", value=str(member.id), inline=False)
    embed.add_field(name="Account Created: ", value=discord.utils.format_dt(member.created_at), inline=False)
    embed.add_field(name="Joined Server: ", value=discord.utils.format_dt(member.joined_at), inline=False)

    embed.add_field(name=f"Roles [{len(member.roles) - 1}]: ", value=", ".join([role.mention for role in member.roles if role.name != "@everyone"]), inline=False)
    embed.set_author(name=member, icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

    await ctx.respond(embed=embed, ephemeral=True)


@bot.slash_command(name="wake", description="Send a magic packet to wake up the server.")
async def wake(ctx: discord.ApplicationContext):
    try:
        if not mac_address:
            await ctx.respond("Internal server error: MAC address not configured. Please set the MAC_ADDRESS environment variable.", ephemeral=True)
            return
        send_magic_packet(mac_address)
        await ctx.respond("Magic packet sent!", ephemeral=True)
    except ValueError as e:
        await ctx.respond(f"Error: {e}", ephemeral=True)


token = os.getenv("TOKEN")
if not token:
    raise ValueError("TOKEN not found in environment variables.")

bot.run(token)
