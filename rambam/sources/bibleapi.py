import requests
import discord
from discord.ext import commands

class BibleAPI:
    def __init__(self, api_key: str):
        self.api_base_url = "https://api.scripture.api.bible"
        self.api_key = api_key
        # self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.headers = {"api-key": self.api_key}

    def get_bibles(self, language: str = None, abbreviation: str = None, name: str = None, ids: str = None, include_full_details: bool = False) -> [dict, str]:
        """
        Get a list of Bible objects authorized for the current API key.

        :param language: ISO 639-3 three digit language code to filter results.
        :param abbreviation: Bible abbreviation to search for.
        :param name: Bible name to search for.
        :param ids: Comma separated list of Bible IDs to return.
        :param include_full_details: Boolean to include full Bible details (e.g. copyright and promo info).
        :return: List of Bible objects or error message.
        """
        url = f"{self.api_base_url}/v1/bibles"
        params = {
            "language": language,
            "abbreviation": abbreviation,
            "name": name,
            "ids": ids,
            "include-full-details": str(include_full_details).lower()
        }
        response = requests.get(url, headers=self.headers, params=params)

        bibles = response.json().get("data", [])

        embeds = []
        for i in range(0, len(bibles), 10):
            page_bibles = bibles[i:i + 10]
            embed = discord.Embed(
                title="Available Bibles",
                description=f"Displaying Bibles {i + 1} to {min(i + 10, len(bibles))} of {len(bibles)}",
                color=discord.Color.blue()
            )
            for bible in page_bibles:
                embed.add_field(
                    name=f"{bible.get('name', 'Unknown Name')} ({bible.get('abbreviation', 'N/A')})",
                    value=f"Language: {bible.get('language', {}).get('name', 'Unknown')}\nType: {bible.get('type', 'N/A')}\n[More Info](https://api.scripture.api.bible/v1/bibles/{bible.get('id', '')})",
                    inline=False
                )
            embeds.append(embed)
        return embeds

# Example usage
if __name__ == "__main__":
    api_key = "your_api_key_here"
    bible_api = BibleAPI(api_key)
    bibles = bible_api.get_bibles()

    # Assuming you have a Discord bot set up with discord.py
    bot = commands.Bot(command_prefix="!")

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")

    @bot.command()
    async def list_bibles(ctx):
        embeds = bible_api.create_embeds(bibles)
        for embed in embeds:
            await ctx.send(embed=embed)

    bot.run("your_discord_bot_token_here")
