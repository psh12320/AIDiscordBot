import os
import openai
from dotenv import load_dotenv
from discord.ext import commands
import discord
from discord.ui import Button, View
from openai import OpenAI
import asyncio
from pydub import AudioSegment
from io import BytesIO
from config import *
import tempfile
import whisper
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# MONGODB_KEY = os.getenv('MONGODB_CLUSTER_PW')
openai.api_key = OPENAI_API_KEY
openai_client = OpenAI()
model = whisper.load_model("base")

uri = f"mongodb+srv://pshricharan2020:xT3krHvuiTrQRTR9@convostorage.uko3c48.mongodb.net/?retryWrites" \
      f"=true&w=majority&appName=convostorage"
mongo_client = MongoClient(uri, server_api=ServerApi('1'))
try:
    mongo_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = mongo_client["convostorage"]
convo = db["convo"]
db.convo.delete_many({})

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.ignore_on_message = False

connections = {}
# "mouthwatering", "finger-licking good", "to die for", "absolutely delicious",
# "Eyes like sparkling diamonds", "Radiant smile", "Graceful movement", "Sculpted features", "Effortless elegance", "Mesmerizing charm"
word_list = [["heavenly", "a taste explosion", "can't get enough of"],
             ["innovative solutions", "transformation", "engagement"],
             ["My first impression of", "You can't beat", "fall in love with"]
            ]
# current_conversation_status = []
# current_status = 0

# TODO:
# 1. Figure out how to delete or end conversation (DONE)
# 2. Store list of words in MongoDB and check (DONE)
# 3. Find a better way to get the inputs (DONE)
# 4. Word check from Word List: Check text. If it matches chat completion, then ok, else follow text.
# 5. Database issue with Word List: document not deleted.


def save_audio(data, filename):
    audio = AudioSegment.from_file(BytesIO(data), format='wav')
    audio.export(filename, format='wav')


