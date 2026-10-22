# 19: User-Isolated MT5 Bridge Architecture and Authentication Security Hardening

**What to build:** Refactor authentication, persistence, and bridge telemetry to provide user-isolated MT5 trading sessions, token-based EA authentication, instantaneous token revocation on logout/password change, brute-force rate limiting, and password complexity hardening.

**Blocked by:** 03 (Auth and Connection Dashboard), 15 (Initial Deposit Telemetry and Persistence)

**Status:** done

## Problem Statement

TradeGear currently operates with a single global telemetry and trading execution state. When multiple users log into their separate web dashboard accounts, they all observe the exact same connected MetaTrader 5 (MT5) trading account, because incoming MT5 heartbeats do not identify or authenticate the owning user. An MT5 terminal connected from one user's laptop broadcasts equity, balance, floating P/L, and open positions to all other logged-in users, violating privacy and preventing independent trading monitoring. Furthermore, authentication lacks critical security protections: passwords can be as short as 4 characters, there is no rate limiting on login/registration endpoints against brute-force attacks, and JWT session tokens cannot be revoked on logout or password change, allowing potentially intercepted tokens to remain valid until expiration. Data is also persisted in flat JSON files without transaction safety or concurrency control.

## Solution

Transform TradeGear into a strictly user-isolated architecture where each TradeGear User owns their private MT5 bridge telemetry, AutoPilot automation, and Drawdown Guard risk management. Each user is provisioned a cryptographically random, high-entropy Bridge Token. MetaTrader 5 BridgeEA passes this token on every heartbeat. The backend validates the token and binds incoming telemetry exclusively to that user's isolated session. Telemetry and control endpoints require authentication and only expose the authenticated user's private MT5 data. Web authentication is hardened with strict password complexity requirements (minimum 8 alphanumeric characters), brute-force rate limiting (HTTP 429), instant token revocation via user token versioning, and migration of persistent state to an ACID-compliant SQLite database with zero external dependencies.

## User Stories

1. As a TradeGear User, I want to have a unique Bridge Token, so that I can securely connect my local MT5 terminal to my personal account.
2. As a TradeGear User, I want my connected MT5 account data (balance, equity, positions, deals) to be visible only to me, so that my financial data and trading activity remain strictly confidential.
3. As a TradeGear User, I want other logged-in users to have their own independent dashboard views, so that another user's MT5 connection or disconnection does not affect or overwrite mine.
4. As a TradeGear User, I want to view and copy my Bridge Token directly from the MT5 connection modal, so that I can easily configure BridgeEA without searching through settings.
5. As a TradeGear User, I want to view, copy, or regenerate my Bridge Token in my Profile tab, so that I can revoke compromised tokens without changing my web password.
6. As a TradeGear User, I want my previous Bridge Token to become immediately invalid when I regenerate it, so that unauthorized terminals can no longer transmit data to my dashboard.
7. As a TradeGear User, I want my AutoPilot mode to be isolated to my account, so that another user enabling or disabling AutoPilot does not alter my autonomous trading state.
8. As a TradeGear User, I want my Drawdown Guard to monitor only my account's peak-to-trough equity, so that another user's trading drawdown never locks out my system.
9. As a TradeGear User, I want my Emergency Kill Switch to close only my open positions, so that my trades can be closed without impacting other users' trades.
10. As a TradeGear User, I want to set a custom initial deposit benchmark for my own account, so that my All-Time P/L and performance curve reflect my personal capital.
11. As a TradeGear User, I want all active sessions to terminate immediately when I log out, so that my session token cannot be reused if my device is shared.
12. As a TradeGear User, I want all previous session tokens to be revoked immediately when I change my password, so that unauthorized active logins are terminated.
13. As a TradeGear User, I want to be enforced to use a strong password (minimum 8 characters with letters and numbers), so that my account is protected against credential cracking.
14. As a TradeGear User, I want existing accounts to remain accessible after system upgrades, so that I do not need to register again.
15. As a BridgeEA on a trader's laptop, I want to transmit my configured Bridge Token via HTTP header and JSON body, so that the backend can authenticate my heartbeat regardless of local network proxy restrictions.
16. As a BridgeEA on a trader's laptop, I want clear feedback on the MT5 chart HUD if my Bridge Token is invalid or missing, so that I know immediately to verify my token configuration.
17. As an administrator, I want brute-force login attempts to be rate-limited, so that dictionary and credential-stuffing attacks are thwarted.
18. As a system operator, I want user data and token associations to be stored in an ACID-compliant database, so that concurrent requests do not corrupt data.

