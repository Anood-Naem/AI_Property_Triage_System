# LangGraph Agent Service

Three-node LangGraph workflow: planner → tool execution → synthesiser.

## Endpoint

`POST /agent/run`

```json
{
  "query": "What renovation work is needed to bring the property to condition score 5?",
  "description": "3-room apartment in Haifa...",
  "image_urls": ["https://example.com/kitchen_good.jpg"]
}
```

## Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8004
```

## Test

```bash
curl -X POST http://localhost:8004/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which rooms need attention and how does this compare to similar listings?",
    "description": "Beautiful 3-room apartment in Haifa with renovated kitchen. Price 1,850,000 ILS.",
    "image_urls": [
      "https://example.com/kitchen_good.jpg",
      "https://example.com/bathroom_needs_renovation.jpg"
    ]
  }'
```
