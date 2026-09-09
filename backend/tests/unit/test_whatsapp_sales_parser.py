"""Unit tests for the WhatsApp sales parser.

Fixtures mirror the real Vrindavan Treats group format: the message POST
date is one day AFTER the sale date, which is embedded as a text label.
"""

from app.services.whatsapp_sales_parser import parse_whatsapp_chat


SAMPLE_CHAT = """03/06/25, 10:21 am - Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them.
03/10/25, 1:00 pm - Swapnil 555 Harak: Cash 8400.  Online 6335
20/11/25, 9:00 am - Support System: Cash 2100
Online 5120
03/12/25, 8:00 am - Support System: Cash 3040
Online .1793
16/08/26, 1:10 pm - Swapnil 555 Harak: 15 August
Cash 2750
Online 5769
17/08/26, 12:37 pm - Swapnil 555 Harak: 16 August
Cash 2860
Online 3079
19/08/26, 3:17 pm - Swapnil 555 Harak: 18 August
Cash 3350
Online 5489
"""


class TestParseWhatsAppChat:
    def test_parses_cash_online_messages(self):
        rows = parse_whatsapp_chat(SAMPLE_CHAT)
        # Encryption notice skipped; 6 real sales rows
        assert len(rows) == 6

    def test_uses_message_date_when_no_label(self):
        rows = parse_whatsapp_chat(SAMPLE_CHAT)
        r = rows[0]
        assert r["sale_date"] == "2025-10-03"
        assert r["cash_amount"] == 8400
        assert r["online_amount"] == 6335

    def test_uses_in_message_date_label_over_post_date(self):
        rows = parse_whatsapp_chat(SAMPLE_CHAT)
        # Message posted 16/08/26 but labelled "15 August" -> sale 2026-08-15
        labelled = [r for r in rows if r["sale_date"] == "2026-08-15"]
        assert len(labelled) == 1
        assert labelled[0]["cash_amount"] == 2750
        assert labelled[0]["online_amount"] == 5769

    def test_dedupes_by_sale_date(self):
        chat = (
            "16/08/26, 1:10 pm - Swapnil: 15 August \nCash 2750 \nOnline 5769\n"
            "16/08/26, 2:00 pm - Swapnil: 15 August \nCash 5000 \nOnline 6000\n"
        )
        rows = parse_whatsapp_chat(chat)
        assert len(rows) == 1  # first wins
        assert rows[0]["cash_amount"] == 2750

    def test_skips_messages_without_cash_online(self):
        chat = "08/06/25, 11:17 am - 100rabh: Vrindavan Treats\n"
        assert parse_whatsapp_chat(chat) == []

    def test_handles_reverse_order_online_then_cash(self):
        chat = "14/12/25, 8:00 am - Support System: Online.4905.\nCash.2110.\n"
        rows = parse_whatsapp_chat(chat)
        assert rows[0]["online_amount"] == 4905
        assert rows[0]["cash_amount"] == 2110

    def test_skips_absurd_amounts(self):
        chat = "01/01/26, 8:00 am - Swapnil: Cash 9999999 Online 8888888\n"
        assert parse_whatsapp_chat(chat) == []

    def test_multi_line_message_continuation(self):
        chat = (
            "20/09/25, 9:00 am - Swapnil: 3076 online \n"
            "5000 cash \n"
            "Counter payment 500\n"
            "Total 8576\n"
        )
        rows = parse_whatsapp_chat(chat)
        assert len(rows) == 1
        assert rows[0]["cash_amount"] == 5000
        assert rows[0]["online_amount"] == 3076


