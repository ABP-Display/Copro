import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Empty, Icon } from "./ui";
type Row = Record<string, any>;
const size = (value: number) =>
  value >= 1048576
    ? `${(value / 1048576).toFixed(1)} Mo`
    : `${Math.ceil(value / 1024)} Ko`;

export function Documents({
  manager,
  section = "library",
}: {
  manager: boolean;
  section?: string;
}) {
  const [documents, setDocuments] = useState<Row[]>([]);
  const [folders, setFolders] = useState<Row[]>([]);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [archived, setArchived] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [upload, setUpload] = useState<Row | null>(null);
  const [edit, setEdit] = useState<Row | null>(null);
  const [folderEditor, setFolderEditor] = useState<Row | null>(null);
  const [sharing, setSharing] = useState<Row | null>(null);
  const request = useRef(0);
  async function load() {
    const id = ++request.current;
    try {
      const [d, f] = await Promise.all([
        api<{ items: Row[] }>(
          `documents/items?archived=${archived ? "1" : "0"}`,
        ),
        api<{ items: Row[] }>("documents/folders"),
      ]);
      if (id !== request.current) return;
      setDocuments(d.items);
      setFolders(f.items);
      setError("");
    } catch (e) {
      if (id === request.current) setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
    return () => {
      request.current += 1;
    };
  }, [archived]);
  async function save(path: string, body: unknown, method = "PATCH") {
    setBusy(true);
    setError("");
    try {
      await api(path, method, body);
      await load();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  const rows = documents.filter(
    (d) =>
      (!filter || String(d.folder) === filter) &&
      `${d.title} ${d.filename}`
        .toLocaleLowerCase("fr")
        .includes(search.toLocaleLowerCase("fr")),
  );
  return (
    <section className="documents-space">
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <div className="document-toolbar">
        {section === "library" && (
          <>
            <label>
              Rechercher
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Titre ou nom du fichier"
              />
            </label>
            <label>
              Dossier
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="">Tous les dossiers</option>
                {folders.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
        {manager && section === "library" && (
          <>
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={archived}
                onChange={(e) => setArchived(e.target.checked)}
              />
              Inclure les archives
            </label>
            <button className="button primary" onClick={() => setUpload({})}>
              <Icon name="plus" size={16} />
              Déposer un document
            </button>
          </>
        )}
        {manager && section === "folders" && (
          <button
            className="button primary"
            onClick={() => setFolderEditor({})}
          >
            <Icon name="plus" size={16} />
            Créer un dossier
          </button>
        )}
      </div>
      {section === "folders" ? (
        <div className="document-grid">
          {folders.map((f) => (
            <article className="document-card" key={f.id}>
              <Icon name="folder" size={25} />
              <h3>{f.name}</h3>
              <p>
                {
                  documents.filter((d) => d.folder === f.id && !d.archived)
                    .length
                }{" "}
                document(s) non archivés
              </p>
              <button
                className="button secondary"
                onClick={() => setFolderEditor(f)}
              >
                Renommer
              </button>
            </article>
          ))}
          {!folders.length && (
            <Empty
              title="Créez votre premier dossier"
              description="Regroupez par exemple les contrats, les factures ou les comptes rendus."
            />
          )}
        </div>
      ) : (
        <div className="document-grid">
          {rows.map((d) => (
            <article
              className={`document-card ${d.archived ? "archived" : ""}`}
              key={d.id}
            >
              <div className="document-card-heading">
                <Icon name="file" size={25} />
                <span className="subtle-badge">
                  {d.archived
                    ? "Archivé"
                    : d.published
                      ? "Partagé"
                      : "Gestionnaires"}
                </span>
              </div>
              <h3>{d.title}</h3>
              <p>{d.folder_name}</p>
              <small>
                {d.filename} · {size(d.size)}
              </small>
              <div className="document-actions">
                <a
                  className="button secondary"
                  href={`/api/documents/items/${d.id}/download/`}
                >
                  Télécharger
                </a>
                {manager && (
                  <>
                    <button className="edit-button" onClick={() => setEdit(d)}>
                      Modifier
                    </button>
                    {!d.archived && (
                      <>
                        <button
                          className="edit-button"
                          onClick={() => setUpload(d)}
                        >
                          Nouvelle version
                        </button>
                        <button
                          className="edit-button"
                          onClick={() => setSharing(d)}
                        >
                          {d.published ? "Retirer le partage" : "Partager"}
                        </button>
                      </>
                    )}
                    <button
                      className="edit-button"
                      disabled={busy}
                      onClick={() =>
                        void save(`documents/items/${d.id}`, {
                          archived: !d.archived,
                        })
                      }
                    >
                      {d.archived ? "Restaurer" : "Archiver"}
                    </button>
                  </>
                )}
              </div>
              {manager && d.versions.length > 0 && (
                <details className="document-history">
                  <summary>{d.versions.length} version(s)</summary>
                  <ul>
                    {d.versions.map((v: Row) => (
                      <li key={v.id}>
                        <a href={`/api/documents/versions/${v.id}/download/`}>
                          {new Date(v.created_at).toLocaleDateString("fr-FR")} ·{" "}
                          {v.filename}
                        </a>
                        <small>
                          {v.author} · {size(v.size)}
                        </small>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </article>
          ))}
          {!rows.length && (
            <Empty
              title={
                manager
                  ? "Aucun document dans cette sélection"
                  : "Aucun document partagé"
              }
              description={
                manager
                  ? "Déposez un PDF, PNG ou JPEG. Vous pourrez ensuite choisir de le partager avec les copropriétaires."
                  : "Les documents publiés par les gestionnaires apparaîtront ici."
              }
            />
          )}
        </div>
      )}
      {upload && (
        <DocumentDialog
          title={upload.id ? "Ajouter une version" : "Déposer un document"}
          busy={busy}
          error={error}
          onClose={() => setUpload(null)}
          onSubmit={async (form) => {
            const body = new FormData(form);
            if (!upload.id) body.set("published", "false");
            if (
              await save(
                upload.id
                  ? `documents/items/${upload.id}/upload`
                  : "documents/items",
                body,
                "POST",
              )
            )
              setUpload(null);
          }}
        >
          {!upload.id && (
            <>
              <label>
                Titre
                <input required name="title" maxLength={150} />
              </label>
              <label>
                Dossier
                <select name="folder" defaultValue={filter}>
                  <option value="">Sans dossier</option>
                  {folders.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          <label>
            Fichier
            <input
              required
              name="file"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
            />
          </label>
          <p className="muted">
            PDF, PNG ou JPEG, 10 Mo maximum.{" "}
            {upload.id
              ? "La version précédente est conservée. Si le document est partagé, cette nouvelle version sera accessible aux copropriétaires."
              : "Le document sera réservé aux gestionnaires. Vous pourrez le partager ensuite."}
          </p>
        </DocumentDialog>
      )}
      {edit && (
        <DocumentDialog
          title="Modifier le document"
          busy={busy}
          error={error}
          onClose={() => setEdit(null)}
          onSubmit={async (form) => {
            const body = new FormData(form);
            if (
              await save(`documents/items/${edit.id}`, {
                title: body.get("title"),
                folder: body.get("folder") || null,
              })
            )
              setEdit(null);
          }}
        >
          <label>
            Titre
            <input
              name="title"
              required
              maxLength={150}
              defaultValue={edit.title}
            />
          </label>
          <label>
            Dossier
            <select name="folder" defaultValue={edit.folder || ""}>
              <option value="">Sans dossier</option>
              {folders.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </label>
        </DocumentDialog>
      )}
      {folderEditor && (
        <DocumentDialog
          title={folderEditor.id ? "Renommer le dossier" : "Créer un dossier"}
          busy={busy}
          error={error}
          onClose={() => setFolderEditor(null)}
          onSubmit={async (form) => {
            const name = new FormData(form).get("name");
            if (
              await save(
                folderEditor.id
                  ? `documents/folders/${folderEditor.id}`
                  : "documents/folders",
                { name },
                folderEditor.id ? "PATCH" : "POST",
              )
            )
              setFolderEditor(null);
          }}
        >
          <label>
            Nom du dossier
            <input
              name="name"
              required
              maxLength={150}
              defaultValue={folderEditor.name || ""}
            />
          </label>
        </DocumentDialog>
      )}
      {sharing && (
        <DocumentDialog
          title={
            sharing.published ? "Retirer le partage" : "Partager ce document ?"
          }
          busy={busy}
          error={error}
          onClose={() => setSharing(null)}
          onSubmit={async () => {
            if (
              await save(`documents/items/${sharing.id}`, {
                published: !sharing.published,
              })
            )
              setSharing(null);
          }}
        >
          <p>
            {sharing.published
              ? "Les copropriétaires ne pourront plus télécharger ce document depuis leur espace."
              : "Tous les copropriétaires ayant un accès pourront télécharger ce document. Vérifiez qu’il ne contient pas de coordonnées, soldes individuels ou autres informations privées."}
          </p>
          <strong>{sharing.title}</strong>
        </DocumentDialog>
      )}
    </section>
  );
}

function DocumentDialog({
  title,
  busy,
  error,
  children,
  onClose,
  onSubmit,
}: {
  title: string;
  busy: boolean;
  error: string;
  children: React.ReactNode;
  onClose: () => void;
  onSubmit: (form: HTMLFormElement) => Promise<void>;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      className="editor-dialog document-dialog"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void onSubmit(e.currentTarget);
        }}
      >
        <div className="dialog-heading">
          <h2>{title}</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Fermer"
            disabled={busy}
            onClick={onClose}
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="dialog-body">
          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}
          {children}
        </div>
        <div className="dialog-footer">
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={onClose}
          >
            Annuler
          </button>
          <button className="button primary" disabled={busy}>
            {busy ? "Enregistrement…" : "Confirmer"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
