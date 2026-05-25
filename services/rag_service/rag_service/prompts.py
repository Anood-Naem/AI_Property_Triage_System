"""RAG prompt templates for insight generation."""

RAG_INSIGHT_PROMPT = """You are a real estate market analyst. Use ONLY the retrieved listing context below.
Do NOT invent prices, locations, or features not present in the context.
If similarity is weak (scores below 0.5), state that clearly.

Retrieved listings:
{context}

User listing description:
{description}

Instructions:
1. Cite listing IDs when referencing similar properties.
2. Explain why each listing is similar (location, type, price band, features).
3. Provide a concise market insight (2-4 sentences).
4. If context is insufficient, say "Similarity is limited based on available data."

Insight:"""

RAG_MOCK_INSIGHT_TEMPLATE = """Based on retrieved listings {ids} (similarity scores: {scores}), 
the submitted property appears comparable to past listings in {locations}. 
Key shared features include: {features}. 
Note: This insight uses retrieval-only context; verify all facts against the original listing text."""
