# Case 101

A detective game with low-poly Three.js environments, paper case files, and a cork evidence board. React provides the interface; Python/FastAPI and NetworkX generate and verify cases before they can be played.

## Run locally

Requires Node.js 20.19+ and Python 3.12+.

```powershell
python -m pip install -r requirements.txt
npm ci
npm run build
npm start
```

Open http://127.0.0.1:4174. For frontend development, keep the Python server running and use `npm run dev` in another terminal (port 5173, with API proxy).

## Play and author

Choose a verified folder or generate a seed-based murder, theft, or sabotage case in a manor, train, or museum. Investigation starts only after selecting a verified case. Search rooms and interview suspects; discovery prerequisites are enforced by the server. Each case retains its own discoveries, pins, card positions, typed connections, notes and saved argument.

Build an argument from discovered evidence, then challenge it: identify the strongest clue, resolve conflicting testimony with an independent record, exclude an alternative suspect, and check an assumption. The server checks the proof instead of trusting client-side completion flags. Accepted alternative proof paths count; a guessed suspect does not. Explicitly revealing a solution does not mark a case solved.

The generator can deliberately assemble broken drafts. Verification reports identify missing prerequisites, cycles, contradictions, time inconsistencies, unreachable conclusions and unsupported or ambiguous solutions. Correction previews explain individual changes; applying them creates a new revision and reruns verification, retaining the original. The prerequisite editor also creates revisions. Player graphs hide unrecovered evidence and conclusions; explicit author mode reveals spoilers and proof paths.

## Architecture and limits

`backend/engine.py` holds seeded template generation, NetworkX graph checks, and fixed-point Horn inference with minimal evidence provenance. AND prerequisites must all be established: a graph path alone is insufficient. `backend/app.py` owns discovery, progress and accusation validation. SQLite stores anonymous browser sessions in `data/case101.sqlite3`; retain this directory and the browser cookie to preserve progress. Set `CASE101_DB` to choose another database location. This is a single-server prototype with anonymous sessions, not an account-based multiplayer service.

Generation uses authored narrative templates and formal assertions, not unrestricted language generation. Verification proves properties of these encoded facts and rules; it cannot interpret arbitrary prose. Three settings share geometry with different props. Optional v2 import retains the original local save and a server snapshot while migrating recognized discovery IDs; old win flags do not authorize a v3 victory.

## Media and audio

The user-supplied `WhatsApp Video 2026-10-15 at 11.33.33 PM.mp4` is the intro. Background music is extracted from the supplied `Video Project.mp4`, with a three-second overlap crossfade at the loop boundary. The intro is muted to avoid competing tracks. Music starts after user interaction, continues across screens, and has a persistent toggle independent of paper/pin effects. Media files live in `public/assets`.

## Verify

```powershell
npm test
node tests/audio.test.mjs
npm run build
```

Tests cover seeded generation across all nine setting/genre combinations, alternate proofs, broken drafts and corrections, prerequisite enforcement, invalid accusations, case/session isolation, board CRUD, graph spoiler boundaries, explicit reveal, and a complete API investigation-to-verdict journey. Audio unit tests cover gesture unlock, looping, toggles, saved preferences and avoiding track restarts.

## Hosting

This version requires a Python service serving both `/api` and the generated `dist` directory. The previous static Sites URL does not run this backend and has not been updated with this build. A static-only upload will not work. Build the frontend before starting Uvicorn; use a persistent database volume, HTTPS reverse proxy, and set `CASE101_ORIGINS` to the public origin if the proxy's internal origin differs. A Dockerfile is included; bind port 4174 and persist `/app/data`. No cloud deployment or paid service is provisioned by this repository.
