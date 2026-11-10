import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Visual} from '../components/Visual';
import {SAFE_TOP, SERIF} from '../types';
import {GoldRule, Label, RisingText, SceneBase} from './ui';

type BeatProps = SceneBase & {
	keyLine: string;
	image?: string | null;
	section: 'reality' | 'origin';
	beatNumber: number;
	beatTotal: number;
	verdict: 'MYTH' | 'FACT';
	year: number;
	era: string;
	seed: number;
};

export const Beat: React.FC<BeatProps> = ({keyLine, image, section, beatNumber, beatTotal, verdict, year, era, seed, palette, accent, duration}) => {
	const frame = useCurrentFrame();
	const underline = interpolate(frame, [10, 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const heading = section === 'reality' ? (verdict === 'MYTH' ? 'What really happened' : 'Why it’s true') : 'Where it came from';
	return (
		<AbsoluteFill style={{alignItems: 'center', paddingTop: SAFE_TOP + 30}}>
			<div style={{display: 'flex', alignItems: 'baseline', gap: 26}}>
				<Label text={heading} color={accent} size={32} />
				<div style={{fontFamily: SERIF, fontWeight: 700, fontSize: 40, color: palette.burgundy}}>
					{beatNumber}/{beatTotal}
				</div>
			</div>
			<div style={{marginTop: 40}}>
				<Visual image={image} seed={seed} year={year} era={era} palette={palette} accent={accent} width={880} height={700} tilt={seed % 2 ? 1.4 : -1.2} duration={duration} />
			</div>
			<div style={{marginTop: 64, width: 940, position: 'relative'}}>
				<RisingText text={keyLine} size={keyLine.length > 28 ? 74 : 86} color={palette.ink} delay={4} weight={800} />
				<div style={{margin: '18px auto 0', height: 8, width: 360 * underline, background: palette.gold}} />
			</div>
		</AbsoluteFill>
	);
};

export const OriginIntro: React.FC<SceneBase & {verdict: 'MYTH' | 'FACT'; era: string}> = ({verdict, era, palette, accent}) => (
	<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingBottom: 260}}>
		<Label text={era} color={accent} size={34} />
		<div style={{height: 50}} />
		<GoldRule palette={palette} />
		<div style={{height: 60, width: 920}} />
		<div style={{width: 900}}>
			<RisingText
				text={verdict === 'MYTH' ? 'So where did this myth come from?' : 'So why does it sound like a myth?'}
				size={98}
				color={palette.burgundy}
				italic
				weight={800}
			/>
		</div>
		<div style={{height: 60}} />
		<GoldRule palette={palette} delay={8} />
	</AbsoluteFill>
);
