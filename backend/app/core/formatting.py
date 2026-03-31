"""Indian number formatting and display utilities."""


def format_indian(amount: float) -> str:
    """Format a number in Indian comma notation (e.g. 1,30,20,768)."""
    is_negative = amount < 0
    n = int(round(abs(amount)))
    s = str(n)
    if len(s) <= 3:
        result = s
    else:
        last3 = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.append(remaining)
        groups.reverse()
        result = ",".join(groups) + "," + last3
    return ("-" + result) if is_negative else result