async def generate_conversation(user_id, text):
    result = db.convo.find_one({'userid': user_id})
    print("USER ID FOUND")
    if result:
        topic = result["topic"]
        convotype = result["convotype"]
        style = result["style"]
        difficulty = result["difficulty"]
        wordlist = result["wordlist"]
        lang = str(result["nativelanguage"])
        currentstatus = int(result["currentstatus"])
        conversation = result["conversation"]
        print("VALUES RECEIVED FROM DATABASE")
        if currentstatus == 0:
            # first time conversation
            print("FIRST TIME CONVERSATION BEGINNING")
            print("DEBUGGING 1")
            if str(convotype) == "Conversation" or "conversation":
                message = [
                    {"role": "system", "content": f"You are to start and maintain a conversation on {topic} in a {style} style using some words from this list: {wordlist}. The conversation should be at a {difficulty} English level. Use the words naturally in context. You must provide feedback in both English and {lang} on: 1. Correct context? 2. Correct position? 3. Correct pronunciation? Give a hint on using the unused phrases from the list and suggest a better response in English if needed. Provide the output in this format: [Your reply to the user] Feedback (English): [You will provide this] Hint (English): [You will provide this] Feedback ({lang}): [You will provide this] Hint ({lang}): [You will provide this] Better Response in English: [You will provide this]"},
                    {"role": "user", "content": text}
                ]

                chat_completion = openai_client.chat.completions.create(
                    model='gpt-3.5-turbo',
                    messages=message,
                    temperature=0.3
                )
                qa = chat_completion.choices[0].message.content
                chat_completion = openai_client.chat.completions.create(
                    model='gpt-3.5-turbo',
                    messages=[
                        {"role": "system", "content": f"Here is a list of phrases: {wordlist}. Identify which phrases were NOT used by the user from this list. Output a python list of unused phrases. Return '[]' if all phrases were used."},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.3
                )
                remaining_list = chat_completion.choices[0].message.content
                generate_audio_reply(qa)
                await play_audio_in_channel(1247498910616780824, "C:/Users/Shricharan"
                                                  "/PycharmProjects"
                                                  "/AIDiscordBot_Test3/speech.mp3")
                conversation += message
                conversation += [{"role": "assistant", "content": qa}]
                db.convo.update_one({"userid": user_id}, {"$set": {"conversation": conversation}})
                db.convo.update_one({"userid": user_id}, {"$set": {"currentstatus": 1}})
                db.convo.update_one({"userid": user_id}, {"$set": {"wordlist": remaining_list}})
                return qa
            elif str(convotype) == "Monotype" or "monotype":
                message = [
                    {"role": "system", "content": f"The user will present a monotalk about {topic} in a {style} style using a {difficulty} English level and some words from this list: {wordlist}. You must provide feedback in both English and {lang} on: 1. Correct context? 2. Correct position? 3. Correct pronunciation? Give an explanation on using the words and suggest a better response in English if needed. Provide the output in this format: [Your reply to the user] Feedback (English): [You will provide this] Explanation (English): [You will provide this] Feedback ({lang}): [You will provide this] Explanation ({lang}): [You will provide this] Better Response in English: [You will provide this]"},
                    {"role": "user", "content": text}
                ]
                chat_completion = openai_client.chat.completions.create(
                    model='gpt-3.5-turbo',
                    messages=message,
                    temperature=0.3
                )
                qa = chat_completion.choices[0].message.content
                generate_audio_reply(qa)
                await play_audio_in_channel(1247498910616780824, "C:/Users/Shricharan"
                                                             "/PycharmProjects"
                                                             "/AIDiscordBot_Test3/speech.mp3")
                # current_conversation_status += message
                # current_conversation_status += {"role": "assistant", "content": qa}
                db.convo.delete_one({"userid": user_id})
                return {'assistant': qa, 'empty': True}
        elif currentstatus == 1:
            # conversation already exists
            conversation += [{"role": "user", "content": text}]
            chat_completion = openai_client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=conversation
            )
            qa = chat_completion.choices[0].message.content
            chat_completion = openai_client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[
                    {"role": "system", "content": f"Here is a list of phrases: {wordlist}. Identify which phrases were NOT used by the user from this list. Output a python list of unused phrases. Return '[]' if all phrases were used."},
                    {"role": "user", "content": text}
                ],
                temperature=0.3
            )
            remaining_list = chat_completion.choices[0].message.content
            generate_audio_reply(qa)
            await play_audio_in_channel(1247498910616780824, "C:/Users/Shricharan"
                                                             "/PycharmProjects"
                                                             "/AIDiscordBot_Test3/speech.mp3")
            conversation += [{"role": "assistant", "content": qa}]
            db.convo.update_one({"userid": user_id}, {"$set": {"conversation": conversation}})
            db.convo.update_one({"userid": user_id}, {"$set": {"wordlist": remaining_list}})
            if remaining_list == [] or '[]':
                db.convo.delete_one({"userid": user_id})
                return {'assistant': qa, 'empty': False}
            return qa


async def play_audio_in_channel(channel_id, audio_file_path):
    channel = bot.get_channel(channel_id)
    if channel:
        voice_client = await channel.connect()
        source = discord.FFmpegPCMAudio(executable="C:/ffmpeg/bin/ffmpeg.exe", source=audio_file_path)
        voice_client.play(source)
        while voice_client.is_playing():
            await asyncio.sleep(0.1)
        await voice_client.disconnect()
    else:
        print(f"Voice channel with ID {channel_id} not found.")


def generate_audio_reply(text):
    with openai_client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="alloy",
            input=text,
    ) as response:
        response.stream_to_file("speech.mp3")


async def play_audio_in_voice_channel(author, file_path):
    voice_channel = author.voice.channel
    if voice_channel is not None:
        vc = await voice_channel.connect()
        vc.play(discord.FFmpegPCMAudio(executable="C:/ffmpeg/bin/ffmpeg.exe", source=file_path))
        while vc.is_playing():
            await asyncio.sleep(0.1)
        await vc.disconnect()
    else:
        print(f"{author.name} is not in a channel.")


