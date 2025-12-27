# RetailOS Admin — Frontend Development Guide

This document explains how to run and develop the Next.js admin UI.

## Quick Start

### With API (Normal Mode)

```bash
# Terminal 1: Start the API
cd /path/to/project
docker-compose up

# Terminal 2: Start the frontend
cd services/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

The UI will connect to the API at `http://127.0.0.1:8000` by default.

### Frontend-Only (Demo Mode)

If you want to work on the UI without running the backend:

```bash
cd services/web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

The app will detect that the API is offline and automatically enable **Demo Mode**:
- A yellow banner will appear: "⚠️ API Offline: Demo Mode"
- Vault pages will load fixture data from `fixtures/*.json`
- Actions will be disabled or show simulation toasts
- You can develop and test UI components without needing the backend

## Environment Variables

Create a `.env.local` file in `services/web/` to customize settings:

```bash
# API base URL (default: http://127.0.0.1:8000)
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

> **Note**: The `NEXT_PUBLIC_` prefix makes this variable available in the browser. On Windows, we use `127.0.0.1` instead of `localhost` to avoid IPv6 resolution issues.

## Available Scripts

```bash
# Development server (with hot reload)
npm run dev

# Production build
npm run build

# Start production server
npm start

# Lint code
npm run lint

# Run end-to-end tests
npm run test:e2e
```

## Project Structure

```
services/web/
├── src/
│   ├── app/                    # Next.js app router pages
│   │   ├── _components/        # Shared components (AppShell, Badge, etc.)
│   │   ├── vaults/             # Vault pages (raw, enriched, live)
│   │   ├── ops/                # Ops pages (inbox, bulk, jobs, etc.)
│   │   ├── layout.tsx          # Root layout with AppShell
│   │   └── page.tsx            # Home page (Ops Workbench)
│   ├── components/             # Reusable UI components
│   │   ├── ui/                 # UI primitives (buttons, cards, etc.)
│   │   ├── tables/             # Table components (DataTable)
│   │   └── inspector/          # Entity inspector drawer
│   └── lib/                    # Shared utilities
│       ├── api.ts              # API client (client-side)
│       ├── demoMode.ts         # Demo mode detection
│       └── toastContext.tsx    # Toast notification system
├── fixtures/                   # Demo mode fixture data
│   ├── vault1.json
│   ├── vault2.json
│   ├── vault3.json
│   └── ops_summary.json
├── public/                     # Static assets
├── tests/                      # Playwright e2e tests
└── package.json
```

## Key Concepts

### API Proxy

All API calls go through `/api/proxy/[...path]` to avoid CORS issues and centralize error handling. The proxy forwards requests to the backend API.

**Example**:
- Frontend calls: `GET /api/proxy/vaults/raw?page=1`
- Proxy forwards to: `GET http://127.0.0.1:8000/vaults/raw?page=1`

### Demo Mode

When the API health check fails, the app enters demo mode:
1. `lib/demoMode.ts` checks `/api/proxy/health` on load
2. If it fails, `isDemoMode()` returns `true`
3. Pages use `getDemoData(key)` to load fixture JSON instead of API calls
4. Actions are disabled or show simulation toasts

### Server vs Client Components

- **Server Components** (default): Render on the server, can fetch data directly
- **Client Components** (`"use client"`): Render in browser, needed for interactivity

**When to use client components**:
- Need React hooks (useState, useEffect, etc.)
- Need browser APIs (localStorage, window, etc.)
- Need event handlers (onClick, onChange, etc.)

**Example**: Vault pages are server components (fetch data), inspector drawer is a client component (interactive).

## Development Workflow

### Adding a New Page

1. Create `src/app/my-page/page.tsx`
2. Add route to navigation in `src/app/_components/AppShell.tsx`
3. Use `PageHeader` component for consistent styling
4. Fetch data via `apiGet()` in server components or `lib/api.ts` in client components

### Adding a New Component

1. Create component in `src/components/[category]/MyComponent.tsx`
2. Export from component file
3. Import and use in pages

### Styling Guidelines

- Use Tailwind CSS classes for all styling
- Follow existing color palette (slate for neutrals, emerald for success, red for danger)
- Use consistent spacing scale: `space-y-4`, `gap-3`, `p-4`, etc.
- Prefer `rounded-xl` for cards, `rounded-md` for buttons/inputs

### Testing

Run Playwright tests before committing:

```bash
npm run test:e2e
```

Add new tests in `tests/*.spec.ts` for new features.

## Troubleshooting

### "Fetch failed" errors

**Symptom**: Console errors about fetch failures when loading pages.

**Solutions**:
1. Check that API is running: `curl http://127.0.0.1:8000/health`
2. Verify `NEXT_PUBLIC_API_BASE_URL` is correct
3. Try using `127.0.0.1` instead of `localhost`
4. If API is unavailable, demo mode should activate automatically

### Demo mode not activating

**Symptom**: App shows errors instead of loading fixtures when API is offline.

**Solutions**:
1. Clear browser cache and hard reload (Ctrl+Shift+R)
2. Check browser console for errors in `demoMode.ts`
3. Verify fixture files exist in `fixtures/` directory

### Build failures

**Symptom**: `npm run build` fails with TypeScript or lint errors.

**Solutions**:
1. Run `npm run lint` to see lint errors
2. Fix TypeScript errors in reported files
3. Ensure all imports are correct
4. Check that all required props are passed to components

### Slow development server

**Symptom**: Hot reload is slow or pages take long to load.

**Solutions**:
1. Reduce enabled features in dev mode if needed
2. Clear `.next` cache: `rm -rf .next` (or `rmdir /s .next` on Windows)
3. Restart dev server

## Changes Checklist

When making changes to the frontend:

- [ ] Run `npm run lint` — fix any errors
- [ ] Run `npm run build` — ensure build succeeds
- [ ] Test in demo mode (API offline)
- [ ] Test in normal mode (API online)
- [ ] Check browser console for errors
- [ ] Run `npm run test:e2e` — verify tests pass
- [ ] Update this doc if changing architecture or workflow
- [ ] Commit with clear message (e.g., `web: add feature X`)

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [React Documentation](https://react.dev)
- [Playwright Documentation](https://playwright.dev)
