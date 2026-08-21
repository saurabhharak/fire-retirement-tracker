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
