import { useEffect, useRef, useState } from "react";
import { api, newOperationId, type Owner, type Lot } from "../api";
import { number } from "../format";
import { Icon, Empty } from "./ui";

type Row = Record<string, any>;
type Field = {
  name: string;
  label: string;
  type?: string;
  optional?: boolean;
  options?: { value: string; label: string }[];
};
const euro = (value: string | number) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(
    Number(value),
  );
const day = () => new Date().toLocaleDateString("en-CA");
const dateText = (value: string) =>
  new Date(value + "T12:00:00").toLocaleDateString("fr-FR");
const tabs = {
  keys: "Charges",
  calls: "Appels de fonds",
  expenses: "Dépenses",
  treasury: "Trésorerie",
  entries: "Journal",
  reports: "Rapports",
};
type Tab = keyof typeof tabs;

export function Finance({
  manager,
  section,
}: {
  manager: boolean;
  section?: string;
}) {
  const [localTab, setTab] = useState<Tab>(manager ? "keys" : "reports");
  const tab = (section || localTab) as Tab;
  const [data, setData] = useState<Record<string, Row[]>>({});
  const [years, setYears] = useState<Row[]>([]);
  const [keys, setKeys] = useState<Row[]>([]);
  const [owners, setOwners] = useState<Owner[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [choices, setChoices] = useState<Row>({ suppliers: [], documents: [] });
  const [selectedYear, setSelectedYear] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const loadRequest = useRef(0);
  const [form, setForm] = useState<{
    resource: string;
    title: string;
    fields: Field[];
    defaults?: Row;
  } | null>(null);
  const [preview, setPreview] = useState<Row[] | null>(null);
  const [shares, setShares] = useState<Row | null>(null);
  const [confirmation, setConfirmation] = useState<{
    title: string;
    message: string;
    action: () => Promise<void>;
  } | null>(null);
  async function load() {
    const request = ++loadRequest.current;
    setError("");
    try {
      const resources = manager
        ? [
            ...new Set([
              "years",
              "keys",
              tab,
              "manage/organization",
              ...(["calls", "expenses", "treasury", "entries"].includes(tab)
                ? ["manage/centers"]
                : []),
              ...(tab === "entries" ? ["accounts", "manage/journals"] : []),
              ...(["expenses", "treasury", "entries"].includes(tab)
                ? ["banks"]
                : []),
            ]),
          ]
        : ["years", tab];
      const results = await Promise.all(
        resources.map((r) => api<{ items: Row[] }>(`finance/${r}`)),
      );
      const all = Object.fromEntries(
        resources.map((r, i) => [r, results[i].items]),
      );
      if (request !== loadRequest.current) return;
      setData(all);
      setYears(all.years);
      setKeys(all.keys || []);
      if (!selectedYear && all.years.length)
        setSelectedYear(String(all.years[0].id));
      if (manager) {
        const [o, l] = await Promise.all([
          ["treasury", "entries"].includes(tab)
            ? api<{ items: Owner[] }>("owners")
            : Promise.resolve({ items: [] }),
          tab === "keys"
            ? api<{ items: Lot[] }>("lots")
            : Promise.resolve({ items: [] }),
        ]);
        if (request !== loadRequest.current) return;
        setOwners(o.items);
        setLots(l.items);
        if (["calls", "expenses"].includes(tab)) {
          const ctx = await api<Row>("finance/cycle/context");
          if (request === loadRequest.current)
            setChoices((v) => ({
              ...v,
              projects: ctx.projects,
              accounts: ctx.accounts,
            }));
        }
        if (["expenses", "entries"].includes(tab)) {
          const options = await api<Row>("operations/options");
          if (request === loadRequest.current)
            setChoices((v) => ({ ...v, ...options }));
        }
      }
    } catch (e) {
      if (request === loadRequest.current) setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
    return () => {
      loadRequest.current += 1;
    };
  }, [manager, tab]);
  const yearOptions = years
    .filter((y) => !y.closed)
    .map((y) => ({ value: String(y.id), label: y.name }));
  const keyOptions = keys.map((k) => ({ value: String(k.id), label: k.name }));
  const ownerOptions = owners.map((o) => ({
    value: String(o.id),
    label: `${o.first_name} ${o.last_name}`,
  }));
  const yearField: Field = {
    name: "year",
    label: "Exercice",
    options: yearOptions,
  };
  const keyField: Field = {
    name: "key",
    label: "Catégorie de charges",
    options: keyOptions,
  };
  const dateField: Field = { name: "date", label: "Date", type: "date" };
  const amountField: Field = {
    name: "amount",
    label: "Montant (€)",
    type: "number",
  };
  const bankField: Field = {
    name: "bank",
    label: "Compte bancaire",
    optional: !(data.banks || []).length,
    options: (data.banks || [])
      .filter((b) => b.active && b.account_active)
      .map((b) => ({
        value: String(b.id),
        label: `${b.name} · ${b.account_code}${b.is_default ? " (par défaut)" : ""}`,
      })),
  };
  const defaultBank = (data.banks || []).find(
    (b) => b.is_default && b.active && b.account_active,
  )?.id;
  const labelField: Field = { name: "label", label: "Libellé" };
  async function perform(path: string, body: unknown = {}) {
    setBusy(true);
    setError("");
    try {
      await api(path, "POST", body);
      setNotice("Opération enregistrée.");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const rows = (data[tab] || []).filter(
    (r) => !selectedYear || !r.year || String(r.year) === selectedYear,
  );
  function add() {
    const common = {
      date:
        data["manage/organization"]?.[0]?.default_today === false ? "" : day(),
      year: selectedYear,
    };
    const analytic: Field = {
      name: "cost_center",
      label: "Comptabilité analytique",
      optional: !data["manage/organization"]?.[0]?.analytic_required,
      options: (data["manage/centers"] || [])
        .filter((c) => c.active)
        .map((c) => ({ value: String(c.id), label: c.name })),
    };
    if (tab === "keys")
      setForm({
        resource: "keys",
        title: "Nouvelle catégorie de charges",
        fields: [
          { name: "name", label: "Nom" },
          {
            name: "general",
            label: "Répartition",
            options: [
              { value: "true", label: "Tantièmes généraux" },
              { value: "false", label: "Tantièmes propres à cette catégorie" },
            ],
          },
          {
            name: "annual_budget",
            label: "Budget indicatif annuel (€)",
            type: "number",
          },
        ],
        defaults: { general: "true", annual_budget: "0" },
      });
    if (tab === "calls")
      setForm({
        resource: "calls",
        title: "Préparer un appel de fonds",
        fields: [
          yearField,
          keyField,
          labelField,
          dateField,
          { name: "due_date", label: "Échéance", type: "date" },
          amountField,
          {
            name: "kind",
            label: "Nature de l’appel",
            options: [
              { value: "current", label: "Budget courant" },
              { value: "works", label: "Travaux votés" },
              { value: "fund", label: "Fonds travaux" },
              { value: "advance", label: "Avance de trésorerie" },
            ],
          },
          {
            name: "project",
            label: "Opération de travaux",
            optional: true,
            options: (choices.projects || [])
              .filter((p: Row) => !p.completed_on)
              .map((p: Row) => ({ value: String(p.id), label: p.name })),
          },
          {
            name: "decision",
            label: "Décision de financement (travaux)",
            optional: true,
          },
          analytic,
        ],
        defaults: { ...common, due_date: day(), kind: "current" },
      });
    if (tab === "expenses")
      setForm({
        resource: "expenses",
        title: "Enregistrer une facture",
        fields: [
          yearField,
          keyField,
          {
            name: "supplier_record",
            label: "Fournisseur de l’annuaire",
            optional: true,
            options: choices.suppliers
              .filter((s: Row) => !s.archived)
              .map((s: Row) => ({ value: String(s.id), label: s.name })),
          },
          { name: "supplier", label: "Nom du fournisseur (saisie libre)" },
          {
            name: "document",
            label: "Pièce de la facture",
            optional: true,
            options: choices.documents.map((d: Row) => ({
              value: String(d.id),
              label: d.title,
            })),
          },
          { name: "reference", label: "Référence de facture" },
          labelField,
          dateField,
          amountField,
          {
            name: "due_date",
            label: "Échéance de la facture",
            type: "date",
            optional: true,
          },
          {
            name: "charge_code",
            label: "Compte de charges",
            optional: false,
            options: (choices.accounts || [])
              .filter((a: Row) => a.code.startsWith("6"))
              .map((a: Row) => ({
                value: a.code,
                label: `${a.code} · ${a.name}`,
              })),
          },
          {
            name: "project",
            label: "Travaux concernés (sinon charges courantes)",
            optional: true,
            options: (choices.projects || [])
              .filter((p: Row) => !p.completed_on)
              .map((p: Row) => ({ value: String(p.id), label: p.name })),
          },
          analytic,
        ],
        defaults: common,
      });
    if (tab === "treasury")
      setForm({
        resource: "receipts",
        title: "Enregistrer un règlement copropriétaire",
        fields: [
          yearField,
          { name: "owner", label: "Copropriétaire", options: ownerOptions },
          dateField,
          amountField,
          { name: "reference", label: "Référence bancaire", optional: true },
          bankField,
          analytic,
        ],
        defaults: { ...common, bank: defaultBank || "" },
      });
    if (tab === "reports")
      setForm({
        resource: "reports",
        title: "Publier une synthèse partagée",
        fields: [
          {
            ...yearField,
            options: years.map((y) => ({ value: String(y.id), label: y.name })),
          },
          { name: "title", label: "Titre" },
        ],
        defaults: { year: selectedYear },
      });
    if (tab === "entries")
      setForm({
        resource: "entries",
        title: "Nouvelle écriture comptable",
        fields: [
          yearField,
          dateField,
          labelField,
          {
            name: "journal",
            label: "Journal",
            options: (data["manage/journals"] || [])
              .filter((j) => j.active)
              .map((j) => ({ value: j.code, label: j.name })),
          },
          analytic,
        ],
        defaults: {
          ...common,
          journal:
            data["manage/journals"]?.find((j) => j.is_default)?.code || "OD",
        },
      });
  }
  return (
    <div className="finance">
      {!section && (
        <div className="finance-toolbar">
          <div className="finance-tabs" role="tablist" aria-label="Finances">
            {Object.entries(tabs)
              .filter(
                ([key]) => manager || !["expenses", "entries"].includes(key),
              )
              .map(([key, label]) => (
                <button
                  role="tab"
                  aria-selected={tab === key}
                  key={key}
                  className={`button ${tab === key ? "primary" : "secondary"}`}
                  onClick={() => {
                    setTab(key as Tab);
                    setNotice("");
                  }}
                >
                  {label}
                </button>
              ))}
          </div>
        </div>
      )}
      <div className="finance-year">
        <label>
          Exercice
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
          >
            <option value="">Tous les exercices</option>
            {years.map((y) => (
              <option key={y.id} value={y.id}>
                {y.name}
                {y.closed ? " — verrouillé" : ""}
              </option>
            ))}
          </select>
        </label>
        {manager && (
          <>
            <button
              className="button secondary"
              onClick={() =>
                setForm({
                  resource: "years",
                  title: "Nouvel exercice",
                  fields: [
                    { name: "name", label: "Nom de l’exercice" },
                    { name: "starts_on", label: "Début", type: "date" },
                    { name: "ends_on", label: "Fin", type: "date" },
                  ],
                })
              }
            >
              <Icon name="plus" size={15} />
              Nouvel exercice
            </button>
          </>
        )}
        {manager && tab === "entries" && (
          <button
            className="button secondary"
            onClick={() =>
              setForm({
                resource: "accounts",
                title: "Nouveau compte",
                fields: [
                  { name: "code", label: "Code comptable" },
                  { name: "name", label: "Libellé" },
                ],
              })
            }
          >
            Compte
          </button>
        )}
        {manager && tab === "calls" && (
          <button
            className="button secondary"
            disabled={busy}
            onClick={() =>
              setForm({
                resource: "cycle/call-schedule",
                title: "Préparer un échéancier d’appels",
                fields: [
                  yearField,
                  keyField,
                  { name: "label", label: "Libellé de l’échéancier" },
                  amountField,
                  {
                    name: "first_date",
                    label: "Première date d’exigibilité",
                    type: "date",
                  },
                  {
                    name: "count",
                    label: "Nombre d’appels (1 à 12)",
                    type: "number",
                  },
                  {
                    name: "interval",
                    label: "Espacement en mois (1 à 12)",
                    type: "number",
                  },
                  {
                    name: "kind",
                    label: "Nature",
                    options: [
                      { value: "current", label: "Budget courant" },
                      { value: "works", label: "Travaux votés" },
                      { value: "fund", label: "Fonds travaux" },
                      { value: "advance", label: "Avance de trésorerie" },
                    ],
                  },
                  {
                    name: "project",
                    label: "Opération de travaux",
                    optional: true,
                    options: (choices.projects || [])
                      .filter((p: Row) => !p.completed_on)
                      .map((p: Row) => ({
                        value: String(p.id),
                        label: p.name,
                      })),
                  },
                  {
                    name: "decision",
                    label: "Décision de financement / échéancier",
                    optional: true,
                  },
                  {
                    name: "cost_center",
                    label: "Comptabilité analytique",
                    optional:
                      !data["manage/organization"]?.[0]?.analytic_required,
                    options: (data["manage/centers"] || [])
                      .filter((c) => c.active)
                      .map((c) => ({ value: String(c.id), label: c.name })),
                  },
                ],
                defaults: {
                  year: selectedYear,
                  label: "Provisions annuelles",
                  first_date:
                    years.find((y) => String(y.id) === selectedYear)
                      ?.starts_on || day(),
                  count: "4",
                  interval: "3",
                  kind: "current",
                  request_id: newOperationId(),
                },
              })
            }
          >
            Échéancier d’appels
          </button>
        )}
        {manager && (
          <button className="button primary" disabled={busy} onClick={add}>
            <Icon name="plus" size={15} />
            {tab === "keys"
              ? "Catégorie"
              : tab === "calls"
                ? "Appel de fonds"
                : tab === "expenses"
                  ? "Facture"
                  : tab === "treasury"
                    ? "Encaissement"
                    : tab === "entries"
                      ? "Écriture"
                      : "Publier un rapport"}
          </button>
        )}
      </div>
      {error && (
        <div className="alert" role="alert">
          {error}
          <button onClick={() => void load()}>Actualiser</button>
        </div>
      )}
      {notice && (
        <p className="finance-notice" role="status">
          {notice}
        </p>
      )}
      {tab === "treasury" ? (
        <>
          <div className="stats-grid">
            {(data.treasury || [])
              .filter((r) => !selectedYear || String(r.id) === selectedYear)
              .map((r) => (
                <article className="stat-card" key={r.id}>
                  <p>{r.year}</p>
                  <strong>{euro(r.treasury_movement)}</strong>
                  <p>Mouvement net du compte banque sur l’exercice</p>
                </article>
              ))}
          </div>
          <p className="muted">
            Le solde bancaire réel nécessite la reprise des soldes d’ouverture
            et un rapprochement avec les relevés.
          </p>
        </>
      ) : tab === "reports" ? (
        <>
          <section className="panel">
            <div className="panel-heading">
              <h2>Synthèses publiées</h2>
            </div>
            {rows.map((r) => (
              <article className="report-card" key={r.id}>
                <h3>{r.title}</h3>
                <p className="muted">
                  Publié le{" "}
                  {new Date(r.published_at).toLocaleDateString("fr-FR")} —{" "}
                  {r.data.year}
                </p>
                <dl>
                  <dt>Charges comptabilisées</dt>
                  <dd>{euro(r.data.charges)}</dd>
                  <dt>Provisions comptabilisées</dt>
                  <dd>{euro(r.data.provisions)}</dd>
                  <dt>Mouvement bancaire net</dt>
                  <dd>{euro(r.data.treasury_movement)}</dd>
                </dl>
                <button
                  className="button secondary"
                  onClick={() => window.print()}
                >
                  Imprimer
                </button>
              </article>
            ))}
            {!rows.length && (
              <Empty
                title="Aucun rapport publié"
                description="Les synthèses validées par le gestionnaire seront accessibles ici."
              />
            )}
          </section>
          {manager && selectedYear && <Balance year={selectedYear} />}
        </>
      ) : (
        <section className="panel">
          <div className="panel-heading">
            <h2>{tabs[tab]}</h2>
            <span className="count-pill">{rows.length}</span>
          </div>
          {rows.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {(tab === "keys"
                      ? [
                          "Catégorie",
                          "Répartition",
                          "Budget annuel indicatif",
                          "Actions",
                        ]
                      : tab === "calls"
                        ? ["Appel", "Date / échéance", "Montant", "État"]
                        : tab === "expenses"
                          ? ["Facture", "Fournisseur", "Montant", "Règlement"]
                          : ["N° / date", "Journal / libellé", "Écritures"]
                    ).map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id}>
                      {tab === "keys" ? (
                        <>
                          <td>{r.name}</td>
                          <td>
                            {r.general
                              ? "Tantièmes généraux"
                              : "Tantièmes spécifiques"}
                          </td>
                          <td>{euro(r.annual_budget)}</td>
                          <td>
                            {manager && !r.general && (
                              <button
                                className="edit-button"
                                onClick={() => setShares(r)}
                              >
                                Définir les tantièmes
                              </button>
                            )}
                          </td>
                        </>
                      ) : tab === "calls" ? (
                        <>
                          <td>
                            <strong>{r.label}</strong>
                            <small>{r.key_name}</small>
                          </td>
                          <td>
                            {dateText(r.date)}
                            <small>Échéance : {dateText(r.due_date)}</small>
                          </td>
                          <td>{euro(r.amount)}</td>
                          <td>
                            <span className="subtle-badge">
                              {r.cancelled
                                ? "Annulé"
                                : r.posted
                                  ? "Validé"
                                  : "Brouillon"}
                            </span>
                            {manager && !r.posted && (
                              <>
                                <button
                                  className="edit-button"
                                  onClick={async () => {
                                    try {
                                      const result = await api<{
                                        items: Row[];
                                      }>(
                                        `finance/calls/${r.id}/preview`,
                                        "POST",
                                        {},
                                      );
                                      setPreview(result.items);
                                    } catch (e) {
                                      setError((e as Error).message);
                                    }
                                  }}
                                >
                                  Prévisualiser la répartition
                                </button>
                                <button
                                  disabled={busy}
                                  className="edit-button"
                                  onClick={() =>
                                    setConfirmation({
                                      title: "Valider cet appel ?",
                                      message:
                                        "La répartition sera figée et une écriture équilibrée sera enregistrée. L’appel validé ne pourra plus être modifié.",
                                      action: () =>
                                        perform(
                                          `finance/calls/${r.id}/publish`,
                                        ),
                                    })
                                  }
                                >
                                  Valider
                                </button>
                              </>
                            )}
                          </td>
                        </>
                      ) : tab === "expenses" ? (
                        <>
                          <td>
                            <strong>{r.label}</strong>
                            <small>
                              {r.reference} · {dateText(r.date)}
                            </small>
                          </td>
                          <td>
                            {r.supplier}
                            <small>
                              {r.supplier_record
                                ? "Fournisseur identifié"
                                : "Saisie libre / historique"}
                            </small>
                            {r.document && (
                              <a
                                className="text-link"
                                href={`/api/documents/items/${r.document}/download/`}
                              >
                                Voir la facture
                              </a>
                            )}
                          </td>
                          <td>
                            {euro(r.amount)}
                            <small>Payé : {euro(r.amount_paid || 0)}</small>
                            <small>Reste : {euro(r.remaining || 0)}</small>
                          </td>
                          <td>
                            {r.cancelled ? (
                              <span className="subtle-badge">Annulée</span>
                            ) : r.paid ? (
                              <span className="subtle-badge">Réglée</span>
                            ) : (
                              <button
                                className="edit-button"
                                onClick={() =>
                                  setForm({
                                    resource: `expenses/${r.id}/pay`,
                                    title: "Enregistrer un règlement",
                                    fields: [
                                      yearField,
                                      dateField,
                                      bankField,
                                      {
                                        name: "amount",
                                        label: "Montant versé (€)",
                                        type: "number",
                                      },
                                    ],
                                    defaults: {
                                      year:
                                        yearOptions.find(
                                          (y) =>
                                            day() >=
                                              (years.find(
                                                (v) => String(v.id) === y.value,
                                              )?.starts_on || "") &&
                                            day() <=
                                              (years.find(
                                                (v) => String(v.id) === y.value,
                                              )?.ends_on || ""),
                                        )?.value || String(r.year),
                                      date: day(),
                                      amount: r.remaining,
                                      bank: defaultBank || "",
                                    },
                                  })
                                }
                              >
                                Enregistrer le paiement
                              </button>
                            )}
                            {!!r.payments?.length && (
                              <details className="payment-history">
                                <summary>
                                  {r.payments.length} règlement
                                  {r.payments.length > 1 ? "s" : ""}
                                </summary>
                                <ul>
                                  {r.payments.map((p: Row) => (
                                    <li key={p.id}>
                                      {dateText(p.date)} · {euro(p.amount)} ·
                                      écriture {p.number}
                                      {` · ${p.bank_name || "Banque historique"}`}
                                    </li>
                                  ))}
                                </ul>
                              </details>
                            )}
                          </td>
                        </>
                      ) : (
                        <>
                          <td>
                            {r.number}
                            <small>{dateText(r.date)}</small>
                          </td>
                          <td>
                            {r.journal}
                            <small>{r.label}</small>
                          </td>
                          <td>
                            {r.lines.map((l: Row, i: number) => (
                              <div key={i}>
                                {l.code} : {euro(l.debit)} débit /{" "}
                                {euro(l.credit)} crédit
                              </div>
                            ))}
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="Aucun élément enregistré"
              description="Les opérations de cet exercice apparaîtront ici."
            />
          )}
        </section>
      )}
      {form && (
        <FinanceForm
          {...form}
          owners={owners}
          accounts={data.accounts || []}
          suppliers={choices.suppliers}
          onClose={() => setForm(null)}
          onSaved={async () => {
            setForm(null);
            setNotice("Opération enregistrée.");
            await load();
          }}
        />
      )}
      {preview && (
        <ReadDialog
          title="Répartition prévisionnelle"
          onClose={() => setPreview(null)}
        >
          <table>
            <thead>
              <tr>
                <th>Lot</th>
                <th>Copropriétaire</th>
                <th>Tantièmes</th>
                <th>Montant</th>
              </tr>
            </thead>
            <tbody>
              {preview.map((r, i) => (
                <tr key={i}>
                  <td>{r.lot}</td>
                  <td>{r.owner}</td>
                  <td>{number(r.shares)}</td>
                  <td>{euro(r.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ReadDialog>
      )}
      {shares && (
        <SharesDialog
          category={shares}
          lots={lots}
          onClose={() => setShares(null)}
          onSaved={async () => {
            setShares(null);
            await load();
          }}
        />
      )}
      {confirmation && (
        <ConfirmDialog
          {...confirmation}
          onClose={() => setConfirmation(null)}
        />
      )}
    </div>
  );
}

function FinanceForm({
  resource,
  title,
  fields,
  defaults = {},
  owners,
  accounts,
  suppliers,
  onClose,
  onSaved,
}: {
  resource: string;
  title: string;
  fields: Field[];
  defaults?: Row;
  owners: Owner[];
  accounts: Row[];
  suppliers: Row[];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [supplierRecord, setSupplierRecord] = useState("");
  const [operationId] = useState(newOperationId);
  const [lines, setLines] = useState<Row[]>([
    { code: "512", debit: "", credit: "", owner: "" },
    { code: "450", debit: "", credit: "", owner: "" },
  ]);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data: Row = {
      ...defaults,
      ...Object.fromEntries(new FormData(event.currentTarget)),
      request_id: defaults.request_id || operationId,
    };
    if ("general" in data) data.general = data.general === "true";
    if (resource === "entries") data.lines = lines;
    try {
      await api(`finance/${resource}`, "POST", data);
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const chart = [
    { code: "401", name: "Fournisseurs" },
    { code: "450", name: "Copropriétaires" },
    { code: "512", name: "Banque" },
    { code: "601", name: "Charges courantes" },
    { code: "701", name: "Provisions" },
    ...accounts.filter(
      (a) => !["401", "450", "512", "601", "701"].includes(a.code),
    ),
  ];
  return (
    <dialog
      ref={dialog}
      className="editor-dialog finance-dialog"
      onCancel={(event) => {
        if (busy) event.preventDefault();
        else onClose();
      }}
      aria-labelledby="finance-form-title"
    >
      <form onSubmit={submit}>
        <div className="dialog-heading">
          <h2 id="finance-form-title">{title}</h2>
        </div>
        <div className="form-fields">
          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}
          {fields.map((f) => (
            <label key={f.name}>
              {f.label}
              {!f.optional && " *"}
              {f.options ? (
                <select
                  name={f.name}
                  required={!f.optional}
                  defaultValue={
                    f.name === "charge_code"
                      ? ""
                      : (defaults[f.name] ??
                        (f.optional ? "" : f.options[0]?.value || ""))
                  }
                  onChange={
                    f.name === "supplier_record"
                      ? (e) => setSupplierRecord(e.target.value)
                      : undefined
                  }
                >
                  <option value="" disabled={!f.optional}>
                    {f.optional
                      ? f.name === "supplier_record"
                        ? "Saisir un nom libre…"
                        : f.name === "bank"
                          ? "Banque historique (512)"
                          : "Aucun"
                      : "Choisir…"}
                  </option>
                  {f.options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  name={f.name}
                  required={
                    !f.optional && !(f.name === "supplier" && supplierRecord)
                  }
                  disabled={f.name === "supplier" && !!supplierRecord}
                  type={f.type || "text"}
                  step={f.type === "number" ? "0.01" : undefined}
                  min={f.type === "number" ? "0" : undefined}
                  maxLength={150}
                  defaultValue={defaults[f.name]}
                />
              )}
            </label>
          ))}
          {resource === "entries" && (
            <div className="entry-lines">
              {lines.map((line, i) => (
                <fieldset key={i}>
                  <legend>Ligne {i + 1}</legend>
                  <label>
                    Compte
                    <select
                      value={line.code}
                      onChange={(e) =>
                        setLines(
                          lines.map((l, j) =>
                            j === i
                              ? {
                                  ...l,
                                  code: e.target.value,
                                  supplier: e.target.value.startsWith("40")
                                    ? l.supplier
                                    : "",
                                }
                              : l,
                          ),
                        )
                      }
                    >
                      {chart.map((a) => (
                        <option key={a.code} value={a.code}>
                          {a.code} — {a.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Fournisseur (compte 40)
                    <select
                      value={line.supplier || ""}
                      disabled={!line.code.startsWith("40")}
                      onChange={(e) =>
                        setLines(
                          lines.map((l, j) =>
                            j === i
                              ? {
                                  ...l,
                                  supplier: e.target.value,
                                  owner: e.target.value ? "" : l.owner,
                                }
                              : l,
                          ),
                        )
                      }
                    >
                      <option value="">Sans fournisseur identifié</option>
                      {suppliers
                        .filter((s) => !s.archived)
                        .map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label>
                    Copropriétaire (si applicable)
                    <select
                      value={line.owner}
                      onChange={(e) =>
                        setLines(
                          lines.map((l, j) =>
                            j === i
                              ? {
                                  ...l,
                                  owner: e.target.value,
                                  supplier: e.target.value ? "" : l.supplier,
                                }
                              : l,
                          ),
                        )
                      }
                    >
                      <option value="">Sans tiers</option>
                      {owners.map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.first_name} {o.last_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="form-row">
                    {["debit", "credit"].map((side) => (
                      <label key={side}>
                        {side === "debit" ? "Débit (€)" : "Crédit (€)"}
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={line[side]}
                          onChange={(e) =>
                            setLines(
                              lines.map((l, j) =>
                                j === i ? { ...l, [side]: e.target.value } : l,
                              ),
                            )
                          }
                        />
                      </label>
                    ))}
                  </div>
                  {lines.length > 2 && (
                    <button
                      type="button"
                      className="delete-link"
                      onClick={() => setLines(lines.filter((_, j) => j !== i))}
                    >
                      Retirer la ligne
                    </button>
                  )}
                </fieldset>
              ))}
              <button
                type="button"
                className="button secondary"
                onClick={() =>
                  setLines([
                    ...lines,
                    { code: "512", debit: "", credit: "", owner: "" },
                  ])
                }
              >
                Ajouter une ligne
              </button>
            </div>
          )}
        </div>
        <div className="dialog-footer">
          <button
            type="button"
            disabled={busy}
            className="button secondary"
            onClick={onClose}
          >
            Annuler
          </button>
          <button className="button primary" disabled={busy}>
            {busy ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </form>
    </dialog>
  );
}

function ReadDialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="editor-dialog finance-dialog"
      onCancel={onClose}
    >
      <div className="dialog-heading">
        <h2>{title}</h2>
      </div>
      <div className="table-scroll">{children}</div>
      <div className="dialog-footer">
        <button className="button secondary" onClick={onClose}>
          Fermer
        </button>
      </div>
    </dialog>
  );
}
function ConfirmDialog({
  title,
  message,
  action,
  onClose,
}: {
  title: string;
  message: string;
  action: () => Promise<void>;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <ReadDialog
      title={title}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <div className="form-fields">
        <p>{message}</p>
        <button
          className="button primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await action();
              onClose();
            } finally {
              setBusy(false);
            }
          }}
        >
          Confirmer
        </button>
      </div>
    </ReadDialog>
  );
}
function SharesDialog({
  category,
  lots,
  onClose,
  onSaved,
}: {
  category: Row;
  lots: Lot[];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(
      category.shares.map((s: Row) => [String(s.lot), s.value]),
    ),
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <ReadDialog title={`Tantièmes — ${category.name}`} onClose={onClose}>
      <div className="form-fields">
        {lots.map((l) => (
          <label key={l.id}>
            Lot {l.number}
            <input
              type="number"
              min="0"
              step="0.01"
              value={values[l.id] || "0"}
              onChange={(e) => setValues({ ...values, [l.id]: e.target.value })}
            />
          </label>
        ))}
        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}
        <button
          className="button primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await api(`finance/keys/${category.id}/shares`, "PUT", {
                shares: lots.map((l) => ({
                  lot: l.id,
                  value: values[l.id] || "0",
                })),
              });
              await onSaved();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Enregistrer les tantièmes
        </button>
      </div>
    </ReadDialog>
  );
}
function Balance({ year }: { year: string }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ items: Row[] }>(`finance/balance?year=${encodeURIComponent(year)}`)
      .then((d) => {
        setRows(d.items);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, [year]);
  return (
    <section className="panel balance-panel">
      <div className="panel-heading">
        <h2>Balance générale</h2>
        <a
          className="button secondary"
          href={`/api/finance/balance/?year=${encodeURIComponent(year)}&format=csv`}
        >
          Exporter CSV
        </a>
      </div>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Compte</th>
              <th>Libellé</th>
              <th>Débit</th>
              <th>Crédit</th>
              <th>Solde</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.code}>
                <td>{r.code}</td>
                <td>{r.name}</td>
                <td>{euro(r.debit)}</td>
                <td>{euro(r.credit)}</td>
                <td>{euro(r.balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
