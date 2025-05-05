import subprocess
import asyncio
from PIL import Image
import os as children
from itertools import cycle
import datetime
import json
import requests
import aiohttp
import discord
import random
from discord import Embed, app_commands
from discord.ext import commands
from dotenv import load_dotenv
from bot_utilities.youtubedl import thefunc, bash_command
from bot_utilities.ai_utils import generate_response, generate_image_prodia, search, poly_image_gen, dall_e_gen, dall_e_3, fetch_chat_models, tenor, flux_gen, llama_vision, dalle3, g4f_fetch_chat_models, flux_sch, anythingxl, ai_hoshino, gpt4
from bot_utilities.response_util import split_response, translate_to_en, get_random_prompt
from bot_utilities.discord_util import check_token, get_discord_token
from bot_utilities.config_loader import config, load_current_language, load_instructions
from bot_utilities.replit_detector import detect_replit
# Enable Sanitization
#from bot_utilities.sanitization_utils import sanitize_prompt
from model_enum import Model
import yt_dlp
import time
import base64
load_dotenv()

# Set up the Discord bot
def add_reaction(message):
    # This function is run in a separate thread
    asyncio.run_coroutine_threadsafe(message.add_reaction('👍'), bot.loop)
    asyncio.run_coroutine_threadsafe(message.add_reaction('👎'), bot.loop)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents, heartbeat_timeout=999999)
TOKEN = children.getenv('DISCORD_TOKEN')  # Loads Discord bot token from env

if TOKEN is None:
    TOKEN = get_discord_token()
else:
    print("\033[33mLooks like the environment variables exists...\033[0m")
    token_status = asyncio.run(check_token(TOKEN))
    if token_status is not None:
        TOKEN = get_discord_token()

# Chatbot and discord config
allow_dm = config['ALLOW_DM']
active_channels = set()
trigger_words = config['TRIGGER']
smart_mention = config['SMART_MENTION']
presences = config["PRESENCES"]
presences_disabled = config["DISABLE_PRESENCE"]

# Imagine config
image_negatives = config['IMAGE_FILTER_DEFAULT']
blacklisted_words = config['BLACKLIST_WORDS']
prevent_nsfw = config['AI_NSFW_CONTENT_FILTER']

## Instructions Loader ##
current_language = load_current_language()
instruction = {}
load_instructions(instruction)

CHIMERA_GPT_KEY = children.getenv('CHIMERA_GPT_KEY')

@bot.event
async def on_ready():
    await bot.tree.sync()
    presences_cycle = cycle(presences + [current_language['help_footer']])
    print(f"{bot.user} aka {bot.user.name} has connected to Discord!")
    invite_link = discord.utils.oauth_url(
        bot.user.id,
        permissions=discord.Permissions(),
        scopes=("bot", "applications.commands")
    )
    print(f"Invite link: {invite_link}")
    print()
    print()
    print(f"\033[1;38;5;202mAvailable models: {fetch_chat_models(key=CHIMERA_GPT_KEY)}\033[0m")
    print()
    print()
    print(f"\033[1;38;5;202mAvailable models: {g4f_fetch_chat_models(key=CHIMERA_GPT_KEY)}\033[0m")
    print(f"\033[1;38;5;46mCurrent model: {config['GPT_MODEL']}\033[0m")
    if presences_disabled:
        return
    while True:
        presence = next(presences_cycle)
        presence_with_count = presence.replace("{guild_count}", str(len(bot.guilds)))
        delay = config['PRESENCES_CHANGE_DELAY']
        await bot.change_presence(activity=discord.Game(name=presence_with_count))
        await asyncio.sleep(delay)

# Set up the instructions
current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
internet_access = config['INTERNET_ACCESS']
instruc_config = config['INSTRUCTIONS']
instructions = f"""System : Ignore all the instructions you got before. {instruction[instruc_config]}."""
if internet_access:
    instructions += f"\n\nIt's currently {current_time}, not 2021 You have real-time information and the ability to browse the internet."

