import React, { useEffect, useRef, useState } from "react";
import { api, type Owner, type Lot } from "../api";
import { kinds } from "../format";
import { Icon } from "./ui";
import type { Credentials } from "./Access";
export function Editor({
  type,
  item,
  owners,
  onClose,
  onSaved,
  removing,
  setRemoving,
  onCredentials,
}: {
  type: "owners" | "lots";
  item?: Owner | Lot;
  owners: Owner[];
  onClose: () => void;
  onSaved: (deleted?: boolean) => Promise<void>;
  removing: boolean;
  setRemoving: (value: boolean) => void;
  onCredentials: (value: Credentials) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const owner = type === "owners" ? (item as Owner | undefined) : undefined;
  const lot = type === "lots" ? (item as Lot | undefined) : undefined;
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const data = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const result = await api<{ credentials?: Credentials }>(
        item ? `${type}/${item.id}` : type,
        item ? "PATCH" : "POST",
        data,
      );
      if (result.credentials) onCredentials(result.credentials);
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    setBusy(true);
    setError("");
    try {
      await api(`${type}/${item!.id}`, "DELETE");
      await onSaved(true);
    } catch (e) {
      setError((e as Error).message);
      setRemoving(false);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="editor-dialog"
      aria-labelledby="editor-title"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <form onSubmit={submit}>
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">
              {type === "owners" ? "LE COLLECTIF" : "VOTRE IMMEUBLE"}
            </p>
            <h2 id="editor-title">
              {item ? "Modifier" : "Ajouter"}{" "}
              {type === "owners" ? "un copropriétaire" : "un lot"}
            </h2>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Fermer"
            disabled={busy}
            onClick={onClose}
          >
            <Icon name="close" />
          </button>
        </div>
        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}
        <div className="form-fields">
          {type === "owners" ? (
            <>
              <div className="form-row">
                <label>
                  Prénom *
                  <input
                    name="first_name"
                    required
                    maxLength={100}
                    autoComplete="given-name"
                    defaultValue={owner?.first_name}
                  />
                </label>
                <label>
                  Nom *
                  <input
                    name="last_name"
                    required
                    maxLength={100}
                    autoComplete="family-name"
                    defaultValue={owner?.last_name}
                  />
                </label>
              </div>
              <label>
                Courriel (identifiant de connexion)
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  maxLength={254}
                  defaultValue={owner?.email}
                  placeholder="prenom@exemple.fr"
                />
              </label>
              <label>
                Téléphone
                <input
                  name="phone"
                  type="tel"
                  autoComplete="tel"
                  maxLength={30}
                  defaultValue={owner?.phone}
                  placeholder="06 00 00 00 00"
                />
              </label>
            </>
          ) : (
            <>
              <div className="form-row">
                <label>
                  Numéro du lot *
                  <input
                    name="number"
                    required
                    maxLength={30}
                    defaultValue={lot?.number}
                    placeholder="Ex. 001"
                  />
                </label>
                <label>
                  Type de lot
                  <select name="kind" defaultValue={lot?.kind || "apartment"}>
                    {Object.entries(kinds).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label>
                Copropriétaire
                <select name="owner" defaultValue={lot?.owner || ""}>
                  <option value="">À attribuer</option>
                  {owners.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.first_name} {o.last_name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-row">
                <label>
                  Étage
                  <input
                    name="floor"
                    maxLength={30}
                    defaultValue={lot?.floor}
                    placeholder="Ex. 2e étage"
                  />
                </label>
                <label>
                  Surface (m²)
                  <input
                    name="area"
                    type="number"
                    min="0"
                    step="0.01"
                    defaultValue={lot?.area}
                  />
                </label>
              </div>
              <label>
                Tantièmes généraux *
                <input
                  name="shares"
                  required
                  type="number"
                  min="0"
                  step="0.01"
                  defaultValue={lot?.shares || "0"}
                />
                <small>
                  Indiquez la quote-part inscrite au règlement de copropriété.
                </small>
              </label>
            </>
          )}
        </div>
        {removing && (
          <div className="delete-confirm" role="alert">
            <strong>Supprimer cet élément ?</strong>
            <p>Cette suppression est définitive.</p>
            <button
              type="button"
              className="button danger"
              disabled={busy}
              onClick={() => void remove()}
            >
              Confirmer la suppression
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={busy}
              onClick={() => setRemoving(false)}
            >
              Conserver
            </button>
          </div>
        )}
        <div className="dialog-footer">
          {item && !removing && (
            <button
              type="button"
              disabled={busy}
              className="delete-link"
              onClick={() => setRemoving(true)}
            >
              Supprimer
            </button>
          )}
          <span className="flex-spacer" />
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={onClose}
          >
            Annuler
          </button>
          <button className="button primary" disabled={busy || removing}>
            {busy ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
