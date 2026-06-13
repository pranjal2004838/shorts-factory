"use client";

import React, { useState } from "react";
import { Player } from "@remotion/player";
import { ShortPreview } from "../remotion/ShortPreview";
import type { EditPlan } from "../types/editPlan";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const NICHES = ["podcaster", "dancer", "artist", "life_coach"] as const;

export default function Home() {
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [plan, setPlan] = useState<EditPlan | null>(null);
  const [niche, setNiche] = useState<string>("dancer");
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [music, setMusic] = useState<File | null>(null);

  async function buildPreview() {
    if (!file) return;
    setLoading(true);
    try {
      setVideoSrc(URL.createObjectURL(file));
      const body = new FormData();
      body.append("file", file);
      if (music) body.append("music", music);
      body.append("niche", niche);
      const res = await fetch(`${API}/plan`, { method: "POST", body });
      if (!res.ok) throw new Error(`Plan failed: ${res.status}`);
      setPlan((await res.json()) as EditPlan);
    } finally {
      setLoading(false);
    }
  }

  const fps = plan?.crop.fps && plan.crop.fps > 0 ? Math.round(plan.crop.fps) : 30;
  const durationInFrames = plan ? Math.max(1, Math.round(plan.duration * fps)) : 1;

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: 32, color: "#e2e8f0" }}>
      <h1 style={{ fontWeight: 900 }}>🏭 Shorts Factory</h1>
      <p style={{ color: "#94a3b8" }}>
        Upload raw footage, pick your niche, and preview the AI edit — free, in your
        browser — before any cloud render.
      </p>

      <div style={{ display: "grid", gap: 12, margin: "24px 0" }}>
        <label>
          Video&nbsp;
          <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <label>
          Music (optional)&nbsp;
          <input type="file" accept="audio/*" onChange={(e) => setMusic(e.target.files?.[0] ?? null)} />
        </label>
        <label>
          Niche&nbsp;
          <select value={niche} onChange={(e) => setNiche(e.target.value)}>
            {NICHES.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <button onClick={buildPreview} disabled={!file || loading} style={{ width: 200 }}>
          {loading ? "Building plan…" : "Build preview"}
        </button>
      </div>

      {videoSrc && plan && (
        <Player
          component={ShortPreview}
          inputProps={{ videoSrc, plan }}
          durationInFrames={durationInFrames}
          fps={fps}
          compositionWidth={1080}
          compositionHeight={1920}
          style={{ width: 360, height: 640, borderRadius: 16 }}
          controls
        />
      )}

      {plan && (
        <pre style={{ background: "#1e293b", padding: 16, borderRadius: 12, marginTop: 24, overflowX: "auto" }}>
          {JSON.stringify(plan.vibe, null, 2)}
        </pre>
      )}
    </main>
  );
}
