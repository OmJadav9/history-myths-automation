import React from 'react';
import {AbsoluteFill, Sequence, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Cue, Palette, SAFE_BOTTOM, SANS} from '../types';

const SUBTITLE_GAP = 24;

const Word: React.FC<{text: string; palette: Palette}> = ({text, palette}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const pop = spring({frame, fps, config: {damping: 14, stiffness: 220}, durationInFrames: 8});
	return (
		<div
			style={{
				transform: `scale(${0.86 + 0.14 * pop})`,
				opacity: Math.min(1, pop * 1.6),
				background: 'rgba(42,27,18,0.86)',
				color: '#FFF8EA',
				fontFamily: SANS,
				fontWeight: 800,
				fontSize: 60,
				lineHeight: 1.1,
				padding: '14px 30px 16px',
				borderRadius: 18,
				borderBottom: `5px solid ${palette.gold}`,
				maxWidth: 900,
				textAlign: 'center',
			}}
		>
			{text}
		</div>
	);
};

export const Subtitles: React.FC<{cues: Cue[]; palette: Palette}> = ({cues, palette}) => (
	<>
		{cues.map((c, i) => (
			<Sequence key={i} from={c.from} durationInFrames={c.durationInFrames} layout="none">
				<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: SAFE_BOTTOM + SUBTITLE_GAP}}>
					<Word text={c.text} palette={palette} />
				</AbsoluteFill>
			</Sequence>
		))}
	</>
);
