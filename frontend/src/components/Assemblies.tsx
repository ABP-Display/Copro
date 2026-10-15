import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { MeetingRoster } from "./RosterEditor";
import { Empty, Icon } from "./ui";
import { VoteCalculator, majorityLabels, type ToolData } from "./Tools";
import { AssemblyWorkflow } from "./AssemblyWorkflow";

export function Assemblies({
  section,
  onGuide,
}: {
  section: string;
  onGuide: () => void;
}) {
  const [meetings, setMeetings] = useState<ToolData[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editor, setEditor] = useState<ToolData | null>(null);
  const [simulation, setSimulation] = useState<ToolData | null>(null);
  const [archives, setArchives] = useState(false);
  const request = useRef(0);
  const meeting = meetings.find((m) => String(m.id) === selected);
  async function load() {
    const current = ++request.current;
    try {
      const data = await api<{ items: ToolData[] }>(
        `ag/meetings?archived=${archives ? "1" : "0"}`,
      );
      if (current !== request.current) return;
      setMeetings(data.items);
      setSelected((previous) =>
        data.items.some((m) => String(m.id) === previous)
          ? previous
          : String(data.items[0]?.id || ""),
      );
      setError("");
    } catch (e) {
      if (current === request.current) setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
    return () => {
      request.current += 1;
    };
  }, [archives]);
  async function save(path: string, body: ToolData, method = "POST") {
    setBusy(true);
    setError("");
    try {
      const result = await api<ToolData>(path, method, body);
      await load();
      return result;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  const formatted = (value: string) =>
    new Date(value).toLocaleString("fr-FR", {
      dateStyle: "long",
      timeStyle: "short",
    });
  return (
    <section className="assembly-space">
      <div className="assembly-guide-entry">
        <button onClick={onGuide}>
          <Icon name="book" size={15} />
          Besoin d’aide ? Suivre le guide
        </button>
      </div>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <div className="assembly-toolbar">
        <label>
          Assemblée
          <select
            aria-label="Assemblée"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Sélectionner une assemblée</option>
            {meetings.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title}
                {m.archived ? " — archivée" : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={archives}
            onChange={(e) => setArchives(e.target.checked)}
          />
          Inclure les archives
        </label>
        <button
          className="button primary"
          onClick={() => setEditor({ kind: "meeting" })}
        >
          <Icon name="plus" size={16} />
          Préparer une AG
        </button>
      </div>
      {!meeting ? (
        <Empty
          title="Préparez votre première assemblée"
          description="Indiquez une date et un lieu, puis ajoutez les résolutions à l’ordre du jour."
        />
      ) : (
        <>
          <section className="panel meeting-summary">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">DOSSIER D’ASSEMBLÉE</p>
                <h2>{meeting.title}</h2>
                <p>
                  {formatted(meeting.scheduled_at)} ·{" "}
                  {meeting.location || "Lieu à préciser"}
                </p>
              </div>
              <span className="subtle-badge">
                {meeting.archived
                  ? "Archivée"
                  : meeting.phase === "draft"
                    ? "En préparation"
                    : "Dossier conservé"}
              </span>
            </div>
            {meeting.notes && <p className="meeting-notes">{meeting.notes}</p>}
            <div className="assembly-actions">
              {!meeting.archived &&
                (!meeting.phase || meeting.phase === "draft") && (
                  <button
                    className="button secondary"
                    onClick={() =>
                      setEditor({ kind: "meeting", item: meeting })
                    }
                  >
                    Modifier l’assemblée
                  </button>
                )}
              {(!meeting.phase || meeting.phase === "draft") && (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() =>
                    void save(
                      `ag/meetings/${meeting.id}`,
                      { archived: !meeting.archived },
                      "PATCH",
                    )
                  }
                >
                  {meeting.archived ? "Restaurer" : "Archiver"}
                </button>
              )}
              <button
                className="button secondary"
                onClick={() => window.print()}
              >
                Imprimer le dossier / PDF
              </button>
            </div>
          </section>
          <AssemblyWorkflow
            meeting={meeting}
            section={section}
            onChanged={load}
            onTemplate={async (template) => {
              const result = await save(
                `ag/meetings/${meeting.id}/resolutions`,
                {
                  position:
                    Math.max(
                      0,
                      ...meeting.resolutions.map((r: ToolData) => r.position),
                    ) + 1,
                  title: template.title,
                  text: template.text,
                  majority: template.majority,
                  notes: "",
                },
              );
              if (!result)
                throw new Error(
                  "La résolution n’a pas pu être créée. Vérifiez le message affiché.",
                );
            }}
          />
          {section === "presence" &&
            (!meeting.phase || meeting.phase === "draft") && (
              <MeetingRoster
                key={meeting.id}
                meeting={meeting}
                busy={busy}
                onSave={(rows) =>
                  save(`ag/meetings/${meeting.id}`, { roster: rows }, "PATCH")
                }
              />
            )}
          {section === "agenda" && (
            <section className="meeting-agenda">
              <div className="panel-heading">
                <div>
                  <h2>Ordre du jour et résolutions</h2>
                  <p>
                    Les simulations enregistrées restent des aides au
                    dépouillement.
                  </p>
                </div>
                {!meeting.archived &&
                  (!meeting.phase || meeting.phase === "draft") && (
                    <button
                      className="button primary"
                      onClick={() =>
                        setEditor({
                          kind: "resolution",
                          meeting: meeting.id,
                          position:
                            Math.max(
                              0,
                              ...meeting.resolutions.map(
                                (r: ToolData) => r.position,
                              ),
                            ) + 1,
                        })
                      }
                    >
                      <Icon name="plus" size={16} />
                      Ajouter une résolution
                    </button>
                  )}
              </div>
              {!meeting.resolutions.length ? (
                <Empty
                  title="L’ordre du jour est vide"
                  description="Ajoutez un titre, le texte proposé et la majorité à vérifier pour chaque résolution."
                />
              ) : (
                meeting.resolutions.map((r: ToolData) => (
                  <article className="resolution-card" key={r.id}>
                    <div className="resolution-heading">
                      <span className="resolution-number">{r.position}</span>
                      <div>
                        <h3>{r.title}</h3>
                        <p>{majorityLabels[r.majority]}</p>
                      </div>
                    </div>
                    <p className="resolution-text">
                      {r.text || "Texte à compléter"}
                    </p>
                    {r.notes && (
                      <p className="resolution-notes">
                        Note de préparation : {r.notes}
                      </p>
                    )}
                    {r.analysis && (
                      <div className="resolution-result">
                        <span className="subtle-badge">
                          Simulation :{" "}
                          {r.analysis.result.adopted
                            ? "majorité atteinte"
                            : "majorité non atteinte"}
                        </span>
                        <p>{r.analysis.result.criterion}</p>
                        {r.analysis.result.bridge && (
                          <p>{r.analysis.result.bridge_message}</p>
                        )}
                        {r.analysis.first_vote && (
                          <p>
                            Premier vote conservé ; résultat affiché du second
                            vote.
                          </p>
                        )}
                      </div>
                    )}
                    {!meeting.archived &&
                      (!meeting.phase || meeting.phase === "draft") && (
                        <div className="assembly-actions">
                          <button
                            className="button secondary"
                            onClick={() =>
                              setEditor({
                                kind: "resolution",
                                item: r,
                                meeting: meeting.id,
                              })
                            }
                          >
                            Modifier
                          </button>
                          <button
                            className="button secondary"
                            onClick={() => setSimulation(r)}
                          >
                            <Icon name="vote" size={16} />
                            {r.analysis
                              ? "Revoir la simulation"
                              : "Simuler le vote"}
                          </button>
                        </div>
                      )}
                  </article>
                ))
              )}
            </section>
          )}
          <p className="assembly-worknote">
            Les envois et signatures sont réalisés hors de Copro. Conservez
            leurs preuves dans le dossier avant de terminer l’AG.
          </p>
        </>
      )}
      {editor && (
        <AssemblyDialog
          title={
            editor.kind === "meeting"
              ? editor.item
                ? "Modifier l’assemblée"
                : "Préparer une assemblée"
              : editor.item
                ? "Modifier la résolution"
                : "Ajouter une résolution"
          }
          busy={busy}
          onClose={() => setEditor(null)}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const body = Object.fromEntries(
                new FormData(e.currentTarget).entries(),
              );
              const path =
                editor.kind === "meeting"
                  ? editor.item
                    ? `ag/meetings/${editor.item.id}`
                    : "ag/meetings"
                  : editor.item
                    ? `ag/resolutions/${editor.item.id}`
                    : `ag/meetings/${editor.meeting}/resolutions`;
              const saved = await save(
                path,
                body,
                editor.item ? "PATCH" : "POST",
              );
              if (saved) {
                if (editor.kind === "meeting" && saved.id)
                  setSelected(String(saved.id));
                setEditor(null);
              }
            }}
          >
            <div className="dialog-body">
              {error && (
                <div className="alert" role="alert">
                  {error}
                </div>
              )}
              <label>
                Titre
                <input
                  name="title"
                  maxLength={150}
                  required
                  defaultValue={editor.item?.title || ""}
                />
              </label>
              {editor.kind === "meeting" ? (
                <>
                  <label>
                    Date et heure
                    <input
                      type="datetime-local"
                      name="scheduled_at"
                      required
                      defaultValue={
                        editor.item?.scheduled_at
                          ? localDateTime(editor.item.scheduled_at)
                          : ""
                      }
                    />
                  </label>
                  <label>
                    Lieu
                    <input
                      name="location"
                      maxLength={250}
                      defaultValue={editor.item?.location || ""}
                    />
                  </label>
                </>
              ) : (
                <>
                  <label>
                    Numéro dans l’ordre du jour
                    <input
                      type="number"
                      min="1"
                      name="position"
                      required
                      defaultValue={editor.item?.position || editor.position}
                    />
                  </label>
                  <label>
                    Majorité à vérifier
                    <select
                      name="majority"
                      defaultValue={editor.item?.majority || "24"}
                    >
                      {Object.entries(majorityLabels).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Texte de la résolution
                    <textarea
                      name="text"
                      maxLength={10000}
                      rows={5}
                      defaultValue={editor.item?.text || ""}
                    />
                  </label>
                  {editor.item?.analysis && (
                    <p className="muted">
                      Modifier la résolution efface sa simulation afin de ne pas
                      conserver un calcul sur un texte ou une majorité modifiés.
                    </p>
                  )}
                </>
              )}
              <label>
                Notes de préparation
                <textarea
                  name="notes"
                  maxLength={5000}
                  rows={3}
                  defaultValue={editor.item?.notes || ""}
                />
              </label>
            </div>
            <div className="dialog-footer">
              <button
                type="button"
                className="button secondary"
                disabled={busy}
                onClick={() => setEditor(null)}
              >
                Annuler
              </button>
              <button className="button primary" disabled={busy}>
                {busy ? "Enregistrement…" : "Enregistrer"}
              </button>
            </div>
          </form>
        </AssemblyDialog>
      )}
      {simulation && (
        <AssemblyDialog
          title={`Simulation — ${simulation.title}`}
          wide
          busy={busy}
          onClose={() => setSimulation(null)}
        >
          <div className="dialog-body">
            <VoteCalculator
              rule={simulation.majority}
              initial={
                simulation.analysis ||
                (meeting?.roster?.length
                  ? {
                      input: {
                        rule: simulation.majority,
                        mode: "first",
                        roster: meeting.roster,
                      },
                    }
                  : undefined)
              }
              onCalculate={async (data) => {
                setBusy(true);
                try {
                  const result = await api<ToolData>(
                    `ag/resolutions/${simulation.id}/simulate`,
                    "POST",
                    data,
                  );
                  await load();
                  return result.result;
                } finally {
                  setBusy(false);
                }
              }}
            />
          </div>
        </AssemblyDialog>
      )}
    </section>
  );
}

function localDateTime(value: string) {
  const d = new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function AssemblyDialog({
  title,
  children,
  onClose,
  wide = false,
  busy = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`editor-dialog assembly-dialog ${wide ? "wide" : ""}`}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="dialog-heading">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Fermer"
          disabled={busy}
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </div>
      {children}
    </dialog>
  );
}
