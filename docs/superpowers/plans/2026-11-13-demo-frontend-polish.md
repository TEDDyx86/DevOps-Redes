# Web-demo Frontend Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the public landing page and authenticated web-demo panel into a clean, readable pixel-retro interface without changing API behavior.

**Architecture:** Keep the current React/Vite routes and API client. Simplify page composition in `Landing.tsx` and `Panel.tsx`, then tune shared visual rules in `styles.css` and focused component styles; preserve the login flow and existing endpoint polling.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS 4, Vitest.

## Global Constraints

- Only modify `demo-frontend`; do not change the main dashboard (`frontend/`, port 8000) or backend.
- Do not alter authentication, endpoints (`/health`, `/mode`, `/work`, `/metrics`), polling cadence, or lab behavior.
- Missing values remain unknown/awaiting data, never zero or healthy by default.
- Preserve local user changes; inspect current working diffs before editing and integrate into the current versions.
- Keep the dark pixel-retro identity while removing global scanlines and misleading decorative metrics.

---

## File Map

- `demo-frontend/src/pages/Landing.tsx`: public product introduction and login CTA; remove redundant simulated showcase sections.
- `demo-frontend/src/pages/Panel.tsx`: authenticated status, `/work` interaction/log, Prometheus counters, and secondary lab controls.
- `demo-frontend/src/styles.css`: global CRT/grid effects and reusable retro surfaces.
- `demo-frontend/src/components/PixelNavHeader.tsx`: existing landing navigation, retain unless current inspection shows it must be adjusted for the concise layout.
- `demo-frontend/src/components/PixelHeroScene.tsx`: hero art and CTA; reduce overly heavy frame/shadows while preserving identity and action.
- `demo-frontend/src/components/RetroWindow.tsx`: shared panel/login windows; retain functional collapse/close behavior and tone down decoration where needed.

## Task 1: Clean the public landing page

**Files:**
- Modify: `demo-frontend/src/pages/Landing.tsx`
- Modify: `demo-frontend/src/components/PixelHeroScene.tsx`
- Test: `demo-frontend/src/api.test.ts` (regression suite; no API behavior change)

**Interfaces:**
- Consumes: `api.health()` and `navigate("/login")` from `src/api.ts`.
- Produces: concise public page with `PixelNavHeader`, hero, short real-capability summary, and footer; CTA continues to navigate to `/login`.

- [ ] **Step 1: Inspect the current landing-page diff and identify user edits to retain.**
  Run: `git diff -- demo-frontend/src/pages/Landing.tsx demo-frontend/src/components/PixelHeroScene.tsx`
  Expected: review all existing edits before replacing or removing JSX.

- [ ] **Step 2: Simplify the page composition.**
  Remove unused state, `triggerWork`, popup health scan, carousel slide data, and imports for `RetroPopups`, `RetroCarousel`, `RetroHud`, and `RetroDesktop` from `Landing.tsx`. Render the existing header and hero, followed by a compact section that describes only real capabilities (service health, `/work` response/latency, and Prometheus HTTP metrics), then a restrained footer. Keep all links/actions purposeful and direct the primary CTA to `/login`.

- [ ] **Step 3: Soften hero framing without losing the pixel-art identity.**
  In `PixelHeroScene.tsx`, retain the SVG scene and CTA. Replace the heavy black 4px frame and offset 8px shadow with a thin subdued edge and a restrained shadow; reduce the title's 3D shadow if it overwhelms the artwork. Preserve accessible image text and button behavior.

- [ ] **Step 4: Run frontend regressions and production build.**
  Run from `demo-frontend`: `npm test`
  Expected: Vitest exits 0.
  Run: `npm run build`
  Expected: `tsc -b && vite build` exits 0.

## Task 2: Make the authenticated panel operational and truthful

**Files:**
- Modify: `demo-frontend/src/pages/Panel.tsx`
- Modify: `demo-frontend/src/components/RetroWindow.tsx` only if visual consistency requires shared window tone adjustments.
- Test: `demo-frontend/src/api.test.ts`
- Test: `demo-frontend/src/metrics.test.ts`

