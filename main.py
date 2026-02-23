import array
import logging
import os
import json
from typing import Optional, Dict, List, IO
import asyncio
import time
from dataclasses import dataclass
import atexit
import io

import discord
from discord import Client, Intents, Interaction, app_commands
from discord.utils import MISSING
from dotenv import load_dotenv
from gtts import gTTS

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Data Classes ---
@dataclass
class Affliction:
    name: str
    description: str
    details: Optional[Dict[str, str]] = None
    weight: int = 1
    danger: int = 1

    def embed(self) -> discord.Embed:
        """
        Creates a Discord embed for the affliction, including its name, description, and any additional details.
        :return:
        """
        embed = discord.Embed(title=self.name, description=f"-# Danger Level:{self.danger}\n\n{self.description}",
                              color=Affliction.get_color_for_danger_level(self.danger))
        if self.details:
            for key, value in self.details.items():
                embed.add_field(name=key.title(), value=value, inline=False)
        return embed

    @staticmethod
    def get_color_for_danger_level(danger_level: int) -> discord.Color:
        """
        Returns the color for the embed based on the danger level of the affliction.
        :param danger_level: The "danger" value of an affliction, which is an integer from 1 to 5. 1 being the least dangerous and 5 being the most dangerous.
        :return: a discord.Color object representing the color for the embed based on the danger level of the affliction.
        """
        if danger_level <= 2:
            return discord.Color.green()
        elif danger_level <= 4:
            return discord.Color.orange()
        else:
            return discord.Color.red()


# --- Managers / Client ---
class MemoryManager:
    def __init__(self):
        self.character_list: Dict[int, List[str]] = {}
        self.afflictions: List[Affliction] = []

        self.load_data()

    # --- Loading ---
    def load_data(self) -> None:
        logging.info("Loading data into memory...")
        self.load_afflictions()
        logging.info(f"Loaded {len(self.afflictions)} afflictions into memory.")
        # Placeholder for loading character lists and affliction history from a file or database

    def load_afflictions(self) -> None:
        affliction_path = "data/afflictions.json"
        if not os.path.exists(affliction_path):
            logging.warning(f"Affliction file not found at {affliction_path}. No afflictions loaded.")
            return

        with open(affliction_path, "r") as f:
            affliction_data = json.load(f)
            self.afflictions = [Affliction(**aff) for aff in affliction_data]

    # --- Saving ---
    def save_data(self) -> None:
        self.save_afflictions()
        # Placeholder for saving character lists and affliction history to a file or database

    def save_afflictions(self) -> None:
        # Placeholder for saving afflictions to a file or database
        if not os.path.exists("data"):
            os.makedirs("data")
        with open("data/afflictions.json", "w") as f:
            json.dump([aff.__dict__ for aff in self.afflictions], f, indent=2)

    def get_character_list(self, discord_id: int) -> List[str]:
        return self.character_list.get(discord_id, [])

    def add_character(self, discord_id: int, character_name: str) -> None:
        if discord_id not in self.character_list:
            self.character_list[discord_id] = []
        if character_name not in self.character_list[discord_id]:
            self.character_list[discord_id].append(character_name)

    def get_afflictions(self) -> List[Affliction]:
        # First we sort the afflictions by "danger" level, then by "weight", and finally alphabetically by name
        self.afflictions.sort(key=lambda aff: (aff.danger, aff.weight, aff.name))

        return self.afflictions


class BotClient(Client):
    listened_channel: Optional[discord.TextChannel] = None
    voice_client: Optional[discord.VoiceClient] = None

    def __init__(self):
        intents = Intents.default()
        intents.message_content = True

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        logging.info("Syncing command tree...")
        await self.tree.sync()

    async def on_ready(self):
        logging.info(f'Logged in as {self.user}')

        logging.info("Loading bot configs... ")
        client.load_data()

    def save_data(self):
        if not os.path.exists("data"):
            os.makedirs("data")

        with open("data/bot_configs.txt", "w") as f:
            f.write(f"listened_channel_id: {self.listened_channel.id if self.listened_channel else 'None'}\n")

    def load_data(self):
        if not os.path.exists("data/bot_configs.txt"):
            return
        with open("data/bot_configs.txt") as f:
            for line in f:
                if line.startswith("listened_channel_id:"):
                    channel_id_str = line.split(":")[1].strip()
                    if channel_id_str != "None":
                        channel_id = int(channel_id_str)
                        self.listened_channel = self.get_channel(channel_id)


# --- Initialization of Globals ---

client = BotClient()
memory = MemoryManager()
OCCULT_PARROT = 767047725333086209


# --- Helper Functions ---


# --- Autocomplete Functions ---
async def character_autocomplete(interaction: Interaction, current: str):
    filtered = [char for char in memory.get_character_list(interaction.user.id) if current.lower() in char.lower()]
    return [app_commands.Choice(name=char, value=char) for char in filtered[:25]]