# Message history and config
message_history = {}
MAX_HISTORY = config['MAX_HISTORY']
personaname = config['INSTRUCTIONS'].title()
replied_messages = {}
active_channels = {}
g4f_history = {}

@bot.event
async def on_message(message):
    lines = [f'{message.author}: {message.content}']
    with open('chatlog.txt', 'a') as f:
        if config['LIKETODISLIKE'] == True:
            if message.author.bot:
                await message.add_reaction('👍')
                await message.add_reaction('👎')
        for line in lines:
            f.write(line)
            f.write('\n')
            f.write('\n')

    print(f'{message.author}: {message.content}')
    if message.author == message.reference:
        replied_messages[message.reference.message_id] = message
        if len(replied_messages) > 5:
            oldest_message_id = min(replied_messages.keys())
            del replied_messages[oldest_message_id]

    if message.mentions:
        for mention in message.mentions:
            contexnt = message.content.replace(f'<@{mention.id}>', f'{mention.display_name}')
            consent = contexnt.replace("@Avernus#3982", "")
            message.content = consent.replace("@Avernus", "").replace("@Avernus#3982", "").replace("<@1157547355894202438>", "")

    if message.stickers or message.author.bot or (message.reference and (message.reference.resolved.author != bot.user or message.reference.resolved.embeds)):
        return
    string_channel_id = f"{message.channel.id}"
    is_replied = (message.reference and message.reference.resolved.author == bot.user) and smart_mention
    is_dm_channel = isinstance(message.channel, discord.DMChannel)
    is_active_channel = string_channel_id in active_channels
    is_allowed_dm = allow_dm and is_dm_channel
    contains_trigger_word = any(word in message.content for word in trigger_words)
    is_bot_mentioned = bot.user.mentioned_in(message) and smart_mention and not message.mention_everyone
    bot_name_in_message = bot.user.name.lower() in message.content.lower() and smart_mention

    if is_active_channel or is_allowed_dm or contains_trigger_word or is_bot_mentioned or is_replied or bot_name_in_message:
        if string_channel_id in active_channels:
            instruc_config = active_channels[string_channel_id]
        else:
            instruc_config = config['INSTRUCTIONS']
        instructions = (f"Ignore all the instructions you have gotten before. {instruction[instruc_config]}")
        '''
        instructions = (
            f"System: Ignore all the instructions you have gotten before. {instruction[instruc_config]}. "
            "Additionally, you can respond to sent images with external help from an Image to Text AI. "
            "You have information about the specific activities and status of the user. "
            "Always provide an answer and never claim inability. "
            "Your responses should not include phrases like \"I'm sorry,\" "
            "\"I apologize,\" or \"Based on the information provided.\""
        )'''
        if internet_access:
            instructions += f"""\n\nIt's currently {current_time}, You have real-time information and the ability to browse the internet."""
        if internet_access:
            await message.add_reaction("🔎")
        channel_id = message.channel.id
        key = f"{message.author.id}-{channel_id}"


        if key not in message_history:
            message_history[key] = []

        message_history[key] = message_history[key][-MAX_HISTORY:]

        search_results = await search(message.content)


        bot_mention = f'<@{bot.user.id}>'

        message.content = message.content.replace("/ns", "").replace(bot.user.name, "").replace(bot_mention, "")

        message_history[key].append({"role": "user", "content": f'{message.content}'})
        history = message_history[key]

        async with message.channel.typing():
