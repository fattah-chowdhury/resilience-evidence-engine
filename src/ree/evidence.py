"""Separate evidence dimensions; grades are rules, never probabilities."""


def assess(claim, source, location, time, independent_groups, rules, verified=False, rejected=False):
    precise = bool(location and location.get("geometry") and
                   not location.get("representational") and location.get("level") in {
                       "source_point", "area"})
    exact_time = time["precision"] == "exact" or (
        rules["allow_auto_accept_relative"] and time["precision"] == "relative")
    reasons = []
    if not location:
        reasons.append("ambiguous_or_unknown_location")
    elif not location.get("geometry"):
        reasons.append("location_without_geometry")
    elif not precise:
        reasons.append("representational_or_unknown_geometry")
    if not exact_time:
        reasons.append(time.get("warning") or "uncertain_event_date")
    if claim["extraction_confidence"] < rules["auto_accept_min_extraction"]:
        reasons.append("keyword_extraction_needs_review")
    if claim.get("acquisition_kind") == "curated_factual_transcription":
        reasons.append("curated_source_transcription")
    if source.get("origin_group") is None:
        reasons.append("source_independence_unknown")
    if claim["polarity"] == "hypothetical":
        reasons.append("hypothetical_or_forecast")
    reasons.extend(claim.get("conflicts", []))
    if rejected or claim["polarity"] == "negated":
        grade, decision = "X", "REJECT"
    elif verified and precise and exact_time and independent_groups >= rules["grade_a_min_independent_groups"]:
        grade, decision = "A", "AUTO_ACCEPT"
    elif precise and exact_time and (verified or not reasons):
        grade, decision = "B", "AUTO_ACCEPT" if not reasons or verified else "REVIEW"
    elif time["start"] and location:
        grade, decision = "C", "REVIEW"
    else:
        grade, decision = "D", "REVIEW"
    return {"grade": grade, "decision": decision, "reasons": sorted(set(reasons)),
            "indicators": {"source_characteristics": source.get("status"),
                           "spatial_precision": location.get("level") if location else "unresolved",
                           "representational": location.get("representational") if location else None,
                           "temporal_precision": time["precision"],
                           "claim_specificity": "structured" if claim["method"] == "structured-field-v1" else "keyword",
                           "extraction_confidence": claim["extraction_confidence"],
                           "extraction_confidence_kind": "heuristic, not calibrated",
                           "corroboration_independent_groups": independent_groups,
                           "verification_state": "rejected" if rejected else (
                               "human_accepted" if verified else "unreviewed"),
                           "polarity": claim["polarity"]}}