# --- Event Handlers ---
@client.event
async def on_message(message: discord.Message):
    if message.channel.id != client.listened_channel.id or message.author.id == client.user.id:
        return
    if not client.voice_client:
        await message.channel.send(
            content="I am not currently in a voice channel. Use the `/join_vc` command to have me join your voice channel.",
            delete_after=10)
        return

    if len(message.content) > 200:
        await message.channel.send(
            content="Message is too long to send via TTS. Please keep messages under 200 characters.", delete_after=10)
        return
    logging.info("Received message: " + message.content)
    buffer = io.BytesIO()
    tts = gTTS(text=message.content, lang='en', tld="com.au")
    tts.write_to_fp(buffer)
    buffer.seek(0)

    client.voice_client.play(discord.FFmpegOpusAudio(buffer, pipe=True))

@client.event
async def on_voice_state_update(_member, before: discord.VoiceState, _after: discord.VoiceState):
    if not client.voice_client or not before.channel:
        return
    if before.channel.id != client.voice_client.channel.id:
        return

    if len([m for m in before.channel.members if not m.bot]) < 1:
        await client.voice_client.disconnect(force=True)
        client.voice_client = None
        logging.info("Left voice channel due to no non-bot users remaining.")
# --- Commands ---
@client.tree.command(name="roll_affliction", description="Roll an affliction for a character.")
@app_commands.describe(character_name="The name of the character to roll an affliction for. [OPTIONAL]")
@app_commands.autocomplete(character_name=character_autocomplete)
async def roll_affliction(interaction: Interaction, character_name: Optional[str] = None):
    if character_name and character_name not in memory.get_character_list(interaction.user.id):
        # New character - add to DB
        memory.add_character(interaction.user.id, character_name)

    await interaction.response.send_message(f"Rolling affliction for {character_name or 'a random character'}...")


@client.tree.command(name="list_afflictions", description="List all afflictions available.")
@app_commands.describe(page="The page number of afflictions to display. [OPTIONAL]")
async def list_afflictions(interaction: Interaction, page: Optional[int] = 1):
    NUMBER_OF_ITEMS_PER_PAGE = 5

    selected_page = page - 1 if page and page > 0 else 1

    if len(memory.get_afflictions()) < 1:
        await interaction.response.send_message("No afflictions found in memory.")
        return

    embeds = [aff.embed() for aff in memory.get_afflictions()]

    if not embeds:
        await interaction.response.send_message("No afflictions found for the specified page.")

    embeds[-1].set_footer(text=f"Page {selected_page + 1}")

    await interaction.response.send_message(embeds=embeds, ephemeral=True)


@client.tree.command(name="show_history", description="Show the history of afflictions rolled for a character.")
@app_commands.describe(character_name="The name of the character to show history for.")
@app_commands.autocomplete(character_name=character_autocomplete)
async def show_history(interaction: Interaction, character_name: str):
    pass


@client.tree.command(name="join_vc", description="Join the voice channel you are currently in.")
async def join_vc(interaction: Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You must be in a voice channel to use this command.", ephemeral=True)
        return

    channel = interaction.user.voice.channel

    if interaction.guild.voice_client is not None:
        client.voice_client = await interaction.guild.voice_client.move_to(channel)
    else:
        client.voice_client = await channel.connect()

    if not client.listened_channel:
        await interaction.response.send_message(
            "Joined voice channel! There is no selected text channel to listen to for TTS messages. Use the `/listen_here` command in a text channel to select it.",
            ephemeral=True)
        return

    await interaction.response.send_message(
        f"Joined voice channel! Now listening for TTS messages in {client.listened_channel.mention}.", ephemeral=True)


@client.tree.command(name="leave_vc", description="Leave the voice channel the bot is currently in.")
async def leave_vc(interaction: Interaction):
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("I am not currently in a voice channel.", ephemeral=True)
        return
    await interaction.guild.voice_client.disconnect(force=True)
    client.voice_client = None
    await interaction.response.send_message("Left voice channel.", ephemeral=True)


@client.tree.command(name="listen_here",
                     description="Tell the bot to listen for messages to be sent via TTS in the current voice channel.")
async def listen_here(interaction: Interaction):
    # if not interaction.permissions.administrator or interaction.user.id != OCCULT_PARROT:
    #     await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    #     return
    client.listened_channel = interaction.channel
    await interaction.response.send_message(
        f"Now listening for TTS messages in {interaction.channel.mention}.", ephemeral=True)


# --- Exit handler ---
def on_exit():
    logging.info("Shutting down bot and saving data...")
    memory.save_data()
    if client.voice_client and client.voice_client.is_connected():
        asyncio.run(client.voice_client.disconnect(force=True))
    client.save_data()


# --- Main Function ---
def main():
    atexit.register(on_exit)

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable is not set.")

    client.run(token)


if __name__ == "__main__":
    main()
