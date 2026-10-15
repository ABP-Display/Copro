import { useState } from "react";
import { BrandMark } from "./BrandMark";
import { Icon } from "./ui";
import "./presentation.css";

const pagesOnly = import.meta.env.MODE === "pages";
const home = pagesOnly ? import.meta.env.BASE_URL : "/presentation";
const loginUrl = pagesOnly
  ? "https://copro.ydoxide.fr/connexion"
  : "/connexion";
const repository = "https://github.com/abp-display/Copro";
const modules = [
  {
    icon: "shield",
    title: "Des accès protégés, des données récupérables",
    tag: "Disponible",
    text: "Activez la double authentification et gardez vos codes de secours. Sauvegardez ensemble la base et les pièces dans une archive chiffrée, puis vérifiez leur restauration sur une copie isolée.",
    detail: "TOTP · codes de secours · restauration vérifiée",
  },
  {
    icon: "people",
    title: "Un conseil syndical avec des rôles précis",
    tag: "Parcours disponible",
    text: "Attribuez les mandats, laissez le trésorier préparer les dépenses et recueillez les avis motivés du conseil. Le syndic comptabilise ; le contrôleur conserve un rapport indépendant.",
    detail: "Mandats datés · validations · contrôle des comptes",
  },
  {
    icon: "calendar",
    title: "Des dossiers suivis dans la durée",
    tag: "Première version",
    text: "Rassemblez les travaux, les sinistres et les devis. Retrouvez les fournisseurs, leurs contrats, préavis et attestations avec les dates à vérifier.",
    detail: "Fournisseurs · contrats · devis · échéances",
  },
  {
    icon: "info",
    title: "Les points à suivre, dès l’accueil",
    tag: "Disponible",
    text: "Consultez les dates proches, les factures restant à régler et les soldes débiteurs à vérifier. Préparez une relance modifiable avec ses preuves.",
    detail: "Métriques · brouillons · validation humaine",
  },
  {
    icon: "people",
    title: "Votre collectif, au même endroit",
    tag: "Disponible",
    text: "Copropriétaires, lots et tantièmes. Retrouvez les bonnes informations et préparez les accès de chaque membre.",
    detail: "Annuaire · lots · accès par courriel",
  },
  {
    icon: "wallet",
    title: "Des comptes que l’on peut suivre",
    tag: "Disponible",
    text: "Reprenez les soldes, rapprochez la banque et préparez les cinq annexes annuelles avec leurs contrôles. Vérifiez les décisions du fonds travaux et restituez les avances versées, y compris après une vente.",
    detail: "Annexes comparées · fonds / PPT · avances et restitutions",
  },
  {
    icon: "vote",
    title: "Une AG guidée, jusqu’au procès-verbal",
    tag: "Parcours guidé",
    text: "Préparez les convocations, vérifiez les cinq annexes jointes à l’approbation des comptes, enregistrez les votes et produisez le PV. Conservez les preuves des signatures et notifications réalisées à l’extérieur.",
    detail: "Votes conservés · PV · suivi des notifications",
  },
  {
    icon: "folder",
    title: "Des documents qui se retrouvent",
    tag: "Disponible",
    text: "Classez les pièces, conservez leurs versions et choisissez les documents à partager. Les téléchargements passent par les contrôles d’accès.",
    detail: "PDF et images · versions · archivage",
  },
  {
    icon: "panel",
    title: "Un espace pour les copropriétaires",
    tag: "Première version",
    text: "Un portail de lecture pour retrouver son compte personnel, les lots, les documents et les annonces publiées, depuis un ordinateur ou un téléphone.",
    detail: "Partage explicite · données privées protégées",
  },
  {
    icon: "calculator",
    title: "Les bons calculs, sans ressaisie",
    tag: "Disponible",
    text: "Vérifiez une majorité, répartissez un montant au centime ou simulez un échéancier. Les outils restent séparés des écritures comptables.",
    detail: "Annuaire réutilisé · saisie libre possible",
  },
];
const roadmap = [
  [
    "Comptabilité à approfondir",
    "Validation métier des modèles, aides et prêts collectifs, mode simplifié et formats bancaires supplémentaires. Les annexes contrôlées et les restitutions d’avances sont disponibles.",
  ],
  [
    "AG et services connectés",
    "Visio, vote direct par les membres, signature qualifiée et courrier recommandé connecté. Le parcours papier et preuves est disponible.",
  ],
  [
    "Obligations et échéances",
    "Un calendrier contextualisé, des sources vérifiables et des explications sur les obligations de l’immeuble.",
  ],
  [
    "Suivi des travaux à approfondir",
    "Avancement détaillé, affectation des paiements et lien complet entre dossiers et comptabilité.",
  ],
  [
    "Communication à compléter",
    "Envoi SMTP, rappels programmés et suivi des échanges. Les brouillons et leur validation sont déjà disponibles.",
  ],
  [
    "Indicateurs à approfondir",
    "Règles de suivi personnalisables et tableaux de bord plus détaillés. Les analyses actuelles utilisent les données saisies, sans moteur IA.",
  ],
];
const setup = {
  docker: `git clone https://github.com/abp-display/Copro.git copro\ncd copro\ncp .env.example .env\n# Renseigner les trois secrets avant de démarrer\ndocker compose up -d --build\ndocker compose ps`,
  native: `# Backend : Python 3.12, environnement virtuel activé\ncd backend\npip install -r requirements.txt\n# Définir DJANGO_SECRET_KEY et ADMIN_PASSWORD\npython manage.py migrate\npython manage.py createsuperuser\npython manage.py runserver 127.0.0.1:8000\n\n# Dans un second terminal : Node.js 22\ncd frontend\nnpm ci\nnpm run dev`,
};
export function Presentation() {
  const [method, setMethod] = useState<"docker" | "native">("docker");
  return (
    <div className="copro-presentation">
      <a href="#presentation-content" className="presentation-skip">
        Aller au contenu
      </a>
      <header className="presentation-header">
        <a className="presentation-brand" href={home}>
          <BrandMark />
          <span>Copro.</span>
        </a>
        <nav aria-label="Présentation du projet">
          <a href="#fonctionnalites">Fonctionnalités</a>
          <a href="#utilisation">Utilisation</a>
          <a href="#installation">Installation</a>
        </nav>
        <a className="presentation-access" href={loginUrl}>
          Ouvrir mon espace <Icon name="arrow" size={16} />
        </a>
      </header>
      <main id="presentation-content">
        <section className="presentation-hero presentation-container">
          <div className="presentation-hero-copy">
            <p className="presentation-kicker">
              <span /> UN PROJET LIBRE, POUR VOTRE IMMEUBLE
            </p>
            <h1>
              Votre copropriété.
              <br />
              Votre collectif.
              <br />
              <em>Votre façon de gérer.</em>
            </h1>
            <p className="presentation-lead">
              Copro. rassemble les comptes, les documents et la préparation de
              vos assemblées dans un espace clair. Pensé pour avancer ensemble,
              même sans être spécialiste.
            </p>
            <div className="presentation-cta">
              <a className="presentation-primary" href={loginUrl}>
                Accéder à Copro. <Icon name="arrow" size={18} />
              </a>
              <a className="presentation-secondary" href="#installation">
                Installer le projet
              </a>
            </div>
            <p className="presentation-hero-note">
              Open source · Auto-hébergement · Projet en développement
            </p>
          </div>
          <div
            className="presentation-demo"
            aria-label="Exemple illustratif, données fictives"
          >
            <div className="demo-top">
              <span className="demo-dot" />
              <span>Résidence des Tilleuls</span>
              <span className="demo-label">EXEMPLE</span>
            </div>
            <div className="demo-body">
              <p className="presentation-kicker">VOTRE ESPACE COMMUN</p>
              <h2>
                Tout se prépare
                <br />
                ensemble.
              </h2>
              <div className="demo-stats">
                <div>
                  <strong>12</strong>
                  <span>copropriétaires</span>
                </div>
                <div>
                  <strong>24</strong>
                  <span>lots</span>
                </div>
                <div>
                  <strong>1</strong>
                  <span>collectif</span>
                </div>
              </div>
              <div className="demo-task">
                <span className="demo-icon">
                  <Icon name="book" />
                </span>
                <div>
                  <strong>Suivre les comptes</strong>
                  <span>Appels de fonds et dépenses réunis</span>
                </div>
                <Icon name="check" size={17} />
              </div>
              <div className="demo-task">
                <span className="demo-icon">
                  <Icon name="calendar" />
                </span>
                <div>
                  <strong>Préparer la prochaine AG</strong>
                  <span>Ordre du jour et résolutions</span>
                </div>
                <Icon name="arrow" size={17} />
              </div>
              <div className="demo-task">
                <span className="demo-icon">
                  <Icon name="folder" />
                </span>
                <div>
                  <strong>Partager les bonnes pièces</strong>
                  <span>Documents choisis par le gestionnaire</span>
                </div>
                <Icon name="arrow" size={17} />
              </div>
              <p className="demo-caption">
                Illustration du projet, sans données de votre copropriété.
              </p>
            </div>
          </div>
        </section>
        <section
          className="presentation-principles"
          aria-label="Les principes du projet"
        >
          <div className="presentation-container">
            <p>
              <Icon name="check" size={19} />
              <span>Des informations lisibles</span>
            </p>
            <p>
              <Icon name="people" size={19} />
              <span>Une gestion partagée</span>
            </p>
            <p>
              <Icon name="shield" size={19} />
              <span>Des accès contrôlés</span>
            </p>
            <p>
              <Icon name="building" size={19} />
              <span>Une installation chez vous</span>
            </p>
          </div>
        </section>
        <section
          id="fonctionnalites"
          className="presentation-section presentation-container"
        >
          <div className="presentation-section-heading">
            <p className="presentation-kicker">
              CE QUE VOUS POUVEZ FAIRE AUJOURD’HUI
            </p>
            <h2>
              Un espace commun.
              <br />
              Des tâches plus simples.
            </h2>
            <p>
              Les fonctions ci-dessous sont présentes dans la version actuelle.
              Les modules en première version restent à compléter.
            </p>
          </div>
          <div className="presentation-modules">
            {modules.map((m) => (
              <article key={m.title}>
                <div className="module-top">
                  <span className="module-icon">
                    <Icon name={m.icon} size={25} />
                  </span>
                  <span
                    className={`module-status ${m.tag === "Disponible" ? "available" : "partial"}`}
                  >
                    {m.tag}
                  </span>
                </div>
                <h3>{m.title}</h3>
                <p>{m.text}</p>
                <div className="module-detail">{m.detail}</div>
              </article>
            ))}
          </div>
        </section>
        <section id="utilisation" className="presentation-how">
          <div className="presentation-container">
            <div className="presentation-section-heading">
              <p className="presentation-kicker">PRENDRE SES REPÈRES</p>
              <h2>
                Du premier lot
                <br />à la prochaine assemblée.
              </h2>
              <p>
                Un parcours progressif pour construire votre espace de gestion.
              </p>
            </div>
            <div className="presentation-steps">
              {[
                [
                  "Décrire votre immeuble",
                  "Renseignez la copropriété, ses membres et ses lots. Vérifiez les tantièmes et les clés de charges.",
                ],
                [
                  "Organiser votre gestion",
                  "Créez l’exercice, préparez les appels de fonds, saisissez les dépenses et contrôlez les rapports.",
                ],
                [
                  "Préparer et partager",
                  "Classez les documents, préparez les résolutions et publiez les informations utiles aux membres.",
                ],
              ].map(([title, text], i) => (
                <article key={title}>
                  <span>0{i + 1}</span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
            <div className="presentation-role-note">
              <Icon name="info" />
              <p>
                <strong>À chacun son espace.</strong> Les gestionnaires
                préparent et modifient les données. Les copropriétaires
                consultent les informations globales et les documents publiés.
                Les gestionnaires enregistrent les votes de séance ; les membres
                retrouvent les résumés de décisions publiés.
              </p>
            </div>
          </div>
        </section>
        <section
          id="installation"
          className="presentation-section presentation-container presentation-install"
        >
          <div>
            <p className="presentation-kicker">VOTRE INSTANCE, VOS DONNÉES</p>
            <h2>
              Installer Copro.
              <br />à votre rythme.
            </h2>
            <p>
              La voie Docker réunit React, Django et PostgreSQL. Le code est
              disponible sous licence GPL-3.0, sans abonnement logiciel imposé
              par ce projet.
            </p>
            <ul>
              <li>
                Docker et Docker Compose, ou Docker Desktop en mode Linux.
              </li>
              <li>
                Trois secrets distincts à renseigner dans le fichier{" "}
                <code>.env</code>.
              </li>
              <li>Un navigateur pour utiliser votre espace.</li>
              <li>Un outil de sauvegarde chiffrée base et documents, avec restauration de contrôle.</li>
              <li>Python 3.12 ou supérieur pour cet outil ; programmation et copie hors site à configurer sur le serveur.</li>
              <li>Une application d’authentification et des codes de secours pour protéger les accès.</li>
            </ul>
            <a
              className="presentation-text-link"
              href={`${repository}/blob/master/README.md`}
              target="_blank"
              rel="noreferrer"
            >
              Lire le guide complet <Icon name="arrow" size={16} />
            </a>
            <p className="presentation-install-note">
              L’hébergement et sa maintenance restent à votre charge. Une
              instance gère actuellement une seule copropriété.
            </p>
          </div>
          <div className="presentation-code">
            <div
              className="install-options"
              aria-label="Méthode d’installation"
            >
              <button
                aria-pressed={method === "docker"}
                onClick={() => setMethod("docker")}
              >
                Docker · recommandé
              </button>
              <button
                aria-pressed={method === "native"}
                onClick={() => setMethod("native")}
              >
                Développement local
              </button>
            </div>
            <pre>
              <code>{setup[method]}</code>
            </pre>
            <p>
              {method === "docker" ? (
                <>
                  Après démarrage : <a href={loginUrl}>ouvrir l’espace</a> sur
                  le port 8081. L’identifiant initial est <code>admin</code> ;
                  son mot de passe est celui défini dans{" "}
                  <code>ADMIN_PASSWORD</code>.
                </>
              ) : (
                "Le développement natif utilise SQLite par défaut. Python 3.12 et Node.js 22 sont requis ; ce parcours n’a pas été validé sous Windows."
              )}
            </p>
          </div>
        </section>
        <section id="evolutions" className="presentation-roadmap">
          <div className="presentation-container">
            <div className="presentation-section-heading">
              <p className="presentation-kicker">LE PROJET CONTINUE</p>
              <h2>
                Une direction claire.
                <br />
                Un périmètre transparent.
              </h2>
              <p>
                Copro. vise une gestion plus complète du quotidien d’un syndic
                bénévole. Ces évolutions sont prévues, elles ne sont pas encore
                livrées et n’ont pas de date garantie.
              </p>
            </div>
            <div className="roadmap-grid">
              {roadmap.map(([title, text], i) => (
                <article key={title}>
                  <span>0{i + 1}</span>
                  <div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                    <small>À développer</small>
                  </div>
                </article>
              ))}
            </div>
            <p className="roadmap-note">
              Le développement des fonctionnalités de Copro. est progressif. Le
              projet actuel ne propose pas de certification de conformité, de
              migration automatique des données ni d’IA entraînée pour le
              syndic.
            </p>
          </div>
        </section>
        <section className="presentation-section presentation-container presentation-faq">
          <div>
            <p className="presentation-kicker">AVANT DE COMMENCER</p>
            <h2>
              Quelques réponses
              <br />
              pour avancer.
            </h2>
          </div>
          <div>
            {[
              [
                "Est-ce un service hébergé ?",
                "Cette page présente un logiciel à installer. Il n’existe pas d’inscription publique ni de service d’hébergement fourni par ce projet. Les accès sont créés par le gestionnaire de l’instance.",
              ],
              [
                "Peut-on déjà conduire les parcours comptables et une AG ?",
                "Oui, les parcours comptables et l’AG menée par le gestionnaire sont disponibles. Les signatures et notifications se font à l’extérieur, avec leurs preuves conservées. Les cas particuliers, modèles réglementaires et services connectés restent à approfondir.",
              ],
              [
                "L’IA gère-t-elle déjà la copropriété ?",
                "Non. Aucune fonction IA n’est actuellement intégrée. L’objectif envisagé est une assistance qui propose des actions avec leurs sources, puis attend une validation humaine.",
              ],
              [
                "Les membres voient-ils toutes les données ?",
                "Non. Le portail de lecture expose les informations globales et les documents publiés. Les coordonnées et soldes individuels des autres propriétaires restent privés.",
              ],
              [
                "Comment contribuer ?",
                "Consultez le dépôt, signalez un problème reproductible ou proposez une amélioration. Conservez les notices de licence et testez vos modifications avant de les partager.",
              ],
            ].map(([title, text]) => (
              <details key={title}>
                <summary>
                  {title}
                  <Icon name="plus" size={18} />
                </summary>
                <p>{text}</p>
              </details>
            ))}
          </div>
        </section>
        <section className="presentation-final presentation-container">
          <BrandMark />
          <h2>
            Un immeuble se gère mieux
            <br />
            quand on avance ensemble.
          </h2>
          <div className="presentation-cta">
            <a className="presentation-primary" href={loginUrl}>
              Ouvrir mon espace <Icon name="arrow" size={18} />
            </a>
            <a
              className="presentation-secondary"
              href={repository}
              target="_blank"
              rel="noreferrer"
            >
              Voir le code source
            </a>
          </div>
        </section>
      </main>
      <footer className="presentation-footer presentation-container">
        <a className="presentation-brand" href={home}>
          <BrandMark />
          <span>Copro.</span>
        </a>
        <p>Projet libre · GPL-3.0 · React, Django et PostgreSQL</p>
        <a href={repository} target="_blank" rel="noreferrer">
          Code et documentation <Icon name="arrow" size={15} />
        </a>
      </footer>
    </div>
  );
}
