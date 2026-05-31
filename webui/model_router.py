import json
import re

from groq import Groq

from config import GROQ_TEXT_MODEL, get_groq_api_key


ROUTER_SYSTEM_PROMPT = """
You are an intelligent routing and context classifier for an AI real estate assistant.

Your job is to understand the user's real intention from the full message.
Do NOT rely on exact keywords.

You must decide:

1. route:
- "groq" for normal assistant answers, listing improvement, report explanation, image analysis,
  or anything that does not require fresh/current web information.
- "sonar" ONLY when the user needs fresh/current web information, such as current prices,
  current market comparison, latest market trends, mortgage rates, regulations, news, or fresh statistics.

2. use_current_report:
Use true when the user refers to the currently generated report/listing/result, for example:
- the report I received
- this report
- the current analysis
- the listing I just submitted
- the property report shown on the page
- compare this report to the market

Only set true if there is a current report available.

3. use_knowledgebase:
Use true when the user needs saved/past/internal reports from the Knowledge Base, for example:
- compare with previous reports
- find similar saved reports
- use reports already stored in the system
- compare this property with past analyzed listings
- check whether we analyzed something similar before

Do NOT use Knowledge Base when:
- the user only says hello or thanks
- the user asks to improve wording only
- the user asks general real estate advice
- the user only asks about the uploaded image
- the user only asks for current market data and does not need saved reports
- the user asks something unrelated to saved/internal reports

Important:
If the user asks to compare the current report with today's market:
- route = "sonar"
- use_current_report = true
- use_knowledgebase = false, unless the user also asks about previous/saved reports.

If the user asks to compare the current report with saved/past reports:
- route = "groq"
- use_current_report = true
- use_knowledgebase = true.

If the user asks to compare current report with both saved reports and today's market:
- route = "sonar"
- use_current_report = true
- use_knowledgebase = true.

Return ONLY valid JSON in this exact structure:
{
  "route": "groq",
  "use_current_report": false,
  "use_knowledgebase": false,
  "knowledgebase_query": "",
  "confidence": 0.0,
  "reason": "short reason"
}
"""


def get_router_client():
    api_key = get_groq_api_key()

    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY. Add it to your .env file.")

    return Groq(api_key=api_key)


def default_decision(reason="Default route."):
    return {
        "route": "groq",
        "use_current_report": False,
        "use_knowledgebase": False,
        "knowledgebase_query": "",
        "confidence": 0.0,
        "reason": reason,
    }


def extract_json(text):
    text = (text or "").strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("No JSON object found.")

    return json.loads(match.group(0))


def to_bool(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in ("true", "yes", "1")


def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def classify_assistant_request(
    user_text: str,
    has_images: bool = False,
    has_current_report: bool = False,
) -> dict:
    user_text = (user_text or "").strip()

    if not user_text:
        return default_decision("Empty user message.")

    try:
        client = get_router_client()

        router_input = f"""
User message:
{user_text}

Has uploaded images:
{has_images}

Is there a current generated report available in Streamlit session:
{has_current_report}
"""

        response = client.chat.completions.create(
            model=GROQ_TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": ROUTER_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": router_input,
                },
            ],
            temperature=0,
            max_completion_tokens=250,
        )

        raw_content = response.choices[0].message.content
        decision = extract_json(raw_content)

        route = str(decision.get("route", "groq")).strip().lower()

        if route not in ("groq", "sonar"):
            route = "groq"

        use_current_report = to_bool(decision.get("use_current_report", False))
        use_knowledgebase = to_bool(decision.get("use_knowledgebase", False))

        if use_current_report and not has_current_report:
            use_current_report = False

        knowledgebase_query = str(
            decision.get("knowledgebase_query") or user_text
        ).strip()

        return {
            "route": route,
            "use_current_report": use_current_report,
            "use_knowledgebase": use_knowledgebase,
            "knowledgebase_query": knowledgebase_query,
            "confidence": to_float(decision.get("confidence", 0.0)),
            "reason": str(decision.get("reason", "")),
        }

    except Exception as error:
        return default_decision(f"Router error: {error}")


def choose_assistant_route(user_text: str, has_images: bool = False) -> str:
    decision = classify_assistant_request(
        user_text=user_text,
        has_images=has_images,
        has_current_report=False,
    )

    return decision["route"]