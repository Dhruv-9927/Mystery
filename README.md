# ClueMesh — The Lantern House

A playable browser detective game with a procedurally modelled, low-poly Three.js environment and the supplied ten-second cinematic intro.

Run `npm run dev`, then open http://localhost:4173. Run `npm test` for the deterministic engine checks. Static deploy files live in `dist/`; no build step is required.

## Play

Enter or skip the intro. Search the three locations and interview four suspects. Pin evidence, connect cards, reconstruct the timeline, and submit a suspect with motive, means and opportunity evidence. Progress saves in browser local storage. Sound is optional.

Inspect checks the complete case graph. Break a clue removes a record from a temporary copy and reports the failed route. Reveal routes is explicitly marked as a spoiler. The Lab runs 100 structural test graphs in a Web Worker; these generated graphs are not additional playable stories.

## Current scope

One authored playable case, fourteen clues, three authored solution routes. The environment uses real 3D geometry; evidence cards, dialogue and menus are readable 2D overlays. Locations currently reuse the mansion architecture with different evidence and props. Suspect interviews are text-based. The generator varies structural test graphs rather than writing full procedural narratives. The verifier validates declared evidence dependencies and routes; it is not a natural-language theorem prover or an exhaustive solver for arbitrary mysteries.

## Assets

The intro video was supplied by the user. Geometry and UI were created for this project. Three.js 0.170.0 is vendored under its MIT license. Fonts load from Google Fonts with system fallbacks.
