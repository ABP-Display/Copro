export type GuidePage =
  | "assemblies"
  | "owners"
  | "lots"
  | "accounting"
  | "documents";
export type GuideLink = { label: string; page: GuidePage; section?: string };
export type GuideStep = {
  id: string;
  period: string;
  title: string;
  introduction: string;
  instructions: { title: string; text: string }[];
  ready: string[];
  remember: string;
  links: GuideLink[];
};

export const assemblyGuideSteps: GuideStep[] = [
  {
    id: "prepare",
    period: "Avant l’AG",
    title: "Créer l’AG et ses résolutions",
    introduction:
      "Commencez par décrire la réunion et ce que les copropriétaires devront décider.",
    instructions: [
      {
        title: "Créer la réunion",
        text: "Dans « Préparer une AG », cliquez sur le bouton du même nom. Renseignez un titre facile à reconnaître, la date, l’heure et le lieu, puis enregistrez.",
      },
      {
        title: "Ajouter les décisions à discuter",
        text: "Dans la bibliothèque de résolutions types, choisissez par exemple l’approbation des comptes ou le budget. Dans « Ordre du jour & simulations », modifiez chaque résolution, remplacez les textes entre crochets et vérifiez la majorité indiquée.",
      },
      {
        title: "Préparer les votants",
        text: "Dans « Présences & droits de vote », chargez les copropriétaires, vérifiez leurs lots et tantièmes, puis cliquez sur « Enregistrer les présences ». Incluez aussi les personnes qui seront absentes. Corrigez un propriétaire sans lot ou des tantièmes nuls avant de continuer.",
      },
      {
        title: "Rassembler les documents",
        text: "Ajoutez les comptes, budgets, devis ou projets de mandat dans « Documents ». Revenez dans « Préparer une AG » pour choisir leurs versions et remplir les adresses de notification, l’organisateur, le retour des formulaires et les modalités de consultation des justificatifs. Enregistrez les vérifications et pièces.",
      },
    ],
    ready: [
      "La date, le lieu et les textes sont complets.",
      "Tous les votants et leurs tantièmes sont vérifiés.",
      "Les pièces demandées sont ajoutées et rattachées aux résolutions.",
    ],
    remember:
      "Une résolution correspond à une décision précise. Les exemples de la bibliothèque sont à personnaliser pour votre immeuble.",
    links: [
      { label: "Préparer une AG", page: "assemblies", section: "preparation" },
      {
        label: "Compléter l’ordre du jour",
        page: "assemblies",
        section: "agenda",
      },
      {
        label: "Vérifier les votants",
        page: "assemblies",
        section: "presence",
      },
      { label: "Ajouter les documents", page: "documents", section: "library" },
    ],
  },
  {
    id: "invite",
    period: "Avant l’AG",
    title: "Préparer et justifier les convocations",
    introduction:
      "Une fois le dossier relu, conservez la version qui sera transmise à chaque copropriétaire.",
    instructions: [
      {
        title: "Relire puis figer le dossier",
        text: "Dans « Préparer une AG », corrigez les points signalés et contrôlez la date limite affichée. Cliquez sur « Figer le dossier de convocation » lorsque tout est prêt. Les textes, destinataires, droits et versions des pièces sont alors conservés.",
      },
      {
        title: "Préparer les exemplaires",
        text: "Dans « Convocations & pièces », affichez la convocation, le formulaire de correspondance et le pouvoir. Utilisez « Imprimer ce document » pour imprimer ou enregistrer chaque document en PDF, puis joignez les fichiers listés dans le dossier.",
      },
      {
        title: "Réaliser la notification",
        text: "Utilisez votre mode de notification à l’extérieur de Copro. Le bouton « Préparer un courriel » ouvre votre messagerie : ajoutez les pièces et vérifiez le contenu avant tout envoi. Le courriel préparé ne vaut pas, à lui seul, notification recommandée.",
      },
      {
        title: "Conserver la preuve pour chacun",
        text: "Ajoutez les preuves dans « Documents », puis revenez à « Convocations & pièces ». Pour chaque destinataire, cliquez sur « Enregistrer la preuve » et recopiez la modalité, les dates réelles d’envoi et de prise d’effet, la référence et la version du justificatif.",
      },
    ],
    ready: [
      "Le dossier de convocation est figé.",
      "Chaque copropriétaire a une preuve enregistrée.",
      "Les dates de notification respectent les contrôles affichés.",
    ],
    remember:
      "Après avoir figé le dossier, une modification de l’ordre du jour nécessite de préparer une nouvelle AG et sa convocation. Relisez les textes avant cette étape.",
    links: [
      {
        label: "Vérifier le dossier",
        page: "assemblies",
        section: "preparation",
      },
      {
        label: "Ouvrir les convocations",
        page: "assemblies",
        section: "invitations",
      },
      { label: "Ajouter les preuves", page: "documents", section: "library" },
    ],
  },
  {
    id: "attendance",
    period: "Le jour de l’AG",
    title: "Accueillir les participants et ouvrir la séance",
    introduction:
      "Indiquez qui participe et comment, puis renseignez le bureau élu par l’assemblée.",
    instructions: [
      {
        title: "Renseigner les présences réelles",
        text: "Dans « Présences & droits de vote », choisissez pour chacun : présent, représenté, par correspondance ou absent. Pour une personne représentée, sélectionnez le mandataire ou saisissez son nom et son domicile, puis rattachez le pouvoir signé et vérifiez son éligibilité.",
      },
      {
        title: "Recopier les formulaires reçus",
        text: "Pour un vote par correspondance, renseignez la date de réception, choisissez la pièce signée et recopiez le choix de chaque résolution. Si la personne vient ou se fait représenter, mettez à jour son mode de participation.",
      },
      {
        title: "Enregistrer la liste",
        text: "Cliquez sur « Enregistrer les présences et pièces ». Imprimez la feuille de présence pour la faire émarger et certifier. Les totaux vous aident à vérifier les voix présentes, représentées et par correspondance.",
      },
      {
        title: "Ouvrir la séance",
        text: "Dans « Séance & votes enregistrés », indiquez le président présent et éligible, le secrétaire et les scrutateurs éventuels. Confirmez les vérifications et l’élection du bureau, puis cliquez sur « Ouvrir la séance ». Cette action est disponible à compter de la date de la réunion.",
      },
    ],
    ready: [
      "Les présences, pouvoirs et formulaires sont enregistrés.",
      "Le bureau élu est renseigné.",
      "Le bandeau affiche « Séance ouverte ».",
    ],
    remember:
      "Enregistrez à nouveau la présence lorsqu’une personne arrive ou part. Les votes déjà enregistrés conservent la liste utilisée au moment du vote.",
    links: [
      {
        label: "Renseigner les présences",
        page: "assemblies",
        section: "presence",
      },
      { label: "Ouvrir la séance", page: "assemblies", section: "session" },
    ],
  },
  {
    id: "votes",
    period: "Le jour de l’AG",
    title: "Enregistrer chaque vote",
    introduction:
      "Le gestionnaire recopie les choix exprimés ; Copro. conserve le résultat et explique son calcul.",
    instructions: [
      {
        title: "Traiter une résolution à la fois",
        text: "Dans « Séance & votes enregistrés », relisez le texte, puis cliquez sur « Saisir et enregistrer les votes ». Choisissez pour, contre ou abstention pour chaque présent ou représenté concerné. Les choix par correspondance proviennent des formulaires enregistrés.",
      },
      {
        title: "Conserver les éléments de séance",
        text: "Si la résolution est amendée, saisissez son texte complet dans le champ prévu. Notez les incidents et réserves utiles, puis cliquez sur « Calculer et enregistrer ce vote ». Relisez les voix et le résultat affichés.",
      },
      {
        title: "Faire un second vote s’il est proposé",
        text: "Lorsqu’une passerelle est possible, un bouton permet d’enregistrer un second vote distinct. Recopiez les nouveaux choix. Le premier tour reste conservé et un seuil de passerelle ne vaut pas adoption de la résolution.",
      },
      {
        title: "Corriger une erreur avant le PV",
        text: "Saisissez un motif et utilisez « Corriger le tour » concerné, puis enregistrez le vote corrigé. Si deux tours existent, corrigez d’abord le second. Les anciens votes restent dans l’historique.",
      },
    ],
    ready: [
      "Chaque résolution possède un vote enregistré.",
      "Les résultats, textes amendés et réserves ont été relus.",
      "Les corrections nécessaires sont terminées.",
    ],
    remember:
      "Les simulations de « Ordre du jour & simulations » servent à préparer les calculs. Seuls les votes enregistrés dans la séance alimentent le procès-verbal.",
    links: [
      {
        label: "Enregistrer les votes de séance",
        page: "assemblies",
        section: "session",
      },
    ],
  },
  {
    id: "minutes",
    period: "Après les votes",
    title: "Préparer puis faire signer le PV",
    introduction:
      "Le procès-verbal reprend les décisions conservées pendant la séance.",
    instructions: [
      {
        title: "Préparer le document final",
        text: "Au bas de « Séance & votes enregistrés », complétez les remarques générales, confirmez la relecture et cliquez sur « Préparer le procès-verbal ». Un vote doit avoir été enregistré pour chaque résolution.",
      },
      {
        title: "Relire et imprimer",
        text: "Dans « Procès-verbal & signatures », vérifiez le bureau, les textes retenus, les résultats, les noms et les réserves. Utilisez « Imprimer ce document ». Faites également signer et certifier la feuille de présence.",
      },
      {
        title: "Conserver les documents signés",
        text: "Faites signer les documents à l’extérieur de Copro., puis ajoutez les scans dans « Documents ». Revenez au PV, choisissez la version du PV signé et celle de la feuille de présence, indiquez la date réelle de signature et cliquez sur « Rattacher les documents signés ».",
      },
      {
        title: "Partager le résumé si vous le souhaitez",
        text: "Une fois le PV signé, vous pouvez publier le résumé des décisions dans l’espace copropriétaire. Ce résumé partage les textes et résultats globaux ; les adresses, preuves et votes individuels restent dans le dossier de gestion.",
      },
    ],
    ready: [
      "Le PV et la présence ont été relus et signés.",
      "Les deux versions signées et la date réelle sont enregistrées.",
      "Le bandeau affiche « PV signé ».",
    ],
    remember:
      "Avant signature, vous pouvez revenir aux votes en conservant le projet et un motif. Après signature, le PV ne se réécrit plus : conservez un additif dans les documents si nécessaire.",
    links: [
      {
        label: "Préparer le PV depuis la séance",
        page: "assemblies",
        section: "session",
      },
      {
        label: "Consulter le PV et ses signatures",
        page: "assemblies",
        section: "minutes",
      },
      {
        label: "Ajouter les scans signés",
        page: "documents",
        section: "library",
      },
    ],
  },
  {
    id: "finish",
    period: "Après l’AG",
    title: "Notifier, appliquer les décisions et archiver",
    introduction:
      "Terminez le dossier en conservant les preuves et en reprenant les décisions utiles à la gestion.",
    instructions: [
      {
        title: "Notifier les destinataires indiqués",
        text: "Dans « Notifications & délais », consultez les copropriétaires à notifier et les dates affichées. Réalisez les notifications à l’extérieur de Copro. avec le PV signé et ses annexes, puis ajoutez les justificatifs dans « Documents ».",
      },
      {
        title: "Enregistrer les preuves et suivre les recours",
        text: "Pour chaque destinataire, cliquez sur « Enregistrer la preuve » et recopiez les dates réelles, la référence et la version du justificatif. Les délais de contestation apparaissent ensuite. La rubrique de recours permet de suivre une procédure déjà engagée, avec sa pièce et son état.",
      },
      {
        title: "Reprendre les décisions adoptées",
        text: "Dans « Décisions à mettre en œuvre », reprenez une régularisation, des postes budgétaires, des appels ou un mandat depuis le vote adopté et le PV signé. Vérifiez les paramètres d’après le texte voté. Les appels créés restent en brouillon, à contrôler et publier dans les finances.",
      },
      {
        title: "Clore et retrouver le dossier",
        text: "Dans « Notifications & délais », confirmez les pièces et notifications, puis cliquez sur « Clore et inscrire l’AG au registre ». Retrouvez ensuite le dossier en cochant « Inclure les archives ». « Registre & historique » permet de consulter les étapes et d’exporter leurs données.",
      },
    ],
    ready: [
      "Les preuves de notification nécessaires sont enregistrées.",
      "Les décisions à mettre en œuvre ont été examinées.",
      "Le dossier clos reste consultable dans les archives.",
    ],
    remember:
      "L’export JSON conserve les données du dossier, sans les fichiers joints. Gardez une sauvegarde de la base et des documents ensemble.",
    links: [
      {
        label: "Suivre les notifications",
        page: "assemblies",
        section: "notifications",
      },
      {
        label: "Appliquer les décisions",
        page: "assemblies",
        section: "decisions",
      },
      {
        label: "Consulter le registre",
        page: "assemblies",
        section: "history",
      },
    ],
  },
];