## Implementation Decisions

- **Single Seam Principle**: All client-server interactions are handled at the top-level HTTP REST boundary. The backend acts as a cohesive service, exposing authenticated telemetry and management endpoints.
- **Persistent User & Token Storage**:
  - Migrate persistence from flat JSON files to a local SQLite database utilizing standard Python `sqlite3` with Write-Ahead Logging (WAL) for concurrency.
  - Define user schema with username (case-insensitive unique index), bcrypt password hash, role, unique bridge token (`tg_live_...`), token version integer for revocation, and active status flag.
  - Automatically migrate existing users and initial deposit preferences from existing JSON files upon startup, renaming the old files to prevent double-processing.
- **Authentication & Session Revocation**:
  - JWT access tokens encode both the username (`sub`) and current token version (`ver`).
  - Auth dependency resolves the user record and verifies that token `ver` matches the current database `token_version`. If mismatched, authentication fails with HTTP 401 Unauthorized.
  - Logout and password change operations increment `token_version` by 1 in the database, invalidating all pre-existing tokens immediately.
- **Brute-Force Rate Limiting**:
  - Implement an in-memory sliding window rate limiter for login and registration attempts keyed by client IP and target username.
  - Exceeding the threshold (5 failed attempts within 5 minutes) returns HTTP 429 Too Many Requests with a retry countdown.
- **Password Complexity Rules**:
  - Enforce minimum 8 characters, containing at least one alphabetical character and one numeric digit.
- **Multi-Tenant In-Memory Bridge & Risk State**:
  - Bridge service stores active sessions in a dictionary keyed by username.
  - Incoming heartbeat requires a valid Bridge Token extracted from the `X-Bridge-Token` header or `bridge_token` JSON body. Invalid or missing tokens return HTTP 401 Unauthorized.
  - Heartbeat telemetry updates only the session of the user associated with the token.
  - Status, quotes, position list, history, and equity curve endpoints require user authentication and read exclusively from that user's session.
  - AutoPilot and Drawdown Guard states are stored per username, preventing cross-user lockouts or autonomous trade collisions.
- **BridgeEA Modifications**:
  - Introduce `InpBridgeToken` input parameter in the Expert Advisor.
  - Include token in outgoing heartbeat requests (both in header and payload).
  - Update chart HUD to display `Unauthorized (Invalid Token)` when receiving HTTP 401.
- **Frontend Dashboard Updates**:
  - Provide Bridge Token visibility, one-click copy, and setup instructions in the MT5 Connection Modal.
  - Add a dedicated Bridge Credentials card in the Profile tab featuring masked token display, reveal toggle, copy action, and token regeneration with confirmation.

## Testing Decisions

- **What makes a good test**: Tests must verify observable system behavior from external seams (HTTP API requests and responses) without relying on internal private attributes.
- **Testing Scenarios**:
  - Multi-user telemetry isolation: User A posts heartbeat with Token A; User B posts heartbeat with Token B. Verify User A only receives MT5 A data, and User B only receives MT5 B data.
  - Unauthenticated heartbeat rejection: Heartbeat without token or with invalid token returns HTTP 401 Unauthorized.
  - Token revocation on logout: Generate access token, perform logout, verify subsequent requests with the same token return HTTP 401 Unauthorized.
  - Token revocation on password change: Change password, verify old token returns HTTP 401 Unauthorized.
  - Rate limiting enforcement: Five consecutive failed logins trigger HTTP 429 Too Many Requests.
  - Password complexity: Passwords shorter than 8 characters or lacking letters/digits return HTTP 400 Bad Request.
  - Auto-migration integrity: Start up with legacy JSON user records, verify accounts can authenticate successfully and receive valid bridge tokens.
- **Prior Art**: Extends existing test structure in `backend/tests/test_auth.py` and `backend/tests/test_bridge.py`.

## Out of Scope

- Multi-broker account switching under a single user login simultaneously (current model supports 1 active MT5 account per user).
- Web-based broker deposits or withdrawals.
- Manual order entry controls (system adheres strictly to Full-Auto Robot Trading).

## Further Notes

- Legacy accounts will be automatically migrated to SQLite upon initial launch with no manual database initialization required.
