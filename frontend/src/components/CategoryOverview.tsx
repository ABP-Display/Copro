import { Icon } from "./ui";
import { sections } from "./Navigation";

export const categoryHelp: Record<
  string,
  { description: string; advice: string; items: Record<string, string> }
> = {
  council: {
    description:
      "Organisez les responsabilités, examinez les pièces et conservez les avis du conseil ainsi que le contrôle indépendant des comptes.",
    advice:
      "Enregistrez les désignations avec leurs pièces et leurs dates, puis préparez et contrôlez les dépenses. Les avis du conseil et l’exécution par le syndic restent distincts.",
    items: {
      mandates:
        "Retrouvez les membres, leurs responsabilités et leurs mandats. L’administrateur principal attribue les accès datés depuis une décision documentée.",
      approvals:
        "Soumettez une facture, un devis ou une préparation. Les membres du conseil donnent des avis motivés avant l’exécution par le syndic.",
      accounts:
        "Examinez les écritures, factures, banques, budgets, contrats et pièces en lecture seule.",
      controls:
        "Le contrôleur indépendant prépare une checklist et conserve son rapport avec les pièces et l’état des comptes examinés.",
      history:
        "Consultez les mandats, modifications des règles, demandes, avis et rapports avec leur date et leur auteur.",
      settings:
        "Choisissez le mode bénévole ou coopératif et documentez la règle de contrôle des dépenses, son seuil et le nombre d’avis requis.",
    },
  },
  operations: {
    description:
      "Suivez les travaux, sinistres et échéances de votre immeuble avec leurs pièces et décisions.",
    advice:
      "Les alertes se basent sur vos données. Relisez les preuves et vérifiez les échéances avant de valider ; aucun courrier ni paiement n’est déclenché automatiquement.",
    items: {
      works:
        "Rassemblez devis, documents, budget et décision d’AG. Comparez les montants avant de retenir un devis.",
      deadlines:
        "Ajoutez une date et une source vérifiée pour chaque obligation applicable à votre immeuble.",
    },
  },
  partners: {
    description:
      "Retrouvez les entreprises, leurs contrats et les pièces à tenir à jour.",
    advice:
      "Créez le fournisseur, puis ses contrats et attestations. Les devis et factures peuvent ensuite reprendre cet annuaire.",
    items: {
      suppliers:
        "Centralisez les contacts et métiers des entreprises, puis choisissez-les dans les devis et factures.",
      contracts:
        "Suivez les dates, coûts déclarés et préavis des contrats avant une éventuelle reconduction.",
      certificates:
        "Conservez les pièces fournisseurs et les dates de validité à vérifier.",
    },
  },
  communication: {
    description:
      "Partagez les informations utiles avec les copropriétaires depuis leur portail.",
    advice:
      "Rédigez d’abord un brouillon, puis publiez le message après relecture. Les annonces sont partagées avec tous les copropriétaires connectés.",
    items: {
      notices:
        "Publiez une annonce, retirez-la pour la corriger et archivez les messages devenus inutiles.",
    },
  },
  assemblies: {
    description:
      "Conduisez une assemblée, de l’ordre du jour aux notifications, avec des pièces et votes conservés à chaque étape.",
    advice:
      "Préparez les textes, copropriétaires et pièces, puis figez les convocations. Enregistrez les preuves d’envoi, les présences et votes, faites signer le PV et suivez ses notifications.",
    items: {
      guide:
        "Apprenez à conduire votre première AG en six étapes : quoi préparer, où cliquer et comment vérifier le dossier avant de continuer.",
      preparation:
        "Créez une assemblée et retrouvez les étapes à préparer. Imprimez un dossier de travail regroupant les informations de réunion et les résolutions.",
      presence:
        "Choisissez les copropriétaires depuis l’annuaire, reprenez leurs tantièmes et renseignez leur présence. La liste enregistrée sert de point de départ aux simulations.",
      agenda:
        "Classez les résolutions par numéro, précisez leur texte et leur majorité, puis enregistrez une simulation. Un second vote est distinct du premier, qui reste conservé.",
      invitations:
        "Imprimez les convocations, formulaires et pouvoirs. Conservez les versions des pièces et les preuves de notification avec contrôle du délai.",
      session:
        "Ouvrez la séance, renseignez le bureau élu et enregistrez chaque vote individuel. Les corrections et seconds tours restent dans l’historique.",
      minutes:
        "Produisez un PV depuis les votes, puis rattachez le PV et la feuille de présence signés. Partagez ensuite un résumé des décisions.",
      notifications:
        "Retrouvez les opposants et défaillants, conservez les preuves de notification et suivez les délais de contestation.",
      decisions:
        "Reprenez un budget adopté ou créez des appels en brouillon à partir d’une décision inscrite au PV signé.",
      history:
        "Consultez les étapes et corrections conservées, puis exportez les données du dossier de l’AG.",
    },
  },
  tools: {
    description:
      "Vérifiez vos calculs avant de préparer un vote, un appel de fonds ou un budget. Ces outils ne modifient pas la comptabilité.",
    advice:
      "Utilisez le calcul de majorité pour le cas général français, avec les droits de vote corrigés. Les outils de répartition et d’échéancier conservent exactement le total au centime.",
    items: {
      vote: "Distinguez voix exprimées, voix de tous les copropriétaires et nombre de copropriétaires. Le résultat explique le seuil et signale les passerelles vers un second vote.",
      split:
        "Répartissez un montant entre plusieurs parts selon leurs tantièmes ou poids, avec un arrondi contrôlé au centime.",
      installments:
        "Divisez une somme en plusieurs échéances égales. Les éventuels centimes restants sont distribués sur les premières échéances.",
    },
  },
  documents: {
    description:
      "Conservez les documents de la copropriété au même endroit, puis choisissez ceux à partager avec les copropriétaires.",
    advice:
      "Les nouveaux documents sont réservés aux gestionnaires. Le bouton Partager les rend accessibles à tous les copropriétaires connectés ; les anciennes versions restent réservées aux gestionnaires.",
    items: {
      library:
        "Déposez des PDF ou images, retrouvez un document, ajoutez une version et gérez son partage. L’archivage masque un document sans effacer son historique.",
      folders:
        "Créez et renommez des dossiers pour organiser les contrats, factures, comptes rendus et autres documents.",
    },
  },
  finance: {
    description:
      "Suivez l’argent de votre copropriété : les sommes demandées, les dépenses et les règlements reçus.",
    advice:
      "Pour commencer, créez un exercice (la période de vos comptes), puis vos catégories de charges avant de préparer un appel de fonds.",
    items: {
      keys: "Classez les dépenses, par exemple l’entretien ou l’ascenseur, et choisissez comment les partager entre les lots.",
      calls:
        "Préparez les sommes à demander aux copropriétaires. Vérifiez la répartition avant de valider : elle sera ensuite conservée dans l’historique.",
      expenses:
        "Enregistrez les factures fournisseurs et leurs règlements pour suivre ce que la copropriété doit payer.",
      treasury:
        "Consultez les mouvements bancaires enregistrés et saisissez les versements reçus des copropriétaires.",
      banks:
        "Distinguez vos comptes bancaires, leur solde comptable et les transferts déjà effectués. Choisissez le compte utilisé pour chaque règlement.",
      reconciliation:
        "Importez un relevé, associez ses mouvements aux écritures et vérifiez les soldes de départ et de fin.",
      funds:
        "Suivez les cotisations et versements par lot, affectez les fonds aux travaux votés et soldez les opérations terminées.",
      reminders:
        "Préparez une relance depuis un compte débiteur, vérifiez ses mouvements sources et validez le texte avant utilisation.",
      reports:
        "Publiez une synthèse globale que les copropriétaires pourront consulter dans leur espace en lecture seule.",
    },
  },
  accounting: {
    description:
      "Organisez les comptes et enregistrez les opérations qui servent à calculer vos états financiers.",
    advice:
      "Les appels de fonds, factures et règlements créent leurs écritures automatiquement. La saisie manuelle est réservée aux autres opérations : ne saisissez pas une seconde fois la même dépense.",
    items: {
      accounts:
        "Un compte sert à classer une opération : banque, fournisseurs, charges… Complétez le plan français avant de saisir des opérations détaillées.",
      opening:
        "Reprenez la balance du précédent syndic avec les soldes individuels et les fonds attachés aux lots.",
      allocation:
        "Vérifiez les clés des dépenses historiques avant de figer leur répartition.",
      lettering:
        "Associez un règlement à une dette précise, même si elle vient d’un exercice précédent.",
      closing:
        "Régularisez les charges approuvées, contrôlez les comptes et reportez les soldes dans l’exercice suivant.",
      corrections:
        "Corrigez un appel, une facture ou un règlement par une écriture inverse. L’opération originale reste dans l’historique.",
      mutations:
        "Enregistrez la date et la notification d’une vente. Vérifiez les réattributions d’appels et de régularisation avant de valider.",
      centers:
        "Regroupez les opérations par bâtiment, équipement ou projet, sans changer leurs comptes. C’est le suivi analytique.",
      budgets:
        "Prévoyez les charges et les produits pour l’année, par compte, puis comparez ces prévisions aux opérations réelles.",
      templates:
        "Enregistrez une structure d’écriture réutilisable pour éviter de ressaisir les mêmes lignes à chaque opération.",
      posting:
        "Saisissez une opération particulière en indiquant les comptes concernés. Le total au débit doit égaler le total au crédit.",
      entries:
        "Consultez les écritures validées. Corrigez une écriture manuelle par une écriture inverse, appelée contrepassation, en conservant l’original.",
    },
  },
  reporting: {
    description:
      "Comprenez vos comptes à partir des opérations enregistrées, puis exportez ou imprimez les résultats.",
    advice:
      "Choisissez un exercice et une période. Les filtres limitent les données affichées ; le budget reste annuel et le bilan est calculé à la date de fin.",
    items: {
      balance:
        "Comparez les débits, crédits et soldes de chaque compte. Utile pour une première vérification de l’ensemble des comptes.",
      aged: "Distinguez les échéances futures, les retards et les crédits à affecter avant de préparer une relance.",
      annexes:
        "Relisez les cinq états calculés et les décomptes individuels, puis imprimez le dossier ou exportez les écritures.",
      auxiliary:
        "Consultez les montants dus ou les avances de chaque copropriétaire : solde avant la période, mouvements et solde final. Ces données individuelles restent privées.",
      "supplier-auxiliary":
        "Retrouvez les dettes et règlements par fournisseur identifié, avec solde avant la période et solde final. Les anciennes écritures sans fournisseur restent signalées séparément.",
      ledger:
        "Retrouvez tous les mouvements d’un compte avec le solde avant la période et son évolution après chaque opération.",
      journal:
        "Relisez les opérations dans l’ordre des dates, avec leurs références et les comptes concernés.",
      income:
        "Comparez les charges et les produits enregistrés pour comprendre le résultat de la période.",
      sheet:
        "Consultez la synthèse des comptes à une date donnée. Cet état ne remplace pas les annexes réglementaires de copropriété.",
      budget:
        "Repérez les écarts entre ce qui était prévu pour l’année et les opérations réellement enregistrées.",
    },
  },
  administration: {
    description:
      "Personnalisez votre copropriété, ses règles de saisie et les accès des personnes qui la gèrent.",
    advice:
      "Commencez par le nom et les coordonnées. Réservez le rôle Gestionnaire aux personnes autorisées à modifier les données ; les autres comptes restent en lecture seule.",
    items: {
      organization:
        "Renseignez le nom et les coordonnées de la copropriété, puis ajustez les paramètres comptables proposés dans les formulaires.",
      journals:
        "Organisez les écritures par famille d’opérations, par exemple achats ou banque, et choisissez le journal proposé par défaut.",
      users:
        "Activez ou désactivez un accès et choisissez le rôle lecture ou gestionnaire. Cette section est réservée à l’administrateur principal.",
      audit:
        "Consultez les opérations comptables et de configuration enregistrées, avec leur date et leur auteur.",
    },
  },
};

export function CategoryOverview({
  category,
  isAdmin,
  onNavigate,
}: {
  category: string;
  isAdmin: boolean;
  onNavigate: (section: string) => void;
}) {
  const group = sections[category];
  const help = categoryHelp[category];
  return (
    <section className="category-overview">
      <div className="category-intro">
        <span className="category-symbol">
          <Icon name={group.icon} size={28} />
        </span>
        <div>
          <p className="eyebrow">POUR BIEN COMMENCER</p>
          <h2>Bien démarrer</h2>
          <p>{help.advice}</p>
        </div>
      </div>
      <div className="category-grid">
        {group.items
          .filter(([key]) => key !== "users" || isAdmin)
          .map(([key, label], index) => (
            <button
              key={key}
              className="category-card"
              onClick={() => onNavigate(key)}
            >
              <span className="category-card-number">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3>{label}</h3>
              <p>{help.items[key]}</p>
              <span className="category-card-link">
                Ouvrir la section <Icon name="arrow" size={16} />
              </span>
            </button>
          ))}
      </div>
    </section>
  );
}
