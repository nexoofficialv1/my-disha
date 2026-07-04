# DISHA v1.0.1 Check Report

## Stack locked
- Frontend: React Native / Expo
- Backend: Python FastAPI
- Database: MongoDB
- APK Build: GitHub Actions local Expo prebuild + Gradle debug APK

## Audit fixes applied
- Provider auto-approval: FIXED. Default is `PENDING`; public listing shows only `APPROVED`.
- Admin approval route: ADDED. Use `X-Admin-Key` header.
- passlib/bcrypt conflict: FIXED with `bcrypt==4.0.1`.
- CORS wildcard+credentials: FIXED via `CORS_ORIGINS` and dynamic credentials flag.
- JWT_SECRET production fallback: FIXED. `APP_ENV=production` requires `JWT_SECRET`.
- Android localhost API default: FIXED. `.env.example` uses production API placeholder and LAN example.
- Branding assets: ADDED icon, adaptive icon, splash.
- Chat polling: ADDED 5-second polling.
- FastAPI 422 error display: FIXED readable normalization.
- .gitignore: ADDED.
- Settings footer `\n`: FIXED.
- Booking date/time text input: REPLACED with native DateTimePicker.
- Login keyboard: FIXED dynamic phone/email keyboard.

## Static checks run in this environment
- Python syntax compile: PASS
- Required files present: PASS
- ZIP root structure: PASS

## Not run here
- Full npm install / Gradle APK build not run inside this environment.
- Backend runtime test requires MongoDB.
- E2E app test requires Android/Expo build environment.
