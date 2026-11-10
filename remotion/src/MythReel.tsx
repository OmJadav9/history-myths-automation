import './fonts';
import React from 'react';
import {Audio} from '@remotion/media';
import {AbsoluteFill, CalculateMetadataFunction, Sequence, staticFile} from 'remotion';
import {PageTurn} from './components/PageTurn';
import {Parchment} from './components/Parchment';
import {Subtitles} from './components/Subtitles';
import {Countdown, Hook, Verdict} from './scenes/Opening';
import {Beat, OriginIntro} from './scenes/Story';
import {Outro, Sources} from './scenes/Closing';
import {ReelProps, Scene} from './types';

// Python decides every frame: each scene sits exactly where the timeline put it.
export const calculateMetadata: CalculateMetadataFunction<ReelProps> = ({props}) => ({
	durationInFrames: props.durationInFrames,
	fps: props.fps,
	width: props.width,
	height: props.height,
});

const SceneView: React.FC<{scene: Scene; index: number; props: ReelProps}> = ({scene, index, props}) => {
	const base = {palette: props.palette, accent: props.accent, duration: scene.durationInFrames};
	switch (scene.type) {
		case 'hook':
			return <Hook {...base} claim={props.claim} image={scene.image} year={props.year} era={props.era} />;
		case 'countdown':
			return <Countdown {...base} claim={props.claim} />;
		case 'verdict':
			return <Verdict {...base} claim={props.claim} verdict={props.verdict} />;
		case 'beat':
			return (
				<Beat
					{...base}
					keyLine={scene.keyLine ?? ''}
					image={scene.image}
					section={scene.section ?? 'reality'}
					beatNumber={scene.beatNumber ?? 1}
					beatTotal={scene.beatTotal ?? 1}
					verdict={props.verdict}
					year={props.year}
					era={props.era}
					seed={index}
				/>
			);
		case 'origin_intro':
			return <OriginIntro {...base} verdict={props.verdict} era={props.era} />;
		case 'sources':
			return <Sources {...base} sources={props.sources} hasImages={props.scenes.some((s) => s.image)} />;
		case 'outro':
			return <Outro {...base} account={props.account} />;
	}
};

const NO_PAGE_TURN = new Set(['countdown', 'verdict']);

export const MythReel: React.FC<ReelProps> = (props) => (
	<AbsoluteFill>
		<Parchment palette={props.palette} accent={props.accent} />
		{props.scenes.map((scene, i) => (
			<Sequence key={i} from={scene.from} durationInFrames={scene.durationInFrames} name={scene.type}>
				<PageTurn durationInFrames={scene.durationInFrames} enabled={!NO_PAGE_TURN.has(scene.type)}>
					<SceneView scene={scene} index={i} props={props} />
				</PageTurn>
			</Sequence>
		))}
		<Subtitles cues={props.subtitles} palette={props.palette} />
		{props.audio ? <Audio src={staticFile(props.audio)} /> : null}
	</AbsoluteFill>
);
