import json
import os
from datetime import datetime, timezone

from django.utils import timezone as django_timezone

from .models import Keyword, ContentItem, Flag


class ScanService:

    # ------------------------------------------------------------------ #
    # STEP 1 — Load content from mock JSON file
    # ------------------------------------------------------------------ #
    @staticmethod
    def fetch_content():
        """
        Reads mock_data.json and saves each article into
        the ContentItem table (skips duplicates by title+source).
        Returns a list of ContentItem objects.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'mock_data.json')

        with open(json_path, 'r') as f:
            raw_items = json.load(f)

        content_items = []
        for item in raw_items:
            last_updated = datetime.fromisoformat(
                item['last_updated'].replace('Z', '+00:00')
            )

            # get_or_create → if it already exists, just return it
            # if not, create it fresh
            obj, created = ContentItem.objects.get_or_create(
                title=item['title'],
                source=item['source'],
                defaults={
                    'body': item['body'],
                    'last_updated': last_updated,
                }
            )

            # If the article already existed, check if it was updated
            # If last_updated changed → update our stored copy
            if not created and obj.last_updated != last_updated:
                obj.body = item['body']
                obj.last_updated = last_updated
                obj.save()

            content_items.append(obj)

        return content_items

    # ------------------------------------------------------------------ #
    # STEP 2 — Score a keyword against one article
    # ------------------------------------------------------------------ #
    @staticmethod
    def compute_score(keyword_name, title, body):
        """
        Scoring rules (as required by the assignment):
          100 → exact keyword match in title
           70 → partial keyword match in title
           40 → keyword appears only in body
            0 → no match at all
        """
        kw        = keyword_name.lower()
        title_low = title.lower()
        body_low  = body.lower()

        # Split title into individual words for exact word matching
        title_words = title_low.split()

        if kw in title_words:
            return 100          # exact word match in title

        if kw in title_low:
            return 70           # partial match in title (e.g. "django" in "djangoproject")

        if kw in body_low:
            return 40           # keyword only in body

        return 0                # no match

    # ------------------------------------------------------------------ #
    # STEP 3 — The suppression logic (most important rule)
    # ------------------------------------------------------------------ #
    @staticmethod
    def should_suppress(existing_flag, content_item):
        """
        Returns True if we should SKIP creating/updating this flag.

        Rule: if a flag was previously marked 'irrelevant',
        suppress it UNLESS the content item has been updated
        since it was reviewed.
        """
        if existing_flag.status != 'irrelevant':
            return False        # not irrelevant → never suppress

        if existing_flag.reviewed_at is None:
            return False        # safety check — no review time recorded

        # Allow it back if the article was updated after the review
        if content_item.last_updated > existing_flag.reviewed_at:
            return False        # content changed → surface it again

        return True             # irrelevant + no update → suppress

    # ------------------------------------------------------------------ #
    # STEP 4 — Run the full scan
    # ------------------------------------------------------------------ #
    @classmethod
    def run_scan(cls):
        """
        Main method called by the /scan/ endpoint.
        Ties everything together.
        """
        keywords      = Keyword.objects.all()
        content_items = cls.fetch_content()

        created_count   = 0
        suppressed_count = 0

        for keyword in keywords:
            for content_item in content_items:

                score = cls.compute_score(
                    keyword.name,
                    content_item.title,
                    content_item.body
                )

                # Skip articles that don't match at all
                if score == 0:
                    continue

                # Check if a flag already exists for this pair
                existing = Flag.objects.filter(
                    keyword=keyword,
                    content_item=content_item
                ).first()

                if existing:
                    # Apply suppression rule
                    if cls.should_suppress(existing, content_item):
                        suppressed_count += 1
                        continue    # skip — don't resurface this flag

                    # Content may have changed — update the score
                    # and reset to pending so reviewer sees it again
                    existing.score  = score
                    existing.status = 'pending'
                    existing.reviewed_at = None
                    existing.save()

                else:
                    # Brand new flag — create it
                    Flag.objects.create(
                        keyword=keyword,
                        content_item=content_item,
                        score=score,
                        status='pending'
                    )
                    created_count += 1

        return {
            'keywords_scanned' : keywords.count(),
            'articles_scanned' : len(content_items),
            'flags_created'    : created_count,
            'flags_suppressed' : suppressed_count,
        }




