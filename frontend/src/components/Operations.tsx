import { useEffect, useState } from "react";
import { api } from "../api";
import { Icon } from "./ui";
import {
  CaseCard,
  ReminderCard,
  CaseEditor,
  caseStatuses,
  reminderStatuses,
} from "./OperationsViews";
import "./operations.css";
import { PartnerRecords } from "./PartnerRecords";
type Data = Record<string, any>;
const money = (v: string) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(
    Number(v),
  );

export function HomeInsights({
  onNavigate,
}: {
  onNavigate: (page: string, section: string) => void;
}) {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<Data>("operations/metrics")
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <section className="panel insights-panel ops-surface">
      <div className="panel-heading">
        <div>
          <h2>Les points à suivre</h2>
          <p>
            Échéances à 30 jours et analyses des données saisies. Vous gardez la
            décision.
          </p>
        </div>
        <span className="subtle-badge">Analyse métrique</span>
      </div>
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : !data ? (
        <p>Analyse en cours…</p>
      ) : (
        <>
          {!data.alerts.length ? (
            <p>Aucun point signalé par ces indicateurs.</p>
          ) : (
            <div className="insight-grid">
              {data.alerts.map((a: Data, i: number) => (
                <button
                  key={i}
                  className={`insight-item ${a.level}`}
                  onClick={() => onNavigate(a.page, a.section)}
                >
                  <Icon name={a.level === "warning" ? "info" : "calendar"} />
                  <span>
                    <strong>{a.title}</strong>
                    <small>{a.detail}</small>
                  </span>
                  <Icon name="arrow" size={16} />
                </button>
              ))}
            </div>
          )}
          <p className="operations-note">
            Calcul au {new Date(data.date).toLocaleDateString("fr-FR")}. Un
            solde débiteur ne prouve pas à lui seul un retard de paiement. Aucun
            message n’est envoyé automatiquement.
          </p>
        </>
      )}
    </section>
  );
}

export function PersonalAccount() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<Data>("operations/my-account")
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <section className="panel ops-surface">
      <div className="panel-heading">
        <div>
          <h2>Mon compte copropriétaire</h2>
          <p>Vos mouvements personnels restent privés.</p>
        </div>
        {data && <strong>{money(data.balance)}</strong>}
      </div>
      {error && (
        <p role="alert" className="alert">
          {error}
        </p>
      )}
      {data && (
        <>
          <p>
            {Number(data.balance) > 0
              ? "Solde débiteur à vérifier avec le gestionnaire."
              : Number(data.balance) < 0
                ? "Votre compte présente un crédit."
                : "Votre compte est équilibré."}
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Libellé</th>
                  <th>Débit</th>
                  <th>Crédit</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r: Data, i: number) => (
                  <tr key={i}>
                    <td>{r.date}</td>
                    <td>{r.label}</td>
                    <td>{money(r.debit)}</td>
                    <td>{money(r.credit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="operations-note">{data.note}</p>
        </>
      )}
    </section>
  );
}

export function Operations({ section }: { section: string }) {
  if (["suppliers", "contracts", "certificates", "notices"].includes(section))
    return <PartnerRecords key={section} section={section} />;
  return <CaseOperations section={section} />;
}

