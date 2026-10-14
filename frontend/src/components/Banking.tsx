import { useEffect, useState, type FormEvent } from "react";
import { api, newOperationId as requestId } from "../api";
import { Icon } from "./ui";
import { OperationsDialog } from "./OperationsViews";
import "./operations.css";

type Bank = {
  id: number;
  name: string;
  bank_name: string;
  iban: string;
  kind: string;
  active: boolean;
  is_default: boolean;
  account_code: string;
  account_active: boolean;
  balance: string;
};
type Year = { id: number; name: string; closed: boolean };
type Transfer = {
  id: number;
  date: string;
  source_name: string;
  destination_name: string;
  reference: string;
  amount: string;
  number: number;
};
type Unassigned = {
  code: string;
  name: string;
  active: boolean;
  balance: string;
};
type Data = {
  items: Bank[];
  unassigned: Unassigned[];
  date: string;
  note: string;
};
type Editor =
  | { type: "bank"; item?: Bank; code?: string }
  | { type: "transfer" };
const kinds: Record<string, string> = {
  current: "Compte courant",
  savings: "Épargne",
  works: "Fonds travaux",
};
const money = (v: string) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(
    Number(v),
  );
const today = () =>
  new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Paris" });

export function Banking() {
  const [data, setData] = useState<Data | null>(null);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [years, setYears] = useState<Year[]>([]);
  const [centers, setCenters] = useState<
    { id: number; name: string; active: boolean }[]
  >([]);
  const [analyticRequired, setAnalyticRequired] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [date, setDate] = useState(today);
  const [archives, setArchives] = useState(false);
  const [search, setSearch] = useState("");
  useEffect(() => {
    let active = true;
    setData(null);
    setError("");
    Promise.all([
      api<Data>(`finance/banks?date=${date}`),
      api<{ items: Transfer[] }>("finance/bank-transfers"),
      api<{ items: Year[] }>("finance/years"),
      api<{ items: { id: number; name: string; active: boolean }[] }>(
        "finance/manage/centers",
      ),
      api<{ items: { analytic_required: boolean }[] }>(
        "finance/manage/organization",
      ),
    ])
      .then(([b, t, y, c, o]) => {
        if (active) {
          setData(b);
          setTransfers(t.items);
          setYears(y.items);
          setCenters(c.items);
          setAnalyticRequired(!!o.items[0]?.analytic_required);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [date]);
  async function refresh() {
    const [b, t] = await Promise.all([
      api<Data>(`finance/banks?date=${date}`),
      api<{ items: Transfer[] }>("finance/bank-transfers"),
    ]);
    setData(b);
    setTransfers(t.items);
  }
  async function save(path: string, body: unknown, method = "POST") {
    setBusy(true);
    setError("");
    try {
      await api(path, method, body);
      setEditor(null);
      await refresh();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  const banks = data?.items || [];
  const activeBanks = banks.filter((b) => b.active && b.account_active);
  const visible = banks.filter(
    (b) =>
      (archives || b.active) &&
      `${b.name} ${b.bank_name} ${b.account_code}`
        .toLocaleLowerCase("fr")
        .includes(search.toLocaleLowerCase("fr")),
  );
  function openBank(item?: Bank, code?: string) {
    setError("");
    setEditor({ type: "bank", item, code });
  }
  return (
    <section className="operations-space">
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      <div className="ops-intro">
        <span className="ops-icon">
          <Icon name="wallet" />
        </span>
        <div>
          <h2>Un suivi distinct pour chaque banque</h2>
          <p>
            Associez chaque banque à un compte comptable, puis choisissez-la
            lors des règlements. Les montants proviennent des écritures
            enregistrées ; le rapprochement bancaire reste à effectuer.
          </p>
        </div>
        <button
          className="button primary"
          disabled={busy || !data}
          onClick={() => openBank()}
        >
          <Icon name="plus" size={17} />
          Ajouter un compte
        </button>
      </div>
      <div className="ops-stats">
        <div>
          <span>Comptes en activité</span>
          <strong>{data ? activeBanks.length : "—"}</strong>
        </div>
        <div>
          <span>Comptes à identifier</span>
          <strong>{data ? data.unassigned.length : "—"}</strong>
        </div>
        <div>
          <span>Transferts affichés</span>
          <strong>{data ? transfers.length : "—"}</strong>
        </div>
      </div>
      <div className="ops-toolbar">
        <label className="ops-search">
          <Icon name="search" size={17} />
          <input
            type="search"
            aria-label="Rechercher une banque"
            placeholder="Nom, établissement ou compte…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label className="ops-field ops-filter">
          Solde au
          <input
            type="date"
            required
            value={date}
            onChange={(e) => {
              if (e.target.value) setDate(e.target.value);
            }}
          />
        </label>
        <label className="ops-checkbox">
          <input
            type="checkbox"
            checked={archives}
            onChange={(e) => setArchives(e.target.checked)}
          />
          Afficher les comptes inactifs
        </label>
      </div>
      {data?.unassigned.length ? (
        <section className="ops-card">
          <div className="ops-card-body">
            <h2>Comptes comptables à identifier</h2>
            <p className="ops-muted">
              Ces comptes comptables existent déjà. Associez-les à leur banque
              réelle pour conserver leurs mouvements ; aucune écriture n’est
              déplacée.
            </p>
            <div className="bank-unassigned">
              {data.unassigned.map((a) => (
                <div key={a.code}>
                  <span>
                    <strong>
                      {a.code} · {a.name}
                    </strong>
                    <small>{money(a.balance)}</small>
                  </span>
                  <button
                    className="button secondary"
                    disabled={busy || !a.active}
                    onClick={() => openBank(undefined, a.code)}
                  >
                    Associer une banque
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}
      {!data ? (
        <div className="ops-empty" role="status">
          Chargement des comptes…
        </div>
      ) : !visible.length ? (
        <div className="ops-empty">
          <Icon name="wallet" size={28} />
          <h3>
            {search
              ? "Aucun compte pour cette recherche"
              : "Identifiez votre premier compte bancaire"}
          </h3>
          <p>
            Ajoutez votre compte courant, puis vos autres comptes avec un code
            comptable distinct pour chacun.
          </p>
        </div>
      ) : (
        <div className="ops-list">
          {visible.map((b) => (
            <article className="ops-card" key={b.id}>
              <header className="ops-card-heading">
                <span className="ops-icon">
                  <Icon name="wallet" />
                </span>
                <div>
                  <p className="ops-kicker">{kinds[b.kind]}</p>
                  <h2>{b.name}</h2>
                </div>
                <span
                  className={`ops-badge ${b.active ? "active" : "archived"}`}
                >
                  {b.is_default ? "Par défaut" : b.active ? "Actif" : "Inactif"}
                </span>
              </header>
              <div className="ops-card-body">
                <dl className="ops-facts">
                  <div>
                    <dt>
                      Solde comptable au{" "}
                      {new Date(`${date}T12:00:00`).toLocaleDateString("fr-FR")}
                    </dt>
                    <dd>{money(b.balance)}</dd>
                  </div>
                  <div>
                    <dt>Compte comptable</dt>
                    <dd>
                      {b.account_code}
                      {!b.account_active && " (inactif)"}
                    </dd>
                  </div>
                  <div>
                    <dt>Établissement</dt>
                    <dd>{b.bank_name || "À préciser"}</dd>
                  </div>
                  <div className="ops-full">
                    <dt>IBAN déclaré</dt>
                    <dd>{b.iban || "Non renseigné"}</dd>
                  </div>
                </dl>
                <p className="ops-muted">
                  Les coordonnées sont privées et restent à vérifier avec votre
                  banque. La catégorie « Fonds travaux » classe ce compte ; elle
                  ne calcule pas les cotisations.
                </p>
              </div>
              <footer className="ops-card-footer">
                <div className="ops-actions">
                  <button
                    className="button secondary"
                    disabled={busy}
                    onClick={() => openBank(b)}
                  >
                    Modifier
                  </button>
                  {!b.is_default && b.active && b.account_active && (
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() =>
                        void save(`finance/banks/${b.id}/default`, {})
                      }
                    >
                      Utiliser par défaut
                    </button>
                  )}
                </div>
              </footer>
            </article>
          ))}
        </div>
      )}
      <section className="ops-card">
        <header className="ops-card-heading">
          <div>
            <p className="ops-kicker">Transferts entre vos comptes</p>
            <h2>Conserver la trace d’un transfert effectué</h2>
          </div>
          <button
            className="button secondary"
            disabled={
              busy || activeBanks.length < 2 || !years.some((y) => !y.closed)
            }
            onClick={() => {
              setError("");
              setEditor({ type: "transfer" });
            }}
          >
            Enregistrer un transfert
          </button>
        </header>
        <div className="ops-card-body">
          <p className="ops-muted">
            Ce formulaire enregistre un mouvement déjà effectué entre deux
            banques. Aucun ordre n’est transmis à la banque. Les 100 derniers
            transferts sont affichés.
          </p>
          {transfers.length ? (
            <div className="ops-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>De / vers</th>
                    <th>Montant</th>
                    <th>Référence</th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.map((t) => (
                    <tr key={t.id}>
                      <td>
                        {new Date(`${t.date}T12:00:00`).toLocaleDateString(
                          "fr-FR",
                        )}
                      </td>
                      <td>
                        {t.source_name}
                        <br />→ {t.destination_name}
                      </td>
                      <td>{money(t.amount)}</td>
                      <td>
                        {t.reference || "—"}
                        <small>Écriture {t.number}</small>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>Aucun transfert enregistré.</p>
          )}
        </div>
      </section>
      {editor && (
        <BankEditor
          key={
            editor.type === "bank"
              ? editor.item?.id || `new-${editor.code || ""}`
              : "transfer"
          }
          editor={editor}
          banks={activeBanks}
          allBanks={banks}
          years={years}
          centers={centers.filter((c) => c.active)}
          analyticRequired={analyticRequired}
          error={error}
          busy={busy}
          onClose={() => setEditor(null)}
          onSave={save}
        />
      )}
    </section>
  );
}

function BankEditor({
  editor,
  banks,
  allBanks,
  years,
  centers,
  analyticRequired,
  error,
  busy,
  onClose,
  onSave,
}: {
  editor: Editor;
  banks: Bank[];
  allBanks: Bank[];
  years: Year[];
  centers: { id: number; name: string }[];
  analyticRequired: boolean;
  error: string;
  busy: boolean;
  onClose: () => void;
  onSave: (path: string, body: unknown, method?: string) => Promise<boolean>;
}) {
  const [operationId] = useState(requestId);
  const item = editor.type === "bank" ? editor.item : undefined;
  const usedCodes = new Set(allBanks.map((b) => b.account_code));
  let code = "512";
  for (let i = 1; usedCodes.has(code); i++) code = `512${i}`;
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body: Record<string, unknown> = Object.fromEntries(fd.entries());
    if (editor.type === "bank") {
      body.active = fd.has("active");
      await onSave(
        `finance/banks${item ? `/${item.id}` : ""}`,
        body,
        item ? "PATCH" : "POST",
      );
    } else {
      body.request_id = operationId;
      await onSave("finance/bank-transfers", body);
    }
  }
  return (
    <OperationsDialog
      title={
        editor.type === "transfer"
          ? "Enregistrer un transfert effectué"
          : item
            ? "Modifier le compte bancaire"
            : "Ajouter un compte bancaire"
      }
      busy={busy}
      onClose={onClose}
    >
      <form className="ops-form" onSubmit={submit}>
        <div className="ops-dialog-body">
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <p className="ops-form-help">
            {editor.type === "bank"
              ? "Le compte comptable doit commencer par 512. Associer un compte existant conserve ses écritures et son solde. Le premier compte actif sera proposé par défaut."
              : "Vérifiez la date et les comptes du transfert déjà effectué. Une écriture équilibrée sera créée ; aucun virement bancaire n’est déclenché."}
          </p>
          <fieldset className="ops-fields" disabled={busy}>
            {editor.type === "bank" ? (
              <>
                <label className="ops-field ops-full">
                  Nom du compte
                  <input
                    name="name"
                    required
                    maxLength={150}
                    defaultValue={item?.name || ""}
                  />
                </label>
                <label className="ops-field">
                  Établissement bancaire
                  <input
                    name="bank_name"
                    maxLength={150}
                    defaultValue={item?.bank_name || ""}
                  />
                </label>
                <label className="ops-field">
                  Compte comptable (512…)
                  <input
                    name="account_code"
                    required
                    pattern="[0-9]{3,20}"
                    maxLength={20}
                    inputMode="numeric"
                    readOnly={!!item}
                    defaultValue={
                      item?.account_code ||
                      (editor.type === "bank" && editor.code) ||
                      code
                    }
                  />
                </label>
                <label className="ops-field ops-full">
                  IBAN (facultatif)
                  <input
                    name="iban"
                    maxLength={64}
                    defaultValue={item?.iban || ""}
                  />
                </label>
                <label className="ops-field ops-full">
                  Usage
                  <select name="kind" defaultValue={item?.kind || "current"}>
                    {Object.entries(kinds).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="ops-checkbox ops-full">
                  <input
                    type="checkbox"
                    name="active"
                    defaultChecked={item?.active ?? true}
                  />
                  Compte actif
                </label>
                {item?.is_default && (
                  <p className="ops-form-help ops-full">
                    Pour désactiver ce compte, définissez d’abord un autre
                    compte par défaut.
                  </p>
                )}
              </>
            ) : (
              <>
                <label className="ops-field">
                  Exercice ouvert
                  <select name="year" required>
                    {years
                      .filter((y) => !y.closed)
                      .map((y) => (
                        <option key={y.id} value={y.id}>
                          {y.name}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="ops-field">
                  Date effective
                  <input
                    name="date"
                    type="date"
                    required
                    defaultValue={today()}
                  />
                </label>
                <label className="ops-field">
                  Depuis le compte
                  <select name="source" required defaultValue={banks[0]?.id}>
                    {banks.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name} · {b.account_code}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="ops-field">
                  Vers le compte
                  <select
                    name="destination"
                    required
                    defaultValue={banks[1]?.id}
                  >
                    {banks.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name} · {b.account_code}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="ops-field">
                  Montant (€)
                  <input
                    name="amount"
                    type="number"
                    required
                    min="0.01"
                    max="9999999999.99"
                    step="0.01"
                  />
                </label>
                <label className="ops-field">
                  Référence bancaire
                  <input name="reference" maxLength={100} />
                </label>
                <label className="ops-field ops-full">
                  Libellé
                  <input
                    name="label"
                    maxLength={250}
                    defaultValue="Transfert entre comptes bancaires"
                  />
                </label>
                <label className="ops-field ops-full">
                  Comptabilité analytique
                  {analyticRequired ? " (obligatoire)" : ""}
                  <select
                    name="cost_center"
                    required={analyticRequired}
                    defaultValue=""
                  >
                    <option value="">Aucune</option>
                    {centers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            )}
          </fieldset>
        </div>
        <footer className="ops-dialog-footer">
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
        </footer>
      </form>
    </OperationsDialog>
  );
}
