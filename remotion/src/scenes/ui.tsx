import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Palette, SANS, SERIF} from '../types';

export type SceneBase = {palette: Palette; accent: string; duration: number};

export const Label: React.FC<{text: string; color: string; bg?: string; size?: number}> = ({text, color, bg, size = 34}) => (
	<div
		style={{
			fontFamily: SANS,
			fontWeight: 800,
			fontSize: size,
			letterSpacing: size * 0.28,
			textTransform: 'uppercase',
			color,
			background: bg,
			padding: bg ? '14px 34px 14px 44px' : 0,
			display: 'inline-block',
		}}
	>
		{text}
	</div>
);

// Words rise in one after another: the claim reads like it's being set in type.
export const RisingText: React.FC<{text: string; size: number; color: string; delay?: number; weight?: number; italic?: boolean}> = ({
	text,
	size,
	color,
	delay = 0,
	weight = 900,
	italic = false,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	return (
		<div style={{fontFamily: SERIF, fontWeight: weight, fontSize: size, lineHeight: 1.08, color, textAlign: 'center', fontStyle: italic ? 'italic' : 'normal'}}>
			{text.split(' ').map((w, i) => {
				const s = spring({frame: frame - delay - i * 2, fps, config: {damping: 16, stiffness: 160}});
				return (
					<span key={i} style={{display: 'inline-block', opacity: s, transform: `translateY(${(1 - s) * 40}px)`, marginRight: size * 0.26}}>
						{w}
					</span>
				);
			})}
		</div>
	);
};

export const GoldRule: React.FC<{palette: Palette; width?: number; delay?: number}> = ({palette, width = 520, delay = 0}) => {
	const frame = useCurrentFrame();
	const grow = interpolate(frame - delay, [0, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<div style={{display: 'flex', alignItems: 'center', gap: 18, width, transform: `scaleX(${grow})`}}>
			<div style={{flex: 1, height: 4, background: palette.gold}} />
			<div style={{width: 22, height: 22, background: palette.burgundy, border: `4px solid ${palette.gold}`, transform: 'rotate(45deg)'}} />
			<div style={{flex: 1, height: 4, background: palette.gold}} />
		</div>
	);
};
