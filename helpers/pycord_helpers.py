from dataclasses import dataclass, field
from typing import Optional

import discord
from discord.ext import pages


class DiscordEmbedCreator:
    """
    A utility class for creating Discord embed objects with structured data.
    """

    @dataclass
    class EmbedFooter:
        """
        Represents the footer of an embed, including text and optional icon URLs.
        """
        text: str
        icon_url: Optional[str] = None
        proxy_icon_url: Optional[str] = None

    @dataclass
    class EmbedImage:
        """
        Represents an image in an embed, including URL and optional proxy, height, and width.
        """
        url: str
        proxy_url: Optional[str] = None
        height: Optional[int] = None
        width: Optional[int] = None

    @dataclass
    class EmbedThumbnail:
        """
        Represents a thumbnail in an embed, including URL and optional proxy, height, and width.
        """
        url: str
        proxy_url: Optional[str] = None
        height: Optional[int] = None
        width: Optional[int] = None

    @dataclass
    class EmbedVideo:
        """
        Represents a video in an embed, including URL and optional proxy, height, and width.
        """
        url: Optional[str] = None
        proxy_url: Optional[str] = None
        height: Optional[int] = None
        width: Optional[int] = None

    @dataclass
    class EmbedAuthor:
        """
        Represents the author of an embed, including name, URL, and optional icon URLs.
        """
        name: str
        url: Optional[str] = None
        icon_url: Optional[str] = None
        proxy_icon_url: Optional[str] = None

    @dataclass
    class EmbedProvider:
        """
        Represents the provider of an embed, including optional name and URL.
        """
        name: Optional[str] = None
        url: Optional[str] = None

    @dataclass
    class EmbedField:
        """
        Represents a field in an embed, including name, value, and whether it should be inline.
        """
        name: str
        value: str
        inline: bool = False

    @dataclass
    class EmbedFieldNewLine:
        """
        Represents a new line field in an embed, used for spacing.
        """
        name: str = "\u200B"
        value: str = "\u200B"
        inline: bool = False

    @dataclass
    class EmbedData:
        """
        Represents the complete data for an embed, including title, description, fields, and other elements.
        """
        title: Optional[str] = None
        description: Optional[str] = None
        url: Optional[str] = None
        timestamp: Optional[str] = None
        color: Optional[int] = None
        footer: Optional["DiscordEmbedCreator.EmbedFooter"] = None
        image: Optional["DiscordEmbedCreator.EmbedImage"] = None
        thumbnail: Optional["DiscordEmbedCreator.EmbedThumbnail"] = None
        video: Optional["DiscordEmbedCreator.EmbedVideo"] = None
        author: Optional["DiscordEmbedCreator.EmbedAuthor"] = None
        provider: Optional["DiscordEmbedCreator.EmbedProvider"] = None
        fields: list["DiscordEmbedCreator.EmbedField"] = field(default_factory=list)
        type: str = "rich"

        MAX_TITLE_LENGTH = 256
        MAX_DESCRIPTION_LENGTH = 4093
        MAX_FIELDS = 25
        MAX_FIELD_NAME_LENGTH = 253
        MAX_FIELD_VALUE_LENGTH = 1021
        MAX_FOOTER_TEXT_LENGTH = 2045
        MAX_AUTHOR_NAME_LENGTH = 253
        MAX_TOTAL_CHARACTERS = 6000

        def to_discord_embed(self) -> discord.Embed:
            """
            Convert the EmbedData instance to a discord.Embed object.

            :return: A discord.Embed object representing the current EmbedData.
            """
            # Truncate fields to meet character limits
            if self.title and len(self.title) > self.MAX_TITLE_LENGTH:
                self.title = f"{self.title[:self.MAX_TITLE_LENGTH]}..."
            if self.description and len(self.description) > self.MAX_DESCRIPTION_LENGTH:
                self.description = f"{self.description[:self.MAX_DESCRIPTION_LENGTH]}..."
            if self.footer and len(self.footer.text) > self.MAX_FOOTER_TEXT_LENGTH:
                self.footer.text = f"{self.footer.text[:self.MAX_FOOTER_TEXT_LENGTH]}..."
            if self.author and len(self.author.name) > self.MAX_AUTHOR_NAME_LENGTH:
                self.author.name = f"{self.author.name[:self.MAX_AUTHOR_NAME_LENGTH]}..."

            # Truncate fields to meet the maximum number of allowed fields
            if len(self.fields) > self.MAX_FIELDS:
                self.fields = self.fields[:self.MAX_FIELDS]

            # Truncate individual field names and values
            total_characters = (
                len(self.title or "") +
                len(self.description or "") +
                len(self.footer.text if self.footer else "") +
                len(self.author.name if self.author else "")
            )

            for embed_field in self.fields:
                if embed_field.name and len(embed_field.name) > self.MAX_FIELD_NAME_LENGTH:
                    embed_field.name = embed_field.name[:self.MAX_FIELD_NAME_LENGTH]
                    field_name_len = len(embed_field.name)
                else:
                    field_name_len = 0

                if embed_field.value and len(embed_field.value) > self.MAX_FIELD_VALUE_LENGTH:
                    embed_field.value = embed_field.value[:self.MAX_FIELD_VALUE_LENGTH]
                    field_value_len = len(embed_field.value)
                else:
                    field_value_len = 0

                total_characters += field_name_len + field_value_len

            # Ensure total character count does not exceed the limit
            if total_characters > self.MAX_TOTAL_CHARACTERS:
                excess = total_characters - self.MAX_TOTAL_CHARACTERS
                if self.description and len(self.description) > excess:
                    self.description = self.description[:len(self.description) - excess]
                else:
                    self.description = ""

            # Create the Discord Embed object
            embed = discord.Embed(
                title=self.title,
                description=self.description,
                url=self.url,
                color=self.color,
                type=self.type if self.type in ["rich", "image", "video", "gifv", "article", "link", "poll_result"] else "rich",
            )
            if self.timestamp:
                embed.timestamp = discord.utils.parse_time(self.timestamp)
            if self.footer:
                embed.set_footer(text=self.footer.text, icon_url=self.footer.icon_url)
            if self.image:
                embed.set_image(url=self.image.url)
            if self.thumbnail:
                embed.set_thumbnail(url=self.thumbnail.url)
            if self.video:
                if "youtube.com" in self.video.url:
                    video_id = self.video.url.split("v=")[1].split("&t=")[0]
                    thumbnail_url = f"""http://img.youtube.com/vi/{video_id}/0.jpg"""
                    embed.set_thumbnail(url=thumbnail_url)

                # Override any other URL set
                embed.url = self.video.url
            if self.author:
                embed.set_author(name=self.author.name, url=self.author.url, icon_url=self.author.icon_url)
            if self.provider:
                # Note: discord.Embed does not support setting provider directly, this is just for completeness
                pass
            for embed_field in self.fields:
                embed.add_field(name=embed_field.name, value=embed_field.value, inline=embed_field.inline)
            return embed

    @staticmethod
    def create_embed(*, embed_data: "DiscordEmbedCreator.EmbedData") -> discord.Embed:
        """
        Create a discord.Embed object from the provided EmbedData.

        :param embed_data: The data to use for creating the embed.
        :return: A discord.Embed object.
        """
        embed = embed_data.to_discord_embed()
        return embed


