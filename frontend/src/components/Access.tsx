import { useEffect, useRef, useState } from "react";
import { api, type User } from "../api";
import { Icon } from "./ui";
export type Credentials = { email: string; temporary_password: string };

export function CredentialsDialog({
  credentials,
  onClose,
}: {
  credentials: Credentials;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [url, setUrl] = useState(window.location.origin);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const valid = /^https?:\/\/[^\s]+$/i.test(url);
  const body = `Bonjour,\n\nVoici votre accès à l’espace de la copropriété :\n${url}\n\nIdentifiant : ${credentials.email}\nMot de passe temporaire : ${credentials.temporary_password}\n\nVous devrez choisir votre propre mot de passe à la première connexion. Votre accès permet de consulter les informations partagées.\n\nÀ bientôt.`;
  const mailto = `mailto:${encodeURIComponent(credentials.email)}?subject=${encodeURIComponent("Votre accès à l’espace copropriété")}&body=${encodeURIComponent(body)}`;
  return (
    <dialog
      ref={dialog}
      className="editor-dialog"
      aria-labelledby="access-title"
      onCancel={onClose}
    >
      <div className="dialog-heading">
        <div>
          <p className="eyebrow">ACCÈS COPROPRIÉTAIRE</p>
          <h2 id="access-title">Les accès sont prêts</h2>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Fermer">
          <Icon name="close" />
        </button>
      </div>
      <div className="form-fields">
        <p className="muted">
          Le mot de passe est affiché une seule fois. Il devra être changé lors
          de la première connexion.
        </p>
        <label>
          Identifiant
          <input readOnly value={credentials.email} />
        </label>
        <label>
          Mot de passe temporaire
          <input readOnly value={credentials.temporary_password} />
        </label>
        <label>
          Adresse de l’application
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            type="url"
          />
          <small>
            Une adresse localhost n’est accessible que depuis cet ordinateur.
            Renseignez l’adresse partagée avant d’envoyer les accès.
          </small>
        </label>
      </div>
      <div className="dialog-footer">
        <button className="button secondary" onClick={onClose}>
          Fermer
        </button>
        {valid && (
          <a className="button primary" href={mailto}>
            <Icon name="mail" size={16} />
            Préparer le courriel
          </a>
        )}
      </div>
    </dialog>
  );
}

export function ChangePassword({
  onChanged,
  onCancel,
  mandatory = false,
}: {
  onChanged: (user: User) => void;
  onCancel: () => void;
  mandatory?: boolean;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    if (data.new_password !== data.confirm_password) {
      setError("Les deux nouveaux mots de passe doivent être identiques.");
      return;
    }
    setBusy(true);
    try {
      const result = await api<{ user: User }>("password", "POST", data);
      onChanged(result.user);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel password-panel">
      <div className="panel-heading">
        <div>
          <h2>
            {mandatory
              ? "Choisissez votre mot de passe"
              : "Changer mon mot de passe"}
          </h2>
          <p>
            {mandatory
              ? "Remplacez votre mot de passe temporaire pour ouvrir votre espace."
              : "Utilisez un mot de passe personnel d’au moins 12 caractères."}
          </p>
        </div>
      </div>
      <form className="form-fields" onSubmit={submit}>
        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}
        <label>
          Mot de passe actuel
          <input
            name="old_password"
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        <label>
          Nouveau mot de passe
          <input
            name="new_password"
            type="password"
            minLength={12}
            autoComplete="new-password"
            required
          />
        </label>
        <label>
          Confirmer le nouveau mot de passe
          <input
            name="confirm_password"
            type="password"
            minLength={12}
            autoComplete="new-password"
            required
          />
        </label>
        <div className="dialog-footer">
          <button type="button" className="button secondary" onClick={onCancel}>
            {mandatory ? "Se déconnecter" : "Annuler"}
          </button>
          <button className="button primary" disabled={busy}>
            {busy ? "Enregistrement…" : "Enregistrer mon mot de passe"}
          </button>
        </div>
      </form>
    </section>
  );
}
