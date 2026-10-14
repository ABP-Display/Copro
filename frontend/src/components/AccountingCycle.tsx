import { useEffect, useRef, useState } from "react";
import { api, newOperationId } from "../api";
import { Icon, Empty } from "./ui";
import "./accounting-cycle.css";

type Row = Record<string, any>;
type Field = {
  name: string;
  label: string;
  type?: string;
  optional?: boolean;
  options?: Row[];
  multiple?: boolean;
};
type Form = {
  title: string;
  help?: string;
  fields: Field[];
  defaults?: Row;
  review?: (values: Row) => Promise<Row>;
  submit: (values: Row) => Promise<void>;
};
const money = (v: any) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(
    Number(v || 0),
  );
const today = () =>
  new Date().toLocaleDateString("en-CA", { timeZone: "Europe/Paris" });
const labels: Record<string, string> = {
  code: "Compte",
  label: "Libellé",
  third_party: "Tiers",
  debit: "Débit",
  credit: "Crédit",
  balance: "Solde",
  budget: "Budget",
  project: "Opération",
  decision: "Décision",
  expenses: "Charges",
  funding: "Financement",
  difference: "Écart",
  completed_on: "Terminée le",
  key_name: "Clé",
  lot_number: "Lot",
  name: "Copropriétaire",
  actual: "Charges réelles",
  provisions: "Provisions",
  adjustment: "Régularisation",
  date: "Date",
  due_date: "Échéance",
  remaining: "Non lettré",
  age: "Jours",
  bucket: "Ancienneté",
  called: "Appelé",
  paid: "Versé",
  used: "Affecté aux travaux",
  available: "Disponible versé",
  account_balance: "Solde du fonds appelé",
};

