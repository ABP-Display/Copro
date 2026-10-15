import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Icon } from "./ui";
type Row = Record<string, any>;
export function CouncilRequestForm({
  versions,
  onSaved,
  onClose,
}: {
  versions: Row[];
  onSaved: () => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [kind, setKind] = useState("expense");
  const [term, setTerm] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<Row[]>([]);
  const [count, setCount] = useState(0);
  const [target, setTarget] = useState("");
  const [proof, setProof] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError("");
    api<Row>(
      `council/targets?kind=${kind}&page=${page}&q=${encodeURIComponent(search)}`,
    )
      .then((r) => {
        if (live) {
          setRows(r.items);
          setCount(r.count);
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [kind, page, search]);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!target) {
      setError("Choisissez le dossier à soumettre.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("council/requests", "POST", {
        kind,
        target: Number(target),
        proof: proof || null,
      });
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
      aria-labelledby="request-form-title"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <form onSubmit={(e) => void submit(e)}>
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">CONTRÔLE DU CONSEIL</p>
            <h2 id="request-form-title">Demander un avis</h2>
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
            Choisissez une facture avec un reste à payer ou un devis non retenu.
            Le dossier et sa pièce seront conservés avec les avis.
          </p>
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <label>
            Type de dossier
            <select
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                setPage(1);
                setTarget("");
              }}
            >
              <option value="expense">Facture fournisseur</option>
              <option value="quote">Devis</option>
            </select>
          </label>
          <label>
            Rechercher un objet, fournisseur ou référence
            <div className="council-search">
              <input value={term} onChange={(e) => setTerm(e.target.value)} />
              <button
                type="button"
                className="button secondary"
                onClick={() => {
                  setSearch(term);
                  setPage(1);
                  setTarget("");
                }}
              >
                Rechercher
              </button>
            </div>
          </label>
          <label>
            Dossier à soumettre
            <select
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              required
              disabled={loading}
            >
              <option value="">
                {loading ? "Recherche…" : "Choisir un dossier…"}
              </option>
              {rows.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label} · {r.supplier} · {r.reference} ·{" "}
                  {Number(r.amount).toLocaleString("fr-FR", {
                    style: "currency",
                    currency: "EUR",
                  })}
                </option>
              ))}
            </select>
            {!rows.length && !loading && (
              <small>
                Aucun dossier disponible pour cette recherche. Les dossiers déjà
                soumis, annulés ou utilisés sont exclus.
              </small>
            )}
          </label>
          {count > 25 && (
            <div className="council-pager">
              <button
                type="button"
                className="button secondary"
                disabled={page === 1 || loading}
                onClick={() => {
                  setPage((p) => p - 1);
                  setTarget("");
                }}
              >
                Précédent
              </button>
              <span>
                Page {page} / {Math.ceil(count / 25)}
              </span>
              <button
                type="button"
                className="button secondary"
                disabled={page * 25 >= count || loading}
                onClick={() => {
                  setPage((p) => p + 1);
                  setTarget("");
                }}
              >
                Suivant
              </button>
            </div>
          )}
          <label>
            Version du justificatif, si différente
            <select value={proof} onChange={(e) => setProof(e.target.value)}>
              <option value="">Utiliser le document rattaché au dossier</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.title} · {v.filename} (version {v.id})
                </option>
              ))}
            </select>
            <small>
              Si aucune pièce n’est rattachée au dossier, choisissez le
              justificatif ici. Ajoutez-le d’abord dans Documents si nécessaire.
            </small>
          </label>
        </div>
        <div className="dialog-footer">
          <button
            type="button"
            className="button secondary"
            onClick={onClose}
            disabled={busy}
          >
            Annuler
          </button>
          <button className="button primary" disabled={busy || loading}>
            {busy ? "Enregistrement…" : "Soumettre au conseil"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
