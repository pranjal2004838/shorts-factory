// Remotion composition that renders the AI EditPlan in the browser.
// It reads cut times, word-level captions and meme overlays and plays
// them back over the uploaded video — a free preview before any cloud
// render. No video is re-encoded here; this is pure browser playback.

import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { EditPlan, PlanWord } from "../types/editPlan";

export interface ShortPreviewProps {
  videoSrc: string;
  plan: EditPlan;
}

const MAX_WORDS = 3;
const GROUP_GAP = 0.45;

function groupWords(words: PlanWord[]): PlanWord[][] {
  const groups: PlanWord[][] = [];
  let current: PlanWord[] = [];
  for (const w of words) {
    if (current.length > 0) {
      const gap = w.start - current[current.length - 1].end;
      if (current.length >= MAX_WORDS || gap > GROUP_GAP) {
        groups.push(current);
        current = [];
      }
    }
    current.push(w);
  }
  if (current.length > 0) groups.push(current);
  return groups;
}

const Caption: React.FC<{ group: PlanWord[]; style: "hype" | "elegant" }> = ({
  group,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const start = group[0].start;
  const end = group[group.length - 1].end;
  if (t < start || t > end) return null;

  const energy = group.some((w) => w.energy);
  const scale = interpolate(t - start, [0, 0.12], [0.8, 1], {
    extrapolateRight: "clamp",
  });
  const text = group.map((w) => w.text).join(" ").toUpperCase();
  const color = energy && style === "hype" ? "#FFEA00" : "#FFFFFF";

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: "22%",
      }}
    >
      <span
        style={{
          transform: `scale(${scale})`,
          color,
          fontFamily: style === "elegant" ? "Georgia, serif" : "Montserrat, sans-serif",
          fontWeight: 900,
          fontSize: energy ? 96 : 80,
          WebkitTextStroke: "6px #000",
          textAlign: "center",
        }}
      >
        {text}
      </span>
    </AbsoluteFill>
  );
};

const Meme: React.FC<{ plan: EditPlan }> = ({ plan }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <>
      {plan.memes
        .filter((m) => t >= m.start && t <= m.end)
        .map((m, i) => (
          <Img
            key={i}
            src={m.gif_url}
            style={{
              position: "absolute",
              top: 80,
              right: 40,
              width: 320,
            }}
          />
        ))}
    </>
  );
};

export const ShortPreview: React.FC<ShortPreviewProps> = ({ videoSrc, plan }) => {
  const groups = groupWords(plan.words);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <OffthreadVideo src={videoSrc} />
      {groups.map((g, i) => (
        <Caption key={i} group={g} style={plan.caption_style} />
      ))}
      <Meme plan={plan} />
    </AbsoluteFill>
  );
};
