// Shape of the EditPlan JSON returned by the backend POST /plan endpoint.
// Mirrors EditPlan.to_dict() in backend/app/orchestrator.py.

export interface Vibe {
  energy: number;
  reverence: number;
  rhythm_dependency: number;
}

export interface CropInfo {
  width: number;
  height: number;
  fps: number;
  centers_x: number[];
}

export interface PlanSegment {
  start: number;
  end: number;
}

export interface PlanWord {
  text: string;
  start: number;
  end: number;
  energy: boolean;
}

export interface PlanMeme {
  query: string;
  start: number;
  end: number;
  gif_url: string;
}

export interface EditPlan {
  vibe: Vibe;
  crop: CropInfo;
  segments: PlanSegment[];
  words: PlanWord[];
  memes: PlanMeme[];
  transitions: number[];
  niche: string | null;
  caption_style: "hype" | "elegant";
  duration: number;
}
