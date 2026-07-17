import { type FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { getAccessToken } from "../../shared/auth/tokens";
import { AuthApiError, register } from "./authApi";

export function RegisterPage() {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (getAccessToken()) {
    return <Navigate to="/admin" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await register({ displayName, email, password });
      navigate("/login", {
        replace: true,
        state: {
          email: email.trim(),
          message: "Account created. Sign in with your new credentials.",
        },
      });
    } catch (caughtError) {
      setError(
        caughtError instanceof AuthApiError
          ? caughtError.message
          : "Unable to create your account. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-introduction">
        <p className="eyebrow">SecureKnowledge</p>
        <h1>Build a secure home for organizational knowledge.</h1>
        <p>
          Create your user account, then establish or join an organization with
          permission-aware workspaces, documents, retrieval, and answers.
        </p>
      </section>

      <section className="auth-card" aria-labelledby="register-title">
        <div>
          <p className="eyebrow">Get started</p>
          <h2 id="register-title">Create an account</h2>
          <p>Your password must contain at least 10 characters.</p>
        </div>

        {error ? (
          <p className="auth-error" role="alert">
            {error}
          </p>
        ) : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Display name <span>Optional</span>
            <input
              autoComplete="name"
              maxLength={200}
              onChange={(event) => setDisplayName(event.target.value)}
              type="text"
              value={displayName}
            />
          </label>
          <label>
            Email address
            <input
              autoComplete="email"
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
              autoComplete="new-password"
              maxLength={128}
              minLength={10}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          <label>
            Confirm password
            <input
              autoComplete="new-password"
              maxLength={128}
              minLength={10}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              type="password"
              value={confirmPassword}
            />
          </label>
          <button disabled={submitting} type="submit">
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="auth-alternative">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
}