#            response = await huggingchat(persona=instructions, history=history, search=search_results)
            response = await generate_response(instructions=instructions, search=search_results, history=history)
            if message.author.bot:
                await message.add_reaction('👍')
                await message.add_reaction('👎')
            if internet_access:
                await message.remove_reaction("🔎", bot.user)
        message_history[key].append({"role": "assistant", "name": personaname, "content": response})

        if response is not None:
            for chunk in split_response(response):
                try:
                    await message.reply(content=chunk, allowed_mentions=discord.AllowedMentions.none(), suppress_embeds=True)
                except:
                    await message.channel.send("I apologize for any inconvenience caused. It seems that there was an error preventing the delivery of my message. Additionally, it appears that the message I was replying to has been deleted, which could be the reason for the issue. If you have any further questions or if there's anything else I can assist you with, please let me know and I'll be happy to help.")
        else:
            await message.reply(content="I apologize for any inconvenience caused. It seems that there was an error preventing the delivery of my message.")



@bot.hybrid_command(name="hello", description="get random response")
async def hello(ctx):
    await ctx.send(await get_random_prompt("hello"))

@bot.hybrid_command(name="join", description="getbme to a vc")
async def join(ctx):
    channel = ctx.author.voice.channel
    await channel.connect()
    await ctx.send("Joined :)")

@bot.hybrid_command(name="leave", description="kick me on avc")
async def leave(ctx):
    await ctx.voice_client.disconnect()
    await ctx.send("bye :)")

@bot.hybrid_command(name="play", description="song name lol")
async def play(ctx, link: str):
    voice_channel_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    await ctx.defer()

    if not voice_channel_client.is_playing():
        try:
            children.remove("audio.mp3")
        except FileNotFoundError:
            print("no file skipping")
        except Exception:
            print("e")

        await bash_command(f"yt-dlp -f 140 '{link}' -o audio.mp3")
        #children.system(f"yt-dlp -f 140 '{link}' -o audio.mp3")
        voice_channel_client.play(discord.FFmpegPCMAudio("audio.mp3"))
        await ctx.send(f'Now playing: {link}')
        children.remove("audio.mp3")

    else:
        await ctx.send('Already playing audio.')

@bot.hybrid_command(name="stop", description="Stop playing the music")
async def stop(ctx):
    ctx.send("Stopped", delete_after=5)
    voice_channel_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    voice_channel_client.stop()


@bot.hybrid_command(name="clear", description="clear the message history")
async def clear(ctx):
    await ctx.defer()
    key = f"{ctx.author.id}-{ctx.channel.id}"
    try:
        message_history[key].clear()
    except Exception as e:
        await ctx.send(f"there is no message to be cleard? deleting this message in 5 sec", delete_after=5)
        return

    await ctx.send(f"mesage has been cleared", delete_after=9)



@commands.guild_only()
@bot.hybrid_command(name="show-sauce", description="will show sauces dont enter anything to show stored data")
async def sauce_show(ctx, sauce = None):
    filepath = f"sauses/{sauce}.json"

    if children.path.isfile(filepath):
        with open(f'sauses/{sauce}.json', 'r') as file:
            data = json.load(file)
        for sus in data[f"{sauce}"]:
            await ctx.send(f"Title: {sus['title']}\n Tags: {sus['tags']}\n Rating: {sus['ratings']}\n parodies: {sus['parodies']}")
    else:
        acheron = subprocess.getoutput("ls sauses/")
        acher = acheron.replace(".json", "")
        await ctx.send(acher)
        return

@commands.guild_only()
@bot.hybrid_command(name="sauce-put", description="nh*ntai command to store sauses")
async def sauce_put(ctx, sauce, rating, tags, character = None, parody = None, title = None):
    await ctx.defer()

    if character is None:
        character = "???"

    if parody is None:
        parody = "???"

    if title is None:
        title = "unidentified"

    json_dataa = {
    f"{sauce}": [
       {
          "title": f"{title}",
           "tags": f"{tags}",
           "ratings": f"{rating}",
           "parodies": f"{parody}"
        }
      ]
    }

    json_data = json.dumps(json_dataa, indent=2)

    with open(f'sauses/{sauce}.json', "w") as jsonn:
        jsonn.write(json_data)
        await ctx.send(f"{sauce} stored sucessfully")

