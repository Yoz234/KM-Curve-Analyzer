"""
LLM-based extraction of KM curve data and HR values from images/text.
Supports OpenAI (gpt-4o), Anthropic (claude-sonnet-4-6), Google (gemini-2.0-flash).
"""

import base64
import json
import re
import os
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Prompts (shared across providers)
# ---------------------------------------------------------------------------

KM_EXTRACTION_SYSTEM = (
    "You are a biostatistics expert specializing in digitizing Kaplan-Meier "
    "survival curves from scientific figures. "
    "Always respond with valid JSON only — no prose, no markdown code blocks."
)

KM_EXTRACTION_PROMPT = """Analyze this Kaplan-Meier survival curve image and extract all data.

Return a JSON object with EXACTLY this structure:
{
  "groups": [
    {
      "name": "<group label from legend>",
      "color_description": "<color/line style>",
      "curve_points": [
        {"time": <number>, "survival": <number 0-1>},
        ...
      ],
      "at_risk_table": [
        {"time": <number>, "n_at_risk": <integer>},
        ...
      ],
      "censor_marks": [<time>, ...]
    }
  ],
  "x_axis": {
    "label": "<axis label e.g. Time (months)>",
    "min": <number>,
    "max": <number>,
    "unit": "<months|years|days|weeks>"
  },
  "y_axis": {
    "label": "<axis label>",
    "is_percentage": <true if 0-100 scale, false if 0-1 scale>
  },
  "title": "<figure title if visible>",
  "n_groups": <integer>,
  "extraction_notes": "<any caveats or uncertainties>"
}

Rules:
1. Extract AT LEAST 10 curve_points per group, capturing all visible inflections.
2. If survival is shown as percentage (0-100), convert to proportion (0-1).
3. For at_risk_table: extract ALL rows shown below the figure. If absent, return [].
4. Time 0 must always be included with survival = 1.0.
5. censor_marks: list the time values of tick marks (censored observations).
6. Multi-panel figures: if the figure contains multiple panels (labeled a/b/c/d, i/ii/iii,
   or with separate titles), treat EACH panel as a separate set of groups — do NOT merge
   curves across panels even if they share the same legend label (e.g. "Placebo" in panel a
   and "Placebo" in panel c are DIFFERENT groups). Prefix every group name with its panel
   label using " — " as separator: "a — Placebo", "a — Regorafenib", "b — Placebo", etc.
7. Single-panel with subgroups: if a single panel shows curves for different subpopulations
   or arms (e.g. "PD-L1 high Treatment", "PD-L1 high Control", "PD-L1 low Treatment"),
   prefix each name with its subgroup category: "PD-L1 high — Treatment", etc.
8. Be precise: read coordinates as carefully as possible."""

HR_EXTRACTION_SYSTEM = (
    "You are a biostatistics expert extracting hazard ratios and statistical "
    "results from biomedical article text or figures. "
    "Always respond with valid JSON only."
)

HR_EXTRACTION_PROMPT = """Extract hazard ratio information from this content.

Return a JSON object with EXACTLY this structure:
{
  "comparisons": [
    {
      "treatment": "<treatment arm name>",
      "reference": "<reference/control arm name>",
      "hazard_ratio": <number or null>,
      "ci_lower": <number or null>,
      "ci_upper": <number or null>,
      "p_value": <number or null>,
      "endpoint": "<e.g. Overall Survival, PFS>",
      "source": "<figure number or section>"
    }
  ],
  "extraction_notes": "<uncertainties or missing data>"
}

Rules:
1. Extract ALL hazard ratios mentioned.
2. p-values: extract exact values if available.
3. If HR is not explicitly stated, return null for that field."""

# ---------------------------------------------------------------------------
# Provider defaults
# ---------------------------------------------------------------------------

PROVIDER_MODELS = {
    "openai":     "gpt-4o",
    "anthropic":  "claude-sonnet-4-6",
    "google":     "gemini-2.0-flash",
}