**Interfaces:**
- Consumes: current `api.authenticated`, `api.health`, `api.mode`, `api.metrics`, `api.work`, `api.setMode`, `api.logout`, and `parseDemoCounters`.
- Produces: operational summary, real request/latency log, actual Prometheus counters, and secondary lab mode controls with unchanged calls and state handling.

- [ ] **Step 1: Inspect the current panel diff and record user changes to preserve.**
  Run: `git diff -- demo-frontend/src/pages/Panel.tsx demo-frontend/src/components/RetroWindow.tsx`
  Expected: current modifications are understood before edits.

- [ ] **Step 2: Replace the decorative HUD with real service status.**
  Remove the `RetroHud` import and instance. Add a compact summary region using existing `online`, `mode`, `lastLatency`, and `workCount` state only. Render loading/unknown distinctly (`null` stays “aguardando/sem dados”); render offline as a critical state. Do not derive CPU/network/session values or imply unobserved service statuses.

- [ ] **Step 3: Preserve the work console and make lab controls secondary.**
  Keep the `/work` button, measured browser latency, bounded recent log, actual Prometheus totals/status breakdown, and logout. Place the `LAB_TOKEN` mode controls in a visually subordinate section/window titled as a lab tool. Keep all current event handlers and error messages; do not change API request cadence or endpoint payloads.

- [ ] **Step 4: Run tests and build.**
  Run from `demo-frontend`: `npm test`
  Expected: all existing Vitest tests pass.
  Run: `npm run build`
  Expected: TypeScript and Vite build pass without errors.

## Task 3: Remove card noise and verify responsive presentation

**Files:**
- Modify: `demo-frontend/src/styles.css`
- Modify: `demo-frontend/src/pages/Landing.tsx`
- Modify: `demo-frontend/src/pages/Login.tsx`
- Modify: `demo-frontend/src/pages/Panel.tsx`
- Modify: `demo-frontend/src/components/RetroWindow.tsx`

**Interfaces:**
- Consumes: Tailwind theme tokens and current page/component class names.
- Produces: clean shared surfaces, no page-wide CRT overlay, consistent card spacing and restrained accent usage without changing component functionality.

- [ ] **Step 1: Remove the global scanline layer.**
  Remove `crt-scanlines` from the landing, login, and panel roots, and remove the `.crt-scanlines::after` overlay rule. This prevents the high-z-index texture from crossing text and cards on every route.

- [ ] **Step 2: Tone down reusable card chrome.**
  In the page and window classes, replace high-intensity multi-layer glows, thick/double borders, and bevels on large content surfaces with a single subtle border, solid background, and consistent padding. Keep high-contrast focus indicators and use status colors only for status or primary actions. Do not remove keyboard-visible focus styles.

- [ ] **Step 3: Remove unused grid animation from the shared visual system if no retained component uses it.**
  Search TSX references for `.synth-grid`, `.perspective-grid`, and `.perspective-plane`; delete only CSS rules that no longer have a caller after removing the decorative HUD. Preserve any class still used in the hero or login.

- [ ] **Step 4: Run tests and build after final class changes.**
  Run from `demo-frontend`: `npm test && npm run build`
  Expected: tests and production build both exit 0.

- [ ] **Step 5: Review route and responsive behavior.**
  Inspect `/`, `/login`, and `/painel` at desktop and narrow mobile widths. Confirm no horizontal overflow, the CTA/login form remain usable, panel cards stack in a sensible order, and no full-page grid/scanline is visible. Confirm authenticated panel behavior with the running local stack if it is available; otherwise report that runtime checks were not performed.

## Verification Against Specification

- Landing simplification and CTA: Task 1.
- Real-data panel hierarchy and removal of fake indicators: Task 2.
- Global overlay/grid removal and card styling: Task 3.
- Authentication, API contracts, polling, missing-data semantics, mobile behavior: Constraints and Tasks 2–3.
