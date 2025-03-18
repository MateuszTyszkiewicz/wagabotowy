import argparse
import logging
import tracemalloc
import asyncio
import concurrent.futures
from functools import partial
from datetime import datetime
import sys
import os

import constants
import custom_exceptions as e
import local_yt_summary as yts
import gemini_api_connection as gapi
import local_discussion_summary as cds

import keyring

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, heartbeat_timeout=60)
start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
executor = concurrent.futures.ThreadPoolExecutor()


def create_parser():
    """Creates a parser"""
    parser = argparse.ArgumentParser(description="A parser with an ez_mode flag")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Uses models on local computer",
    )
    parser.add_argument(
        "--ez_mode",
        action="store_true",
        help="Enable easy mode which runs smaller models to reduce needed computing resources",
    )
    return parser

def get_discord_bot_token():
    """
    Fetches the DISCORD_BOT_TOKEN depending on the runtime environment.
    - Uses keyring if running locally.
    - Reads from Podman secrets if running in Podman.
    """
    try:
        # Check if running inside a Podman container by looking for Podman secrets
        if os.path.exists("/run/secrets/"):
            # Read API key from Podman secrets
            with open("/run/secrets/DISCORD_BOT_TOKEN", "r") as secret_file:
                DISCORD_BOT_TOKEN = secret_file.read().strip()
            logging.info("DISCORD_BOT_TOKEN fetched from Podman secrets.")
        else:
            # Use keyring to fetch the API key locally
            DISCORD_BOT_TOKEN = keyring.get_password("DISCORD_BOT_TOKEN", "DISCORD_BOT_TOKEN")
            if not DISCORD_BOT_TOKEN:
                raise ValueError("DISCORD_BOT_TOKEN not found in keyring.")
            logging.info("DISCORD_BOT_TOKEN fetched from keyring.")
        
        return DISCORD_BOT_TOKEN

    except Exception as e:
        logging.error("Error fetching DISCORD BOT TOKEN: %s", e)
        return None


parser = create_parser()
args = parser.parse_args()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
file_handler = logging.FileHandler(f"logs/{start_time}.log", mode="w", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)


logging.basicConfig(
    level=logging.DEBUG,  # Set the log level to DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Define the format
    datefmt="%Y-%m-%d %H:%M:%S",  # Define the date format
    handlers=[file_handler, console_handler],
)


@bot.event
async def on_ready():
    """Informs that the bot is logged in."""
    logging.info("Logged in as %s", bot.user)


@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def hello(ctx):
    """Says Hello!"""
    await ctx.send("Hello!")


@bot.command(
    help="Tworzy podsumowanie dyskusji do X wiadomości wstecz (domyślnie 50, min 5, max 200)"
)
@commands.cooldown(3, 60, commands.BucketType.user)
async def tldr(ctx, messages_limit=50):
    """Creates the discussion summary and sends it as the message.

    Args:
        limit (int): Amount of messages taken for the summary.
    """
    tracemalloc.start()
    channel = ctx.channel
    message_about_number_of_messages, messages_limit = format_tldr_input_number_to_int(
        messages_limit, 300, 30
    )
    if messages_limit is None:
        await ctx.send(message_about_number_of_messages)
        return

    await ctx.send(message_about_number_of_messages)
    logging.info("Tworzę podsumowanie ostatnich %s wiadomości", messages_limit)
    messages = []
    async for message in channel.history(limit=messages_limit + 1):
        messages.append(message)

    content_list = [
        f"{message.author}: {message.content}"
        for message in reversed(messages)
        if not message.content.startswith("!") and not message.author == bot.user
    ]

    content = "\n".join(content_list)
    cleaned_content = cds.clean_discussion_string(content)
    logging.info(cleaned_content)

    if args.local:  # Used when we run models locally
        try:
            if args.ez_mode:
                model = constants.MODEL_DISCORD_SUMMARY_LOCAL["ez"]
            else:
                model = constants.MODEL_DISCORD_SUMMARY_LOCAL["normal"]
            loop = asyncio.get_running_loop()
            summary_generator = partial(cds.generate_summary, model, cleaned_content)
            logging.info("Starting generating the summary")
            message = await loop.run_in_executor(executor, summary_generator)
            logging.info("Successfully generated the summary")
        except Exception:
            logging.info("Failed to generate the summary")
            await ctx.send("Coś się popsuło i nie było mnie słychać!")

    else:  # Used when we use Gemini API
        try:
            logging.info("Starting generating the summary")
            loop = asyncio.get_running_loop()
            message = await loop.run_in_executor(
                executor, gapi.create_discussion_summary, cleaned_content
            )
            logging.info("Successfully generated the summary")
        except:
            logging.info("Failed to generate the summary")
            await ctx.send("Coś się popsuło i nie było mnie słychać!")

    logging.info("Message to send: %s", message)
    try:
        await ctx.send(message)
    except discord.errors.ConnectionClosed:
        await on_disconnect()
        await ctx.send(message)
    except Exception:
        logging.info(
            "Coś się zepsuło i nie było mnie słychać. Message length: %s", len(message)
        )
        await ctx.send("Coś się popsuło i nie było mnie słychać.")


@tldr.error
async def tldr_error(ctx, error):
    """Runs when someone uses the tldr command during the cooldown"""
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = round(error.retry_after, 2)
        await ctx.send(
            f"{ctx.author.mention} masz cooldowna. Spróbuj za {retry_after:.2f} sekund."
        )


