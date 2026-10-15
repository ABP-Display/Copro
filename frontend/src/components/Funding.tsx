import { useEffect, useState } from "react";
import { api, newOperationId } from "../api";
import "./regulatory.css";

type Row = Record<string, any>;
const euro = (v: string | number) => new Intl.NumberFormat("fr-FR", {style:"currency",currency:"EUR"}).format(Number(v));
const today = () => new Date().toLocaleDateString("en-CA");
export function Funding() {
  const [years,setYears] = useState<Row[]>([]), [year,setYear] = useState("");
  const [data,setData] = useState<Row|null>(null), [policy,setPolicy] = useState<Row>({});
  const [refund,setRefund] = useState<Row|null>(null), [busy,setBusy] = useState(false);
  const [error,setError] = useState(""), [notice,setNotice] = useState("");
  useEffect(() => { api<{items:Row[]}>("finance/years").then(r => {setYears(r.items);setYear(String(r.items.find(y=>!y.closed&&y.starts_on<=today()&&y.ends_on>=today())?.id || r.items.find(y=>!y.closed)?.id || r.items[0]?.id || ""));}).catch(e=>setError(e.message)); },[]);
  async function load(selected=year) {
    if (!selected) return;
    const r = await api<Row>(`finance/funding/context?year=${selected}`);
    setData(r);setPolicy(r.policy);
  }
  useEffect(() => { let alive=true;setData(null);setRefund(null);setError("");
    if(year) api<Row>(`finance/funding/context?year=${year}`).then(r=>{if(alive){setData(r);setPolicy(r.policy);}}).catch(e=>{if(alive)setError(e.message);});
    return()=>{alive=false;}; },[year]);
  const update = (key:string,value:any) => setPolicy(p=>({...p,[key]:value}));
  async function send(path:string,body:Row) {
    setBusy(true);setError("");setNotice("");
    try {await api(`finance/funding/${path}`,"POST",{...body,year,request_id:newOperationId()});
      await load();setRefund(null);setNotice("Enregistrement effectué. Les contrôles ont été recalculés.");
    } catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  }
  const selectProof = (key:string,label:string) => <label>{label}<select value={policy[key]||""} onChange={e=>update(key,e.target.value||null)}><option value="">À choisir dans Documents</option>{data?.versions.map((v:Row)=><option key={v.id} value={v.id}>{v.label}</option>)}</select></label>;
  const input = (key:string,label:string,type="text") => <label>{label}<input type={type} min={type==="number"?"0":undefined} step={type==="number"?"0.01":undefined} maxLength={type==="text"?250:undefined} value={policy[key]??""} onChange={e=>update(key,e.target.value)}/></label>;
  return <div className="funding-page">
    <header className="cycle-toolbar">
      <label>Exercice<select value={year} onChange={e=>setYear(e.target.value)}>{years.map(y=><option key={y.id} value={y.id}>{y.name}{y.closed?" · clôturé":""}</option>)}</select></label></header>
    {error&&<p className="alert error" role="alert">{error}</p>}{notice&&<p className="alert success" role="status">{notice}</p>}
    {!years.length&&<section className="panel"><p>Créez d’abord un exercice dans Gestion comptable → Exercice & clôture.</p></section>}
    {data&&<>
      <section className="panel funding-intro"><h2>Deux réserves, deux usages</h2><div className="funding-cards"><article><strong>Fonds travaux · 105</strong><p>Attaché au lot, conservé par la copropriété lors d’une vente. Les versements disponibles servent aux travaux autorisés.</p></article><article><strong>Avances · 103</strong><p>Réserve de trésorerie, avance du PPT ou besoin temporaire : seules les sommes effectivement versées et encore disponibles peuvent être restituées à leur titulaire.</p></article></div><p className="muted">Les appels se préparent dans Appels de fonds. L’affectation du 105 et la clôture des opérations restent dans Fonds & travaux votés.</p></section>
      <section className="panel"><h2>Contrôles des décisions annuelles</h2><div className="funding-cards"><article><span>Minimum annuel du fonds</span><strong>{euro(data.rules.minimum)}</strong><small>Contrôle au {data.rules.as_of}{data.rules.required_from?` · dix ans le ${data.rules.required_from}`:""}</small></article><article><span>Plafond de réserve 1031</span><strong>{euro(data.rules.reserve_ceiling)}</strong><small>Un sixième du budget, soldes antérieurs compris</small></article><article><span>Suspension du fonds</span><strong>{data.rules.suspension_possible?"Seuils atteints":"Seuils non atteints"}</strong><small>Une décision d’AG reste nécessaire</small></article></div>
        {data.rules.errors.length>0&&<div className="alert error"><strong>À compléter ou à corriger</strong><ul>{data.rules.errors.map((s:string)=><li key={s}>{s}</li>)}</ul></div>}
        <details><summary>Comprendre les règles et les points à vérifier</summary><ul>{data.rules.warnings.map((s:string)=><li key={s}>{s}</li>)}</ul><p>Minimum : 5 % du budget ; si un PPT est adopté, le plus élevé de 5 % du budget et 2,5 % du coût total de ses travaux. La suspension suppose un fonds supérieur au budget et, avec un PPT adopté, supérieur également à 50 % de ses travaux.</p>{data.rules.sources.map((s:Row)=><p key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></p>)}</details>
      </section>
      <form className="panel" onSubmit={e=>{e.preventDefault();void send("policy",policy);}}><h2>Paramétrage de l’exercice {years.find(y=>String(y.id)===year)?.name}</h2><p className="muted">L’enregistrement d’un paramétrage incomplet reste possible ; ses erreurs seront visibles et bloqueront les nouveaux appels concernés. Il ne valide ni ne modifie les appels déjà publiés.</p>
        <fieldset disabled={busy||data.closed} className="funding-fields"><legend>Immeuble, budget et PPT</legend>
          <label>Destination<select value={policy.housing} onChange={e=>update("housing",e.target.value)}><option value="unknown">À renseigner</option><option value="housing">Habitation totale ou partielle</option><option value="other">Sans habitation</option></select></label>
          {input("received_on","Réception de l’immeuble","date")}{input("annual_budget","Budget prévisionnel voté (€)","number")}{input("budget_reference","Référence de son approbation")}
          <label>PPT adopté ?<select value={policy.ppt_adopted===null?"":String(policy.ppt_adopted)} onChange={e=>update("ppt_adopted",e.target.value===""?null:e.target.value==="true")}><option value="">À vérifier</option><option value="false">Non</option><option value="true">Oui</option></select></label>{input("ppt_amount","Coût total des travaux du PPT (€)","number")}
        </fieldset>
        <fieldset disabled={busy||data.closed} className="funding-fields"><legend>Fonds travaux</legend>{input("fund_contribution","Cotisation annuelle votée (€)","number")}{input("fund_reference","Décision de cotisation")}{selectProof("fund_proof","Pièce de la décision")}
          <label className="funding-check"><input type="checkbox" checked={policy.suspended} onChange={e=>update("suspended",e.target.checked)}/>Cotisations suspendues par décision d’AG</label>{input("suspension_reference","Décision de suspension")}{selectProof("suspension_proof","Pièce de la suspension")}
        </fieldset>
        <fieldset disabled={busy||data.closed} className="funding-fields"><legend>Avances</legend><label className="funding-check"><input type="checkbox" checked={policy.reserve_authorized} onChange={e=>update("reserve_authorized",e.target.checked)}/>Le règlement prévoit une réserve de trésorerie</label>{input("advance_reference","Règlement / décision et échéancier des avances")}{selectProof("advance_proof","Pièce justificative des avances")}</fieldset>
        <button className="button" disabled={busy||data.closed}>Enregistrer et contrôler</button>{data.closed&&<p>Exercice clôturé : paramétrage conservé en lecture.</p>}
      </form>
      <section className="panel"><h2>Avances par lot et titulaire</h2><p className="muted">Soldes actuels, tous exercices confondus. Après une vente, l’avance versée reste au nom de son titulaire historique. Une restitution bancaire enregistre un paiement déjà effectué ; elle ne déclenche aucun virement.</p>
        <div className="table-wrap"><table><thead><tr><th>Lot / titulaire</th><th>Compte</th><th>Constitué</th><th>Versé</th><th>Restitué / affecté</th><th>Disponible</th><th>Action</th></tr></thead><tbody>{data.advances.map((r:Row)=><tr key={`${r.lot}:${r.owner}:${r.code}`}><td><strong>Lot {r.lot_number}</strong><br/>{r.owner_name}</td><td>{r.code}</td><td>{euro(r.constituted)}</td><td>{euro(r.paid)}</td><td>{euro(r.refunded)} / {euro(r.used)}</td><td>{r.inconsistent?"À corriger":euro(r.refundable)}</td><td><button className="button secondary" disabled={busy||data.closed||r.inconsistent||Number(r.refundable)<=0} onClick={()=>setRefund({...r,amount:r.refundable,date:today(),method:"account",reference:"",proof:"",bank:""})}>{r.code==="1032"?"Gérer l’avance":"Restituer"}</button></td></tr>)}</tbody></table></div>{!data.advances.length&&<p>Aucune avance attribuée. Préparez un appel de type Avance, ou reprenez les soldes effectivement versés avec leur lot et leur titulaire.</p>}
      </section>
      {refund&&<form className="panel funding-refund" onSubmit={e=>{e.preventDefault();void send(refund.method==="works"?"use":"refund",refund);}}><h2>Utiliser ou restituer l’avance · lot {refund.lot_number}</h2><p>{refund.owner_name} · compte {refund.code} · disponible {euro(refund.refundable)}</p><fieldset disabled={busy} className="funding-fields"><legend>Pièce et comptabilisation</legend>{[["date","Date","date"],["amount","Montant (€)","number"],["reference","Référence de restitution","text"]].map(([key,label,type])=><label key={key}>{label}<input required type={type} step={type==="number"?"0.01":undefined} min={type==="number"?"0.01":undefined} max={type==="number"?refund.refundable:undefined} value={refund[key]} onChange={e=>setRefund({...refund,[key]:e.target.value})}/></label>)}
        <label>Justificatif<select required value={refund.proof} onChange={e=>setRefund({...refund,proof:e.target.value})}><option value="">Choisir une version documentaire</option>{data.versions.map((v:Row)=><option key={v.id} value={v.id}>{v.label}</option>)}</select></label>
        <label>Mode<select value={refund.method} onChange={e=>setRefund({...refund,method:e.target.value})}><option value="account">Crédit du compte copropriétaire 450</option><option value="bank">Règlement bancaire déjà effectué</option>{refund.code==="1032"&&<option value="works">Affectation aux travaux votés du PPT</option>}</select></label>
        {refund.method==="bank"&&<label>Banque courante<select required value={refund.bank} onChange={e=>setRefund({...refund,bank:e.target.value})}><option value="">Choisir</option>{data.banks.filter((b:Row)=>b.kind!=="works").map((b:Row)=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>}
        {refund.method==="works"&&<label>Opération votée<select required value={refund.project||""} onChange={e=>setRefund({...refund,project:e.target.value})}><option value="">Choisir des travaux ouverts</option>{data.projects.map((p:Row)=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>}
        <label className="funding-check"><input type="checkbox" required/>J’ai vérifié le titulaire, les versements et la pièce de restitution.</label></fieldset><div className="cycle-actions"><button className="button" disabled={busy}>{refund.method==="works"?"Confirmer l’affectation":"Confirmer la restitution"}</button><button type="button" className="button secondary" disabled={busy} onClick={()=>setRefund(null)}>Annuler</button></div></form>}
      <section className="panel"><h2>Avances PPT affectées aux travaux</h2><p className="muted">Une affectation consomme le disponible 1032 et finance le projet en 102. Le titulaire doit encore posséder le lot ; une avance du vendeur ne finance pas automatiquement les travaux de l’acquéreur.</p>{data.uses.map((r:Row)=><article key={r.id} className="funding-history"><div><strong>{euro(r.amount)} · {r.project}</strong><p>Lot {r.lot} · {r.owner} · {r.date} · {r.reference}{r.cancelled?" · corrigée":""}</p></div>{!r.cancelled&&!data.closed&&<button className="button secondary" disabled={busy} onClick={()=>{if(window.confirm("Contrepasser cette affectation dans l’exercice sélectionné, à la date du jour ?"))void send("cancel-use",{id:r.id,date:today()});}}>Corriger l’affectation</button>}</article>)}{!data.uses.length&&<p>Aucune avance affectée à des travaux.</p>}</section>
      <section className="panel"><h2>Historique des restitutions</h2>{data.refunds.map((r:Row)=><article key={r.id} className="funding-history"><div><strong>{euro(r.amount)} · {r.owner}</strong><p>Lot {r.lot} · {r.date} · {r.reference} · {r.cancelled?"corrigée":r.method==="bank"?"règlement enregistré":"crédit du compte"}</p></div>{!r.cancelled&&!data.closed&&<button className="button secondary" disabled={busy} onClick={()=>{if(window.confirm("Enregistrer l’écriture inverse de cette restitution dans l’exercice sélectionné, à la date du jour ?"))void send("cancel-refund",{id:r.id,date:today()});}}>Corriger</button>}</article>)}{!data.refunds.length&&<p>Aucune restitution enregistrée.</p>}</section>
    </>}
  </div>;
}
