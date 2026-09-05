import json

from backend.app.config import settings, FailureCategory


def diagnose_with_llm(event, rule_category: FailureCategory, rule_confidence: float) -> tuple[FailureCategory, float, str]:
    """Optional LLM fallback. Only called when enabled and rule confidence is low.
    Any failure silently falls back to the rule-based result.
    """
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        system = (
            "You are a payment failure root-cause classifier. Return ONLY JSON of the "
            'form {"category": "<one of soft_decline|hard_decline|insufficient_funds|'
            'gateway_error|genuine_abandonment|mandate_expiry|willful_non_payment>", '
            '"confidence": <float 0-1>}. No other text.'
        )
        user_content = json.dumps({
            "event_type": event.event_type,
            "decline_code": event.decline_code,
            "gateway_error": event.gateway_error,
            "context": event.context,
        })
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        parsed = json.loads(text)
        category = FailureCategory(parsed["category"])
        confidence = float(parsed["confidence"])
        return category, confidence, "llm"
    except Exception:
        return rule_category, rule_confidence, "rule_based"