@bot.command(
    help="Tworzy podsumowanie filmu z YT, używasz komendy w odpowiedzi na wiadomość z linkiem"
)
@commands.cooldown(3, 60, commands.BucketType.user)
async def tldw(ctx):
    """Creates the summary of the given YouTube video.
    To use, it use the command in the response to the message with YT link."""
    if ctx.message.reference:
        # Get the message being replied to
        ref_message = await ctx.fetch_message(ctx.message.reference.message_id)
        # Extract the link from the message
        link = ref_message.content
    else:
        await ctx.send("To nie link do filmu na YT.")
        return
    logging.info("Zaczynam podsumowanie!")
    await ctx.send("Zaczynam podsumowanie!")
    try:
        logging.info("Starting generting the tldw summary")

        if args.local:  # Used when we run models locally
            loop = asyncio.get_running_loop()
            summary_generator = partial(yts.generate_summary, link, args.ez_mode)
            message = await loop.run_in_executor(executor, summary_generator)

        else:
            loop = asyncio.get_running_loop()
            message = await loop.run_in_executor(
                executor, gapi.create_youtube_summary, link
            )

        logging.info("Successfully generated the summary")
        logging.info(message)
        try:
            await ctx.send(message)
        except discord.errors.ConnectionClosed:
            await on_disconnect()
            await ctx.send(message)
    except ValueError:
        await ctx.send("Nie wygląda to jak link do filmu na YT!")
    except e.MissingTranscriptError:
        await ctx.send("Przykro mi, brakuje transkryptu lub nie obsługuję tego języka.")
    except e.GeminiNotWorkingError:
        logging.warning("Gemini is not working")
        await ctx.send("Coś się zepsuło i nie było mnie słychać.")
    except Exception:
        logging.info("General exception. Message length: %s", len(message))
        await ctx.send("Coś się zepsuło i nie było mnie słychać.")


@tldw.error
async def tldw_error(ctx, error):
    """Runs when someone uses the tldw command during the cooldown"""
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = round(error.retry_after, 2)
        await ctx.send(
            f"{ctx.author.mention} masz cooldowna. Spróbuj za {retry_after:.2f} sekund."
        )


@bot.command(help="Wyjaśnia pojęcie, o które zapytasz w maksymalnie trzech słowach")
@commands.cooldown(3, 60, commands.BucketType.user)
async def coto(ctx, *, thing: str):
    """Describes the given string"""
    channel_name = ctx.channel.name  # Used to give bot some context
    logging.info("Channel name: %s", channel_name)
    logging.info("Value entered to coto: %s", thing)
    await ctx.send("Już tłumaczę!")
    if len(thing) == "":
        await ctx.send("Pojęcie do zdefiniowania nie zostało podane.")
        return
    if len(thing) > 100:
        await ctx.send("Chyba sobie żartujesz. Trzy. Słowa.")
        return
    try:
        logging.info("Starting generting coto")

        if args.local:
            await ctx.send(
                "Na razie tylko API Gemini obsługuje tę funkcję, a jestem uruchomiony lokalnie."
            )
            return

        else:
            loop = asyncio.get_running_loop()
            coto_generator = partial(gapi.describe_thing_pl, thing, channel_name)
            message = await loop.run_in_executor(executor, coto_generator)

        logging.info("Successfully generated coto")
        logging.info(message)
        try:
            await ctx.send(message)
        except discord.errors.ConnectionClosed:
            await on_disconnect()
            await ctx.send(message)
    except e.TooManyWordsError:
        await ctx.send("Za dużo słów. Maksymalna liczba to trzy.")
    except e.TryinToOmitWordsLimitError:
        await ctx.send("Niezła próba!")
    except e.GeminiNotWorkingError:
        await ctx.send("Z jakiegoś powodu nie działam poprawnie.")
    except Exception:
        await ctx.send("Coś się popsuło i nie było mnie słychać.")


@coto.error
async def coto_error(ctx, error):
    """Runs when someone uses the coto command during the cooldown"""
    if isinstance(error, commands.CommandOnCooldown):
        retry_after = round(error.retry_after, 2)
        await ctx.send(
            f"{ctx.author.mention} masz cooldowna. Spróbuj za {retry_after:.2f} sekund."
        )


@bot.event
async def on_disconnect():
    """Used when the bot disconnected from the server"""
    logging.warning("Disconnected from Discord. Attempting to reconnect...")
    await bot.wait_until_ready()


def format_tldr_input_number_to_int(
    messages_number=50, upper_limit=300, lower_limit=30
):
    """Formatting the input number (can be anything)"""
    try:
        messages_number = int(messages_number)
        message = f"Już się robi! Czas podsumować {messages_number} wiadomości."
    except:
        message = "Nie podałeś liczby!"
        return message, None
    if messages_number > upper_limit:
        messages_number = 300
        message = (
            "Jesteś zbyt zachłanny! Górny limit liczby wiadomości to 300."
            " Zbijam liczbę wiadomości do tej wartości."
        )
    if messages_number < lower_limit:
        messages_number = 30
        message = (
            "Chcesz podsumować zbyt mało wiadomości. "
            "Dolny limit to 30 i tyle mogę podsumować."
        )
    return message, messages_number


async def main():
    """Runs the bot"""
    if args.local:
        logging.info("Running models locally")
        if args.ez_mode:
            logging.info("Easy mode enabled!")
        else:
            logging.info("Easy mode disabled!")
    else:
        gapi.configure_genai()
        logging.info("Runing models using Gemini")
    async with bot:
        TOKEN = get_discord_bot_token()
        await bot.start(TOKEN)


if __name__ == "__main__":
    with asyncio.Runner() as runner:
        runner.run(main())
