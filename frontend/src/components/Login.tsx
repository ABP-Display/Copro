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
  const [challenge, setChallenge] = useState(false);
  const [code, setCode] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("session");
      const data = await api<{ user?: User; mfa_required?: boolean }>(challenge ? "login/verify" : "login", "POST", challenge ? { code } : { username, password });
      if (data.mfa_required) { setChallenge(true); setPassword(""); setCode(""); }
      else if (data.user) onLogin(data.user);
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
          <p className="muted">{challenge ? "Saisissez le code de votre application d’authentification, ou un code de secours. Cette étape expire après cinq minutes." : "Connectez-vous pour retrouver votre collectif."}</p>
          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}
          {!challenge && <><label>
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
          </label></>}
          {challenge && <label>Code d’authentification ou code de secours<input autoFocus autoComplete="one-time-code" required maxLength={40} value={code} onChange={e => setCode(e.target.value)} /></label>}
          <button disabled={busy} className="button primary login-submit">
            {busy ? "Vérification…" : challenge ? "Vérifier le code" : "Se connecter"}
            <Icon name="arrow" size={18} />
          </button>
          {challenge && <button type="button" className="text-link" onClick={() => { setChallenge(false); setCode(""); setError(""); }}>Revenir au mot de passe</button>}
          <p className="login-help">
            Gestionnaires et copropriétaires : connectez-vous à votre espace.
          </p>
        </form>
      </section>
    </div>
  );
}
