import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import { Icon } from "./ui";
import { OperationsDialog } from "./OperationsViews";
import "./operations.css";

type Data = Record<string, any>;
type Options = { suppliers: Data[]; documents: Data[] };
const names: Record<string, string> = {
  suppliers: "fournisseur",
  contracts: "contrat",
  certificates: "attestation",
  notices: "annonce",
};
const statuses: Record<string, string> = {
  active: "Actif",
  ended: "Terminé",
  archived: "Archivé",
  draft: "Brouillon",
  published: "Publié",
};
const certificateKinds: Record<string, string> = {
  insurance: "Assurance",
  urssaf: "Attestation URSSAF",
  kbis: "Extrait Kbis",
  other: "Autre",
};
const day = (v: string | null) =>
  v ? new Date(`${v}T12:00:00`).toLocaleDateString("fr-FR") : "Non renseignée";
const money = (v: string | null) =>
  v === null
    ? "Non renseigné"
    : new Intl.NumberFormat("fr-FR", {
        style: "currency",
        currency: "EUR",
      }).format(Number(v));
const copy: Record<string, [string, string]> = {
  suppliers: [
    "Vos partenaires, au même endroit",
    "Retrouvez les coordonnées, les métiers et les coûts annuels déclarés des contrats actifs. Les devis peuvent reprendre cet annuaire.",
  ],
  contracts: [
    "Anticiper les fins de contrat",
    "Renseignez les dates, le préavis et les pièces du contrat. Les dates à vérifier apparaissent aussi sur l’accueil ; aucune résiliation ni reconduction n’est effectuée.",
  ],
  certificates: [
    "Les pièces à tenir à jour",
    "Suivez les dates de validité saisies et reliez les pièces de la bibliothèque. Le contenu et l’authenticité des attestations restent à vérifier.",
  ],
  notices: [
    "Une information claire pour les voisins",
    "Préparez un brouillon et publiez-le lorsque le texte est prêt. Les annonces publiées sont visibles par tous les copropriétaires connectés.",
  ],
};

