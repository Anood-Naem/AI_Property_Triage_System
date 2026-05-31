# LangGraph Agent Service

Three-node LangGraph workflow: planner → tool execution → synthesiser.

## Endpoint

`POST /agent/run`

### URLs only

```json
{
  "query": "Which rooms need attention?",
  "description": "3-room apartment in Haifa...",
  "image_urls": ["https://example.com/kitchen_good.jpg"]
}
```

### URLs + PC upload (base64)

```json
{
  "query": "Which rooms need attention?",
  "description": "3-room apartment in Haifa...",
  "image_urls": ["https://example.com/kitchen_good.jpg"],
  "images": [
    {
      "image_base64": "<base64>",
      "mime_type": "image/jpeg",
      "filename": "bathroom.jpg"
    }
  ]
}
```

Uploads are forwarded to the image service (`/analyse/batch`). Max **20** images total (`image_urls` + `images`).

## Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8004
```

## Test

```bash
curl -X POST http://localhost:8004/agent/run \
  -H "Content-Type: application/json" \
  -d '{"query":"Which rooms need attention?","description":"Apartment in Haifa.","image_urls":["https://example.com/kitchen_good.jpg"]}'
```
