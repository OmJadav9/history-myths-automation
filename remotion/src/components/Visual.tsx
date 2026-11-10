import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Palette, SANS, SERIF} from '../types';

type FrameProps = {palette: Palette; accent: string; width: number; height: number; tilt?: number};

const FrameCard: React.FC<FrameProps & {children: React.ReactNode}> = ({palette, accent, width, height, tilt = 0, children}) => (
	<div
		style={{
			width,
			height,
			padding: 14,
			background: palette.gold,
			transform: `rotate(${tilt}deg)`,
			boxShadow: '0 30px 60px rgba(42,27,18,0.45), 0 6px 14px rgba(42,27,18,0.35)',
			border: `3px solid ${palette.burgundy}`,
		}}
	>
		<div style={{width: '100%', height: '100%', overflow: 'hidden', position: 'relative', outline: `2px solid ${accent}`}}>
			{children}
		</div>
	</div>
);

// Slow Ken Burns push on a public-domain image; direction alternates by `seed`.
const KenBurns: React.FC<{src: string; seed: number; duration: number}> = ({src, seed, duration}) => {
	const frame = useCurrentFrame();
	const p = interpolate(frame, [0, Math.max(duration, 1)], [0, 1], {extrapolateRight: 'clamp'});
	const dir = seed % 2 === 0 ? 1 : -1;
	const scale = 1.06 + 0.12 * p;
	return (
		<Img
			src={staticFile(src)}
			style={{
				width: '100%',
				height: '100%',
				objectFit: 'cover',
				transform: `scale(${scale}) translate(${dir * 2.5 * p}%, ${-1.5 * p}%)`,
				filter: 'sepia(0.28) contrast(1.05) saturate(0.9)',
			}}
		/>
	);
};

const formatYear = (year: number) => (year < 0 ? `${-year} BC` : year < 1000 ? `AD ${year}` : `${year}`);

// Fallback when Commons has no usable image: an animated timeline that counts up to the myth's year.
const YearMotif: React.FC<{year: number; era: string; palette: Palette; accent: string}> = ({year, era, palette, accent}) => {
	const frame = useCurrentFrame();
	const t = interpolate(frame, [0, 40], [0, 1], {extrapolateRight: 'clamp'});
	const shown = Math.round(year - 300 * (1 - t));
	const ticks = Array.from({length: 9}, (_, i) => i);
	return (
		<div style={{width: '100%', height: '100%', background: palette.burgundy, position: 'relative', fontFamily: SERIF}}>
			<div style={{position: 'absolute', top: 90, width: '100%', textAlign: 'center', color: palette.gold, fontSize: 150, fontWeight: 900}}>
				{formatYear(shown)}
			</div>
			<div style={{position: 'absolute', top: 290, width: '100%', textAlign: 'center', color: palette.parchment, fontFamily: SANS, fontSize: 36, letterSpacing: 8, fontWeight: 600, textTransform: 'uppercase'}}>
				{era}
			</div>
			<svg width="100%" height="160" style={{position: 'absolute', bottom: 70}} viewBox="0 0 820 160">
				<line x1="20" y1="80" x2="800" y2="80" stroke={palette.gold} strokeWidth="6" />
				{ticks.map((i) => (
					<line key={i} x1={20 + i * 97.5} y1={i % 2 ? 62 : 50} x2={20 + i * 97.5} y2={i % 2 ? 98 : 110} stroke={palette.parchment} strokeWidth="4" />
				))}
				<circle cx={20 + 780 * t} cy="80" r="22" fill={accent} stroke={palette.gold} strokeWidth="6" />
			</svg>
		</div>
	);
};

export const Visual: React.FC<
	FrameProps & {image?: string | null; seed: number; year: number; era: string; duration: number}
> = ({image, seed, year, era, duration, ...frame}) => (
	<FrameCard {...frame}>
		{image ? (
			<KenBurns src={image} seed={seed} duration={duration} />
		) : (
			<YearMotif year={year} era={era} palette={frame.palette} accent={frame.accent} />
		)}
	</FrameCard>
);
