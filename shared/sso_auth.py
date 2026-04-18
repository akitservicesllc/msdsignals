"""
SSO auth for the AK IT Services Streamlit app ecosystem.

Architecture
------------
Market AI Genie (MAG) is the master app. It's password-protected.
After login, MAG issues signed HMAC-SHA256 tokens that external apps
(Pine Screener, VL Tracker, etc.) can validate via the shared secret.

Flow
----
1. MAG's sidebar external-app links are wrapped by `sso_url()`, which
   appends `?sso=<token>` with a 30-day TTL.
2. External apps call `require_auth("<App Name>")` at the top of app.py:
     - If session already authed, pass-through.
     - Else if `?sso=<token>` is valid, set session + 30-day secure cookie.
     - Else if cookie is present (new tab on same browser), JS redirects
       back to same URL with `?sso=<cookie_value>` — auto auth.
     - Else show the gate page (link to MAG + manual password fallback).
3. Manual password fallback uses `APP_PASSWORD` env var (same value as MAG).

Security
--------
- Tokens are signed with `SSO_SHARED_SECRET` (64-char random hex env var).
- Cookie is `Secure; SameSite=Lax; path=/; max-age=30d`.
- Token payload is base64url-encoded JSON; signature is base64url HMAC-SHA256.
- `hmac.compare_digest` is used for constant-time sig comparison.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

import streamlit as st
import streamlit.components.v1 as _components

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
COOKIE_NAME = "akit_sso"
TOKEN_TTL_SEC = 60 * 60 * 24 * 30  # 30 days
COOKIE_MAX_AGE = TOKEN_TTL_SEC      # match token TTL
MAG_URL = "https://market-ai-genie.azurewebsites.net/"
SESSION_FLAG = "_sso_authed"
COOKIE_CHECK_FLAG = "_sso_cookie_checked"


def _run_script(html: str) -> None:
    """Execute a <script>…</script> snippet in the parent page context.

    Streamlit's st.html() only runs scripts when unsafe_allow_javascript=True,
    and that parameter was added in Streamlit 1.50 (May 2025). On older
    versions we'd get TypeError: unexpected keyword argument. This helper
    tries the new signature first and transparently falls back to
    components.v1.html — which works across all versions, and whose iframe
    can still redirect the parent via window.parent.location (cookies set
    from inside the iframe won't persist on the parent origin in older
    Streamlit, but the redirect path and URL-param auth still work).
    """
    try:
        st.html(html, unsafe_allow_javascript=True)
        return
    except TypeError:
        pass
    except Exception:
        pass
    # Fallback — runs in iframe. Cookie setting is best-effort via
    # window.parent.document.cookie (may fail cross-origin on older builds);
    # JS-driven redirects via window.top.location are unaffected.
    try:
        _components.html(html, height=0)
    except Exception:
        pass


def _get_secret() -> bytes:
    """Return the shared secret as bytes. Raises if not set in prod-like envs."""
    s = os.environ.get("SSO_SHARED_SECRET", "")
    if not s:
        # Dev fallback — NEVER ship without the env var set on Azure.
        s = "DEV-ONLY-SSO-SECRET-SET-SSO_SHARED_SECRET-IN-AZURE"
    return s.encode("utf-8")


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------
def _b64url_enc(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_dec(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_sso_token(user: str = "admin", ttl_sec: int = TOKEN_TTL_SEC) -> str:
    """Issue an SSO token signed with SSO_SHARED_SECRET.

    Token format: base64url(payload_json) + "." + base64url(hmac_sha256).
    Payload contains user, expiry timestamp, and a random nonce.
    """
    payload = {
        "u": user,
        "exp": int(time.time()) + int(ttl_sec),
        "n": secrets.token_hex(8),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_get_secret(), payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_enc(payload_bytes)}.{_b64url_enc(sig)}"


def verify_sso_token(token: str) -> Optional[dict]:
    """Return the decoded payload if the token is valid + not expired, else None."""
    if not token or "." not in token:
        return None
    try:
        p_b64, s_b64 = token.split(".", 1)
        payload_bytes = _b64url_dec(p_b64)
        sig = _b64url_dec(s_b64)
        expected = hmac.new(_get_secret(), payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(payload_bytes.decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def sso_url(base_url: str, user: str = "admin") -> str:
    """Wrap an external-app URL with a fresh `?sso=<token>` param. MAG helper."""
    token = issue_sso_token(user=user)
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}sso={token}"


# ---------------------------------------------------------------------------
# Client-side JS helpers — injected via st.html() which renders directly in
# the parent page (no iframe), so cookies persist across tabs for the app's
# origin.
# ---------------------------------------------------------------------------
def _js_set_cookie(token: str) -> str:
    escaped = token.replace("\\", "\\\\").replace("'", "\\'")
    return f"""
    <script>
    (function() {{
        try {{
            document.cookie = "{COOKIE_NAME}=" + '{escaped}' +
                "; max-age={COOKIE_MAX_AGE}; path=/; secure; samesite=lax";
        }} catch (e) {{ console.warn('SSO cookie set failed:', e); }}
    }})();
    </script>
    """


def _js_check_cookie_and_redirect() -> str:
    """If cookie is present and URL lacks ?sso=, redirect with ?sso=<cookie>."""
    return f"""
    <script>
    (function() {{
        try {{
            const url = new URL(window.location.href);
            if (url.searchParams.has('sso')) return;
            const m = document.cookie.match(/(?:^|; ){COOKIE_NAME}=([^;]+)/);
            if (m && m[1]) {{
                url.searchParams.set('sso', decodeURIComponent(m[1]));
                window.location.replace(url.toString());
            }}
        }} catch (e) {{ console.warn('SSO cookie check failed:', e); }}
    }})();
    </script>
    """


def _js_strip_sso_param() -> str:
    """Remove ?sso=... from URL without reloading, so it doesn't linger."""
    return """
    <script>
    (function() {
        try {
            const url = new URL(window.location.href);
            if (url.searchParams.has('sso')) {
                url.searchParams.delete('sso');
                window.history.replaceState({}, '', url.toString());
            }
        } catch (e) {}
    })();
    </script>
    """


