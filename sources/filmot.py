import json
import re
import urllib.parse

import discord.ext
import requests

import helpers.pycord_helpers

PycordEmbedCreator = helpers.pycord_helpers.DiscordEmbedCreator()
PycordPaginator = helpers.pycord_helpers.DiscordEmbedPaginator()


class YouTubeTranscriptSearch:
    def __init__(self):
        self.base_url = "https://filmot.com/search"
        self.channel_id = "UCAAJCQ0FCqRmAEv95SyTfNg"

    def search_transcripts(self, query: str) -> [dict, str]:
        """
        Search YouTube transcripts for a given query on a specific channel.

        :param query: The search string to look for in the transcripts.
        :return: A list of search results or an error message if the request fails.
        """
        encoded_query = urllib.parse.quote(query)

        page = 1
        all_results = []

        while True:
            url = f"{self.base_url}/{encoded_query}/1/{page}?gridView=1&channelID={self.channel_id}"
            headers = {"accept": "application/json"}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                html_content = response.text
                results = self.parse_results(html_content=html_content)
                print("Found results")

                if not results:
                    # No more results, stop paging
                    break

                all_results.extend(results)
                page += 1
            else:
                print(f"Error: Unable to fetch transcripts (status code {response.status_code})")
                break

        return all_results

    @staticmethod
    def parse_results(*, html_content: str) -> [dict, bool]:
        """
        Parse the HTML content to extract transcript results.

        :param html_content: The HTML content from the search response.
        :return: A list of parsed results.
        """
        # Extract JavaScript object from HTML content using regex
        match = re.search(r"window\.results\s*=\s*(\{.*?});", html_content, re.DOTALL)
        if not match:
            return False

        results_json_str = match.group(1)
        results_json_str = re.sub(r"\s+", " ", results_json_str)  # Remove extra whitespace

        try:
            results = json.loads(results_json_str)  # Convert to dictionary safely
        except json.JSONDecodeError:
            return False

        parsed_results = []
        for _, value in results.items():
            video_id = value.get("vid")
            hits = value.get("hits", [])
            for hit in hits:
                parsed_results.append({
                    "video_id": video_id,
                    "start": hit.get("start"),
                    "duration": hit.get("dur"),
                    "token": hit.get("token"),
                    "context_before": hit.get("ctx_before"),
                    "context_after": hit.get("ctx_after")
                })

        return parsed_results

    @staticmethod
    def create_embeds(*, results: list) -> list[discord.ext.pages.Page]:
        """
        Create a list of Discord embeds from the parsed results, grouping them by video ID.

        :param results: The parsed search results.
        :return: A list of discord.Embed objects.
        """

        embeds = []

        for result in results:
            video_embed_data = PycordEmbedCreator.EmbedData(
                title=f"""Starts at {result["start"]} seconds, duration {result["duration"]} seconds.""",
                description=f"""{result["context_before"]} `{result["token"]}` {result["context_after"]}""",
                video=PycordEmbedCreator.EmbedVideo(url=f"""https://www.youtube.com/watch?v={result["video_id"]}&t={int(result["start"])}s"""),
                # url=f"""https://www.youtube.com/watch?v={result["video_id"]}&t={int(result["start"])}s""",
                footer=PycordEmbedCreator.EmbedFooter(text=f"""Starts at {result["start"]} seconds, duration {result["duration"]} seconds"""),
            )

            embeds.append(PycordEmbedCreator.create_embed(embed_data=video_embed_data))

        # return embeds

        paged_embeds = PycordPaginator.create_paginated_embeds(embeds=embeds)

        return paged_embeds