export function PartnerRecords({ section }: { section: string }) {
  const [items, setItems] = useState<Data[]>([]);
  const [options, setOptions] = useState<Options>({
    suppliers: [],
    documents: [],
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState<Data | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [archives, setArchives] = useState(false);
  async function load() {
    const [data, choices] = await Promise.all([
      api<{ items: Data[] }>(`operations/${section}`),
      api<Options>("operations/options"),
    ]);
    setItems(data.items);
    setOptions(choices);
  }
  useEffect(() => {
    let active = true;
    Promise.all([
      api<{ items: Data[] }>(`operations/${section}`),
      api<Options>("operations/options"),
    ])
      .then(([data, choices]) => {
        if (active) {
          setItems(data.items);
          setOptions(choices);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [section]);
  async function mutate(body: Data, item?: Data) {
    setBusy(true);
    setError("");
    try {
      await api(
        `operations/${section}${item ? `/${item.id}` : ""}`,
        item ? "PATCH" : "POST",
        body,
      );
      setEditor(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const itemStatus = (item: Data) =>
    item.status || (item.archived ? "archived" : "active");
  const visible = items.filter(
    (item) =>
      (archives || itemStatus(item) !== "archived") &&
      (!status || itemStatus(item) === status) &&
      `${item.title || item.name} ${item.supplier_name || ""} ${item.trade || ""} ${item.reference || ""}`
        .toLocaleLowerCase("fr")
        .includes(search.toLocaleLowerCase("fr")),
  );
  const today = new Date().toLocaleDateString("sv-SE", {
    timeZone: "Europe/Paris",
  });
  const ongoing = items.filter(
    (item) => !["archived", "ended"].includes(itemStatus(item)),
  );
  const near =
    section === "contracts"
      ? ongoing.filter((i) => i.attention).length
      : section === "certificates"
        ? ongoing.filter((i) => i.valid_until < today).length
        : section === "notices"
          ? items.filter((i) => i.status === "published").length
          : ongoing.reduce((sum, i) => sum + i.active_contracts, 0);
  const countLabel =
    section === "contracts"
      ? "Dates à vérifier"
      : section === "certificates"
        ? "Dates dépassées"
        : section === "notices"
          ? "Publiées"
          : "Contrats actifs";
  const availableStatuses =
    section === "notices"
      ? ["draft", "published", "archived"]
      : section === "contracts"
        ? ["active", "ended", "archived"]
        : ["active", "archived"];
  return (
    <section className="operations-space">
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      <div className="ops-intro">
        <span className="ops-icon">
          <Icon
            name={
              section === "notices"
                ? "file"
                : section === "suppliers"
                  ? "people"
                  : "calendar"
            }
          />
        </span>
        <div>
          <h2>{copy[section][0]}</h2>
          <p>{copy[section][1]}</p>
        </div>
        <button
          className="button primary"
          disabled={loading || busy}
          onClick={() => {
            setError("");
            setEditor({});
          }}
        >
          <Icon name="plus" size={17} />
          Ajouter{" "}
          {section === "certificates" || section === "notices"
            ? "une"
            : "un"}{" "}
          {names[section]}
        </button>
      </div>
      <div className="ops-stats">
        <div>
          <span>Enregistrements</span>
          <strong>{loading ? "—" : items.length}</strong>
        </div>
        <div>
          <span>
            {section === "notices" ? "Brouillons à relire" : "En suivi"}
          </span>
          <strong>
            {loading
              ? "—"
              : section === "notices"
                ? items.filter((i) => i.status === "draft").length
                : ongoing.length}
          </strong>
        </div>
        <div>
          <span>{countLabel}</span>
          <strong>{loading ? "—" : near}</strong>
        </div>
      </div>
      <div className="ops-toolbar">
        <label className="ops-search">
          <Icon name="search" size={18} />
          <input
            type="search"
            aria-label="Rechercher"
            placeholder="Rechercher un nom ou une référence…"
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
            {availableStatuses.map((s) => (
              <option key={s} value={s}>
                {statuses[s]}
              </option>
            ))}
          </select>
        </label>
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
        {section === "contracts" && (
          <a
            className="button secondary"
            href="/api/operations/contracts/?format=csv"
          >
            Exporter CSV
          </a>
        )}
      </div>
      {loading ? (
        <div className="ops-empty" role="status">
          Chargement…
        </div>
      ) : !visible.length ? (
        <div className="ops-empty">
          <span className="ops-empty-icon">
            <Icon name="folder" size={30} />
          </span>
          <h3>
            {search || status
              ? "Aucun résultat pour ces filtres"
              : "Vos informations seront réunies ici"}
          </h3>
          <p>
            {search || status
              ? "Ajustez votre recherche ou le statut."
              : `Ajoutez ${section === "certificates" || section === "notices" ? "une première" : "un premier"} ${names[section]} pour commencer.`}
          </p>
          {error && (
            <button
              className="button secondary"
              onClick={() => {
                setLoading(true);
                void load()
                  .then(() => setError(""))
                  .catch((e) => setError(e.message))
                  .finally(() => setLoading(false));
              }}
            >
              Réessayer
            </button>
          )}
        </div>
      ) : (
        <div className="ops-list">
          {visible.map((item) => (
            <article key={item.id} className="ops-card">
              <header className="ops-card-heading">
                <span className="ops-icon">
                  <Icon name={section === "suppliers" ? "people" : "file"} />
                </span>
                <div>
                  <p className="ops-kicker">
                    {section === "certificates"
                      ? certificateKinds[item.kind]
                      : names[section]}
                  </p>
                  <h2>{item.name || item.title}</h2>
                  {item.supplier_name && (
                    <p className="ops-muted">{item.supplier_name}</p>
                  )}
                </div>
                <span className={`ops-badge ${itemStatus(item)}`}>
                  {statuses[itemStatus(item)]}
                </span>
              </header>
              <div className="ops-card-body">
                {section === "suppliers" ? (
                  <>
                    <dl className="ops-facts">
                      <div>
                        <dt>Activité</dt>
                        <dd>{item.trade || "À préciser"}</dd>
                      </div>
                      <div>
                        <dt>Contact</dt>
                        <dd>{item.contact || "À préciser"}</dd>
                      </div>
                      <div>
                        <dt>SIRET déclaré</dt>
                        <dd>{item.siret || "Non renseigné"}</dd>
                      </div>
                      <div>
                        <dt>Courriel</dt>
                        <dd>
                          {item.email ? (
                            <a
                              href={`mailto:${encodeURIComponent(item.email)}`}
                            >
                              {item.email}
                            </a>
                          ) : (
                            "Non renseigné"
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>Téléphone</dt>
                        <dd>{item.phone || "Non renseigné"}</dd>
                      </div>
                      <div>
                        <dt>Coûts annuels des contrats actifs</dt>
                        <dd>
                          {money(item.annual_cost)}
                          {item.unknown_costs > 0 && (
                            <small className="ops-muted">
                              {" "}
                              + {item.unknown_costs} coût(s) à préciser
                            </small>
                          )}
                        </dd>
                      </div>
                    </dl>
                    {item.address && (
                      <p className="ops-description">{item.address}</p>
                    )}
                  </>
                ) : section === "contracts" ? (
                  <>
                    <dl className="ops-facts">
                      <div>
                        <dt>Début / fin déclarée</dt>
                        <dd>
                          {day(item.starts_on)} / {day(item.ends_on)}
                        </dd>
                      </div>
                      <div>
                        <dt>Date limite de préavis</dt>
                        <dd>
                          {day(item.notice_on)}
                          {item.ends_on && (
                            <small className="ops-muted">
                              {" "}
                              ({item.notice_days} jours)
                            </small>
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>Coût annuel indicatif</dt>
                        <dd>{money(item.annual_cost)}</dd>
                      </div>
                      <div>
                        <dt>Reconduction tacite déclarée</dt>
                        <dd>{item.tacit_renewal ? "Oui" : "Non"}</dd>
                      </div>
                      <div>
                        <dt>Référence</dt>
                        <dd>{item.reference || "À préciser"}</dd>
                      </div>
                    </dl>
                    {item.status === "active" && item.attention && (
                      <p className="ops-attention">
                        <Icon name="info" size={16} />
                        {item.attention === "expired"
                          ? "La date de fin est dépassée. Vérifiez la situation réelle du contrat."
                          : "La date de préavis ou de fin approche, ou est déjà dépassée. Vérifiez les clauses avant toute démarche."}
                      </p>
                    )}
                    <div className="ops-documents">
                      {item.documents.map((id: number) => (
                        <DocumentLink key={id} id={id} options={options} />
                      ))}
                    </div>
                  </>
                ) : section === "certificates" ? (
                  <>
                    <dl className="ops-facts">
                      <div>
                        <dt>Validité déclarée jusqu’au</dt>
                        <dd>{day(item.valid_until)}</dd>
                      </div>
                      <div>
                        <dt>Pièce justificative</dt>
                        <dd>
                          {item.document ? (
                            <DocumentLink
                              id={item.document}
                              options={options}
                            />
                          ) : (
                            "Aucune pièce liée"
                          )}
                        </dd>
                      </div>
                    </dl>
                    {!item.archived && item.valid_until < today && (
                      <p className="ops-attention">
                        La date saisie est dépassée. Demandez et vérifiez une
                        pièce à jour.
                      </p>
                    )}
                  </>
                ) : (
                  <>
                    <p className="ops-description">{item.text}</p>
                    {item.published_at && (
                      <p className="ops-muted">
                        Dernière publication :{" "}
                        {new Date(item.published_at).toLocaleString("fr-FR")}
                      </p>
                    )}
                  </>
                )}
                {item.notes && <p className="ops-description">{item.notes}</p>}
              </div>
              <footer className="ops-card-footer">
                <div className="ops-actions">
                  {(section !== "notices" || item.status === "draft") && (
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() => {
                        setError("");
                        setEditor(item);
                      }}
                    >
                      Modifier
                    </button>
                  )}
                  {section === "notices" && item.status === "draft" && (
                    <button
                      className="button primary"
                      disabled={busy}
                      onClick={() => void mutate({ status: "published" }, item)}
                    >
                      Publier aux copropriétaires
                    </button>
                  )}
                  {section === "notices" && item.status === "published" && (
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() => void mutate({ status: "draft" }, item)}
                    >
                      Retirer la publication
                    </button>
                  )}
                  {section === "contracts" && item.status === "active" && (
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() => void mutate({ status: "ended" }, item)}
                    >
                      Déclarer terminé
                    </button>
                  )}
                  {section === "contracts" && item.status === "ended" && (
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() => void mutate({ status: "active" }, item)}
                    >
                      Remettre en suivi
                    </button>
                  )}
                  <button
                    className="ops-text-button"
                    disabled={busy}
                    onClick={() =>
                      void mutate(
                        section === "suppliers" || section === "certificates"
                          ? { archived: !item.archived }
                          : {
                              status:
                                item.status === "archived"
                                  ? section === "notices"
                                    ? "draft"
                                    : "active"
                                  : "archived",
                            },
                        item,
                      )
                    }
                  >
                    {itemStatus(item) === "archived" ? "Restaurer" : "Archiver"}
                  </button>
                </div>
              </footer>
            </article>
          ))}
        </div>
      )}
      {editor && (
        <RecordEditor
          key={editor.id || "new"}
          section={section}
          item={editor}
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

function DocumentLink({ id, options }: { id: number; options: Options }) {
  return (
    <a className="ops-document" href={`/api/documents/items/${id}/download/`}>
      <Icon name="file" size={15} />
      {options.documents.find((d) => d.id === id)?.title || `Document #${id}`}
    </a>
  );
}

function RecordEditor({
  section,
  item,
  options,
  busy,
  error,
  onClose,
  onSave,
}: {
  section: string;
  item: Data;
  options: Options;
  busy: boolean;
  error: string;
  onClose: () => void;
  onSave: (body: Data, item?: Data) => Promise<void>;
}) {
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const data: Data = Object.fromEntries(fd.entries());
    if (section === "contracts") {
      data.documents = fd.getAll("documents");
      data.tacit_renewal = fd.has("tacit_renewal");
    }
    void onSave(data, item.id ? item : undefined);
  }
  function field(
    label: string,
    name: string,
    type = "text",
    required = false,
    maxLength = 150,
  ) {
    return (
      <label
        className={`ops-field ${["title", "name", "email"].includes(name) ? "ops-full" : ""}`}
        key={name}
      >
        {label}
        <input
          name={name}
          type={type}
          required={required}
          maxLength={maxLength}
          defaultValue={item[name] ?? (name === "notice_days" ? 0 : "")}
          {...(type === "number"
            ? {
                min: 0,
                step: name === "notice_days" ? 1 : 0.01,
                max: name === "notice_days" ? 3650 : 9999999999.99,
              }
            : {})}
        />
      </label>
    );
  }
  const supplierPicker = (
    <label className="ops-field ops-full">
      Fournisseur
      <select name="supplier" required defaultValue={item.supplier || ""}>
        <option value="">Choisir dans l’annuaire…</option>
        {options.suppliers
          .filter((s) => !s.archived || s.id === item.supplier)
          .map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
              {s.archived ? " (archivé)" : ""}
            </option>
          ))}
      </select>
      {!options.suppliers.some((s) => !s.archived) && !item.supplier && (
        <small>Ajoutez d’abord un fournisseur dans l’annuaire.</small>
      )}
    </label>
  );
  return (
    <OperationsDialog
      title={`${item.id ? "Modifier" : "Ajouter"} ${section === "notices" || section === "certificates" ? "une" : "un"} ${names[section]}`}
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
            {section === "notices"
              ? "Le texte est enregistré en brouillon. Publiez-le ensuite depuis la liste pour le partager. Évitez les données personnelles ou les comptes individuels."
              : section === "contracts"
                ? "Recopiez les modalités du contrat signé. La date limite affichée sera la date de fin moins le nombre de jours de préavis saisi."
                : "Les informations restent réservées aux gestionnaires. Vous pourrez les compléter ultérieurement."}
          </p>
          <fieldset className="ops-fields" disabled={busy}>
            {section === "suppliers" ? (
              <>
                {field("Nom de l’entreprise", "name", "text", true)}
                {field("Activité / métier", "trade", "text", false, 100)}
                {field(
                  "SIRET (14 chiffres, facultatif)",
                  "siret",
                  "text",
                  false,
                  14,
                )}
                {field("Personne à contacter", "contact")}
                {field("Téléphone", "phone", "tel", false, 30)}
                {field("Courriel", "email", "email", false, 254)}
                <label className="ops-field ops-full">
                  Adresse
                  <textarea
                    name="address"
                    rows={3}
                    maxLength={1000}
                    defaultValue={item.address || ""}
                  />
                </label>
              </>
            ) : section === "contracts" ? (
              <>
                {supplierPicker}
                {field("Nom du contrat", "title", "text", true)}
                {field("Référence", "reference", "text", false, 100)}
                {field("Coût annuel indicatif (€)", "annual_cost", "number")}
                {field("Début", "starts_on", "date", true)}
                {field("Fin (facultative)", "ends_on", "date")}
                {field("Préavis (jours calendaires)", "notice_days", "number")}
                <label className="ops-field">
                  Statut
                  <select name="status" defaultValue={item.status || "active"}>
                    <option value="active">Actif</option>
                    <option value="ended">Terminé</option>
                    <option value="archived">Archivé</option>
                  </select>
                </label>
                <label className="ops-checkbox ops-full">
                  <input
                    type="checkbox"
                    name="tacit_renewal"
                    defaultChecked={item.tacit_renewal || false}
                  />
                  Reconduction tacite indiquée au contrat
                </label>
                <div className="ops-doc-picker ops-full">
                  <h3>Documents liés</h3>
                  <div>
                    {options.documents.map((d) => (
                      <label key={d.id}>
                        <input
                          type="checkbox"
                          name="documents"
                          value={d.id}
                          defaultChecked={(item.documents || []).includes(d.id)}
                        />
                        <Icon name="file" size={16} />
                        {d.title}
                      </label>
                    ))}
                  </div>
                  {!options.documents.length && (
                    <p className="ops-muted">
                      Déposez les pièces dans la bibliothèque pour les lier ici.
                    </p>
                  )}
                  {(item.documents || [])
                    .filter(
                      (id: number) =>
                        !options.documents.some((d) => d.id === id),
                    )
                    .map((id: number) => (
                      <input
                        key={id}
                        type="hidden"
                        name="documents"
                        value={id}
                      />
                    ))}
                </div>
              </>
            ) : section === "certificates" ? (
              <>
                {supplierPicker}
                {field("Titre de l’attestation", "title", "text", true)}
                <label className="ops-field">
                  Type
                  <select name="kind" defaultValue={item.kind || "insurance"}>
                    {Object.entries(certificateKinds).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                {field(
                  "Validité déclarée jusqu’au",
                  "valid_until",
                  "date",
                  true,
                )}
                <label className="ops-field ops-full">
                  Pièce justificative
                  <select name="document" defaultValue={item.document || ""}>
                    <option value="">Aucune pièce liée</option>
                    {item.document &&
                      !options.documents.some(
                        (d) => d.id === item.document,
                      ) && (
                        <option value={item.document}>
                          Document lié #{item.document}
                        </option>
                      )}
                    {options.documents.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.title}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            ) : (
              <>
                {field("Titre de l’annonce", "title", "text", true)}
                <label className="ops-field ops-full">
                  Message
                  <textarea
                    name="text"
                    required
                    rows={8}
                    maxLength={10000}
                    defaultValue={item.text || ""}
                  />
                </label>
              </>
            )}
            {["suppliers", "contracts"].includes(section) && (
              <label className="ops-field ops-full">
                Notes
                <textarea
                  name="notes"
                  rows={4}
                  maxLength={5000}
                  defaultValue={item.notes || ""}
                />
              </label>
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

export function SharedNotices() {
  const [items, setItems] = useState<Data[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<{ items: Data[] }>("operations/notices")
      .then((data) => {
        if (active) setItems(data.items);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <section className="panel ops-surface shared-notices">
      <div className="panel-heading">
        <div>
          <h2>Annonces de la copropriété</h2>
          <p>Les informations publiées par votre gestionnaire.</p>
        </div>
      </div>
      {error ? (
        <p className="alert" role="alert">
          {error}
        </p>
      ) : !items ? (
        <p>Chargement…</p>
      ) : !items.length ? (
        <p className="muted">Aucune annonce publiée pour le moment.</p>
      ) : (
        <div className="ops-list">
          {items.map((item) => (
            <article key={item.id} className="shared-notice">
              <h3>{item.title}</h3>
              <p className="ops-description">{item.text}</p>
              <small>
                Publié le{" "}
                {new Date(item.published_at).toLocaleDateString("fr-FR")}
              </small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
