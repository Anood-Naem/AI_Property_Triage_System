# Layer 4 — optional local LLM (RAG insight)

Place a GGUF file here for richer RAG insights (optional). Example name used by compose:

`qwen2.5-1.5b-instruct-q4_k_m.gguf`

Set in `.env`:

```env
GGUF_MODEL_PATH=/models/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

If empty or missing, RAG still works with retrieval + template insight. Do not commit `.gguf` files to git.
