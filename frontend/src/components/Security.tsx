import { useEffect, useRef, useState } from "react";
import { api, type User } from "../api";
import { ChangePassword } from "./Access";
import { Icon } from "./ui";
import "./security.css";

type SecurityStatus = { user: User; mfa_enabled: boolean; mfa_required: boolean; recovery_remaining: number };
type Setup = { secret: string; qr: string; expires_at: string };

export function SecurityButton({ onUser }: { onUser: (user: User) => void }) {
  const [open, setOpen] = useState(false);
  return <>
    <button className="button secondary security-account-button" onClick={() => setOpen(true)}>
      <Icon name="shield" size={16} /> Mon compte
    </button>
    {open && <SecurityDialog onUser={onUser} onClose={() => setOpen(false)} />}
  </>;
}

function SecurityDialog({ onUser, onClose }: { onUser: (user: User) => void; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog ref={dialog} className="editor-dialog security-dialog" onCancel={onClose} aria-labelledby="security-dialog-title">
    <div className="dialog-heading"><h2 id="security-dialog-title">Mon compte et ma sécurité</h2>
      <button className="icon-button" onClick={onClose} aria-label="Fermer"><Icon name="close" /></button>
    </div>
    <SecurityPanel onUser={onUser} />
  </dialog>;
}

export function SecurityPanel({ onUser, mandatory = false }: { onUser: (user: User) => void; mandatory?: boolean }) {
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [setup, setSetup] = useState<Setup | null>(null);
  const [codes, setCodes] = useState<string[]>([]);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [changePassword, setChangePassword] = useState(false);
  const [confirmedSaved, setConfirmedSaved] = useState(false);
  async function load() {
    const data = await api<SecurityStatus>("security/status");
    setStatus(data);
    return data;
  }
  useEffect(() => { void load().catch(e => setError(e.message)); }, []);
  async function act(action: "setup" | "confirm" | "disable" | "recovery") {
    setBusy(true); setError(""); setNotice("");
    try {
      const data = await api<Setup & { user: User; recovery_codes?: string[] }>(`security/${action}`, "POST", { password, code });
      if (action === "setup") setSetup(data);
      else {
        setSetup(null); setPassword(""); setCode("");
        setCodes(data.recovery_codes || []); setConfirmedSaved(false);
        await load();
        // Keep the mandatory enrolment screen open until the user has saved the codes.
        if (!data.recovery_codes?.length) onUser(data.user);
        setNotice(action === "disable" ? "Double authentification désactivée. Les autres sessions ont été révoquées." : "Votre sécurité a été mise à jour. Les autres sessions ont été révoquées.");
      }
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  function downloadCodes() {
    const blob = new Blob([`Copro. — codes de secours\nChaque code est utilisable une seule fois avec votre mot de passe.\nConservez-les à part du téléphone.\n\n${codes.join("\n")}\n`], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = "copro-codes-de-secours.txt"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="security-content">
    <div className="security-intro"><span className="section-icon"><Icon name="shield" /></span><div>
      <h2>Double authentification</h2>
      <p>Après votre mot de passe, votre application d’authentification fournit un code à six chiffres. Aucun SMS ni courriel n’est nécessaire.</p>
    </div></div>
    {(mandatory || status?.mfa_required) && <p className="security-note">La double authentification est obligatoire pour votre accès de gestion. Enregistrez vos codes de secours avant de continuer.</p>}
    {error && <p className="alert" role="alert">{error}</p>}
    {notice && <p className="security-success" role="status">{notice}</p>}
    {!status && !error && <p role="status">Chargement de votre sécurité…</p>}
    {codes.length > 0 ? <section className="security-recovery" aria-labelledby="recovery-title">
      <h3 id="recovery-title">Conservez vos dix codes de secours</h3>
      <p>Ils ne seront plus affichés. Chaque code permet une connexion avec votre mot de passe si votre téléphone est indisponible. Une nouvelle liste annule la précédente.</p>
      <div className="recovery-codes">{codes.map(value => <code key={value}>{value}</code>)}</div>
      <button className="button secondary" onClick={downloadCodes}>Télécharger mes codes</button>
      <label className="security-checkbox"><input type="checkbox" checked={confirmedSaved} onChange={e => setConfirmedSaved(e.target.checked)} />J’ai conservé mes codes dans un endroit sûr.</label>
      <button className="button primary" disabled={!confirmedSaved} onClick={() => { setCodes([]); if (status) onUser(status.user); }}>Terminer</button>
    </section> : status && <>
      <div className="security-status"><strong>{status.mfa_enabled ? "Protection activée" : "Protection à activer"}</strong>
        <span>{status.mfa_enabled ? `${status.recovery_remaining} code(s) de secours disponible(s)` : "Prévoyez une application compatible TOTP sur votre téléphone."}</span>
      </div>
      {setup ? <form onSubmit={e => { e.preventDefault(); void act("confirm"); }} className="security-form">
        <h3>1. Ajouter Copro. dans votre application</h3>
        <p>Scannez ce QR code avec votre application d’authentification. Il est créé localement par Copro. et expire après dix minutes.</p>
        <img className="security-qr" src={setup.qr} alt="QR code de configuration de la double authentification" />
        <details><summary>Utiliser une clé manuelle</summary><code className="security-secret">{setup.secret}</code><p>Compte : {status.user.username} · Type : TOTP · 6 chiffres · 30 secondes.</p></details>
        <h3>2. Vérifier le premier code</h3>
        <label>Code de l’application<input autoFocus inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e => setCode(e.target.value)} required /></label>
        <div className="security-actions"><button className="button primary" disabled={busy}>Activer et obtenir mes codes de secours</button><button type="button" className="button secondary" onClick={() => { setSetup(null); setPassword(""); setCode(""); }}>Annuler</button></div>
      </form> : <form className="security-form" onSubmit={e => { e.preventDefault(); void act(status.mfa_enabled ? "recovery" : "setup"); }}>
        <label>Mot de passe actuel<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
        {status.mfa_enabled && <label>Code de l’application ou code de secours<input autoComplete="one-time-code" value={code} onChange={e => setCode(e.target.value)} required maxLength={40} /><small>Un code déjà utilisé est refusé. Attendez le prochain code si nécessaire.</small></label>}
        <div className="security-actions">
          <button className="button primary" disabled={busy}>{busy ? "Vérification…" : status.mfa_enabled ? "Renouveler les codes de secours" : "Configurer mon application"}</button>
          {status.mfa_enabled && !status.mfa_required && <button type="button" className="button secondary" disabled={busy || !password || !code} onClick={() => void act("disable")}>Désactiver la double authentification</button>}
        </div>
      </form>}
      {!mandatory && !setup && <button className="text-link" onClick={() => setChangePassword(!changePassword)}>Changer mon mot de passe</button>}
      {changePassword && <ChangePassword onChanged={onUser} onCancel={() => setChangePassword(false)} />}
    </>}
  </div>;
}

type BackupRecord = { archive_id: string; action: string; filename: string; database_rows: number; files: number; size: number; created_at: string };
type BackupStatus = { require_managers: boolean; items: BackupRecord[]; events: { action: string; detail: string; created_at: string; user__username: string | null }[] };
const commands = [
  ["Installer l’outil une fois", "python -m pip install -r scripts/requirements.txt"],
  ["Sauvegarder et vérifier la restauration", "python scripts/backup.py create --verify --keep 7"],
  ["Vérifier une archive existante", "python scripts/backup.py verify backups/NOM.coprobackup"],
  ["Restaurer l’instance (remplace les données)", "python scripts/backup.py restore backups/NOM.coprobackup --confirm copro"],
];

export function BackupSettings({ isAdmin, onUser }: { isAdmin: boolean; onUser: (user: User) => void }) {
  const [data, setData] = useState<BackupStatus | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [required, setRequired] = useState(false);
  async function load() {
    const result = await api<BackupStatus>("security/backups"); setData(result); setRequired(result.require_managers);
  }
  useEffect(() => { if (isAdmin) void load().catch(e => setError(e.message)); }, [isAdmin]);
  if (!isAdmin) return <p className="alert">Cette section est réservée à l’administrateur principal.</p>;
  async function savePolicy(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setNotice(""); setBusy(true);
    const form = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const result = await api<{ user: User }>("security/policy", "POST", { ...form, require_managers: required });
      onUser(result.user); await load(); setNotice("Règle de sécurité enregistrée.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const latestCreated = data?.items.find(item => item.action === "created");
  const latestVerified = data?.items.find(item => item.action === "verified");
  const date = (value?: string) => value ? new Date(value).toLocaleString("fr-FR") : "Aucune opération enregistrée";
  return <div className="security-content">
    {error && <p className="alert" role="alert">{error}</p>}{notice && <p className="security-success" role="status">{notice}</p>}
    <section className="panel security-card"><div className="panel-heading"><div><h2>Sauvegarder ensemble la base et les pièces</h2><p>Les archives chiffrées comprennent PostgreSQL et toutes les versions des documents. La vérification restaure réellement une copie isolée et compare les empreintes.</p></div><button className="button secondary" onClick={() => void load().catch(e => setError(e.message))}>Actualiser</button></div>
      <div className="security-summary"><article><span>Dernière sauvegarde</span><strong>{date(latestCreated?.created_at)}</strong></article><article><span>Dernière restauration de contrôle réussie</span><strong>{date(latestVerified?.created_at)}</strong></article></div>
      <p className="security-note">Les opérations se lancent sur le serveur depuis le dossier du projet. La création suspend brièvement l’application ; la vérification isolée peut ensuite continuer pendant son utilisation. Conservez la phrase secrète et le fichier .env séparément des archives.</p>
      <div className="security-commands">{commands.map(([title, command]) => <div key={command}><strong>{title}</strong><code>{command}</code></div>)}</div>
      <p>Pour une exécution programmée, utilisez le Planificateur de tâches Windows ou cron avec un secret fourni par le serveur. La rétention ne supprime que les anciennes archives de cet outil dont la restauration a été vérifiée.</p>
      <a className="text-link" href="https://github.com/abp-display/Copro/blob/master/docs/guides/SAUVEGARDE-SECURITE.md" target="_blank" rel="noreferrer">Lire le guide de sauvegarde et de reprise</a>
      <div className="table-scroll"><table><thead><tr><th>Date</th><th>Opération</th><th>Archive</th><th>Contrôle</th></tr></thead><tbody>{data?.items.map((item, index) => <tr key={`${item.archive_id}-${index}`}><td>{date(item.created_at)}</td><td>{{ created: "Créée", verified: "Restauration vérifiée", restored: "Restaurée" }[item.action] || item.action}</td><td className="security-filename">{item.filename}</td><td>{item.database_rows} lignes · {item.files} pièces</td></tr>)}</tbody></table></div>
      {data && !data.items.length && <p className="muted">Aucune sauvegarde n’a encore été enregistrée par l’outil.</p>}
    </section>
    <section className="panel security-card"><div className="panel-heading"><div><h2>Exiger la double authentification pour la gestion</h2><p>Activez d’abord votre propre protection dans « Mon compte ». La règle concerne les accès de gestion permanents et ceux accordés par mandat.</p></div></div>
      <form className="security-form" onSubmit={savePolicy}>
        <label className="security-checkbox"><input type="checkbox" checked={required} onChange={e => setRequired(e.target.checked)} />Double authentification obligatoire pour les gestionnaires</label>
        <label>Votre mot de passe<input type="password" name="password" autoComplete="current-password" required /></label>
        <label>Votre code d’authentification ou code de secours<input name="code" autoComplete="one-time-code" maxLength={40} /></label>
        <button className="button primary" disabled={busy}>Enregistrer la règle</button>
      </form>
    </section>
    <section className="panel security-card"><div className="panel-heading"><div><h2>Historique de sécurité</h2><p>Activations, connexions à double facteur, changements de règle et récupérations serveur.</p></div></div>
      <div className="table-scroll"><table><thead><tr><th>Date</th><th>Compte</th><th>Action</th><th>Précision</th></tr></thead><tbody>{data?.events.map((event, index) => <tr key={index}><td>{date(event.created_at)}</td><td>{event.user__username || "Compte supprimé"}</td><td>{securityEventLabel(event.action)}</td><td>{event.detail || "—"}</td></tr>)}</tbody></table></div>
    </section>
  </div>;
}

function securityEventLabel(action: string) {
  return ({ "mfa.enabled": "Double authentification activée", "mfa.disable": "Double authentification désactivée", "mfa.recovery": "Codes de secours renouvelés", "mfa.login": "Connexion à double facteur", "mfa.policy": "Règle de sécurité modifiée", "access.emergency": "Récupération par le serveur" } as Record<string, string>)[action] || action;
}

export function BackupReminder({ onOpen }: { onOpen: () => void }) {
  const [data, setData] = useState<BackupStatus | null>(null);
  useEffect(() => { void api<BackupStatus>("security/backups").then(setData).catch(() => {}); }, []);
  if (!data) return null;
  const verified = data.items.find(item => item.action === "verified");
  const created = data.items.find(item => item.action === "created");
  const old = !verified || Date.now() - new Date(verified.created_at).getTime() > 48 * 3600 * 1000;
  const pending = created && created.archive_id !== verified?.archive_id;
  if (!old && !pending) return null;
  return <div className="security-note security-home-note"><div><strong>{!verified ? "Vérifiez votre première sauvegarde" : pending ? "Une sauvegarde attend son contrôle de restauration" : "Contrôlez la fraîcheur de vos sauvegardes"}</strong><p>{!verified ? "Aucune restauration de contrôle réussie n’est enregistrée pour cette instance." : "La dernière archive créée n’est pas vérifiée, ou le dernier contrôle enregistré remonte à plus de 48 heures."}</p></div><button className="button secondary" onClick={onOpen}>Sauvegardes & reprise</button></div>;
}
