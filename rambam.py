import os

import discord
from discord.ext import bridge
from discord.ext.pages import Paginator

import helpers
import sources

SefariaAPI = sources.sefaria.SefariaAPI()
YouTubeSearch = sources.filmot.YouTubeTranscriptSearch()
BibleGateway = sources.biblegateway.BibleGateway()
KeywordReferenceSearch = helpers.keywordmessageparser.KeywordMessageParser()


def main() -> None:
    print("Starting bot")
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True  # Enable access to message content

    bot = bridge.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"{bot.user} is ready and online!")

    @bot.slash_command(name="bdb", description="Get a lexicon entry from Sefaria.")
    async def bdb(ctx: discord.ApplicationContext, hebrew: str, lookup_ref: str = None):
        definitions = SefariaAPI.get_sefaria_lexicon(word=hebrew, lookup_ref=lookup_ref)
        paginator = Paginator(pages=definitions)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.slash_command(name="yt", description="Search Dan McClellan's YouTube video transcripts")
    async def youtube_transcript_search(ctx: discord.ApplicationContext, search: str):
        # Defer the interaction to keep it open while processing
        await ctx.defer()

        results = YouTubeSearch.search_transcripts(query=search)
        embeds = YouTubeSearch.create_embeds(results=results)
        paginator = Paginator(pages=embeds)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.slash_command(name="sefaria", description="Fetch a referenced text from Sefaria")
    async def sefaria_text(ctx: discord.ApplicationContext, reference: str, version: str = None, language: str = None, fill_in_missing_segments: bool = True):
        # Defer the interaction to keep it open while processing
        await ctx.defer()

        embeds = SefariaAPI.get_sefaria_text(reference=reference, version=version, language=language, fill_in_missing_segments=fill_in_missing_segments)
        paginator = Paginator(pages=embeds)

        await paginator.respond(ctx.interaction)  # Use paginator to respond with the embeds

    @bot.slash_command(name="bible", description="Fetch a reference")
    async def bible(ctx: discord.ApplicationContext, reference: str, version: str = "NRSVUE"):
        # Defer the interaction to keep it open while processing
        await ctx.defer()

        embeds = BibleGateway.fetch_verse(verses=reference, version=version)
        paginator = Paginator(pages=embeds)

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
            print("Non-text message, skip!")
            return

        if message_dict.get("author", {}).get("bot", False):
            print("Bot message, skip!")
            # Message is coming from a bot, skip!
            return

        if message_dict.get("channel", {}).get("id") not in [1303123580514472067, 1303068218578960425]:
            print("Wrong channel, skip!")
            print(f"""Channel ID: {message_dict.get("channel", {}).get("id")}""")
            return

        print(message_dict)

        embeds = KeywordReferenceSearch.parse_message(message=message_dict.get("content"))
        if embeds:
            paginator = Paginator(pages=embeds)

            # await paginator.send(ctx.interaction, target=message.channel)  # Use paginator to respond with the embeds
            await paginator.send(ctx, target=message.channel)  # Use paginator to respond with the embeds

    bot.run(os.getenv('TOKEN'))  # run the bot with the token


if __name__ == '__main__':
    main()
