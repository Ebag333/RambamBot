from dataclasses import dataclass, field
from typing import Optional

import biblescrapeway
import discord.ext
import markdownify

import helpers.pycord_helpers

PycordEmbedCreator = helpers.pycord_helpers.DiscordEmbedCreator()
PycordPaginator = helpers.pycord_helpers.DiscordEmbedPaginator()


@dataclass
class BibleData:
    books = (
        "Genesis",
        "Exodus",
        "Leviticus",
        "Numbers",
        "Deuteronomy",
        "Joshua",
        "Judges",
        "Ruth",
        "1 Samuel",
        "2 Samuel",
        "1 Kings",
        "2 Kings",
        "1 Chronicles",
        "2 Chronicles",
        "Ezra",
        "Nehemiah",
        "Esther",
        "Job",
        "Psalm",
        "Proverbs",
        "Ecclesiastes",
        "Song of Songs",
        "Isaiah",
        "Jeremiah",
        "Lamentations",
        "Ezekiel",
        "Daniel",
        "Hosea",
        "Joel",
        "Amos",
        "Obadiah",
        "Jonah",
        "Micah",
        "Nahum",
        "Habakkuk",
        "Zephaniah",
        "Haggai",
        "Zechariah",
        "Malachi",
        "Matthew",
        "Mark",
        "Luke",
        "John",
        "Acts",
        "Romans",
        "1 Corinthians",
        "2 Corinthians",
        "Galatians",
        "Ephesians",
        "Philippians",
        "Colossians",
        "1 Thessalonians",
        "2 Thessalonians",
        "1 Timothy",
        "2 Timothy",
        "Titus",
        "Philemon",
        "Hebrews",
        "James",
        "1 Peter",
        "2 Peter",
        "1 John",
        "2 John",
        "3 John",
        "Jude",
        "Revelation",
        "Tobit",
        "Judith",
        "Greek Esther",
        "Wisdom of Solomon",
        "Sirach",
        "Baruch",
        "Letter of Jeremiah",
        "Prayer of Azariah",
        "Susanna",
        "Bel and the Dragon",
        "1 Maccabees",
        "2 Maccabees",
        "1 Esdras",
        "Prayer of Manasseh",
        "Psalm 151",
        "3 Maccabees",
        "2 Esdras",
        "4 Maccabees",
    )

    versions: dict[str, str] = field(default_factory=lambda: {
        "KJ21": "21st Century King James Version (KJ21)",
        "ASV": "American Standard Version (ASV)",
        "AMP": "Amplified Bible (AMP)",
        "AMPC": "Amplified Bible, Classic Edition (AMPC)",
        "BRG": "BRG Bible (BRG)",
        "CSB": "Christian Standard Bible (CSB)",
        "CEB": "Common English Bible (CEB)",
        "CJB": "Complete Jewish Bible (CJB)",
        "CEV": "Contemporary English Version (CEV)",
        "DARBY": "Darby Translation (DARBY)",
        "DLNT": "Disciples’ Literal New Testament (DLNT)",
        "DRA": "Douay-Rheims 1899 American Edition (DRA)",
        "ERV": "Easy-to-Read Version (ERV)",
        "EASY": "EasyEnglish Bible (EASY)",
        "EHV": "Evangelical Heritage Version (EHV)",
        "ESV": "English Standard Version (ESV)",
        "ESVUK": "English Standard Version Anglicised (ESVUK)",
        "EXB": "Expanded Bible (EXB)",
        "GNV": "1599 Geneva Bible (GNV)",
        "GW": "GOD’S WORD Translation (GW)",
        "GNT": "Good News Translation (GNT)",
        "HCSB": "Holman Christian Standard Bible (HCSB)",
        "ICB": "International Children’s Bible (ICB)",
        "ISV": "International Standard Version (ISV)",
        "PHILLIPS": "J.B. Phillips New Testament (PHILLIPS)",
        "JUB": "Jubilee Bible 2000 (JUB)",
        "KJV": "King James Version (KJV)",
        "AKJV": "Authorized (King James) Version (AKJV)",
        "LSB": "Legacy Standard Bible (LSB)",
        "LEB": "Lexham English Bible (LEB)",
        "TLB": "Living Bible (TLB)",
        "MSG": "The Message (MSG)",
        "MEV": "Modern English Version (MEV)",
        "MOUNCE": "Mounce Reverse Interlinear New Testament (MOUNCE)",
        "NOG": "Names of God Bible (NOG)",
        "NABRE": "New American Bible (Revised Edition) (NABRE)",
        "NASB": "New American Standard Bible (NASB)",
        "NASB1995": "New American Standard Bible 1995 (NASB1995)",
        "NCB": "New Catholic Bible (NCB)",
        "NCV": "New Century Version (NCV)",
        "NET": "New English Translation (NET)",
        "NIRV": "New International Reader's Version (NIRV)",
        "NIV": "New International Version (NIV)",
        "NIVUK": "New International Version - UK (NIVUK)",
        "NKJV": "New King James Version (NKJV)",
        "NLV": "New Life Version (NLV)",
        "NLT": "New Living Translation (NLT)",
        "NMB": "New Matthew Bible (NMB)",
        "NRSVA": "New Revised Standard Version, Anglicised (NRSVA)",
        "NRSVACE": "New Revised Standard Version, Anglicised Catholic Edition (NRSVACE)",
        "NRSVCE": "New Revised Standard Version Catholic Edition (NRSVCE)",
        "NRSVUE": "New Revised Standard Version Updated Edition (NRSVUE)",
        "NTFE": "New Testament for Everyone (NTFE)",
        "OJB": "Orthodox Jewish Bible (OJB)",
        "RGT": "Revised Geneva Translation (RGT)",
        "RSV": "Revised Standard Version (RSV)",
        "RSVCE": "Revised Standard Version Catholic Edition (RSVCE)",
        "TLV": "Tree of Life Version (TLV)",
        "VOICE": "The Voice (VOICE)",
        "WEB": "World English Bible (WEB)",
        "WE": "Worldwide English (New Testament) (WE)",
        "WYC": "Wycliffe Bible (WYC)",
        "YLT": "Young's Literal Translation (YLT)"
    })

    def get_books(self) -> list[str]:
        """
        Returns the list of books.
        """
        return list(self.books)

    def convert_version(self, version: str) -> Optional[str]:
        """
        Convert between short and long version of the Bible version name.
        :param version: The short or long version name to convert.
        :return: The corresponding long or short version name if found, else None.
        """
        # Check if it's a short version
        if version in self.versions:
            return self.versions[version]
        # Check if it's a long version
        for short, long in self.versions.items():
            if version.lower() == long.lower():
                return short
        return None


class BibleGateway:
    def __init__(self):
        pass

    @staticmethod
    def fetch_verse(*, verses: str, version: str = "NRSVUE") -> list[discord.ext.pages.Page]:
        verses_data = biblescrapeway.query(verses, version=version)

        embeds = []

        for verse_data in verses_data:
            line_embed_data = PycordEmbedCreator.EmbedData(
                description=markdownify.markdownify(verse_data.text),
                footer=PycordEmbedCreator.EmbedFooter(text=f"{verse_data.book} {verse_data.chapter}:{verse_data.verse} [{verse_data.version}]")
            )
            embeds.append(PycordEmbedCreator.create_embed(embed_data=line_embed_data))

        paged_embeds = PycordPaginator.create_paginated_embeds(embeds=embeds)

        return paged_embeds