class TestSplitMessageDayAggregation:
    """Second pass: days where cash and online were posted as separate
    messages on the same date."""

    def test_separate_side_messages_pair_up(self):
        chat = (
            "23/09/25, 9:00 am - Support System: Cash total.1510\n"
            "23/09/25, 9:01 am - Swapnil 555 Harak: 2046 online\n"
            "23/09/25, 9:05 am - Support System: 1950 cash\n"
            "23/09/25, 9:06 am - Swapnil 555 Harak: 917 online\n"
        )
        rows = parse_whatsapp_chat(chat)
        assert len(rows) == 1
        assert rows[0]["sale_date"] == "2025-09-23"
        assert rows[0]["cash_amount"] == 3460.0
        assert rows[0]["online_amount"] == 2963.0

    def test_arithmetic_chain_is_summed(self):
        chat = (
            "14/06/26, 8:00 pm - Support System: Online 3230+2550=5780\n"
            "14/06/26, 8:01 pm - Support System: Cash 2000\n"
        )
        rows = parse_whatsapp_chat(chat)
        assert len(rows) == 1
        assert rows[0]["online_amount"] == 5780.0
        assert rows[0]["cash_amount"] == 2000.0

    def test_one_sided_day_is_skipped(self):
        chat = (
            "22/09/25, 8:00 pm - Support System: 3900 total.\n"
            "22/09/25, 8:01 pm - Support System: 400 cash thevto\n"
            "22/09/25, 8:02 pm - Support System: 510 counter\n"
        )
        assert parse_whatsapp_chat(chat) == []

    def test_paired_message_wins_over_same_day_partials(self):
        chat = (
            "15/08/26, 10:00 am - Swapnil 555 Harak: 15 August \nCash 2750 \nOnline 5769\n"
            "15/08/26, 11:00 am - Support System: Cash 100\n"
        )
        rows = parse_whatsapp_chat(chat)
        assert len(rows) == 1
        assert rows[0]["cash_amount"] == 2750.0
        assert rows[0]["online_amount"] == 5769.0


class TestAuditBugFixes:
    """Regression tests for bugs found in the Aug 2026 audit."""

    def test_double_dot_separator(self):
        """Cash..16500 (double dot) should parse. Bug: June 6 was missed."""
        chat = (
            "08/06/26, 12:55 am - Swapnil 555 Harak: 6 June\n"
            "Cash..16500\n"
            "Online 19337\n"
            "Hdfc 1730\n"
        )
        rows = parse_whatsapp_chat(chat)
        assert len(rows) == 1
        assert rows[0]["sale_date"] == "2026-06-06"
        assert rows[0]["cash_amount"] == 16500.0
        assert rows[0]["online_amount"] == 19337.0

    def test_no_space_date_label(self):
        """'11August' (no space) should parse as Aug 11. Bug: misattributed to Aug 12."""
        chat = (
            "12/08/26, 6:03 pm - Swapnil 555 Harak: 11August\n"
            "Cash 4620\n"
            "Online 5134\n"
            "13/08/26, 1:00 pm - Swapnil 555 Harak: 12 August\n"
            "Cash 6170\n"
            "Online 5367\n"
        )
        rows = parse_whatsapp_chat(chat)
        dates = {r["sale_date"]: r for r in rows}
        assert "2026-08-11" in dates
        assert dates["2026-08-11"]["cash_amount"] == 4620.0
        assert "2026-08-12" in dates
        assert dates["2026-08-12"]["cash_amount"] == 6170.0

    def test_online_only_labeled_post(self):
        """'14 August\nOnline 580' with no cash should still produce a row."""
        chat = (
            "15/08/26, 12:48 pm - Swapnil 555 Harak: 14 August\n"
            "Online 580\n"
        )
        rows = parse_whatsapp_chat(chat)
        assert len(rows) == 1
        assert rows[0]["sale_date"] == "2026-08-14"
        assert rows[0]["online_amount"] == 580.0
        assert rows[0]["cash_amount"] == 0.0

    def test_bare_number_label_still_skipped(self):
        """A bare number label like '26\\nCash 9400' should NOT match as a date
        (no month name present). Parser correctly falls back to post date."""
        chat = (
            "28/06/26, 9:25 am - Swapnil 555 Harak: 26\n"
            "Cash 9400\n"
            "Online 13825\n"
        )
        rows = parse_whatsapp_chat(chat)
        assert len(rows) == 1
        # Falls back to message date since "26" alone is not a valid date label
        assert rows[0]["sale_date"] == "2026-06-28"
