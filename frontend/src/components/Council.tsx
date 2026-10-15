import { useEffect, useState } from "react";
import { api, type User } from "../api";
import { Icon, Empty } from "./ui";
import { CouncilEditor, type CouncilField } from "./CouncilEditor";
import { CouncilRequestForm } from "./CouncilRequestForm";
import { CouncilUpload } from "./CouncilUpload";
import { CouncilMandateForm } from "./CouncilMandateForm";
import { CredentialsDialog, type Credentials } from "./Access";
import { BrandMark } from "./BrandMark";
import { MemberPortal } from "./MemberPortal";
import "./council.css";

type Row = Record<string, any>;
export type CouncilContext = {
  user: User;
  settings: Row;
  roles: { value: string; label: string; capabilities: string[] }[];
  mandates: Row[];
  years: Row[];
  keys: Row[];
  centers: Row[];
  accounts: Row[];
  projects: Row[];
  suppliers: Row[];
  documents: Row[];
  versions: Row[];
  owners?: Row[];
  users?: Row[];
  assembly_mandates?: Row[];
};
const money = (v: any) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(
    Number(v || 0),
  );
const day = (v: string) =>
  v
    ? new Date(v.length === 10 ? v + "T12:00:00" : v).toLocaleDateString(
        "fr-FR",
      )
    : "—";
