"""
HTML Parser for Telegram Web Channel Previews.
Extracts posts, channel metadata, media, reactions, and pagination links.
"""

from typing import Optional, List, Tuple
from bs4 import BeautifulSoup, Tag
import re

from .models import (
    TelegramPost,
    ChannelInfo,
    PostReaction,
    ForwardInfo,
    LinkPreview,
    PollInfo,
    PollOption,
    MediaAttachment,
)
from .utils import parse_count_str, extract_background_image_url


class TelegramParser:
    """Parses Telegram channel HTML preview pages."""

    @staticmethod
    def parse_channel_info(soup: BeautifulSoup, default_username: str) -> ChannelInfo:
        """Extract channel header information (title, bio, subscriber count, avatar)."""
        # Channel title
        title_el = (
            soup.find("div", class_="tgme_channel_info_header_title")
            or soup.find("div", class_="tgme_page_title")
        )
        title = title_el.get_text(strip=True) if title_el else default_username

        # Bio / Description
        desc_el = (
            soup.find("div", class_="tgme_channel_info_description")
            or soup.find("div", class_="tgme_page_description")
        )
        description = desc_el.get_text(separator="\n", strip=True) if desc_el else None

        # Subscribers count
        subs_text = None
        counters = soup.find("div", class_="tgme_channel_info_counters")
        if counters:
            counter_val = counters.find("span", class_="counter_value")
            if counter_val:
                subs_text = counter_val.get_text(strip=True)
        if not subs_text:
            extra_el = soup.find("div", class_="tgme_page_extra")
            if extra_el:
                extra_text = extra_el.get_text(strip=True)
                match = re.search(r"([\d\s\.,KMkm]+)\s*(?:subscribers|members|عضو|مشترک)?", extra_text)
                if match:
                    subs_text = match.group(1).strip()

        # Avatar URL
        avatar_url = None
        avatar_img = (
            soup.find("img", class_="tgme_page_photo_image")
            or soup.find("div", class_="tgme_page_photo").find("img")
            if soup.find("div", class_="tgme_page_photo")
            else None
        )
        if avatar_img and avatar_img.get("src"):
            avatar_url = avatar_img["src"]

        # Verified badge
        is_verified = bool(soup.find(class_=re.compile(r"verified", re.I)))

        return ChannelInfo(
            username=default_username,
            title=title,
            description=description,
            subscribers=subs_text,
            subscribers_numeric=parse_count_str(subs_text),
            avatar_url=avatar_url,
            is_verified=is_verified,
        )

    @classmethod
    def parse_posts(cls, soup: BeautifulSoup, channel_username: str) -> List[TelegramPost]:
        """Extract all posts present in the page."""
        posts: List[TelegramPost] = []
        msg_elements = soup.find_all("div", class_="tgme_widget_message")

        for msg_el in msg_elements:
            post = cls._parse_single_post(msg_el, channel_username)
            if post:
                posts.append(post)

        return posts

    @classmethod
    def _parse_single_post(cls, msg_el: Tag, channel_username: str) -> Optional[TelegramPost]:
        """Parse an individual message DOM element."""
        data_post = msg_el.get("data-post")
        if not data_post or "/" not in data_post:
            return None

        parts = data_post.split("/", 1)
        post_channel = parts[0]
        try:
            post_id = int(parts[1])
        except ValueError:
            return None

        post_url = f"https://t.me/{post_channel}/{post_id}"

        # 1. Pinned status
        is_pinned = bool(msg_el.find("div", class_="tgme_widget_message_pinned"))

        # 2. Forward info
        is_forwarded = False
        forward_info = None
        fwd_el = msg_el.find("div", class_="tgme_widget_message_forwarded_from")
        if fwd_el:
            is_forwarded = True
            fwd_name_el = fwd_el.find("a", class_="tgme_widget_message_forwarded_from_name")
            if fwd_name_el:
                forward_info = ForwardInfo(
                    from_name=fwd_name_el.get_text(strip=True),
                    from_url=fwd_name_el.get("href"),
                )
            else:
                forward_info = ForwardInfo(from_name=fwd_el.get_text(strip=True))

        # 3. Reply info
        reply_to_id = None
        reply_el = msg_el.find("a", class_="tgme_widget_message_reply")
        if reply_el and reply_el.get("href"):
            match = re.search(r"/(\d+)$", reply_el["href"])
            if match:
                reply_to_id = int(match.group(1))

        # 4. Message Text & HTML
        text = ""
        raw_html = None
        text_el = msg_el.find("div", class_="tgme_widget_message_text")
        if text_el:
            text = text_el.get_text(separator="\n", strip=True)
            raw_html = "".join(str(c) for c in text_el.contents).strip()

        # 5. Date & Time
        date_iso = None
        date_formatted = None
        time_el = msg_el.find("time")
        if time_el:
            date_iso = time_el.get("datetime")
            date_formatted = time_el.get_text(strip=True)

        # 6. Views
        views_str = None
        views_el = msg_el.find("span", class_="tgme_widget_message_views")
        if views_el:
            views_str = views_el.get_text(strip=True)
        views_num = parse_count_str(views_str)

        # 7. Reactions
        reactions: List[PostReaction] = []
        total_reactions = 0
        reaction_tags = msg_el.find_all("div", class_="tgme_widget_message_reaction")
        for r_tag in reaction_tags:
            emoji_el = r_tag.find("span", class_="tgme_reaction") or r_tag.find("img")
            emoji = emoji_el.get_text(strip=True) if emoji_el else ""
            if not emoji and emoji_el and emoji_el.name == "img":
                emoji = emoji_el.get("alt", "emoji")

            count_el = r_tag.find("span", class_="tgme_widget_message_reaction_count")
            count_val = parse_count_str(count_el.get_text(strip=True)) if count_el else 1
            if emoji and count_val is not None:
                reactions.append(PostReaction(emoji=emoji, count=count_val))
                total_reactions += count_val

        # 8. Media attachments
        media_list: List[MediaAttachment] = []

        # Photos
        photo_wraps = msg_el.find_all("a", class_="tgme_widget_message_photo_wrap")
        for photo_wrap in photo_wraps:
            style = photo_wrap.get("style", "")
            img_url = extract_background_image_url(style)
            if img_url:
                media_list.append(
                    MediaAttachment(
                        type="photo",
                        url=img_url,
                        thumbnail_url=img_url,
                    )
                )

        # Videos
        video_els = msg_el.find_all("video", class_="tgme_widget_message_video")
        for vid in video_els:
            src = vid.get("src")
            thumb = None
            parent_wrap = vid.find_parent("div", class_="tgme_widget_message_video_player")
            if parent_wrap:
                thumb_wrap = parent_wrap.find("i", class_="tgme_widget_message_video_thumb")
                if thumb_wrap and thumb_wrap.get("style"):
                    thumb = extract_background_image_url(thumb_wrap.get("style"))
            duration_el = parent_wrap.find("time", class_="message_video_duration") if parent_wrap else None
            duration = duration_el.get_text(strip=True) if duration_el else None

            media_list.append(
                MediaAttachment(
                    type="video",
                    url=src,
                    thumbnail_url=thumb,
                    duration=duration,
                )
            )

        # Voice notes / Audio
        voice_els = msg_el.find_all("audio", class_="tgme_widget_message_voice")
        for voice in voice_els:
            src = voice.get("src")
            duration_el = msg_el.find("time", class_="message_audio_duration")
            duration = duration_el.get_text(strip=True) if duration_el else None
            media_list.append(
                MediaAttachment(
                    type="voice",
                    url=src,
                    duration=duration,
                )
            )

        # Documents / Files
        doc_els = msg_el.find_all("div", class_="tgme_widget_message_document")
        for doc in doc_els:
            title_el = doc.find("div", class_="tgme_widget_message_document_title")
            extra_el = doc.find("div", class_="tgme_widget_message_document_extra")
            f_name = title_el.get_text(strip=True) if title_el else "document"
            f_size = extra_el.get_text(strip=True) if extra_el else None
            media_list.append(
                MediaAttachment(
                    type="document",
                    file_name=f_name,
                    file_size=f_size,
                )
            )

        # 9. Link preview
        link_preview = None
        lp_el = msg_el.find("a", class_="tgme_widget_message_link_preview")
        if lp_el:
            site_el = lp_el.find("div", class_="link_preview_site_name")
            lp_title_el = lp_el.find("div", class_="link_preview_title")
            desc_el = lp_el.find("div", class_="link_preview_description")
            img_el = lp_el.find("i", class_="link_preview_image")

            img_url = extract_background_image_url(img_el.get("style")) if img_el else None
            link_preview = LinkPreview(
                site_name=site_el.get_text(strip=True) if site_el else None,
                title=lp_title_el.get_text(strip=True) if lp_title_el else None,
                description=desc_el.get_text(strip=True) if desc_el else None,
                image_url=img_url,
                url=lp_el.get("href"),
            )

        # 10. Poll
        poll_info = None
        poll_el = msg_el.find("div", class_="tgme_widget_message_poll")
        if poll_el:
            q_el = poll_el.find("div", class_="tgme_widget_message_poll_question")
            question = q_el.get_text(strip=True) if q_el else ""
            options: List[PollOption] = []
            opt_els = poll_el.find_all("div", class_="tgme_widget_message_poll_option")
            for opt in opt_els:
                opt_text_el = opt.find("div", class_="tgme_widget_message_poll_option_text")
                opt_pct_el = opt.find("div", class_="tgme_widget_message_poll_option_percent")
                o_text = opt_text_el.get_text(strip=True) if opt_text_el else ""
                o_pct = opt_pct_el.get_text(strip=True) if opt_pct_el else "0%"
                if o_text:
                    options.append(PollOption(text=o_text, percent=o_pct))

            votes_el = poll_el.find("div", class_="tgme_widget_message_poll_type")
            votes = votes_el.get_text(strip=True) if votes_el else None
            poll_info = PollInfo(question=question, options=options, total_votes=votes)

        return TelegramPost(
            id=post_id,
            channel=post_channel,
            url=post_url,
            date_iso=date_iso,
            date_formatted=date_formatted,
            text=text,
            raw_html=raw_html,
            views=views_str,
            views_numeric=views_num,
            is_pinned=is_pinned,
            is_forwarded=is_forwarded,
            forward_info=forward_info,
            reply_to_post_id=reply_to_id,
            reactions=reactions,
            total_reactions_count=total_reactions,
            media=media_list,
            link_preview=link_preview,
            poll=poll_info,
        )

    @staticmethod
    def extract_before_id(soup: BeautifulSoup) -> Optional[int]:
        """Extract the pagination before_id from the 'Load more' / 'messages_more' anchor."""
        more_anchor = soup.find("a", class_="tme_messages_more")
        if not more_anchor:
            return None

        # Check href (e.g., /s/telegram?before=441)
        href = more_anchor.get("href", "")
        match = re.search(r"[?&]before=(\d+)", href)
        if match:
            return int(match.group(1))

        # Check data-before
        data_before = more_anchor.get("data-before")
        if data_before and data_before.isdigit():
            return int(data_before)

        return None
