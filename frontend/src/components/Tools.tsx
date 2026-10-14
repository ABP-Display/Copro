import { useEffect, useState } from "react";
import { api } from "../api";
import { Icon } from "./ui";
import { RosterEditor } from "./RosterEditor";
export type ToolData = Record<string, any>;
export const majorityLabels: Record<string, string> = {
  "24": "Article 24 — majorité simple",
  "25": "Article 25 — majorité absolue",
  "26": "Article 26 — double majorité",
  unanimity: "Unanimité",
};
const blank = {
  rule: "24",
  mode: "first",
  total_votes: "",
  total_owners: "",
  participating_owners: "",
  for_owners: "",
  for_votes: "",
  against_votes: "0",
  abstain_votes: "0",
};
const euro = (value: string | number) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(
    Number(value),
  );

export function VoteCalculator({
  rule,
  initial,
  onCalculate,
}: {
  rule?: string;
  initial?: ToolData | null;
  onCalculate?: (data: ToolData) => Promise<ToolData>;
}) {
  const [form, setForm] = useState<ToolData>(
    { ...blank, rule: rule || "24", ...initial?.input },
  );
  const [entryMode, setEntryMode] = useState(
    initial?.input && !initial.input.roster ? "free" : "roster",
  );
  const [result, setResult] = useState<ToolData | null>(
    initial?.result || null,
  );
  const [baseline, setBaseline] = useState<ToolData | null>(
    initial?.input?.initial || null,
  );
  const [lastInput, setLastInput] = useState<ToolData | null>(
    initial?.input || null,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  function update(key: string, value: string) {
    setForm({ ...form, [key]: value });
    setResult(null);
    setError("");
  }
  async function calculate() {
    setBusy(true);
    setError("");
    const data: ToolData = { ...form, ...(baseline ? { initial: baseline } : {}) };
    if (entryMode === "roster") data.roster = form.roster || [];
    else delete data.roster;
    try {
      const answer = onCalculate
        ? await onCalculate(data)
        : await api<ToolData>("ag/tools/vote", "POST", data);
      setResult(answer);
      setLastInput(data);
    } catch (e) {
      setError((e as Error).message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  }
  function numberField(key: string, label: string, integer = false) {
    return (
      <label>
        {label}
        <input
          required
          type="number"
          min="0"
          max="1000000000"
          step={integer ? "1" : "0.01"}
          value={form[key]}
          onChange={(e) => update(key, e.target.value)}
        />
      </label>
    );
  }
  return (
    <section className="calculator vote-calculator">
      <div className="tool-intro">
        <Icon name="vote" />
        <p>
          Simulation du cas général en France, pour au moins trois
          copropriétaires. Saisissez les droits de vote corrigés, notamment
          après une éventuelle réduction au titre de l’article 22. Le choix de
          la majorité dépend de la résolution.
        </p>
      </div>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void calculate();
        }}
      >
        <div className="calculator-toolbar">
          <label>
            Majorité
            <select
              value={form.rule}
              disabled={!!rule || form.mode !== "first"}
              onChange={(e) => update("rule", e.target.value)}
            >
              {Object.entries(majorityLabels).map(([key, label]) => (
                <option value={key} key={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <span className="subtle-badge">
            {form.mode === "first"
              ? "Premier vote"
              : `Second vote — passerelle ${form.mode}`}
          </span>
          {!onCalculate && (
            <button
              type="button"
              className="button secondary"
              onClick={() => {
                setEntryMode("free");
                setForm({
                  rule: rule || "25",
                  mode: "first",
                  total_votes: "1000",
                  total_owners: "10",
                  participating_owners: "6",
                  for_owners: "3",
                  for_votes: "400",
                  against_votes: "300",
                  abstain_votes: "100",
                });
                setResult(null);
                setBaseline(null);
                setLastInput(null);
                setError("");
              }}
            >
              Charger un exemple
            </button>
          )}
        </div>
        <label className="vote-entry-mode">
          Saisie des résultats
          <select
            disabled={busy || form.mode !== "first"}
            value={entryMode}
            onChange={(e) => {
              setEntryMode(e.target.value);
              setResult(null);
              setError("");
            }}
          >
            <option value="roster">
              Par copropriétaire — présences et votes
            </option>
            <option value="free">Totaux en saisie libre</option>
          </select>
        </label>
        {entryMode === "roster" ? (
          <RosterEditor
            voting
            rows={form.roster || []}
            disabled={busy}
            onChange={(rows) => {
              setForm({ ...form, roster: rows });
              setResult(null);
              setError("");
            }}
          />
        ) : (
          <div className="calculator-fields">
            <fieldset>
              <legend>Voix et tantièmes</legend>
              <p>Utilisez la même unité pour tous les montants de voix.</p>
              {numberField("total_votes", "Voix de tous les copropriétaires")}
              {numberField("for_votes", "Voix pour")}
              {numberField("against_votes", "Voix contre")}
              {numberField("abstain_votes", "Voix d’abstention")}
            </fieldset>
            <fieldset>
              <legend>Nombre de copropriétaires</legend>
              <p>
                Comptez les copropriétaires, pas les lots ni les personnes
                portant des mandats.
              </p>
              {numberField("total_owners", "Copropriétaires au total", true)}
              {numberField(
                "participating_owners",
                "Présents, représentés ou votant par correspondance",
                true,
              )}
              {numberField(
                "for_owners",
                "Copropriétaires ayant voté pour",
                true,
              )}
            </fieldset>
          </div>
        )}
        <div className="tool-actions">
          <button className="button primary" disabled={busy}>
            {busy
              ? "Calcul…"
              : onCalculate
                ? "Enregistrer la simulation"
                : "Calculer la majorité"}
          </button>
          {form.mode !== "first" && (
            <button
              type="button"
              className="button secondary"
              onClick={() => {
                setForm({
                  ...form,
                  initial: undefined,
                  mode: "first",
                  rule: rule || baseline?.rule || "25",
                });
                setBaseline(null);
                setResult(null);
              }}
            >
              Revenir au premier vote
            </button>
          )}
        </div>
      </form>
      {result && (
        <div
          className={`vote-result ${result.adopted ? "positive" : "neutral"}`}
          role="status"
        >
          <p className="eyebrow">RÉSULTAT DE LA SIMULATION</p>
          <h3>
            {result.adopted
              ? "Majorité atteinte"
              : result.status === "no_expressed_votes"
                ? "Aucune voix exprimée"
                : "Majorité non atteinte"}
          </h3>
          <p>{result.explanation}</p>
          <p className="vote-criterion">{result.criterion}</p>
          <dl className="tool-totals">
            <div>
              <dt>Voix participantes</dt>
              <dd>{result.participating_votes}</dd>
            </div>
            <div>
              <dt>Voix exprimées</dt>
              <dd>{result.expressed_votes}</dd>
            </div>
            <div>
              <dt>Voix absentes</dt>
              <dd>{result.absent_votes}</dd>
            </div>
          </dl>
          {result.bridge && (
            <div className="vote-bridge">
              <p>{result.bridge_message}</p>
              <button
                className="button secondary"
                onClick={() => {
                  setBaseline(lastInput);
                  setForm({
                    ...form,
                    mode: result.bridge,
                    rule: result.bridge === "25-1" ? "24" : "25",
                  });
                  setResult(null);
                }}
              >
                Préparer le second vote
              </button>
            </div>
          )}
        </div>
      )}
      <div className="tool-sources">
        <p>
          Outil d’aide au calcul : il ne valide pas la convocation, les mandats
          ou la régularité d’un vote. Les copropriétés à deux et les autres
          régimes particuliers nécessitent un traitement distinct.
        </p>
        <p>
          Références consultées le 13/10/2026 :{" "}
          <a
            href="https://www.service-public.gouv.fr/particuliers/vosdroits/F2137"
            target="_blank"
            rel="noreferrer"
          >
            Service Public
          </a>{" "}
          ·{" "}
          <a
            href="https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000880200"
            target="_blank"
            rel="noreferrer"
          >
            Loi du 10 juillet 1965
          </a>
          .
        </p>
      </div>
    </section>
  );
}

export function Tools({ section }: { section: string }) {
  const [directory,setDirectory]=useState<ToolData[]>([]);
  useEffect(()=>{let active=true;if(section==="split")api<ToolData>("ag/electorate").then(data=>{if(active)setDirectory(data.items);}).catch(()=>{});return()=>{active=false;};},[section]);
  const [amount, setAmount] = useState("");
  const [count, setCount] = useState("12");
  const [rows, setRows] = useState([
    { label: "Part 1", weight: "1" },
    { label: "Part 2", weight: "1" },
  ]);
  const [result, setResult] = useState<ToolData | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  function changed() {
    setResult(null);
    setError("");
  }
  async function calculate() {
    setBusy(true);
    setError("");
    try {
      setResult(
        await api<ToolData>(
          `ag/tools/${section}`,
          "POST",
          section === "split" ? { amount, rows } : { amount, count },
        ),
      );
    } catch (e) {
      setError((e as Error).message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  }
  if (section === "vote") return <VoteCalculator />;
  return (
    <section className="calculator">
      <div className="tool-intro">
        <Icon name="calculator" />
        <p>
          {section === "split"
            ? "Répartissez un montant selon des poids ou tantièmes. L’arrondi conserve exactement le total au centime ; les parts nulles restent à zéro."
            : "Divisez un montant en échéances égales. Les centimes restants sont placés sur les premières échéances."}{" "}
          Ce calcul ne crée aucune opération comptable.
        </p>
      </div>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void calculate();
        }}
      >
        <div className="calculator-toolbar">
          <label>
            Montant total (€)
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value);
                changed();
              }}
            />
          </label>
          {section === "installments" && (
            <label>
              Nombre d’échéances
              <input
                required
                type="number"
                min="1"
                max="60"
                value={count}
                onChange={(e) => {
                  setCount(e.target.value);
                  changed();
                }}
              />
            </label>
          )}
        </div>
        {section === "split" && (
          <div className="split-rows">
            <label>Reprendre un copropriétaire<select value="" onChange={e=>{const owner=directory.find(o=>String(o.owner_id)===e.target.value);if(owner){setRows([...rows,{label:owner.name,weight:owner.shares}]);changed();}}}><option value="">Choisir dans l’annuaire…</option>{directory.map(o=><option key={o.owner_id} value={o.owner_id}>{o.name} — {o.shares} tantièmes</option>)}</select></label>
            {rows.map((row, index) => (
              <div className="split-row" key={index}>
                <label>
                  Libellé
                  <input
                    required
                    maxLength={100}
                    value={row.label}
                    onChange={(e) => {
                      setRows(
                        rows.map((r, i) =>
                          i === index ? { ...r, label: e.target.value } : r,
                        ),
                      );
                      changed();
                    }}
                  />
                </label>
                <label>
                  Poids / tantièmes
                  <input
                    required
                    type="number"
                    min="0"
                    step="0.01"
                    value={row.weight}
                    onChange={(e) => {
                      setRows(
                        rows.map((r, i) =>
                          i === index ? { ...r, weight: e.target.value } : r,
                        ),
                      );
                      changed();
                    }}
                  />
                </label>
                <button
                  type="button"
                  className="icon-button"
                  aria-label={`Supprimer la part ${index + 1}`}
                  disabled={rows.length === 1}
                  onClick={() => {
                    setRows(rows.filter((_, i) => i !== index));
                    changed();
                  }}
                >
                  <Icon name="close" />
                </button>
              </div>
            ))}
            <button
              type="button"
              className="button secondary"
              disabled={rows.length >= 200}
              onClick={() => {
                setRows([
                  ...rows,
                  { label: `Part ${rows.length + 1}`, weight: "1" },
                ]);
                changed();
              }}
            >
              <Icon name="plus" size={16} />
              Ajouter une part
            </button>
          </div>
        )}
        <div className="tool-actions">
          <button className="button primary" disabled={busy}>
            {busy ? "Calcul…" : "Calculer la répartition"}
          </button>
        </div>
      </form>
      {result && (
        <section className="panel tool-output">
          <div className="panel-heading">
            <h2>
              {section === "split"
                ? "Répartition au centime"
                : "Échéancier simulé"}
            </h2>
            <button className="button secondary" onClick={() => window.print()}>
              Imprimer / PDF
            </button>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{section === "split" ? "Part" : "Échéance"}</th>
                  {section === "split" && <th>Poids</th>}
                  <th>Montant</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row: ToolData, index: number) => (
                  <tr key={index}>
                    <td>{row.label || `Échéance ${row.number}`}</td>
                    {section === "split" && <td>{row.weight}</td>}
                    <td>{euro(row.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="tool-total">
            Total conservé : <strong>{euro(result.total)}</strong>
          </div>
        </section>
      )}
    </section>
  );
}