@bot.command()
async def speak(ctx):
    channel = ctx.author.voice
    if channel is None:
        await ctx.send("ASSISTANT: You're not in a voice chat")
    else:
        voice = await channel.channel.connect()
        connections.update({ctx.guild.id: {"voice": voice, "recording": True}})
        file_name = f"{ctx.author.display_name}-{ctx.author.discriminator}.mp3"
        voice.start_recording(
            discord.sinks.MP3Sink(),
            lambda sink, member, file_name=file_name: once_done(sink, member, file_name),
            ctx.author,
            file_name
        )
        await ctx.send("ASSISTANT: Recording has started")


async def once_done(sink, member: discord.Member, name: str, *args):
    await sink.vc.disconnect()
    print(sink.audio_data.items())
    files = [discord.File(audio.file, f"{name}.{sink.encoding}") for user_id, audio in sink.audio_data.items()]
    channel = bot.get_channel(Config.log_channel)
    for user_id, audio in sink.audio_data.items():
        audio.file.seek(0)
        audio_bytes = BytesIO(audio.file.read())
        print(f"Audio data for {user_id}: size={len(audio_bytes.getvalue())} bytes")
        print(audio_bytes.getvalue()[:100])
        if len(audio_bytes.getvalue()) == 0:
            print(f"No audio data for user {user_id}. Skipping transcription.")
            continue
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
            temp_audio_file.write(audio_bytes.getvalue())
            temp_audio_file_path = temp_audio_file.name
        try:
            result = model.transcribe(temp_audio_file_path)
            print("Audio Transcribed")
            text = result['text']
            await channel.send("YOU: " + text)
            print("MEMBER ID is: ", member.id)
            result = await generate_conversation(member.id, text)
            if isinstance(result, dict):
                await channel.send("ASSISTANT: " + result['assistant'])
                if result['empty'] is True:
                    await channel.send("ASSISTANT: Well done in your Monotalk!")
                else:
                    await channel.send("ASSISTANT: You have used all the words and completed the game! Well done!")
            else:
                await channel.send("ASSISTANT: " + result)
        except Exception as e:
            print(f"Error transcribing audio for {user_id}: {e}")
        finally:
            os.remove(temp_audio_file_path)


@bot.command()
async def stop(ctx):
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]["voice"]
        print(vc)
        vc.stop_recording()
        del connections[ctx.guild.id]
        await ctx.send("ASSISTANT: The audio has been saved and logged")
    else:
        if ctx.guild.id in connections:
            vc = connections[ctx.guild.id]["voice"]
            print(vc)
            vc.stop_recording()
        await ctx.send("I'm not currently recording")


