import { useEffect, useState, useRef, lazy, Suspense } from "react";
import {
  api,
  ApiError,
  type User,
  type Owner,
  type Lot,
  type Overview,
  type Organization,
} from "./api";
import { kinds, number } from "./format";
import { Icon, Empty, BuildingIllustration } from "./components/ui";
import { Login } from "./components/Login";
import { Operations, HomeInsights } from "./components/Operations";
import { Presentation } from "./components/Presentation";
import { BrandMark } from "./components/BrandMark";
import { Editor } from "./components/Editor";
import { CredentialsDialog, type Credentials } from "./components/Access";
import { MemberPortal } from "./components/MemberPortal";
import { Finance } from "./components/Finance";
import { Accounting, AccountingReports } from "./components/Accounting";
import {
  Navigation,
  sections,
  navigationDestination,
} from "./components/Navigation";
import { Banking } from "./components/Banking";
import { AccountingCycle } from "./components/AccountingCycle";
import { Documents } from "./components/Documents";
import { Assemblies } from "./components/Assemblies";
import { Tools } from "./components/Tools";
import { CategoryOverview, categoryHelp } from "./components/CategoryOverview";
const AssemblyGuide = lazy(() =>
  import("./components/AssemblyGuide").then((module) => ({
    default: module.AssemblyGuide,
  })),
);
const Council = lazy(() =>
  import("./components/Council").then((m) => ({ default: m.Council })),
);
const CouncilPortal = lazy(() =>
  import("./components/Council").then((m) => ({ default: m.CouncilPortal })),
);
type Page =
  | "council"
  | "operations"
  | "partners"
  | "communication"
  | "overview"
  | "owners"
  | "lots"
  | "finance"
  | "accounting"
  | "reporting"
  | "documents"
  | "assemblies"
  | "tools"
  | "administration";
