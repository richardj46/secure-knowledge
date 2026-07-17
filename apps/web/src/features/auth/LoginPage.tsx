import { type FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { getAccessToken, storeAccessToken } from "../../shared/auth/tokens";
import { AuthApiError, login } from "./authApi";

interface LoginLocationState {
  email?: string;
  from?: string;
  message?: string;
}

export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as LoginLocationState | null) ?? {};
  const [email, setEmail] = useState(state.email ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (getAccessToken()) {
    return <Navigate to="/admin" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const token = await login(email, password);
      if (token.token_type.toLowerCase() !== "bearer") {
        throw new AuthApiError("The server returned an unsupported token.", 500);
      }
      storeAccessToken(token.access_token);
      const destination =
        state.from?.startsWith("/") && !state.from.startsWith("//")
          ? state.from
          : "/admin";
      navigate(destination, { replace: true });
    } catch (caughtError) {
      setError(
        caughtError instanceof AuthApiError
          ? caughtError.message
          : "Unable to sign in. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-introduction">
        <p className="eyebrow">SecureKnowledge</p>
        <h1>Inspect knowledge systems with confidence.</h1>
        <p>
          Sign in to review retrieval evidence, answer citations, ingestion
          failures, evaluation regressions, and organization audit events.
        </p>
      </section>

      <section className="auth-card" aria-labelledby="login-title">
        <div>
          <p className="eyebrow">Welcome back</p>
          <h2 id="login-title">Sign in</h2>
          <p>Use your organization account to continue.</p>
        </div>

        {state.message ? (
          <p className="auth-notice" role="status">
            {state.message}
          </p>
        ) : null}
        {error ? (
          <p className="auth-error" role="alert">
            {error}
          </p>
        ) : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email address
            <input
              autoComplete="email"
              autoFocus
              maxLength={320}
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              maxLength={128}
              minLength={10}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          <button disabled={submitting} type="submit">
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="auth-alternative">
          New to SecureKnowledge? <Link to="/register">Create an account</Link>
        </p>
      </section>
    </main>
  );
}