const today = () => new Date().toLocaleDateString("en-CA");
const stages: Record<string, string> = {
  pending: "En attente",
  approved: "Validé",
  rejected: "Refusé",
  stale: "Dossier modifié",
  withdrawn: "Retiré",
  draft: "Brouillon",
  submitted: "Soumis au conseil",
  posted: "Comptabilisé",
  cancelled: "Annulé",
};
const sections = {
  mandates: "Composition & mandats",
  approvals: "Dépenses à valider",
  accounts: "Consulter les comptes",
  controls: "Contrôle indépendant",
  history: "Historique",
  settings: "Mode & règles",
};
const checks = {
  books: "Écritures et équilibre des comptes examinés",
  invoices: "Factures et justificatifs contrôlés",
  banks: "Banques, relevés et rapprochements examinés",
  allocation: "Répartitions des charges vérifiées",
  budget: "Budget et écarts examinés",
};
const conclusions: Record<string, string> = {
  draft: "En préparation",
  favorable: "Avis favorable",
  reserves: "Avis avec réserves",
  adverse: "Avis défavorable",
};
function fileLink(id: number, label = "Consulter la pièce") {
  return (
    <a className="council-file" href={`/api/council/files/${id}/`}>
      {label}
      <Icon name="arrow" size={13} />
    </a>
  );
}
function download(name: string, content: string) {
  const url = URL.createObjectURL(
    new Blob([content], { type: "text/markdown;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
type Editor = {
  title: string;
  description?: string;
  fields: CouncilField[];
  submitLabel?: string;
  save: (data: Row) => Promise<void>;
};

export function Council({ section = "mandates" }: { section?: string }) {
  const [context, setContext] = useState<CouncilContext | null>(null);
  const [storedItems, setItems] = useState<Row[]>([]);
  const [loadedKey, setLoadedKey] = useState("");
  const [drafts, setDrafts] = useState<Row[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [generation, setGeneration] = useState(0);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [mandateForm, setMandateForm] = useState(false);
  const [requestForm, setRequestForm] = useState(false);
  const [uploadForm, setUploadForm] = useState(false);
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [kind, setKind] = useState("expenses");
  const [year, setYear] = useState("");
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const dataKey = `${section}:${kind}:${year}:${page}`;
  const items = loadedKey === dataKey ? storedItems : [];
  function reload(message = "") {
    setNotice(message);
    setGeneration((v) => v + 1);
  }
  useEffect(() => {
    setPage(1);
  }, [section, kind, year]);
  useEffect(() => {
    setNotice("");
  }, [section]);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError("");
    async function load() {
      try {
        const c = await api<CouncilContext>("council/context");
        if (!live) return;
        setContext(c);
        const selectedYear = year || String(c.years[0]?.id || "");
        if (section === "approvals") {
          const [r, d] = await Promise.all([
            api<Row>(`council/requests?page=${page}`),
            api<Row>("council/drafts"),
          ]);
          if (live) {
            setItems(r.items);
            setCount(r.count);
            setDrafts(d.items);
          }
        } else if (section === "controls") {
          const r = await api<Row>("council/controls");
          if (live) setItems(r.items);
        } else if (["accounts", "history"].includes(section)) {
          if (
            ["ledger", "balance", "budget"].includes(kind) &&
            !selectedYear &&
            section !== "history"
          ) {
            setItems([]);
            setCount(0);
            return;
          }
          const r = await api<Row>(
            `council/records?kind=${section === "history" ? "history" : kind}&page=${page}${selectedYear && section !== "history" ? `&year=${selectedYear}` : ""}`,
          );
          if (live) {
            setItems(r.items || r.rows);
            setCount(r.count);
          }
        } else if (live) {
          setItems([]);
        }
        if (live) setLoadedKey(dataKey);
      } catch (e) {
        if (live) {
          setError((e as Error).message);
          setItems([]);
        }
      } finally {
        if (live) setLoading(false);
      }
    }
    void load();
    return () => {
      live = false;
    };
  }, [section, kind, year, page, generation]);
  const c = context;
  const can = (name: string) => c?.user.capabilities?.includes(name);
  const versionChoices =
    c?.versions.map((v) => ({
      value: v.id,
      label: `${v.title} · ${v.filename} (version ${v.id})`,
    })) || [];
  function reasonAction(
    title: string,
    description: string,
    path: string,
    message: string,
  ) {
    setEditor({
      title,
      description,
      fields: [{ name: "reason", label: "Motif", type: "textarea" }],
      save: async (data) => {
        await api(path, "POST", data);
        reload(message);
      },
    });
  }
  function settingsEditor() {
    if (!c) return;
    setEditor({
      title: "Mode de gestion et contrôle des dépenses",
      description:
        "La règle est un contrôle interne documenté. Elle ne remplace ni une décision d’AG ni une délégation de pouvoirs. Une demande déjà ouverte conserve ses validations requises.",
      fields: [
        {
          name: "mode",
          label: "Mode de gestion",
          choices: [
            { value: "benevole", label: "Syndic bénévole" },
            { value: "cooperative", label: "Syndicat coopératif" },
          ],
          value: c.settings.mode,
        },
        {
          name: "approval_enabled",
          label:
            "Exiger un contrôle avant de retenir un devis ou d’enregistrer un règlement fournisseur",
          type: "checkbox",
          value: c.settings.approval_enabled,
        },
        {
          name: "threshold",
          label: "Montant à partir duquel le contrôle est requis (€)",
          type: "number",
          value: c.settings.threshold,
          help: "0 € : toutes les dépenses. Le montant total de la facture est retenu, même pour un paiement partiel.",
        },
        {
          name: "required_approvals",
          label: "Nombre d’avis favorables distincts (1 à 10)",
          type: "number",
          value: c.settings.required_approvals,
        },
        {
          name: "reference",
          label: "Référence de la règle de contrôle",
          type: "textarea",
          optional: true,
          value: c.settings.reference,
        },
        {
          name: "proof",
          label: "Document définissant la règle",
          choices: versionChoices,
          optional: true,
          value: c.settings.proof,
        },
        {
          name: "reason",
          label: "Motif de cette configuration",
          type: "textarea",
        },
      ],
      save: async (data) => {
        await api("council/settings", "PATCH", data);
        reload("Les règles sont enregistrées et leur modification est tracée.");
      },
    });
  }
  function prepareExpense(draft?: Row) {
    if (!c) return;
    const choices = (rows: Row[], label: string) =>
      rows.map((r) => ({ value: r.id, label: r[label] }));
    setEditor({
      title: draft ? "Corriger la préparation" : "Préparer une dépense",
      description:
        "Ce brouillon ne crée aucune écriture. Soumettez-le au conseil, puis le syndic pourra le comptabiliser après contrôle. Joignez d’abord la facture dans Documents.",
      fields: [
        { name: "label", label: "Objet de la dépense" },
        {
          name: "year",
          label: "Exercice",
          choices: choices(
            c.years.filter((y) => !y.closed),
            "name",
          ),
        },
        {
          name: "key",
          label: "Clé de charges",
          choices: choices(c.keys, "name"),
        },
        {
          name: "supplier_record",
          label: "Fournisseur de l’annuaire",
          choices: choices(c.suppliers, "name"),
          optional: true,
        },
        { name: "supplier", label: "Ou nom du fournisseur", optional: true },
        { name: "reference", label: "Référence de la facture" },
        {
          name: "date",
          label: "Date de la facture",
          type: "date",
          value: today(),
        },
        {
          name: "due_date",
          label: "Date d’échéance",
          type: "date",
          optional: true,
        },
        { name: "amount", label: "Montant total (€)", type: "number" },
        {
          name: "document",
          label: "Facture / justificatif",
          choices: choices(c.documents, "title"),
        },
        {
          name: "charge_code",
          label: "Compte de charges",
          optional: true,
          choices: c.accounts.map((a) => ({
            value: a.code,
            label: `${a.code} · ${a.name}`,
          })),
          help: "À défaut : 601 pour les charges courantes, 671 pour les travaux.",
        },
        {
          name: "project",
          label: "Opération de travaux, si concernée",
          choices: choices(c.projects, "name"),
          optional: true,
        },
        {
          name: "cost_center",
          label: "Analytique, si utilisée",
          choices: choices(c.centers, "name"),
          optional: true,
        },
      ].map((field: CouncilField) => ({
        ...field,
        value: draft ? draft.data[field.name] : field.value,
      })),
      save: async (data) => {
        await api(
          `council/drafts${draft ? `/${draft.id}` : ""}`,
          draft ? "PATCH" : "POST",
          data,
        );
        reload("La dépense est préparée. Soumettez-la maintenant au conseil.");
      },
    });
  }
  function requestReview() {
    setRequestForm(true);
  }
  function giveOpinion(item: Row) {
    setEditor({
      title: "Donner mon avis",
      description:
        "Relisez le justificatif et le dossier. Votre avis est daté et conservé ; il ne pourra pas être réécrit. Vous ne pouvez pas valider votre propre préparation.",
      fields: [
        {
          name: "decision",
          label: "Avis",
          choices: [
            { value: "approved", label: "Favorable" },
            { value: "rejected", label: "Refusé" },
          ],
        },
        { name: "reason", label: "Motif et points vérifiés", type: "textarea" },
      ],
      save: async (data) => {
        await api(`council/requests/${item.id}/review`, "POST", data);
        reload("Votre avis est conservé dans le dossier.");
      },
    });
  }
  function controlEditor(item?: Row, finalize = false) {
    if (!c) return;
    setEditor({
      title: finalize
        ? "Finaliser mon rapport de contrôle"
        : item
          ? "Compléter mon rapport"
          : "Préparer un contrôle des comptes",
      description: finalize
        ? "La version finale est conservée avec les pièces et l’état des comptes contrôlé. Les modifications comptables ultérieures seront signalées."
        : "Le contrôleur travaille indépendamment de la gestion. Examinez les comptes, puis décrivez vos constats, y compris les anomalies relevées.",
      fields: [
        ...(!item
          ? [
              {
                name: "year",
                label: "Exercice contrôlé",
                choices: c.years.map((y) => ({ value: y.id, label: y.name })),
              },
            ]
          : []),
        {
          name: "title",
          label: "Titre du rapport",
          value: item?.title || "Contrôle des comptes",
        },
        ...Object.entries(checks).map(([name, label]) => ({
          name,
          label,
          type: "checkbox",
          value: item?.checks[name] || false,
        })),
        {
          name: "observations",
          label: "Constats, anomalies et recommandations",
          type: "textarea",
          value: item?.observations,
        },
        {
          name: "evidence",
          label: "Pièces du contrôle",
          type: "multiple",
          choices: versionChoices,
          optional: true,
          value: item?.evidence || [],
          help: "Plusieurs pièces peuvent être sélectionnées. Au moins une pièce est requise à la finalisation.",
        },
        ...(finalize
          ? [
              {
                name: "conclusion",
                label: "Conclusion du contrôle",
                choices: Object.entries(conclusions)
                  .filter(([id]) => id !== "draft")
                  .map(([value, label]) => ({ value, label })),
              },
            ]
          : []),
      ],
      submitLabel: finalize
        ? "Conserver le rapport final"
        : "Enregistrer le brouillon",
      save: async (data) => {
        const checked = Object.fromEntries(
          Object.keys(checks).map((k) => [k, data[k]]),
        );
        Object.keys(checks).forEach((k) => delete data[k]);
        await api(
          `council/controls${item ? `/${item.id}${finalize ? "/finalize" : ""}` : ""}`,
          item && !finalize ? "PATCH" : "POST",
          { ...data, checks: checked },
        );
        reload(
          finalize
            ? "Le rapport final est conservé."
            : "Le rapport est enregistré en brouillon.",
        );
      },
    });
  }
  if (!c && loading)
    return <p role="status">Chargement du conseil syndical…</p>;
  return (
    <div className="council-space">
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="council-notice" role="status">
          <Icon name="check" size={17} />
          {notice}
        </div>
      )}
      {c && (
        <>
          <section className="council-intro">
            <div>
              <p className="eyebrow">UNE GESTION À PLUSIEURS</p>
              <h2>
                Des responsabilités claires,
                <br />
                des décisions conservées.
              </h2>
              <p>
                Chacun accède aux pièces utiles à sa mission. Préparer,
                contrôler et comptabiliser sont des actions distinctes.
              </p>
            </div>
            <span className="subtle-badge">
              {c.settings.mode === "cooperative"
                ? "Syndicat coopératif"
                : "Syndic bénévole"}
            </span>
          </section>
          {loading && (
            <p className="muted" role="status">
              Actualisation…
            </p>
          )}
          {section === "mandates" && (
            <>
              <div className="council-toolbar">
                <div>
                  <h2>Composition et mandats</h2>
                  <p>Les dates, pièces et responsabilités de votre équipe.</p>
                </div>
                {can("access.admin") && (
                  <button
                    className="button primary"
                    onClick={() => setMandateForm(true)}
                  >
                    <Icon name="plus" size={16} />
                    Confier une responsabilité
                  </button>
                )}
              </div>
              <div className="council-role-grid">
                {c.roles.map((r) => (
                  <article key={r.value}>
                    <Icon
                      name={
                        r.value === "controller"
                          ? "shield"
                          : r.value === "treasurer"
                            ? "wallet"
                            : "people"
                      }
                    />
                    <h3>{r.label}</h3>
                    <p>
                      {r.value === "controller"
                        ? "Consulte les pièces et rédige son contrôle indépendant."
                        : ["council", "president", "vice"].includes(r.value)
                          ? "Consulte les comptes et donne des avis tracés sur les dépenses."
                          : r.value === "treasurer"
                            ? "Consulte les comptes et prépare des dépenses en brouillon."
                            : "Assure la gestion et comptabilise les opérations."}
                    </p>
                  </article>
                ))}
              </div>
              {!c.mandates.length ? (
                <Empty
                  title="Votre équipe reste à constituer"
                  description="L’administrateur principal peut reprendre les désignations d’AG ou enregistrer les mandats depuis leurs pièces."
                />
              ) : (
                <div className="council-mandates">
                  {c.mandates.map((m) => (
                    <article className="council-card" key={m.id}>
                      <div className="council-card-heading">
                        <div>
                          <p className="eyebrow">{m.role_label}</p>
                          <h3>{m.name}</h3>
                          <p>
                            {day(m.starts_on)} → {day(m.ends_on)}
                          </p>
                        </div>
                        <span
                          className={`council-status ${m.active ? "approved" : "withdrawn"}`}
                        >
                          {m.revoked_at
                            ? "Terminé"
                            : m.active
                              ? "Actif"
                              : new Date(m.starts_on) > new Date()
                                ? "À venir"
                                : "Hors période / sans accès actif"}
                        </span>
                      </div>
                      <p>{m.reference}</p>
                      {m.revocation_reason && (
                        <p>
                          <strong>Motif de fin :</strong> {m.revocation_reason}
                        </p>
                      )}
                      {m.permanent_manager && (
                        <p className="council-inline-help">
                          Ce compte possède également un accès permanent de
                          gestion. Terminer ce mandat ne retire pas cet accès ;
                          l’administrateur le gère dans Utilisateurs.
                        </p>
                      )}
                      <div className="council-actions">
                        {m.proof && fileLink(m.proof, "Pièce de désignation")}
                        {can("access.admin") && !m.revoked_at && (
                          <button
                            className="button secondary"
                            onClick={() =>
                              reasonAction(
                                "Terminer ce mandat",
                                "Les accès de ce mandat sont retirés immédiatement. Les mandats de présidence qui en dépendent cessent aussi de donner accès. La décision et son motif restent conservés.",
                                `council/mandates/${m.id}/revoke`,
                                "Le mandat est terminé.",
                              )
                            }
                          >
                            Terminer le mandat
                          </button>
                        )}
                        {can("access.admin") &&
                          c.users?.find((u) => u.id === m.user)?.external && (
                            <button
                              className="button secondary"
                              onClick={() =>
                                setEditor({
                                  title: "Renouveler l’accès du contrôleur",
                                  description:
                                    "Un nouveau mot de passe temporaire remplacera le précédent. La personne devra le changer à sa prochaine connexion.",
                                  fields: [
                                    {
                                      name: "confirm",
                                      label:
                                        "Je confirme la réinitialisation de cet accès",
                                      type: "checkbox",
                                    },
                                  ],
                                  save: async (d) => {
                                    if (!d.confirm)
                                      throw new Error(
                                        "Confirmez la réinitialisation.",
                                      );
                                    const r = await api<Row>(
                                      `council/mandates/${m.id}/reset-external`,
                                      "POST",
                                      {},
                                    );
                                    setCredentials(r.credentials);
                                    reload("L’accès temporaire est prêt.");
                                  },
                                })
                              }
                            >
                              Renouveler son accès
                            </button>
                          )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
          {section === "settings" && (
            <section className="panel council-settings">
              <div className="panel-heading">
                <div>
                  <h2>Mode de gestion et règles de contrôle</h2>
                  <p>
                    Les droits des mandats et les contrôles avant exécution.
                  </p>
                </div>
                {can("access.admin") && (
                  <button className="button primary" onClick={settingsEditor}>
                    Modifier les règles
                  </button>
                )}
              </div>
              <dl>
                <div>
                  <dt>Organisation</dt>
                  <dd>
                    {c.settings.mode === "cooperative"
                      ? "Président du conseil et syndic réunis ; contrôle des comptes indépendant."
                      : "Syndic bénévole et conseil syndical avec responsabilités distinctes."}
                  </dd>
                </div>
                <div>
                  <dt>Contrôle obligatoire</dt>
                  <dd>
                    {c.settings.approval_enabled
                      ? `À partir de ${money(c.settings.threshold)} · ${c.settings.required_approvals} avis favorable(s) distinct(s)`
                      : "Désactivé. Les demandes soumises volontairement restent contrôlées."}
                  </dd>
                </div>
                <div>
                  <dt>Règle enregistrée</dt>
                  <dd>{c.settings.reference || "Aucune règle renseignée"}</dd>
                </div>
              </dl>
              {c.settings.proof &&
                fileLink(c.settings.proof, "Document de la règle")}
              <p className="council-inline-help">
                Un avis favorable est un contrôle interne. Il ne donne pas à lui
                seul une délégation juridique au conseil et ne réalise aucun
                paiement bancaire. Les avis sont conservés avec leurs motifs et
                leurs auteurs.
              </p>
              {!can("access.admin") && (
                <p className="muted">
                  La configuration et l’attribution des accès sont réservées à
                  l’administrateur principal.
                </p>
              )}
            </section>
          )}
          {section === "approvals" && (
            <>
              <div className="council-toolbar">
                <div>
                  <h2>Préparer et contrôler les dépenses</h2>
                  <p>
                    Une pièce, une demande, des avis nominatifs, puis une
                    exécution par le syndic.
                  </p>
                </div>
                <div className="council-actions">
                  {can("expense.prepare") && (
                    <button
                      className="button secondary"
                      onClick={() => setUploadForm(true)}
                    >
                      Ajouter un justificatif
                    </button>
                  )}
                  {can("management.write") && (
                    <button
                      className="button secondary"
                      onClick={() => void requestReview()}
                    >
                      Demander un avis
                    </button>
                  )}
                  {can("expense.prepare") && (
                    <button
                      className="button primary"
                      onClick={() => prepareExpense()}
                    >
                      <Icon name="plus" size={16} />
                      Préparer une dépense
                    </button>
                  )}
                </div>
              </div>
              <p className="council-inline-help">
                {c.settings.approval_enabled
                  ? `Contrôle requis dès ${money(c.settings.threshold)}. Le règlement d’une facture et la sélection d’un devis attendent les avis requis.`
                  : "Vous pouvez soumettre un dossier volontairement. L’administrateur peut rendre ce contrôle obligatoire dans Mode & règles."}{" "}
                Le syndic ne valide pas ses propres préparations. Un refus ou
                une pièce modifiée bloque la suite.
              </p>
              {drafts.length > 0 && (
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Dépenses préparées</h3>
                      <p>
                        Un brouillon ne modifie pas la comptabilité. Les 200
                        dernières préparations sont affichées.
                      </p>
                    </div>
                  </div>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Objet</th>
                          <th>Préparé par</th>
                          <th>Montant</th>
                          <th>État</th>
                          <th>Suite</th>
                        </tr>
                      </thead>
                      <tbody>
                        {drafts.map((d) => (
                          <tr key={d.id}>
                            <td>
                              <strong>{d.data.label}</strong>
                              <small>
                                {d.data.supplier} · {d.data.reference}
                              </small>
                            </td>
                            <td>{d.author}</td>
                            <td>{money(d.data.amount)}</td>
                            <td>
                              <span className={`council-status ${d.status}`}>
                                {stages[d.status]}
                              </span>
                            </td>
                            <td>
                              <div className="council-actions">
                                {d.status === "draft" &&
                                  can("expense.prepare") &&
                                  (can("management.write") ||
                                    d.author_id === c.user.id) && (
                                    <>
                                      <button
                                        className="button secondary"
                                        onClick={() =>
                                          setEditor({
                                            title:
                                              "Soumettre cette préparation",
                                            description: `${d.data.label} · ${money(d.data.amount)}. Le justificatif et les données seront conservés avec la demande.`,
                                            fields: [
                                              {
                                                name: "proof",
                                                label:
                                                  "Version du justificatif, si différente",
                                                choices: versionChoices,
                                                optional: true,
                                              },
                                            ],
                                            save: async (v) => {
                                              await api(
                                                `council/drafts/${d.id}/submit`,
                                                "POST",
                                                v,
                                              );
                                              reload(
                                                "La préparation a été soumise au conseil.",
                                              );
                                            },
                                          })
                                        }
                                      >
                                        Soumettre au conseil
                                      </button>
                                      <button
                                        className="button secondary"
                                        onClick={() => prepareExpense(d)}
                                      >
                                        Corriger
                                      </button>
                                      <button
                                        className="button secondary"
                                        onClick={() =>
                                          reasonAction(
                                            "Annuler la préparation",
                                            "Le brouillon restera dans l’historique.",
                                            `council/drafts/${d.id}/cancel`,
                                            "La préparation est annulée.",
                                          )
                                        }
                                      >
                                        Annuler
                                      </button>
                                    </>
                                  )}
                                {d.status === "submitted" &&
                                  can("management.write") && (
                                    <button
                                      className="button secondary"
                                      disabled={d.review_state !== "approved"}
                                      title={
                                        d.review_state === "approved"
                                          ? "Les avis sont favorables"
                                          : "Les avis favorables du conseil sont attendus"
                                      }
                                      onClick={() =>
                                        setEditor({
                                          title:
                                            "Comptabiliser la préparation contrôlée",
                                          description:
                                            "La facture sera enregistrée dans l’exercice indiqué, avec une écriture équilibrée. Aucun paiement bancaire n’est réalisé. Les avis doivent être favorables et le dossier inchangé.",
                                          fields: [
                                            {
                                              name: "confirmed",
                                              label:
                                                "J’ai vérifié la facture et son exercice",
                                              type: "checkbox",
                                            },
                                          ],
                                          save: async (v) => {
                                            if (!v.confirmed)
                                              throw new Error(
                                                "Confirmez la vérification.",
                                              );
                                            await api(
                                              `council/drafts/${d.id}/post`,
                                              "POST",
                                              {},
                                            );
                                            reload(
                                              "La facture est comptabilisée. Son règlement reste à enregistrer dans Dépenses.",
                                            );
                                          },
                                        })
                                      }
                                    >
                                      {d.review_state === "approved"
                                        ? "Comptabiliser après contrôle"
                                        : "En attente des avis"}
                                    </button>
                                  )}
                                {d.expense && (
                                  <span>Facture n°{d.expense}</span>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
              <h3 className="council-list-title">
                Demandes et avis du conseil
              </h3>
              {!items.length && !loading ? (
                <Empty
                  title="Aucun dossier soumis"
                  description="Le syndic soumet une facture ou un devis. Un trésorier peut préparer une dépense et la transmettre au conseil."
                />
              ) : (
                <div className="council-requests">
                  {items.map((r) => (
                    <article className="council-card" key={r.id}>
                      <div className="council-card-heading">
                        <div>
                          <p className="eyebrow">
                            {r.kind === "quote"
                              ? "DEVIS"
                              : r.kind === "draft"
                                ? "DÉPENSE PRÉPARÉE"
                                : "FACTURE"}{" "}
                            · DOSSIER {r.id}
                          </p>
                          <h3>{r.snapshot.label}</h3>
                          <p>
                            {r.snapshot.supplier} · {money(r.snapshot.amount)}
                          </p>
                        </div>
                        <span className={`council-status ${r.state}`}>
                          {stages[r.state]}
                        </span>
                      </div>
                      <p>
                        Soumis par {r.created_by} le {day(r.created_at)} ·{" "}
                        {r.required_approvals} avis favorable(s) requis
                      </p>
                      {r.snapshot.reference && (
                        <p>Référence : {r.snapshot.reference}</p>
                      )}
                      {fileLink(r.proof, "Lire le justificatif contrôlé")}
                      <div className="council-opinions">
                        {r.reviews.map((v: Row) => (
                          <div key={v.id}>
                            <span className={`council-status ${v.decision}`}>
                              {v.decision === "approved"
                                ? "Favorable"
                                : "Refusé"}
                            </span>
                            <strong>{v.author}</strong>
                            <span>{day(v.created_at)}</span>
                            <p>{v.reason}</p>
                          </div>
                        ))}
                        {!r.reviews.length && (
                          <p>Aucun avis enregistré pour le moment.</p>
                        )}
                      </div>
                      {r.withdrawal_reason && (
                        <p>Retrait : {r.withdrawal_reason}</p>
                      )}
                      <div className="council-actions">
                        {can("expense.review") &&
                          ["pending", "approved"].includes(r.state) &&
                          !r.reviews.some(
                            (v: Row) => v.author_id === c.user.id,
                          ) &&
                          r.created_by_id !== c.user.id && (
                            <button
                              className="button primary"
                              onClick={() => giveOpinion(r)}
                            >
                              Donner mon avis
                            </button>
                          )}
                        {r.can_withdraw &&
                          (can("management.write") ||
                            (r.created_by_id === c.user.id &&
                              can("expense.prepare"))) && (
                            <button
                              className="button secondary"
                              onClick={() =>
                                reasonAction(
                                  "Retirer cette demande",
                                  "Les avis et la demande restent conservés. Pour un dossier refusé ou corrigé, préparez ensuite une nouvelle demande.",
                                  `council/requests/${r.id}/withdraw`,
                                  "La demande a été retirée ; son historique est conservé.",
                                )
                              }
                            >
                              Retirer avec un motif
                            </button>
                          )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
              <Pager count={count} page={page} size={50} onPage={setPage} />
            </>
          )}
          {section === "controls" && (
            <>
              <div className="council-toolbar">
                <div>
                  <h2>Le contrôle indépendant des comptes</h2>
                  <p>
                    Une checklist, des pièces et un rapport conservé pour chaque
                    contrôle.
                  </p>
                </div>
                {can("accounts.control") && (
                  <button
                    className="button secondary"
                    onClick={() => setUploadForm(true)}
                  >
                    Ajouter un justificatif
                  </button>
                )}
                {can("accounts.control") && (
                  <button
                    className="button primary"
                    onClick={() => controlEditor()}
                  >
                    Préparer un rapport
                  </button>
                )}
              </div>
              {!can("accounts.control") && (
                <p className="council-inline-help">
                  Les rapports sont consultables par le conseil et le syndic.
                  Leur rédaction et leur finalisation appartiennent au
                  contrôleur indépendant désigné.
                </p>
              )}
              {!items.length && !loading && (
                <Empty
                  title="Aucun rapport de contrôle"
                  description="Désignez un contrôleur indépendant, puis il pourra examiner les pièces et rédiger son rapport depuis son accès."
                />
              )}
              {items.map((r) => (
                <article className="council-card council-control" key={r.id}>
                  <div className="council-card-heading">
                    <div>
                      <p className="eyebrow">EXERCICE {r.year_name}</p>
                      <h3>{r.title}</h3>
                      <p>
                        {r.author} · {day(r.finalized_at || r.created_at)}
                      </p>
                    </div>
                    <span
                      className={`council-status ${r.finalized_at ? "approved" : "draft"}`}
                    >
                      {conclusions[r.conclusion]}
                    </span>
                  </div>
                  <ul className="council-checklist">
                    {Object.entries(checks).map(([id, label]) => (
                      <li key={id}>
                        <Icon
                          name={r.checks[id] ? "check" : "info"}
                          size={16}
                        />
                        {label}
                        {r.checks[id] ? "" : " — à examiner"}
                      </li>
                    ))}
                  </ul>
                  <p className="council-observations">{r.observations}</p>
                  <div className="council-actions">
                    {r.evidence.map((id: number) => (
                      <span key={id}>
                        {fileLink(
                          id,
                          c.versions.find((v) => v.id === id)?.title ||
                            `Pièce ${id}`,
                        )}
                      </span>
                    ))}
                  </div>
                  {r.changed_since_control && (
                    <p className="alert">
                      Les comptes ou leur état ont changé depuis ce contrôle. Le
                      rapport décrit la version examinée ; préparez un nouveau
                      contrôle pour les données actuelles.
                    </p>
                  )}
                  <div className="council-actions">
                    {can("accounts.control") &&
                      r.author_id === c.user.id &&
                      !r.finalized_at && (
                        <>
                          <button
                            className="button secondary"
                            onClick={() => controlEditor(r)}
                          >
                            Compléter le brouillon
                          </button>
                          <button
                            className="button primary"
                            onClick={() => controlEditor(r, true)}
                          >
                            Finaliser mon rapport
                          </button>
                        </>
                      )}
                    {r.finalized_at && (
                      <button
                        className="button secondary"
                        onClick={() =>
                          download(
                            `Copro-controle-comptes-${r.id}.md`,
                            `# ${r.title}\n\nExercice : ${r.year_name}\nContrôleur : ${r.author}\nFinalisé le ${day(r.finalized_at)}\nConclusion : ${conclusions[r.conclusion]}\n\n## Vérifications\n${Object.entries(
                              checks,
                            )
                              .map(
                                ([k, label]) =>
                                  `- [${r.checks[k] ? "x" : " "}] ${label}`,
                              )
                              .join(
                                "\n",
                              )}\n\n## Observations\n${r.observations}\n\n## État comptable contrôlé\n${JSON.stringify(r.snapshot, null, 2)}\n\nPièces (versions) : ${r.evidence.join(", ")}\nLes fichiers joints restent conservés dans l’application.\n`,
                          )
                        }
                      >
                        Télécharger le rapport
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </>
          )}
          {["accounts", "history"].includes(section) && (
            <>
              {section === "accounts" && (
                <div className="council-filters">
                  <label>
                    Que souhaitez-vous examiner ?
                    <select
                      value={kind}
                      onChange={(e) => setKind(e.target.value)}
                    >
                      {Object.entries({
                        expenses: "Factures et règlements",
                        quotes: "Devis",
                        balance: "Balance des comptes",
                        ledger: "Écritures détaillées",
                        budget: "Budget / réalisé",
                        banks: "Comptes bancaires",
                        statements: "Relevés et rapprochements",
                        works: "Travaux et sinistres",
                        contracts: "Contrats",
                        documents: "Pièces et versions",
                      }).map(([id, title]) => (
                        <option value={id} key={id}>
                          {title}
                        </option>
                      ))}
                    </select>
                  </label>
                  {[
                    "expenses",
                    "balance",
                    "ledger",
                    "budget",
                    "statements",
                  ].includes(kind) && (
                    <label>
                      Exercice
                      <select
                        value={year || c.years[0]?.id || ""}
                        onChange={(e) => setYear(e.target.value)}
                      >
                        <option value="">Choisir…</option>
                        {c.years.map((y) => (
                          <option key={y.id} value={y.id}>
                            {y.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
              )}
              {section === "history" ? (
                <div className="council-history">
                  {items.map((e) => (
                    <article key={e.id}>
                      <Icon name="check" size={16} />
                      <div>
                        <strong>{historyLabel(e.action)}</strong>
                        <p>
                          {e.actor} · {day(e.created_at)} · dossier {e.target}
                        </p>
                        {e.details.reason && <p>{e.details.reason}</p>}
                        {e.details.reference && <p>{e.details.reference}</p>}
                      </div>
                    </article>
                  ))}
                  {!items.length && !loading && (
                    <Empty
                      title="Aucune opération conservée"
                      description="Les mandats, règles, avis et rapports apparaîtront ici."
                    />
                  )}
                </div>
              ) : (
                <RecordList kind={kind} rows={items} versions={c.versions} />
              )}
              <Pager count={count} page={page} size={100} onPage={setPage} />
            </>
          )}
        </>
      )}
      {editor && (
        <CouncilEditor
          title={editor.title}
          description={editor.description}
          fields={editor.fields}
          submitLabel={editor.submitLabel}
          onSave={editor.save}
          onClose={() => setEditor(null)}
        />
      )}
      {uploadForm && (
        <CouncilUpload
          onSaved={() =>
            reload("La pièce est ajoutée aux documents de gestion.")
          }
          onClose={() => setUploadForm(false)}
        />
      )}
      {requestForm && c && (
        <CouncilRequestForm
          versions={c.versions}
          onSaved={() => reload("La demande est prête pour le conseil.")}
          onClose={() => setRequestForm(false)}
        />
      )}
      {mandateForm && c && (
        <CouncilMandateForm
          context={c}
          onClose={() => setMandateForm(false)}
          onSave={async (data) => {
            const r = await api<Row>("council/mandates", "POST", data);
            if (r.credentials) setCredentials(r.credentials);
            reload("La responsabilité et ses accès datés sont enregistrés.");
          }}
        />
      )}
      {credentials && (
        <CredentialsDialog
          credentials={credentials}
          onClose={() => setCredentials(null)}
        />
      )}
    </div>
  );
}

function Pager({
  count,
  page,
  size,
  onPage,
}: {
  count: number;
  page: number;
  size: number;
  onPage: (n: number) => void;
}) {
  return count > size ? (
    <nav className="council-pager" aria-label="Pages des résultats">
      <button
        className="button secondary"
        disabled={page === 1}
        onClick={() => onPage(page - 1)}
      >
        Précédent
      </button>
      <span>
        Page {page} / {Math.ceil(count / size)} · {count} éléments
      </span>
      <button
        className="button secondary"
        disabled={page * size >= count}
        onClick={() => onPage(page + 1)}
      >
        Suivant
      </button>
    </nav>
  ) : null;
}
const recordFields: Record<string, [string, string][]> = {
  works: [
    ["title", "Dossier"],
    ["kind", "Nature"],
    ["description", "Description"],
    ["status", "État"],
    ["budget", "Budget indicatif"],
    ["due_date", "Échéance"],
  ],
  statements: [
    ["bank", "Banque"],
    ["starts_on", "Début"],
    ["ends_on", "Fin"],
    ["opening_balance", "Solde initial"],
    ["closing_balance", "Solde final"],
    ["validated", "Rapprochement validé"],
  ],
  expenses: [
    ["id", "Facture n°"],
    ["date", "Date"],
    ["label", "Objet"],
    ["supplier", "Fournisseur"],
    ["reference", "Référence"],
    ["amount", "Montant"],
    ["amount_paid", "Réglé"],
    ["remaining", "Reste"],
  ],
  quotes: [
    ["id", "Devis n°"],
    ["label", "Dossier"],
    ["supplier", "Fournisseur"],
    ["amount", "Montant"],
    ["selected", "Retenu"],
  ],
  balance: [
    ["code", "Compte"],
    ["name", "Libellé"],
    ["debit", "Débit"],
    ["credit", "Crédit"],
    ["balance", "Solde"],
  ],
  budget: [
    ["code", "Compte"],
    ["name", "Libellé"],
    ["budget", "Prévu"],
    ["actual", "Réalisé"],
    ["variance", "Écart"],
  ],
  ledger: [
    ["date", "Date"],
    ["number", "Écriture"],
    ["journal", "Journal"],
    ["account", "Compte"],
    ["label", "Libellé"],
    ["owner", "Copropriétaire"],
    ["supplier", "Fournisseur"],
    ["debit", "Débit"],
    ["credit", "Crédit"],
  ],
  banks: [
    ["name", "Compte"],
    ["bank_name", "Banque"],
    ["iban", "IBAN"],
    ["account", "Compte comptable"],
  ],
  contracts: [
    ["title", "Contrat"],
    ["supplier", "Fournisseur"],
    ["reference", "Référence"],
    ["starts_on", "Début"],
    ["ends_on", "Fin"],
    ["annual_cost", "Coût annuel"],
  ],
  documents: [
    ["title", "Pièce"],
    ["filename", "Fichier"],
    ["created_at", "Date"],
    ["archived", "Archivée"],
  ],
};
function RecordList({
  kind,
  rows,
  versions,
}: {
  kind: string;
  rows: Row[];
  versions: Row[];
}) {
  const fields = recordFields[kind] || [];
  if (!rows.length)
    return (
      <Empty
        title="Aucun élément à examiner"
        description="Les informations saisies dans l’application seront consultables ici en lecture seule."
      />
    );
  return (
    <section className="panel">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {fields.map(([key, label]) => (
                <th key={key}>{label}</th>
              ))}
              <th>{kind === "statements" ? "Mouvements" : "Pièces"}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.id || `${r.code}-${i}`}>
                {fields.map(([key]) => (
                  <td key={key}>
                    {[
                      "amount",
                      "amount_paid",
                      "remaining",
                      "debit",
                      "credit",
                      "balance",
                      "budget",
                      "actual",
                      "variance",
                      "annual_cost",
                      "opening_balance",
                      "closing_balance",
                    ].includes(key)
                      ? money(r[key])
                      : [
                            "date",
                            "starts_on",
                            "ends_on",
                            "created_at",
                            "due_date",
                          ].includes(key)
                        ? day(r[key])
                        : typeof r[key] === "boolean"
                          ? r[key]
                            ? "Oui"
                            : "Non"
                          : String(r[key] ?? "—")}
                  </td>
                ))}
                <td>
                  {kind === "statements" && (
                    <details>
                      <summary>Voir les mouvements</summary>
                      <ul className="council-statement-lines">
                        {(r.movements || []).map((m: Row) => (
                          <li key={m.id}>
                            <strong>
                              {day(m.date)} · {money(m.amount)}
                            </strong>
                            <span>{m.label}</span>
                            <small>
                              {m.matched ? "Rapproché" : "À rapprocher"}
                            </small>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  {kind === "documents"
                    ? fileLink(r.id, "Télécharger")
                    : (
                        r.versions ||
                        (r.version
                          ? [r.version]
                          : r.document
                            ? versions
                                .filter((v) => v.document === r.document)
                                .slice(0, 1)
                                .map((v) => v.id)
                            : [])
                      ).map((id: number) => (
                        <span key={id}>{fileLink(id)}</span>
                      ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function historyLabel(action: string) {
  return (
    (
      {
        "mandate.granted": "Responsabilité confiée",
        "mandate.revoked": "Mandat terminé",
        "settings.updated": "Règles de contrôle modifiées",
        "review.requested": "Dossier soumis au conseil",
        "review.approved": "Avis favorable conservé",
        "review.rejected": "Refus motivé conservé",
        "review.withdrawn": "Demande retirée",
        "expense.prepared": "Dépense préparée",
        "expense.posted": "Dépense comptabilisée",
        "expense.cancelled": "Préparation annulée",
        "expense.updated": "Préparation corrigée",
        "document.prepared": "Justificatif ajouté",
        "control.saved": "Rapport en préparation",
        "control.finalized": "Rapport final conservé",
        "external.reset": "Accès temporaire renouvelé",
      } as Record<string, string>
    )[action] || action
  );
}

export function CouncilPortal({
  user,
  onUser,
  onLogout,
}: {
  user: User;
  onUser: (user: User) => void;
  onLogout: () => Promise<void>;
}) {
  const [section, setSection] = useState("mandates");
  const [member, setMember] = useState(false);
  const [error, setError] = useState("");
  if (member && user.has_owner)
    return (
      <>
        <div className="council-back">
          <button className="button primary" onClick={() => setMember(false)}>
            Revenir au conseil syndical
          </button>
        </div>
        <MemberPortal user={user} onUser={onUser} onLogout={onLogout} />
      </>
    );
  return (
    <div className="council-portal">
      <header className="member-header">
        <a className="brand" href="/">
          <BrandMark />
          Copro.
        </a>
        <div>
          <span className="subtle-badge">Conseil & contrôle</span>
          {user.has_owner && (
            <button
              className="button secondary"
              onClick={() => setMember(true)}
            >
              Mon espace copropriétaire
            </button>
          )}
          <button
            className="button secondary"
            onClick={async () => {
              try {
                const r = await api<{ user: User }>("session");
                onUser(r.user);
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Actualiser mon accès
          </button>
          <button className="button secondary" onClick={() => void onLogout()}>
            Se déconnecter
          </button>
        </div>
      </header>
      <main>
        <p className="eyebrow">BONJOUR {user.display_name || user.username}</p>
        <h1>Conseil syndical & contrôles</h1>
        {error && <p className="alert">{error}</p>}
        <nav className="council-tabs" aria-label="Rubriques du conseil">
          {Object.entries(sections).map(([id, title]) => (
            <button
              key={id}
              className={section === id ? "active" : ""}
              aria-current={section === id ? "page" : undefined}
              onClick={() => setSection(id)}
            >
              {title}
            </button>
          ))}
        </nav>
        <Council section={section} />
      </main>
    </div>
  );
}