class InfoView(View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.user_data = {}
        self.interactions_completed = False

    async def on_timeout(self):
        if not self.interactions_completed:
            await self.ctx.send("You took too long to respond. Please start again.")
        self.stop()


async def ask_difficulty(ctx):
    view = InfoView(ctx)
    difficulty_levels = ["Easy", "Medium", "Hard"]
    for level in difficulty_levels:
        view.add_item(Button(label=level, style=discord.ButtonStyle.primary, custom_id=level))
    await ctx.send("Choose your difficulty level:", view=view)
    def check(interaction):
        return interaction.user.id == ctx.author.id and interaction.data['custom_id'] in difficulty_levels
    interaction = await bot.wait_for("interaction", check=check)
    selected = interaction.data['custom_id']
    view.clear_items()
    await interaction.message.edit(content=f"Choose your difficulty level: {selected}", view=view)
    view.user_data['difficulty'] = selected
    await interaction.response.defer()
    await ask_convotype(ctx, view)


async def ask_convotype(ctx, view):
    convotypes = ["Conversation", "Monotalk"]
    for convotype in convotypes:
        view.add_item(Button(label=convotype, style=discord.ButtonStyle.primary, custom_id=convotype))
    await ctx.send("Choose the type of conversation:", view=view)
    def check(interaction):
        return interaction.user.id == ctx.author.id and interaction.data['custom_id'] in convotypes
    interaction = await bot.wait_for("interaction", check=check)
    selected = interaction.data['custom_id']
    view.clear_items()
    await interaction.message.edit(content=f"Choose the type of conversation: {selected}", view=view)
    view.user_data['convotype'] = selected
    await interaction.response.defer()
    await ask_topic(ctx, view)


async def ask_topic(ctx, view):
    message = await ctx.send("Enter the topic:")
    def check(message):
        return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id
    bot.ignore_on_message = True
    response = await bot.wait_for("message", check=check)
    view.user_data['topic'] = response.content.strip()
    await response.delete()
    await message.edit(content=f"Enter the topic: {view.user_data['topic']}")
    bot.ignore_on_message = False
    await ask_style(ctx, view)


async def ask_style(ctx, view):
    styles = ["Formal", "Informal"]
    for style in styles:
        view.add_item(Button(label=style, style=discord.ButtonStyle.primary, custom_id=style))
    await ctx.send("Choose the style:", view=view)
    def check(interaction):
        return interaction.user.id == ctx.author.id and interaction.data['custom_id'] in styles
    interaction = await bot.wait_for("interaction", check=check)
    selected = interaction.data['custom_id']
    view.clear_items()
    await interaction.message.edit(content=f"Choose the style: {selected}", view=view)
    view.user_data['style'] = selected
    await interaction.response.defer()
    await ask_index(ctx, view)


async def ask_index(ctx, view):
    indices = list(range(1, len(word_list) + 1))
    for idx in indices:
        view.add_item(Button(label=str(idx), style=discord.ButtonStyle.primary, custom_id=str(idx)))
    await ctx.send("Choose the word list number:", view=view)
    def check(interaction):
        return interaction.user.id == ctx.author.id and interaction.data['custom_id'] in map(str, indices)
    interaction = await bot.wait_for("interaction", check=check)
    selected = interaction.data['custom_id']
    view.clear_items()
    await interaction.message.edit(content=f"Choose the word list number: {selected}", view=view)
    view.user_data['index'] = int(selected)
    await interaction.response.defer()
    await ask_language(ctx, view)


async def ask_language(ctx, view):
    message = await ctx.send("Enter your Native Language:")
    def check(message):
        return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id
    bot.ignore_on_message = True
    response = await bot.wait_for("message", check=check)
    view.user_data['language'] = response.content.strip()
    view.interactions_completed = True
    await response.delete()
    await message.edit(content=f"Enter your Native Language: {view.user_data['language']}")
    bot.ignore_on_message = False
    await create_record(ctx, view.user_data)


async def create_record(ctx, data):
    new_record = {
        "userid": int(ctx.author.id),
        "topic": data['topic'],
        "convotype": data['convotype'],
        "style": data['style'],
        "difficulty": data['difficulty'],
        "wordlist": [word_list[data['index'] - 1]],
        "nativelanguage": data['language'],
        "currentstatus": 0,
        "conversation": []
    }
    convo.insert_one(new_record)
    await ctx.send("Use the !speak command to start your conversation :)")


@bot.command()
async def info(ctx):
    print("1 CTX AUTHOR ID is: ", ctx.author.id)
    if db.convo.find_one({"user_id": ctx.author.id}) is None:
        await ask_difficulty(ctx)
    else:
        await ctx.send("Use the !speak command to continue your conversation :)")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return
    if hasattr(bot, 'ignore_on_message') and bot.ignore_on_message:
        return
    await message.channel.send(
        "These are the steps to use this bot:\n"
        "1. Join the Voice Channel\n"
        "2. Use the command !info to start a conversation or monotalk!\n"
    )
    await message.channel.send("These are your current word lists: ")
    for index in range(len(word_list)):
        await message.channel.send(f"List {index + 1}: {word_list[index]}\n")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


bot.run(TOKEN)
