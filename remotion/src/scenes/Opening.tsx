import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Visual} from '../components/Visual';
import {SAFE_TOP, SANS, SERIF} from '../types';
import {Label, RisingText, SceneBase} from './ui';

type ClaimScene = SceneBase & {claim: string; image?: string | null; year: number; era: string};

export const Hook: React.FC<ClaimScene> = ({claim, image, year, era, palette, accent, duration}) => (
	<AbsoluteFill style={{alignItems: 'center', paddingTop: SAFE_TOP + 30}}>
		<Label text="Myth or fact?" color={palette.gold} bg={palette.burgundy} size={44} />
		<div style={{marginTop: 54}}>
			<Visual image={image} seed={0} year={year} era={era} palette={palette} accent={accent} width={860} height={640} tilt={-1.6} duration={duration} />
		</div>
		<div style={{marginTop: 70, width: 940}}>
			<RisingText text={claim} size={claim.length > 42 ? 76 : 92} color={palette.ink} delay={6} />
		</div>
	</AbsoluteFill>
);

const COUNTDOWN_SECONDS = 3;
const RING_RADIUS = 190;

export const Countdown: React.FC<SceneBase & {claim: string}> = ({claim, palette}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const total = COUNTDOWN_SECONDS * fps;
	const remaining = Math.max(1, COUNTDOWN_SECONDS - Math.floor(frame / fps));
	const inSecond = (frame % fps) / fps;
	const circumference = 2 * Math.PI * RING_RADIUS;
	const pulse = 1 + 0.12 * Math.exp(-inSecond * 9);
	return (
		<AbsoluteFill style={{alignItems: 'center', paddingTop: SAFE_TOP + 40}}>
			<div style={{width: 900, fontFamily: SERIF, fontWeight: 800, fontSize: 64, textAlign: 'center', color: palette.ink, lineHeight: 1.1}}>
				{claim}
			</div>
			<div style={{marginTop: 90, position: 'relative', width: 460, height: 460, transform: `scale(${pulse})`}}>
				<svg width="460" height="460" viewBox="0 0 460 460">
					<circle cx="230" cy="230" r={RING_RADIUS + 26} fill={palette.burgundy} />
					<circle cx="230" cy="230" r={RING_RADIUS} fill="none" stroke="rgba(212,168,72,0.25)" strokeWidth="22" />
					<circle
						cx="230"
						cy="230"
						r={RING_RADIUS}
						fill="none"
						stroke={palette.gold}
						strokeWidth="22"
						strokeLinecap="round"
						strokeDasharray={circumference}
						strokeDashoffset={circumference * (frame / total)}
						transform="rotate(-90 230 230)"
					/>
				</svg>
				<div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: SERIF, fontWeight: 900, fontSize: 240, color: palette.parchment}}>
					{remaining}
				</div>
			</div>
			<div style={{marginTop: 70, fontFamily: SANS, fontWeight: 900, fontSize: 66, letterSpacing: 10, textTransform: 'uppercase', color: palette.burgundy}}>
				Decide now!
			</div>
		</AbsoluteFill>
	);
};

const STAMP_LAND = 5;
const SHAKE_FRAMES = 12;
const claimStyle: React.CSSProperties = {fontFamily: SERIF, fontWeight: 800, fontSize: 78, textAlign: 'center', lineHeight: 1.12};

export const Verdict: React.FC<SceneBase & {claim: string; verdict: 'MYTH' | 'FACT'}> = ({claim, verdict, palette}) => {
	const frame = useCurrentFrame();
	const isMyth = verdict === 'MYTH';
	const ink = isMyth ? '#9B1C20' : '#9A6F12';
	const scale = interpolate(frame, [0, STAMP_LAND], [2.6, 1], {extrapolateRight: 'clamp', easing: Easing.in(Easing.quad)});
	const opacity = interpolate(frame, [0, 2], [0, 1], {extrapolateRight: 'clamp'});
	const k = Math.max(0, frame - STAMP_LAND);
	const decay = k < SHAKE_FRAMES ? 1 - k / SHAKE_FRAMES : 0;
	const shakeX = Math.sin(k * 2.7) * 16 * decay;
	const shakeY = Math.cos(k * 3.3) * 10 * decay;
	const strike = interpolate(frame, [STAMP_LAND + 4, STAMP_LAND + 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', transform: `translate(${shakeX}px, ${shakeY}px)`}}>
			<div style={{position: 'relative', width: 920, marginTop: -120}}>
				<div style={{...claimStyle, color: palette.ink, opacity: isMyth ? 0.75 : 1}}>{claim}</div>
				{isMyth ? (
					// Same text, transparent, with a line-through per line; revealed left-to-right like a pen stroke.
					<div
						style={{
							...claimStyle,
							position: 'absolute',
							inset: 0,
							color: 'transparent',
							textDecoration: 'line-through',
							textDecorationColor: ink,
							textDecorationThickness: 9,
							clipPath: `inset(0 ${(1 - strike) * 100}% 0 0)`,
						}}
					>
						{claim}
					</div>
				) : null}
			</div>
			<div
				style={{
					marginTop: 90,
					transform: `scale(${scale}) rotate(-11deg)`,
					opacity,
					border: `14px solid ${ink}`,
					outline: `5px solid ${ink}`,
					outlineOffset: 10,
					padding: '18px 60px 10px',
					color: ink,
					fontFamily: SANS,
					fontWeight: 900,
					fontSize: 200,
					letterSpacing: 18,
					lineHeight: 1,
					mixBlendMode: 'multiply',
					background: 'rgba(255,255,255,0.08)',
				}}
			>
				{verdict}
			</div>
		</AbsoluteFill>
	);
};
