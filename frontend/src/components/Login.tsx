import React, { useState } from "react";
import { api, type User } from "../api";
import { Icon, BuildingIllustration } from "./ui";
import { BrandMark } from "./BrandMark";
export function Login({
  onLogin,
  error: initialError,
}: {
  onLogin: (user: User) => void;
  error: string;
}) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(initialError);
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("session");
      const data = await api<{ user: User }>("login", "POST", {
        username,
        password,
      });
      onLogin(data.user);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-layout">
      <section className="login-story">
        <a className="brand" href="/">
          <BrandMark />
          <span>Copro.</span>
        </a>
        <div>
          <p className="eyebrow">VOTRE COPROPRIÉTÉ, ENSEMBLE</p>
          <h1>
            Un lieu de vie.
            <br />
            Un projet commun.
          </h1>
          <p>
            Moins de dispersion.
            <br />
            Plus de clarté pour votre immeuble.
          </p>
          <BuildingIllustration />
        </div>
        <span className="login-footnote">Pensé pour une gestion partagée.</span>
      </section>
      <section className="login-form-side">
        <form className="login-form" onSubmit={submit}>
          <span className="section-icon">
            <Icon name="shield" size={24} />
          </span>
          <p className="eyebrow">BIENVENUE CHEZ VOUS</p>
          <h2>Votre espace copropriété</h2>
          <a href="/presentation" className="login-project-link">
            Découvrir le projet Copro.
          </a>
          <p className="muted">
            Connectez-vous pour retrouver votre collectif.
          </p>
          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}
          <label>
            Courriel ou identifiant gestionnaire
            <input
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label>
            Mot de passe
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button disabled={busy} className="button primary login-submit">
            {busy ? "Connexion…" : "Se connecter"}
            <Icon name="arrow" size={18} />
          </button>
          <p className="login-help">
            Gestionnaires et copropriétaires : connectez-vous à votre espace.
          </p>
        </form>
      </section>
    </div>
  );
}
