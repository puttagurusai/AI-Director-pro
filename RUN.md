# How to run AI Director

You need **Blender 4.2+** (5.1 works). Groq + Poly Haven are optional for the first test.

Repo folder:

`C:\me\proj\ai_director_addon`

---

## A. Offline (no API keys) — try this first

You get a greybox scene for the Domain you pick (park, space, city, …). The prompt does **not** change the layout yet.

### 1. Install the addon (use the ZIP, not the folder)

Blender **Install from Disk** unpacks an archive. A folder path like `C:\me\proj\ai_director_addon\` causes:

`Error extracting archive: [Errno 2] No such file or directory`

Use the zip that is already built:

`C:\me\proj\ai_director_addon\ai_director.zip`

1. Open Blender.
2. **Edit → Preferences → Get Extensions** (or **Add-ons**).
3. Click the drop-down **∨** at the top-right → **Install from Disk…**
4. Select **`ai_director.zip`** (not the folder, not `ai_director_backend`).
5. Enable **AI Director**. Allow **Network** if asked.

Rebuild the zip after code changes:

```powershell
python C:\me\proj\ai_director_addon\pack_addon.py
```

Then install the new zip again (or disable, remove, reinstall).

### 2. N-panel only has **Offline**

3D View → **N** → **AI Director**. Check **Offline** (default). No API URL field, no Poly Haven key field.

**Poly Haven does not use an API key.** It is a public CC0 API. When Offline is **unchecked**, the local server talks to Poly Haven automatically.

**Groq** (the LLM) is the only secret: set `GROQ_API_KEY` in the **server terminal**, not in Blender.

### 3. Generate a scene

1. 3D Viewport → press **N** → tab **AI Director**.
2. **Domain**: try `Park`, then `Space`, then `Interior`.
3. Prompt: anything (offline uses the bundled scene for that domain).
4. Click **Generate Scene**.

You should see a ground/room plus proxy props. **Ctrl+Z** undoes the whole job.

---

## B. Full path — Groq (text) + Poly Haven (assets)

The prompt drives the scene. Poly Haven fills CC0 models/HDRIs when a match exists; otherwise you keep named proxies.

### 1. Groq API key

1. Create a key at [https://console.groq.com/keys](https://console.groq.com/keys).
2. Poly Haven needs **no key**.

### 2. Start the local backend

**PowerShell:**

```powershell
cd C:\me\proj\ai_director_addon\ai_director_backend
pip install -r requirements.txt
$env:GROQ_API_KEY = "paste_your_key_here"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Command Prompt:**

```bat
cd C:\me\proj\ai_director_addon\ai_director_backend
pip install -r requirements.txt
set GROQ_API_KEY=paste_your_key_here
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Leave this window open. Check it is alive:

```powershell
curl http://127.0.0.1:8000/healthz
```

You want `"ok": true`. If Groq is set you also get `"groq": true`.

### 3. Point the addon at the API

**Edit → Preferences → Add-ons → AI Director:**

| Setting | Value |
| --- | --- |
| **Use bundled fixture (offline)** | **OFF** (unchecked) |
| **API base URL** | `http://127.0.0.1:8000` |

### 4. Generate from text

1. N-panel **AI Director**.
2. Domain: **Auto** or pick Park / City / Zoo / Space / …
3. Prompt examples:
   - `A park at dusk with a path, benches, and trees`
   - `Small living room, sofa facing a window, plant next to the sofa`
   - `Space station deck with crates and an antenna`
   - `City street, two buildings, streetlamps`
4. **Generate Scene**. First run can take a while (Groq + Poly Haven downloads). Later runs use the disk cache.

---

## If something fails

| Symptom | Fix |
| --- | --- |
| Generate says planner is down / HTTP error | Backend window must be running on port 8000 |
| `"groq": false` on `/healthz` | `GROQ_API_KEY` not set in **that** terminal; restart uvicorn |
| Scene ignores the prompt | Offline fixture is still **ON** — uncheck it |
| Empty viewport | Look at world origin; for park/city the ground is tens of meters wide — frame all (`Home` / View → Frame All) |
| Addon not listed | Install the folder that contains `blender_manifest.toml`, not `ai_director_backend` |
| Groq HTTP 401 | Bad or expired key |
| Boxes instead of furniture | Normal when Poly Haven has no match (animals, cars, spaceships stay proxies) |

---

## Quick test without Blender UI

Backend tests:

```powershell
cd C:\me\proj\ai_director_addon\ai_director_backend
python -m pytest -q
```

Headless park apply (uses Blender, no Groq):

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python "C:\me\proj\ai_director_addon\ai_director_backend\tests\addon\apply_offline.py" -- park
```

Expect `APPLY_OK park` in the log.
