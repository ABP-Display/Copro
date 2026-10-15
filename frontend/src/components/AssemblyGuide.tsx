import { useState } from "react";
import { Icon } from "./ui";
import {
  assemblyGuideSteps,
  assemblyGuideQuestions,
  assemblyGuideGlossary,
  assemblyGuideMemo,
  type GuidePage,
  type GuideLink,
} from "./assembly-guide-content";
import "./assembly-guide.css";

export function AssemblyGuide({
  onNavigate,
}: {
  onNavigate: (page: GuidePage, section?: string) => void;
}) {
  const [active, setActive] = useState(() => {
    try {
      const saved = Number(sessionStorage.getItem("copro.ag.guide.step") || 0);
      return Number.isInteger(saved) &&
        saved >= 0 &&
        saved < assemblyGuideSteps.length
        ? saved
        : 0;
    } catch {
      return 0;
    }
  });
  function selectStep(index: number, focus = false) {
    setActive(index);
    try {
      sessionStorage.setItem("copro.ag.guide.step", String(index));
    } catch {
      /* The guide also works when storage is disabled. */
    }
    if (focus)
      requestAnimationFrame(() =>
        document.getElementById(`ag-guide-step-${index}`)?.focus(),
      );
  }
  function downloadMemo() {
    const url = URL.createObjectURL(
      new Blob([assemblyGuideMemo()], { type: "text/markdown;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "Copro-guide-assemblee-generale.md";
    link.click();
    URL.revokeObjectURL(url);
  }
  const goTo = (link: GuideLink) => onNavigate(link.page, link.section);
  return (
    <div className="ag-guide">
      <section className="ag-guide-hero">
        <div>
          <span className="ag-guide-kicker">
            <Icon name="book" size={16} /> VOTRE PREMIÈRE AG
          </span>
          <h2>
            Une étape à la fois,
            <br />
            jusqu’au procès-verbal.
          </h2>
          <p>
            Retrouvez quoi préparer, où cliquer et ce qu’il faut vérifier avant
            de passer à la suite.
          </p>
        </div>
        <div className="ag-guide-tools">
          <span>6 étapes · à votre rythme</span>
          <button className="button" onClick={() => window.print()}>
            <Icon name="file" size={16} />
            Imprimer / PDF
          </button>
          <button className="ag-guide-download" onClick={downloadMemo}>
            Télécharger le mémo
          </button>
        </div>
      </section>

      <section
        className="ag-guide-before"
        aria-labelledby="ag-guide-before-title"
      >
        <div>
          <p className="eyebrow">AVANT DE COMMENCER</p>
          <h2 id="ag-guide-before-title">
            Réunissez les trois éléments du dossier
          </h2>
          <p>
            Le guide est consultable même si votre première AG n’est pas encore
            créée.
          </p>
        </div>
        <div className="ag-guide-prerequisites">
          <button onClick={() => onNavigate("lots")}>
            <Icon name="people" />
            <span>
              <strong>Les personnes et les lots</strong>Des propriétaires
              rattachés aux lots et des tantièmes vérifiés.
            </span>
            <Icon name="arrow" size={16} />
          </button>
          <button onClick={() => onNavigate("accounting", "budgets")}>
            <Icon name="wallet" />
            <span>
              <strong>Les comptes et le budget</strong>Les éléments à présenter
              pour les décisions de l’assemblée.
            </span>
            <Icon name="arrow" size={16} />
          </button>
          <button onClick={() => onNavigate("documents", "library")}>
            <Icon name="folder" />
            <span>
              <strong>Les pièces à joindre</strong>Des comptes, devis et projets
              de mandat ajoutés dans Documents.
            </span>
            <Icon name="arrow" size={16} />
          </button>
        </div>
      </section>

      <div className="ag-guide-layout">
        <nav className="ag-guide-index" aria-label="Étapes du guide AG">
          <p className="eyebrow">LE PARCOURS</p>
          <ol>
            {assemblyGuideSteps.map((step, index) => (
              <li key={step.id}>
                <button
                  aria-current={active === index ? "step" : undefined}
                  aria-controls={`ag-guide-panel-${step.id}`}
                  onClick={() => selectStep(index)}
                >
                  <span className="ag-guide-step-number">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span>
                    <small>{step.period}</small>
                    <strong>{step.title}</strong>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </nav>
        <div className="ag-guide-reading">
          {assemblyGuideSteps.map((step, index) => (
            <section
              className="ag-guide-step"
              key={step.id}
              id={`ag-guide-panel-${step.id}`}
              hidden={active !== index}
              aria-labelledby={`ag-guide-step-${index}`}
            >
              <header>
                <p className="eyebrow">
                  ÉTAPE {index + 1} / {assemblyGuideSteps.length} ·{" "}
                  {step.period}
                </p>
                <h2 tabIndex={-1} id={`ag-guide-step-${index}`}>
                  {step.title}
                </h2>
                <p>{step.introduction}</p>
              </header>
              <ol className="ag-guide-instructions">
                {step.instructions.map((instruction, i) => (
                  <li key={instruction.title}>
                    <span>{i + 1}</span>
                    <div>
                      <h3>{instruction.title}</h3>
                      <p>{instruction.text}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <aside className="ag-guide-remember">
                <Icon name="info" size={19} />
                <div>
                  <strong>À retenir</strong>
                  <p>{step.remember}</p>
                </div>
              </aside>
              <div className="ag-guide-ready">
                <h3>Vous pouvez continuer lorsque…</h3>
                <ul>
                  {step.ready.map((item) => (
                    <li key={item}>
                      <Icon name="check" size={16} />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="ag-guide-shortcuts">
                <span>Ouvrir la bonne rubrique</span>
                {step.links.map((link) => (
                  <button
                    key={`${link.page}-${link.section}`}
                    onClick={() => goTo(link)}
                  >
                    {link.label}
                    <Icon name="arrow" size={14} />
                  </button>
                ))}
              </div>
            </section>
          ))}
          <div className="ag-guide-pagination">
            <button
              className="button secondary"
              disabled={active === 0}
              onClick={() => selectStep(active - 1, true)}
            >
              <Icon name="chevron-left" size={16} />
              Étape précédente
            </button>
            <span aria-live="polite">
              {active + 1} sur {assemblyGuideSteps.length}
            </span>
            {active < assemblyGuideSteps.length - 1 ? (
              <button
                className="button primary"
                onClick={() => selectStep(active + 1, true)}
              >
                Étape suivante
                <Icon name="arrow" size={16} />
              </button>
            ) : (
              <button
                className="button primary"
                onClick={() => onNavigate("assemblies", "preparation")}
              >
                Ouvrir mes AG
                <Icon name="arrow" size={16} />
              </button>
            )}
          </div>
          <p className="ag-guide-context">
            Dans les rubriques de travail, sélectionnez toujours la bonne
            réunion dans la liste « Assemblée » en haut de la page. Ce guide
            explique les étapes ; il ne valide aucune AG.
          </p>
        </div>
      </div>

      <section className="ag-guide-bottom">
        <div className="ag-guide-faq">
          <p className="eyebrow">POUR SE DÉBLOQUER</p>
          <h2>Les questions fréquentes</h2>
          {assemblyGuideQuestions.map((item) => (
            <details key={item.question}>
              <summary>{item.question}</summary>
              <p>{item.answer}</p>
            </details>
          ))}
        </div>
        <div className="ag-guide-glossary">
          <p className="eyebrow">LES MOTS UTILES</p>
          <h2>Un petit lexique</h2>
          <dl>
            {assemblyGuideGlossary.map((item) => (
              <div key={item.term}>
                <dt>{item.term}</dt>
                <dd>{item.definition}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>
      <p className="ag-guide-scope">
        <Icon name="info" size={17} />
        <span>
          Copro. prépare les documents et conserve les preuves. Les signatures
          et notifications se réalisent à l’extérieur de l’application.
          Appuyez-vous sur les dates affichées et vérifiez les modèles et
          modalités adaptés à votre copropriété.
        </span>
      </p>
    </div>
  );
}
