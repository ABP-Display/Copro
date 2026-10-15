import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Icon } from "./ui";
export function CouncilUpload({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api("council/upload", "POST", data);
      onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={ref}
      className="editor-dialog council-dialog"
      aria-labelledby="council-upload-title"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <form onSubmit={(e) => void submit(e)}>
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">PIÈCES DE GESTION</p>
            <h2 id="council-upload-title">Ajouter un justificatif</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            disabled={busy}
            onClick={onClose}
            aria-label="Fermer"
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="form-fields">
          <p className="muted">
            La pièce sera consultable par l’équipe de gestion et de contrôle.
            Elle ne sera pas publiée dans l’espace commun des copropriétaires.
          </p>
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <label>
            Titre de la pièce
            <input name="title" required maxLength={150} />
          </label>
          <label>
            Fichier PDF ou image
            <input
              type="file"
              name="file"
              required
              accept=".pdf,.png,.jpg,.jpeg"
            />
            <small>PDF, PNG ou JPEG · 10 Mo maximum.</small>
          </label>
        </div>
        <div className="dialog-footer">
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={onClose}
          >
            Annuler
          </button>
          <button className="button primary" disabled={busy}>
            {busy ? "Ajout…" : "Ajouter la pièce"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
