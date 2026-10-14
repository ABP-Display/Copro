import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Empty, Icon } from "./ui";
type Row = Record<string, any>;
type Field = {
  name: string;
  label: string;
  type?: string;
  optional?: boolean;
  options?: { value: string; label: string }[];
};
const euro = (value: any) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(
    Number(value),
  );
const today = () => new Date().toLocaleDateString("en-CA");

export function Accounting({
  administration = false,
  isAdmin = false,
  section,
  onOrganizationChange,
}: {
  administration?: boolean;
  isAdmin?: boolean;
  section?: string;
  onOrganizationChange?: () => void;
}) {
  const [localTab, setTab] = useState(
    administration ? "organization" : "accounts",
  );
  const tab = section || localTab;
  const [data, setData] = useState<Record<string, Row[]>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const loadRequest = useRef(0);
  const [editor, setEditor] = useState<{
    resource: string;
    item?: Row;
    fields: Field[];
    title: string;
    path?: string;
  } | null>(null);
  async function load() {
    const request = ++loadRequest.current;
    try {
      const dependencies: Record<string, string[]> = {
        organization: ["organization"],
        accounts: ["accounts"],
        centers: ["centers"],
        journals: ["journals"],
        budgets: ["budgets", "accounts", "centers"],
        templates: [
          "templates",
          "accounts",
          "journals",
          "centers",
          "organization",
        ],
        entries: ["organization", "centers"],
        users: isAdmin ? ["users"] : [],
        audit: ["audit"],
      };
      const resources = dependencies[tab] || [];
      const results = await Promise.all(
        resources.map((r) => api<{ items: Row[] }>(`finance/manage/${r}`)),
      );
      const years = ["budgets", "templates", "entries"].includes(tab)
        ? await api<{ items: Row[] }>("finance/years")
        : { items: [] };
      const entries =
        tab === "entries"
          ? await api<{ items: Row[] }>("finance/entries")
          : { items: [] };
      const keys =
        tab === "budgets"
          ? await api<{ items: Row[] }>("finance/keys")
          : { items: [] };
      if (request !== loadRequest.current) return;
      setData({
        ...Object.fromEntries(resources.map((r, i) => [r, results[i].items])),
        years: years.items,
        keys: keys.items,
        entries: entries.items,
      });
      setError("");
    } catch (e) {
      if (request === loadRequest.current) setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
    return () => {
      loadRequest.current += 1;
    };
  }, [isAdmin, tab]);
  const menus = administration
    ? {
        organization: "Coordonnées & paramètres",
        journals: "Journaux",
        ...(isAdmin ? { users: "Utilisateurs" } : {}),
        audit: "Historique",
      }
    : {
        accounts: "Plan comptable",
        centers: "Analytique",
        budgets: "Budgets",
        templates: "Modèles d’écriture",
        entries: "Écritures",
      };
  const options = (resource: string, label: string) =>
    (data[resource] || []).map((r) => ({
      value: String(r.id),
      label: label === "account" ? `${r.code} — ${r.name}` : String(r[label]),
    }));
  const year: Field = {
    name: "year",
    label: "Exercice",
    options: (data.years || [])
      .filter((y) => !y.closed)
      .map((y) => ({ value: String(y.id), label: y.name })),
  };
  const center: Field = {
    name: "cost_center",
    label: "Comptabilité analytique",
    optional: true,
    options: options("centers", "name"),
  };
  const specifications: Record<string, Field[]> = {
    accounts: [
      { name: "code", label: "Code comptable" },
      { name: "name", label: "Libellé" },
      { name: "active", label: "Compte actif", type: "checkbox" },
    ],
    centers: [
      { name: "name", label: "Nom" },
      { name: "active", label: "Actif", type: "checkbox" },
    ],
    journals: [
      { name: "code", label: "Code du journal" },
      { name: "name", label: "Libellé" },
      { name: "active", label: "Actif", type: "checkbox" },
    ],
    budgets: [
      year,
      {
        name: "account",
        label: "Compte de charges ou produits",
        options: (data.accounts || [])
          .filter((a) => a.code.startsWith("6") || a.code.startsWith("7"))
          .map((a) => ({
            value: String(a.id),
            label: `${a.code} — ${a.name}`,
          })),
      },
      center,
      {
        name: "key",
        label: "Clé de répartition du budget",
        optional: true,
        options: options("keys", "name"),
      },
      { name: "amount", label: "Budget annuel (€)", type: "number" },
      {
        name: "variance_note",
        label: "Explication de l’écart / contexte du budget",
        type: "textarea",
        optional: true,
      },
    ],
    organization: [
      { name: "name", label: "Nom de la copropriété" },
      { name: "address", label: "Adresse", type: "textarea", optional: true },
      { name: "email", label: "Courriel", type: "email", optional: true },
      { name: "phone", label: "Téléphone", optional: true },
      {
        name: "registration",
        label: "Identifiant / immatriculation",
        optional: true,
      },
      {
        name: "code_length",
        label: "Longueur minimale des codes comptables",
        type: "number",
      },
      {
        name: "analytic_required",
        label: "Analytique obligatoire",
        type: "checkbox",
      },
      {
        name: "report_prefix",
        label: "Préfixe par défaut des rapports",
        optional: true,
      },
      {
        name: "default_today",
        label: "Date du jour proposée pour une nouvelle écriture",
        type: "checkbox",
      },
    ],
    templates: [
      { name: "name", label: "Nom du modèle" },
      {
        name: "journal",
        label: "Journal",
        options: (data.journals || [])
          .filter((j) => j.active)
          .map((j) => ({ value: j.code, label: j.name })),
      },
    ],
  };
  function edit(resource: string, item?: Row) {
    setEditor({
      resource,
      item,
      fields: specifications[resource],
      title: item ? "Modifier" : "Ajouter",
    });
  }
  async function run(path: string, body: Row = {}) {
    setBusy(true);
    try {
      await api(path, "POST", body);
      setNotice("Modification enregistrée.");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const labels: Record<string, string> = {
    code: "Code",
    name: "Libellé",
    active: "Actif",
    is_default: "Par défaut",
    year: "Exercice",
    account: "Compte",
    cost_center: "Analytique",
    amount: "Budget",
    username: "Identifiant",
    email: "Courriel",
    is_staff: "Gestionnaire",
    is_superuser: "Administrateur principal",
    is_active: "Actif",
    last_login: "Dernière connexion",
    action: "Action",
    target: "Élément",
    created_at: "Date",
    actor__username: "Utilisateur",
    number: "N°",
    date: "Date",
    journal: "Journal",
    label: "Libellé",
    reference: "Référence",
    reversed: "Contrepassée",
  };
  const columns: Record<string, string[]> = {
    accounts: ["code", "name", "active"],
    journals: ["code", "name", "active", "is_default"],
    centers: ["name", "active"],
    budgets: [
      "year",
      "account",
      "cost_center",
      "key",
      "amount",
      "variance_note",
    ],
    templates: ["name", "journal"],
    users: ["username", "email", "is_staff", "is_superuser", "is_active"],
    audit: ["created_at", "actor__username", "action", "target"],
    entries: ["number", "date", "journal", "label", "cost_center", "reversed"],
  };
  function display(key: string, value: any) {
    if (value === true) return "Oui";
    if (value === false) return "Non";
    if (value === null || value === undefined || value === "") return "—";
    if (key === "amount") return euro(value);
    if (key === "year")
      return data.years?.find((y) => y.id === value)?.name || value;
    if (key === "account")
      return data.accounts?.find((a) => a.id === value)?.code || value;
    if (key === "cost_center")
      return data.centers?.find((c) => c.id === value)?.name || value;
    if (key === "key")
      return data.keys?.find((k) => k.id === value)?.name || value;
    if (key === "created_at") return new Date(value).toLocaleString("fr-FR");
    return String(value);
  }
  return (
    <section className="finance">
      {!section && (
        <div className="finance-tabs">
          {Object.entries(menus).map(([key, label]) => (
            <button
              className={`button ${tab === key ? "primary" : "secondary"}`}
              key={key}
              onClick={() => {
                setTab(key);
                setNotice("");
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}
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
      {tab === "organization" ? (
        <section className="panel">
          <div className="panel-heading">
            <h2>Configuration générale</h2>
            <button
              className="button primary"
              onClick={() => edit("organization", data.organization?.[0])}
            >
              Modifier
            </button>
          </div>
          <div className="configuration-details">
            {specifications.organization.map((f) => (
              <div key={f.name}>
                <strong>{f.label}</strong>
                <span>{display(f.name, data.organization?.[0]?.[f.name])}</span>
              </div>
            ))}
            <div>
              <strong>Devise / précision</strong>
              <span>EUR / 2 décimales</span>
            </div>
          </div>
        </section>
      ) : (
        <section className="panel">
          <div className="panel-heading">
            <h2>{(menus as Row)[tab]}</h2>
            <div className="finance-tabs">
              {specifications[tab] && (
                <button className="button primary" onClick={() => edit(tab)}>
                  <Icon name="plus" size={16} />
                  Ajouter
                </button>
              )}
              {tab === "accounts" && (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() =>
                    void run("finance/operations/initialize-chart/1")
                  }
                >
                  Compléter le plan français Diacamma
                </button>
              )}
            </div>
          </div>
          {data[tab]?.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {columns[tab]?.map((c) => (
                      <th key={c}>{labels[c] || c}</th>
                    ))}
                    {tab !== "audit" && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {data[tab].map((row) => (
                    <tr key={row.id}>
                      {columns[tab]?.map((c) => (
                        <td key={c}>{display(c, row[c])}</td>
                      ))}
                      {tab !== "audit" && (
                        <td>
                          <div className="row-actions">
                            {specifications[tab] && (
                              <button
                                className="edit-button"
                                onClick={() => edit(tab, row)}
                              >
                                Modifier
                              </button>
                            )}
                            {tab === "journals" && !row.is_default && (
                              <button
                                className="edit-button"
                                disabled={busy}
                                onClick={() =>
                                  void run(
                                    `finance/operations/default-journal/${row.id}`,
                                  )
                                }
                              >
                                Par défaut
                              </button>
                            )}
                            {tab === "templates" && (
                              <button
                                className="edit-button"
                                onClick={() =>
                                  setEditor({
                                    resource: "apply-template",
                                    path: `finance/operations/apply-template/${row.id}`,
                                    title: `Utiliser ${row.name}`,
                                    fields: [
                                      year,
                                      {
                                        name: "date",
                                        label: "Date",
                                        type: "date",
                                      },
                                      {
                                        name: "label",
                                        label: "Libellé",
                                        optional: true,
                                      },
                                      center,
                                    ],
                                    item: { date: today(), label: row.name },
                                  })
                                }
                              >
                                Utiliser
                              </button>
                            )}
                            {tab === "entries" && !row.reversed && (
                              <button
                                className="edit-button"
                                onClick={() =>
                                  setEditor({
                                    resource: "reverse",
                                    path: `finance/operations/reverse-entry/${row.id}`,
                                    title: "Contrepasser l’écriture",
                                    fields: [
                                      {
                                        name: "date",
                                        label: "Date de contrepassation",
                                        type: "date",
                                      },
                                    ],
                                    item: { date: today() },
                                  })
                                }
                              >
                                Contrepasser
                              </button>
                            )}
                            {tab === "users" && !row.is_superuser && (
                              <>
                                <button
                                  className="edit-button"
                                  disabled={busy}
                                  onClick={async () => {
                                    setBusy(true);
                                    try {
                                      await api(
                                        `finance/manage/users/${row.id}`,
                                        "PATCH",
                                        { is_active: !row.is_active },
                                      );
                                      await load();
                                    } catch (e) {
                                      setError((e as Error).message);
                                    } finally {
                                      setBusy(false);
                                    }
                                  }}
                                >
                                  {row.is_active ? "Désactiver" : "Activer"}
                                </button>
                                <button
                                  className="edit-button"
                                  onClick={() =>
                                    setEditor({
                                      resource: "users",
                                      item: row,
                                      title: "Modifier le rôle",
                                      fields: [
                                        {
                                          name: "is_staff",
                                          label:
                                            "Accès gestionnaire (écriture et données privées)",
                                          type: "checkbox",
                                        },
                                      ],
                                    })
                                  }
                                >
                                  Rôle
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="Aucun élément enregistré"
              description="Ajoutez les informations nécessaires à la gestion de votre copropriété."
            />
          )}
        </section>
      )}
      {editor && (
        <ResourceEditor
          {...editor}
          accounts={data.accounts || []}
          onClose={() => setEditor(null)}
          onSaved={async () => {
            setEditor(null);
            setNotice("Modification enregistrée.");
            await load();
            if (editor.resource === "organization") onOrganizationChange?.();
          }}
        />
      )}
    </section>
  );
}

function ResourceEditor({
  resource,
  item,
  fields,
  title,
  path,
  accounts,
  onClose,
  onSaved,
}: {
  resource: string;
  item?: Row;
  fields: Field[];
  title: string;
  path?: string;
  accounts: Row[];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [lines, setLines] = useState<Row[]>(
    item?.lines || [
      { code: "", debit: "", credit: "" },
      { code: "", debit: "", credit: "" },
    ],
  );
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const value: Row = Object.fromEntries(new FormData(form));
    for (const f of fields)
      if (f.type === "checkbox")
        value[f.name] = (
          form.elements.namedItem(f.name) as HTMLInputElement
        ).checked;
    if (resource === "templates") value.lines = lines;
    setBusy(true);
    try {
      await api(
        path || `finance/manage/${resource}${item?.id ? `/${item.id}` : ""}`,
        path ? "POST" : item?.id ? "PATCH" : "POST",
        value,
      );
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="editor-dialog finance-dialog"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
      aria-labelledby="resource-title"
    >
      <form onSubmit={submit}>
        <div className="dialog-heading">
          <h2 id="resource-title">{title}</h2>
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
              {f.options ? (
                <select
                  name={f.name}
                  defaultValue={item?.[f.name] || ""}
                  required={!f.optional}
                >
                  <option value="">
                    {f.optional ? "Sans analytique" : "Choisir…"}
                  </option>
                  {f.options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : f.type === "checkbox" ? (
                <input
                  name={f.name}
                  type="checkbox"
                  defaultChecked={item?.[f.name] ?? f.name === "active"}
                />
              ) : f.type === "textarea" ? (
                <textarea
                  name={f.name}
                  maxLength={f.name === "variance_note" ? 2000 : 1000}
                  defaultValue={item?.[f.name]}
                />
              ) : (
                <input
                  name={f.name}
                  type={f.type || "text"}
                  step={
                    f.type === "number"
                      ? f.name === "code_length"
                        ? "1"
                        : "0.01"
                      : undefined
                  }
                  min={f.type === "number" ? "0" : undefined}
                  maxLength={f.name === "code" ? 20 : 150}
                  required={!f.optional}
                  defaultValue={item?.[f.name]}
                />
              )}
            </label>
          ))}
          {resource === "templates" && (
            <div className="entry-lines">
              {lines.map((line, i) => (
                <fieldset key={i}>
                  <legend>Ligne {i + 1}</legend>
                  <label>
                    Compte
                    <select
                      required
                      value={line.code}
                      onChange={(e) =>
                        setLines(
                          lines.map((l, j) =>
                            j === i ? { ...l, code: e.target.value } : l,
                          ),
                        )
                      }
                    >
                      <option value="">Choisir…</option>
                      {accounts
                        .filter((a) => a.active)
                        .map((a) => (
                          <option key={a.id} value={a.code}>
                            {a.code} — {a.name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <div className="form-row">
                    {["debit", "credit"].map((side) => (
                      <label key={side}>
                        {side === "debit" ? "Débit" : "Crédit"}
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
                      Retirer
                    </button>
                  )}
                </fieldset>
              ))}
              <button
                type="button"
                className="button secondary"
                onClick={() =>
                  setLines([...lines, { code: "", debit: "", credit: "" }])
                }
              >
                Ajouter une ligne
              </button>
            </div>
          )}
          {resource === "reverse" && (
            <p className="muted">
              L’original sera conservé. Une écriture inverse équilibrée sera
              créée dans le même exercice ouvert. Les opérations métier
              nécessitent leur propre correction.
            </p>
          )}
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
            {busy ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </form>
    </dialog>
  );
}

export function AccountingReports({ section }: { section?: string }) {
  const [years, setYears] = useState<Row[]>([]);
  const [centers, setCenters] = useState<Row[]>([]);
  const [journals, setJournals] = useState<Row[]>([]);
  const [owners, setOwners] = useState<Row[]>([]);
  const [suppliers, setSuppliers] = useState<Row[]>([]);
  const [filters, setFilters] = useState<Row>({
    year: "",
    start: "",
    end: "",
    prefix: "",
    center: "",
    journal: "",
    owner: "",
    supplier: "",
    nonzero: false,
  });
  const [localKind, setKind] = useState("balance");
  const kind = section || localKind;
  const [result, setResult] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    Promise.all([
      api<{ items: Row[] }>("finance/years"),
      api<{ items: Row[] }>("finance/manage/centers"),
      api<{ items: Row[] }>("finance/manage/journals"),
      api<{ items: Row[] }>("owners"),
      api<{ items: Row[] }>("finance/manage/organization"),
      api<Row>("operations/options"),
    ])
      .then(([y, c, j, o, s, choices]) => {
        setYears(y.items);
        setCenters(c.items);
        setJournals(j.items);
        setOwners(o.items);
        setSuppliers(choices.suppliers);
        setFilters((f) => ({
          ...f,
          year: String(y.items[0]?.id || ""),
          prefix: s.items[0]?.report_prefix || "",
        }));
      })
      .catch((e) => setError(e.message));
  }, []);
  const query = new URLSearchParams(
    Object.fromEntries(
      Object.entries(filters)
        .filter(
          ([k, v]) =>
            (k !== "owner" || kind !== "supplier-auxiliary") &&
            (k !== "supplier" ||
              ["supplier-auxiliary", "balance", "ledger", "journal"].includes(
                kind,
              )) &&
            (k === "prefix" || (v !== "" && v !== false)),
        )
        .map(([k, v]) => [k, v === true ? "1" : String(v)]),
    ),
  ).toString();
  const activeRequest = useRef(0);
  useEffect(() => {
    activeRequest.current += 1;
    setResult(null);
    setBusy(false);
    setError("");
  }, [query, kind]);
  async function generate() {
    const request = ++activeRequest.current;
    setBusy(true);
    try {
      const data = await api<Row>(`finance/reporting/${kind}?${query}`);
      if (request !== activeRequest.current) return;
      setResult(data);
      setError("");
    } catch (e) {
      if (request !== activeRequest.current) return;
      setError((e as Error).message);
      setResult(null);
    } finally {
      if (request === activeRequest.current) setBusy(false);
    }
  }
  const reports = {
    balance: "Balance générale",
    auxiliary: "Comptes copropriétaires",
    "supplier-auxiliary": "Comptes fournisseurs",
    ledger: "Grand livre",
    journal: "Journal comptable",
    income: "Compte de résultat",
    sheet: "Bilan",
    budget: "Budget / réalisé",
  };
  const labels: Row = {
    code: "Compte",
    name: "Libellé du compte",
    date: "Date",
    number: "N°",
    journal: "Journal",
    label: "Libellé",
    reference: "Référence",
    owner: kind === "auxiliary" ? "Copropriétaire" : "Tiers",
    supplier: "Fournisseur",
    opening: ["auxiliary", "supplier-auxiliary"].includes(kind)
      ? "Solde au début de période"
      : "Solde avant mouvement",
    debit: "Débit",
    credit: "Crédit",
    balance: "Solde",
    section: "Rubrique",
    actual: "Réalisé",
    budget: "Budget annuel",
    variance: "Écart",
    previous_actual: "Réalisé précédent (année entière)",
    previous_budget: "Budget précédent",
    variance_note: "Explication de l’écart",
    amount: "Montant",
    charges: "Charges",
    products: "Produits",
    result: "Résultat",
    assets: "Actif",
    liabilities: "Passif",
    difference: "Écart actif / passif",
  };
  const money = [
    "opening",
    "debit",
    "credit",
    "balance",
    "actual",
    "budget",
    "variance",
    "previous_actual",
    "previous_budget",
    "amount",
  ];
  const columns = result?.rows?.length ? Object.keys(result.rows[0]) : [];
  return (
    <section className="finance">
      {!section && (
        <div className="finance-tabs">
          {Object.entries(reports).map(([key, label]) => (
            <button
              key={key}
              className={`button ${kind === key ? "primary" : "secondary"}`}
              onClick={() => {
                setKind(key);
                setResult(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      {years.length ? (
        <>
          <form
            className="report-filters"
            onSubmit={(e) => {
              e.preventDefault();
              void generate();
            }}
          >
            <label>
              Exercice
              <select
                required
                value={filters.year}
                onChange={(e) => {
                  setFilters({
                    ...filters,
                    year: e.target.value,
                    start: "",
                    end: "",
                  });
                  setResult(null);
                }}
              >
                {years.map((y) => (
                  <option key={y.id} value={y.id}>
                    {y.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Début
              <input
                type="date"
                disabled={kind === "sheet"}
                value={filters.start}
                onChange={(e) =>
                  setFilters({ ...filters, start: e.target.value })
                }
              />
            </label>
            <label>
              Fin
              <input
                type="date"
                value={filters.end}
                onChange={(e) =>
                  setFilters({ ...filters, end: e.target.value })
                }
              />
            </label>
            <label>
              Préfixe du compte
              <input
                value={filters.prefix}
                inputMode="numeric"
                onChange={(e) =>
                  setFilters({ ...filters, prefix: e.target.value })
                }
              />
            </label>
            <label>
              Analytique
              <select
                value={filters.center}
                onChange={(e) =>
                  setFilters({ ...filters, center: e.target.value })
                }
              >
                <option value="">Toutes</option>
                {centers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Journal
              <select
                value={filters.journal}
                onChange={(e) =>
                  setFilters({ ...filters, journal: e.target.value })
                }
              >
                <option value="">Tous</option>
                {journals.map((j) => (
                  <option key={j.id} value={j.code}>
                    {j.name}
                  </option>
                ))}
              </select>
            </label>
            {["balance", "ledger", "journal", "auxiliary"].includes(kind) && (
              <label>
                Copropriétaire
                <select
                  value={filters.owner}
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      owner: e.target.value,
                      supplier: "",
                    })
                  }
                >
                  <option value="">Tous les tiers</option>
                  {owners.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.first_name} {o.last_name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {["balance", "ledger", "journal", "supplier-auxiliary"].includes(
              kind,
            ) && (
              <label>
                Fournisseur
                <select
                  value={filters.supplier}
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      supplier: e.target.value,
                      owner: "",
                    })
                  }
                >
                  <option value="">Tous les fournisseurs</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                      {s.archived ? " (archivé)" : ""}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {["balance", "auxiliary", "supplier-auxiliary"].includes(kind) && (
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={filters.nonzero}
                  onChange={(e) =>
                    setFilters({ ...filters, nonzero: e.target.checked })
                  }
                />
                Comptes non soldés uniquement
              </label>
            )}
            <button className="button primary" disabled={busy}>
              {busy ? "Calcul…" : "Calculer le rapport"}
            </button>
            <a
              className="button secondary"
              href={`/api/finance/reporting/${kind}/?${query}&format=csv`}
            >
              Exporter CSV
            </a>
          </form>
          {result && (
            <>
              {["budget", "income"].includes(kind) && (
                <p className="report-note">
                  {result.previous_year
                    ? `Comparatif : ${result.previous_year}, exercice entier. Le réalisé courant suit les dates sélectionnées ; les budgets restent annuels.`
                    : "Aucun exercice précédent enregistré ; les comparatifs sont laissés vides."}{" "}
                  Les explications sont renseignées dans Gestion comptable →
                  Budgets.
                </p>
              )}
              {kind === "supplier-auxiliary" && (
                <p className="report-note">
                  Un solde positif représente une dette envers le fournisseur.
                  Les factures et règlements sans fournisseur identifié sont
                  regroupés séparément. Le rapport porte sur l’exercice
                  sélectionné, sans reports automatiques ni lettrage.
                </p>
              )}
              {kind === "auxiliary" && (
                <p className="report-note">
                  Un solde positif indique un montant dû à la copropriété ; un
                  solde négatif indique une avance. Ces montants portent sur
                  l’exercice sélectionné, sans reprise automatique des exercices
                  précédents.
                </p>
              )}
              <section className="panel report-output">
                <div className="panel-heading">
                  <div>
                    <h2>{(reports as Row)[kind]}</h2>
                    <p>
                      {result.year} · {result.start} au {result.end}
                    </p>
                  </div>
                  <button
                    className="button secondary"
                    onClick={() => window.print()}
                  >
                    Imprimer / PDF
                  </button>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        {columns.map((c) => (
                          <th key={c}>{labels[c] || c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row: Row, i: number) => (
                        <tr key={i}>
                          {columns.map((c) => (
                            <td key={c}>
                              {money.includes(c)
                                ? row[c] == null
                                  ? "—"
                                  : euro(row[c])
                                : String(row[c] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!result.rows.length && (
                  <Empty
                    title="Aucun mouvement sur cette sélection"
                    description="Vérifiez l’exercice, la période et les filtres."
                  />
                )}
                <div className="report-totals">
                  {Object.entries(result.totals).map(([key, value]) => (
                    <div key={key}>
                      <span>{labels[key] || key}</span>
                      <strong>{euro(value)}</strong>
                    </div>
                  ))}
                </div>
                <p className="report-note">
                  Rapport calculé à partir des écritures enregistrées. Les
                  annexes réglementaires et la reprise des soldes de l’ancien
                  syndic sont des traitements distincts.
                </p>
              </section>
            </>
          )}
        </>
      ) : (
        <Empty
          title="Créez d’abord un exercice"
          description="Les rapports seront calculés à partir de la gestion comptable et de ses écritures."
        />
      )}
    </section>
  );
}