export function App() {
  if (window.location.pathname.replace(/\/$/, "") === "/presentation")
    return <Presentation />;
  return <Application />;
}
function Application() {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [page, setPage] = useState<Page>("overview");
  const [section, setSection] = useState("");
  const [compact, setCompact] = useState(() => {
    try {
      return localStorage.getItem("copro.sidebar.compact") === "1";
    } catch {
      return false;
    }
  });
  function toggleCompact() {
    setCompact((value) => {
      const next = !value;
      try {
        localStorage.setItem("copro.sidebar.compact", next ? "1" : "0");
      } catch {}
      return next;
    });
  }
  const [organization, setOrganization] = useState<Organization>({
    id: 1,
    name: "Ma copropriété",
  });
  async function loadOrganization() {
    try {
      const data = await api<{ organization: Organization | null }>("session");
      if (data.organization) setOrganization(data.organization);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    if (user) void loadOrganization();
  }, [user]);
  const [owners, setOwners] = useState<Owner[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [stats, setStats] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [editor, setEditor] = useState<{
    type: "owners" | "lots";
    item?: Owner | Lot;
  } | null>(null);
  const [notice, setNotice] = useState("");
  const [removing, setRemoving] = useState(false);
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [accessOwner, setAccessOwner] = useState<Owner | null>(null);

  useEffect(() => {
    api<{ user: User | null }>("session")
      .then((data) => setUser(data.user))
      .catch((e) => setError(e.message))
      .finally(() => setInitializing(false));
  }, []);
  async function load() {
    setBusy(true);
    setError("");
    try {
      const [o, l, s] = await Promise.all([
        api<{ items: Owner[] }>("owners"),
        api<{ items: Lot[] }>("lots"),
        api<Overview>("overview"),
      ]);
      setOwners(o.items);
      setLots(l.items);
      setStats(s);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setUser(null);
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    if (user?.is_manager) void load();
  }, [user]);
  useEffect(() => {
    if (notice) {
      const timer = setTimeout(() => setNotice(""), 4500);
      return () => clearTimeout(timer);
    }
  }, [notice]);
  function navigate(next: Page, child?: string) {
    const target = navigationDestination(next, child);
    setPage(target.page as Page);
    setSection(target.section || "");
    setSearch("");
    setRemoving(false);
  }
  async function signOut() {
    try {
      await api("logout", "POST");
      setUser(null);
      setStats(null);
      setOwners([]);
      setLots([]);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const title =
    sections[page]?.items.find(([key]) => key === section)?.[1] ||
    {
      operations: "Travaux & entretien",
      partners: "Fournisseurs & contrats",
      communication: "Communication",
      overview: "Vue d’ensemble",
      owners: "Copropriétaires",
      finance: "Charges & finances",
      lots: "Lots & tantièmes",
      accounting: "Gestion comptable",
      reporting: "Rapports comptables",
      administration: "Administration & configuration",
      documents: "Documents",
      assemblies: "Assemblées générales",
      tools: "Outils",
      council: "Conseil syndical",
    }[page];
  const filteredOwners = owners.filter((o) =>
    `${o.first_name} ${o.last_name} ${o.email}`
      .toLocaleLowerCase("fr")
      .includes(search.toLocaleLowerCase("fr")),
  );
  const filteredLots = lots.filter((l) =>
    `${l.number} ${kinds[l.kind]} ${l.owner_name}`
      .toLocaleLowerCase("fr")
      .includes(search.toLocaleLowerCase("fr")),
  );

  if (initializing)
    return (
      <div className="boot">
        <BrandMark />
        <p>Ouverture de votre espace…</p>
      </div>
    );
  if (!user)
    return window.location.pathname.replace(/\/$/, "") === "/connexion" ? (
      <Login error={error} onLogin={setUser} />
    ) : (
      <Presentation />
    );
  if (!user.is_manager || user.must_change_password)
    return !user.must_change_password &&
      user.capabilities?.includes("council.read") ? (
      <Suspense fallback={<p role="status">Ouverture du conseil…</p>}>
        <CouncilPortal user={user} onUser={setUser} onLogout={signOut} />
      </Suspense>
    ) : (
      <MemberPortal user={user} onUser={setUser} onLogout={signOut} />
    );
  return (
    <div className={`app-shell ${compact ? "menu-compact" : ""}`}>
      <Navigation
        user={user}
        organization={organization}
        page={page}
        section={section}
        ownersCount={owners.length}
        compact={compact}
        onToggleCompact={toggleCompact}
        onNavigate={(next, child) => navigate(next as Page, child)}
        onLogout={signOut}
      />
      <div className="main-shell">
        <header className="topbar">
          <span>
            {organization.name} <span className="breadcrumb-slash">/</span>
            <strong>{title}</strong>
          </span>
          <div className="header-actions">
            <span className="private-label">
              <span /> Espace privé
            </span>
            <button
              className="icon-button mobile-logout"
              aria-label="Se déconnecter"
              onClick={() => void signOut()}
            >
              <Icon name="logout" size={16} />
            </button>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <p className="eyebrow">LA COPROPRIÉTÉ, ENSEMBLE</p>
              <h1>{title}</h1>
              <p className="muted">
                {categoryHelp[page]?.items[section] ||
                  categoryHelp[page]?.description ||
                  (page === "overview"
                    ? "Les bonnes informations, pour avancer sereinement."
                    : page === "owners"
                      ? "Un annuaire commun pour garder le lien entre voisins."
                      : page === "finance"
                        ? "Suivez les charges, les opérations et les synthèses partagées."
                        : page === "accounting"
                          ? "Organisez vos comptes, budgets et écritures."
                          : page === "reporting"
                            ? "Consultez et exportez vos états comptables."
                            : page === "administration"
                              ? "Configurez votre copropriété et ses accès."
                              : "Une vision claire de votre immeuble et de sa répartition.")}
              </p>
            </div>
            {["overview", "owners", "lots"].includes(page) && (
              <button
                className="button primary"
                onClick={() => {
                  setRemoving(false);
                  setEditor({ type: page === "lots" ? "lots" : "owners" });
                }}
              >
                <Icon name="plus" size={18} />
                {page === "lots"
                  ? "Ajouter un lot"
                  : "Ajouter un copropriétaire"}
              </button>
            )}
          </div>
          {error && (
            <div className="alert" role="alert">
              {error}
              <button onClick={() => void load()}>Réessayer</button>
            </div>
          )}
          {sections[page] && !section ? (
            <CategoryOverview
              category={page}
              isAdmin={!!user.is_admin}
              onNavigate={(child) => navigate(page, child)}
            />
          ) : ["operations", "partners", "communication"].includes(page) ? (
            <Operations section={section} />
          ) : page === "finance" && section === "reminders" ? (
            <Operations section="reminders" />
          ) : page === "finance" && section === "banks" ? (
            <Banking />
          ) : (page === "accounting" &&
              [
                "opening",
                "allocation",
                "lettering",
                "closing",
                "corrections",
                "mutations",
              ].includes(section)) ||
            (page === "finance" &&
              ["reconciliation", "funds"].includes(section)) ||
            (page === "reporting" && ["annexes", "aged"].includes(section)) ? (
            <AccountingCycle key={section} section={section} />
          ) : page === "council" ? (
            <Suspense fallback={<p role="status">Chargement du conseil…</p>}>
              <Council section={section} />
            </Suspense>
          ) : page === "assemblies" && section === "guide" ? (
            <Suspense fallback={<p role="status">Chargement du guide…</p>}>
              <AssemblyGuide onNavigate={navigate} />
            </Suspense>
          ) : page === "assemblies" ? (
            <Assemblies
              section={section}
              onGuide={() => navigate("assemblies", "guide")}
            />
          ) : page === "tools" ? (
            <Tools key={section} section={section} />
          ) : page === "documents" ? (
            <Documents manager section={section} />
          ) : page === "accounting" ? (
            section === "posting" ? (
              <Finance manager section="entries" />
            ) : (
              <Accounting
                key="accounting"
                section={section}
                isAdmin={user.is_admin}
              />
            )
          ) : page === "reporting" ? (
            <AccountingReports section={section} />
          ) : page === "administration" ? (
            <Accounting
              key="administration"
              section={section}
              administration
              isAdmin={user.is_admin}
              onOrganizationChange={() => void loadOrganization()}
            />
          ) : page === "finance" ? (
            <Finance manager section={section} />
          ) : busy && !stats ? (
            <div className="empty-state">
              <p>Chargement des informations…</p>
            </div>
          ) : page === "overview" ? (
            <>
              <HomeInsights onNavigate={(p, s) => navigate(p as Page, s)} />
              <section className="welcome-card">
                <div className="welcome-copy">
                  <span className="pill">VOTRE ESPACE COMMUN</span>
                  <h2>
                    Un immeuble.
                    <br />
                    Une équipe.
                  </h2>
                  <p>
                    Organisez votre copropriété, partagez les informations et
                    construisez une gestion plus simple.
                  </p>
                  <button
                    className="text-link light"
                    onClick={() => navigate("lots")}
                  >
                    Découvrir les lots <Icon name="arrow" size={18} />
                  </button>
                </div>
                <BuildingIllustration />
              </section>
              <section className="stats-grid" aria-label="Chiffres clés">
                {[
                  [
                    "Copropriétaires",
                    stats?.owners_count || 0,
                    "people",
                    "Les membres de votre copropriété",
                  ],
                  [
                    "Lots enregistrés",
                    stats?.lots_count || 0,
                    "building",
                    "Appartements et annexes",
                  ],
                  [
                    "Tantièmes généraux",
                    number(stats?.shares_total || 0),
                    "lots",
                    "Somme des tantièmes saisis",
                  ],
                ].map(([label, value, icon, caption]) => (
                  <article className="stat-card" key={String(label)}>
                    <div className="stat-top">
                      <span>{label}</span>
                      <span className="stat-icon">
                        <Icon name={String(icon)} />
                      </span>
                    </div>
                    <strong>{value}</strong>
                    <p>{caption}</p>
                  </article>
                ))}
              </section>
              <div className="overview-columns">
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Les copropriétaires</h2>
                      <p>Votre collectif, au même endroit.</p>
                    </div>
                    <button
                      className="text-link"
                      onClick={() => navigate("owners")}
                    >
                      Tout voir <Icon name="arrow" size={16} />
                    </button>
                  </div>
                  {owners.length ? (
                    <div className="owner-preview">
                      {owners.slice(0, 4).map((o) => (
                        <div className="person-row" key={o.id}>
                          <span className="avatar pastel">
                            {o.first_name[0]}
                            {o.last_name[0]}
                          </span>
                          <div>
                            <strong>
                              {o.first_name} {o.last_name}
                            </strong>
                            <small>{o.email || "Courriel à renseigner"}</small>
                          </div>
                          <span className="subtle-badge">
                            {o.lots_count} lot{o.lots_count !== 1 ? "s" : ""}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title="Votre collectif commence ici"
                      description="Ajoutez le premier copropriétaire pour constituer l’annuaire."
                      action="Ajouter un copropriétaire"
                      onAction={() => setEditor({ type: "owners" })}
                    />
                  )}
                </section>
                <section className="panel setup-panel">
                  <span className="section-icon">
                    <Icon name="check" />
                  </span>
                  <h2>Prenons un bon départ</h2>
                  <p className="muted">
                    Les premières étapes pour organiser votre immeuble.
                  </p>
                  <button
                    className="setup-step"
                    onClick={() => navigate("owners")}
                  >
                    <span
                      className={
                        owners.length ? "step-number done" : "step-number"
                      }
                    >
                      {owners.length ? <Icon name="check" size={15} /> : "1"}
                    </span>
                    <div>
                      <strong>Réunir les copropriétaires</strong>
                      <small>Complétez les coordonnées du collectif</small>
                    </div>
                    <Icon name="arrow" size={16} />
                  </button>
                  <button
                    className="setup-step"
                    onClick={() => navigate("lots")}
                  >
                    <span
                      className={
                        lots.length ? "step-number done" : "step-number"
                      }
                    >
                      {lots.length ? <Icon name="check" size={15} /> : "2"}
                    </span>
                    <div>
                      <strong>Décrire les lots</strong>
                      <small>Renseignez les propriétaires et tantièmes</small>
                    </div>
                    <Icon name="arrow" size={16} />
                  </button>
                  {!!stats?.unassigned_count && (
                    <p className="attention">
                      {stats.unassigned_count} lot(s) restent à attribuer.
                    </p>
                  )}
                </section>
              </div>
            </>
          ) : (
            <section className="panel directory-panel">
              <div className="directory-toolbar">
                <div className="table-title">
                  <h2>
                    {page === "owners"
                      ? "Annuaire des copropriétaires"
                      : "Les lots de l’immeuble"}
                  </h2>
                  <span className="count-pill">
                    {page === "owners" ? owners.length : lots.length}
                  </span>
                </div>
                <label className="search">
                  <Icon name="search" size={18} />
                  <input
                    aria-label="Rechercher"
                    placeholder={
                      page === "owners"
                        ? "Rechercher un copropriétaire…"
                        : "Rechercher un lot…"
                    }
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </label>
              </div>
              {page === "owners" ? (
                filteredOwners.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Copropriétaire</th>
                          <th>Coordonnées</th>
                          <th>Lots</th>
                          <th>
                            <span className="sr-only">Actions</span>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredOwners.map((o) => (
                          <tr key={o.id}>
                            <td>
                              <div className="person-cell">
                                <span className="avatar pastel">
                                  {o.first_name[0]}
                                  {o.last_name[0]}
                                </span>
                                <strong>
                                  {o.first_name} {o.last_name}
                                </strong>
                              </div>
                            </td>
                            <td>
                              <span>{o.email || "—"}</span>
                              <small>
                                {o.phone || "Téléphone non renseigné"}
                              </small>
                            </td>
                            <td>
                              <span className="subtle-badge">
                                {o.lots_count} lot
                                {o.lots_count !== 1 ? "s" : ""}
                              </span>
                            </td>
                            <td>
                              <button
                                className="edit-button"
                                onClick={() => {
                                  setRemoving(false);
                                  setEditor({ type: "owners", item: o });
                                }}
                                aria-label={`Modifier ${o.first_name} ${o.last_name}`}
                              >
                                <Icon name="edit" size={16} />
                                Modifier
                              </button>
                              {o.email && (
                                <button
                                  className="edit-button"
                                  onClick={() => setAccessOwner(o)}
                                >
                                  <Icon name="mail" size={16} />
                                  {o.has_access
                                    ? "Réinitialiser accès"
                                    : "Créer accès"}
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title={
                      search
                        ? "Aucun résultat"
                        : "Ajoutez votre premier copropriétaire"
                    }
                    description={
                      search
                        ? "Essayez un autre nom ou une autre adresse."
                        : "Ses coordonnées et ses lots seront réunis ici."
                    }
                    action={search ? undefined : "Ajouter un copropriétaire"}
                    onAction={() => setEditor({ type: "owners" })}
                  />
                )
              ) : filteredLots.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Lot</th>
                        <th>Copropriétaire</th>
                        <th>Étage / surface</th>
                        <th>Tantièmes</th>
                        <th>
                          <span className="sr-only">Actions</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredLots.map((l) => (
                        <tr key={l.id}>
                          <td>
                            <strong>Lot {l.number}</strong>
                            <small>{kinds[l.kind]}</small>
                          </td>
                          <td>
                            {l.owner_name || (
                              <span className="warning-badge">À attribuer</span>
                            )}
                          </td>
                          <td>
                            {l.floor || "—"}
                            <small>
                              {l.area
                                ? `${number(l.area)} m²`
                                : "Surface non renseignée"}
                            </small>
                          </td>
                          <td>
                            <strong className="tabular">
                              {number(l.shares)}
                            </strong>
                          </td>
                          <td>
                            <button
                              className="edit-button"
                              aria-label={`Modifier le lot ${l.number}`}
                              onClick={() => {
                                setRemoving(false);
                                setEditor({ type: "lots", item: l });
                              }}
                            >
                              <Icon name="edit" size={16} />
                              Modifier
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty
                  title={
                    search ? "Aucun résultat" : "Un premier lot pour commencer"
                  }
                  description={
                    search
                      ? "Essayez un autre numéro ou copropriétaire."
                      : "Ajoutez les appartements, caves, parkings et leurs tantièmes."
                  }
                  action={search ? undefined : "Ajouter un lot"}
                  onAction={() => setEditor({ type: "lots" })}
                />
              )}
            </section>
          )}
          <footer className="page-footer">
            <span>
              copro. <span>Une gestion plus simple, ensemble.</span>
            </span>
            <span>Votre espace de travail</span>
          </footer>
        </main>
      </div>
      {editor && (
        <Editor
          key={`${editor.type}-${editor.item?.id || "new"}`}
          type={editor.type}
          item={editor.item}
          owners={owners}
          removing={removing}
          setRemoving={setRemoving}
          onCredentials={setCredentials}
          onClose={() => setEditor(null)}
          onSaved={async (deleted) => {
            setEditor(null);
            setNotice(
              deleted
                ? "Élément supprimé."
                : "Les informations ont été enregistrées.",
            );
            await load();
          }}
        />
      )}
      {notice && (
        <div className="toast" role="status">
          <Icon name="check" />
          {notice}
        </div>
      )}
      {credentials && (
        <CredentialsDialog
          credentials={credentials}
          onClose={() => setCredentials(null)}
        />
      )}
      {accessOwner && (
        <AccessConfirmation
          owner={accessOwner}
          onClose={() => setAccessOwner(null)}
          onCreated={async (value) => {
            setAccessOwner(null);
            setCredentials(value);
            await load();
          }}
        />
      )}
    </div>
  );
}

function AccessConfirmation({
  owner,
  onClose,
  onCreated,
}: {
  owner: Owner;
  onClose: () => void;
  onCreated: (value: Credentials) => Promise<void>;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="editor-dialog"
      onCancel={onClose}
      aria-labelledby="reset-title"
    >
      <div className="dialog-heading">
        <h2 id="reset-title">
          {owner.has_access ? "Réinitialiser" : "Créer"} l’accès
        </h2>
      </div>
      <div className="form-fields">
        <p>
          {owner.first_name} {owner.last_name} — {owner.email}
        </p>
        <p className="muted">
          {owner.has_access
            ? "Un nouveau mot de passe temporaire remplacera le précédent et les sessions existantes seront invalidées."
            : "Un mot de passe temporaire sera généré pour une première connexion."}
        </p>
        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}
      </div>
      <div className="dialog-footer">
        <button className="button secondary" disabled={busy} onClick={onClose}>
          Annuler
        </button>
        <button
          className="button primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              const result = await api<{ credentials: Credentials }>(
                `owners/${owner.id}/access`,
                "POST",
                { reset: !!owner.has_access },
              );
              await onCreated(result.credentials);
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Création…" : "Générer les accès"}
        </button>
      </div>
    </dialog>
  );
}
