"""Small, deterministic Bangla/Banglish language layer; no network or model runtime."""
import re
import unicodedata
from calendar import monthrange
from datetime import date, timedelta
from difflib import SequenceMatcher
from django.utils import timezone

DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
LETTERS = dict(zip(
    "অআইঈউঊঋএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়ৎংঃঁািীুূৃেৈোৌ্",
    ["o", "a", "i", "i", "u", "u", "ri", "e", "oi", "o", "ou", "k", "kh", "g", "gh", "ng", "ch", "ch", "j", "jh", "n", "t", "th", "d", "dh", "n", "t", "th", "d", "dh", "n", "p", "f", "b", "bh", "m", "j", "r", "l", "s", "s", "s", "h", "r", "r", "y", "t", "ng", "", "", "a", "i", "i", "u", "u", "ri", "e", "oi", "o", "ou", ""],
))


def normalize(text):
    text = unicodedata.normalize("NFC", str(text)).casefold().translate(DIGITS)
    text = "".join(LETTERS.get(ch, ch) for ch in text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def phonetic(text):
    text = normalize(text).replace("ph", "f").replace("bh", "b").replace("sh", "s").replace("chh", "ch").replace("kh", "k").replace("th", "t").replace("dh", "d")
    return re.sub(r"[aeiou\s]", "", text)


def has(text, *words):
    text = str(text).casefold().translate(DIGITS)
    return any(word in text if re.search(r"[\u0980-\u09ff]", word) else re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text) for word in words)


def match_entities(question, rows):
    """Return scored, ambiguous candidates rather than silently choosing a near match."""
    normalized = normalize(question)
    tokens = normalized.split()
    windows = {" ".join(tokens[i:i + size]) for size in range(1, 7) for i in range(len(tokens) - size + 1)}
    stripped = set(windows)
    for word in windows:
        for suffix in ("er", "r", "ke", "ta", "tir", "der", "s"):
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                stripped.add(word[:-len(suffix)])
    reserved = set(normalize("employee employees salary stock party payment due main total month leave absent কর্মী কর্মীর কর্মীদের কর্মচারী বেতন বেতনের মজুদ স্টক পার্টি পার্টির পেমেন্ট মোট মাস ছুটি অনুপস্থিত কবে কত কার সব নাম").split())
    name_windows = {word for word in stripped if not any(token in reserved for token in word.split())}
    compact_windows = {phonetic(word) for word in name_windows}
    results = []
    for row in rows:
        name = normalize(row["name"])
        code = normalize(row.get("code", ""))
        score = 0.0
        if name in stripped:
            score = .90 if all(token in reserved for token in name.split()) else 1.0
        elif code and code in windows:
            score = 1.0
        elif len(phonetic(name)) >= 3 and phonetic(name) in compact_windows:
            score = .95
        elif any(len(token) >= 3 and token in name_windows for token in name.split() if token not in ("md", "mohammad", "muhammad")):
            score = .93
        else:
            relevant = [window for window in name_windows if abs(len(window) - len(name)) <= 3]
            score = max((SequenceMatcher(None, name, word).ratio() * .90 for word in relevant), default=0)
        if score >= .72:
            results.append({**row, "score": score})
    return sorted(results, key=lambda row: (-row["score"], row["name"], row["id"]))


MONTHS = {
    1: ("january", "jan", "januari", "জানুয়ারি", "জানুয়ারি"),
    2: ("february", "feb", "februari", "ফেব্রুয়ারি", "ফেব্রুয়ারি"),
    3: ("march", "mar", "মার্চ"), 4: ("april", "apr", "এপ্রিল"),
    5: ("may", "মে"), 6: ("june", "jun", "জুন"),
    7: ("july", "jul", "জুলাই"), 8: ("august", "aug", "আগস্ট"),
    9: ("september", "sep", "sept", "সেপ্টেম্বর"), 10: ("october", "oct", "অক্টোবর"),
    11: ("november", "nov", "নভেম্বর"), 12: ("december", "dec", "ডিসেম্বর"),
}


