// Set this to the deployed Render API URL before publishing. For local use, keep localhost.
const API_BASE_URL = "https://climate-policy-agent-api.onrender.com";
const form=document.getElementById("ask-form"), questionInput=document.getElementById("question");
const locationInput=document.getElementById("location"), button=document.getElementById("submit");
const statusBox=document.getElementById("status"), resultsSection=document.getElementById("results");
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function safeLink(url,label){const a=el("a","",label||url);a.href=url;a.target="_blank";a.rel="noopener noreferrer";return a;}
function renderRecommendations(items){
 const box=document.getElementById("recommendations");box.replaceChildren();
 if(!items.length){box.append(el("article","card","No clear policy-action passages were extracted. Inspect the sources below or try a more focused question."));return;}
 items.forEach((x,i)=>{const c=el("article","card");c.append(el("span","tag",x.support_level+" · "+x.source_count+" source(s)"),el("h3","","Evidence-linked policy/action passage"),el("div","passage",x.recommendation),el("p","muted",x.caution));
 x.sources.forEach(s=>{const p=el("p","");p.append(document.createTextNode("Supporting source: "),safeLink(s.url,s.title));c.append(p,el("p","muted",s.source_type+" · "+s.evidence_basis));});
 (x.supporting_passages||[]).slice(0,2).forEach(t=>c.append(el("div","passage",t)));box.append(c);});
}
function renderSources(items){
 const box=document.getElementById("evidence");box.replaceChildren();
 items.forEach((x,i)=>{const c=el("article","card");c.append(el("span","tag","SOURCE "+(i+1)),el("h3","",x.title));
 const p=el("p","");p.append(safeLink(x.url,x.url));c.append(p,el("p","muted",x.source_type+" · "+x.page_status+" · "+x.evidence_basis));
 if(x.date)c.append(el("p","muted","Search date: "+x.date));if(x.snippet)c.append(el("div","passage","Search snippet: "+x.snippet));
 (x.passages||[]).forEach(v=>c.append(el("div","passage",v.text)));box.append(c);});
}
async function loadSkills(){
 try{const r=await fetch(API_BASE_URL+"/api/skills");if(!r.ok)return;const data=await r.json();const box=document.getElementById("skills");box.replaceChildren();
 data.forEach(s=>{const d=el("div","skill");d.append(el("strong","",s.name),el("p","muted",s.description));box.append(d);});}catch(_){}
}
form.addEventListener("submit",async e=>{
 e.preventDefault();const question=questionInput.value.trim();if(question.length<5)return;
 button.disabled=true;statusBox.textContent="Searching live sources, opening pages and comparing evidence…";resultsSection.hidden=true;
 try{
  const r=await fetch(API_BASE_URL+"/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({question,location:locationInput.value,max_results:8})});
  const data=await r.json();if(!r.ok)throw new Error(data.detail||"Request failed ("+r.status+")");
  renderRecommendations(data.recommendations||[]);renderSources(data.sources||[]);
  document.getElementById("rec-status").textContent=data.recommendation_status||"";
  const ul=document.getElementById("limitations");ul.replaceChildren();(data.limitations||[]).forEach(t=>ul.append(el("li","",t)));
  document.getElementById("method").textContent="Method: "+data.method+" · Queries: "+(data.queries||[]).join(" | ");
  resultsSection.hidden=false;statusBox.textContent="Reviewed "+(data.sources||[]).length+" live source(s). Check full source context before relying on findings.";
  loadSkills();
 }catch(err){statusBox.textContent="Search failed: "+err.message;}
 finally{button.disabled=false;}
});
