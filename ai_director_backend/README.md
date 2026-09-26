# AI Director backend

Local planner. **Groq** turns the prompt into SceneIR. **Poly Haven** supplies CC0 GLBs/HDRIs. Without `GROQ_API_KEY`, the API returns bundled domain fixtures.

```
cd ai_director_backend
pip install -r requirements.txt
set GROQ_API_KEY=your_key
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`POST /v1/scenes` `{ "prompt": "a park at dusk", "domain": "auto" }`

In the Blender addon: uncheck **Use bundled fixture (offline)** so Generate calls this API.

# Blender addon

In Blender 4.2+: Edit → Preferences → Extensions / Add-ons → Install from disk → this repo folder (`ai_director_addon` containing `blender_manifest.toml`).

N-panel **AI Director**:
1. Domain (Auto, Interior, Park, Forest, City, Zoo, Space, Beach, Generic)
2. Prompt
3. Generate Scene

Preferences: keep **Use bundled fixture (offline)** on. No Groq key. No `exec`.
