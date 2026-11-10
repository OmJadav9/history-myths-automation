import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {SANS, SERIF} from '../types';
import {GoldRule, Label, RisingText, SceneBase} from './ui';

export const Sources: React.FC<SceneBase & {sources: string[]; hasImages: boolean}> = ({sources, hasImages, palette, accent}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	return (
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingBottom: 220}}>
			<div style={{fontFamily: SERIF, fontWeight: 900, fontSize: 104, color: palette.burgundy}}>Sources</div>
			<div style={{height: 34}} />
			<GoldRule palette={palette} width={440} />
			<div style={{height: 50}} />
			{sources.map((s, i) => {
				const p = spring({frame: frame - 4 - i * 4, fps, config: {damping: 18}});
				return (
					<div key={s} style={{opacity: p, transform: `translateX(${(1 - p) * -60}px)`, display: 'flex', alignItems: 'center', gap: 24, width: 860, margin: '16px 0'}}>
						<div style={{width: 18, height: 18, background: palette.gold, transform: 'rotate(45deg)', flexShrink: 0}} />
						<div style={{fontFamily: SANS, fontWeight: 600, fontSize: 50, color: palette.ink, lineHeight: 1.15}}>{s}</div>
					</div>
				);
			})}
			{hasImages ? (
				<div style={{marginTop: 50}}>
					<Label text="Images: Wikimedia Commons, public domain" color={accent} size={24} />
				</div>
			) : null}
		</AbsoluteFill>
	);
};

export const Outro: React.FC<SceneBase & {account: string}> = ({account, palette}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const pill = spring({frame: frame - 18, fps, config: {damping: 12}});
	return (
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingBottom: 240}}>
			<div style={{width: 920}}>
				<RisingText text="Did you believe this one?" size={104} color={palette.burgundy} />
			</div>
			<div style={{height: 50}} />
			<GoldRule palette={palette} />
			<div style={{height: 50}} />
			<div style={{fontFamily: SANS, fontWeight: 700, fontSize: 54, color: palette.ink, textAlign: 'center', width: 860, lineHeight: 1.25}}>
				Comment a myth you want busted next
			</div>
			<div
				style={{
					marginTop: 70,
					transform: `scale(${pill})`,
					background: palette.burgundy,
					color: palette.gold,
					fontFamily: SANS,
					fontWeight: 800,
					fontSize: 44,
					padding: '22px 46px',
					borderRadius: 999,
					border: `4px solid ${palette.gold}`,
				}}
			>
				Follow @{account}
			</div>
			<div style={{marginTop: 26, fontFamily: SANS, fontWeight: 600, fontSize: 38, color: palette.burgundy, opacity: pill}}>
				A new myth busted every day
			</div>
		</AbsoluteFill>
	);
};
