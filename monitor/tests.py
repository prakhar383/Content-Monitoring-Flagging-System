from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from datetime import datetime, timedelta

from .models import Keyword, ContentItem, Flag
from .services import ScanService


# ================================================================ #
# 1. SCORING LOGIC TESTS
# ================================================================ #
class ScoringTest(TestCase):
    """
    Tests for ScanService.compute_score()
    Verifies all three scoring rules work correctly.
    """

    def test_exact_title_match_returns_100(self):
        score = ScanService.compute_score(
            "django", "Learn Django Fast", "some body text"
        )
        self.assertEqual(score, 100)

    def test_partial_title_match_returns_70(self):
        # "django" is inside "djangoproject" — partial match
        score = ScanService.compute_score(
            "django", "Visit djangoproject today", "some body"
        )
        self.assertEqual(score, 70)

    def test_body_only_match_returns_40(self):
        score = ScanService.compute_score(
            "python", "Cooking Tips", "Learn python for automation"
        )
        self.assertEqual(score, 40)

    def test_no_match_returns_0(self):
        score = ScanService.compute_score(
            "django", "Cooking Tips", "Best recipes for beginners"
        )
        self.assertEqual(score, 0)

    def test_case_insensitive_matching(self):
        # Keywords are lowercased — "Python" in title should still match
        score = ScanService.compute_score(
            "python", "Python Automation Scripts", "some body"
        )
        self.assertEqual(score, 100)


# ================================================================ #
# 2. SUPPRESSION LOGIC TESTS
# ================================================================ #
class SuppressionTest(TestCase):
    """
    Tests for ScanService.should_suppress()
    This is the most important business rule in the assignment.
    """

    def setUp(self):
        # Create base objects used across all suppression tests
        self.keyword = Keyword.objects.create(name="python")
        self.content_item = ContentItem.objects.create(
            title="Python Guide",
            source="mock",
            body="Learn python programming",
            last_updated=timezone.now() - timedelta(days=5),
        )

    def test_pending_flag_never_suppressed(self):
        flag = Flag.objects.create(
            keyword=self.keyword,
            content_item=self.content_item,
            score=100,
            status="pending",
        )
        result = ScanService.should_suppress(flag, self.content_item)
        self.assertFalse(result)

    def test_relevant_flag_never_suppressed(self):
        flag = Flag.objects.create(
            keyword=self.keyword,
            content_item=self.content_item,
            score=100,
            status="relevant",
            reviewed_at=timezone.now() - timedelta(days=1),
        )
        result = ScanService.should_suppress(flag, self.content_item)
        self.assertFalse(result)

    def test_irrelevant_flag_suppressed_when_content_unchanged(self):
        """
        Core suppression rule:
        Flag is irrelevant + article NOT updated since review → suppress it
        """
        reviewed_time = timezone.now() - timedelta(days=1)
        # Article was last updated 5 days ago — BEFORE the review
        self.content_item.last_updated = timezone.now() - timedelta(days=5)
        self.content_item.save()

        flag = Flag.objects.create(
            keyword=self.keyword,
            content_item=self.content_item,
            score=40,
            status="irrelevant",
            reviewed_at=reviewed_time,
        )
        result = ScanService.should_suppress(flag, self.content_item)
        self.assertTrue(result)  # should be suppressed

    def test_irrelevant_flag_resurfaces_when_content_updated(self):
        """
        Core suppression rule exception:
        Flag is irrelevant BUT article was updated after review → show again
        """
        reviewed_time = timezone.now() - timedelta(days=3)
        # Article updated 1 day ago — AFTER the review
        self.content_item.last_updated = timezone.now() - timedelta(days=1)
        self.content_item.save()

        flag = Flag.objects.create(
            keyword=self.keyword,
            content_item=self.content_item,
            score=40,
            status="irrelevant",
            reviewed_at=reviewed_time,
        )
        result = ScanService.should_suppress(flag, self.content_item)
        self.assertFalse(result)  # should NOT be suppressed


