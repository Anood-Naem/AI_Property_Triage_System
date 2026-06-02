# n8n workflow import guide

Workflow file:

- `ai_property_triage_workflow.json`

## Import steps

1. Open n8n.
2. Import the JSON file.
3. Re-select credentials for all LLM nodes (Gemini/OpenAI) in your own n8n account.
4. Verify URLs:
   - If n8n runs in Docker, keep `host.docker.internal:8001-8004` as configured.
   - If n8n runs directly on host, change service URLs to `http://localhost:8001` ... `8004`.
5. Activate workflow.

## Expected webhook path

`/webhook/ai-property-analysis`

Set WebUI `N8N_WEBHOOK_URL` accordingly.
