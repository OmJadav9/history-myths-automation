import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Palette} from '../types';

// Aged paper: base tone, warm vignette, fibre noise and a faint burgundy edge burn.
export const Parchment: React.FC<{palette: Palette; accent: string}> = ({palette, accent}) => (
	<AbsoluteFill style={{backgroundColor: palette.parchment}}>
		<AbsoluteFill
			style={{
				background: `radial-gradient(ellipse at 50% 42%, rgba(255,250,235,0.55) 0%, rgba(0,0,0,0) 55%),
				radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 58%, rgba(92,52,24,0.38) 100%)`,
			}}
		/>
		<svg width="1080" height="1920" style={{position: 'absolute', inset: 0, opacity: 0.32, mixBlendMode: 'multiply'}}>
			<filter id="paper">
				<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={3} seed={4} />
				<feColorMatrix type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.32  0 0 0 0 0.18  0 0 0 0.55 0" />
			</filter>
			<rect width="1080" height="1920" filter="url(#paper)" />
		</svg>
		<svg width="1080" height="1920" style={{position: 'absolute', inset: 0, opacity: 0.18, mixBlendMode: 'multiply'}}>
			<filter id="stains">
				<feTurbulence type="fractalNoise" baseFrequency="0.006" numOctaves={2} seed={11} />
				<feColorMatrix type="matrix" values="0 0 0 0 0.5  0 0 0 0 0.3  0 0 0 0 0.12  0 0 0 1.4 -0.45" />
			</filter>
			<rect width="1080" height="1920" filter="url(#stains)" />
		</svg>
		<AbsoluteFill style={{boxShadow: `inset 0 0 0 18px ${palette.burgundy}, inset 0 0 0 22px ${accent}`}} />
	</AbsoluteFill>
);