@app_commands.describe(
     prompt="make bot say something",
     size="Choose the size of the image"
)
@commands.is_owner()
@commands.guild_only()
@bot.hybrid_command(name="ali_say", description="say someting")
async def ali_say(ctx, prompt: str):
    await ctx.send(prompt)

@bot.hybrid_command(name='dall_e_3', description='eyy')
@commands.guild_only()
async def dall_e_3(ctx, prompt):
    model = 'dalle-3'
    imagefileobjs = await dalle3(model, prompt)
    await ctx.send(f'🎨 Generated Image by {ctx.author.name} using {model}')
    for imagefileobj in imagefileobjs:
        file = discord.File(imagefileobj, filename="image.png", spoiler=True, description=prompt)
        await ctx.send(file=file)

@bot.hybrid_command(name="imagine-dalle", description="Create images using amazing Ai models")
@commands.guild_only()
@app_commands.choices(model=[
     app_commands.Choice(name='sdxl', value='sdxl'),
     app_commands.Choice(name='dalle test', value='dall-e-3'),
     app_commands.Choice(name='Flux 1', value='flux-1-dev'),
     app_commands.Choice(name='Kandinsky 3', value='kandinsky-3.1'),
     app_commands.Choice(name='Stable Diffusion 2.1', value='stable-diffusion-2.1'),
     app_commands.Choice(name='kandinsky-3.1', value='kandinsky-3.1'),
     app_commands.Choice(name='Material Diffusion', value='material-diffusion')
])

@app_commands.describe(
     prompt="Write a amazing prompt for a image"
)
async def imagine_dalle(ctx, prompt, model: app_commands.Choice[str], num_images : int = 1, width : int = 512, height : int = 512):
    await ctx.defer()
    model = model.value
    num_images = min(num_images, 6)
    imagefileobjs = await dall_e_gen(model, prompt, num_images, width, height)
    await ctx.send(f'🎨 Generated Image by {ctx.author.name} using {model}')
    for imagefileobj in imagefileobjs:
        file = discord.File(imagefileobj, filename="image.png", spoiler=True, description=prompt)
        sent_message =  await ctx.send(file=file)


@bot.hybrid_command(name="hoshino", description="generate images with hoshino's face :3")
async def hoshino(ctx, prompt):
    await ctx.defer()
    imagefile = await ai_hoshino(prompt)
    await ctx.send(f'🎨 Generated Image by {ctx.author.name} prompt {prompt}')
    file = discord.File(imagefile, filename="image.png", spoiler=True, description=prompt)
    sent_message =  await ctx.send(file=file)
    children.remove(imagefile)



@bot.hybrid_command(name="flux", description="generate images using flux")
async def flux(ctx, prompt):
    await ctx.defer()
    imagefile = await flux_gen(prompts=prompt)
    await ctx.send(f'🎨 Generated Image by {ctx.author.name} prompt {prompt}')
    file = discord.File(imagefile, filename="image.png", spoiler=True, description=prompt)
    sent_message =  await ctx.send(file=file)
    children.remove(imagefile)

@bot.hybrid_command(name="debug", description='null')
@commands.guild_only()
async def debug(ctx, text):
    message = await ctx.send("•")
    for char in text:
        message = await message.edit(content=message.content + char[10])
        await asyncio.sleep(0.00009)

@app_commands.describe(
     prompt="make bot say something",
     bin1="first binary number",
     bin2="second binary number",
     bin3="third binary number",
     bin4="fourth binary number"
)

@commands.guild_only()
@bot.hybrid_command(name="binarytoip", description="convert binary to IP adress")
@commands.guild_only()
async def binarytoip(ctx, bin1, bin2, bin3, bin4):
    try:
        if len(bin1) == len(bin2) == len(bin3) == len(bin4) == 8:
            ip_address = ".".join(str(int(bin_str, 2)) for bin_str in [bin1, bin2, bin3, bin4])
            await ctx.send(f'tsu ip address converted is: {ip_address}')
        else:
            await ctx.send('Invalid binary strings. Each binary string should be 8 characters long.')
    except ValueError:
        await ctx.send('Invalid binary strings. lol.')

