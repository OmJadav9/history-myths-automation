import React from 'react';
import {Composition} from 'remotion';
import {MythReel, calculateMetadata} from './MythReel';
import {sampleProps} from './sample';

export const RemotionRoot: React.FC = () => (
	<Composition
		id="MythReel"
		component={MythReel}
		width={1080}
		height={1920}
		fps={30}
		durationInFrames={sampleProps.durationInFrames}
		defaultProps={sampleProps}
		calculateMetadata={calculateMetadata}
	/>
);
