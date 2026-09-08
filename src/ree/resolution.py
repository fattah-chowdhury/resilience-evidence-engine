"""Transparent, intentionally conservative date, place and claim extraction rules."""

import calendar
import re
import unicodedata
from datetime import UTC, date, datetime, timedelta

from ree.models import check_geometry
from ree.storage import stable_id

DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
MONTHS = {name.lower(): i for i in range(1, 13)
          for name in (calendar.month_name[i], calendar.month_abbr[i])}


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())


def resolve_time(text, reference=None):
    result = {"start": None, "end": None, "precision": "unknown", "original": text,
              "method": "date-rules-v1", "candidates": [], "reference": reference}
    if not text:
        return result
    value = str(text).translate(DIGITS).strip()

    def interval(start, end, precision):
        result.update(start=start.isoformat(), end=end.isoformat(), precision=precision)
        return result

    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T.+", value):
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                result["warning"] = "timestamp_without_timezone"
                return result
            day = dt.astimezone(UTC).date()
            result["timestamp_utc"] = dt.astimezone(UTC).isoformat()
            return interval(day, day, "exact")
        dates = re.findall(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)", value)
        if len(set(dates)) > 1:
            days = [date.fromisoformat(x) for x in dates]
            if len(days) == 2 and re.search(r"\b(to|through|between)\b|[–—/]", value, re.IGNORECASE):
                if days[0] > days[1]:
                    raise ValueError("reversed interval")
                return interval(*days, "range")
            result.update(candidates=dates, warning="conflicting_dates")
            return result
        if dates:
            day = date.fromisoformat(dates[0])
            return interval(day, day, "exact")
        m = re.search(r"\b([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\b", value)
        if m and m[1].lower() in MONTHS:
            day = date(int(m[3]), MONTHS[m[1].lower()], int(m[2]))
            return interval(day, day, "exact")
        m = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", value)
        if m and m[2].lower() in MONTHS:
            day = date(int(m[3]), MONTHS[m[2].lower()], int(m[1]))
            return interval(day, day, "exact")
        month = re.fullmatch(r"(\d{4})-(\d{2})", value)
        named = re.search(r"\b([A-Za-z]+)\s+(\d{4})\b", value)
        year = mon = None
        if month:
            year, mon = int(month[1]), int(month[2])
        elif named and named[1].lower() in MONTHS:
            year, mon = int(named[2]), MONTHS[named[1].lower()]
        if year is not None:
            return interval(date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1]),
                            "month")
        if reference:
            ref = date.fromisoformat(str(reference)[:10])
            lower = value.casefold()
            if "yesterday" in lower:
                day = ref - timedelta(days=1)
                return interval(day, day, "relative")
            if "last week" in lower:
                end = ref - timedelta(days=ref.weekday() + 1)
                return interval(end - timedelta(days=6), end, "week")
            for weekday, name in enumerate(calendar.day_name):
                if re.search(r"\b" + name.lower() + r"\b", lower):
                    day = ref - timedelta(days=(ref.weekday() - weekday) % 7)
                    return interval(day, day, "relative")
    except (ValueError, OverflowError):
        result["warning"] = "invalid_date"
    return result


class LocalGazetteer:
    def __init__(self, rows):
        self.rows = rows
        by_id = {r["id"]: r for r in rows}
        if len(by_id) != len(rows):
            raise ValueError("Duplicate gazetteer IDs")
        for row in rows:
            check_geometry(row.get("geometry"))
            parent = row.get("parent_id")
            if parent and parent in by_id and row.get("country") != by_id[parent].get("country"):
                raise ValueError("Gazetteer parent and child country conflict")
            seen = {row["id"]}
            while parent:
                if parent not in by_id or parent in seen:
                    raise ValueError("Gazetteer has missing parent or cycle")
                seen.add(parent)
                parent = by_id[parent].get("parent_id")
            if (row.get("geometry") or {}).get("type") == "Point" and row.get("level") in {
                "country", "region", "district", "subdistrict", "city"
            } and not row.get("representational"):
                raise ValueError("Administrative/settlement point must be representational")

    def candidates(self, text, country=""):
        matches = []
        for row in self.rows:
            if country and row.get("country", "").casefold() != country.casefold():
                continue
            names = [row["name"], *row.get("aliases", [])]
            lengths = [len(n) for n in names if re.search(
                r"(?<!\w)" + re.escape(n) + r"(?!\w)", text, re.IGNORECASE)]
            if lengths:
                matches.append((max(lengths), row))
        if not matches:
            return []
        longest = max(x[0] for x in matches)
        return [x[1] for x in matches if x[0] == longest]

    def resolve(self, record, statement):
        if record.geometry:
            return [{"id": stable_id("place", record.source_id, record.source_record_id),
                     "name": record.location_text or record.title,
                     "parent_id": None, "country": record.country, "geometry": record.geometry,
                     "level": record.geometry_role,
                     "representational": record.geometry_role != "source_point"
                     and record.geometry_role != "area", "selected": True,
                     "confidence": None, "method": "source-geometry-v1"}]
        matches = self.candidates(record.location_text or statement, record.country)
        return [{**r, "selected": len(matches) == 1, "confidence": None,
                 "method": "gazetteer-exact-candidates-v1"} for r in matches]


def extract(record, taxonomy):
    text = normalized(record.text)
    spans = []
    offset = 0
    for part in re.split(r"(?<=[.!?।])\s+(?=[A-Zঅ-ঔক-হ])", text):
        start = text.find(part, offset)
        offset = start + len(part)
        spans.append((start, offset, part))
    if record.category:
        if record.category not in taxonomy:
            raise ValueError(f"category is absent from configured taxonomy: {record.category}")
        spans = [(0, len(text), text)]
    claims = []
    for start, end, part in spans:
        categories = [record.category] if record.category else [
            k for k, terms in taxonomy.items() if any(
                re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", part, re.IGNORECASE) for t in terms)]
        for cat in categories:
            negated = bool(re.search(r"\b(no|not|never|without)\b|হয়নি|হয়নি", part, re.IGNORECASE))
            speculative = bool(re.search(r"\b(may|might|could|forecast|risk|warning|expected)\b",
                                         part, re.IGNORECASE))
            claims.append({"statement": part, "category": cat, "span_start": start,
                           "span_end": end, "extraction_confidence":
                           1.0 if record.category else 0.65,
                           "method": "structured-field-v1" if record.category else "keyword-v1",
                           "polarity": "negated" if negated else (
                               "hypothetical" if speculative else "reported")})
    return text, claims


def extract_quantities(text):
    result = []
    for match in re.finditer(r"(?P<approx>nearly |about |approximately )?(?P<value>\d+(?:\.\d+)?)\s+"
                             r"(?P<unit>people|households|houses|feet|meters|metres|kilometers|hectares)\b",
                             text.translate(DIGITS), re.IGNORECASE):
        unit = match["unit"].casefold()
        result.append({"kind": "count" if unit in {"people", "households", "houses"} else "measurement",
                       "value": float(match["value"]), "unit": unit,
                       "approximate": bool(match["approx"]), "method": "quantity-pattern-v1",
                       "span_start": match.start(), "span_end": match.end(),
                       "note": "Mentioned value only; affected population or measurement role is not inferred."})
    return result