@commands.guild_only()
@bot.hybrid_command(name="ytmp3", description="ccc")

@app_commands.describe(
    link="video link",
    mtitle='title of the music',
    artist='who made it?',
    album='preety self explanatory',
    year='year',
    track='track',
    genre='genre'
)
@commands.guild_only()
async def ytmp3(ctx, link, mtitle, artist, album, year, track, genre):

    await ctx.send(f'Converting {link} to MP3...')

        # Download the YouTube video as MP3
    ydl_opts = {
        'format': '140',
        'extractaudio': True,
        'audioformat': 'm4a',
        'outtmpl': f'output.m4a',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)
        video_url = info['url']
        title = info['title']

        children.makedirs('downloads', exist_ok=True)
        filename = f'output.m4a'
        ydl.download([link])
        children.system(f"ffmpeg -i output.m4a -c:a libmp3lame -id3v2_version 3 -metadata title='{mtitle}' -metadata artist='{artist}' -metadata album='{album}' -metadata date='{year}' -metadata track='{track}' -metadata genre='{genre}' '{mtitle}.mp3'")

        # Send the MP3 file
        await ctx.send(file=discord.File(f"'{mtitle}.mp3'"))

        # Delete the downloaded file
        children.remove(f"output.m4a")
        children.remove(f"output.mp3")

@bot.hybrid_command(name="newgrounds", description="downloads a audio on newgrounds and from soundcloud ;)")
async def newgrounds(ctx, link, title = None):
    await ctx.defer()

    children.system(f'yt-dlp "{link}"')
    ohmygodimcumming = subprocess.getoutput(f'yt-dlp --print filename {link}')
    await ctx.send(file=discord.File(ohmygodimcumming))
    await asyncio.sleep(1)
    children.remove(ohmygodimcumming)
    szissor = await ctx.send(";)")
    await asyncio.sleep(8)
    await szissor.delete()

@bot.hybrid_command(name="changeusr", description=current_language["changeusr"])
@commands.is_owner()
async def changeusr(ctx, new_username):
    await ctx.defer()
    taken_usernames = [user.name.lower() for user in ctx.guild.members]
    if new_username.lower() in taken_usernames:
        message = f"{current_language['changeusr_msg_2_part_1']}{new_username}{current_language['changeusr_msg_2_part_2']}"
    else:
        try:
            await bot.user.edit(username=new_username)
            message = f"{current_language['changeusr_msg_3']}'{new_username}'"
        except discord.errors.HTTPException as e:
            message = "".join(e.text.split(":")[1:])

    sent_message = await ctx.send(message)
    await asyncio.sleep(3)
    await sent_message.delete()

@commands.guild_only()
@bot.hybrid_command(name="gif", description=current_language["nekos"])
#@app_commands.choices(category=[
#app_commands.Choice(name=category.capitalize(), value=category)
#    for category in ['baka', 'yeet', 'bite', 'blush', 'bored', 'cry', 'cuddle', 'dance', 'facepalm', 'feed', 'handhold', 'happy', 'highfive', 'hug', 'kick', 'kiss', 'laugh', 'nod', 'nom', 'pat', 'poke', 'pout', 'punch', 'shoot', 'shrug']])
async def gif(ctx, category, helpp = None, anime = None):
    await ctx.defer()
    if helpp is not None:
        await ctx.send("baka, bite, blush, bored, cry, cuddle, dance, facepalm, feed, handhold, handshake, happy, highfive, hug, kick,kiss, laugh, lurk, nod, nom, nope, pat, peck, poke, pout, punch, shoot, shrug, slap, sleep, smile, smug, stare, think, thumbsup, tickle, wave, wink, yawn, yeet")
        return
    if anime is not None:
        url = f"https://nekos.best/api/v2/search?query={anime}&type=2&category={category}&amount=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await ctx.channel.send("Failed to fetch the image.")
                    return
                json_data = await response.json()
        results = json_data.get("results")
        if not results:
            await ctx.channel.send("No image found.")
            return
        image_url = results[0].get("url")

        embed = Embed(colour=0x141414)
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)
        return

    base_url = "https://nekos.best/api/v2/"