def _parse_json_response(text: str) -> Dict[str, Any]:
    """Strip any accidental markdown wrappers and parse JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _encode_image(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


# ---------------------------------------------------------------------------
# Provider-specific clients
# ---------------------------------------------------------------------------

def _call_openai(
    image_bytes: bytes,
    media_type: str,
    prompt: str,
    system: str,
    api_key: str,
    model: str,
) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    b64 = _encode_image(image_bytes)
    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ],
    )
    return response.choices[0].message.content


def _call_openai_text(
    text: str,
    prompt: str,
    system: str,
    api_key: str,
    model: str,
) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"{prompt}\n\n---\nContent:\n{text}"},
        ],
    )
    return response.choices[0].message.content


def _call_anthropic(
    image_bytes: bytes,
    media_type: str,
    prompt: str,
    system: str,
    api_key: str,
    model: str,
) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    b64 = _encode_image(image_bytes)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return response.content[0].text


def _call_anthropic_text(
    text: str,
    prompt: str,
    system: str,
    api_key: str,
    model: str,
) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[
            {"role": "user", "content": f"{prompt}\n\n---\nContent:\n{text}"}
        ],
    )
    return response.content[0].text


def _call_google(
    image_bytes: bytes,
    media_type: str,
    prompt: str,
    system: str,
    api_key: str,
    model: str,
) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=media_type),
            f"{system}\n\n{prompt}",
        ],
    )
    return response.text


def _call_google_text(
    text: str,
    prompt: str,
    system: str,
    api_key: str,
    model: str,
) -> str:
    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=f"{system}\n\n{prompt}\n\n---\nContent:\n{text}",
    )
    return response.text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_km_from_image(
    image_bytes: bytes,
    media_type: str = "image/png",
    provider: str = "openai",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract KM curve data from an image using the specified LLM provider.

    Args:
        image_bytes: Raw image bytes
        media_type:  MIME type (image/png, image/jpeg, etc.)
        provider:    "openai" | "anthropic" | "google"
        api_key:     Provider API key (falls back to env var if None)
    """
    key, model = _resolve_key_and_model(provider, api_key)

    if provider == "openai":
        raw = _call_openai(image_bytes, media_type, KM_EXTRACTION_PROMPT,
                           KM_EXTRACTION_SYSTEM, key, model)
    elif provider == "anthropic":
        raw = _call_anthropic(image_bytes, media_type, KM_EXTRACTION_PROMPT,
                              KM_EXTRACTION_SYSTEM, key, model)
    elif provider == "google":
        raw = _call_google(image_bytes, media_type, KM_EXTRACTION_PROMPT,
                           KM_EXTRACTION_SYSTEM, key, model)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use openai, anthropic, or google.")

    result = _parse_json_response(raw)

    # Normalise survival values to [0,1]
    for group in result.get("groups", []):
        if result.get("y_axis", {}).get("is_percentage", False):
            for pt in group.get("curve_points", []):
                if pt["survival"] > 1.0:
                    pt["survival"] = pt["survival"] / 100.0

    return result


def extract_hr_from_text(
    text: str,
    provider: str = "openai",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract HR and CI values from article text."""
    key, model = _resolve_key_and_model(provider, api_key)

    if provider == "openai":
        raw = _call_openai_text(text, HR_EXTRACTION_PROMPT,
                                HR_EXTRACTION_SYSTEM, key, model)
    elif provider == "anthropic":
        raw = _call_anthropic_text(text, HR_EXTRACTION_PROMPT,
                                   HR_EXTRACTION_SYSTEM, key, model)
    elif provider == "google":
        raw = _call_google_text(text, HR_EXTRACTION_PROMPT,
                                HR_EXTRACTION_SYSTEM, key, model)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return _parse_json_response(raw)


def extraction_to_ipd_inputs(extraction: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert LLM extraction output to inputs for ipd_reconstruction."""
    groups_out = []
    for g in extraction.get("groups", []):
        pts = [(float(p["time"]), float(p["survival"]))
               for p in g.get("curve_points", [])]
        risk = [(float(r["time"]), int(r["n_at_risk"]))
                for r in g.get("at_risk_table", [])]
        n_total = int(risk[0][1]) if risk else None
        groups_out.append({
            "name": g.get("name", "Unknown"),
            "curve_points": pts,
            "at_risk_table": risk if risk else None,
            "n_total": n_total,
        })

    # For groups missing both at_risk_table and n_total, fill in a fallback
    # so IPD reconstruction doesn't fail on figures without at-risk tables.
    # Priority 1: largest n_total seen across sibling groups (same trial).
    # Priority 2: estimate from the first survival drop in the curve itself.
    max_n = max((g["n_total"] for g in groups_out if g["n_total"] is not None), default=None)
    for g in groups_out:
        if g["n_total"] is not None:
            continue
        if max_n is not None:
            g["n_total"] = max_n
        else:
            # Estimate: S(t1) ≈ (n-1)/n  →  n ≈ 1/(1-S(t1))
            pts = g["curve_points"]
            for i in range(len(pts) - 1):
                s0, s1 = pts[i][1], pts[i + 1][1]
                if s0 > s1 > 0 and s0 - s1 > 0.001:
                    g["n_total"] = max(10, round(s0 / (s0 - s1)))
                    break

    return groups_out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ENV_KEYS = {
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google":    "GOOGLE_API_KEY",
}


def _resolve_key_and_model(
    provider: str,
    api_key: Optional[str],
) -> tuple[str, str]:
    """Return (api_key, model). Raise if key not available."""
    key = api_key or os.environ.get(_ENV_KEYS.get(provider, ""), "")
    if not key:
        env_var = _ENV_KEYS.get(provider, "")
        raise ValueError(
            f"No API key for provider '{provider}'. "
            f"Enter it in the UI or set the {env_var} environment variable."
        )
    model = PROVIDER_MODELS[provider]
    return key, model
