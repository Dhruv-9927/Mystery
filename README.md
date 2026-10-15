# ClueMesh — Mystery Generation with Verifiable Evidence Paths

A playable browser detective game with a procedurally modelled, low-poly Three.js environment and the supplied ten-second cinematic intro.

Run `npm run dev`, then open http://localhost:4173. Run `npm test` for the deterministic engine checks. Static deploy files live in `dist/`; no build step is required.

## Play

Enter or skip the intro. Search the three locations and interview four suspects. Pin evidence, connect cards, reconstruct the timeline, and submit a suspect with motive, means and opportunity evidence. Progress saves in browser local storage. Sound is optional.

Choose an archive folder or generate a seed-based case in a country estate, sleeper train or museum. Each generated case changes people, culprit, motive, testimony and supporting records from shared ground truth. The seed and setting reproduce the case. Every accepted case is playable, including verified batch results. Each case saves its own clues, connections and card positions.

## Current scope

The directed graph contains suspects, locations, clues, events, inferred facts and suspect conclusions. Discovery prerequisites are enforced in play. AND/OR inference rules produce minimal evidence proof sets by fixed-point propagation; routes are derived, not stored as a prewritten list. Accusations run the same inference using only attached recovered evidence. The crime-time record and category-specific evidence for the same suspect are required.

The verifier checks missing references, circular dependencies, discoverability, trusted assertion consistency with the timeline, resolvable witness lies, reachability, justification and a unique supported suspect. The graph shows directed requires/reveals/supports/refutes/contradicts edges. Author mode and shortest-path highlighting are explicit spoiler controls. Four fault-injection modes explain exact failed nodes and block play. A Web Worker checks 100 cases without blocking the main thread.

The low-poly 3D scenes are built with geometry; archive folders, parchment, corkboard and dialogue use readable 2D overlays. Settings share basic architectural components with distinct props. The generator is rule/template based, currently centred on a poisoned-drink mystery family; it does not generate unrestricted prose. Verification operates on the formal assertions and rules, not the meaning of arbitrary natural-language text. Tests cover 300 generated cases across all settings and every minimal proof, plus mutations and invalid seeds.

## Assets

The intro video was supplied by the user. Geometry and UI were created for this project. Three.js 0.170.0 is vendored under its MIT license. Fonts load from Google Fonts with system fallbacks.