# ================================================================ #
# 3. KEYWORD API TESTS
# ================================================================ #
class KeywordAPITest(TestCase):
    """
    Tests for POST /api/keywords/ and GET /api/keywords/
    """

    def setUp(self):
        self.client = APIClient()

    def test_create_keyword_success(self):
        response = self.client.post(
            "/api/keywords/",
            {"name": "django"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "django")
        self.assertEqual(Keyword.objects.count(), 1)

    def test_keyword_is_lowercased_on_save(self):
        # Our validator strips and lowercases
        response = self.client.post(
            "/api/keywords/",
            {"name": "  Django  "},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "django")

    def test_duplicate_keyword_rejected(self):
        Keyword.objects.create(name="python")
        response = self.client.post(
            "/api/keywords/",
            {"name": "python"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_list_keywords(self):
        Keyword.objects.create(name="python")
        Keyword.objects.create(name="django")
        response = self.client.get("/api/keywords/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)


# ================================================================ #
# 4. FLAG API TESTS
# ================================================================ #
class FlagAPITest(TestCase):
    """
    Tests for GET /api/flags/ and PATCH /api/flags/{id}/
    """

    def setUp(self):
        self.client = APIClient()
        self.keyword = Keyword.objects.create(name="python")
        self.content = ContentItem.objects.create(
            title="Python Guide",
            source="mock",
            body="Learn python",
            last_updated=timezone.now(),
        )
        self.flag = Flag.objects.create(
            keyword=self.keyword,
            content_item=self.content,
            score=100,
            status="pending",
        )

    def test_list_flags(self):
        response = self.client.get("/api/flags/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_flags_by_status(self):
        response = self.client.get("/api/flags/?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        response = self.client.get("/api/flags/?status=relevant")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_patch_flag_to_relevant(self):
        response = self.client.patch(
            f"/api/flags/{self.flag.id}/",
            {"status": "relevant"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.flag.refresh_from_db()
        self.assertEqual(self.flag.status, "relevant")

    def test_patch_flag_to_irrelevant_sets_reviewed_at(self):
        """
        When a reviewer marks a flag irrelevant,
        reviewed_at must be stamped — this drives suppression.
        """
        response = self.client.patch(
            f"/api/flags/{self.flag.id}/",
            {"status": "irrelevant"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.flag.refresh_from_db()
        self.assertEqual(self.flag.status, "irrelevant")
        self.assertIsNotNone(self.flag.reviewed_at)  # must be stamped!

    def test_patch_invalid_status_rejected(self):
        response = self.client.patch(
            f"/api/flags/{self.flag.id}/",
            {"status": "approved"},  # not a valid status
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_nonexistent_flag_returns_404(self):
        response = self.client.patch(
            "/api/flags/9999/",
            {"status": "relevant"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


# ================================================================ #
# 5. FULL SCAN INTEGRATION TEST
# ================================================================ #
class ScanIntegrationTest(TestCase):
    """
    End-to-end test of the scan endpoint.
    Tests that scanning creates flags and suppression works
    across two consecutive scans.
    """

    def setUp(self):
        self.client = APIClient()

    def test_scan_creates_flags(self):
        Keyword.objects.create(name="python")
        response = self.client.post("/api/scan/")
        self.assertEqual(response.status_code, 200)
        # At least one flag should have been created
        self.assertGreater(Flag.objects.count(), 0)

    def test_second_scan_suppresses_irrelevant_flags(self):
        """
        Full suppression flow:
        1. Scan → flags created
        2. Mark one flag irrelevant
        3. Scan again → that flag is suppressed
        """
        Keyword.objects.create(name="python")

        # First scan
        self.client.post("/api/scan/")
        flag = Flag.objects.first()

        # Reviewer marks it irrelevant
        self.client.patch(
            f"/api/flags/{flag.id}/",
            {"status": "irrelevant"},
            format="json",
        )

        # Second scan
        response = self.client.post("/api/scan/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(
            response.data["results"]["flags_suppressed"], 1
        )