import { useEffect, useRef, useState } from "react";
import { api, newOperationId } from "../api";
import type { ToolData as Row } from "./Tools";
import { majorityLabels } from "./Tools";
import { Icon } from "./ui";
import "./assembly-workflow.css";

const phases: Record<string, string> = {
  draft: "Préparation",
  convened: "Convocations",
  session: "Séance ouverte",
  minutes: "PV à signer",
  signed: "PV signé",
  closed: "AG archivée",
};
const presenceNames: Record<string, string> = {
  absent: "Absent",
  present: "Présent",
  represented: "Représenté",
  correspondence: "Par correspondance",
};
const choiceNames: Record<string, string> = {
  for: "Pour",
  against: "Contre",
  abstain: "Abstention",
};
const personKey = (r: Row) =>
  r.owner_id ? `owner:${r.owner_id}` : `free:${r.name.toLocaleLowerCase()}`;
const dateLabel = (day: string) =>
  day
    ? new Date(day.length === 10 ? day + "T12:00:00" : day).toLocaleDateString(
        "fr-FR",
      )
    : "—";
const today = () => new Date().toLocaleDateString("en-CA");

export function AssemblyWorkflow({
  meeting,
  section,
  onChanged,
  onTemplate,
}: {
  meeting: Row;
  section: string;
  onChanged: () => Promise<void>;
  onTemplate: (template: Row) => Promise<void>;
}) {
  const [data, setData] = useState<Row | null>(null);
  const [context, setContext] = useState<Row>({
    versions: [],
    templates: [],
    keys: [],
    years: [],
    accounts: [],
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [printView, setPrintView] = useState("invitation");
  const [delivery, setDelivery] = useState<Row | null>(null);
  const [vote, setVote] = useState<Row | null>(null);
  const [execution, setExecution] = useState<Row | null>(null);
  useEffect(() => {
    let active = true;
    setData(null);
    Promise.all([
      api<Row>(`ag/meetings/${meeting.id}/workflow`),
      api<Row>("ag/workflow-context"),
    ])
      .then(([workflow, options]) => {
        if (active) {
          setData(workflow);
          setContext(options);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [meeting.id, meeting.resolutions.length, meeting.roster]);
  async function act(action: string, body: Row = {}) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api<Row>(
        `ag/meetings/${meeting.id}/workflow/${action}`,
        "POST",
        { ...body, request_id: newOperationId() },
      );
      setData(result);
      await onChanged();
      setMessage("Enregistrement conservé dans l’historique de l’AG.");
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  if (!data)
    return (
      <section className="panel">
        {error ? (
          <p role="alert">{error}</p>
        ) : (
          <p role="status">Chargement du parcours AG…</p>
        )}
      </section>
    );
  const draft = data.phase === "draft";
  const packet = data.packet?.electors ? data.packet : data.preview;
  const electors: Row[] = data.packet?.electors || [];
  const recorded: Row[] = data.votes || [];
  const invitations = data.deliveries.filter(
    (d: Row) => d.kind === "invitation",
  );
  const notificationSet = new Set(
    data.deliveries
      .filter((d: Row) => d.kind === "minutes")
      .map((d: Row) => d.elector),
  );
  const requirements: string[] = data.minutes.required_notifications || [];
  const canEditPresence = ["convened", "session"].includes(data.phase);
  return (
    <div className="ag-workflow">
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="ag-success" role="status">
          {message}
        </div>
      )}
      <section className="panel ag-progress">
        <div>
          <p className="eyebrow">PARCOURS D’ASSEMBLÉE</p>
          <h2>{phases[data.phase]}</h2>
          <p>
            Les pièces, destinataires et votes restent liés au dossier de cette
            AG.
          </p>
        </div>
        <ol>
          {["draft", "convened", "session", "minutes", "signed", "closed"].map(
            (p, i) => (
              <li key={p} aria-current={p === data.phase ? "step" : undefined}>
                <span>{i + 1}</span>
                {phases[p]}
              </li>
            ),
          )}
        </ol>
        {packet?.two_owners && (
          <p className="ag-help">
            Syndicat à deux copropriétaires : les votes utilisent les règles de
            l’article 41-16, sans réduction des voix de l’article 22.
          </p>
        )}
      </section>

      {section === "preparation" && draft && (
        <>
          <section className="panel">
            <h2>Résolutions types à personnaliser</h2>
            <p>
              Choisissez un point, puis complétez les champs entre crochets dans
              l’ordre du jour. Vérifiez la majorité selon la décision précise.
            </p>
            <div className="ag-templates">
              {context.templates.map((t: Row) => (
                <button
                  className="ag-template"
                  disabled={busy}
                  key={t.id}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await onTemplate(t);
                    } catch (e) {
                      setError((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <Icon name="plus" size={16} />
                  <span>
                    {t.title}
                    <small>{majorityLabels[t.majority]}</small>
                  </span>
                </button>
              ))}
            </div>
          </section>
          <Preparation
            key={`${meeting.id}-${meeting.resolutions.length}`}
            meeting={meeting}
            config={data.config}
            context={context}
            busy={busy}
            onSave={(config) => act("configure", { config })}
          />
          <section className="panel">
            <h2>Vérifier avant de figer</h2>
            <p>
              Complétez l’ordre du jour, le corps électoral et les pièces. Après
              cette étape, les textes et droits convoqués sont conservés.
            </p>
            {data.checks.map((c: string) => (
              <p className="alert" key={c}>
                {c}
              </p>
            ))}
            {packet && (
              <p className="ag-success">
                {packet.electors.length} copropriétaires ·{" "}
                {packet.resolutions.length} résolutions. Dernière prise d’effet
                possible de la convocation :{" "}
                {dateLabel(packet.latest_notification)}. Prévoyez le temps
                d’acheminement.
              </p>
            )}
            {packet?.account_year && (
              <p className="ag-help">
                Comptes de {packet.account_year.name} : approbation annuelle à
                prévoir avant le{" "}
                {dateLabel(packet.account_year.approval_deadline)}.
                {new Date(packet.scheduled_at).toLocaleDateString("en-CA") >
                packet.account_year.approval_deadline
                  ? " La date prévue dépasse cette échéance ; vérifiez la situation."
                  : ""}
              </p>
            )}
            <button
              className="button primary"
              disabled={busy || !packet}
              onClick={() => void act("freeze")}
            >
              Figer le dossier de convocation
            </button>
          </section>
        </>
      )}
      {section === "preparation" && !draft && (
        <section className="panel">
          <h2>Le dossier convoqué est conservé</h2>
          <p>
            Continuez dans Convocations, Présences, Séance puis Procès-verbal.
            Une modification de l’ordre du jour nécessite une nouvelle AG.
          </p>
          <p className="muted">Empreinte du dossier : {data.digest}</p>
        </section>
      )}

      {section === "invitations" && (
        <>
          <section className="panel">
            <h2>Convocations et preuves de notification</h2>
            <p>
              Préparez les documents ci-dessous, joignez les versions listées,
              puis réalisez l’envoi recommandé, qualifié ou la remise contre
              émargement. Le courriel préparé est un accompagnement ; il ne vaut
              pas notification recommandée.
            </p>
            {draft ? (
              <p className="ag-help">
                Terminez la préparation et figez le dossier pour accéder aux
                convocations individuelles.
              </p>
            ) : (
              <>
                <p className="ag-help">
                  Dernière prise d’effet :{" "}
                  <strong>
                    {dateLabel(data.deadlines.latest_notification)}
                  </strong>{" "}
                  · Retour des votes par correspondance :{" "}
                  <strong>
                    {dateLabel(data.deadlines.correspondence_deadline)}
                  </strong>
                  .
                </p>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Copropriétaire</th>
                        <th>Lots / voix</th>
                        <th>Notification</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {electors.map((r) => {
                        const sent = invitations.find(
                          (d: Row) => d.elector === r.elector,
                        );
                        return (
                          <tr key={r.elector}>
                            <td>{r.name}</td>
                            <td>
                              {r.lots.join(", ") || "Saisie libre"} · {r.shares}
                            </td>
                            <td>
                              {sent
                                ? `${dateLabel(sent.effective_on)} · ${sent.reference}`
                                : "À notifier"}
                            </td>
                            <td>
                              <div className="ag-row-actions">
                                {r.email && (
                                  <a
                                    className="button secondary"
                                    href={`mailto:${encodeURIComponent(r.email)}?subject=${encodeURIComponent(`Convocation — ${meeting.title}`)}&body=${encodeURIComponent(`Bonjour ${r.name},\n\nVous êtes convoqué(e) le ${dateLabel(packet.scheduled_at)} à ${packet.location}. Veuillez trouver les pièces jointes, l’ordre du jour et le formulaire de vote.\n\nJoignez les fichiers du dossier avant envoi. La notification légale doit être réalisée séparément selon la modalité retenue.\n${packet.organizer}`)}`}
                                  >
                                    Préparer un courriel
                                  </a>
                                )}
                                {!sent && data.phase === "convened" && (
                                  <button
                                    className="button secondary"
                                    onClick={() =>
                                      setDelivery({
                                        kind: "invitation",
                                        elector: r.elector,
                                        name: r.name,
                                      })
                                    }
                                  >
                                    Enregistrer la preuve
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
          {packet && (
            <PrintDocuments
              packet={packet}
              minutes={data.minutes}
              participants={data.participants}
              view={printView}
              onView={setPrintView}
            />
          )}
        </>
      )}

      {section === "presence" && !draft && (
        <>
          <Participants
            key={JSON.stringify(data.participants)}
            packet={data.packet}
            participants={data.participants}
            versions={context.versions}
            disabled={busy || !canEditPresence}
            onSave={(participants) => act("participants", { participants })}
          />
          <PrintDocuments
            packet={data.packet}
            minutes={data.minutes}
            participants={data.participants}
            view="attendance"
            fixed
            onView={setPrintView}
          />
        </>
      )}

      {section === "session" && (
        <>
          {draft && (
            <section className="panel">
              <p>
                Préparez l’AG et enregistrez les convocations avant d’ouvrir la
                séance.
              </p>
            </section>
          )}
          {data.phase === "convened" && (
            <section className="panel">
              <h2>Ouvrir la séance</h2>
              <p>
                {invitations.length}/{electors.length} convocations justifiées.
                Enregistrez les présences et pouvoirs avant de choisir le bureau
                élu.
              </p>
              <ActionForm
                busy={busy}
                submit="Ouvrir la séance"
                onSubmit={(body) => act("start", body)}
              >
                <label>
                  Président de séance
                  <select name="president" required>
                    <option value="">Choisir une personne présente</option>
                    {electors
                      .filter(
                        (r) =>
                          data.participants.find(
                            (p: Row) => p.elector === r.elector,
                          )?.attendance === "present",
                      )
                      .map((r) => (
                        <option value={r.elector} key={r.elector}>
                          {r.name}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Secrétaire
                  <input
                    name="secretary"
                    list="ag-owner-names"
                    required
                    maxLength={200}
                  />
                </label>
                <label>
                  Scrutateurs (si élus)
                  <input
                    name="scrutineers"
                    list="ag-owner-names"
                    maxLength={500}
                  />
                </label>
                <datalist id="ag-owner-names">
                  {electors.map((r) => (
                    <option key={r.elector} value={r.name} />
                  ))}
                </datalist>
                <Check
                  name="president_eligible"
                  label="Le président est éligible au regard de l’article 22, et n’est pas le syndic ou une personne interdite."
                />
                <Check
                  name="bureau_elected"
                  label="L’assemblée a élu ce bureau de séance."
                />
                <Check
                  name="attendance_checked"
                  label="Les présences, pouvoirs et formulaires ont été contrôlés."
                />
              </ActionForm>
            </section>
          )}
          {data.bureau.president && (
            <section className="panel">
              <h2>Bureau de séance</h2>
              <p>
                Président : {data.bureau.president} · Secrétaire :{" "}
                {data.bureau.secretary} · Scrutateurs :{" "}
                {data.bureau.scrutineers || "Aucun"}
              </p>
            </section>
          )}
          {data.packet.resolutions?.map((r: Row) => {
            const votes = recorded.filter(
              (v) => v.resolution === r.id && !v.voided,
            );
            const last = votes.at(-1);
            return (
              <section className="panel" key={r.id}>
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">
                      RÉSOLUTION {r.position} · {r.key_name}
                    </p>
                    <h2>{r.title}</h2>
                    <p>{majorityLabels[r.majority]}</p>
                  </div>
                  {last && (
                    <span className="subtle-badge">
                      {last.result.adopted ? "Adoptée" : "Non adoptée"}
                    </span>
                  )}
                </div>
                <p className="ag-text">{r.text}</p>
                {votes.map((v) => (
                  <div className="ag-vote-result" key={v.id}>
                    <h3>Tour {v.tour}</h3>
                    <p>
                      {v.result.for_votes} pour · {v.result.against_votes}{" "}
                      contre · {v.result.abstain_votes} abstention
                    </p>
                    <p>{v.result.explanation}</p>
                    {v.amendment && <p>Texte amendé : {v.amendment}</p>}
                    {v.incident && <p>Incident / réserves : {v.incident}</p>}
                    {data.phase === "session" && (
                      <ActionForm
                        busy={busy}
                        submit={`Corriger le tour ${v.tour}`}
                        onSubmit={(body) =>
                          act("void-vote", { ...body, vote: v.id })
                        }
                      >
                        <label>
                          Motif de correction
                          <input name="reason" required maxLength={500} />
                        </label>
                      </ActionForm>
                    )}
                  </div>
                ))}
                {data.phase === "session" &&
                  (!last || (last.tour === 1 && last.result.bridge)) && (
                    <button
                      className="button primary"
                      disabled={busy}
                      onClick={() =>
                        setVote({
                          resolution: r,
                          tour: last ? 2 : 1,
                          initial: last,
                        })
                      }
                    >
                      {last
                        ? `Enregistrer le second vote (${last.result.bridge})`
                        : "Saisir et enregistrer les votes"}
                    </button>
                  )}
              </section>
            );
          })}
          {data.phase === "session" && (
            <section className="panel">
              <h2>Terminer les votes et préparer le PV</h2>
              <p>
                Les votes de chaque résolution doivent être enregistrés. Les
                changements de présence sont conservés avec chaque tour. Relisez
                les textes, les résultats, les opposants et les réserves avant
                cette étape.
              </p>
              <ActionForm
                busy={busy}
                submit="Préparer le procès-verbal"
                onSubmit={(body) => act("minutes", body)}
              >
                <label>
                  Remarques générales de séance
                  <textarea name="remarks" maxLength={5000} />
                </label>
                <Check
                  name="reviewed"
                  label="Les résultats et mentions de séance ont été relus."
                />
              </ActionForm>
            </section>
          )}
        </>
      )}

      {section === "minutes" && (
        <>
          {!data.minutes.resolutions ? (
            <section className="panel">
              <h2>Un PV issu des votes enregistrés</h2>
              <p>
                Terminez les votes dans Séance, puis préparez le procès-verbal.
              </p>
            </section>
          ) : (
            <>
              <PrintDocuments
                packet={data.packet}
                minutes={data.minutes}
                participants={data.participants}
                view="minutes"
                fixed
                onView={setPrintView}
              />
              {data.phase === "minutes" && (
                <section className="panel">
                  <h2>Conserver le PV et la présence signés</h2>
                  <p>
                    Imprimez le PV et la feuille de présence. Faites signer par
                    le président, le secrétaire et les scrutateurs, puis ajoutez
                    les scans dans Documents. Délai de signature :{" "}
                    {dateLabel(data.deadlines.signature_deadline)}. Enregistrez
                    la date réelle, même en cas de retard.
                  </p>
                  <ActionForm
                    busy={busy}
                    submit="Rattacher les documents signés"
                    onSubmit={(body) => act("sign", body)}
                  >
                    <VersionSelect
                      name="signed_proof"
                      label="PV signé"
                      versions={context.versions}
                    />
                    <VersionSelect
                      name="attendance_proof"
                      label="Feuille de présence signée / certifiée"
                      versions={context.versions}
                    />
                    <label>
                      Date de signature
                      <input
                        name="signed_on"
                        type="date"
                        required
                        max={today()}
                      />
                    </label>
                    <Check
                      name="signatures_checked"
                      label="Toutes les signatures requises et l’annexe de présence ont été vérifiées."
                    />
                  </ActionForm>
                  <details>
                    <summary>Corriger avant signature</summary>
                    <ActionForm
                      busy={busy}
                      submit="Revenir aux votes en conservant le projet de PV"
                      onSubmit={(body) => act("revise-minutes", body)}
                    >
                      <label>
                        Motif
                        <input name="reason" required maxLength={500} />
                      </label>
                    </ActionForm>
                  </details>
                </section>
              )}
              {["signed", "closed"].includes(data.phase) && (
                <section className="panel">
                  <h2>Résumé partagé dans l’espace copropriétaire</h2>
                  <p>
                    Partagez les textes et résultats globaux des décisions. Les
                    adresses, preuves et votes individuels restent dans le
                    dossier de gestion.
                  </p>
                  <button
                    className="button secondary"
                    disabled={busy}
                    onClick={() =>
                      void act("publish", { published: !data.published })
                    }
                  >
                    {data.published
                      ? "Retirer le résumé partagé"
                      : "Publier le résumé des décisions"}
                  </button>
                </section>
              )}
            </>
          )}
        </>
      )}

      {section === "notifications" && (
        <section className="panel">
          <h2>Notifier et suivre les délais</h2>
          <p>
            Les opposants et défaillants sont déterminés depuis les votes
            enregistrés. Joignez le PV signé et ses annexes à la notification
            réalisée hors de l’application. Délai ordinaire :{" "}
            {dateLabel(data.deadlines.notification_deadline)}.
          </p>
          {data.minutes.signed_on && (
            <p className="ag-success">
              PV signé le {dateLabel(data.minutes.signed_on)}.
              {data.minutes.signed_on > data.deadlines.signature_deadline
                ? " Signature enregistrée après le délai : vérifiez les conséquences."
                : ""}
            </p>
          )}
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Destinataire</th>
                  <th>Suivi</th>
                  <th>Contestation jusqu’au</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {requirements.map((key) => {
                  const recipient = electors.find((r) => r.elector === key);
                  const sent = data.deliveries.find(
                    (d: Row) => d.kind === "minutes" && d.elector === key,
                  );
                  return (
                    <tr key={key}>
                      <td>{recipient?.name}</td>
                      <td>
                        {sent
                          ? `${dateLabel(sent.effective_on)} · ${sent.reference}${sent.sent_on > data.deadlines.notification_deadline ? " · Envoi tardif" : ""}`
                          : "À notifier"}
                      </td>
                      <td>
                        {sent
                          ? dateLabel(sent.appeal_until)
                          : "Après notification effective"}
                      </td>
                      <td>
                        {!sent && data.phase === "signed" && (
                          <button
                            className="button secondary"
                            onClick={() =>
                              setDelivery({
                                kind: "minutes",
                                elector: key,
                                name: recipient?.name,
                              })
                            }
                          >
                            Enregistrer la preuve
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {data.minutes.resolutions && !requirements.length && (
            <p>
              Aucun opposant ou défaillant identifié dans les votes enregistrés.
              Conservez le PV accessible aux copropriétaires.
            </p>
          )}
          {data.phase === "signed" && (
            <ActionForm
              busy={busy}
              submit="Clore et inscrire l’AG au registre"
              onSubmit={(body) => act("close", body)}
            >
              <Check
                name="reviewed"
                label="Les pièces signées et notifications nécessaires sont conservées."
              />
            </ActionForm>
          )}
          {data.phase === "closed" && (
            <p className="ag-success">
              L’AG est archivée ; les votes, PV et preuves restent consultables.
            </p>
          )}
          {["signed", "closed"].includes(data.phase) && (
            <details className="ag-appeals">
              <summary>Suivre un recours ou une contestation</summary>
              <p>
                Le suivi ne dépose aucun recours. Conservez la référence et les
                pièces de la procédure réellement engagée.
              </p>
              <ActionForm
                busy={busy}
                submit="Conserver le recours déclaré"
                onSubmit={(body) => act("appeal", body)}
              >
                <label>
                  Copropriétaire
                  <select name="elector" required>
                    <option value="">Choisir le déclarant</option>
                    {electors.map((r) => (
                      <option key={r.elector} value={r.elector}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Résolution contestée
                  <select name="resolution" required>
                    {data.packet.resolutions.map((r: Row) => (
                      <option key={r.id} value={r.id}>
                        {r.position}. {r.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Date du recours
                  <input name="filed_on" type="date" required max={today()} />
                </label>
                <label>
                  Référence de procédure
                  <input name="reference" required maxLength={250} />
                </label>
                <VersionSelect
                  name="proof"
                  label="Pièce de la procédure"
                  versions={context.versions}
                />
                <label>
                  Suivi et observations
                  <textarea name="notes" maxLength={5000} />
                </label>
              </ActionForm>
              {data.appeals.map((a: Row) => (
                <article className="ag-decision" key={a.id}>
                  <h3>
                    {a.reference} · {dateLabel(a.filed_on)}
                  </h3>
                  <ActionForm
                    busy={busy}
                    submit="Actualiser le suivi"
                    onSubmit={(body) =>
                      act("appeal-update", { ...body, appeal: a.id })
                    }
                  >
                    <label>
                      État
                      <select name="status" defaultValue={a.status}>
                        <option value="filed">Recours déclaré</option>
                        <option value="ongoing">En cours</option>
                        <option value="resolved">Terminé</option>
                      </select>
                    </label>
                    <label>
                      Observations et issue
                      <textarea
                        name="notes"
                        maxLength={5000}
                        defaultValue={a.notes}
                      />
                    </label>
                  </ActionForm>
                </article>
              ))}
            </details>
          )}
        </section>
      )}

      {section === "decisions" && (
        <section className="panel">
          <h2>Mettre en œuvre les décisions</h2>
          <p>
            Après signature du PV, reprenez les postes d’un budget voté ou créez
            un échéancier d’appels. Les montants et dates sont à contrôler
            d’après le texte adopté ; les appels créés restent en brouillon.
          </p>
          {recorded
            .filter(
              (v) =>
                !v.voided &&
                v.result.adopted &&
                !recorded.some(
                  (other) =>
                    !other.voided &&
                    other.resolution === v.resolution &&
                    other.tour > v.tour,
                ),
            )
            .map((v) => {
              const r = data.packet.resolutions.find(
                (r: Row) => r.id === v.resolution,
              );
              return (
                <article className="ag-decision" key={v.id}>
                  <h3>{r.title}</h3>
                  {v.execution ? (
                    <p className="ag-success">
                      Mise en œuvre conservée : {v.execution.data.reference} ·{" "}
                      {v.execution.data.calls
                        ? `${v.execution.data.calls.length} appels en brouillon`
                        : v.execution.data.regularization
                          ? "Régularisation enregistrée"
                          : v.execution.data.owner
                            ? `Mandat de ${v.execution.data.name} jusqu’au ${dateLabel(v.execution.data.ends_on)}`
                            : "Postes budgétaires enregistrés"}
                    </p>
                  ) : (
                    <button
                      className="button secondary"
                      disabled={
                        busy || !["signed", "closed"].includes(data.phase)
                      }
                      onClick={() =>
                        setExecution({ vote: v.id, title: r.title })
                      }
                    >
                      Reprendre cette décision
                    </button>
                  )}
                </article>
              );
            })}
        </section>
      )}

      {section === "history" && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Registre et historique de l’AG</h2>
              <p>
                Les corrections conservent leurs motifs et les versions
                précédentes.
              </p>
            </div>
            <button
              className="button secondary"
              onClick={() => {
                const blob = new Blob(
                  [JSON.stringify({ meeting, workflow: data }, null, 2)],
                  { type: "application/json" },
                );
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `ag-${meeting.id}-donnees.json`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              Exporter les données (JSON)
            </button>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Étape</th>
                  <th>Référence</th>
                </tr>
              </thead>
              <tbody>
                {data.events.map((e: Row, i: number) => (
                  <tr key={i}>
                    <td>{new Date(e.date).toLocaleString("fr-FR")}</td>
                    <td>
                      {(
                        {
                          configure: "Préparation",
                          freeze: "Dossier figé",
                          delivery: "Preuve de notification",
                          attendance: "Présences / pouvoirs",
                          start: "Ouverture de séance",
                          vote: "Vote",
                          void_vote: "Correction de vote",
                          minutes: "Projet de PV",
                          signatures: "Signatures conservées",
                          revise_minutes: "Correction du projet de PV",
                          close: "Archivage",
                          publish: "Partage du résumé",
                          execute: "Mise en œuvre",
                        } as Record<string, string>
                      )[e.action] || e.action}
                    </td>
                    <td>
                      {e.data.reason ||
                        e.data.reference ||
                        (e.data.id ? `#${e.data.id}` : "—")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {delivery && (
        <WorkflowDialog
          title={`Preuve — ${delivery.name}`}
          onClose={() => setDelivery(null)}
        >
          <p className="ag-help">
            Renseignez les dates réelles et une pièce de preuve déjà ajoutée
            dans Documents. Un courriel ordinaire ne remplace pas une
            notification légale.
          </p>
          <ActionForm
            busy={busy}
            submit="Conserver la preuve"
            onSubmit={async (body) => {
              const ok = await act("delivery", {
                ...body,
                kind: delivery.kind,
                elector: delivery.elector,
              });
              if (ok) setDelivery(null);
              return ok;
            }}
          >
            <label>
              Modalité
              <select name="method">
                <option value="lrar">Lettre recommandée postale</option>
                <option value="lre">Lettre recommandée électronique</option>
                <option value="qualified">Procédé électronique qualifié</option>
                {delivery.kind === "invitation" && (
                  <option value="hand">Remise contre émargement</option>
                )}
              </select>
            </label>
            <label>
              Date d’envoi
              <input name="sent_on" type="date" required max={today()} />
            </label>
            <label>
              Date de prise d’effet de la notification
              <input name="effective_on" type="date" required max={today()} />
            </label>
            <label>
              Référence du suivi
              <input name="reference" required maxLength={250} />
            </label>
            <VersionSelect
              name="proof"
              label="Preuve et accusé / émargement"
              versions={context.versions}
            />
            <Check
              name="proof_checked"
              label="Le destinataire, la modalité et la date de prise d’effet ont été vérifiés sur la preuve."
            />
          </ActionForm>
        </WorkflowDialog>
      )}
      {vote && (
        <WorkflowDialog
          title={`Vote ${vote.tour} — ${vote.resolution.title}`}
          onClose={() => setVote(null)}
        >
          <ActionForm
            busy={busy}
            submit="Calculer et enregistrer ce vote"
            onSubmit={async (body) => {
              const choices = Object.fromEntries(
                Object.entries(body)
                  .filter(([k]) => k.startsWith("choice:"))
                  .map(([k, v]) => [k.slice(7), v]),
              );
              const ok = await act("vote", {
                resolution: vote.resolution.id,
                tour: vote.tour,
                choices,
                amendment: body.amendment || "",
                incident: body.incident,
              });
              if (ok) setVote(null);
              return ok;
            }}
          >
            {vote.resolution.rights.map((right: Row) => {
              const r = electors.find((r) => r.elector === right.elector);
              const p = data.participants.find(
                (p: Row) => p.elector === right.elector,
              );
              return ["present", "represented"].includes(p.attendance) ? (
                <label key={r?.elector}>
                  {r?.name} · {right.shares} voix
                  <select
                    name={`choice:${r?.elector}`}
                    required
                    defaultValue=""
                  >
                    <option value="">Choisir le vote exprimé</option>
                    {Object.entries(choiceNames).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <p key={r?.elector}>
                  {r?.name} · {presenceNames[p.attendance]} · {right.shares}{" "}
                  voix
                  {p.attendance === "correspondence"
                    ? ` · ${choiceNames[p.choices[String(vote.resolution.id)]]}`
                    : ""}
                </p>
              );
            })}
            <label>
              Texte amendé complet, s’il y a lieu
              <textarea
                name="amendment"
                maxLength={5000}
                defaultValue={vote.initial?.amendment || ""}
                readOnly={vote.tour === 2}
              />
            </label>
            <p className="ag-help">
              Si le texte est amendé, les copropriétaires ayant voté pour par
              correspondance sont réputés défaillants pour cette résolution. Une
              passerelle garde le même texte.
            </p>
            <label>
              Incidents techniques, réserves, observations
              <textarea name="incident" maxLength={5000} />
            </label>
          </ActionForm>
        </WorkflowDialog>
      )}
      {execution && (
        <WorkflowDialog
          title={`Décision — ${execution.title}`}
          onClose={() => setExecution(null)}
        >
          <Execution
            context={context}
            approvedOn={new Date(data.packet.scheduled_at).toLocaleDateString(
              "en-CA",
            )}
            busy={busy}
            onSubmit={async (body) => {
              const ok = await act("execute", {
                ...body,
                vote: execution.vote,
              });
              if (ok) setExecution(null);
              return ok;
            }}
          />
        </WorkflowDialog>
      )}
    </div>
  );
}

function Check({
  name,
  label,
  checked = false,
}: {
  name: string;
  label: string;
  checked?: boolean;
}) {
  return (
    <label className="checkbox-field ag-check">
      <input type="checkbox" name={name} required defaultChecked={checked} />
      {label}
    </label>
  );
}
function VersionSelect({
  name,
  label,
  versions,
  value = "",
}: {
  name: string;
  label: string;
  versions: Row[];
  value?: string | number;
}) {
  return (
    <label>
      {label}
      <select name={name} defaultValue={value} required>
        <option value="">Choisir une version ajoutée dans Documents</option>
        {versions.map((v) => (
          <option key={v.id} value={v.id}>
            {v.title} — {v.filename} · version {v.id}
          </option>
        ))}
      </select>
    </label>
  );
}
function ActionForm({
  children,
  onSubmit,
  busy,
  submit,
}: {
  children: React.ReactNode;
  onSubmit: (body: Row) => Promise<boolean>;
  busy: boolean;
  submit: string;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const body = Object.fromEntries(new FormData(form));
        form
          .querySelectorAll<HTMLInputElement>('input[type="checkbox"]')
          .forEach((input) => {
            (body as Row)[input.name] = input.checked;
          });
        void onSubmit(body);
      }}
    >
      <fieldset disabled={busy} className="ag-form">
        {children}
        <button className="button primary">
          {busy ? "Enregistrement…" : submit}
        </button>
      </fieldset>
    </form>
  );
}

function Preparation({
  meeting,
  config,
  context,
  busy,
  onSave,
}: {
  meeting: Row;
  config: Row;
  context: Row;
  busy: boolean;
  onSave: (config: Row) => Promise<boolean>;
}) {
  const [templates, setTemplates] = useState<Record<string, string>>(
    Object.fromEntries(
      meeting.resolutions.map((r: Row) => [
        String(r.id),
        config.resolutions?.[r.id]?.template ||
          context.templates.find((t: Row) => t.title === r.title)?.id ||
          "",
      ]),
    ),
  );
  return (
    <section className="panel">
      <h2>Informations et pièces du dossier</h2>
      <p>
        Les adresses sont celles auxquelles notifier les copropriétaires ou leur
        mandataire commun. Les versions choisies sont conservées même si un
        document est actualisé ensuite.
      </p>
      <ActionForm
        busy={busy}
        submit="Enregistrer les vérifications et pièces"
        onSubmit={(body) => {
          const contacts = Object.fromEntries(
            (meeting.roster || []).map((r: Row) => [
              personKey(r),
              {
                address: body[`address:${personKey(r)}`],
                email: body[`email:${personKey(r)}`] || "",
              },
            ]),
          );
          const resolutions = Object.fromEntries(
            meeting.resolutions.map((r: Row) => {
              const t = context.templates.find(
                (t: Row) => t.id === templates[r.id],
              );
              const required = t?.pieces || [];
              const pieces = required.map((label: string, index: number) => ({
                label,
                version: Number(body[`piece:${r.id}:${index}`]),
              }));
              if (body[`extra:${r.id}`])
                pieces.push({
                  label: "Pièce complémentaire",
                  version: Number(body[`extra:${r.id}`]),
                });
              return [
                String(r.id),
                {
                  template: templates[r.id],
                  pieces,
                  key: body[`key:${r.id}`] || null,
                  key_confirmed: body[`confirmed:${r.id}`] === true,
                  request_owner: body[`request_owner:${r.id}`] || null,
                  request_version: body[`request_version:${r.id}`] || null,
                  request_received_on: body[`request_received:${r.id}`] || null,
                },
              ];
            }),
          );
          return onSave({
            ...config,
            organizer: body.organizer,
            return_address: body.return_address,
            consultation: body.consultation,
            notice_days: Number(body.notice_days),
            fiscal_year: body.fiscal_year || null,
            legal_checked: body.legal_checked,
            local_holidays: body.local_holidays === true,
            syndic_elector: body.syndic_elector,
            manual_electorate_reason: body.manual_electorate_reason,
            contacts,
            resolutions,
          });
        }}
      >
        <label>
          Nom du syndic / organisateur
          <input
            name="organizer"
            required
            maxLength={200}
            defaultValue={config.organizer || ""}
          />
        </label>
        <label>
          Exercice présenté pour l’approbation annuelle
          <select name="fiscal_year" defaultValue={config.fiscal_year || ""}>
            <option value="">AG sans approbation annuelle / à préciser</option>
            {context.years.map((y: Row) => (
              <option key={y.id} value={y.id}>
                {y.name} · fin le {dateLabel(y.ends_on)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Adresse de retour des formulaires
          <input
            name="return_address"
            required
            maxLength={500}
            defaultValue={config.return_address || ""}
          />
        </label>
        <label>
          Consultation des pièces justificatives : lieu, dates et horaires
          <textarea
            name="consultation"
            required
            maxLength={2000}
            defaultValue={config.consultation || ""}
          />
        </label>
        <label>
          Délai de convocation prévu par le règlement (jours)
          <input
            name="notice_days"
            type="number"
            min={21}
            max={365}
            defaultValue={config.notice_days || 21}
            required
          />
        </label>
        <label>
          Syndic bénévole / président du conseil en mode coopératif
          <select
            name="syndic_elector"
            defaultValue={config.syndic_elector || ""}
          >
            <option value="">
              Personne extérieure / à vérifier selon le mandat
            </option>
            {meeting.roster.map((r: Row) => (
              <option key={personKey(r)} value={personKey(r)}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-field">
          <input
            type="checkbox"
            name="local_holidays"
            defaultChecked={config.local_holidays === true}
          />
          Tenir aussi compte du Vendredi saint et du 26 décembre
          (Alsace-Moselle)
        </label>
        <label>
          Explication des électeurs saisis librement (si utilisés)
          <input
            name="manual_electorate_reason"
            maxLength={500}
            defaultValue={config.manual_electorate_reason || ""}
          />
        </label>
        {meeting.roster.map((r: Row) => (
          <div className="ag-form-group" key={personKey(r)}>
            <h3>{r.name}</h3>
            <label>
              Adresse de notification
              <input
                name={`address:${personKey(r)}`}
                required
                maxLength={500}
                defaultValue={config.contacts?.[personKey(r)]?.address || ""}
              />
            </label>
            {!r.owner_id && (
              <label>
                Courriel (facultatif)
                <input
                  type="email"
                  name={`email:${personKey(r)}`}
                  defaultValue={config.contacts?.[personKey(r)]?.email || ""}
                />
              </label>
            )}
          </div>
        ))}
        {meeting.resolutions.map((r: Row) => {
          const settings = config.resolutions?.[r.id] || {};
          const t = context.templates.find(
            (t: Row) => t.id === templates[r.id],
          );
          return (
            <div className="ag-form-group" key={r.id}>
              <h3>
                {r.position}. {r.title}
              </h3>
              <label>
                Type de résolution / pièces à contrôler
                <select
                  value={templates[r.id] || ""}
                  onChange={(e) =>
                    setTemplates((v) => ({ ...v, [r.id]: e.target.value }))
                  }
                >
                  <option value="">Autre décision — liste à vérifier</option>
                  {context.templates.map((t: Row) => (
                    <option key={t.id} value={t.id}>
                      {t.title}
                    </option>
                  ))}
                </select>
              </label>
              {(t?.pieces || []).map((label: string, index: number) => (
                <VersionSelect
                  key={`${templates[r.id]}:${index}`}
                  label={label}
                  name={`piece:${r.id}:${index}`}
                  versions={context.versions}
                  value={
                    settings.pieces?.find((p: Row) => p.label === label)
                      ?.version || ""
                  }
                />
              ))}
              <label>
                Pièce complémentaire
                <select
                  name={`extra:${r.id}`}
                  defaultValue={
                    settings.pieces?.find(
                      (p: Row) => p.label === "Pièce complémentaire",
                    )?.version || ""
                  }
                >
                  <option value="">Aucune</option>
                  {context.versions.map((v: Row) => (
                    <option key={v.id} value={v.id}>
                      {v.title} · version {v.id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Droits pour cette résolution
                <select name={`key:${r.id}`} defaultValue={settings.key || ""}>
                  <option value="">
                    Tantièmes généraux de tous les copropriétaires
                  </option>
                  {context.keys.map((k: Row) => (
                    <option key={k.id} value={k.id}>
                      {k.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  name={`confirmed:${r.id}`}
                  defaultChecked={settings.key_confirmed === true}
                />
                Si une clé spéciale est choisie, son utilisation pour ce vote a
                été vérifiée dans le règlement et selon l’objet de la décision.
              </label>
              <details>
                <summary>
                  Demande écrite d’un copropriétaire à l’origine de ce point
                </summary>
                <label>
                  Demandeur
                  <select
                    name={`request_owner:${r.id}`}
                    defaultValue={settings.request_owner || ""}
                  >
                    <option value="">Aucune demande rattachée</option>
                    {context.owners.map((o: Row) => (
                      <option key={o.id} value={o.id}>
                        {o.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Demande reçue le
                  <input
                    name={`request_received:${r.id}`}
                    type="date"
                    max={today()}
                    defaultValue={settings.request_received_on || ""}
                  />
                </label>
                <label>
                  Version de la demande écrite
                  <select
                    name={`request_version:${r.id}`}
                    defaultValue={settings.request_version || ""}
                  >
                    <option value="">Choisir la demande dans Documents</option>
                    {context.versions.map((v: Row) => (
                      <option key={v.id} value={v.id}>
                        {v.title} · version {v.id}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="muted">
                  Rattachez la demande avant de figer la convocation. Une
                  question arrivée trop tard est à porter à l’AG suivante.
                </p>
              </details>
            </div>
          );
        })}
        <Check
          name="legal_checked"
          checked={config.legal_checked === true}
          label="J’ai vérifié l’ordre du jour, les majorités et pièces nécessaires, le règlement, les identités et mandataires communs, ainsi que le calendrier applicable à cette AG ordinaire en France métropolitaine."
        />
      </ActionForm>
    </section>
  );
}

function Participants({
  packet,
  participants,
  versions,
  disabled,
  onSave,
}: {
  packet: Row;
  participants: Row[];
  versions: Row[];
  disabled: boolean;
  onSave: (rows: Row[]) => Promise<boolean>;
}) {
  const [rows, setRows] = useState<Row[]>(participants);
  const update = (key: string, changes: Row) =>
    setRows((v) =>
      v.map((r) => (r.elector === key ? { ...r, ...changes } : r)),
    );
  const totals = Object.keys(presenceNames).map((key) => [
    presenceNames[key],
    rows
      .filter((r) => r.attendance === key)
      .reduce(
        (total, r) =>
          total +
          Number(
            packet.electors.find((e: Row) => e.elector === r.elector).shares,
          ),
        0,
      ),
  ]);
  return (
    <section className="panel">
      <h2>Présences, pouvoirs et correspondance</h2>
      <p>
        Modifiez et enregistrez cette liste lorsqu’une personne arrive ou part.
        Chaque vote conserve la présence utilisée à son dépouillement. Un mandat
        exige une pièce et la vérification de l’éligibilité du mandataire.
      </p>
      <div className="ag-totals">
        {totals.map(([label, total]) => (
          <span key={label}>
            {label}
            <strong>{total} voix</strong>
          </span>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void onSave(rows);
        }}
      >
        <fieldset disabled={disabled} className="ag-form">
          {rows.map((r) => {
            const e = packet.electors.find((e: Row) => e.elector === r.elector);
            return (
              <div className="ag-form-group" key={r.elector}>
                <h3>
                  {e.name} · {e.shares} voix
                  {e.raw_shares !== e.shares
                    ? ` (article 22 : ${e.raw_shares} avant réduction)`
                    : ""}
                </h3>
                <label>
                  Participation
                  <select
                    value={r.attendance}
                    onChange={(event) =>
                      update(r.elector, {
                        attendance: event.target.value,
                        proof: "",
                        choices: {},
                      })
                    }
                  >
                    {Object.entries(presenceNames).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                {r.attendance === "represented" && (
                  <>
                    <label>
                      Mandataire copropriétaire
                      <select
                        value={r.representative_id || ""}
                        onChange={(event) => {
                          const id = event.target.value;
                          update(r.elector, {
                            representative_id: id,
                            representative:
                              packet.electors.find((p: Row) => p.elector === id)
                                ?.name || "",
                          });
                        }}
                      >
                        <option value="">
                          Personne extérieure — saisir son nom
                        </option>
                        {packet.electors
                          .filter((p: Row) => p.elector !== r.elector)
                          .map((p: Row) => (
                            <option key={p.elector} value={p.elector}>
                              {p.name}
                            </option>
                          ))}
                      </select>
                    </label>
                    <label>
                      Nom du mandataire
                      <input
                        required
                        maxLength={200}
                        value={r.representative || ""}
                        onChange={(event) =>
                          update(r.elector, {
                            representative: event.target.value,
                          })
                        }
                        readOnly={!!r.representative_id}
                      />
                    </label>
                    {!r.representative_id && (
                      <label>
                        Domicile du mandataire
                        <input
                          required
                          maxLength={500}
                          value={r.representative_address || ""}
                          onChange={(event) =>
                            update(r.elector, {
                              representative_address: event.target.value,
                            })
                          }
                        />
                      </label>
                    )}
                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        required
                        checked={r.eligible === true}
                        onChange={(event) =>
                          update(r.elector, { eligible: event.target.checked })
                        }
                      />
                      Mandat signé et mandataire éligible : ni syndic, ni
                      personne interdite par l’article 22.
                    </label>
                  </>
                )}
                {["represented", "correspondence"].includes(r.attendance) && (
                  <label>
                    {r.attendance === "represented"
                      ? "Pouvoir signé"
                      : "Formulaire de vote signé"}
                    <select
                      required
                      value={
                        typeof r.proof === "object" ? r.proof.id : r.proof || ""
                      }
                      onChange={(event) =>
                        update(r.elector, { proof: Number(event.target.value) })
                      }
                    >
                      <option value="">Choisir la pièce dans Documents</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.title} · version {v.id}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {r.attendance === "correspondence" && (
                  <>
                    <label>
                      Formulaire reçu le
                      <input
                        type="date"
                        required
                        value={r.received_on || ""}
                        max={packet.correspondence_deadline}
                        onChange={(event) =>
                          update(r.elector, { received_on: event.target.value })
                        }
                      />
                    </label>
                    {packet.resolutions.map((res: Row) => (
                      <label key={res.id}>
                        {res.position}. {res.title}
                        <select
                          required
                          value={r.choices?.[res.id] || ""}
                          onChange={(event) =>
                            update(r.elector, {
                              choices: {
                                ...r.choices,
                                [res.id]: event.target.value,
                              },
                            })
                          }
                        >
                          <option value="">
                            Recopier le choix du formulaire
                          </option>
                          {Object.entries(choiceNames).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </>
                )}
              </div>
            );
          })}
          <button className="button primary">
            Enregistrer les présences et pièces
          </button>
        </fieldset>
      </form>
    </section>
  );
}

function PrintDocuments({
  packet,
  minutes,
  participants,
  view,
  onView,
  fixed = false,
}: {
  packet: Row;
  minutes: Row;
  participants: Row[];
  view: string;
  onView: (view: string) => void;
  fixed?: boolean;
}) {
  return (
    <section className="panel ag-documents">
      <div className="panel-heading ag-no-print">
        <div>
          <h2>Documents à imprimer / PDF</h2>
          <p>
            Imprimez le document affiché, ou enregistrez-le en PDF avec le
            navigateur.
          </p>
        </div>
        <button className="button secondary" onClick={() => window.print()}>
          Imprimer ce document
        </button>
      </div>
      {!fixed && (
        <div className="ag-document-switch ag-no-print">
          {[
            ["invitation", "Convocation"],
            ["attendance", "Feuille de présence"],
            ["correspondence", "Vote par correspondance"],
            ["power", "Pouvoir"],
            ...(minutes.resolutions ? [["minutes", "Procès-verbal"]] : []),
          ].map(([value, label]) => (
            <button
              className={`button ${view === value ? "primary" : "secondary"}`}
              key={value}
              onClick={() => onView(value)}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <article className="ag-print-document">
        <p className="eyebrow">{packet.organizer}</p>
        <h2>
          {
            (
              {
                invitation: "Convocation à l’assemblée générale",
                attendance: "Feuille de présence",
                correspondence: "Formulaire de vote par correspondance",
                power: "Pouvoir de représentation",
                minutes: "Procès-verbal de l’assemblée générale",
              } as Record<string, string>
            )[view]
          }
        </h2>
        <h3>{packet.title}</h3>
        <p>
          {new Date(packet.scheduled_at).toLocaleString("fr-FR")} ·{" "}
          {packet.location}
        </p>
        {view === "invitation" && (
          <>
            <p>
              Madame, Monsieur, vous êtes convoqué(e) à l’assemblée générale
              ci-dessus. L’ordre du jour, les pièces désignées ci-dessous, un
              formulaire de vote par correspondance et un pouvoir sont joints à
              cette convocation.
            </p>
            <h3>Consultation des justificatifs</h3>
            <p className="ag-text">{packet.consultation}</p>
            <h3>Ordre du jour</h3>
            {packet.resolutions.map((r: Row) => (
              <div key={r.id}>
                <h4>
                  {r.position}. {r.title} — {majorityLabels[r.majority]}
                </h4>
                <p className="ag-text">{r.text}</p>
                {r.pieces.map((p: Row) => (
                  <p key={`${p.id}-${p.label}`}>
                    Pièce : {p.label} — {p.title} ({p.filename}, version {p.id})
                  </p>
                ))}
              </div>
            ))}
            <p>
              Le formulaire de vote doit être reçu au plus tard le{" "}
              {dateLabel(packet.correspondence_deadline)} à{" "}
              {packet.return_address}. En cas de représentation, joignez un
              pouvoir signé identifiant le mandant et le mandataire.
            </p>
          </>
        )}
        {view === "attendance" && (
          <>
            <p>
              Présence à vérifier et certifier par le président de séance. Les
              changements de présence figurent dans les instantanés des votes.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Nom et domicile</th>
                  <th>Lots</th>
                  <th>Voix</th>
                  <th>Participation / mandataire</th>
                  <th>Émargement</th>
                </tr>
              </thead>
              <tbody>
                {packet.electors.map((r: Row) => {
                  const p = participants.find(
                    (p: Row) => p.elector === r.elector,
                  );
                  return (
                    <tr key={r.elector}>
                      <td>
                        {r.name}
                        <br />
                        {r.address}
                      </td>
                      <td>{r.lots.join(", ")}</td>
                      <td>{r.shares}</td>
                      <td>
                        {presenceNames[p?.attendance || "absent"]}
                        {p?.representative
                          ? ` — ${p.representative}, ${p.representative_address}`
                          : ""}
                      </td>
                      <td className="ag-signature-cell" />
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p>
              Certifiée exacte par le président de séance : nom, date et
              signature.
            </p>
          </>
        )}
        {view === "correspondence" && (
          <>
            <p>
              Je soussigné(e) : nom / prénom :
              _____________________________________
              <br />
              Domicile : _______________________________________________________
              <br />
              Copropriétaire du ou des lots :
              ____________________________________
            </p>
            <p>
              Ce formulaire doit être réceptionné par le syndic au plus tard le{" "}
              <strong>{dateLabel(packet.correspondence_deadline)}</strong>, à
              l’adresse suivante : {packet.return_address}. Cocher une seule
              case par résolution.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Résolution</th>
                  <th>Pour</th>
                  <th>Contre</th>
                  <th>Abstention</th>
                </tr>
              </thead>
              <tbody>
                {packet.resolutions.map((r: Row) => (
                  <tr key={r.id}>
                    <td>
                      {r.position}. {r.title}
                      <p className="ag-text">{r.text}</p>
                    </td>
                    <td>☐</td>
                    <td>☐</td>
                    <td>☐</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p>
              Si une résolution pour laquelle vous avez voté favorablement est
              amendée en séance, vous êtes assimilé(e) à un copropriétaire
              défaillant pour cette résolution. Votre présence ou représentation
              à l’assemblée prévaut sur le formulaire.
            </p>
            <p>
              Fait à ______________________, le ______________________.
              Signature :
            </p>
          </>
        )}
        {view === "power" && (
          <>
            <p>
              Je soussigné(e) ______________________, domicilié(e)
              ______________________,
              <br />
              copropriétaire du ou des lots ______________________, donne mandat
              à ______________________,
              <br />
              domicilié(e) ______________________, pour me représenter à l’AG
              indiquée ci-dessus et voter les résolutions inscrites à l’ordre du
              jour.
            </p>
            <p>
              Consignes éventuelles :
              _______________________________________________________
            </p>
            <p>
              Le mandataire et le mandat doivent respecter l’article 22. Le
              syndic et les personnes interdites par cet article ne peuvent
              recevoir ce pouvoir.
            </p>
            <p>
              Fait à ______________________, le ______________________.
              Signature du mandant :
            </p>
          </>
        )}
        {view === "minutes" && minutes.resolutions && (
          <>
            <p>
              Président : {minutes.bureau.president}
              <br />
              Secrétaire : {minutes.bureau.secretary}
              <br />
              Scrutateur(s) : {minutes.bureau.scrutineers || "Aucun"}
            </p>
            {minutes.resolutions.map((r: Row) => (
              <div key={r.resolution.id}>
                <h3>
                  {r.resolution.position}. {r.resolution.title}
                </h3>
                <p className="ag-text">
                  {r.votes.at(-1).amendment || r.resolution.text}
                </p>
                <p>
                  Décision :{" "}
                  <strong>{r.adopted ? "ADOPTÉE" : "NON ADOPTÉE"}</strong>
                </p>
                {r.votes.map((v: Row) => (
                  <div key={v.id}>
                    <p>
                      Tour {v.tour} — {majorityLabels[v.result.rule]} :{" "}
                      {v.result.for_votes} voix pour, {v.result.against_votes}{" "}
                      contre, {v.result.abstain_votes} abstention.
                    </p>
                    <p>{v.result.explanation}</p>
                    {v.incident && <p>Incidents / réserves : {v.incident}</p>}
                  </div>
                ))}
                {["for", "against", "abstain", "absent"].map((group) => (
                  <p key={group}>
                    {group === "absent" ? "Défaillants" : choiceNames[group]} :{" "}
                    {r.groups[group]
                      .map((p: Row) => `${p.name} (${p.shares} voix)`)
                      .join(", ") || "Aucun"}
                  </p>
                ))}
              </div>
            ))}
            {minutes.remarks && <p>Observations : {minutes.remarks}</p>}
            <p className="ag-text">{minutes.appeal_notice}</p>
            <p>
              Annexe : feuille de présence certifiée, formulaires et pouvoirs
              conservés avec le dossier.
            </p>
            <div className="ag-signatures">
              <span>Président — date et signature</span>
              <span>Secrétaire — date et signature</span>
              <span>Scrutateur(s) — date et signature</span>
            </div>
            <p className="muted">Empreinte du projet : {minutes.digest}</p>
          </>
        )}
      </article>
    </section>
  );
}

function Execution({
  context,
  approvedOn,
  busy,
  onSubmit,
}: {
  context: Row;
  approvedOn: string;
  busy: boolean;
  onSubmit: (body: Row) => Promise<boolean>;
}) {
  const [kind, setKind] = useState("current");
  const [year, setYear] = useState("");
  const [preview, setPreview] = useState<Row | null>(null);
  const [previewError, setPreviewError] = useState("");
  useEffect(() => {
    let active = true;
    setPreview(null);
    setPreviewError("");
    if (kind === "accounts" && year)
      api<Row>(
        `finance/cycle/regularization?year=${year}&approved_on=${approvedOn}`,
      )
        .then((result) => {
          if (active) setPreview(result.preview);
        })
        .catch((e) => {
          if (active) setPreviewError(e.message);
        });
    return () => {
      active = false;
    };
  }, [kind, year, approvedOn]);
  const [lines, setLines] = useState<Row[]>([
    { code: "", key: "", amount: "" },
  ]);
  return (
    <ActionForm
      busy={busy}
      submit="Créer depuis la décision adoptée"
      onSubmit={(body) =>
        onSubmit({ ...body, kind, lines, source_hash: preview?.source_hash })
      }
    >
      <label>
        Mise en œuvre
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="accounts">
            Approbation des comptes et régularisation
          </option>
          <option value="syndic">Mandat du syndic bénévole</option>
          <option value="council">
            Mandat d’un membre du conseil syndical
          </option>
          <option value="budget">Postes du budget voté</option>
          <option value="current">Appels du budget courant</option>
          <option value="works">Travaux et appels dédiés</option>
          <option value="fund">Cotisation au fonds travaux</option>
          <option value="advance">Avance de trésorerie</option>
        </select>
      </label>
      {!["syndic", "council"].includes(kind) && (
        <label>
          Exercice
          <select
            name="year"
            required
            value={year}
            onChange={(e) => setYear(e.target.value)}
          >
            <option value="">Choisir un exercice ouvert</option>
            {context.years
              .filter((y: Row) => !y.closed)
              .map((y: Row) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                </option>
              ))}
          </select>
        </label>
      )}
      {kind === "budget" ? (
        <>
          {lines.map((line, index) => (
            <div className="ag-form-group" key={index}>
              <label>
                Poste de charges
                <select
                  required
                  value={line.code}
                  onChange={(e) =>
                    setLines((rows) =>
                      rows.map((r, i) =>
                        i === index ? { ...r, code: e.target.value } : r,
                      ),
                    )
                  }
                >
                  <option value="">Choisir un compte</option>
                  {context.accounts.map((a: Row) => (
                    <option key={a.code} value={a.code}>
                      {a.code} · {a.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Clé
                <select
                  required
                  value={line.key}
                  onChange={(e) =>
                    setLines((rows) =>
                      rows.map((r, i) =>
                        i === index ? { ...r, key: e.target.value } : r,
                      ),
                    )
                  }
                >
                  <option value="">Choisir une clé</option>
                  {context.keys.map((k: Row) => (
                    <option key={k.id} value={k.id}>
                      {k.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Montant voté (€)
                <input
                  type="number"
                  required
                  min={0}
                  step="0.01"
                  value={line.amount}
                  onChange={(e) =>
                    setLines((rows) =>
                      rows.map((r, i) =>
                        i === index ? { ...r, amount: e.target.value } : r,
                      ),
                    )
                  }
                />
              </label>
            </div>
          ))}
          <button
            type="button"
            className="button secondary"
            onClick={() =>
              setLines((v) => [...v, { code: "", key: "", amount: "" }])
            }
          >
            Ajouter un poste
          </button>
        </>
      ) : ["syndic", "council"].includes(kind) ? (
        <>
          <label>
            Copropriétaire élu
            <select name="owner" required>
              <option value="">Choisir la personne élue</option>
              {context.owners
                .filter((o: Row) => Number(o.shares) > 0)
                .map((o: Row) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Début du mandat
            <input name="starts_on" type="date" required min={approvedOn} />
          </label>
          <label>
            Fin du mandat
            <input name="ends_on" type="date" required />
          </label>
          <label>
            Conditions du mandat / indemnité votée
            <textarea name="notes" maxLength={1000} />
          </label>
          <p className="ag-help">
            Le mandat est inscrit avec sa décision et ses dates. Les droits de
            connexion des utilisateurs se gèrent dans Administration. En mode
            coopératif, la désignation du président par le conseil syndical est
            une décision distincte à conserver.
          </p>
        </>
      ) : kind === "accounts" ? (
        <>
          <p>
            Date d’approbation : {dateLabel(approvedOn)}. Les propriétaires à
            cette date reçoivent la régularisation.
          </p>
          {previewError && <p className="alert">{previewError}</p>}
          {preview ? (
            <>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Lot</th>
                      <th>Charges</th>
                      <th>Provisions</th>
                      <th>Régularisation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r: Row, i: number) => (
                      <tr key={i}>
                        <td>{r.lot_number}</td>
                        <td>{r.actual} €</td>
                        <td>{r.provisions} €</td>
                        <td>{r.adjustment} €</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {preview.errors.map((e: string) => (
                <p className="alert" key={e}>
                  {e}
                </p>
              ))}
            </>
          ) : (
            <p>
              Choisissez l’exercice pour examiner la répartition avant
              validation.
            </p>
          )}
        </>
      ) : (
        <>
          <label>
            Libellé
            <input name="label" required maxLength={140} />
          </label>
          <label>
            Clé de répartition
            <select name="key" required>
              <option value="">Choisir une clé</option>
              {context.keys.map((k: Row) => (
                <option key={k.id} value={k.id}>
                  {k.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Montant total voté (€)
            <input
              name="amount"
              type="number"
              required
              min="0.01"
              step="0.01"
            />
          </label>
          <label>
            Première échéance
            <input name="date" type="date" required />
          </label>
          <label>
            Nombre d’échéances
            <input
              name="count"
              type="number"
              required
              min={1}
              max={12}
              defaultValue={4}
            />
          </label>
          <label>
            Espacement en mois
            <input
              name="months"
              type="number"
              required
              min={1}
              max={12}
              defaultValue={3}
            />
          </label>
        </>
      )}
      <Check
        name="reviewed"
        label="Les postes, montants, clés, dates et modalités correspondent à la résolution adoptée."
      />
    </ActionForm>
  );
}

function WorkflowDialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      className="ag-modal"
      aria-label={title}
    >
      <div className="dialog-heading">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Fermer" onClick={onClose}>
          <Icon name="close" />
        </button>
      </div>
      <div className="dialog-body">{children}</div>
    </dialog>
  );
}

export function SharedAssemblyDecisions() {
  const [items, setItems] = useState<Row[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<Row>("ag/summaries")
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
  return error ? (
    <p className="alert" role="alert">
      {error}
    </p>
  ) : items.length ? (
    <section className="panel">
      <h2>Décisions des assemblées générales</h2>
      {items.map((item) => (
        <article key={item.id}>
          <h3>
            {item.title} · {dateLabel(item.date)}
          </h3>
          {item.resolutions.map((r: Row, i: number) => (
            <details key={i}>
              <summary>
                {r.title} · {r.adopted ? "Adoptée" : "Non adoptée"}
              </summary>
              <p className="ag-text">{r.text}</p>
              <p>
                {r.result.for_votes} voix pour · {r.result.against_votes} contre
                · {r.result.abstain_votes} abstention
              </p>
            </details>
          ))}
        </article>
      ))}
    </section>
  ) : null;
}