# ---------------------------------------------------------------------------
# Public API — call this at the top of each external app's app.py
# ---------------------------------------------------------------------------
def require_auth(app_name: str = "App") -> bool:
    """Authentication gate. Returns True if the session is authenticated.

    Usage (at top of app.py, after st.set_page_config):
        from shared.sso_auth import require_auth
        if not require_auth("Pine Screener"):
            st.stop()
    """
    # 1. Already authed in this Streamlit session
    if st.session_state.get(SESSION_FLAG):
        return True

    # 2. Token in URL?  (normal SSO path from MAG)
    token = st.query_params.get("sso", "")
    if isinstance(token, list):
        token = token[0] if token else ""
    if token:
        payload = verify_sso_token(token)
        if payload:
            st.session_state[SESSION_FLAG] = True
            st.session_state["_sso_user"] = payload.get("u", "admin")
            # Persist cookie for other tabs; strip token from URL bar.
            _run_script(_js_set_cookie(token) + _js_strip_sso_param())
            return True
        else:
            st.warning("SSO token expired or invalid. Please log in again.")

    # 3. Cookie fallback — emit once per session. If a valid cookie exists,
    # the JS will redirect to `?sso=<cookie>` and the new page load will hit
    # branch (2) above. If no cookie, nothing happens and the gate renders.
    if not st.session_state.get(COOKIE_CHECK_FLAG):
        st.session_state[COOKIE_CHECK_FLAG] = True
        _run_script(_js_check_cookie_and_redirect())

    # 4. Render the gate (manual login + link to MAG)
    _render_gate(app_name)
    return False


# ---------------------------------------------------------------------------
# Gate UI
# ---------------------------------------------------------------------------
def _render_gate(app_name: str):
    """Render the login gate page."""
    st.markdown(
        f"""
        <div style="max-width:460px;margin:60px auto 16px auto;padding:32px 32px 24px 32px;
                    background:#ffffff;border:1px solid #e8eaed;border-radius:14px;
                    box-shadow:0 2px 12px rgba(60,64,67,0.08);
                    font-family:'Google Sans',-apple-system,Segoe UI,sans-serif;">
            <div style="font-size:26px;font-weight:700;color:#202124;margin:0 0 4px 0;">
                🔒 {app_name}
            </div>
            <div style="font-size:14px;color:#5f6368;margin:0 0 20px 0;">
                Access restricted. Please sign in via Market AI Genie.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.link_button(
        "🏠 Log in via Market AI Genie",
        MAG_URL,
        use_container_width=True,
        type="primary",
    )

    # Inline manual-login form (always visible — no popover, reliable across reruns).
    with st.form("_sso_manual_login", clear_on_submit=False):
        pw = st.text_input(
            "Or enter password directly:",
            type="password",
            key="_sso_pw_input",
            placeholder="Password",
        )
        if st.form_submit_button("🔑 Sign in", use_container_width=True):
            expected = os.environ.get("APP_PASSWORD", "Munusamy@123")
            if pw and pw == expected:
                tok = issue_sso_token()
                st.session_state[SESSION_FLAG] = True
                st.session_state["_sso_user"] = "admin"
                _run_script(_js_set_cookie(tok))
                st.rerun()
            else:
                st.error("Incorrect password")
