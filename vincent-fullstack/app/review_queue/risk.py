import re

HIGH_STAKES_FIELDS = {"amount", "total", "due_date", "signee", "account_number", "tax_id"}
CONFIDENCE_LOW = 0.5
CONFIDENCE_MEDIUM = 0.8


def assess_risk(doc_type: str, content: str, extracted_fields: dict, extraction_confidence: dict):
    flags = []
    extracted_fields = extracted_fields or {}
    extraction_confidence = extraction_confidence or {}

    for field_name, confidence in extraction_confidence.items():
        if confidence < CONFIDENCE_LOW:
            severity = "high" if field_name in HIGH_STAKES_FIELDS else "medium"
            flags.append({
                "field": field_name,
                "issue": f"Low extraction confidence ({confidence:.0%})",
                "severity": severity,
            })
        elif confidence < CONFIDENCE_MEDIUM and field_name in HIGH_STAKES_FIELDS:
            flags.append({
                "field": field_name,
                "issue": f"Moderate confidence ({confidence:.0%}) on a high-stakes field",
                "severity": "medium",
            })

    for field_name in HIGH_STAKES_FIELDS:
        if field_name in extraction_confidence and field_name not in extracted_fields:
            flags.append({
                "field": field_name,
                "issue": "Expected field is missing from extraction",
                "severity": "high",
            })

    for field_name in ("amount", "total"):
        value = extracted_fields.get(field_name)
        if value:
            cleaned = re.sub(r"[^\d.]", "", str(value))
            try:
                amount = float(cleaned) if cleaned else None
            except ValueError:
                amount = None
            if amount is None:
                flags.append({"field": field_name, "issue": "Amount is not a parseable number", "severity": "high"})
            elif amount <= 0:
                flags.append({"field": field_name, "issue": "Amount is zero or negative", "severity": "high"})

    if doc_type in ("invoice", "contract") and len(content) < 40:
        flags.append({"issue": "Content unusually short for this document type", "severity": "medium"})

    if any(f["severity"] == "high" for f in flags):
        level = "high"
    elif any(f["severity"] == "medium" for f in flags):
        level = "medium"
    else:
        level = "low"

    return level, flags