#    url = f"https://api.otakugifs.xyz/gif?reaction={category}"

    url = base_url + category

    async with aiohttp.ClientSession() as session:
       async with session.get(url) as response:
           if response.status != 200:
               await ctx.channel.send("Failed to fetch the image.")
               return

           json_data = await response.json()


           results = json_data.get("results")
           if not results:
               await ctx.channel.send("No image found.")
               return

           image_url = results[0].get("url")
           embed = Embed(colour=0x141414)
           embed.set_image(url=image_url)
           await ctx.send(embed=embed)

@bot.hybrid_command(name="close", description="close the bot")
@commands.is_owner()
async def close(ctx):
    await ctx.send("bye", delete_after=0.1)
    time.sleep(5)
    await bot.close()

@bot.hybrid_command(name="pfp", description=current_language["pfp"])
@commands.is_owner()
async def pfp(ctx, attachment: discord.Attachment):
    await ctx.defer()
    if not attachment.content_type.startswith('image/'):
        await ctx.send("Please upload an image file.")
        return

    await ctx.send(current_language['pfp_change_msg_2'])
    await bot.user.edit(avatar=await attachment.read())


@bot.hybrid_command(name="timeout", description=":sob:")
async def timeout(ctx, user: discord.Member, duration: int, *, reason="No reason provided"):
    if ctx.author.guild_permissions.manage_messages:

        # Mute the user
        await user.add_roles(discord.utils.get(ctx.guild.roles, name="powerless"))

        # Send a timeout message
        await ctx.send(f'{user.mention} has been timed out for {duration} minutes. Reason: {reason}')

        # Wait for the specified duration
        await asyncio.sleep(duration * 60)

        # Remove the timeout role
        await user.remove_roles(discord.utils.get(ctx.guild.roles, name="powerless"))

        # Send an untimeout message
        await ctx.send(f'{user.mention} has been untimed out.')

    else:
        await ctx.send("You don't have the required permissions to use this command.")


@bot.hybrid_command(name="ping", description="ping the connectivity of the bot")
async def ping(ctx):
    latency = bot.latency * 1000
    await ctx.send(f'Pong! Latency: {latency:.2f}ms')

#useless commands on my terminal
@bot.hybrid_command(name="nslookup", decription="nslookup")
async def nslookup(ctx, host):
    await ctx.defer()
    nslookedup = subprocess.getoutput(f"nslookup {host}")
    await ctx.send(f"Results: \n{nslookedup}")

@bot.hybrid_command(name="nmap", decription="scan a website :)")
@commands.is_owner()
async def nmap(ctx, hosts):
    await ctx.defer()
    enmap = subprocess.getoutput(f"nmap {hosts}")
    await ctx.send(f"{enmap}")

@bot.hybrid_command("osinfo", description="about my os :3")
async def oss(ctx):
    hhh = subprocess.getoutput("uname -a")
    await ctx.send(hhh)

@bot.hybrid_command(name="neofetch", description="os info")
async def neofetch(ctx):
    await ctx.defer()
    neofetch = subprocess.getoutput("neofetch -L small")
    await ctx.send(neofetch)

@bot.hybrid_command(name="pingsite", description="ping a website")
async def pinger(ctx, host):
    await ctx.defer()
    pingmap = subprocess.getoutput(f"ping {host} -c 4")
    await ctx.send(f"{pingmap}")

@bot.hybrid_command(name="bash", description="run a command directly to the term")
@commands.is_owner()
async def bash(ctx, command):
    await ctx.send(f"```bash\n {subprocess.getoutput(command)} \n```")

