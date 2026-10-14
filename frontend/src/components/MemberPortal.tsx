import { useEffect, useState } from "react";
import { api, type User, type Lot, type Overview } from "../api";
import { kinds, number } from "../format";
import { BrandMark } from "./BrandMark";
import { ChangePassword } from "./Access";
import { Finance } from "./Finance";
import { PersonalAccount } from "./Operations";
import { Documents } from "./Documents";
import { SharedNotices } from "./PartnerRecords";
import { SharedAssemblyDecisions } from "./AssemblyWorkflow";
export function MemberPortal({
  user,
  onUser,
  onLogout,
}: {
  user: User;
  onUser: (user: User) => void;
  onLogout: () => Promise<void>;
}) {
  const [lots, setLots] = useState<Lot[]>([]);
  const [stats, setStats] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [password, setPassword] = useState(false);
  useEffect(() => {
    if (user.must_change_password || user.is_former_owner) return;
    Promise.all([api<{ items: Lot[] }>("lots"), api<Overview>("overview")])
      .then(([l, s]) => {
        setLots(l.items);
        setStats(s);
      })
      .catch((e) => setError(e.message));
  }, [user]);
  return (
    <div className="member-shell">
      <header className="member-header">
        <a className="brand" href="/">
          <BrandMark />
          Copro.
        </a>
        <div>
          <span className="subtle-badge">Lecture seule</span>
          <button
            className="button secondary"
            onClick={() => setPassword(true)}
          >
            Mon mot de passe
          </button>
          <button className="button secondary" onClick={() => void onLogout()}>
            Se déconnecter
          </button>
        </div>
      </header>
      <main>
        <p className="eyebrow">ESPACE COPROPRIÉTAIRE</p>
        <h1>Bonjour {user.display_name || user.username}</h1>
        <p className="muted">
          {user.is_former_owner
            ? "Après la cession de vos lots, vous conservez l’accès à votre compte individuel."
            : "Consultez les informations partagées de votre immeuble."}
        </p>
        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}
        {user.must_change_password || password ? (
          <ChangePassword
            mandatory={user.must_change_password}
            onCancel={() =>
              user.must_change_password ? void onLogout() : setPassword(false)
            }
            onChanged={(u) => {
              onUser(u);
              setPassword(false);
            }}
          />
        ) : (
          <>
            <PersonalAccount />
            {!user.is_former_owner && (
              <>
                <SharedNotices />
                <SharedAssemblyDecisions />
                <section className="stats-grid">
                  {[
                    ["Lots", stats?.lots_count || 0],
                    ["Copropriétaires", stats?.owners_count || 0],
                    ["Tantièmes généraux", number(stats?.shares_total || 0)],
                  ].map(([label, value]) => (
                    <article className="stat-card" key={label}>
                      <p>{label}</p>
                      <strong>{value}</strong>
                    </article>
                  ))}
                </section>
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Les lots de la copropriété</h2>
                      <p>
                        Les coordonnées et les comptes individuels des autres
                        copropriétaires sont privés.
                      </p>
                    </div>
                  </div>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Lot</th>
                          <th>Type</th>
                          <th>Étage</th>
                          <th>Surface</th>
                          <th>Tantièmes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {lots.map((l) => (
                          <tr key={l.id}>
                            <td>{l.number}</td>
                            <td>{kinds[l.kind]}</td>
                            <td>{l.floor || "—"}</td>
                            <td>{l.area ? `${number(l.area)} m²` : "—"}</td>
                            <td>{number(l.shares)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!lots.length && (
                    <div className="empty-state">
                      <p>Aucun lot n’est encore enregistré.</p>
                    </div>
                  )}
                </section>
                <Finance manager={false} />
                <section className="member-documents">
                  <h2>Documents partagés</h2>
                  <Documents manager={false} />
                </section>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
