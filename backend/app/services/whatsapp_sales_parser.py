"""Pure WhatsApp chat parser for daily parlour sales (cash + online).

The daily pattern in the Vrindavan Treats group is:
    "Cash 8400.  Online 6335"
    "Cash.6450\nOnline.5169"
    "15 August \nCash 2750 \nOnline 5769"   <- the sales date is in the text
    "1 August \nCash 3860 \nOnline 6135"

Key nuance: the message POST date is often one day AFTER the sale date
("16/08/26 - Swapnil: 15 August"), so when a message text contains a date
label like "15 August", that is the authoritative sale date. Otherwise the
message date is used.

Pure module — no I/O. Unit-tested in tests/unit/test_whatsapp_sales_parser.py.
"""

import re
from datetime import date

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

_MSG_LINE_RE = re.compile(
    r"^(\d{2})/(\d{2})/(\d{2}),\s+\d{1,2}:\d{2}\s*[ap]m\s*-\s*(.+?):\s?(.*)$",
    re.IGNORECASE,
)

# DOTALL so cash/online on separate lines still match ("Online.4905.\nCash.2110.")
_CASH_ONLINE_RE = re.compile(
    r"(cash|counter)\s*[.:]?\s*(\d[\d,]*)\s*.*?(online|upi|gpay|phonepe|paytm)\s*[.:]?\s*(\d[\d,]*)",
    re.IGNORECASE | re.DOTALL,
)
_ONLINE_CASH_RE = re.compile(
    r"(online|upi|gpay|phonepe|paytm)\s*[.:]?\s*(\d[\d,]*)\s*.*?(cash|counter)\s*[.:]?\s*(\d[\d,]*)",
    re.IGNORECASE | re.DOTALL,
)
# Number-then-keyword: "3076 online \n5000 cash"
_NUM_ONLINE_RE = re.compile(
    r"(\d[\d,]*)\s*(online|upi|gpay|phonepe|paytm)\s*.*?(\d[\d,]*)\s*(cash|counter)",
    re.IGNORECASE | re.DOTALL,
)
_NUM_CASH_RE = re.compile(
    r"(\d[\d,]*)\s*(cash|counter)\s*.*?(\d[\d,]*)\s*(online|upi|gpay|phonepe|paytm)",
    re.IGNORECASE | re.DOTALL,
)


def _label_to_date(label: str) -> date | None:
    """Parse an in-message date label like '15 August' -> date(year=2026...)."""
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\b", label)
    if not m:
        return None
    day = int(m.group(1))
    mon = _MONTHS.get(m.group(2).lower())
    if not mon or day < 1 or day > 31:
        return None
    # Chats span Oct 2025 -> Aug 2026; label without year defaults to 2026.
    return date(2026, mon, day)


def _msg_line_date(day: str, mon: str, yr: str) -> date:
    return date(2000 + int(yr), int(mon), int(day))


def parse_whatsapp_chat(text: str) -> list[dict]:
    """Parse a WhatsApp exported chat into daily sales rows.

    Returns [{sale_date: 'YYYY-MM-DD', cash_amount, online_amount, sender_name,
    source: 'whatsapp'}]. Skips system/encryption messages and messages
    without a cash+online pair. Deduplicates by sale_date (first wins).
    """
    messages: list[dict] = []
    for line in text.splitlines():
        m = _MSG_LINE_RE.match(line)
        if m:
            day, mon, yr, sender, body = m.groups()
            messages.append(
                {
                    "msg_date": _msg_line_date(day, mon, yr),
                    "sender": sender.strip(),
                    "lines": [body.strip()],
                }
            )
        elif messages:
            # List-append + single join at the end: repeated string
            # concatenation here was O(n^2) on large chat exports.
            messages[-1]["lines"].append(line.strip())

    parsed: list[dict] = []
    seen_dates: set[date] = set()

    for msg in messages:
        body = "\n".join(msg["lines"])
        mm = _CASH_ONLINE_RE.search(body)
        if mm:
            cash = int(mm.group(2).replace(",", ""))
            online = int(mm.group(4).replace(",", ""))
        else:
            mm = _ONLINE_CASH_RE.search(body)
            if mm:
                online = int(mm.group(2).replace(",", ""))
                cash = int(mm.group(4).replace(",", ""))
            else:
                mm = _NUM_ONLINE_RE.search(body)
                if mm:
                    online = int(mm.group(1).replace(",", ""))
                    cash = int(mm.group(3).replace(",", ""))
                else:
                    mm = _NUM_CASH_RE.search(body)
                    if mm:
                        cash = int(mm.group(1).replace(",", ""))
                        online = int(mm.group(3).replace(",", ""))
                    else:
                        continue
        # Sanity: a single parlour day won't exceed ₹2L in either stream.
        if cash > 200000 or online > 200000:
            continue

        sale_date = _label_to_date(body.strip()) or msg["msg_date"]
        if sale_date in seen_dates:
            continue
        seen_dates.add(sale_date)

        parsed.append(
            {
                "sale_date": sale_date.isoformat(),
                "cash_amount": float(cash),
                "online_amount": float(online),
                "sender_name": msg["sender"],
                "source": "whatsapp",
            }
        )

    return parsed
