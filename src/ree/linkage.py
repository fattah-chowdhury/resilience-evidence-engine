"""Conservative identity linkage. Similarity alone only proposes a review."""

import math
from datetime import date
from difflib import SequenceMatcher

from ree.models import canonical, digest
from ree.storage import stable_id


def distance_km(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, [*a, *b])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))


def group_claims(claims, sources, days, km, link_decisions=None, excluded_claim_ids=None):
    link_decisions = link_decisions or []
    excluded_claim_ids = excluded_claim_ids or set()
    groups = {}
    for c in claims:
        source = sources[c["source_id"]]
        if c.get("provider_event_id"):
            key = ("provider-key", source.get("origin_group") or c["source_id"],
                   c["provider_event_id"], c["category"])
        else:
            # A copied sentence does not demonstrate that events are identical.
            key = ("unlinked", c["claim_id"])
        c["event_id"] = stable_id("event", *key)
        c["origin_event_id"] = c["event_id"]
        c["link_method"] = key[0]
        groups.setdefault(c["event_id"], []).append(c)
    parents = {event_id: event_id for event_id in groups}
    aliases = {event_id: [event_id] for event_id in groups}

    def representative(event_id):
        while parents[event_id] != event_id:
            event_id = parents[event_id]
        return event_id

    for decision in link_decisions:
        left, right = decision["left_event_id"], decision["right_event_id"]
        if left not in aliases or right not in aliases:
            raise ValueError("Event-link decision refers to an event absent from the replay")
        if groups[aliases[left][0]][0]["category"] != groups[aliases[right][0]][0]["category"]:
            raise ValueError("Different event categories cannot be merged")
        if decision["decision"] == "accepted":
            a, b = representative(aliases[left][0]), representative(aliases[right][0])
            parents[max(a, b)] = min(a, b)
            members = sorted(event_id for event_id in groups if representative(event_id) == min(a, b))
            aliases[stable_id("event", "human-reviewed-merge", *members)] = members
    components = {}
    for event_id in groups:
        components.setdefault(representative(event_id), []).append(event_id)
    merged = {}
    for members in components.values():
        new_id = members[0] if len(members) == 1 else stable_id("event", "human-reviewed-merge", *sorted(members))
        retained = [claim for old_id in members for claim in groups[old_id]
                    if claim["claim_id"] not in excluded_claim_ids]
        if not retained:
            continue
        merged[new_id] = retained
        for claim in merged[new_id]:
            claim["event_id"] = new_id
            claim["link_decisions"] = [d for d in link_decisions if set(members) &
                                       (set(aliases[d["left_event_id"]]) | set(aliases[d["right_event_id"]]))]
            if len(members) > 1:
                claim["link_method"] = "human-reviewed-merge"
    groups = merged
    for group in groups.values():
        groups_seen = set()
        texts_seen = set()
        prior_texts = []
        for c in sorted(group, key=lambda x: x["claim_id"]):
            text_hash = digest(c["statement"].casefold())
            near_copy = any(min(len(t), len(c["statement"])) >= 50 and
                            SequenceMatcher(None, t, c["statement"].casefold()).ratio() >= 0.95
                            for t in prior_texts)
            if text_hash not in texts_seen and not near_copy:
                origin = sources[c["source_id"]].get("origin_group")
                if origin:
                    groups_seen.add(origin)
            texts_seen.add(text_hash)
            prior_texts.append(c["statement"].casefold())
        for c in group:
            c["independent_groups"] = len(groups_seen)
            c["conflicts"] = []
        exact_days = {c["time"]["start"] for c in group if c["time"]["precision"] in {"exact", "relative"}}
        quantities = {}
        for c in group:
            for q in c["quantities"]:
                quantities.setdefault((q.get("kind"), q.get("unit")), set()).add(canonical(q.get("value")))
        conflicts = []
        geometries = {canonical(c["selected_location"]["geometry"]) for c in group
                      if c.get("selected_location") and c["selected_location"].get("geometry")}
        if len(geometries) > 1:
            conflicts.append("conflicting_locations")
        if len(exact_days) > 1:
            conflicts.append("conflicting_dates")
        if any(len(values) > 1 for values in quantities.values()):
            conflicts.append("conflicting_quantities")
        for c in group:
            c["conflicts"] = conflicts.copy()
    proposals = []
    rejected_pairs = {frozenset((d["left_event_id"], d["right_event_id"])) for d in link_decisions
                      if d["decision"] == "rejected"}
    # Block by category. This first release caps records and is intended for small studies.
    representatives = [min(g, key=lambda c: c["claim_id"]) for g in groups.values()]
    for i, a in enumerate(representatives):
        for b in representatives[i + 1:]:
            if a["category"] != b["category"] or not a["time"]["start"] or not b["time"]["start"]:
                continue
            if abs((date.fromisoformat(a["time"]["start"]) - date.fromisoformat(b["time"]["start"])).days) > days:
                continue
            la, lb = a.get("selected_location"), b.get("selected_location")
            if not la or not lb:
                continue
            close = la["id"] == lb["id"]
            ga, gb = la.get("geometry"), lb.get("geometry")
            if ga and gb and ga["type"] == gb["type"] == "Point":
                close = distance_km(ga["coordinates"], gb["coordinates"]) <= km
            if close and frozenset((a["event_id"], b["event_id"])) not in rejected_pairs:
                proposals.append({"left_event_id": a["event_id"], "right_event_id": b["event_id"],
                                  "status": "pending", "reason": "nearby_same_category_and_time",
                                  "text_similarity": round(SequenceMatcher(None, a["statement"], b["statement"]).ratio(), 4)})
    return groups, proposals
