# Frontend Guide

The frontend is a React app in `frontend/` (Create React App).

## What the Current UI Supports
- Register and login.
- Upload project ZIP files.
- List projects and view project report details.
- View contributors and snapshot skill badges.
- View top ranked projects.
- View portfolio skills timeline.
- Trigger resume generation and open generated PDF.

## Run Frontend Locally
```bash
cd frontend
npm install
npm start
```

Default URL:
- `http://localhost:3000`

API base URL env var:
- `REACT_APP_API_URL` (defaults to `http://localhost:5001` in `frontend/src/api.js`)

Example:
```bash
export REACT_APP_API_URL='http://localhost:5001'
```

## Key Files
- `frontend/src/App.js`
  - Auth state and dashboard shell wiring.
- `frontend/src/Auth.jsx`
  - Login/register UI.
- `frontend/src/Dashboard.jsx`
  - Main project dashboard views and actions.
- `frontend/src/api.js`
  - API helper client module with token-aware wrappers.

## Notes on Current State
- The dashboard currently calls `/projects` with bearer token and no query params, which works because the API derives the default portfolio from auth context.
- There are two API client implementations (`App.js` inline object and `src/api.js`). Keeping one shared client would reduce drift.
- Error handling is mostly inline and user-facing; consider centralized handling if frontend scope expands.

## Docker Workflow
`docker-compose.yml` includes a `frontend` service on port `3000` with bind mount hot-reload.

Start all services:
```bash
docker compose up --build
```