export const assemblyGuideQuestions = [
  {
    question: "Puis-je lire ce guide avant de créer une AG ?",
    answer:
      "Oui. Il est accessible sans sélectionner d’assemblée. Quand vous ouvrez une rubrique depuis le guide, choisissez l’AG concernée dans la liste en haut de la page.",
  },
  {
    question: "Pourquoi un bouton est-il bloqué ?",
    answer:
      "Lisez le point signalé dans la page. Il manque souvent une pièce, une présence enregistrée, une preuve de convocation ou un vote ; la date de séance ou l’état du dossier peuvent aussi bloquer l’action. Revenez à l’étape précédente pour compléter le dossier.",
  },
  {
    question: "J’ai préparé un courriel : est-il envoyé ?",
    answer:
      "Le bouton ouvre votre messagerie. Vous devez ajouter les pièces, relire et envoyer vous-même. Pour la notification, utilisez la modalité adaptée et conservez sa preuve dans Copro.",
  },
  {
    question: "Puis-je essayer un vote avant la réunion ?",
    answer:
      "Oui, dans « Ordre du jour & simulations » pendant la préparation, ou dans les outils. Pour le PV, recopiez ensuite les choix réels dans « Séance & votes enregistrés ».",
  },
  {
    question: "Quelle différence entre archiver un brouillon et clore l’AG ?",
    answer:
      "« Archiver » dans l’en-tête range une préparation. Pour terminer une AG tenue, suivez le parcours jusqu’au PV signé et aux preuves de notification, puis utilisez « Clore et inscrire l’AG au registre ».",
  },
  {
    question: "Où sont passées les anciennes AG ?",
    answer:
      "Dans une rubrique de l’AG, cochez « Inclure les archives », puis choisissez la réunion dans la liste « Assemblée ». Les pièces et l’historique restent consultables.",
  },
];

