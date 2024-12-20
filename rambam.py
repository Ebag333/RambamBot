import logging
import os
import sys

import discord
from discord.ext import bridge
from discord.ext.pages import Paginator

import helpers.helpers
import helpers.keywordmessageparser
import sources

logging.basicConfig(level=logging.INFO)

logging.info("Starting bot")

SefariaAPI = sources.sefaria.SefariaAPI()
YouTubeSearch = sources.filmot.YouTubeTranscriptSearch()
BibleGateway = sources.biblegateway.BibleGateway()
KeywordReferenceSearch = helpers.keywordmessageparser.KeywordMessageParser(sefaria_index=SefariaAPI.sefaria_index)
BibleBooks = helpers.helpers.BibleBooks


def main() -> None:
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True  # Enable access to message content

    bot = bridge.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logging.info(f"{bot.user} is ready and online!")

    @bot.slash_command(name="bdb", description="Get a lexicon entry from Sefaria.")
    async def bdb(ctx: discord.ApplicationContext, hebrew: str, lookup_ref: str = None):
        all_embeds = SefariaAPI.get_sefaria_lexicon(word=hebrew, lookup_ref=lookup_ref)
        show_disabled = bool(len(all_embeds) > 1)
        paginator = Paginator(pages=all_embeds, show_disabled=show_disabled, show_indicator=show_disabled, author_check=False, timeout=600)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.slash_command(name="yt", description="Search Dan McClellan's YouTube video transcripts")
    async def youtube_transcript_search(ctx: discord.ApplicationContext, search: str):
        # Defer the interaction to keep it open while processing
        await ctx.defer()

        results = YouTubeSearch.search_transcripts(query=search)
        all_embeds = YouTubeSearch.create_embeds(results=results)
        show_disabled = bool(len(all_embeds) > 1)
        paginator = Paginator(pages=all_embeds, show_disabled=show_disabled, show_indicator=show_disabled, author_check=False, timeout=600)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.slash_command(name="sefaria", description="Fetch a referenced text from Sefaria")
    async def sefaria_text(ctx: discord.ApplicationContext, reference: str, version: str = None, language: str = None, fill_in_missing_segments: bool = True):
        # Defer the interaction to keep it open while processing
        await ctx.defer()

        all_embeds = SefariaAPI.get_sefaria_text(reference=reference, version=version, language=language, fill_in_missing_segments=fill_in_missing_segments)
        show_disabled = bool(len(all_embeds) > 1)
        paginator = Paginator(pages=all_embeds, show_disabled=show_disabled, show_indicator=show_disabled, author_check=False, timeout=600)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.slash_command(name="codex", description="Fetch an image of a codex from Sefaria")
    async def sefaria_codex(ctx: discord.ApplicationContext, reference: str):
        # Defer the interaction to keep it open while processing
        await ctx.defer()

        all_embeds = SefariaAPI.get_sefaria_codex(reference=reference)
        show_disabled = bool(len(all_embeds) > 1)
        paginator = Paginator(pages=all_embeds, show_disabled=show_disabled, show_indicator=show_disabled, author_check=False, timeout=600)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.slash_command(name="references", description="Fetch cross references and commentary from Sefaria")
    async def sefaria_references(ctx: discord.ApplicationContext, reference: str):
        # Defer the interaction to keep it open while processing
        await ctx.defer()

        all_embeds = SefariaAPI.get_sefaria_links(reference=reference)
        show_disabled = bool(len(all_embeds) > 1)
        paginator = Paginator(pages=all_embeds, show_disabled=show_disabled, show_indicator=show_disabled, author_check=False, timeout=600)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.slash_command(name="bible", description="Fetch a reference")
    async def bible(ctx: discord.ApplicationContext, reference: str, version: str = "NRSVUE"):
        # Defer the interaction to keep it open while processing
        await ctx.defer()

        all_embeds = BibleGateway.fetch_verse(verses=reference, version=version)
        show_disabled = bool(len(all_embeds) > 1)
        paginator = Paginator(pages=all_embeds, show_disabled=show_disabled, show_indicator=show_disabled, author_check=False, timeout=600)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.event
    async def on_command_error(ctx, error):
        message = ctx.message

        message_dict = {
            "id": message.id,
            "channel": {
                "id": message.channel.id,
                "name": getattr(message.channel, "name", None)
            },
            "type": str(message.type),
            "author": {
                "id": message.author.id,
                "username": message.author.name,
                "discriminator": message.author.discriminator,
                "bot": message.author.bot
            },
            "content": message.clean_content,
            "created_at": message.created_at.isoformat(),
            "edited_at": message.edited_at.isoformat() if message.edited_at else None,
            "embeds": [embed.to_dict() for embed in message.embeds],
            "attachments": [attachment.to_dict() for attachment in message.attachments],
            "reactions": [reaction.emoji for reaction in message.reactions],
            "mentions": [mention.id for mention in message.mentions],
            "pinned": message.pinned,
            "tts": message.tts,
            "jump_url": message.jump_url
        }

        if message.type != discord.MessageType.default:
            logging.info("Non-text message, skip!")
            return

        if message_dict.get("author", {}).get("bot", False):
            logging.info("Bot message, skip!")
            # Message is coming from a bot, skip!
            return

        if message_dict.get("channel", {}).get("id") not in [1303123580514472067, 1303068218578960425]:
            logging.info("Wrong channel, skip!")
            logging.info(f"Channel ID: {message_dict.get('channel', {}).get('id')}")
            return

        logging.info(message_dict)

        combined_matches = KeywordReferenceSearch.parse_message(message=message_dict.get("content"))
        if combined_matches:
            all_embeds = []

            for _, source, reference in combined_matches:
                if source == "biblegateway":
                    embeds = BibleGateway.fetch_verse(verses= BibleBooks.extract_book_reference(user_input=reference)["reference"])
                    all_embeds.extend(embeds)
                elif source == "sefaria":
                    embeds = SefariaAPI.get_sefaria_text(reference=BibleBooks.extract_book_reference(user_input=reference)["reference"], language="English")
                    all_embeds.extend(embeds)

            show_disabled = bool(len(all_embeds) > 1)
            paginator = Paginator(pages=all_embeds, show_disabled=show_disabled, show_indicator=show_disabled, author_check=False, timeout=600)

            # await paginator.send(ctx.interaction, target=message.channel)  # Use paginator to respond with the embeds
            await paginator.send(ctx, target=message.channel)  # Use paginator to respond with the embeds

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logging.error("DISCORD_TOKEN not found in environment variables")
        sys.exit()

    bot.run(token)  # run the bot with the token


if __name__ == "__main__":
    main()
