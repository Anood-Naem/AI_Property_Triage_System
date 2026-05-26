from groq import Groq

from config import GROQ_TEXT_MODEL, get_groq_api_key


ROUTER_SYSTEM_PROMPT = """
You are a routing classifier for an AI real estate assistant.

Your job is to decide which service should answer the user's message.

Available routes:

1. groq
Use this for:
- normal text chat
- improving property listings
- rewriting descriptions
- explaining real estate concepts
- analyzing property descriptions
- analyzing uploaded property images when no fresh web data is needed
- general real-estate assistant answers
- anything that does NOT require fresh internet data

2. sonar
Use this ONLY when the user needs real-time or current web information, such as:
- current property prices
- latest market trends
- today's mortgage rates
- recent real estate news
- updated regulations
- fresh statistics
- anything likely to change over time

Important image rule:
- If the user uploaded an image but only asks to analyze the image, route to groq.
- If the user uploaded an image and asks for current prices, latest trends, current market comparison,
  recent regulations, or any real-time information based on the image, route to sonar.

Examples:
- "Improve this listing" -> groq
- "Analyze this uploaded apartment image" -> groq
- "What is the condition of this kitchen?" -> groq
- "What are current apartment prices in Tel Aviv?" -> sonar
- "What are the latest real estate trends in Haifa?" -> sonar
- "Based on this apartment image, how much do similar apartments cost today?" -> sonar
- "לפי התמונה הזאת, כמה נכסים דומים עולים היום בחיפה?" -> sonar

Return only one word:
groq
or
sonar

If unsure, return groq.
"""


def get_router_client():
    api_key = get_groq_api_key()

    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY. Add it to your .env file.")

    return Groq(api_key=api_key)


def choose_assistant_route(user_text: str, has_images: bool = False) -> str:
    user_text = (user_text or "").strip()

    if not user_text:
        return "groq"

    try:
        client = get_router_client()

        router_input = f"""
User message:
{user_text}

Has uploaded images:
{has_images}
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
            max_completion_tokens=5,
        )

        route = response.choices[0].message.content.strip().lower()

        if "sonar" in route:
            return "sonar"

        return "groq"

    except Exception:
        return "groq"