import {ReelProps} from './types';

// Silent, image-free preview for Remotion Studio (`npm run studio`). Real renders get props from Python.
const fps = 30;
const scenes: ReelProps['scenes'] = [
	{type: 'hook', from: 0, durationInFrames: 90},
	{type: 'countdown', from: 90, durationInFrames: 90},
	{type: 'verdict', from: 180, durationInFrames: 60},
	{type: 'beat', from: 240, durationInFrames: 120, section: 'reality', keyLine: 'No horned helmets found', beatNumber: 1, beatTotal: 2},
	{type: 'beat', from: 360, durationInFrames: 120, section: 'reality', keyLine: 'Plain rounded iron caps', beatNumber: 2, beatTotal: 2},
	{type: 'origin_intro', from: 480, durationInFrames: 75},
	{type: 'beat', from: 555, durationInFrames: 120, section: 'origin', keyLine: 'Blame an 1870s opera', beatNumber: 1, beatTotal: 1},
	{type: 'sources', from: 675, durationInFrames: 75},
	{type: 'outro', from: 750, durationInFrames: 120},
];

export const sampleProps: ReelProps = {
	claim: 'Vikings wore horned helmets.',
	verdict: 'MYTH',
	hook: 'The most famous Viking look is fake',
	category: 'Medieval',
	era: 'Viking Age',
	year: 900,
	account: 'did.you.know9104',
	accent: '#5B6E3A',
	palette: {burgundy: '#6E1622', gold: '#D4A848', parchment: '#EFE3C8', ink: '#2A1B12'},
	scenes,
	subtitles: [
		{text: 'Myth or fact?', from: 0, durationInFrames: 30},
		{text: 'Vikings wore horned', from: 30, durationInFrames: 30},
		{text: 'helmets.', from: 60, durationInFrames: 25},
	],
	sources: ['Encyclopaedia Britannica', 'National Museum of Denmark'],
	audio: '',
	durationInFrames: 870,
	fps,
	width: 1080,
	height: 1920,
};