function Table({ rows, keys }: { rows: Row[]; keys: string[] }) {
  if (!rows.length)
    return (
      <p className="muted cycle-empty">Aucun mouvement pour cette rubrique.</p>
    );
  const amounts = [
    "debit",
    "credit",
    "balance",
    "budget",
    "expenses",
    "funding",
    "difference",
    "actual",
    "provisions",
    "adjustment",
    "remaining",
    "called",
    "paid",
    "used",
    "available",
    "account_balance",
    "actual_previous",
    "actual_current",
    "budget_current",
    "budget_next",
    "budget_following",
    "received",
  ];
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k}>
                {labels[k] ||
                  (
                    {
                      actual_previous: "Réalisé N−1",
                      actual_current: "Réalisé N",
                      budget_current: "Budget saisi N",
                      budget_next: "Budget saisi N+1",
                      budget_following: "Budget saisi N+2",
                      received: "Encaissements lettrés",
                    } as Record<string, string>
                  )[k] ||
                  k}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.id || i}>
              {keys.map((k) => (
                <td
                  key={k}
                  className={amounts.includes(k) ? "cycle-number" : ""}
                >
                  {row[k] === null
                    ? "—"
                    : amounts.includes(k)
                      ? money(row[k])
                      : String(row[k] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AccountingCycle({ section }: { section: string }) {
  const [context, setContext] = useState<Row>({
    years: [],
    owners: [],
    lots: [],
    suppliers: [],
    keys: [],
    accounts: [],
    banks: [],
    projects: [],
  });
  const [year, setYear] = useState("");
  const [approvalDate, setApprovalDate] = useState(today());
  const [data, setData] = useState<Row>({});
  const [reg, setReg] = useState<Row>({});
  const [bankLines, setBankLines] = useState<Row[]>([]);
  const [statement, setStatement] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<Form | null>(null);
  const [opening, setOpening] = useState(false);
  const sequence = useRef(0);
  async function load() {
    const run = ++sequence.current;
    try {
      const ctx = await api<Row>("finance/cycle/context");
      const selected = year || String(ctx.years[0]?.id || "");
      const resource =
        section === "closing"
          ? "close"
          : section === "reconciliation"
            ? "statements"
            : section === "aged"
              ? "outstanding"
              : section;
      const resources =
        !selected &&
        !["lettering", "reconciliation", "funds", "aged", "mutations"].includes(
          section,
        )
          ? []
          : [
              resource,
              ...(section === "closing" ? ["regularization"] : []),
              ...(section === "reconciliation" ? ["bank-lines"] : []),
            ];
      const results = await Promise.all(
        resources.map((r) =>
          api<Row>(
            `finance/cycle/${r}${selected ? `?year=${selected}${r === "regularization" ? `&approved_on=${approvalDate}` : ""}` : ""}`,
          ),
        ),
      );
      if (run !== sequence.current) return;
      setContext(ctx);
      setYear(selected);
      setData(results[0] || {});
      if (section === "closing") setReg(results[1]);
      if (section === "reconciliation") {
        setBankLines(results[1].rows);
        setStatement((v) =>
          results[0].items.some((s: Row) => String(s.id) === v)
            ? v
            : String(results[0].items[0]?.id || ""),
        );
      }
    } catch (e) {
      if (run === sequence.current) setError((e as Error).message);
    }
  }
  useEffect(() => {
    setData({});
    setError("");
    setNotice("");
    void load();
    return () => {
      sequence.current++;
    };
  }, [section, year, approvalDate]);
  const selectedYear = context.years.find((y: Row) => String(y.id) === year);
  const yearField: Field = {
    name: "year",
    label: "Exercice de l’opération",
    options: context.years
      .filter((y: Row) => !y.closed)
      .map((y: Row) => ({ value: y.id, label: y.name })),
  };
  const keyField: Field = {
    name: "key",
    label: "Clé de répartition",
    options: context.keys.map((k: Row) => ({ value: k.id, label: k.name })),
  };
  const dateField: Field = {
    name: "date",
    label: "Date comptable",
    type: "date",
  };
  const centreField: Field = {
    name: "cost_center",
    label: "Comptabilité analytique (si nécessaire)",
    optional: true,
    options: (context.centres || []).map((c: Row) => ({
      value: c.id,
      label: c.name,
    })),
  };
  const decisionField: Field = {
    name: "decision",
    label: "Référence de la décision approuvée (AG / PV)",
  };
  async function act(resource: string, values: Row) {
    setBusy(true);
    setError("");
    try {
      const body = { ...values };
      if (resource.startsWith("validate-statement/"))
        body.transit_reasons = Object.fromEntries(
          Object.entries(values)
            .filter(([k]) => k.startsWith("transit_"))
            .map(([k, v]) => [k.slice(8), v]),
        );
      await api(`finance/cycle/${resource}`, "POST", body);
      setForm(null);
      setOpening(false);
      setNotice("Opération enregistrée.");
      await load();
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setBusy(false);
    }
  }
  function show(
    title: string,
    resource: string,
    fields: Field[],
    defaults: Row = {},
    help?: string,
  ) {
    setForm({
      title,
      fields,
      defaults,
      help,
      submit: (values) => act(resource, values),
    });
  }
  const currentStatement = (data.items || []).find(
    (s: Row) => String(s.id) === statement,
  );
  const needsYear = ![
    "lettering",
    "reconciliation",
    "funds",
    "aged",
    "mutations",
  ].includes(section);

  return (
    <div className="cycle-page">
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert success" role="status">
          {notice}
        </div>
      )}
      <div className="cycle-toolbar">
        {needsYear && (
          <label>
            Exercice
            <select value={year} onChange={(e) => setYear(e.target.value)}>
              {context.years.map((y: Row) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                  {y.closed ? " · clôturé" : ""}
                </option>
              ))}
            </select>
          </label>
        )}
        {section === "closing" && (
          <button
            className="button secondary"
            onClick={() =>
              setForm({
                title: "Créer un exercice",
                fields: [
                  { name: "name", label: "Nom" },
                  { name: "starts_on", label: "Début", type: "date" },
                  { name: "ends_on", label: "Fin", type: "date" },
                ],
                submit: async (v) => {
                  await api("finance/years", "POST", v);
                  setForm(null);
                  await load();
                },
              })
            }
          >
            Nouvel exercice
          </button>
        )}
        {section === "reconciliation" && (
          <button
            className="button"
            onClick={() =>
              show(
                "Importer un relevé",
                "statements",
                [
                  {
                    name: "bank",
                    label: "Compte bancaire",
                    options: context.banks.map((b: Row) => ({
                      value: b.id,
                      label: b.name,
                    })),
                  },
                  { name: "starts_on", label: "Début du relevé", type: "date" },
                  { name: "ends_on", label: "Fin du relevé", type: "date" },
                  {
                    name: "opening_balance",
                    label: "Solde de départ (€)",
                    type: "number",
                  },
                  {
                    name: "closing_balance",
                    label: "Solde final (€)",
                    type: "number",
                  },
                  { name: "csv", label: "Relevé CSV", type: "file" },
                ],
                {},
                "Colonnes : date;libelle;montant;reference. Crédit reçu positif, débit payé négatif. L’import crée un relevé à vérifier et ne crée aucune écriture.",
              )
            }
          >
            Importer un relevé
          </button>
        )}
        {section === "annexes" && (
          <>
            <button className="button secondary" onClick={() => window.print()}>
              Imprimer / PDF
            </button>
            <a
              className="button secondary"
              href={`/api/finance/cycle/fec/?year=${year}`}
            >
              Exporter les écritures (FEC)
            </a>
            <a
              className="button secondary"
              href={`/api/finance/cycle/archive/?year=${year}`}
            >
              Exporter les données (JSON)
            </a>
          </>
        )}
      </div>
      {section === "mutations" && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Une vente, un historique conservé</h2>
              <p>
                Les appels sont attribués selon leur exigibilité et la
                régularisation selon la propriété à l’approbation. Une
                correction d’un exercice clos est enregistrée dans un exercice
                ouvert.
              </p>
            </div>
            <button
              className="button"
              disabled={busy}
              onClick={() =>
                setForm({
                  title: "Enregistrer une mutation",
                  help: "Prévisualisez les changements de comptes avant validation. Aucun prorata privé vendeur/acquéreur ni remboursement bancaire automatique n’est effectué.",
                  fields: [
                    {
                      name: "lot",
                      label: "Lot vendu",
                      options: context.lots.map((l: Row) => ({
                        value: l.id,
                        label: `Lot ${l.number} · ${context.owners.find((o: Row) => o.id === l.owner_id)?.name || "À attribuer"}`,
                      })),
                    },
                    {
                      name: "new_owner",
                      label: "Acquéreur de l’annuaire",
                      options: context.owners.map((o: Row) => ({
                        value: o.id,
                        label: o.name,
                      })),
                    },
                    {
                      name: "effective_date",
                      label: "Date effective de la mutation",
                      type: "date",
                    },
                    {
                      name: "reference",
                      label: "Référence de notification / acte",
                    },
                  ],
                  defaults: { effective_date: today() },
                  review: (v) =>
                    api<Row>("finance/cycle/preview-mutation", "POST", v),
                  submit: (v) => act("mutation", v),
                })
              }
            >
              Enregistrer une vente
            </button>
          </div>
          {(data.rows || []).map((m: Row) => (
            <article className="cycle-task" key={m.id}>
              <div>
                <strong>
                  Lot {m.lot_number} · {m.old_owner} → {m.new_owner}
                </strong>
                <p className="muted">
                  {m.effective_date} · {m.reference} · {m.adjustments}{" "}
                  correction(s) comptable(s){!m.active ? " · annulée" : ""}
                </p>
              </div>
              {m.active && (
                <button
                  className="button secondary"
                  onClick={() =>
                    show(
                      "Corriger cette mutation",
                      `cancel-mutation/${m.id}`,
                      [],
                      {},
                      "Seule la dernière mutation active peut être corrigée. Les écritures inverses sont conservées dans l’exercice ouvert, sans supprimer les comptes historiques.",
                    )
                  }
                >
                  Corriger
                </button>
              )}
            </article>
          ))}
        </section>
      )}
      {needsYear && !selectedYear && (
        <Empty
          title="Créez votre premier exercice"
          description="La période comptable se configure dans Exercice & clôture."
        />
      )}
      {section === "closing" && !reg.saved && !selectedYear?.closed && (
        <label>
          Date d’approbation pour l’aperçu des répartitions
          <input
            type="date"
            value={approvalDate}
            onChange={(e) => setApprovalDate(e.target.value || today())}
          />
        </label>
      )}

      {section === "opening" && selectedYear && (
        <section className="panel cycle-intro">
          <span className="stat-icon">
            <Icon name="book" />
          </span>
          <h2>Reprendre les comptes au bon point de départ</h2>
          <p>
            Reportez la balance reçue de l’ancien syndic : banques, dettes
            fournisseurs, comptes copropriétaires, avances et fonds travaux. Les
            totaux débit et crédit doivent être égaux.
          </p>
          <p className="muted">
            Chaque compte propriétaire conserve son titulaire ; le fonds travaux
            est rattaché aux lots. Une seule reprise est autorisée. Pour les
            exercices suivants, la clôture génère les reports automatiquement.
          </p>
          <button
            className="button"
            disabled={selectedYear.closed || busy || !!data.entries?.length}
            onClick={() => setOpening(true)}
          >
            Saisir la balance initiale
          </button>
          {(data.entries || []).map((e: Row) => (
            <section key={e.id}>
              <h3>Reprise enregistrée · {e.date}</h3>
              <p>{e.reference}</p>
              <Table
                rows={e.rows}
                keys={["code", "third_party", "debit", "credit"]}
              />
              {!selectedYear.closed && (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() =>
                    show(
                      "Corriger la balance initiale",
                      `undo-opening/${e.id}`,
                      [],
                      { year },
                      "Une écriture inverse sera conservée avant de saisir la reprise corrigée. Les lettrages doivent être annulés auparavant.",
                    )
                  }
                >
                  Corriger la reprise
                </button>
              )}
            </section>
          ))}
        </section>
      )}

      {section === "corrections" && (
        <section className="panel">
          <h2>Corriger en conservant l’historique</h2>
          <p className="muted">
            L’opération reste enregistrée et une écriture inverse est ajoutée.
            Pour corriger une donnée, recréez ensuite l’opération correcte.
            Dissociez d’abord les rapprochements et lettrages. Les 200 dernières
            opérations de cet exercice sont affichées.
          </p>
          {(data.rows || []).map((r: Row) => (
            <article className="cycle-task" key={r.id}>
              <div>
                <strong>{r.label}</strong>
                <p className="muted">
                  #{r.number} · {r.date} · {r.journal}
                </p>
              </div>
              <button
                className="button secondary"
                disabled={busy || selectedYear?.closed}
                onClick={() =>
                  show(
                    "Corriger cette opération",
                    `cancel-entry/${r.id}`,
                    [dateField],
                    { year, date: r.date },
                    "Une écriture inverse sera ajoutée dans cet exercice. Aucun paiement bancaire ou courriel ne sera exécuté.",
                  )
                }
              >
                Créer l’écriture inverse
              </button>
            </article>
          ))}
        </section>
      )}
      {section === "allocation" && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Répartitions à vérifier</h2>
              <p>
                Reliez les écritures historiques à leur clé. La répartition est
                conservée avant la régularisation.
              </p>
            </div>
          </div>
          {(data.rows || []).map((r: Row) => (
            <article className="cycle-task" key={r.id}>
              <div>
                <strong>{r.label}</strong>
                <p className="muted">
                  Écriture {r.number} · {r.code} ·{" "}
                  {money(Number(r.debit) - Number(r.credit))}
                </p>
              </div>
              <button
                className="button secondary"
                disabled={busy || selectedYear?.closed}
                onClick={() =>
                  show(
                    "Vérifier la répartition",
                    `allocation/${r.id}`,
                    [
                      keyField,
                      {
                        name: "project",
                        label: "Travaux concernés (compte 67)",
                        optional: true,
                        options: context.projects
                          .filter((p: Row) => !p.completed_on)
                          .map((p: Row) => ({ value: p.id, label: p.name })),
                      },
                    ],
                    { year, key: r.key || "" },
                    "Les tantièmes et propriétaires actuels seront utilisés : vérifiez qu’ils correspondent à la situation de cette dépense historique.",
                  )
                }
              >
                Choisir la clé
              </button>
            </article>
          ))}
          {!data.rows?.length && (
            <p className="cycle-empty muted">
              Aucune répartition en attente pour cet exercice.
            </p>
          )}
        </section>
      )}

      {section === "lettering" && (
        <>
          <section className="panel cycle-intro">
            <h2>Affecter un règlement à une dette</h2>
            <p>
              Le lettrage explique quelles sommes ont été réglées. Il conserve
              les montants comptables et peut relier des exercices différents.
            </p>
            <button
              className="button"
              disabled={busy}
              onClick={() =>
                show(
                  "Lettrer deux mouvements",
                  "lettering",
                  [
                    {
                      name: "debit_line",
                      label: "Débit",
                      options: (data.rows || [])
                        .filter((r: Row) => Number(r.debit) > 0)
                        .map((r: Row) => ({
                          value: r.id,
                          label: `${r.third_party} · ${r.code} · ${r.label} · ${money(r.remaining)}`,
                        })),
                    },
                    {
                      name: "credit_line",
                      label: "Crédit",
                      options: (data.rows || [])
                        .filter((r: Row) => Number(r.credit) > 0)
                        .map((r: Row) => ({
                          value: r.id,
                          label: `${r.third_party} · ${r.code} · ${r.label} · ${money(r.remaining)}`,
                        })),
                    },
                    {
                      name: "amount",
                      label: "Montant à affecter (€)",
                      type: "number",
                    },
                  ],
                  {},
                  "Choisissez le même copropriétaire ou fournisseur et le même compte. Un règlement partiel laisse le complément disponible.",
                )
              }
            >
              Affecter un règlement
            </button>
          </section>
          <section className="panel">
            <h2>Mouvements non lettrés</h2>
            <Table
              rows={data.rows || []}
              keys={[
                "date",
                "third_party",
                "code",
                "label",
                "debit",
                "credit",
                "remaining",
              ]}
            />
            {(data.rows || [])
              .filter(
                (r: Row) =>
                  r.kind === "opening" && r.supplier && Number(r.credit) > 0,
              )
              .map((r: Row) => (
                <div className="cycle-task" key={r.id}>
                  <span>
                    Dette reprise · {r.third_party} · {money(r.remaining)}
                  </span>
                  <button
                    className="button secondary"
                    onClick={() =>
                      show(
                        "Enregistrer le règlement d’une dette reprise",
                        `pay-balance/${r.id}`,
                        [
                          yearField,
                          dateField,
                          {
                            name: "bank",
                            label: "Banque utilisée",
                            options: context.banks.map((b: Row) => ({
                              value: b.id,
                              label: b.name,
                            })),
                          },
                          {
                            name: "amount",
                            label: "Montant réglé (€)",
                            type: "number",
                          },
                          centreField,
                        ],
                        { year, date: today(), amount: r.remaining },
                        "Enregistrement d’un paiement déjà effectué, sans ordre envoyé à la banque. La dette reprise sera lettrée automatiquement.",
                      )
                    }
                  >
                    Enregistrer un règlement
                  </button>
                </div>
              ))}
          </section>
          {!!data.matches?.length && (
            <section className="panel">
              <h2>Affectations enregistrées</h2>
              {data.matches.map((m: Row) => (
                <div className="cycle-task" key={m.id}>
                  <span>
                    Débit #{m.debit_line_id} ↔ crédit #{m.credit_line_id} ·{" "}
                    {money(m.amount)}
                  </span>
                  <button
                    className="text-link"
                    disabled={busy}
                    onClick={() =>
                      show(
                        "Annuler cette affectation",
                        `unletter/${m.id}`,
                        [],
                        {},
                        "Les lignes redeviendront disponibles ; aucune écriture ne sera supprimée.",
                      )
                    }
                  >
                    Annuler
                  </button>
                </div>
              ))}
            </section>
          )}
        </>
      )}

      {section === "aged" && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Échéances et soldes non lettrés</h2>
              <p>
                Une échéance future est distinguée d’un retard. Les crédits
                disponibles restent visibles pour les affecter avant toute
                relance.
              </p>
            </div>
          </div>
          <Table
            rows={data.rows || []}
            keys={[
              "name",
              "label",
              "due_date",
              "debit",
              "credit",
              "remaining",
              "bucket",
            ]}
          />
        </section>
      )}

      {section === "reconciliation" && (
        <>
          <section className="panel cycle-intro">
            <h2>Comparer la banque et les comptes</h2>
            <p>
              Importez un relevé, puis associez chaque mouvement à une ou
              plusieurs écritures. Les suggestions restent à valider. Un relevé
              vérifié doit retrouver exactement ses soldes de départ et de fin.
            </p>
            <a
              className="text-link"
              download="modele-releve.csv"
              href={
                "data:text/csv;charset=utf-8," +
                encodeURIComponent(
                  "date;libelle;montant;reference\n2026-01-05;Virement reçu;100,00;V001\n",
                )
              }
            >
              Télécharger le modèle CSV
            </a>
          </section>
          {!!data.items?.length && (
            <label className="cycle-selector">
              Relevé
              <select
                value={statement}
                onChange={(e) => setStatement(e.target.value)}
              >
                {data.items.map((s: Row) => (
                  <option key={s.id} value={s.id}>
                    {s.bank_name} · {s.starts_on} → {s.ends_on}
                    {s.validated ? " · vérifié" : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          {currentStatement && (
            <section className="panel">
              <div className="cycle-metrics">
                {[
                  ["Solde du relevé", currentStatement.closing_balance],
                  ["Solde comptable", currentStatement.ledger_balance],
                  ["Écart à expliquer", currentStatement.difference],
                ].map(([title, v]) => (
                  <div key={title}>
                    <small>{title}</small>
                    <strong>{money(v)}</strong>
                  </div>
                ))}
              </div>
              {currentStatement.rows.map((r: Row) => (
                <article className="cycle-task" key={r.id}>
                  <div>
                    <strong>{r.label}</strong>
                    <p className="muted">
                      {r.date} · {r.reference || "Sans référence"} ·{" "}
                      {money(r.amount)}
                    </p>
                    {r.matched && (
                      <small>
                        Rapproché avec{" "}
                        {r.line_ids.map((id: number) => `#${id}`).join(", ")}
                      </small>
                    )}
                  </div>
                  {!currentStatement.validated && (
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() =>
                        r.matched
                          ? show(
                              "Annuler ce rapprochement",
                              `bank-unmatch/${r.id}`,
                              [],
                            )
                          : show(
                              "Associer le mouvement bancaire",
                              `bank-match/${r.id}`,
                              [
                                {
                                  name: "line_ids",
                                  label: "Écritures à associer",
                                  multiple: true,
                                  options: bankLines
                                    .filter(
                                      (l) =>
                                        context.banks.find(
                                          (b: Row) =>
                                            b.id === currentStatement.bank,
                                        )?.account__code === l.code,
                                    )
                                    .map((l) => ({
                                      value: l.id,
                                      label: `${l.date} · ${l.label} · ${money(Number(l.debit) - Number(l.credit))}`,
                                    })),
                                },
                              ],
                              {
                                line_ids:
                                  r.suggestions.length === 1
                                    ? [String(r.suggestions[0])]
                                    : [],
                              },
                              "Vous pouvez choisir plusieurs écritures pour un virement groupé. La somme doit correspondre exactement au relevé.",
                            )
                      }
                    >
                      {r.matched ? "Dissocier" : "Rapprocher"}
                    </button>
                  )}
                </article>
              ))}
              <button
                className="button"
                disabled={busy}
                onClick={() =>
                  show(
                    currentStatement.validated
                      ? "Déverrouiller le relevé"
                      : "Valider le relevé",
                    `${currentStatement.validated ? "unlock-statement" : "validate-statement"}/${currentStatement.id}`,
                    currentStatement.validated
                      ? []
                      : (currentStatement.transit_candidates || []).map(
                          (l: Row) => ({
                            name: `transit_${l.id}`,
                            label: `Motif du transit : ${l.date} · ${l.label} · ${money(l.amount)}`,
                          }),
                        ),
                    {},
                    currentStatement.validated
                      ? "Possible uniquement tant que l’exercice est ouvert."
                      : "Tous les mouvements et les soldes seront contrôlés. Aucun ordre ne sera envoyé à la banque.",
                  )
                }
              >
                {currentStatement.validated
                  ? "Déverrouiller"
                  : "Valider le rapprochement"}
              </button>
            </section>
          )}
          <section className="panel">
            <h2>Écritures bancaires à rapprocher</h2>
            <Table
              rows={bankLines}
              keys={["date", "code", "label", "debit", "credit"]}
            />
          </section>
        </>
      )}

      {section === "funds" && (
        <>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Fonds travaux attaché aux lots</h2>
                <p>
                  Les sommes appelées sont distinguées des versements lettrés.
                  Seules les sommes versées disponibles peuvent être affectées
                  aux travaux.
                </p>
              </div>
            </div>
            <Table
              rows={data.rows || []}
              keys={[
                "lot_number",
                "called",
                "paid",
                "used",
                "available",
                "account_balance",
              ]}
            />
          </section>
          <section className="panel">
            <div className="panel-heading">
              <h2>Financement des travaux votés</h2>
              <button
                className="button secondary"
                onClick={() =>
                  show("Créer une opération votée", "project", [
                    { name: "name", label: "Travaux" },
                    keyField,
                    {
                      name: "budget",
                      label: "Budget voté (€)",
                      type: "number",
                    },
                    decisionField,
                  ])
                }
              >
                Ajouter une opération
              </button>
            </div>
            {context.projects.map((p: Row) => (
              <article className="cycle-task" key={p.id}>
                <div>
                  <strong>{p.name}</strong>
                  <p className="muted">
                    {money(p.budget)} · {p.decision}
                    {p.completed_on ? ` · terminée le ${p.completed_on}` : ""}
                  </p>
                </div>
                {!p.completed_on && (
                  <div className="cycle-actions">
                    <button
                      className="button secondary"
                      onClick={() =>
                        show(
                          "Affecter le fonds travaux",
                          `fund-use/${p.id}`,
                          [
                            yearField,
                            dateField,
                            {
                              name: "amount",
                              label: "Montant affecté (€)",
                              type: "number",
                            },
                            decisionField,
                            centreField,
                          ],
                          { year, date: today() },
                          "La clé des travaux sera appliquée aux lots. Les versements disponibles seront contrôlés pour chacun.",
                        )
                      }
                    >
                      Affecter le fonds
                    </button>
                    <button
                      className="button secondary"
                      onClick={() =>
                        show(
                          "Terminer et solder les travaux",
                          `project-complete/${p.id}`,
                          [yearField, dateField, decisionField],
                          { year, date: today() },
                          "Les charges et financements seront comparés, puis le complément ou l’excédent affecté aux comptes des copropriétaires. Vérifiez la décision et les factures avant validation.",
                        )
                      }
                    >
                      Solder les travaux
                    </button>
                  </div>
                )}
              </article>
            ))}
          </section>
        </>
      )}

      {section === "closing" && selectedYear && (
        <>
          <section className="panel cycle-intro">
            <h2>Un exercice, jusqu’au suivant</h2>
            <p>
              Vérifiez les répartitions, rapprochez la banque, puis régularisez
              les charges approuvées. La clôture conserve le dossier et reporte
              les comptes de bilan et les tiers dans l’exercice suivant.
            </p>
            <p className="muted">
              Une clôture définitive ne se déverrouille pas. Les corrections
              ultérieures se font dans un exercice ouvert en conservant les
              écritures d’origine.
            </p>
          </section>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>1. Régularisation des charges</h2>
                <p>
                  Charges réelles moins provisions : un montant positif reste
                  dû, un montant négatif crédite le copropriétaire.
                </p>
              </div>
            </div>
            {!!reg.preview?.errors?.length && (
              <div className="alert error">
                {reg.preview.errors.map((e: string) => (
                  <p key={e}>{e}</p>
                ))}
              </div>
            )}
            <Table
              rows={reg.saved?.data.rows || reg.preview?.rows || []}
              keys={[
                "key_name",
                "lot_number",
                "name",
                "actual",
                "provisions",
                "adjustment",
              ]}
            />
            {reg.saved ? (
              <div className="cycle-task">
                <p>
                  Validée selon {reg.saved.decision} · {reg.saved.approved_on}
                </p>
                {!selectedYear.closed && (
                  <button
                    className="button secondary"
                    disabled={busy}
                    onClick={() =>
                      show(
                        "Annuler la régularisation",
                        `undo-regularization/${reg.saved.id}`,
                        [],
                        { year },
                        "Une écriture inverse sera conservée. Vous pourrez corriger les charges puis recalculer la répartition.",
                      )
                    }
                  >
                    Annuler pour corriger
                  </button>
                )}
              </div>
            ) : (
              !!reg.preview?.rows?.length && (
                <button
                  className="button"
                  disabled={
                    busy || selectedYear.closed || !!reg.preview?.errors?.length
                  }
                  onClick={() =>
                    show(
                      "Enregistrer les charges approuvées",
                      "regularization",
                      [decisionField],
                      {
                        year,
                        source_hash: reg.preview.source_hash,
                        approved_on: approvalDate,
                      },
                      "À utiliser après l’approbation des comptes. Vérifiez les montants ci-dessus ; leur écriture sera datée de la fin d’exercice et leur échéance de la date déclarée.",
                    )
                  }
                >
                  Valider la régularisation approuvée
                </button>
              )
            )}
          </section>
          <section className="panel">
            <h2>2. Contrôles avant clôture</h2>
            {!data.source_hash ? (
              <p role="status">Chargement des contrôles de clôture…</p>
            ) : selectedYear.closed ? (
              <div className="alert success">
                {data.closed
                  ? "Exercice clôturé. Le dossier est conservé et les soldes ont été reportés."
                  : "Ancien verrouillage technique : aucun dossier de clôture ni report n’a été généré."}
              </div>
            ) : data.errors?.length ? (
              <div className="cycle-checks">
                {data.errors.map((e: string) => (
                  <div key={e}>
                    <Icon name="calendar" size={18} />
                    <span>{e}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="alert success">
                Les contrôles automatiques sont satisfaits. Relisez aussi les
                pièces et le dossier d’approbation.
              </div>
            )}
            {selectedYear.closed && !data.closed && (
              <button
                className="button secondary"
                disabled={busy}
                onClick={() =>
                  show(
                    "Reprendre le verrouillage historique",
                    "legacy-reopen",
                    [],
                    { year },
                    "Seul l’ancien verrouillage technique sera levé pour réaliser les contrôles, la régularisation et les reports. Une clôture définitive ne peut pas être levée.",
                  )
                }
              >
                Reprendre les opérations de clôture
              </button>
            )}
            {!selectedYear.closed && (
              <button
                className="button"
                disabled={busy || !data.source_hash || !!data.errors?.length}
                onClick={() =>
                  show(
                    "Clôturer et reporter les soldes",
                    "close",
                    [
                      {
                        name: "next_year",
                        label: "Exercice suivant",
                        options: context.years
                          .filter(
                            (y: Row) =>
                              !y.closed && y.starts_on > selectedYear.ends_on,
                          )
                          .map((y: Row) => ({
                            value: y.id,
                            label: `${y.name} · ${y.starts_on}`,
                          })),
                      },
                    ],
                    { year, source_hash: data.source_hash },
                    "Cette validation fige l’exercice, conserve les états et génère les à-nouveaux détaillés. Le début du prochain exercice doit être le lendemain de la clôture.",
                  )
                }
              >
                Clôturer avec les reports
              </button>
            )}
          </section>
        </>
      )}

      {section === "annexes" && data.data && (
        <section className="cycle-report">
          <div className="panel cycle-intro">
            <h2>Dossier comptable · {data.data.year}</h2>
            <p>
              {data.data.starts_on} → {data.data.ends_on}
            </p>
            <p className="muted">{data.data.note}</p>
          </div>
          {data.data.annexes.map((a: Row) => (
            <section className="panel" key={a.number}>
              <h2>
                État {a.number} · {a.title}
              </h2>
              <Table
                rows={a.rows}
                keys={
                  a.number === 1
                    ? [
                        "code",
                        "label",
                        "third_party",
                        "debit",
                        "credit",
                        "balance",
                      ]
                    : a.number === 2
                      ? ["code", "label", "debit", "credit", "balance"]
                      : a.number === 3
                        ? [
                            "key_name",
                            "code",
                            "label",
                            "actual_previous",
                            "budget_current",
                            "actual_current",
                            "budget_next",
                            "budget_following",
                          ]
                        : [
                            "project",
                            "decision",
                            "budget",
                            "expenses",
                            "funding",
                            "paid",
                            "received",
                            "difference",
                            "completed_on",
                          ]
                }
              />
            </section>
          ))}
          <section className="panel">
            <h2>Décomptes individuels par lot</h2>
            <Table
              rows={data.data.individual_allocations}
              keys={[
                "key_name",
                "lot_number",
                "name",
                "actual",
                "provisions",
                "adjustment",
              ]}
            />
          </section>
        </section>
      )}

      {form && <CycleForm form={form} onClose={() => setForm(null)} />}
      {opening && (
        <OpeningForm
          context={context}
          year={year}
          onClose={() => setOpening(false)}
          onSubmit={(v) => act("opening", { year, ...v })}
        />
      )}
    </div>
  );
}

function CycleForm({ form, onClose }: { form: Form; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [values, setValues] = useState<Row>(form.defaults || {});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  const [review, setReview] = useState<Row | null>(null);
  const [operationId] = useState(newOperationId);
  useEffect(() => {
    setReview(null);
  }, [values]);
  async function readFile(file: File | undefined, name: string) {
    setValues((v) => ({ ...v, [name]: "" }));
    if (!file) return;
    if (file.size > 2_000_000) {
      setError("Fichier limité à 2 Mo.");
      return;
    }
    const content = await file.text();
    setValues((v) => ({ ...v, [name]: content }));
  }
  return (
    <dialog
      ref={ref}
      className="editor-dialog assembly-dialog"
      onCancel={onClose}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            if (form.review && !review) {
              setReview(await form.review(values));
              return;
            }
            await form.submit({
              ...values,
              request_id: values.request_id || operationId,
              ...(review ? { source_hash: review.source_hash } : {}),
            });
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <header className="dialog-heading">
          <div>
            <span className="eyebrow">COMPTABILITÉ</span>
            <h2>{form.title}</h2>
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
        </header>
        <div className="dialog-body">
          {form.help && <p className="muted">{form.help}</p>}
          {error && (
            <div className="alert error" role="alert">
              {error}
            </div>
          )}
          {form.fields.map((f) => (
            <label key={f.name}>
              {f.label}
              {f.type === "file" ? (
                <input
                  type="file"
                  accept=".csv,text/csv"
                  required
                  onChange={(e) => void readFile(e.target.files?.[0], f.name)}
                />
              ) : f.options ? (
                <select
                  required={!f.optional}
                  multiple={f.multiple}
                  size={f.multiple ? 6 : undefined}
                  value={values[f.name] || (f.multiple ? [] : "")}
                  onChange={(e) =>
                    setValues({
                      ...values,
                      [f.name]: f.multiple
                        ? Array.from(e.target.selectedOptions).map(
                            (o) => o.value,
                          )
                        : e.target.value,
                    })
                  }
                >
                  {!f.multiple && (
                    <option value="">
                      {f.optional ? "Aucun" : "Choisir…"}
                    </option>
                  )}
                  {f.options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  required={!f.optional}
                  type={f.type || "text"}
                  step={f.type === "number" ? "0.01" : undefined}
                  maxLength={f.type === "text" || !f.type ? 250 : undefined}
                  value={values[f.name] || ""}
                  onChange={(e) =>
                    setValues({ ...values, [f.name]: e.target.value })
                  }
                />
              )}
            </label>
          ))}
          {review && (
            <div className="cycle-review">
              <h3>Vérifiez les comptes avant de confirmer</h3>
              <p>
                Lot {review.lot} · {review.old_owner} → {review.new_owner} ·{" "}
                {review.effective_date}
              </p>
              {review.adjustments.map((a: Row, i: number) => (
                <section key={i}>
                  <p>
                    <strong>{a.label}</strong> · {a.date} · {a.year}
                  </p>
                  <Table
                    rows={a.lines}
                    keys={["name", "code", "debit", "credit"]}
                  />
                </section>
              ))}
              <h3>Soldes prévus après le changement</h3>
              <Table rows={review.balances} keys={["name", "balance"]} />
              <p className="muted">
                Les montants sont enregistrés dans les comptes ; aucun
                remboursement, prélèvement ni courriel n’est exécuté.
              </p>
            </div>
          )}
        </div>
        <footer className="dialog-footer">
          <button
            className="button secondary"
            type="button"
            disabled={busy}
            onClick={onClose}
          >
            Annuler
          </button>
          <button
            className="button"
            disabled={
              busy ||
              (form.fields.some((f) => f.type === "file") && !values.csv)
            }
          >
            {busy
              ? "Vérification…"
              : form.review && !review
                ? "Prévisualiser"
                : review
                  ? "Confirmer ces changements"
                  : "Valider"}
          </button>
        </footer>
      </form>
    </dialog>
  );
}

function OpeningForm({
  context,
  year: _year,
  onClose,
  onSubmit,
}: {
  context: Row;
  year: string;
  onClose: () => void;
  onSubmit: (v: Row) => Promise<void>;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [rows, setRows] = useState<Row[]>([
    { code: "512", debit: "", credit: "" },
    { code: "450", debit: "", credit: "" },
  ]);
  const [reference, setReference] = useState("");
  const [operationId] = useState(newOperationId);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  function update(i: number, k: string, v: string) {
    setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  }
  return (
    <dialog
      ref={ref}
      className="editor-dialog cycle-opening-dialog"
      onCancel={onClose}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await onSubmit({ lines: rows, reference, request_id: operationId });
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <header className="dialog-heading">
          <div>
            <span className="eyebrow">REPRISE INITIALE</span>
            <h2>Balance transmise par l’ancien syndic</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            disabled={busy}
            aria-label="Fermer"
          >
            <Icon name="close" />
          </button>
        </header>
        <div className="dialog-body">
          <p className="muted">
            Saisissez les soldes des comptes de bilan. Un solde débiteur va au
            débit, un solde créditeur au crédit. Identifiez chaque tiers et
            chaque lot pour le fonds travaux.
          </p>
          {error && <div className="alert error">{error}</div>}
          <label>
            Référence de la balance
            <input
              value={reference}
              maxLength={100}
              onChange={(e) => setReference(e.target.value)}
            />
          </label>
          {rows.map((r, i) => (
            <div className="cycle-opening-row" key={i}>
              <label>
                Compte
                <input
                  list="opening-accounts"
                  required
                  value={r.code}
                  onChange={(e) => update(i, "code", e.target.value)}
                />
              </label>
              <label>
                Copropriétaire
                <select
                  value={r.owner || ""}
                  onChange={(e) => update(i, "owner", e.target.value)}
                  required={r.code.startsWith("450")}
                >
                  <option value="">Aucun</option>
                  {context.owners.map((o: Row) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Fournisseur
                <select
                  value={r.supplier || ""}
                  onChange={(e) => update(i, "supplier", e.target.value)}
                >
                  <option value="">Aucun</option>
                  {context.suppliers.map((o: Row) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Lot
                <select
                  value={r.lot || ""}
                  required={r.code.startsWith("105")}
                  onChange={(e) => update(i, "lot", e.target.value)}
                >
                  <option value="">Aucun</option>
                  {context.lots.map((l: Row) => (
                    <option key={l.id} value={l.id}>
                      Lot {l.number}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Débit (€)
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={r.debit}
                  onChange={(e) => update(i, "debit", e.target.value)}
                />
              </label>
              <label>
                Crédit (€)
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={r.credit}
                  onChange={(e) => update(i, "credit", e.target.value)}
                />
              </label>
              <button
                type="button"
                className="icon-button"
                disabled={rows.length <= 2}
                aria-label="Retirer la ligne"
                onClick={() => setRows(rows.filter((_, j) => i !== j))}
              >
                <Icon name="close" />
              </button>
            </div>
          ))}
          <datalist id="opening-accounts">
            {context.accounts.map((a: Row) => (
              <option key={a.code} value={a.code}>
                {a.name}
              </option>
            ))}
          </datalist>
          <button
            type="button"
            className="text-link"
            onClick={() =>
              setRows([...rows, { code: "", debit: "", credit: "" }])
            }
          >
            Ajouter une ligne
          </button>
          <p>
            <strong>
              Débit {money(rows.reduce((t, r) => t + Number(r.debit || 0), 0))}{" "}
              · Crédit{" "}
              {money(rows.reduce((t, r) => t + Number(r.credit || 0), 0))}
            </strong>
          </p>
        </div>
        <footer className="dialog-footer">
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={onClose}
          >
            Annuler
          </button>
          <button className="button" disabled={busy}>
            {busy ? "Contrôle…" : "Valider la reprise"}
          </button>
        </footer>
      </form>
    </dialog>
  );
}
