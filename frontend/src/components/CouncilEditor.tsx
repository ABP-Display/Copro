import { useEffect, useRef, useState } from "react";
import { Icon } from "./ui";

export type Choice = { value: string | number; label: string };
export type CouncilField = {
  name: string;
  label: string;
  type?: string;
  optional?: boolean;
  choices?: Choice[];
  value?: any;
  help?: string;
};
export function CouncilEditor({
  title,
  description,
  fields,
  submitLabel = "Enregistrer",
  onSave,
  onClose,
}: {
  title: string;
  description?: string;
  fields: CouncilField[];
  submitLabel?: string;
  onSave: (values: Record<string, any>) => Promise<void>;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const values: Record<string, any> = Object.fromEntries(form);
    fields.forEach((field) => {
      if (field.type === "checkbox")
        values[field.name] = form.get(field.name) === "on";
      if (field.type === "multiple")
        values[field.name] = form.getAll(field.name).map(Number);
    });
    try {
      await onSave(values);
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={ref}
      className="editor-dialog council-dialog"
      aria-labelledby="council-editor-title"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <form onSubmit={(e) => void submit(e)}>
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">CONSEIL & RESPONSABILITÉS</p>
            <h2 id="council-editor-title">{title}</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            disabled={busy}
            aria-label="Fermer"
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="form-fields">
          {description && <p className="muted">{description}</p>}
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          {fields.map((field) => (
            <label
              key={field.name}
              className={
                field.type === "checkbox" ? "council-check" : undefined
              }
            >
              {field.type === "checkbox" ? (
                <>
                  <input
                    type="checkbox"
                    name={field.name}
                    defaultChecked={!!field.value}
                  />
                  {field.label}
                </>
              ) : (
                <>
                  {field.label}
                  {field.choices ? (
                    <select
                      name={field.name}
                      required={!field.optional}
                      defaultValue={
                        field.value ?? (field.type === "multiple" ? [] : "")
                      }
                      multiple={field.type === "multiple"}
                      size={field.type === "multiple" ? 5 : undefined}
                    >
                      {field.type !== "multiple" && (
                        <option value="">
                          {field.optional
                            ? "Aucun / non renseigné"
                            : "Choisir…"}
                        </option>
                      )}
                      {field.choices.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  ) : field.type === "textarea" ? (
                    <textarea
                      name={field.name}
                      required={!field.optional}
                      defaultValue={field.value || ""}
                      maxLength={10000}
                      rows={4}
                    />
                  ) : (
                    <input
                      name={field.name}
                      type={field.type || "text"}
                      required={!field.optional}
                      defaultValue={field.value ?? ""}
                      step={field.type === "number" ? "0.01" : undefined}
                      maxLength={1000}
                    />
                  )}
                </>
              )}
              {field.help && <small>{field.help}</small>}
            </label>
          ))}
        </div>
        <div className="dialog-footer">
          <button
            type="button"
            className="button secondary"
            onClick={onClose}
            disabled={busy}
          >
            Annuler
          </button>
          <button className="button primary" disabled={busy}>
            {busy ? "Enregistrement…" : submitLabel}
          </button>
        </div>
      </form>
    </dialog>
  );
}
