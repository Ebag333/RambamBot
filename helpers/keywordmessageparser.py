import re

import sources.biblegateway
import sources.sefaria

SefariaAPI = sources.sefaria.SefariaAPI()
BibleGateway = sources.biblegateway.BibleGateway()
BibleData = sources.biblegateway.BibleData


class KeywordMessageParser:
    def __init__(self):
        self.christian_titles = BibleData.books
        self.jewish_titles = [d["title"] for d in SefariaAPI.sefaria_index if "title" in d]
        self.jewish_titles = [title for title in self.jewish_titles if title not in self.christian_titles]

    def parse_message(self, message: str):
        # Regular expression to match keyword followed by book/chapter reference
        pattern = r"\b({keywords})\s+(\d+(?:\.\d+|:\d+)*)"

        combined_matches = []

        # Process keywords for Christian Bible references
        keyword_a_pattern = pattern.format(keywords="|".join(map(re.escape, self.christian_titles)))
        matches_a = re.finditer(keyword_a_pattern, message)
        for match in matches_a:
            combined_matches.append((match.start(), "biblegateway", f"{match.group(1)} {match.group(2)}"))

        # Process keywords for Sefaria references
        keyword_b_pattern = pattern.format(keywords="|".join(map(re.escape, self.jewish_titles)))
        matches_b = re.finditer(keyword_b_pattern, message)
        for match in matches_b:
            combined_matches.append((match.start(), "sefaria", f"{match.group(1)} {match.group(2)}"))

        # Sort matches by their order in the message
        combined_matches.sort(key=lambda x: x[0])

        # Remove all really broad references, like whole chapters
        combined_matches = [item for item in combined_matches if re.search(r'\d+[:.\s]\d+', item[2])]

        all_embeds = []

        for _, source, reference in combined_matches:
            if source == "biblegateway":
                embeds = BibleGateway.fetch_verse(verses=reference)
                all_embeds.extend(embeds)
            elif source == "sefaria":
                embeds = SefariaAPI.get_sefaria_text(reference=reference, language="English")
                all_embeds.extend(embeds)

        return all_embeds
