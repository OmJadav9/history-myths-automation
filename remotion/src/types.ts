export type SceneType = 'hook' | 'countdown' | 'verdict' | 'beat' | 'origin_intro' | 'sources' | 'outro';

export type Scene = {
	type: SceneType;
	from: number;
	durationInFrames: number;
	keyLine?: string;
	image?: string | null;
	section?: 'reality' | 'origin';
	beatNumber?: number;
	beatTotal?: number;
};

export type Cue = {text: string; from: number; durationInFrames: number};

export type Palette = {burgundy: string; gold: string; parchment: string; ink: string};

export type ReelProps = {
	claim: string;
	verdict: 'MYTH' | 'FACT';
	hook: string;
	category: string;
	era: string;
	year: number;
	account: string;
	accent: string;
	palette: Palette;
	scenes: Scene[];
	subtitles: Cue[];
	sources: string[];
	audio: string;
	durationInFrames: number;
	fps: number;
	width: number;
	height: number;
};

// Instagram UI covers the top 250px and bottom 340px of a 1080x1920 reel.
export const SAFE_TOP = 250;
export const SAFE_BOTTOM = 340;
export const SERIF = "'Playfair Display', Georgia, serif";
export const SANS = "'Inter', Arial, sans-serif";
