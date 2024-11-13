"""
This module provides utility classes for fuzzy matching and handling Bible book references.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

import fuzzywuzzy.fuzz


class MatchingHelpers:
    """
    A helper class for performing fuzzy matching operations on dictionaries.

    This class provides static methods to help find the best match among dictionaries
    based on specified fields and values using fuzzy matching.
    """

    @staticmethod
    def fuzzy_match_best_dicts(*, data_list: list[dict], target_fields: list[str], target_values: list[str], threshold: int = 80) -> list[dict]:
        """
        Fuzz match dictionaries based on multiple fields.

        :param data_list: List of dictionaries to search in.
        :param target_fields: List of target fields to search.
        :param target_values: List of target values to match.
        :param threshold: Minimum score threshold for matching.
        :return: list of dict: Matching dictionaries ordered by total fuzzy score.
        """

        matches = []
        for d in data_list:
            total_score = 0
            for field, value in zip(target_fields, target_values):
                if value is None:
                    continue
                field_value = d.get(field, "")
                score = fuzzywuzzy.fuzz.ratio(field_value, value)
                total_score += score
            # Only consider dictionaries with at least one score above threshold
            if total_score > 0 and any(fuzzywuzzy.fuzz.ratio(d.get(field, ""), value) >= threshold for field, value in
                                       zip(target_fields, target_values) if value is not None):
                matches.append((d, total_score))
        # Sort matches by score in descending order
        matches.sort(key=lambda x: x[1], reverse=True)
        # Return just the matching dictionaries, ordered by score
        return [match[0] for match in matches]


@dataclass
class BibleBooks:
    """
    A utility class for managing Bible book information and extracting references.

    This class provides methods to extract book titles, chapters, and verses from user input,
    resolve book names from abbreviations, and convert between versions of the Bible.
    """

    @classmethod
    def extract_book_reference(cls, user_input: str) -> dict[str, Optional[str]]:
        """
        Extract the book title, chapter, and verse from a user input string.

        :param user_input: The input string containing the book title and references.
        :return: A dictionary containing the extracted book title, chapter, verse, side, and validity status.
        """

        # Breakdown of the regex:
        # ^(\d*\s*[A-Za-z]+(?:\s[A-Za-z]+)*)  -> Matches the book title, which may include an optional number prefix and multiple words
        #   ^                                 -> Start of the string
        #   (\d*\s*[A-Za-z]+(?:\s[A-Za-z]+)*) -> Captures the book name, possibly with a leading number (e.g., "1 Samuel")
        #     \d*                            -> Matches zero or more digits (e.g., "1" in "1 Samuel")
        #     \s*                            -> Matches zero or more whitespace characters
        #     [A-Za-z]+                      -> Matches one or more alphabetic characters (e.g., the book name itself)
        #     (?:\s[A-Za-z]+)*               -> Non-capturing group to match additional words in the book name (e.g., "Song of Solomon")
        # (?:\s+(\d+)([ab])?(?:[:.](\d+(?:-\d+)?))?)? -> Matches the chapter, side, and verse information (optional)
        #   \s+                              -> Matches one or more whitespace characters
        #   (\d+)                            -> Captures the chapter number
        #   ([ab])?                          -> Optionally captures the side (a or b)
        #   (?:[:.](\d+(?:-\d+)?))?          -> Optionally matches the verse or verse range, preceded by ":" or "."
        #     [:.]                          -> Matches either ":" or "."
        #     (\d+(?:-\d+)?)                -> Captures the verse number or range (e.g., "5" or "5-10")
        match = re.match(r"^(\d*\s*[A-Za-z]+(?:\s[A-Za-z]+)*)(?:\s+(\d+)([ab])?(?:[:.](\d+(?:-\d+)?))?)?", user_input)
        book = None
        chapter = None
        verse = None
        side = None
        valid = False
        large_reference = False

        if match:
            book = cls.get_book_name(reference=match.group(1).strip())
            chapter = match.group(2)
            side = match.group(3)
            verse = match.group(4)

            # Determine if the reference is valid
            if book and chapter:
                valid = True

            # Determine if the reference is a large reference (e.g., whole chapter or book or large verse range)
            if not verse:
                large_reference = True
            elif "-" in verse:
                start_verse, end_verse = map(int, verse.split("-"))
                if end_verse - start_verse > 10:
                    large_reference = True

        # Format reference string
        reference = f"{book}"
        if chapter:
            reference += f" {chapter}"
        if side:
            reference += f"{side}"
        if verse:
            reference += f":{verse}"

        return {
            "book": book,
            "chapter": chapter,
            "verse": verse,
            "side": side,
            "reference": reference,
            "valid": valid,
            "large_reference": large_reference
        }

    @classmethod
    def get_book_name(cls, reference: str) -> str:
        """
        Resolve the book name from the given reference.

        :param reference: The reference string containing the book name or abbreviation.
        :return: The full book name if found, otherwise the original reference.
        """
        for book in cls.bible_books:
            if reference.lower() in [abbr.lower() for abbr in book.get("abbreviations", [])]:
                return book.get("book", reference).strip()
        return reference

    @classmethod
    def get_books(cls) -> list[str]:
        """
        Get a list of all the books in the Bible.

        :return: A list of book names in the Bible.
        """
        return list(cls.bible_books_list)

    @classmethod
    def convert_version(cls, *, version: str) -> Optional[str]:
        """
        Convert between short and long version of the Bible version name.

        :param version: The short or long version name to convert.
        :return: The corresponding long or short version name if found, else None.
        """
        # Check if it's a short version
        if version in cls.versions:
            return cls.versions[version]
        # Check if it's a long version
        for short, long in cls.versions.items():
            if version.lower() == long.lower():
                return short
        return None

    bible_books = [
        {
            "book": "Genesis",
            "abbreviations": ["Gen", "Ge", "Gn"]
        },
        {
            "book": "Exodus",
            "abbreviations": ["Exod", "Ex", "Exo"]
        },
        {
            "book": "Leviticus",
            "abbreviations": ["Lev", "Lv", "Le"]
        },
        {
            "book": "Numbers",
            "abbreviations": ["Num", "Nu", "Nm", "Nb"]
        },
        {
            "book": "Deuteronomy",
            "abbreviations": ["Deut", "Dt", "De"]
        },
        {
            "book": "Joshua",
            "abbreviations": ["Josh", "Jos", "Jsh"]
        },
        {
            "book": "Judges",
            "abbreviations": ["Judg", "Jdg", "Jdgs", "Jg"]
        },
        {
            "book": "Ruth",
            "abbreviations": ["Ruth", "Ru", "Rth"]
        },
        {
            "book": "1 Samuel",
            "abbreviations": ["1 Sam", "1 Sm", "1 Sa", "I Sam", "I Sa", "I Sm", "First Samuel", "First Sam"]
        },
        {
            "book": "2 Samuel",
            "abbreviations": ["2 Sam", "2 Sm", "2 Sa", "II Sam", "II Sa", "II Sm", "Second Samuel", "Second Sam"]
        },
        {
            "book": "1 Kings",
            "abbreviations": ["1 Kings", "1 Kgs", "1 Ki", "1Kgs", "1Kin", "1Ki", "1K", "I Kgs", "I Ki", "1st Kings",
                              "1st Kgs", "First Kings", "First Kgs"]
        },
        {
            "book": "2 Kings",
            "abbreviations": ["2 Kings", "2 Kgs", "2 Ki", "2Kgs", "2Kin", "2Ki", "2K", "II Kgs", "II Ki", "2nd Kings",
                              "2nd Kgs", "Second Kings", "Second Kgs"]
        },
        {
            "book": "1 Chronicles",
            "abbreviations": ["1 Chron", "1 Chr", "1 Ch", "1Chron", "1Chr", "1Ch", "I Chron", "I Chr", "I Ch",
                              "1st Chronicles", "1st Chron", "First Chronicles", "First Chron"]
        },
        {
            "book": "2 Chronicles",
            "abbreviations": ["2 Chron", "2 Chr", "2 Ch", "2Chron", "2Chr", "2Ch", "II Chron", "II Chr", "II Ch",
                              "2nd Chronicles", "2nd Chron", "Second Chronicles", "Second Chron"]
        },
        {
            "book": "Ezra",
            "abbreviations": ["Ez", "Ezr"]
        },
        {
            "book": "Nehemiah",
            "abbreviations": ["Neh", "Ne"]
        },
        {
            "book": "Esther",
            "abbreviations": ["Esth", "Est", "Es"]
        },
        {
            "book": "Job",
            "abbreviations": ["Jb"]
        },
        {
            "book": "Psalms",
            "abbreviations": ["Ps", "Psa", "Psm", "Pss", "Psalm", "Pslm"]
        },
        {
            "book": "Proverbs",
            "abbreviations": ["Prov", "Prv", "Pr", "Pro"]
        },
        {
            "book": "Ecclesiastes",
            "abbreviations": ["Eccles", "Eccle", "Eccl", "Ecc", "Qoheleth", "Qoh"]
        },
        {
            "book": "Song of Songs",
            "abbreviations": ["Song", "SoS", "Song of Solomon", "So", "Canticles", "Canticle of Canticles", "Cant"]
        },
        {
            "book": "Isaiah",
            "abbreviations": ["Isa", "Is"]
        },
        {
            "book": "Jeremiah",
            "abbreviations": ["Jer", "Je", "Jr"]
        },
        {
            "book": "Lamentations",
            "abbreviations": ["Lam", "La", "Lament"]
        },
        {
            "book": "Ezekiel",
            "abbreviations": ["Ezek", "Eze", "Ezk"]
        },
        {
            "book": "Daniel",
            "abbreviations": ["Dan", "Dn", "Da"]
        },
        {
            "book": "Hosea",
            "abbreviations": ["Hos", "Ho"]
        },
        {
            "book": "Joel",
            "abbreviations": ["Jl"]
        },
        {
            "book": "Amos",
            "abbreviations": ["Am"]
        },
        {
            "book": "Obadiah",
            "abbreviations": ["Obad", "Ob"]
        },
        {
            "book": "Jonah",
            "abbreviations": ["Jon", "Jnh"]
        },
        {
            "book": "Micah",
            "abbreviations": ["Mic", "Mc"]
        },
        {
            "book": "Nahum",
            "abbreviations": ["Nah", "Na"]
        },
        {
            "book": "Habakkuk",
            "abbreviations": ["Hab", "Hb"]
        },
        {
            "book": "Zephaniah",
            "abbreviations": ["Zeph", "Zep", "Zp"]
        },
        {
            "book": "Haggai",
            "abbreviations": ["Hag", "Hg"]
        },
        {
            "book": "Zechariah",
            "abbreviations": ["Zech", "Zec", "Zc"]
        },
        {
            "book": "Malachi",
            "abbreviations": ["Mal", "Ml"]
        },
        {
            "book": "Matthew",
            "abbreviations": ["Matt", "Mt"]
        },
        {
            "book": "Mark",
            "abbreviations": ["Mar", "Mk", "Mrk", "Mr"]
        },
        {
            "book": "Luke",
            "abbreviations": ["Lk", "L"]
        },
        {
            "book": "John",
            "abbreviations": ["Jn", "Jhn", "Joh"]
        },
        {
            "book": "Acts",
            "abbreviations": ["Ac", "Act"]
        },
        {
            "book": "Romans",
            "abbreviations": ["Rom", "Ro", "Rm"]
        },
        {
            "book": "1 Corinthians",
            "abbreviations": ["1 Cor", "1 Co", "I Cor", "I Co", "1Cor", "1Co", "I Corinthians", "1Corinthians",
                              "1st Corinthians", "First Corinthians"]
        },
        {
            "book": "2 Corinthians",
            "abbreviations": ["2 Cor", "2 Co", "II Cor", "II Co", "2Cor", "2Co", "II Corinthians", "2Corinthians",
                              "2nd Corinthians", "Second Corinthians"]
        },
        {
            "book": "Galatians",
            "abbreviations": ["Gal", "Ga"]
        },
        {
            "book": "Ephesians",
            "abbreviations": ["Eph", "Ep", "Ephes"]
        },
        {
            "book": "Philippians",
            "abbreviations": ["Phil", "Php", "Phl", "Pp"]
        },
        {
            "book": "Colossians",
            "abbreviations": ["Col", "Cl"]
        },
        {
            "book": "Colossians",
            "abbreviations": ["Col", "Cl"]
        },
        {
            "book": "1 Thessalonians",
            "abbreviations": ["1 Thess", "1 Thes", "1 Th", "I Thessalonians", "I Thess", "I Thes", "I Th",
                              "1Thessalonians", "1Thess", "1Thes", "1Th", "1st Thessalonians", "1st Thess",
                              "First Thessalonians", "First Thess"]
        },
        {
            "book": "2 Thessalonians",
            "abbreviations": ["2 Thess", "2 Thes", "2 Th", "II Thessalonians", "II Thess", "II Thes", "II Th",
                              "2Thessalonians", "2Thess", "2Thes", "2Th", "2nd Thessalonians", "2nd Thess",
                              "Second Thessalonians", "Second Thess"]
        },
        {
            "book": "1 Timothy",
            "abbreviations": ["1 Tim", "1 Ti", "I Timothy", "I Tim", "I Ti", "1Timothy", "1Tim", "1Ti", "1st Timothy",
                              "1st Tim", "First Timothy", "First Tim"]
        },
        {
            "book": "2 Timothy",
            "abbreviations": ["2 Tim", "2 Ti", "II Timothy", "II Tim", "II Ti", "2Timothy", "2Tim", "2Ti",
                              "2nd Timothy", "2nd Tim", "Second Timothy", "Second Tim"]
        },
        {
            "book": "Titus",
            "abbreviations": ["Titus", "Tit", "ti"]
        },
        {
            "book": "Philemon",
            "abbreviations": ["Philem", "Phm", "Pm"]
        },
        {
            "book": "Hebrews",
            "abbreviations": ["Heb"]
        },
        {
            "book": "James",
            "abbreviations": ["James", "Jas", "Jm"]
        },
        {
            "book": "1 Peter",
            "abbreviations": ["1 Pet", "1 Pe", "1 Pt", "1 P", "I Pet", "I Pt", "I Pe", "1Peter", "1Pet", "1Pe", "1Pt",
                              "1P", "I Peter", "1st Peter", "First Peter"]
        },
        {
            "book": "2 Peter",
            "abbreviations": ["2 Pet", "2 Pe", "2 Pt", "2 P", "II Peter", "II Pet", "II Pt", "II Pe", "2Peter", "2Pet",
                              "2Pe", "2Pt", "2P", "2nd Peter", "Second Peter"]
        },
        {
            "book": "1 John",
            "abbreviations": ["1 John", "1 Jhn", "1 Jn", "1 J", "1John", "1Jhn", "1Joh", "1Jn", "1Jo", "1J", "I John",
                              "I Jhn", "I Joh", "I Jn", "I Jo", "1st John", "First John"]
        },
        {
            "book": "2 John",
            "abbreviations": ["2 John", "2 Jhn", "2 Jn", "2 J", "2John", "2Jhn", "2Joh", "2Jn", "2Jo", "2J", "II John",
                              "II Jhn", "II Joh", "II Jn", "II Jo", "2nd John", "Second John"]
        },
        {
            "book": "3 John",
            "abbreviations": ["3 John", "3 Jhn", "3 Jn", "3 J", "3John", "3Jhn", "3Joh", "3Jn", "3Jo", "3J", "III John",
                              "III Jhn", "III Joh", "III Jn", "III Jo", "3rd John", "Third John"]
        },
        {
            "book": "Jude",
            "abbreviations": ["Jude", "Jud", "Jd"]
        },
        {
            "book": "Revelation",
            "abbreviations": ["Rev", "Re", "The Revelation"]
        },
        {
            "book": "Tobit",
            "abbreviations": ["Tob", "Tb"]
        },
        {
            "book": "Judith",
            "abbreviations": ["Jth", "Jdth", "Jdt"]
        },
        {
            "book": "Additions to Esther",
            "abbreviations": ["Add Esth", "Add Es", "Rest of Esther", "The Rest of Esther", "AEs", "AddEsth"]
        },
        {
            "book": "Wisdom of Solomon",
            "abbreviations": ["Wisd of Sol", "Wisdom", "Wis", "Ws"]
        },
        {
            "book": "Sirach",
            "abbreviations": ["Sir", "Ecclesiasticus"]
        },
        {
            "book": "Ecclesiasticus",
            "abbreviations": ["Ecclus"]
        },
        {
            "book": "Baruch",
            "abbreviations": ["Bar"]
        },
        {
            "book": "Letter of Jeremiah",
            "abbreviations": ["Ep Jer", "Let Jer", "Ltr Jer", "LJe"]
        },
        {
            "book": "Song of Three Youths",
            "abbreviations": [
                "Sg of 3 Childr", "Song of Three", "Song of Thr", "Song Thr", "The Song of Three Youths",
                "The Song of the Three Holy Children", "Song of the Three Holy Children", "Song of Three Children",
                "The Song of Three Jews", "Song of Three Jews", "Prayer of Azariah", "Azariah", "Pr Az"
            ]
        },
        {
            "book": "Susanna",
            "abbreviations": ["Sus"]
        },
        {
            "book": "Bel and the Dragon",
            "abbreviations": ["Bel"]
        },
        {
            "book": "1 Maccabees",
            "abbreviations": [
                "1 Macc", "1 Mac", "1Maccabees", "1Macc", "1Mac", "1Ma", "1M", "I Maccabees", "I Macc", "I Mac",
                "I Ma", "1st Maccabees", "First Maccabees"
            ]
        },
        {
            "book": "2 Maccabees",
            "abbreviations": [
                "2 Macc", "2 Mac", "2Maccabees", "2Macc", "2Mac", "2Ma", "2M", "II Maccabees", "II Macc", "II Mac",
                "II Ma", "2nd Maccabees", "Second Maccabees"
            ]
        },
        {
            "book": "3 Maccabees",
            "abbreviations": [
                "3 Macc", "3 Mac", "3Maccabees", "3Macc", "3Mac", "3Ma", "3M", "III Maccabees", "III Macc", "III Mac",
                "III Ma", "3rd Maccabees", "Third Maccabees"
            ]
        },
        {
            "book": "4 Maccabees",
            "abbreviations": [
                "4 Macc", "4 Mac", "4Maccabees", "4Macc", "4Mac", "4Ma", "4M", "IV Maccabees", "IV Macc", "IV Mac",
                "IV Ma", "4th Maccabees", "Fourth Maccabees"
            ]
        },
        {
            "book": "1 Esdras",
            "abbreviations": [
                "1 Esd", "1 Esdr", "1Esdras", "1Esdr", "1Esd", "1Es", "I Esdras", "I Esdr", "I Esd", "I Es",
                "1st Esdras", "First Esdras"
            ]
        },
        {
            "book": "2 Esdras",
            "abbreviations": [
                "2 Esd", "2 Esdr", "2Esdras", "2Esdr", "2Esd", "2Es", "II Esdras", "II Esdr", "II Esd", "II Es",
                "2nd Esdras", "Second Esdras"
            ]
        },
        {
            "book": "Prayer of Manasseh",
            "abbreviations": [
                "Pr of Man", "Pr of Man", "PMa", "Prayer of Manasses"
            ]
        },
        {
            "book": "Additional Psalm",
            "abbreviations": [
                "Add Psalm", "Add Ps"
            ]
        },
        {
            "book": "Ode",
            "abbreviations": ["Ode"]
        },
        {
            "book": "Psalms of Solomon",
            "abbreviations": ["Ps Solomon", "Ps Sol", "Psalms Solomon", "PsSol"]
        },
        {
            "book": "Epistle to the Laodiceans",
            "abbreviations": [
                "Ep Lao", "Epistle to Laodiceans", "Epistle Laodiceans", "Epist Laodiceans", "Ep Laod", "Laodiceans",
                "Laod"
            ]
        },
        {
            "book": "Revelation",
            "abbreviations": ["Rev", "Re", "The Revelation"]
        },
        {
            "book": "Tobit",
            "abbreviations": ["Tob", "Tb"]
        },
        {
            "book": "Judith",
            "abbreviations": ["Jth", "Jdth", "Jdt"]
        },
        {
            "book": "Additions to Esther",
            "abbreviations": ["Add Esth", "Add Es", "Rest of Esther", "The Rest of Esther", "AEs", "AddEsth"]
        },
        {
            "book": "Wisdom of Solomon",
            "abbreviations": ["Wisd of Sol", "Wisdom", "Wis", "Ws"]
        },
        {
            "book": "Sirach",
            "abbreviations": ["Sir", "Ecclesiasticus"]
        },
        {
            "book": "Ecclesiasticus",
            "abbreviations": ["Ecclus"]
        },
        {
            "book": "Baruch",
            "abbreviations": ["Bar"]
        },
        {
            "book": "Letter of Jeremiah",
            "abbreviations": ["Ep Jer", "Let Jer", "Ltr Jer", "LJe"]
        },
        {
            "book": "Song of Three Youths",
            "abbreviations": [
                "Sg of 3 Childr", "Song of Three", "Song of Thr", "Song Thr", "The Song of Three Youths", 
                "The Song of the Three Holy Children", "Song of the Three Holy Children", "Song of Three Children", 
                "The Song of Three Jews", "Song of Three Jews", "Prayer of Azariah", "Azariah", "Pr Az"
            ]
        },
        {
            "book": "Susanna",
            "abbreviations": ["Sus"]
        },
        {
            "book": "Bel and the Dragon",
            "abbreviations": ["Bel"]
        },
        {
            "book": "1 Maccabees",
            "abbreviations": [
                "1 Macc", "1 Mac", "1Maccabees", "1Macc", "1Mac", "1Ma", "1M", "I Maccabees", "I Macc", "I Mac", 
                "I Ma", "1st Maccabees", "First Maccabees"
            ]
        },
        {
            "book": "2 Maccabees",
            "abbreviations": [
                "2 Macc", "2 Mac", "2Maccabees", "2Macc", "2Mac", "2Ma", "2M", "II Maccabees", "II Macc", "II Mac", 
                "II Ma", "2nd Maccabees", "Second Maccabees"
            ]
        },
        {
            "book": "3 Maccabees",
            "abbreviations": [
                "3 Macc", "3 Mac", "3Maccabees", "3Macc", "3Mac", "3Ma", "3M", "III Maccabees", "III Macc", "III Mac", 
                "III Ma", "3rd Maccabees", "Third Maccabees"
            ]
        },
        {
            "book": "4 Maccabees",
            "abbreviations": [
                "4 Macc", "4 Mac", "4Maccabees", "4Macc", "4Mac", "4Ma", "4M", "IV Maccabees", "IV Macc", "IV Mac", 
                "IV Ma", "4th Maccabees", "Fourth Maccabees"
            ]
        },
        {
            "book": "1 Esdras",
            "abbreviations": [
                "1 Esd", "1 Esdr", "1Esdras", "1Esdr", "1Esd", "1Es", "I Esdras", "I Esdr", "I Esd", "I Es", 
                "1st Esdras", "First Esdras"
            ]
        },
        {
            "book": "2 Esdras",
            "abbreviations": [
                "2 Esd", "2 Esdr", "2Esdras", "2Esdr", "2Esd", "2Es", "II Esdras", "II Esdr", "II Esd", "II Es", 
                "2nd Esdras", "Second Esdras"
            ]
        },
        {
            "book": "Prayer of Manasseh",
            "abbreviations": [
                "Pr of Man", "Pr of Man", "PMa", "Prayer of Manasses"
            ]
        },
        {
            "book": "Additional Psalm",
            "abbreviations": [
                "Add Psalm", "Add Ps"
            ]
        },
        {
            "book": "Ode",
            "abbreviations": ["Ode"]
        },
        {
            "book": "Psalms of Solomon",
            "abbreviations": ["Ps Solomon", "Ps Sol", "Psalms Solomon", "PsSol"]
        },
        {
            "book": "Epistle to the Laodiceans",
            "abbreviations": [
                "Ep Lao", "Epistle to Laodiceans", "Epistle Laodiceans", "Epist Laodiceans", "Ep Laod", "Laodiceans", "Laod"
            ]
        }
    ]

    bible_books_list = (
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
