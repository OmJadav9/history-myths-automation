import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';

// Fonts are committed under public/fonts (OFL) so rendering never fetches anything over the network.
const handle = delayRender('Loading local fonts');
const faces = [
	new FontFace('Playfair Display', `url('${staticFile('fonts/PlayfairDisplay.ttf')}') format('truetype')`, {
		weight: '400 900',
	}),
	new FontFace('Inter', `url('${staticFile('fonts/Inter.ttf')}') format('truetype')`, {weight: '100 900'}),
];

Promise.all(faces.map((f) => f.load()))
	.then((loaded) => {
		loaded.forEach((f) => document.fonts.add(f));
		continueRender(handle);
	})
	.catch((err) => cancelRender(err));
