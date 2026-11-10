import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

const TURN_FRAMES = 12;
const FADE_OUT_FRAMES = 4;

// Each scene enters like a page swinging in from its left edge, with the fold shadow lifting off.
export const PageTurn: React.FC<{children: React.ReactNode; durationInFrames: number; enabled?: boolean}> = ({
	children,
	durationInFrames,
	enabled = true,
}) => {
	const frame = useCurrentFrame();
	const {width} = useVideoConfig();
	const t = enabled
		? interpolate(frame, [0, TURN_FRAMES], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)})
		: 1;
	const fadeOut = interpolate(frame, [durationInFrames - FADE_OUT_FRAMES, durationInFrames], [1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	return (
		<AbsoluteFill style={{perspective: width * 2.2, opacity: fadeOut}}>
			<AbsoluteFill
				style={{
					transformOrigin: 'left center',
					transform: `rotateY(${(1 - t) * -80}deg)`,
					backfaceVisibility: 'hidden',
				}}
			>
				{children}
				<AbsoluteFill
					style={{
						background: 'linear-gradient(90deg, rgba(42,27,18,0.55) 0%, rgba(42,27,18,0) 45%)',
						opacity: 1 - t,
						pointerEvents: 'none',
					}}
				/>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};
