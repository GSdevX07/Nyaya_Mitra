# Nyaya Mitra: Zero-Downtime Credential & Secret Rotation Standard Operating Procedure

**Document Version**: 1.0  
**Target Audience**: Security Operations Engineers, Database Administrators, DevOps  
**Review Cycle**: Biannual / Immediately upon suspected compromise

---

## 1. Overview & Rotation Principles

Nyaya Mitra coordinates with multiple external services and manages critical secrets:
1. `JWT_SECRET`: Signing token for internal and institutional API sessions.
2. `SUPABASE_SERVICE_KEY`: Master service role key for cloud PostgreSQL persistence.
3. Database Passwords (`DB_PASSWORD`): Master and pooled credentials.
4. AI Provider API Keys (`GROQ_API_KEY`, Watsonx credentials, etc.).

### Zero-Downtime Rotation Principles
- **Dual-Key Verification Windows**: Support previous and current verification keys during active rollover windows.
- **Automated Revocation on Roll**: Old sessions are terminated gracefully or allowed to expire within TTL limits.
- **Audit Logging**: Every key rotation generates a `KEY_ROTATED` audit record in the immutable audit ledger.

---

## 2. Step-by-Step Rotation Procedures

### Procedure 1: JWT Secret Rotation (`JWT_SECRET`)
1. **Preparation**:
   - Generate a cryptographically strong 256-bit random string:
     ```bash
     python -c "import secrets; print(secrets.token_urlsafe(48))"
     ```
2. **Phase 1: Secondary Verification Deployment**:
   - In `auth/config.py`, configure `JWT_SECRET` as the new primary key for signing new tokens, while maintaining `JWT_SECRET_PREVIOUS` in the verification algorithm list.
   - Deploy backend service. All new logins receive tokens signed by the new key. Existing valid tokens continue to verify against the previous key.
3. **Phase 2: Transition Window**:
   - Allow existing tokens to reach their maximum access TTL (60 minutes).
4. **Phase 3: Retirement & Invalidation**:
   - Remove `JWT_SECRET_PREVIOUS`.
   - Any unrefreshed sessions must re-authenticate.
   - Record `KEY_ROTATED` audit event.

---

### Procedure 2: Supabase Service Key Rotation (`SUPABASE_SERVICE_KEY`)
1. Log in to the Supabase Cloud Management Dashboard.
2. Navigate to **Project Settings** -> **API**.
3. Under **Project API Keys**, select **Roll Key** -> **Service Role Key**.
4. Specify an active rollover grace period (e.g. 2 hours).
5. Update the secret in the cloud vault (`CloudVaultSecretManager` or deployment secret store).
6. Trigger rolling deployment of the backend service.
7. Verify successful read/write test:
   ```bash
   python -c "from app.supabase_adapter import get_supabase_client; c = get_supabase_client(); print(c.table('cases').select('id').limit(1).execute())"
   ```
8. Confirm key revocation in the Supabase management console.

---

### Procedure 3: Third-Party LLM Provider Keys (`GROQ_API_KEY`, Watsonx)
1. Generate a new API key in the provider console (e.g. Groq Console / IBM Cloud IAM).
2. Store the new key in the secret manager under `GROQ_API_KEY_NEW`.
3. Switch primary reference in the secret manager or runtime configuration.
4. Execute health check test against the AI Gateway.
5. Invalidate the old key in the provider console.

---

## 3. Emergency Incident Key Invalidation (Compromise Protocol)
If a secret is exposed in logs, public git repositories, or compromised infrastructure:
1. **Immediate Invalidation**: Delete or roll the compromised key immediately; do NOT use a grace period.
2. **Session Flush**: Invoke `POST /auth/sessions/revoke-all` to invalidate all active session tokens immediately.
3. **Breach Audit**: Run audit log query filtering on the actor or time window of the compromise.
4. **Declare Incident**: Trigger `declare_incident("CREDENTIAL_COMPROMISE")` in `incident_response.py`.