export const assemblyGuideGlossary = [
  {
    term: "AG",
    definition:
      "Assemblée générale : la réunion où les copropriétaires prennent les décisions inscrites à l’ordre du jour.",
  },
  {
    term: "Résolution",
    definition:
      "Le texte d’une décision soumise au vote, par exemple l’adoption d’un budget.",
  },
  {
    term: "Tantièmes",
    definition:
      "Les parts associées aux lots, utilisées pour certaines répartitions de charges et certains votes.",
  },
  {
    term: "Pouvoir",
    definition:
      "Le document par lequel un copropriétaire se fait représenter par un mandataire.",
  },
  {
    term: "Majorité",
    definition:
      "La règle de calcul choisie pour décider si une résolution est adoptée.",
  },
  {
    term: "PV",
    definition:
      "Procès-verbal : le document qui conserve les décisions et les résultats des votes de la réunion.",
  },
];

export function assemblyGuideMemo() {
  return (
    [
      "# Ma première AG dans Copro. — guide pas à pas",
      "Choisissez l’AG concernée dans la liste en haut de chaque rubrique. Les envois et signatures sont réalisés hors de Copro., puis leurs preuves sont rattachées au dossier.",
      ...assemblyGuideSteps.flatMap((step, index) => [
        `## ${index + 1}. ${step.title} — ${step.period}`,
        step.introduction,
        ...step.instructions.map(
          (instruction, i) =>
            `${i + 1}. **${instruction.title}** : ${instruction.text}`,
        ),
        "### Avant de continuer",
        ...step.ready.map((item) => `- [ ] ${item}`),
        `À retenir : ${step.remember}`,
      ]),
      "## Questions fréquentes",
      ...assemblyGuideQuestions.flatMap((item) => [
        `### ${item.question}`,
        item.answer,
      ]),
      "## Les mots utiles",
      ...assemblyGuideGlossary.map(
        (item) => `- **${item.term}** : ${item.definition}`,
      ),
      "Les dates et contrôles affichés suivent les données saisies. Les modèles et modalités sont à vérifier pour la situation de votre copropriété. Ce guide explique l’application ; les services de visio, signature qualifiée et recommandé connecté ne sont pas intégrés.",
    ].join("\n\n") + "\n"
  );
}
