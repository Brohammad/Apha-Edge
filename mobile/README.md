# AlphaEdge Mobile

React Native (Expo) companion app for portfolio overview and order monitoring on iOS and Android.

## Setup

```bash
cd mobile
npm install
npm start
```

Set the API URL in `app.json` → `extra.apiBaseUrl` (default `http://localhost:8000/api/v1`).

For device testing, use your machine's LAN IP instead of `localhost`.

## Screens

- **Login** — JWT auth with secure token storage
- **Overview** — portfolio list and cash balances
- **Orders** — live order blotter

## Production

```bash
npx expo prebuild
eas build --platform all
```

See [Expo docs](https://docs.expo.dev/) for store submission.
