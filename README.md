# DISHA v1.0.1 Clean Functional Build

**DISHA – Local Services OS**  
**An ASTRA Technologies Product**

This package uses one fixed stack:

- Frontend: React Native / Expo Router
- Backend: Python FastAPI
- Database: MongoDB
- APK Build: GitHub Actions local Android debug build

## Repository root must contain

```text
.github/
frontend/
backend/
docs/
README.md
```

Do not upload only the workflow. Do not upload only a nested folder.

## What works in this build

- Register / login with email or mobile + password
- Terms acceptance before registration
- Session save / auto-login
- Purpose selection: service taker, provider, both
- Category listing from backend
- Provider setup and edit with per-service price
- Provider search and category filter
- Provider detail
- Booking creation
- Customer booking list
- Provider booking list
- Booking status update with permission checks
- Basic chat threads and messages
- Real unread count from backend
- Settings, Privacy Policy, Terms, Delete Account, Logout
- Backend auto-seeds categories on startup
- GitHub Actions APK workflow

## Not included in v1.0 scope

- Google login
- Mobile OTP
- Maps live integration
- Weather API
- Online payment
- Push notification

These are intentionally excluded from this build so the current foundation stays stable.

## Copyright

Copyright © Astra Technologies. All Rights Reserved.


## v1.0.1 security/production fixes
See `docs/PRODUCTION_FIXES_1_0_1.md` and `CHECK_REPORT.md`.
