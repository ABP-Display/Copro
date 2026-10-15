import { useEffect, useRef, useState } from "react";
import { Icon } from "./ui";
import type { CouncilContext } from "./Council";

export function CouncilMandateForm({
  context,
  onSave,
  onClose,
}: {
  context: CouncilContext;
  onSave: (data: any) => Promise<void>;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [role, setRole] = useState("council");
  const [owner, setOwner] = useState("");
  const [beneficiary, setBeneficiary] = useState("owner");
  const [source, setSource] = useState("");
  const [start, setStart] = useState(new Date().toLocaleDateString("en-CA"));
  const [end, setEnd] = useState("");
  const [reference, setReference] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  function useSource(id: string) {
    setSource(id);
    const item = context.assembly_mandates?.find((m) => String(m.id) === id);
    if (item) {
      setOwner(String(item.owner));
      setRole(item.kind);
      setStart(item.starts_on);
      setEnd(item.ends_on);
      setReference(item.reference);
      setBeneficiary("owner");
    }
  }
  const authority = ["coop_syndic", "president", "vice"].includes(role)
    ? "council"
    : role === "treasurer"
      ? "organisation"
      : "ag";
  const seatRequired = ["coop_syndic", "president", "vice"].includes(role);
  const roles = context.roles.filter((r) =>
    context.settings.mode === "cooperative"
      ? !["syndic", "president"].includes(r.value)
      : r.value !== "coop_syndic",
  );
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(e.currentTarget);
    try {
      await onSave({
        ...Object.fromEntries(form),
        role,
        owner: beneficiary === "owner" ? owner : null,
        authority,
        starts_on: form.get("starts_on") || start,
        ends_on: form.get("ends_on") || end,
        reference,
        assembly_mandate: source || null,
        eligibility_confirmed: form.has("eligibility_confirmed"),
      });
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
      aria-labelledby="mandate-form-title"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <form onSubmit={(e) => void submit(e)}>
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">MANDAT ET ACCÈS DATÉS</p>
            <h2 id="mandate-form-title">Confier une responsabilité</h2>
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
            Enregistrez une désignation déjà décidée. Les droits commencent et
            se terminent aux dates du mandat. Seul l’administrateur principal
            peut les attribuer.
          </p>
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <label>
            Reprendre une décision d’AG
            <select value={source} onChange={(e) => useSource(e.target.value)}>
              <option value="">Saisir depuis un document de désignation</option>
              {context.assembly_mandates
                ?.filter(
                  (m) =>
                    m.signed &&
                    (context.settings.mode !== "cooperative" ||
                      m.kind !== "syndic"),
                )
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} · {m.kind === "council" ? "Conseil" : "Syndic"} ·{" "}
                    {m.starts_on}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Responsabilité
            <select
              value={role}
              disabled={!!source}
              onChange={(e) => {
                setRole(e.target.value);
                setBeneficiary("owner");
              }}
              required
            >
              {roles.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          {role === "controller" && (
            <label>
              Personne à désigner
              <select
                value={beneficiary}
                onChange={(e) => setBeneficiary(e.target.value)}
              >
                <option value="owner">Un copropriétaire</option>
                <option value="user">Un compte existant</option>
                <option value="external">
                  Un contrôleur extérieur : créer son accès
                </option>
              </select>
            </label>
          )}
          {beneficiary === "owner" ? (
            <label>
              Copropriétaire
              <select
                value={owner}
                disabled={!!source}
                onChange={(e) => setOwner(e.target.value)}
                required
              >
                <option value="">Choisir une personne…</option>
                {context.owners?.map((o) => (
                  <option value={o.id} key={o.id} disabled={!o.has_access}>
                    {o.name}
                    {!o.has_access ? " — créer d’abord son accès" : ""}
                  </option>
                ))}
              </select>
            </label>
          ) : beneficiary === "user" ? (
            <label>
              Compte du contrôleur
              <select name="user" required>
                <option value="">Choisir…</option>
                {context.users
                  ?.filter((u) => u.is_active && !u.permanent_manager)
                  .map((u) => (
                    <option value={u.id} key={u.id}>
                      {u.name} · {u.email}
                    </option>
                  ))}
              </select>
            </label>
          ) : (
            <>
              <label>
                Nom du contrôleur
                <input name="external_name" required maxLength={150} />
              </label>
              <label>
                Courriel de connexion
                <input name="external_email" type="email" required />
              </label>
            </>
          )}
          <div className="council-form-pair">
            <label>
              Début du mandat
              <input
                type="date"
                name="starts_on"
                value={start}
                disabled={!!source}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </label>
            <label>
              Fin du mandat
              <input
                type="date"
                name="ends_on"
                value={end}
                disabled={!!source}
                min={start}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </label>
          </div>
          {seatRequired && (
            <label>
              Mandat de membre du conseil support
              <select name="seat" required>
                <option value="">Choisir le mandat de cette personne…</option>
                {context.mandates
                  .filter(
                    (m) =>
                      String(m.owner) === owner &&
                      m.role === "council" &&
                      !m.revoked_at,
                  )
                  .map((m) => (
                    <option value={m.id} key={m.id}>
                      {m.name} · {m.starts_on} → {m.ends_on}
                    </option>
                  ))}
              </select>
              <small>
                La présidence ne peut pas dépasser la période du mandat de
                membre du conseil.
              </small>
            </label>
          )}
          <p className="council-inline-help">
            Désignation par :{" "}
            <strong>
              {authority === "ag"
                ? "l’assemblée générale"
                : authority === "council"
                  ? "le conseil syndical"
                  : "l’organisation interne"}
            </strong>
            .{" "}
            {role === "coop_syndic" &&
              "La présidence du conseil et la fonction de syndic sont réunies."}
            {role === "treasurer" &&
              "Le référent prépare les dépenses ; il ne peut ni les comptabiliser ni enregistrer leur règlement."}
            {role === "controller" &&
              "Le contrôle indépendant donne accès aux pièces et aux rapports, sans pouvoir modifier les comptes ni valider ses propres opérations."}
          </p>
          <label>
            Référence de la décision / mission
            <textarea
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              required
              maxLength={1000}
              rows={3}
            />
          </label>
          {!source && (
            <label>
              Pièce de désignation
              <select name="proof" required={role !== "treasurer"}>
                <option value="">Choisir une version de document…</option>
                {context.versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.title} — {v.filename} (version {v.id})
                  </option>
                ))}
              </select>
              <small>
                Ajoutez le PV ou la pièce dans Documents avant de revenir ici.
              </small>
            </label>
          )}
          <label className="council-check">
            <input type="checkbox" name="eligibility_confirmed" required />
            J’ai vérifié l’éligibilité de la personne, les dates et la décision.
            J’autorise les accès correspondant à cette responsabilité.
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
            {busy ? "Enregistrement…" : "Enregistrer le mandat et ses accès"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