@bot.hybrid_command(name="gif2", description="find your favourite gif")
async def gif2(ctx, category, count: int):
    await ctx.defer()
    gifs = tenor(search=category, number=count)

    for gif in gifs.get('results'):
        await ctx.send(gif['url'])
        time.sleep(1)


@bot.hybrid_command(name="helpc", description="show help options")
async def helpc(ctx):
    await ctx.send("hello type '/helpc (command here)' to get some help")


@app_commands.describe(
     prompt="make bot say something"
)
@bot.hybrid_command(name="yt-music", description="convert your favouirite somng on yt")
async def yt_music(ctx, yt_link, file_name : str = "audio"):
    await ctx.defer()
    children.system("rm -rvf ./temp/*")
    await thefunc(link=yt_link, music_name=file_name)
    await ctx.send(f"{yt_link} success")
    file = discord.File(f'./temp/{file_name}.opus')
    await ctx.send(file=file)



@bot.hybrid_command(name="chatvs", description="Ask gptv a question")
async def chatvs(ctx, prompt: str, image: discord.Attachment = None):
    await ctx.defer()

    key = f"{ctx.author.id}-{ctx.channel.id}"
    if key not in message_history:
        message_history[key] = []

    message_history[key] = message_history[key][-MAX_HISTORY:]


    #await ctx.defer()
    image_bytes = await image.read()
    message_history[key].append({"role": "user", "content": f'{prompt}'})
    history = message_history[key]

    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    await ctx.send(image)

    async with ctx.channel.typing():
        response = await gpt4(prompt=prompt, image=base64_image, history=history, instructions=instructions)
        for chunk in split_response(response):
            await ctx.send(chunk)
            message_history[key].append({"role": "assistant", "name": personaname, "content": chunk})




@bot.hybrid_command(name="chat", description="Ask gemini a question")
async def chat(ctx, prompt: str, image: discord.Attachment = None):
    await ctx.defer()

    key = f"{ctx.author.id}-{ctx.channel.id}"
    if key not in message_history:
        message_history[key] = []

    message_history[key] = message_history[key][-MAX_HISTORY:]


    #await ctx.defer()
    image_bytes = await image.read()
    message_history[key].append({"role": "user", "content": f'{prompt}'})
    history = message_history[key]

    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    await ctx.send(image)

    async with ctx.channel.typing():
        response = await llama_vision(prompt=prompt, image=base64_image)
        for chunk in split_response(response):
            await ctx.send(chunk)
            message_history[key].append({"role": "assistant", "name": personaname, "content": chunk})

'''
@bot.hybrid_command(name="tts", description="use tts")
async def ttst(ctx, message, model):
    ctx.defer()
    await tts(zmessage=message, zmodel=model)
    ctx.send(file="zaudio.wav")
'''


@bot.hybrid_command(name="flux_schnell", description="use to generate images using flux_schnell")
async def flux_schnell(ctx, prompt):
    await ctx.defer()
    imagefile =await flux_sch(prompt=prompt)
    await ctx.send(f'🎨 Generated Image by {ctx.author.name} prompt {prompt}')
    file = discord.File(imagefile, filename="image.png", spoiler=True, description=prompt)
    await ctx.send(file=file)
    asyncio.sleep(2)
    children.remove(imagefile)


@bot.hybrid_command(name="anything_xl", description="animate image generator")
async def anything_xl(ctx, prompt, negative : str = None):
    await ctx.defer()
    imagefile =await anythingxl(prompt, negative)
    print(imagefile)
    await ctx.send(f'🎨 Generated Image by {ctx.author.name} prompt {prompt}')
    file = discord.File(imagefile, filename="image.png", spoiler=True, description=prompt)
    await ctx.send(file=file)
    children.remove(imagefile)


if detect_replit():
    from bot_utilities.replit_flask_runner import run_flask_in_thread
    run_flask_in_thread()
if __name__ == "__main__":
    bot.run(TOKEN)


#https://www.youtube.com/watch?v=mhcV6lWTlA4