class DiscordEmbedPaginator:
    """
    A utility class for creating paginated Discord embeds.
    """

    @dataclass
    class EmbedFooter:
        """
        Represents the footer of an embed, including text and optional icon URLs.
        """
        text: str
        icon_url: Optional[str] = None
        proxy_icon_url: Optional[str] = None

    @dataclass
    class EmbedData:
        """
        Represents the complete data for an embed, including title, description, footer, and other optional elements.
        """
        title: Optional[str] = None
        description: Optional[str] = None
        url: Optional[str] = None
        color: Optional[int] = None
        footer: Optional["DiscordEmbedPaginator.EmbedFooter"] = None

        def to_discord_embed(self) -> discord.Embed:
            """
            Convert the EmbedData instance to a discord.Embed object.

            :return: A discord.Embed object representing the current EmbedData.
            """
            embed = discord.Embed(
                title=self.title,
                description=self.description,
                url=self.url,
                color=self.color,
            )
            if self.footer:
                embed.set_footer(text=self.footer.text, icon_url=self.footer.icon_url)
            return embed

    @staticmethod
    def create_paginated_embeds(*, embeds: list[discord.Embed], header_embed: Optional[discord.Embed] = None, footer_embed: Optional[discord.Embed] = None, embeds_per_page: int = 10) -> list[pages.Page]:
        """
        Create a list of paginated embeds with optional header and footer embeds.

        :param embeds: A list of discord.Embed objects to paginate.
        :param header_embed: An optional discord.Embed to be added as the header of each page.
        :param footer_embed: An optional discord.Embed to be added as the footer of each page.
        :param embeds_per_page: The number of embeds to include per page.
        :return: A list of pages.Page objects representing the paginated embeds.
        """
        # Adjust embeds_per_page based on the presence of header and footer
        max_embeds_per_page = embeds_per_page
        if header_embed:
            max_embeds_per_page -= 1
        if footer_embed:
            max_embeds_per_page -= 1

        paginated_embeds = []
        current_page = []

        for embed in embeds:
            current_page.append(embed)

            if len(current_page) == max_embeds_per_page:
                if header_embed:
                    current_page.insert(0, header_embed)

                if footer_embed:
                    current_page.append(footer_embed)

                paginated_embeds.append(pages.Page(embeds=current_page))
                current_page = []

        # Add the last page if it has any remaining embeds
        if len(current_page) > 0:
            if header_embed:
                current_page.insert(0, header_embed)

            if footer_embed:
                current_page.append(footer_embed)

            paginated_embeds.append(pages.Page(embeds=current_page))

        return paginated_embeds
