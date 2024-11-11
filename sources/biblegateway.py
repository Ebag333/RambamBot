from dataclasses import dataclass, field
from typing import Optional

import biblescrapeway
import discord.ext
import markdownify

import helpers.pycord_helpers
import helpers.helpers

PycordEmbedCreator = helpers.pycord_helpers.DiscordEmbedCreator()
PycordPaginator = helpers.pycord_helpers.DiscordEmbedPaginator()
BibleBooks = helpers.helpers.BibleBooks


class BibleGateway:
    def __init__(self):
        pass

    @staticmethod
    def fetch_verse(*, verses: str, version: str = "NRSVUE") -> list[discord.ext.pages.Page]:
        parsed_reference = BibleBooks.extract_book_reference(user_input=verses)
        verses_data = biblescrapeway.query(parsed_reference["reference"], version=version)

        embeds = []

        for verse_data in verses_data:
            line_embed_data = PycordEmbedCreator.EmbedData(
                description=markdownify.markdownify(verse_data.text),
                footer=PycordEmbedCreator.EmbedFooter(text=f"{verse_data.book} {verse_data.chapter}:{verse_data.verse} [{verse_data.version}]")
            )
            embeds.append(PycordEmbedCreator.create_embed(embed_data=line_embed_data))

        paged_embeds = PycordPaginator.create_paginated_embeds(embeds=embeds)

        return paged_embeds
