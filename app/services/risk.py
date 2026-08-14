from typing import Any
import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def analyze_risk(text: str) -> dict[str, Any]:
    text = normalize(text)

    patterns = {
        "upfront_payment": [
            "pay to apply",
            "application fee",
            "registration fee",
            "training fee",
            "pay for training",
            "pay a fee",
            "payment required to apply",
            "payment required before applying",
        ],

        "unpaid": [
            "unpaid position",
            "unpaid role",
            "unpaid internship",
            "work without pay",
            "no salary",
            "without compensation",
        ],

        "commission_only": [
            "commission only",
            "100% commission",
            "commission-based only",
            "commission based only",
        ],

        "messaging_app_only": [
            # WhatsApp
            "apply via whatsapp",
            "apply through whatsapp",
            "apply on whatsapp",
            "contact us on whatsapp",
            "contact us via whatsapp",
            "contact us through whatsapp",
            "contact the recruiter on whatsapp",
            "contact the recruiter via whatsapp",
            "contact the recruiter through whatsapp",
            "whatsapp to apply",
            "whatsapp application",

            # Telegram
            "apply via telegram",
            "apply through telegram",
            "apply on telegram",
            "contact us on telegram",
            "contact us via telegram",
            "contact us through telegram",
            "contact the recruiter on telegram",
            "contact the recruiter via telegram",
            "contact the recruiter through telegram",
            "telegram to apply",
            "telegram application",
        ],
    }

    detected = []

    for category, phrases in patterns.items():
        if any(
            phrase in text
            for phrase in phrases
        ):
            detected.append(category)

    severity = "low"

    if "upfront_payment" in detected:
        severity = "critical"

    elif "unpaid" in detected:
        severity = "critical"

    elif "messaging_app_only" in detected:
        severity = "high"

    elif "commission_only" in detected:
        severity = "medium"

    return {
        "severity": severity,
        "flags": detected,
    }