import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Organization, User } from "../api";
import { Icon } from "./ui";
import { BrandMark } from "./BrandMark";

export const sections: Record<
  string,
  { label: string; icon: string; items: [string, string][] }
> = {
  council: {
    label: "Conseil syndical",
    icon: "shield",
    items: [
      ["mandates", "Composition & mandats"],
      ["approvals", "Dépenses à valider"],
      ["accounts", "Consulter les comptes"],
      ["controls", "Contrôle indépendant"],
      ["history", "Historique du conseil"],
      ["settings", "Mode & règles"],
    ],
  },
  operations: {
    label: "Travaux & entretien",
    icon: "building",
    items: [
      ["works", "Travaux & sinistres"],
      ["deadlines", "Échéances & obligations"],
    ],
  },
  partners: {
    label: "Fournisseurs & contrats",
    icon: "people",
    items: [
      ["suppliers", "Fournisseurs"],
      ["contracts", "Contrats & préavis"],
      ["certificates", "Attestations"],
    ],
  },
  communication: {
    label: "Communication",
    icon: "message",
    items: [["notices", "Annonces partagées"]],
  },
  assemblies: {
    label: "Assemblées générales",
    icon: "calendar",
    items: [
      ["guide", "Guide d’utilisation"],
      ["preparation", "Préparer une AG"],
      ["presence", "Présences & droits de vote"],
      ["agenda", "Ordre du jour & simulations"],
      ["invitations", "Convocations & pièces"],
      ["session", "Séance & votes enregistrés"],
      ["minutes", "Procès-verbal & signatures"],
      ["notifications", "Notifications & délais"],
      ["decisions", "Décisions à mettre en œuvre"],
      ["history", "Registre & historique"],
    ],
  },
  tools: {
    label: "Outils",
    icon: "calculator",
    items: [
      ["vote", "Calcul de majorité"],
      ["split", "Répartir un montant"],
      ["installments", "Simuler un échéancier"],
    ],
  },
  documents: {
    label: "Documents",
    icon: "folder",
    items: [
      ["library", "Bibliothèque"],
      ["folders", "Dossiers"],
    ],
  },
  finance: {
    label: "Charges & finances",
    icon: "wallet",
    items: [
      ["keys", "Charges"],
      ["calls", "Appels de fonds"],
      ["expenses", "Dépenses"],
      ["treasury", "Trésorerie"],
      ["banks", "Comptes bancaires"],
      ["reconciliation", "Rapprochement bancaire"],
      ["funds", "Fonds & travaux votés"],
      ["funding", "Fonds & avances"],
      ["reminders", "Relances à valider"],
      ["reports", "Synthèses publiées"],
    ],
  },
  accounting: {
    label: "Gestion comptable",
    icon: "book",
    items: [
      ["accounts", "Plan comptable"],
      ["opening", "Reprise des soldes"],
      ["allocation", "Répartitions à vérifier"],
      ["lettering", "Affecter les règlements"],
      ["centers", "Analytique"],
      ["budgets", "Budgets"],
      ["templates", "Modèles d’écriture"],
      ["posting", "Saisie d’écritures"],
      ["entries", "Écritures"],
      ["closing", "Exercice & clôture"],
      ["corrections", "Corrections conservées"],
      ["mutations", "Changements de propriétaire"],
    ],
  },
  reporting: {
    label: "Rapports comptables",
    icon: "chart",
    items: [
      ["balance", "Balance générale"],
      ["auxiliary", "Comptes copropriétaires"],
      ["supplier-auxiliary", "Comptes fournisseurs"],
      ["ledger", "Grand livre"],
      ["journal", "Journal comptable"],
      ["income", "Compte de résultat"],
      ["sheet", "Bilan"],
      ["budget", "Budget / réalisé"],
      ["aged", "Échéances & impayés"],
      ["annexes", "Dossier comptable annuel"],
    ],
  },
  administration: {
    label: "Administration",
    icon: "shield",
    items: [
      ["organization", "Coordonnées & paramètres"],
      ["journals", "Journaux"],
      ["users", "Utilisateurs"],
      ["security", "Mon compte & sécurité"],
      ["backups", "Sauvegardes & reprise"],
      ["audit", "Historique"],
    ],
  },
};

