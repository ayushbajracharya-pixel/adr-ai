## ADR AI Client

A Vite + React + TypeScript frontend for ADR AI.

---

### Prerequisites

- Node.js 18+ (LTS recommended)
- npm (or pnpm/yarn)

---

### Quick start

1) Install dependencies
```bash
cd client
npm install
```

2) Configure environment
```bash
# Create client/.env (or .env.local) with:
VITE_API_BASE_URL=http://localhost:8000/api
# Optional: choose a dev port for the client (avoid 8000 which the server uses)
PORT=3000
```
Notes:
- The server exposes its REST API under `/api` (e.g. `/api/query`, `/api/upload`, `/api/files`).
- The client sends requests to `VITE_API_BASE_URL + route`, so make sure `/api` is included.

3) Run the development server
```bash
npm run dev
```
Open `http://localhost:5173` (or the port you set in `PORT`).

4) Ensure the backend is running
- Start the FastAPI server following `server/README.md` (default: `http://localhost:8000`).

---

### Available scripts

```bash
# Start the Vite dev server
npm run dev

# Build for production
npm run build

# Preview the production build locally
npm run preview

# Lint the project
npm run lint
```

Dev server settings (see `vite.config.ts`):
- Host: `::` (LAN-accessible)
- Port: read from `PORT` in env, fallback is 8000. If your server uses 8000, set `PORT=5173` in `.env`.

---

### Project structure (client)

```text
client/
  src/
    constants/
      apiRoutes.ts        # '/query', '/files', '/upload', '/files/:objectKey'
      env-contants.ts     # reads VITE_API_BASE_URL
    lib/
      api.ts              # axios instance + chat/file APIs
    ...                   # UI, routes, components
  vite.config.ts          # alias '@' -> './src', PORT from env
  package.json
  README.md
```

Path alias:
- Import from `src` using `@`, e.g. `import { chatApi } from '@/lib/api'`.

---

### Troubleshooting

- Requests fail or are blank: verify `VITE_API_BASE_URL` includes `/api`, e.g. `http://localhost:8000/api`.
- Port conflict: set `PORT=5173` in `client/.env`.
- CORS/network errors: ensure the server is running and reachable at `http://localhost:8000`.


