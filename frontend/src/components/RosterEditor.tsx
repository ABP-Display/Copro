import { useEffect, useState } from "react";
import { api } from "../api";
import type { ToolData } from "./Tools";

export function RosterEditor({
  rows,
  onChange,
  voting = false,
  disabled = false,
}: {
  rows: ToolData[];
  onChange: (rows: ToolData[]) => void;
  voting?: boolean;
  disabled?: boolean;
}) {
  const [owners, setOwners] = useState<ToolData[]>([]);
  const [error, setError] = useState("");
  const [unassigned, setUnassigned] = useState(0);
  useEffect(() => {
    let active = true;
    api<ToolData>("ag/electorate")
      .then((data) => {
        if (active) {
          setOwners(data.items);
          setUnassigned(data.unassigned_lots);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  const update = (index: number, changes: ToolData) =>
    onChange(rows.map((r, i) => (i === index ? { ...r, ...changes } : r)));
  const total =
    rows.reduce((sum, r) => sum + Math.round(Number(r.shares || 0) * 100), 0) /
    100;
  const present = rows.filter((r) => r.attendance !== "absent");
  return (
    <section className="roster-editor">
      <p>
        Incluez tous les copropriétaires, même absents. Les tantièmes généraux
        regroupent leurs lots ; vous pouvez corriger les droits pour la
        résolution. Une ligne compte pour un copropriétaire.
      </p>
      {error && (
        <p role="alert" className="alert">
          {error}
        </p>
      )}
      {unassigned > 0 && (
        <p className="alert">
          {unassigned} lot(s) sans copropriétaire : leurs tantièmes ne sont pas
          repris. Complétez l’annuaire ou la liste avant de calculer.
        </p>
      )}
      <fieldset disabled={disabled}>
        <div className="tool-actions">
          <button
            className="button secondary"
            type="button"
            disabled={rows.length > 0 || !owners.length}
            onClick={() => onChange(owners.map((o) => ({ ...o })))}
          >
            Charger tous les copropriétaires
          </button>
          <label>
            Ajouter depuis l’annuaire
            <select
              value=""
              onChange={(e) => {
                const owner = owners.find(
                  (o) => String(o.owner_id) === e.target.value,
                );
                if (owner) onChange([...rows, { ...owner }]);
              }}
            >
              <option value="">Choisir un copropriétaire…</option>
              {owners
                .filter((o) => !rows.some((r) => r.owner_id === o.owner_id))
                .map((o) => (
                  <option key={o.owner_id} value={o.owner_id}>
                    {o.name} — {o.shares} tantièmes
                  </option>
                ))}
            </select>
          </label>
          <button
            className="button secondary"
            type="button"
            onClick={() =>
              onChange([
                ...rows,
                {
                  owner_id: null,
                  name: "",
                  shares: "",
                  attendance: "absent",
                  vote: "pending",
                },
              ])
            }
          >
            Ajouter en saisie libre
          </button>
        </div>
        {rows.map((r, index) => (
          <div className="roster-row" key={index}>
            <label>
              Copropriétaire
              {r.owner_id ? (
                <span className="roster-name">
                  {r.name}
                  <small>Depuis l’annuaire</small>
                </span>
              ) : (
                <input
                  required
                  maxLength={200}
                  value={r.name}
                  onChange={(e) => update(index, { name: e.target.value })}
                  placeholder="Nom et prénom"
                />
              )}
            </label>
            <label>
              Droits de vote
              <input
                required
                type="number"
                min={voting ? "0.01" : "0"}
                step="0.01"
                max="1000000000"
                value={r.shares}
                onChange={(e) => update(index, { shares: e.target.value })}
              />
            </label>
            <label>
              Présence
              <select
                value={r.attendance}
                onChange={(e) =>
                  update(index, { attendance: e.target.value, vote: "pending" })
                }
              >
                <option value="absent">Absent</option>
                <option value="present">Présent</option>
                <option value="represented">Représenté</option>
                <option value="correspondence">Par correspondance</option>
              </select>
            </label>
            {voting && (
              <label>
                Vote
                <select
                  value={r.vote}
                  disabled={r.attendance === "absent"}
                  onChange={(e) => update(index, { vote: e.target.value })}
                >
                  <option value="pending">À renseigner</option>
                  <option value="for">Pour</option>
                  <option value="against">Contre</option>
                  <option value="abstain">Abstention</option>
                </select>
              </label>
            )}
            <button
              type="button"
              className="button secondary"
              aria-label={`Retirer ${r.name || "la ligne " + (index + 1)}`}
              onClick={() => onChange(rows.filter((_, i) => i !== index))}
            >
              Retirer
            </button>
          </div>
        ))}
      </fieldset>
      <p className="roster-summary">
        <strong>
          {rows.length} copropriétaire(s) · {total.toLocaleString("fr-FR")} voix
          au total
        </strong>
        <br />
        {present.length} participant(s) ·{" "}
        {(
          present.reduce(
            (sum, r) => sum + Math.round(Number(r.shares || 0) * 100),
            0,
          ) / 100
        ).toLocaleString("fr-FR")}{" "}
        voix participantes
      </p>
      <p>
        Le statut « représenté » ne contrôle pas les pouvoirs. Vérifiez les
        mandats et les droits corrigés avant utilisation.
      </p>
    </section>
  );
}

export function MeetingRoster({
  meeting,
  onSave,
  busy,
}: {
  meeting: ToolData;
  onSave: (rows: ToolData[]) => Promise<unknown>;
  busy: boolean;
}) {
  const [rows, setRows] = useState<ToolData[]>(meeting.roster || []);
  const [saved, setSaved] = useState(false);
  return (
    <section className="panel">
      <h2>Présences et droits de vote</h2>
      <p>
        Enregistrez cette liste comme point de départ des simulations de l’AG.
        Les simulations déjà enregistrées conservent leur propre liste.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const result = await onSave(rows);
          if (result) setSaved(true);
        }}
      >
        <RosterEditor
          rows={rows}
          onChange={(value) => {
            setRows(value);
            setSaved(false);
          }}
          disabled={busy || meeting.archived}
        />
        {!meeting.archived && (
          <button className="button primary" disabled={busy || !rows.length}>
            {busy ? "Enregistrement…" : "Enregistrer les présences"}
          </button>
        )}
        {saved && <p role="status">Présences enregistrées.</p>}
      </form>
    </section>
  );
}