export const navigationThemes = [
  { label: "Votre immeuble", pages: ["owners", "lots"] },
  {
    label: "Gestion financière",
    pages: ["finance", "accounting", "reporting"],
  },
  { label: "Entretien & prestataires", pages: ["operations", "partners"] },
  {
    label: "Vie de la copropriété",
    pages: ["council", "assemblies", "communication", "documents"],
  },
  { label: "Outils & paramètres", pages: ["tools", "administration"] },
];

export function navigationDestination(page: string, section?: string) {
  if (page === "operations" && section) {
    if (["suppliers", "contracts", "certificates"].includes(section))
      return { page: "partners", section };
    if (section === "notices") return { page: "communication", section };
    if (section === "reminders") return { page: "finance", section };
  }
  return { page, section };
}

export function Navigation({
  user,
  organization,
  page,
  section,
  ownersCount,
  compact,
  onToggleCompact,
  onNavigate,
  onLogout,
}: {
  user: User;
  organization: Organization;
  page: string;
  section: string;
  ownersCount: number;
  compact: boolean;
  onToggleCompact: () => void;
  onNavigate: (page: string, section?: string) => void;
  onLogout: () => Promise<void>;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [selector, setSelector] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [tooltip, setTooltip] = useState<{ label: string; top: number } | null>(
    null,
  );
  const [flyout, setFlyout] = useState<{ key: string; top: number } | null>(
    null,
  );
  const flyoutRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (flyout)
      flyoutRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }, [flyout?.key]);
  useEffect(() => {
    const close = () => {
      setFlyout(null);
      setTooltip(null);
    };
    window.addEventListener("resize", close);
    return () => window.removeEventListener("resize", close);
  }, []);
  function showHint(label: string, target: HTMLElement) {
    if (compact && window.matchMedia("(min-width: 641px)").matches && !flyout) {
      const box = target.getBoundingClientRect();
      setTooltip({ label, top: box.top + box.height / 2 });
    }
  }
  function toggleGroup(key: string, target: HTMLElement) {
    setTooltip(null);
    if (compact && window.matchMedia("(min-width: 641px)").matches) {
      const height = sections[key].items.length * 43 + 65;
      setFlyout((old) =>
        old?.key === key
          ? null
          : {
              key,
              top: Math.max(
                12,
                Math.min(
                  target.getBoundingClientRect().top,
                  window.innerHeight - height - 12,
                ),
              ),
            },
      );
    } else setExpanded((old) => ({ ...old, [key]: !old[key] }));
  }
  function navigate(next: string, child?: string) {
    onNavigate(next, child);
    setMobileOpen(false);
    setFlyout(null);
    setTooltip(null);
  }
  const selectorRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (section && sections[page]) setExpanded((e) => ({ ...e, [page]: true }));
  }, [page, section]);
  useEffect(() => {
    function dismiss(event: PointerEvent) {
      if (!selectorRef.current?.contains(event.target as Node))
        setSelector(false);
      if (
        !flyoutRef.current?.contains(event.target as Node) &&
        !(event.target as Element).closest(".nav-expand")
      )
        setFlyout(null);
    }
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);
  return (
    <>
      <button
        className={`mobile-menu-toggle icon-button ${mobileOpen ? "is-open" : ""}`}
        aria-label={mobileOpen ? "Fermer le menu" : "Ouvrir le menu"}
        aria-expanded={mobileOpen}
        aria-controls="main-sidebar"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        <Icon name={mobileOpen ? "close" : "menu"} />
      </button>
      {mobileOpen && (
        <button
          className="sidebar-overlay"
          aria-label="Fermer le menu"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        id="main-sidebar"
        className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setMobileOpen(false);
            setFlyout(null);
            setTooltip(null);
          }
        }}
      >
        <a
          className="brand"
          aria-label="Copro — Vue d’ensemble"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("overview");
          }}
        >
          <BrandMark />
          <span className="brand-name">
            Copro
            <span className="brand-dot">.</span>
          </span>
        </a>
        <div
          className="organization-picker"
          ref={selectorRef}
          onKeyDown={(e) => {
            if (e.key === "Escape") setSelector(false);
          }}
        >
          <button
            className="organization-trigger"
            aria-label={`Sélectionner la copropriété : ${organization.name}`}
            aria-expanded={selector}
            aria-controls="organization-options"
            onClick={() => setSelector(!selector)}
          >
            <span className="workspace-symbol">
              <Icon name="building" size={18} />
            </span>
            <span className="organization-name">
              <strong>{organization.name}</strong>
              <small>Copropriété</small>
            </span>
            <Icon name="chevron" size={16} />
          </button>
          {selector && (
            <div className="organization-options" id="organization-options">
              <p>VOTRE ESPACE</p>
              <button aria-current="true" onClick={() => setSelector(false)}>
                <span>{organization.name}</span>
                <Icon name="check" size={16} />
              </button>
              <small>Une seule structure est configurée actuellement.</small>
            </div>
          )}
        </div>
        <div
          className="sidebar-scroll"
          onScroll={() => {
            setTooltip(null);
            setFlyout(null);
          }}
        >
          <nav aria-label="Navigation principale">
            {[["overview", "dashboard", "Vue d’ensemble"]].map(
              ([key, icon, label]) => (
                <button
                  key={key}
                  className={`nav-item ${page === key ? "active" : ""}`}
                  aria-current={page === key ? "page" : undefined}
                  aria-label={label}
                  onMouseEnter={(e) => showHint(label, e.currentTarget)}
                  onMouseLeave={() => setTooltip(null)}
                  onFocus={(e) => showHint(label, e.currentTarget)}
                  onBlur={() => setTooltip(null)}
                  onClick={() => navigate(key)}
                >
                  <Icon name={icon} />
                  <span className="nav-text">{label}</span>
                  {key === "owners" && (
                    <span className="nav-count">{ownersCount}</span>
                  )}
                </button>
              ),
            )}
            {navigationThemes.map((theme, themeIndex) => (
              <div
                className="nav-theme"
                role="group"
                aria-labelledby={`theme-${themeIndex}`}
                key={theme.label}
              >
                <p className="nav-label" id={`theme-${themeIndex}`}>
                  {theme.label}
                </p>
                {theme.pages.map((key) => {
                  const group = sections[key];
                  if (!group) {
                    const label =
                      key === "owners" ? "Copropriétaires" : "Lots & tantièmes";
                    return (
                      <button
                        key={key}
                        className={`nav-item ${page === key ? "active" : ""}`}
                        aria-current={page === key ? "page" : undefined}
                        aria-label={label}
                        onMouseEnter={(e) => showHint(label, e.currentTarget)}
                        onMouseLeave={() => setTooltip(null)}
                        onFocus={(e) => showHint(label, e.currentTarget)}
                        onBlur={() => setTooltip(null)}
                        onClick={() => navigate(key)}
                      >
                        <Icon name={key === "owners" ? "people" : "lots"} />
                        <span className="nav-text">{label}</span>
                        {key === "owners" && (
                          <span className="nav-count">{ownersCount}</span>
                        )}
                      </button>
                    );
                  }
                  return (
                    <div
                      className={`nav-group ${page === key ? "current-group" : ""}`}
                      key={key}
                    >
                      <div className="nav-category-row">
                        <button
                          className={`nav-item nav-group-link ${page === key && !section ? "active" : ""}`}
                          aria-label={group.label}
                          aria-current={
                            page === key && !section ? "page" : undefined
                          }
                          onClick={() => navigate(key)}
                          onMouseEnter={(e) =>
                            showHint(group.label, e.currentTarget)
                          }
                          onMouseLeave={() => setTooltip(null)}
                          onFocus={(e) =>
                            showHint(group.label, e.currentTarget)
                          }
                          onBlur={() => setTooltip(null)}
                        >
                          <Icon name={group.icon} />
                          <span className="nav-text">{group.label}</span>
                        </button>
                        <button
                          className="nav-expand"
                          aria-label={`Afficher les sections : ${group.label}`}
                          aria-expanded={
                            compact && !mobileOpen
                              ? flyout?.key === key
                              : !!expanded[key]
                          }
                          aria-controls={`nav-${key}`}
                          onClick={(e) => toggleGroup(key, e.currentTarget)}
                        >
                          <span
                            className={`nav-chevron ${(compact && !mobileOpen ? flyout?.key === key : expanded[key]) ? "open" : ""}`}
                          >
                            <Icon name="chevron" size={15} />
                          </span>
                        </button>
                      </div>
                      {expanded[key] && (!compact || mobileOpen) && (
                        <div className="nav-subpages" id={`nav-${key}`}>
                          {group.items
                            .filter(
                              ([item]) => !["users", "backups"].includes(item) || user.is_admin,
                            )
                            .map(([item, label]) => (
                              <button
                                key={item}
                                className={`nav-subpage ${page === key && section === item ? "active" : ""}`}
                                aria-current={
                                  page === key && section === item
                                    ? "page"
                                    : undefined
                                }
                                onClick={() => navigate(key, item)}
                              >
                                {label}
                              </button>
                            ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </nav>
        </div>
        <div className="sidebar-bottom">
          <div className="profile">
            <span className="avatar">
              {user.username.slice(0, 2).toUpperCase()}
            </span>
            <div>
              <strong>{user.username}</strong>
              <small>Gestionnaire</small>
            </div>
            <button
              className="icon-button"
              aria-label="Se déconnecter"
              onClick={() => void onLogout()}
            >
              <Icon name="logout" size={18} />
            </button>
          </div>
        </div>
      </aside>
      <button
        className="sidebar-collapse"
        aria-label={compact ? "Agrandir le menu" : "Réduire le menu"}
        aria-expanded={!compact}
        aria-controls="main-sidebar"
        title={compact ? "Agrandir le menu" : "Réduire le menu"}
        onClick={() => {
          onToggleCompact();
          setFlyout(null);
          setTooltip(null);
        }}
      >
        <Icon name="chevron-left" size={17} />
      </button>
      {tooltip &&
        createPortal(
          <div
            className="nav-tooltip"
            aria-hidden="true"
            style={{ top: tooltip.top }}
          >
            {tooltip.label}
          </div>,
          document.body,
        )}
      {flyout &&
        createPortal(
          <div
            className="compact-flyout"
            ref={flyoutRef}
            id={`nav-${flyout.key}`}
            style={{ top: flyout.top }}
            onKeyDown={(e) => {
              if (e.key === "Escape") setFlyout(null);
            }}
          >
            <strong>{sections[flyout.key].label}</strong>
            <button
              className="flyout-intro"
              onClick={() => navigate(flyout.key)}
            >
              Présentation de la catégorie <Icon name="arrow" size={14} />
            </button>
            {sections[flyout.key].items
              .filter(([key]) => !["users", "backups"].includes(key) || user.is_admin)
              .map(([key, label]) => (
                <button
                  key={key}
                  aria-current={
                    page === flyout.key && section === key ? "page" : undefined
                  }
                  onClick={() => navigate(flyout.key, key)}
                >
                  {label}
                </button>
              ))}
          </div>,
          document.body,
        )}
    </>
  );
}
