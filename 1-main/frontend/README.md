# Shorts Factory — Frontend (Week 4)

Next.js app with a Remotion in-browser preview of the AI EditPlan.

## How it works

1. You upload a video (+ optional music) and pick a niche.
2. The app POSTs to the backend `/plan` endpoint, which runs the 5-agent
   orchestrator and returns the EditPlan as JSON.
3. The Remotion `<Player>` renders `ShortPreview` — cuts, animated
   captions and meme overlays — over your local video, **for free**, with
   zero cloud render.
4. Only when you're happy do you hit the backend `/process/agentic`
   endpoint to produce the final encoded MP4.

## Run

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000. Make sure the backend is running
(`uvicorn app.main:app --reload` in `../backend`).

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |
