import concurrent.futures
import re
import urllib.parse
from typing import Optional, Any, Union

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

    def fetch_sefaria_versions(self, *, titles: [str, list[str]], max_threads: int = 50) -> list[dict[str, str]]:
        """
        Fetch version information for the specified titles from the Sefaria API.

        This function concurrently fetches versions for each title using a ThreadPoolExecutor.

        :param titles: A list of titles to fetch versions for. If a single title is passed as a string, it will be converted to a list.
        :param max_threads: The maximum number of threads to use for concurrent requests.
        :return: A list of dictionaries containing the version information for each title.
        """
        if isinstance(titles, str):
            titles = [titles]

        versions = []
        count = 0

        def fetch_version(*, title: str) -> list[dict[str, str]]:
            """
            Fetch version information for a single title from the Sefaria API.

            :param title: The title to fetch versions for.
            :return: A list of dictionaries containing the version information for the title.
            :raises Exception: If the request to the Sefaria API fails.
            """
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
            future_to_title = {executor.submit(fetch_version, title=title): title for title in titles}
            for future in concurrent.futures.as_completed(future_to_title):
                try:
                    versions.append(future.result())
                except Exception as exc:
                    title = future_to_title[future]
                    print(f"{title} generated an exception: {exc}")

        versions = [d for sublist in versions for d in sublist]
        versions = [d for d in versions if "title" in d and "versionTitle" in d and "languageFamilyName" in d]

        return versions

    def get_sefaria_related(self, *, reference: str) -> Optional[dict[str, Any]]:
        """
        Fetches related content from the Sefaria API based on a biblical reference.

        This method uses the `reference` parameter to determine the appropriate biblical reference,
        parses it using `BibleBooks.extract_book_reference`, and constructs a URL to query Sefaria's
        related content API. If the `reference` is valid, it sends an HTTP GET request and returns
        the JSON response. Otherwise, it returns `None`.

        :param reference: A string representing a biblical reference (e.g., "Genesis 1:1").
        :return: A dictionary containing the API's response if the reference is valid,
                 or `None` if the reference could not be parsed.
        """
        parsed_reference = BibleBooks.extract_book_reference(user_input=reference)
        response = None

        if parsed_reference:
            url = f"""{self.sefaria_api_base_url}/related/{urllib.parse.quote(parsed_reference.get("reference"))}"""
            headers = {"accept": "application/json"}

            response = requests.get(url, headers=headers)

            try:
                response = response.json()
            except requests.exceptions.JSONDecodeError:
                response = None

        return response

    def get_sefaria_codex(self, *, reference: str) -> list[Any]:
        """
        Fetches and formats codex information from the Sefaria API for display in embeds.

        This method retrieves related content from the Sefaria API using the provided `reference`
        and extracts manuscript (codex) data. Each codex is converted into an embed using the
        `PycordEmbedCreator`, and the embeds are paginated using `PycordPaginator`.

        :param reference: A string representing a biblical reference (e.g., "Exodus 20:1").
        :return: A list of paginated embed objects ready for display.
        """
        codexes = self.get_sefaria_related(reference=reference).get("manuscripts", [])

        embeds = []

        for codex in codexes:
            line_embed_data = PycordEmbedCreator.EmbedData(
                title=f"""{codex.get("manuscript", {}).get("title", "")}""",
                image=PycordEmbedCreator.EmbedImage(
                    url=codex.get("image_url")
                ),
                footer=PycordEmbedCreator.EmbedFooter(
                    text=f"""Results from Sefaria ({reference})"""),
            )
            embeds.append(PycordEmbedCreator.create_embed(embed_data=line_embed_data))

        paged_embeds = PycordPaginator.create_paginated_embeds(embeds=embeds)

        return paged_embeds

    def get_sefaria_links(self, *, reference: str) -> list[Any]:
        """
        Retrieves and formats links from the Sefaria API for display in embeds.

        This method fetches related links for the given biblical `reference` using the Sefaria API,
        then formats them as embeds suitable for display. A header embed is included as the first
        page of the paginated embeds, providing a link to the full reference on Sefaria.

        :param reference: A string representing a biblical reference (e.g., "Isaiah 7:14").
        :return: A list of paginated embed objects ready for display.
        """
        links = self.get_sefaria_related(reference=reference).get("links", [])
        parsed_reference = BibleBooks.extract_book_reference(user_input=reference)
        parsed_reference = urllib.parse.quote(parsed_reference.get("reference"))

        embeds = []

        header_embed_data = PycordEmbedCreator.EmbedData(
            title=reference,
            url=f"https://www.sefaria.org/{parsed_reference}?lang=bi&with=all&lang2=en",
            footer=PycordEmbedCreator.EmbedFooter(
                text="Results from Sefaria"),
        )
        header_embed = PycordEmbedCreator.create_embed(embed_data=header_embed_data)

        for link in links:
            # https://www.sefaria.org/Isaiah.7.14?lang=bi&with=all&lang2=en
            source_ref = urllib.parse.quote(link.get("sourceRef"))
            if source_ref:
                url = f"https://www.sefaria.org/{source_ref}?lang=bi&with=all&lang2=en"
            else:
                url = ""

            line_embed_data = PycordEmbedCreator.EmbedData(
                description=f"""{link.get("category")}: [{link.get("sourceRef")}]({url})""",
            )

            embeds.append(PycordEmbedCreator.create_embed(embed_data=line_embed_data))

        paged_embeds = PycordPaginator.create_paginated_embeds(embeds=embeds, header_embed=header_embed)

        return paged_embeds

    def get_sefaria_text(self, *, reference: str, version: Optional[str] = None, language: Optional[str] = None, fill_in_missing_segments: bool = True) -> list[discord.ext.pages.Page]:
        """
        Fetches and formats the text of a biblical reference from the Sefaria API.

        This method retrieves the specified text for a given `reference` from Sefaria, optionally filtered
        by `version` and `language`. It supports filling in missing segments if the `fill_in_missing_segments`
        parameter is enabled. The response is converted into a list of paginated embed pages for display.

        :param reference: A string representing a biblical reference (e.g., "Genesis 1:1").
        :param version: Optional; a specific text version to retrieve (e.g., "KJV").
        :param language: Optional; the language of the text to retrieve (e.g., "en").
        :param fill_in_missing_segments: A boolean indicating whether missing text segments should be filled. Defaults to True.
        :return: A list of `discord.ext.pages.Page` objects containing the formatted text.
        """
        parsed_reference = BibleBooks.extract_book_reference(user_input=reference)

        best_versions = MatchingHelpers.fuzzy_match_best_dicts(
            data_list=self.sefaria_versions,
            target_fields=["title", "versionTitle", "language"],
            target_values=[parsed_reference["book"], version, language]
        )

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
    def get_sefaria_manuscripts(self, reference: str) -> Union[dict[str, Any], str]:
        """
        Fetches manuscript data for a given reference from the Sefaria API.

        This method constructs a URL using the provided `reference` and queries the Sefaria API
        for manuscript data. If the API call is successful, it returns the parsed JSON response.
        Otherwise, it returns an error message with the HTTP status code.

        :param reference: A string representing the reference for which to fetch manuscript data (e.g., "Genesis 1:1").
        :return: A dictionary containing the manuscript data if the API call succeeds,
                 or an error message as a string if the call fails.
        """
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
    def flatten_definitions(*, definitions_dict: list[dict[str, Any]]) -> list[str]:
        """
        Flattens nested definitions from a dictionary of senses into a single list of definitions.

        This method recursively traverses a dictionary structure representing word senses to extract all
        definitions into a flat list. It handles nested senses by iterating through them recursively.

        :param definitions_dict: A list of dictionaries representing word senses, where each dictionary
                                 may contain a "definition" key and a nested "senses" key.
        :return: A list of strings containing all definitions found in the nested structure.
        """
        definitions = []

        def extract_definitions(senses: list[dict[str, Any]]) -> None:
            """
            Recursively extracts definitions from a list of word senses.

            This function iterates through each sense in the provided list, adding any found definitions
            to the outer `definitions` list. If a sense contains nested "senses", it calls itself
            recursively to continue extracting definitions.

            :param senses: A list of dictionaries representing word senses. Each dictionary may
                           include a "definition" key and a "senses" key for nested senses.
            """
            for item in senses:
                if "definition" in item:
                    definitions.append(item["definition"])
                if "senses" in item:
                    extract_definitions(item["senses"])

        extract_definitions(definitions_dict)
        return definitions