function CaseOperations({ section }: { section: string }) {
  const [items, setItems] = useState<Data[]>([]);
  const [reminders, setReminders] = useState<Data[]>([]);
  const [options, setOptions] = useState<Data>({
    owners: [],
    documents: [],
    resolutions: [],
  });
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editor, setEditor] = useState<Data | null>(null);
  const [selectedOwner, setSelectedOwner] = useState("");
  const [archives, setArchives] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setEditor(null);
    setSearch("");
    setStatus("");
  }, [section]);
  async function load() {
    try {
      const [c, r, o] = await Promise.all([
        api<Data>("operations/cases"),
        api<Data>("operations/reminders"),
        api<Data>("operations/options"),
      ]);
      setItems(c.items);
      setReminders(r.items);
      setOptions(o);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function mutate(path: string, body: Data, method = "POST") {
    setBusy(true);
    setError("");
    try {
      const result = await api<Data>(path, method, body);
      await load();
      return result;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  const base = items.filter((c) =>
    section === "deadlines" ? c.kind === "obligation" : c.kind !== "obligation",
  );
  const visible = base.filter(
    (c) =>
      (archives || c.status !== "archived") &&
      (!status || c.status === status) &&
      `${c.title} ${c.description}`
        .toLocaleLowerCase("fr")
        .includes(search.toLocaleLowerCase("fr")),
  );
  const reminderList = reminders.filter(
    (r) =>
      (!status || r.status === status) &&
      r.name.toLocaleLowerCase("fr").includes(search.toLocaleLowerCase("fr")),
  );
  const now = new Date();
  const today = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
  const overdue = base.filter(
    (c) => c.status === "open" && c.due_date && c.due_date < today,
  ).length;
  const isReminder = section === "reminders";
  return (
    <section className="operations-space">
      {error && !editor && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <div className="ops-intro">
        <span className="ops-icon">
          <Icon
            name={
              isReminder
                ? "file"
                : section === "deadlines"
                  ? "calendar"
                  : "building"
            }
            size={24}
          />
        </span>
        <div>
          <h2>
            {isReminder
              ? "Un courrier préparé, une décision qui vous appartient"
              : section === "deadlines"
                ? "Les dates utiles, au bon endroit"
                : "Du premier devis au dossier terminé"}
          </h2>
          <p>
            {isReminder
              ? "Relisez le solde et ses mouvements avant validation. Aucun courrier n’est envoyé automatiquement."
              : section === "deadlines"
                ? "Renseignez les échéances applicables et leur source. Les dates proches apparaîtront sur l’accueil."
                : "Réunissez devis, budget, pièces et décisions d’AG. Retenir une offre ne passe pas commande."}
          </p>
        </div>
        {!isReminder && (
          <button
            className="button primary"
            disabled={loading || busy}
            onClick={() => setEditor({ type: "case" })}
          >
            <Icon name="plus" size={16} />
            {section === "deadlines"
              ? "Ajouter une échéance"
              : "Nouveau dossier"}
          </button>
        )}
      </div>
      <div className="ops-stats" aria-label="Chiffres de suivi">
        {(isReminder
          ? [
              [
                "À relire",
                reminders.filter((r) => r.status === "draft").length,
              ],
              [
                "Validées",
                reminders.filter((r) => r.status === "approved").length,
              ],
              [
                "Envois déclarés",
                reminders.filter((r) => r.status === "sent").length,
              ],
            ]
          : [
              [
                "Dossiers en cours",
                base.filter((c) => c.status === "open").length,
              ],
              ["Dates dépassées", overdue],
              ["Terminés", base.filter((c) => c.status === "done").length],
            ]
        ).map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{loading ? "—" : value}</strong>
          </div>
        ))}
      </div>
      {isReminder && (
        <section className="ops-compose">
          <div>
            <span className="ops-kicker">Préparer un brouillon</span>
            <h2>Choisir le compte à vérifier</h2>
            <p>
              Le courrier reprend les mouvements enregistrés et conserve leurs
              preuves.
            </p>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void mutate("operations/reminders", { owner: selectedOwner });
            }}
          >
            <label className="ops-field">
              Copropriétaire
              <select
                required
                disabled={busy || loading}
                value={selectedOwner}
                onChange={(e) => setSelectedOwner(e.target.value)}
              >
                <option value="">Choisir dans l’annuaire…</option>
                {options.owners.map((o: Data) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="button primary"
              disabled={busy || !selectedOwner || loading}
            >
              <Icon name="plus" size={16} />
              Préparer le brouillon
            </button>
          </form>
        </section>
      )}
      <div className="ops-toolbar">
        <label className="ops-search">
          <Icon name="search" size={18} />
          <input
            type="search"
            aria-label={
              isReminder ? "Rechercher une relance" : "Rechercher un dossier"
            }
            placeholder={
              isReminder
                ? "Rechercher un copropriétaire…"
                : "Rechercher un dossier…"
            }
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label className="ops-field ops-filter">
          Statut
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              if (e.target.value === "archived") setArchives(true);
            }}
          >
            <option value="">Tous les statuts</option>
            {Object.entries(isReminder ? reminderStatuses : caseStatuses).map(
              ([key, label]) => (
                <option key={key} value={key}>
                  {String(label)}
                </option>
              ),
            )}
          </select>
        </label>
        {!isReminder && (
          <label className="ops-checkbox">
            <input
              type="checkbox"
              checked={archives}
              onChange={(e) => {
                setArchives(e.target.checked);
                if (!e.target.checked && status === "archived") setStatus("");
              }}
            />
            Afficher les archives
          </label>
        )}
      </div>
      {loading ? (
        <div className="ops-empty" role="status">
          Chargement de vos dossiers…
        </div>
      ) : !(isReminder ? reminderList : visible).length ? (
        <div className="ops-empty">
          <span className="ops-empty-icon">
            <Icon
              name={
                isReminder
                  ? "file"
                  : section === "deadlines"
                    ? "calendar"
                    : "folder"
              }
              size={30}
            />
          </span>
          <h3>
            {search || status
              ? "Aucun résultat pour ces filtres"
              : isReminder
                ? "Vos courriers seront réunis ici"
                : section === "deadlines"
                  ? "Votre calendrier commence ici"
                  : "Votre premier dossier, en quelques étapes"}
          </h3>
          <p>
            {search || status
              ? "Modifiez la recherche ou le statut pour retrouver vos dossiers."
              : isReminder
                ? "Choisissez un copropriétaire ci-dessus pour préparer un brouillon à relire."
                : "Ajoutez un titre et une date, puis complétez les documents et les décisions à votre rythme."}
          </p>
          {search || status ? (
            <button
              className="button secondary"
              onClick={() => {
                setSearch("");
                setStatus("");
              }}
            >
              Réinitialiser les filtres
            </button>
          ) : (
            !isReminder && (
              <button
                className="button secondary"
                onClick={() => setEditor({ type: "case" })}
              >
                {section === "deadlines"
                  ? "Ajouter une échéance"
                  : "Créer mon premier dossier"}
              </button>
            )
          )}
        </div>
      ) : (
        <div className="ops-list">
          {isReminder
            ? reminderList.map((r) => (
                <ReminderCard
                  key={r.id}
                  item={r}
                  text={drafts[r.id] ?? r.text}
                  onText={(text) => setDrafts({ ...drafts, [r.id]: text })}
                  busy={busy}
                  mutate={mutate}
                />
              ))
            : visible.map((c) => (
                <CaseCard
                  key={c.id}
                  item={c}
                  options={options}
                  busy={busy}
                  onEdit={() => setEditor({ type: "case", item: c })}
                  onQuote={() => setEditor({ type: "quote", case: c.id })}
                  mutate={mutate}
                />
              ))}
        </div>
      )}
      {editor && (
        <CaseEditor
          editor={editor}
          section={section}
          options={options}
          busy={busy}
          error={error}
          onClose={() => setEditor(null)}
          onSave={mutate}
        />
      )}
    </section>
  );
}
