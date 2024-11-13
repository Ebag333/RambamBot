import concurrent.futures
import re
import urllib.parse

import discord.ext
import markdownify
import requests

import helpers.helpers
from helpers.pycord_helpers import DiscordEmbedCreator, DiscordEmbedPaginator

PycordEmbedCreator = DiscordEmbedCreator()
PycordPaginator = DiscordEmbedPaginator()
MatchingHelpers = helpers.helpers.MatchingHelpers()
BibleBooks = helpers.helpers.BibleBooks


class SefariaAPI:
    def __init__(self):
        print("Initializing Sefaria")
        self.sefaria_api_base_url = "https://www.sefaria.org/api"
        self.sefaria_texts = f"{self.sefaria_api_base_url}/v3/texts/"
        self.sefaria_manuscripts = f"{self.sefaria_api_base_url}/manuscripts/"
        self.sefaria_lexicon = f"{self.sefaria_api_base_url}/words/"
        self.sefaria_index = self.fetch_sefaria_index()
        self.sefaria_index_titles = [index.get("title") for index in self.sefaria_index if index.get("title")]
        self.sefaria_versions = self.fetch_sefaria_versions(titles=self.sefaria_index_titles)
        print("Sefaria initialized")

    def fetch_sefaria_index(self) -> list[dict]:
        """
        Fetch the Sefaria index data from the API.

        :return: A dictionary containing the Sefaria index data.
        """

        def recurse(entries):
            for entry in entries:
                if "contents" in entry:
                    recurse(entry["contents"])
                else:
                    flattened.append(entry)

        url = f"{self.sefaria_api_base_url}/index/"
        response = requests.get(url)
        if response.status_code == 200:
            index_data = response.json()
        else:
            index_data = None
            print(f"Failed to fetch index data from Sefaria API. Status code: {response.status_code}")

        flattened = []

        recurse(index_data)

        flattened = [d for d in flattened if "title" in d]

        return flattened

    def fetch_sefaria_versions(self, *, titles, max_threads=50):
        if isinstance(titles, str):
            titles = [titles]

        versions = []
        count = 0

        def fetch_version(title):
            nonlocal count
            count += 1
            # print(f"Fetching versions for {title} [{count}/{len(titles)}]")
            url = f"{self.sefaria_api_base_url}/texts/versions/{title}"
            response = requests.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to fetch version data for {title} from Sefaria API. Status code: {response.status_code}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_to_title = {executor.submit(fetch_version, title): title for title in titles}
            for future in concurrent.futures.as_completed(future_to_title):
                try:
                    versions.append(future.result())
                except Exception as exc:
                    title = future_to_title[future]
                    print(f"{title} generated an exception: {exc}")

        versions = [d for sublist in versions for d in sublist]
        versions = [d for d in versions if "title" in d and "versionTitle" in d and "languageFamilyName" in d]

        return versions

    def get_sefaria_text(self, *, reference: str, version: str = None, language: str = None, fill_in_missing_segments: bool = True) -> list[discord.ext.pages.Page]:
        parsed_reference = BibleBooks.extract_book_reference(user_input=reference)

        best_versions = MatchingHelpers.fuzzy_match_best_dicts(data_list=self.sefaria_versions, target_fields=["title", "versionTitle", "language"], target_values=[parsed_reference["book"], version, language])

        if best_versions:
            sefaria_version = f"""{best_versions[0].get("languageFamilyName")}|{best_versions[0].get("versionTitle")}"""
        else:
            sefaria_version = None

        params = {
            "return_format": "default",
            "version": sefaria_version or "primary",
            "fill_in_missing_segments": 1 if fill_in_missing_segments else 0,
        }

        url = f"""{self.sefaria_api_base_url}/v3/texts/{urllib.parse.quote(parsed_reference["reference"])}"""

        headers = {"accept": "application/json"}

        response = requests.get(url, headers=headers, params=params)
        response = response.json()

        versions = response.get("versions")

        if versions:
            text = versions[0].get("text", "Reference not found.")
        else:
            text = "Reference not found."

        header_embed_data = PycordEmbedCreator.EmbedData(
            title=reference,
            fields=[
                PycordEmbedCreator.EmbedField(name="Version", value=version, inline=True),
                PycordEmbedCreator.EmbedField(name="Language", value=language, inline=True),
                PycordEmbedCreator.EmbedField(name="Fill Missing Segments", value="True" if fill_in_missing_segments else "False", inline=True),
            ],
            footer=PycordEmbedCreator.EmbedFooter(
                text=f"""Results from Sefaria ({best_versions[0].get("versionTitle")})"""),
        )
        header_embed = PycordEmbedCreator.create_embed(embed_data=header_embed_data)

        embeds = []

        if isinstance(text, str):
            line_embed_data = PycordEmbedCreator.EmbedData(
                description=markdownify.markdownify(text),
            )
            embeds.append(PycordEmbedCreator.create_embed(embed_data=line_embed_data))
        else:
            for line in text:
                line_embed_data = PycordEmbedCreator.EmbedData(
                    description=markdownify.markdownify(line),
                )
                embeds.append(PycordEmbedCreator.create_embed(embed_data=line_embed_data))

        paged_embeds = PycordPaginator.create_paginated_embeds(embeds=embeds, header_embed=header_embed)

        return paged_embeds

    # Define a function to get Sefaria manuscripts data
    def get_sefaria_manuscripts(self, reference):
        url = f"{self.sefaria_manuscripts}{reference}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return f"Error: Unable to fetch manuscripts from Sefaria (status code {response.status_code})"

    def get_sefaria_lexicon(self, word: str, lookup_ref: str = None) -> [str, discord.Embed]:
        """
        Define a function to get Sefaria lexicon data and format it for Discord

        :param word: The word to search for in the lexicons (must be in Hebrew)
        :param lookup_ref: Optional reference to refine the search (e.g., a specific biblical verse)
        :return: Formatted lexicon data as a Discord Embed, or an error message if the request fails
        """
        encoded_word = urllib.parse.quote(word)
        url = f"{self.sefaria_lexicon}{encoded_word}"
        headers = {"accept": "application/json"}
        params = {}
        if lookup_ref:
            params["lookup_ref"] = lookup_ref
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if not data:
                data = f"No lexicon entries found for: {word}"

            header_embed_data = PycordEmbedCreator.EmbedData(
                title="Lexicon",
                fields=[
                    PycordEmbedCreator.EmbedField(name="word", value=word, inline=True),
                    PycordEmbedCreator.EmbedField(name="Lookup Reference", value=lookup_ref, inline=True),
                ],
                footer=PycordEmbedCreator.EmbedFooter(
                    text="Results from Sefaria"),
            )
            header_embed = PycordEmbedCreator.create_embed(embed_data=header_embed_data)

            embeds = []

            if isinstance(data, str):
                line_embed_data = PycordEmbedCreator.EmbedData(
                    description=markdownify.markdownify(data),
                )
                embeds.append(PycordEmbedCreator.create_embed(embed_data=line_embed_data))
            else:
                for entry in data:
                    entry_senses = self.flatten_definitions(definitions_dict=entry.get("content", {}).get("senses", []))

                    # Removing reference links
                    entry_senses = [re.sub(r"<a[^>]*>|</a>", "", sense) for sense in entry_senses]
                    # Convert to Markdown
                    entry_senses = [markdownify.markdownify(sense) for sense in entry_senses]

                    for sense in entry_senses:
                        line_embed_data = PycordEmbedCreator.EmbedData(
                            description=sense,
                            footer=PycordEmbedCreator.EmbedFooter(text=f"""Headword: {entry.get("headword", "Unknown")} | Lexicon: {entry.get("parent_lexicon", "Unknown")}""")
                        )
                        embeds.append(PycordEmbedCreator.create_embed(embed_data=line_embed_data))

            paged_embeds = PycordPaginator.create_paginated_embeds(embeds=embeds, header_embed=header_embed)

            return paged_embeds

        else:
            return f"Error: Unable to fetch lexicon data from Sefaria (status code {response.status_code})"

    @staticmethod
    def flatten_definitions(*, definitions_dict: list):
        definitions = []

        def extract_definitions(senses):
            for item in senses:
                if "definition" in item:
                    definitions.append(item["definition"])
                if "senses" in item:
                    extract_definitions(item["senses"])

        extract_definitions(definitions_dict)
        return definitions