def period(question):
    text = question.casefold().translate(DIGITS)
    today = timezone.localdate()
    try:
        match = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", text)
        if match:
            value = date(*map(int, match.groups()))
            return {"start": value.isoformat(), "end": value.isoformat(), "label": value.isoformat(), "explicit": True}
        match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text)
        if match:
            day, month, year = map(int, match.groups())
            value = date(year, month, day)
            return {"start": value.isoformat(), "end": value.isoformat(), "label": value.isoformat(), "explicit": True}
        month_match = re.search(r"\b(\d{4})[-/](\d{1,2})\b", text)
        year, month = today.year, today.month
        explicit = False
        if month_match:
            year, month = map(int, month_match.groups()); explicit = True
        else:
            for number, aliases in MONTHS.items():
                if any(re.search(r"(?<![a-z0-9\u0980-\u09ff])" + re.escape(alias) + r"(?:ের|এর|ে)?(?![a-z0-9\u0980-\u09ff])", text) for alias in aliases):
                    month = number; explicit = True
                    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", text)
                    if year_match: year = int(year_match.group())
                    # A day immediately before a month name is an exact day.
                    for alias in aliases:
                        day_match = re.search(r"(?<!\d)(\d{1,2})\s+" + re.escape(alias), text)
                        if day_match:
                            value = date(year, month, int(day_match.group(1)))
                            return {"start": value.isoformat(), "end": value.isoformat(), "label": value.isoformat(), "explicit": True}
                    break
        if has(text, "last month", "previous month", "ager mash", "ag er mash", "goto mash", "গত মাস", "আগের মাস"):
            previous = today.replace(day=1) - timedelta(days=1)
            year, month, explicit = previous.year, previous.month, True
        elif has(text, "this month", "current month", "ei mash", "e mas", "ei mas", "এই মাস", "চলতি মাস"):
            year, month, explicit = today.year, today.month, True
        elif has(text, "today", "aj", "aaj", "আজ"):
            return {"start": today.isoformat(), "end": today.isoformat(), "label": today.isoformat(), "explicit": True}
        elif has(text, "yesterday", "gotokal", "গতকাল"):
            value = today - timedelta(days=1)
            return {"start": value.isoformat(), "end": value.isoformat(), "label": value.isoformat(), "explicit": True}
        if explicit:
            return {"start": date(year, month, 1).isoformat(), "end": date(year, month, monthrange(year, month)[1]).isoformat(), "label": f"{year:04d}-{month:02d}", "explicit": True}
        return None
    except ValueError:
        return {"error": "তারিখ বা মাসটি সঠিক নয়। যেমন 2026-11 অথবা 2026-11-16 লিখুন।"}


def intent(question, previous=None):
    if has(question, "lot", "লট"):
        return "lot"
    if has(question, "showroom", "শোরুম", "zone", "জোন") and not has(question, "stock", "স্টক", "মজুদ"):
        return "showroom"
    if has(question, "salary", "salaries", "monthly pay", "attendance", "হাজিরা", "বেতন", "beton", "betan", "বেতনের", "মাইনে", "maine", "absent", "absence", "অনুপস্থিত", "leave", "ছুটি", "chuti", "বোনাস", "bonus", "overtime", "ওভারটাইম", "loan", "অগ্রিম", "advance", "deduction", "কর্তন", "employee", "কর্মী", "কর্মচারী"):
        return "employee"
    if has(question, "stock", "stok", "স্টক", "মজুদ", "inventory", "product", "পণ্য", "মাল"):
        return "stock"
    if has(question, "showroom", "শোরুম", "zone", "জোন"):
        return "showroom"
    if has(question, "producer", "প্রডিউসার", "উৎপাদক", "কারিগর"):
        return "producer"
    if has(question, "swing", "sewing", "selai", "সেলাই", "operator", "অপারেটর"):
        return "swing"
    if has(question, "party", "partyr", "পার্টি", "wholesale", "পাইকারি", "paikari", "buyer", "ক্রেতা", "payment", "payement", "পেমেন্ট", "due", "বকেয়া", "বকেয়া", "baki", "বাকি", "পরিশোধ", "paid", "joma", "জমা"):
        return "party"
    if has(question, "business", "ব্যবসা", "saransho", "সারাংশ", "overall", "সর্বমোট"):
        return "business"
    return previous or "unknown"
