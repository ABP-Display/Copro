import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type FormEvent,
} from "react";
import { Icon } from "./ui";
type Data = Record<string, any>;
type Mutation = (
  path: string,
  body: Data,
  method?: string,
) => Promise<Data | null>;
export const caseStatuses: Data = {
  open: "En cours",
  done: "Terminé",
  archived: "Archivé",
};
export const reminderStatuses: Data = {
  draft: "À relire",
  approved: "Validé",
  sent: "Envoi déclaré",
  cancelled: "Annulé",
};
const kinds: Data = {
  works: "Travaux",
  incident: "Sinistre",
  obligation: "Échéance",
};
const euro = (v: string) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(
    Number(v),
  );
const day = (v: string | null) =>
  v
    ? new Date(`${v}T12:00:00`).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "À préciser";
function DocumentLink({ id, options }: { id: number; options: Data }) {
  return (
    <a className="ops-document" href={`/api/documents/items/${id}/download/`}>
      <Icon name="file" size={15} />
      {options.documents.find((d: Data) => d.id === id)?.title ||
        `Document #${id}`}
    </a>
  );
}

export function CaseCard({
  item: c,
  options,
  busy,
  onEdit,
  onQuote,
  mutate,
}: {
  item: Data;
  options: Data;
  busy: boolean;
  onEdit: () => void;
  onQuote: () => void;
  mutate: Mutation;
}) {
  const resolution = options.resolutions.find(
    (r: Data) => r.id === c.resolution,
  );
  return (
    <article className="ops-card">
      <header className="ops-card-heading">
        <span className="ops-icon">
          <Icon
            name={c.kind === "obligation" ? "calendar" : "building"}
            size={22}
          />
        </span>
        <div>
          <p className="ops-kicker">{kinds[c.kind]}</p>
          <h2>{c.title}</h2>
        </div>
        <span className={`ops-badge ${c.status}`}>
          {caseStatuses[c.status]}
        </span>
      </header>
      <div className="ops-card-body">
        {c.description && <p className="ops-description">{c.description}</p>}
        <dl className="ops-facts">
          <div>
            <dt>Date à suivre</dt>
            <dd>{day(c.due_date)}</dd>
          </div>
          {c.kind !== "obligation" && (
            <div>
              <dt>Budget indicatif</dt>
              <dd>{euro(c.budget)}</dd>
            </div>
          )}
          <div>
            <dt>Décision d’AG</dt>
            <dd>
              {c.resolution
                ? resolution?.title || `Résolution #${c.resolution}`
                : "Aucune résolution liée"}
            </dd>
          </div>
        </dl>
        {(c.documents.length > 0 || c.source_url) && (
          <div className="ops-documents">
            {c.documents.map((id: number) => (
              <DocumentLink key={id} id={id} options={options} />
            ))}
            {c.source_url && (
              <a
                className="ops-document"
                href={c.source_url}
                target="_blank"
                rel="noreferrer"
              >
                <Icon name="info" size={15} />
                Consulter la source
              </a>
            )}
          </div>
        )}
        {c.kind !== "obligation" && (
          <section className="ops-quotes">
            <div className="ops-subheading">
              <h3>
                Les devis du dossier <span>{c.quotes.length}</span>
              </h3>
              {c.status === "open" && (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={onQuote}
                >
                  <Icon name="plus" size={15} />
                  Ajouter un devis
                </button>
              )}
            </div>
            {!c.quotes.length ? (
              <p className="ops-muted">
                Ajoutez vos devis pour comparer les montants et conserver votre
                choix.
              </p>
            ) : (
              <div className="ops-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Fournisseur et notes</th>
                      <th>Montant</th>
                      <th>Écart au budget</th>
                      <th>Décision</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.quotes.map((q: Data) => (
                      <tr
                        key={q.id}
                        className={q.selected ? "ops-selected-quote" : ""}
                      >
                        <td>
                          <strong>{q.supplier}</strong>
                          {q.notes && (
                            <p className="ops-quote-notes">{q.notes}</p>
                          )}
                          {q.document && (
                            <DocumentLink id={q.document} options={options} />
                          )}
                        </td>
                        <td className="ops-money">{euro(q.amount)}</td>
                        <td className="ops-money">
                          {Number(c.budget) > 0
                            ? euro(String(Number(q.amount) - Number(c.budget)))
                            : "Budget non renseigné"}
                        </td>
                        <td>
                          {q.selected ? (
                            <div className="ops-quote-choice">
                              <span className="ops-badge done">
                                <Icon name="check" size={13} />
                                Retenu
                              </span>
                              <button
                                className="ops-text-button"
                                disabled={busy || c.status !== "open"}
                                onClick={() =>
                                  void mutate(
                                    `operations/quotes/${q.id}/select`,
                                    { selected: false },
                                  )
                                }
                              >
                                Annuler le choix
                              </button>
                            </div>
                          ) : (
                            <button
                              className="button secondary"
                              disabled={
                                busy ||
                                c.status !== "open" ||
                                c.quotes.some((x: Data) => x.selected)
                              }
                              onClick={() =>
                                void mutate(
                                  `operations/quotes/${q.id}/select`,
                                  {},
                                )
                              }
                            >
                              Retenir ce devis
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
      <footer className="ops-card-footer">
        <p>
          {c.kind === "obligation"
            ? "Date et applicabilité à vérifier avec votre source."
            : "Le choix d’un devis ne passe pas commande."}
        </p>
        <button className="button secondary" disabled={busy} onClick={onEdit}>
          Modifier le dossier
        </button>
      </footer>
    </article>
  );
}

export function ReminderCard({
  item: r,
  text,
  onText,
  busy,
  mutate,
}: {
  item: Data;
  text: string;
  onText: (text: string) => void;
  busy: boolean;
  mutate: Mutation;
}) {
  const dirty = text !== r.text;
  return (
    <article className="ops-card ops-reminder">
      <header className="ops-card-heading">
        <span className="ops-icon">
          <Icon name="file" size={22} />
        </span>
        <div>
          <p className="ops-kicker">Courrier de suivi</p>
          <h2>{r.name}</h2>
        </div>
        <span className={`ops-badge ${r.status}`}>
          {reminderStatuses[r.status]}
        </span>
      </header>
      <div className="ops-card-body">
        <div className="ops-reminder-summary">
          <div>
            <span>Solde à vérifier</span>
            <strong>{euro(r.balance)}</strong>
          </div>
          <p>
            Calcul au {day(r.evidence.date)}. Contrôlez les échéances et les
            paiements avant de valider.
          </p>
        </div>
        <label className="ops-field">
          Texte du courrier
          <textarea
            rows={9}
            maxLength={10000}
            value={text}
            readOnly={r.status !== "draft" || busy}
            onChange={(e) => onText(e.target.value)}
          />
        </label>
        {dirty && (
          <p className="ops-edit-note">
            Modifications à enregistrer avant validation.
          </p>
        )}
        <details className="ops-evidence">
          <summary>
            <Icon name="book" size={17} />
            Vérifier les mouvements utilisés <Icon name="chevron" size={16} />
          </summary>
          <div>
            <p className="ops-muted">{r.evidence.note}</p>
            <div className="ops-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Écriture</th>
                    <th>Libellé</th>
                    <th>Débit</th>
                    <th>Crédit</th>
                  </tr>
                </thead>
                <tbody>
                  {(r.evidence.rows || []).map((row: Data) => (
                    <tr key={row.id}>
                      <td>{day(row.date)}</td>
                      <td>{row.number}</td>
                      <td>{row.label}</td>
                      <td className="ops-money">{euro(row.debit)}</td>
                      <td className="ops-money">{euro(row.credit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </details>
        {r.validated_at && (
          <p className="ops-muted">
            Validation conservée le{" "}
            {new Date(r.validated_at).toLocaleString("fr-FR")}.
          </p>
        )}
      </div>
      <footer className="ops-card-footer">
        <div className="ops-actions">
          {r.status === "draft" && (
            <>
              <button
                className="button secondary"
                disabled={busy || !dirty}
                onClick={() =>
                  void mutate(`operations/reminders/${r.id}`, { text }, "PATCH")
                }
              >
                Enregistrer le texte
              </button>
              <button
                className="button primary"
                disabled={busy || dirty}
                onClick={() =>
                  void mutate(
                    `operations/reminders/${r.id}`,
                    { status: "approved" },
                    "PATCH",
                  )
                }
              >
                <Icon name="check" size={16} />
                Valider après vérification
              </button>
            </>
          )}
          {r.status === "approved" && (
            <>
              {r.email ? (
                <a
                  className="button primary"
                  href={`mailto:${encodeURIComponent(r.email)}?subject=${encodeURIComponent("Point sur votre compte copropriétaire")}&body=${encodeURIComponent(r.text)}`}
                >
                  Préparer le courriel
                </a>
              ) : (
                <span className="ops-muted">
                  Renseignez le courriel dans l’annuaire pour préparer le
                  message.
                </span>
              )}
              <button
                className="button secondary"
                disabled={busy}
                onClick={() =>
                  void mutate(
                    `operations/reminders/${r.id}`,
                    { status: "sent" },
                    "PATCH",
                  )
                }
              >
                Déclarer l’envoi effectué
              </button>
              <button
                className="button secondary"
                onClick={() => window.print()}
              >
                Imprimer / PDF
              </button>
            </>
          )}
          {["draft", "approved"].includes(r.status) && (
            <button
              className="ops-text-button"
              disabled={busy}
              onClick={() =>
                void mutate(
                  `operations/reminders/${r.id}`,
                  { status: "cancelled" },
                  "PATCH",
                )
              }
            >
              Annuler le brouillon
            </button>
          )}
        </div>
      </footer>
    </article>
  );
}

export function OperationsDialog({
  title,
  children,
  busy,
  onClose,
}: {
  title: string;
  children: ReactNode;
  busy: boolean;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    return () => {
      ref.current?.close();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="ops-dialog"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      aria-labelledby="ops-dialog-title"
    >
      <header className="ops-dialog-heading">
        <div>
          <p className="ops-kicker">Votre copropriété</p>
          <h2 id="ops-dialog-title">{title}</h2>
        </div>
        <button
          className="icon-button"
          type="button"
          disabled={busy}
          aria-label="Fermer le formulaire"
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </header>
      {children}
    </dialog>
  );
}

export function CaseEditor({
  editor,
  section,
  options,
  busy,
  error,
  onClose,
  onSave,
}: {
  editor: Data;
  section: string;
  options: Data;
  busy: boolean;
  error: string;
  onClose: () => void;
  onSave: Mutation;
}) {
  const [supplierRecord, setSupplierRecord] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const data: Data = Object.fromEntries(fd.entries());
    if (editor.type === "case") data.documents = fd.getAll("documents");
    const path =
      editor.type === "quote"
        ? `operations/cases/${editor.case}/quotes`
        : editor.item
          ? `operations/cases/${editor.item.id}`
          : "operations/cases";
    if (await onSave(path, data, editor.item ? "PATCH" : "POST")) onClose();
  }
  const item = editor.item || {};
  return (
    <OperationsDialog
      title={
        editor.type === "quote"
          ? "Ajouter un devis"
          : editor.item
            ? "Modifier le dossier"
            : section === "deadlines"
              ? "Ajouter une échéance"
              : "Créer un dossier"
      }
      busy={busy}
      onClose={onClose}
    >
      <form onSubmit={submit} className="ops-form">
        <div className="ops-dialog-body">
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <p className="ops-form-help">
            {editor.type === "quote"
              ? "Renseignez le montant et la pièce du devis pour le comparer aux autres offres."
              : "Commencez par un titre et une date. Vous pourrez compléter les pièces et la décision liée ensuite."}
          </p>
          <fieldset disabled={busy} className="ops-fields">
            {editor.type === "case" ? (
              <>
                <label className="ops-field">
                  Type de dossier
                  <select
                    name="kind"
                    defaultValue={
                      item.kind ||
                      (section === "deadlines" ? "obligation" : "works")
                    }
                  >
                    <option value="works">Travaux</option>
                    <option value="incident">Sinistre</option>
                    <option value="obligation">Échéance / obligation</option>
                  </select>
                </label>
                <label className="ops-field">
                  Statut
                  <select name="status" defaultValue={item.status || "open"}>
                    <option value="open">En cours</option>
                    <option value="done">Terminé</option>
                    <option value="archived">Archivé</option>
                  </select>
                </label>
                <label className="ops-field ops-full">
                  Titre{" "}
                  <input
                    autoFocus
                    name="title"
                    required
                    maxLength={150}
                    placeholder="Ex. Réfection de la toiture"
                    defaultValue={item.title || ""}
                  />
                </label>
                <label className="ops-field ops-full">
                  Description
                  <textarea
                    name="description"
                    rows={4}
                    maxLength={5000}
                    defaultValue={item.description || ""}
                    placeholder="Les informations utiles pour comprendre et suivre ce dossier."
                  />
                </label>
                <label className="ops-field">
                  Date à suivre
                  <input
                    name="due_date"
                    type="date"
                    defaultValue={item.due_date || ""}
                  />
                </label>
                <label className="ops-field">
                  Budget indicatif (€)
                  <input
                    name="budget"
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    defaultValue={item.budget || "0"}
                  />
                </label>
                <label className="ops-field ops-full">
                  Source ou référence (HTTPS)
                  <input
                    name="source_url"
                    type="url"
                    maxLength={500}
                    placeholder="https://…"
                    defaultValue={item.source_url || ""}
                  />
                </label>
                <label className="ops-field ops-full">
                  Décision d’AG liée
                  <select
                    name="resolution"
                    defaultValue={item.resolution || ""}
                  >
                    <option value="">Aucune résolution liée</option>
                    {item.resolution &&
                      !options.resolutions.some(
                        (r: Data) => r.id === item.resolution,
                      ) && (
                        <option value={item.resolution}>
                          Résolution liée #{item.resolution}
                        </option>
                      )}
                    {options.resolutions.map((r: Data) => (
                      <option key={r.id} value={r.id}>
                        {r.title}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="ops-full ops-doc-picker">
                  <h3>Documents liés</h3>
                  {options.documents.length ? (
                    <div>
                      {options.documents.map((d: Data) => (
                        <label key={d.id}>
                          <input
                            type="checkbox"
                            name="documents"
                            value={d.id}
                            defaultChecked={(item.documents || []).includes(
                              d.id,
                            )}
                          />
                          <Icon name="file" size={16} />
                          <span>{d.title}</span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <p className="ops-muted">
                      Aucun document disponible. Vous pouvez déposer les pièces
                      dans la bibliothèque et les lier plus tard.
                    </p>
                  )}
                  {(item.documents || [])
                    .filter(
                      (id: number) =>
                        !options.documents.some((d: Data) => d.id === id),
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
            ) : (
              <>
                <label className="ops-field ops-full">
                  Fournisseur de l’annuaire
                  <select
                    name="supplier_record"
                    value={supplierRecord}
                    onChange={(e) => setSupplierRecord(e.target.value)}
                  >
                    <option value="">Saisir un nom libre…</option>
                    {(options.suppliers || [])
                      .filter((s: Data) => !s.archived)
                      .map((s: Data) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                  </select>
                </label>
                {!supplierRecord && (
                  <label className="ops-field">
                    Nom du fournisseur
                    <input
                      autoFocus
                      name="supplier"
                      required
                      maxLength={150}
                      placeholder="Nom de l’entreprise"
                    />
                  </label>
                )}
                <label className="ops-field">
                  Montant (€)
                  <input
                    name="amount"
                    required
                    type="number"
                    min="0.01"
                    step="0.01"
                  />
                </label>
                <label className="ops-field ops-full">
                  Notes
                  <textarea
                    name="notes"
                    rows={4}
                    maxLength={2000}
                    placeholder="Prestations, délais, points à comparer…"
                  />
                </label>
                <label className="ops-field ops-full">
                  Pièce justificative
                  <select name="document">
                    <option value="">Aucun document lié</option>
                    {options.documents.map((d: Data) => (
                      <option key={d.id} value={d.id}>
                        {d.title}
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
            className="button secondary"
            type="button"
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
