## Testing (Regression + Functionality)

This repo uses **browser-agent E2E tests** for the admin console.

### Run the stack

```bash
docker-compose up -d
```

### Run browser-agent tests (Playwright)

```bash
cd services/web
npm run test:e2e
```

Notes:
- Tests assume `web` is reachable at `http://localhost:3000`.
- If you run services on different ports, set `PLAYWRIGHT_BASE_URL`.

