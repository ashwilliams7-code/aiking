
(function(){
  const email='ash@aiking.info';
  const doc=document.documentElement;
  doc.classList.add('js');
  const motionOK=window.matchMedia('(prefers-reduced-motion: no-preference)').matches;
  const finePointer=window.matchMedia('(pointer:fine)').matches;
  const saveData=!!(navigator.connection&&navigator.connection.saveData);

  /* ---------- focus trap utility ---------- */
  const FOCUSABLE='a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
  function trapFocus(container,e){
    const f=Array.from(container.querySelectorAll(FOCUSABLE)).filter(el=>el.offsetParent!==null||el===document.activeElement);
    if(!f.length) return;
    const first=f[0],last=f[f.length-1];
    if(!container.contains(document.activeElement)){e.preventDefault();first.focus();return;}
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  }

  /* ---------- briefing builder: guided three-step intake ----------
     One component, mounted inline (contact page) and as a modal built
     at body level on demand. Sends via the visitor's own mail client
     by default; if a meta[name="briefing-endpoint"] or
     window.AIKING_BRIEFING_ENDPOINT is present, POSTs JSON there and
     falls back to the mail draft on failure. */
  const year=document.querySelector('[data-year]');
  if(year) year.textContent=new Date().getFullYear();

  const DRAFT_KEY='aiking-briefing-draft';
  const FIELDS=['name','role','organisation','email','timeframe','maturity','outcome'];
  const TIMEFRAMES=['Exploring now','Next 30 days','Next quarter','Later this year'];
  const MATURITY=["Haven't started",'Individual tools in use','Pilots underway','Systems in production'];
  const endpointMeta=document.querySelector('meta[name="briefing-endpoint"]');
  const endpoint=(endpointMeta&&endpointMeta.content)||window.AIKING_BRIEFING_ENDPOINT||'';

  let brfRef='';
  function briefRef(){
    if(brfRef) return brfRef;
    try{
      brfRef=sessionStorage.getItem('aiking-brf-ref')||'';
      if(!brfRef){ brfRef='BRF-'+Math.random().toString(36).slice(2,6).toUpperCase(); sessionStorage.setItem('aiking-brf-ref',brfRef); }
    }catch(_){ if(!brfRef) brfRef='BRF-'+Math.random().toString(36).slice(2,6).toUpperCase(); }
    return brfRef;
  }
  let bbSeq=0; /* ids must stay unique across mounts — contact.html carries both the inline form and the modal */
  function chipGroup(name,options,required,uid){
    return '<div class="bb-chips" role="radiogroup" aria-labelledby="'+uid+'-'+name+'-label">'+options.map(o=>(
      '<label class="bb-chip"><input type="radio" name="'+name+'" value="'+o.replace(/"/g,'&quot;')+'"'+(required?' required aria-describedby="'+uid+'-'+name+'-err"':'')+'><span>'+o+'</span></label>'
    )).join('')+'</div>';
  }
  function briefingMarkup(){
    const uid='bb'+(++bbSeq);
    return '<form class="bb" novalidate data-bb>'+
      '<div class="bb-top"><span class="bb-ref">Private &amp; confidential</span><span class="bb-meta">Step <b data-bb-num>01</b> / 03</span></div>'+
      '<div class="bb-rail"><i data-bb-rail></i></div>'+
      '<div class="bb-viewport" data-bb-viewport>'+
        '<fieldset class="bb-step active" data-step="1">'+
          '<legend class="bb-legend" tabindex="-1"><i>01</i>Who the briefing is for</legend>'+
          '<div class="bb-grid">'+
            '<label class="bb-field">Name<input name="name" autocomplete="name" required><em class="bb-err" aria-live="polite"></em></label>'+
            '<label class="bb-field">Role<input name="role" autocomplete="organization-title" required><em class="bb-err" aria-live="polite"></em></label>'+
            '<label class="bb-field">Company<input name="organisation" autocomplete="organization" required><em class="bb-err" aria-live="polite"></em></label>'+
            '<label class="bb-field">Email<input name="email" type="email" inputmode="email" autocomplete="email" required><em class="bb-err" aria-live="polite"></em></label>'+
          '</div>'+
        '</fieldset>'+
        '<fieldset class="bb-step" data-step="2">'+
          '<legend class="bb-legend" tabindex="-1"><i>02</i>Where things stand</legend>'+
          '<div class="bb-choice"><span class="bb-choice-label" id="'+uid+'-timeframe-label">Timeframe</span>'+chipGroup('timeframe',TIMEFRAMES,true,uid)+'<em class="bb-err" id="'+uid+'-timeframe-err" aria-live="polite"></em></div>'+
          '<div class="bb-choice"><span class="bb-choice-label" id="'+uid+'-maturity-label">Where AI sits today</span>'+chipGroup('maturity',MATURITY,false,uid)+'</div>'+
          '<label class="bb-field bb-area"><span class="bb-area-label">What should AI change in your business?</span>'+
            '<textarea name="outcome" rows="4" required maxlength="1200" placeholder="Example: lead follow-up, reporting, audit and assurance, operations coordination, customer service or executive decision support..."></textarea>'+
            '<span class="bb-count" aria-hidden="true"><b data-bb-count>0</b>/1200</span><em class="bb-err" aria-live="polite"></em>'+
          '</label>'+
        '</fieldset>'+
        '<fieldset class="bb-step" data-step="3">'+
          '<legend class="bb-legend" tabindex="-1"><i>03</i>Review your briefing</legend>'+
          '<div class="bb-doc" data-bb-doc></div>'+
          '<p class="form-note">Goes directly to Ash Williams, who reads every briefing personally. Confidential — never a mailing list.</p>'+
        '</fieldset>'+
      '</div>'+
      '<input class="bb-hp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">'+
      '<div class="bb-nav">'+
        '<button type="button" class="btn secondary small bb-back" data-bb-back hidden>Back</button>'+
        '<button type="submit" class="btn primary bb-next" data-bb-next><span class="bb-next-label">Continue</span> <span class="arrow">→</span></button>'+
      '</div>'+
      '<p class="bb-hint" data-bb-hint>Draft saves automatically in your browser.</p>'+
      '<div class="bb-sr" aria-live="polite" data-bb-live></div>'+
      '<div class="bb-done" data-bb-done hidden>'+
        '<svg class="bb-tick" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="30"/><path d="M20 33.5 28.5 42 45 24"/></svg>'+
        '<h3>Briefing drafted.</h3>'+
        '<p data-bb-donemsg>Your email app should now be open with the full briefing. Review it and press send — Ash replies personally.</p>'+
        '<div class="bb-done-actions">'+
          '<a class="btn primary" data-bb-mailto href="mailto:ash@aiking.info">Open email draft <span class="arrow">→</span></a>'+
          '<button type="button" class="btn secondary" data-bb-copy>Copy briefing</button>'+
        '</div>'+
        '<p class="form-note">Held in strict confidence — <a href="/privacy.html">how your details are handled</a>. Prefer to write instead? <a href="mailto:ash@aiking.info">ash@aiking.info</a></p>'+
      '</div>'+
    '</form>';
  }

  function wireBriefing(form){
    if(!form) return;
    const steps=Array.from(form.querySelectorAll('.bb-step'));
    const viewport=form.querySelector('[data-bb-viewport]');
    const rail=form.querySelector('[data-bb-rail]');
    const num=form.querySelector('[data-bb-num]');
    const back=form.querySelector('[data-bb-back]');
    const next=form.querySelector('[data-bb-next]');
    const nextLabel=form.querySelector('.bb-next-label');
    const hint=form.querySelector('[data-bb-hint]');
    const live=form.querySelector('[data-bb-live]');
    const doc=form.querySelector('[data-bb-doc]');
    const count=form.querySelector('[data-bb-count]');
    const ta=form.querySelector('textarea[name="outcome"]');
    const ref=briefRef();
    const stepNames={1:'who the briefing is for',2:'where things stand',3:'review your briefing'};
    let cur=1,sent=false,saveT=null;

    function fields(){ const fd=new FormData(form); const o={}; FIELDS.forEach(k=>o[k]=(fd.get(k)||'').toString().trim()); return o; }
    function esc(s){ return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

    function saveDraft(){ clearTimeout(saveT); saveT=setTimeout(()=>{ try{localStorage.setItem(DRAFT_KEY,JSON.stringify(fields()));}catch(_){}} ,350); }
    function restoreDraft(){
      let d=null; try{ d=JSON.parse(localStorage.getItem(DRAFT_KEY)||'null'); }catch(_){}
      if(!d) return;
      let had=false;
      FIELDS.forEach(k=>{
        if(!d[k]) return;
        if(k==='timeframe'||k==='maturity'){
          form.querySelectorAll('input[name="'+k+'"]').forEach(r=>{ if(r.value===d[k]){ r.checked=true; had=true; } });
        }else{
          const el=form.querySelector('[name="'+k+'"]'); if(el){ el.value=d[k]; had=true; }
        }
      });
      if(had&&hint) hint.textContent='Draft restored — picking up where you left off.';
      if(ta) growTa();
      if(count&&ta) count.textContent=String(ta.value.length);
    }

    function sizeViewport(){ if(!viewport) return; const a=steps[cur-1]; requestAnimationFrame(()=>{ viewport.style.height=(a.offsetHeight+16)+'px'; }); } /* +16 = the viewport's 8px focus-ring padding, top+bottom */
    form._bbResize=sizeViewport;
    form._bbGrow=growTa;
    window.addEventListener('resize',sizeViewport,{passive:true});
    window.addEventListener('load',sizeViewport,{once:true});
    if(document.fonts&&document.fonts.ready) document.fonts.ready.then(()=>sizeViewport());
    function growTa(){ if(!ta) return; ta.style.height='auto'; if(ta.scrollHeight) ta.style.height=Math.min(ta.scrollHeight,420)+'px'; sizeViewport(); } /* scrollHeight is 0 inside display:none — leave auto rather than clipping to 0 */

    function setStep(n,focus){
      cur=n;
      steps.forEach(s=>{ const i=+s.dataset.step; s.classList.toggle('active',i===n); s.classList.toggle('bb-before',i<n); });
      if(rail) rail.style.width=(n/steps.length*100)+'%';
      if(num) num.textContent='0'+n;
      if(back) back.hidden=n===1;
      if(nextLabel) nextLabel.textContent=n===steps.length?'Send briefing request':'Continue';
      if(n===steps.length) renderDoc();
      sizeViewport();
      if(live) live.textContent='Step '+n+' of '+steps.length+' — '+stepNames[n];
      if(focus!==false){ const lg=steps[n-1].querySelector('.bb-legend'); if(lg) lg.focus({preventScroll:true}); }
    }

    function markErr(el,msg){ const f=el.closest('.bb-field,.bb-choice'); if(!f) return; f.classList.add('invalid'); const em=f.querySelector('.bb-err'); if(em) em.textContent=msg; }
    function clearErr(el){ const f=el.closest('.bb-field,.bb-choice'); if(!f) return; f.classList.remove('invalid'); const em=f.querySelector('.bb-err'); if(em) em.textContent=''; }
    function validateStep(n){
      const s=steps[n-1]; let ok=true,first=null;
      s.querySelectorAll('input[required]:not([type=radio]),textarea[required]').forEach(el=>{
        const v=el.value.trim(); let msg='';
        if(!v) msg='Required';
        else if(el.type==='email'&&!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) msg='Check this address';
        if(msg){ ok=false; markErr(el,msg); if(!first) first=el; } else clearErr(el);
      });
      const groups={};
      s.querySelectorAll('input[type=radio][required]').forEach(r=>{ (groups[r.name]=groups[r.name]||[]).push(r); });
      Object.keys(groups).forEach(k=>{
        const any=groups[k].some(r=>r.checked);
        const box=groups[k][0].closest('.bb-choice');
        if(!any){ ok=false; if(box){ box.classList.add('invalid'); const em=box.querySelector('.bb-err'); if(em) em.textContent='Pick one'; } if(!first) first=groups[k][0]; }
        else if(box){ box.classList.remove('invalid'); const em=box.querySelector('.bb-err'); if(em) em.textContent=''; }
      });
      if(!ok){ s.classList.remove('shake'); void s.offsetWidth; s.classList.add('shake'); sizeViewport(); if(first) first.focus(); }
      return ok;
    }

    function renderDoc(){
      if(!doc) return;
      const f=fields();
      const dt=new Intl.DateTimeFormat('en-AU',{timeZone:'Australia/Sydney',day:'2-digit',month:'short',year:'numeric'}).format(new Date());
      const rows=[
        ['prepared',dt+' · Sydney',0],
        ['from',f.name+' — '+f.role,1],['company',f.organisation,1],['reply to',f.email,1],
        ['timeframe',f.timeframe,2],['ai today',f.maturity||'Not specified',2]
      ];
      doc.innerHTML=rows.map((r,i)=>'<div class="bb-doc-row" style="--i:'+i+'"><span>'+r[0]+'</span><b>'+esc(r[1])+'</b>'+(r[2]?'<button type="button" class="bb-edit" data-bb-edit="'+r[2]+'">Edit</button>':'')+'</div>').join('')+
        '<div class="bb-doc-ask" style="--i:'+rows.length+'"><span>the ask</span><p>'+esc(f.outcome)+'</p><button type="button" class="bb-edit" data-bb-edit="2">Edit</button></div>';
      setTimeout(sizeViewport,40);
    }

    function mailParts(){
      const f=fields();
      const lines=['Name: '+f.name,'Role: '+f.role,'Company: '+f.organisation,'Email: '+f.email,'Timeframe: '+f.timeframe,'Where AI sits today: '+(f.maturity||'Not specified'),'','What AI should change in the business:',f.outcome,'','— Prepared on aiking.info'];
      return { subject:'Private briefing — '+f.name+(f.organisation?', '+f.organisation:''), body:lines.join('\n') };
    }

    function showDone(mailOpened){
      sent=true;
      const m=mailParts();
      const href='mailto:'+email+'?subject='+encodeURIComponent(m.subject)+'&body='+encodeURIComponent(m.body);
      form.classList.add('done');
      const done=form.querySelector('[data-bb-done]');
      const ml=form.querySelector('[data-bb-mailto]'); if(ml) ml.href=href;
      const msg=form.querySelector('[data-bb-donemsg]');
      if(!mailOpened){
        const h=form.querySelector('[data-bb-done] h3'); if(h) h.textContent='Briefing received.';
        if(msg) msg.textContent='Thank you. Ash reads every briefing personally and will reply to you directly.';
      }
      else if(dr&&msg){ /* default copy already references the draft */ }
      if(done){ done.hidden=false; const h=done.querySelector('h3'); if(h){ h.setAttribute('tabindex','-1'); setTimeout(()=>h.focus({preventScroll:true}),0); } }
      try{ localStorage.removeItem(DRAFT_KEY); }catch(_){}
      if(live) live.textContent='Briefing sent. Ash will reply personally.';
      const copy=form.querySelector('[data-bb-copy]');
      if(copy&&!copy.dataset.wired){
        copy.dataset.wired='1';
        copy.addEventListener('click',()=>{
          if(navigator.clipboard&&navigator.clipboard.writeText){
            navigator.clipboard.writeText(m.subject+'\n\n'+m.body).then(()=>{
              copy.textContent='Copied ✓'; setTimeout(()=>{ copy.textContent='Copy briefing'; },2400);
            }).catch(()=>{});
          }
        });
      }
    }

    function send(){
      if(sent) return;
      const hp=form.querySelector('.bb-hp');
      next.disabled=true; next.classList.add('sending');
      if(nextLabel) nextLabel.textContent='Preparing briefing';
      const m=mailParts();
      const href='mailto:'+email+'?subject='+encodeURIComponent(m.subject)+'&body='+encodeURIComponent(m.body);
      const finish=openMail=>{ next.disabled=false; next.classList.remove('sending'); if(openMail) window.location.href=href; showDone(openMail); };
      if(endpoint&&!(hp&&hp.value)){
        const f=fields(); f.ref=ref; f.page=location.pathname; f.website=(hp&&hp.value)||'';
        /* API enum codes; the mailto/summary keep the display strings */
        const TF={'Exploring now':'exploring_now','Next 30 days':'next_30_days','Next quarter':'next_quarter','Later this year':'later_this_year'};
        const MT={"Haven't started":'not_started','Individual tools in use':'individual_tools','Pilots underway':'pilots_underway','Systems in production':'systems_in_production'};
        f.timeframe=TF[f.timeframe]||f.timeframe;
        if(f.maturity) f.maturity=MT[f.maturity]||f.maturity; else delete f.maturity;
        const idem=ref+':'+(self.crypto&&crypto.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(36).slice(2,14));
        fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':idem},body:JSON.stringify(f)})
          .then(r=>{ if(!r.ok) throw 0; finish(false); })
          .catch(()=>finish(true));
      }else{
        setTimeout(()=>finish(true),motionOK?850:0);
      }
    }

    form.addEventListener('submit',e=>{
      e.preventDefault();
      if(form.classList.contains('done')) return;
      if(!validateStep(cur)) return;
      if(cur<steps.length) setStep(cur+1); else send();
    });
    if(back) back.addEventListener('click',()=>{ if(cur>1) setStep(cur-1); });
    form.addEventListener('click',e=>{ const b=e.target.closest('[data-bb-edit]'); if(b) setStep(+b.dataset.bbEdit); });
    form.addEventListener('input',e=>{
      const t=e.target;
      if(t.matches('input:not([type=radio]),textarea')) clearErr(t);
      if(t.type==='radio'){ const box=t.closest('.bb-choice'); if(box){ box.classList.remove('invalid'); const em=box.querySelector('.bb-err'); if(em) em.textContent=''; } }
      if(t===ta){ if(count) count.textContent=String(ta.value.length); growTa(); }
      saveDraft();
    });
    form.addEventListener('blur',e=>{
      const t=e.target;
      if(t.matches&&t.matches('input[type=email]')&&t.value.trim()&&!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(t.value.trim())) markErr(t,'Check this address');
    },true);

    restoreDraft();
    setStep(1,false);
  }

  /* modal shell — built at body level the first time it's needed */
  let modal=null,modalTrigger=null;
  function ensureModal(){
    if(modal) return modal;
    modal=document.createElement('div');
    modal.className='modal'; modal.hidden=true; modal.setAttribute('data-briefing-modal','');
    modal.innerHTML='<div class="modal-backdrop" data-close-briefing></div>'+
      '<div class="modal-panel bb-panel" data-lenis-prevent role="dialog" aria-modal="true" aria-labelledby="briefing-title">'+
        '<button class="modal-close" type="button" aria-label="Close briefing form" data-close-briefing>×</button>'+
        '<span class="section-kicker">Private briefing</span>'+
        '<h2 id="briefing-title">Request a private briefing.</h2>'+
        '<p class="lead">Three short steps — about two minutes. Ash reads every request personally and replies with the clearest way forward.</p>'+
        briefingMarkup()+
      '</div>';
    document.body.appendChild(modal);
    wireBriefing(modal.querySelector('[data-bb]'));
    modal.addEventListener('click',e=>{ if(e.target.closest('[data-close-briefing]')||e.target.matches('.modal-backdrop')) closeModal(); });
    return modal;
  }
  function openModal(trigger){
    ensureModal();
    modalTrigger=trigger||null; modal.hidden=false; document.body.classList.add('modal-open');
    const f=modal.querySelector('[data-bb]'); if(f&&f._bbGrow) f._bbGrow(); else if(f&&f._bbResize) f._bbResize();
    const target=finePointer?modal.querySelector('.bb-step.active input,.bb-step.active textarea')||modal.querySelector('#briefing-title'):modal.querySelector('.modal-panel');
    if(target){ if(!target.matches('input,textarea,button,a')) target.setAttribute('tabindex','-1'); setTimeout(()=>target.focus({preventScroll:true}),40); }
  }
  function closeModal(){ if(!modal||modal.hidden) return; modal.hidden=true; document.body.classList.remove('modal-open'); if(modalTrigger){modalTrigger.focus();modalTrigger=null;} }
  document.querySelectorAll('[data-open-briefing]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();openModal(el);}));
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){closeModal();closeNav();}
    if(e.key==='Tab'){
      if(modal&&!modal.hidden){trapFocus(modal.querySelector('.modal-panel')||modal,e);}
      else if(menu&&menu.classList.contains('open')){trapFocus(menu,e);}
    }
  });
  /* inline mounts (contact page) */
  document.querySelectorAll('[data-briefing-inline]').forEach(el=>{ el.innerHTML=briefingMarkup(); wireBriefing(el.querySelector('[data-bb]')); });
  /* pre-build the modal during idle so the first open is instant */
  if('requestIdleCallback' in window) requestIdleCallback(()=>ensureModal(),{timeout:4000}); else setTimeout(ensureModal,2500);

  /* ---------- header: shrink on scroll ---------- */
  const header=document.querySelector('.site-header');
  if(header){
    let ticking=false;
    const onScroll=()=>{ if(ticking) return; ticking=true; requestAnimationFrame(()=>{ header.classList.toggle('scrolled',window.scrollY>10); ticking=false; }); };
    window.addEventListener('scroll',onScroll,{passive:true}); onScroll();
  }

  /* ---------- mobile nav: burger + body-level overlay ---------- */
  const navLinks=document.querySelector('.nav-links');
  const navActions=document.querySelector('.nav-actions');
  let burger=null,menu=null;
  function closeNav(){ if(menu&&menu.classList.contains('open')){ menu.classList.remove('open'); menu.setAttribute('aria-hidden','true'); document.body.classList.remove('nav-lock'); if(burger){burger.setAttribute('aria-expanded','false');burger.focus();} } }
  if(header&&navLinks&&navActions){
    menu=document.createElement('div');
    menu.className='mobile-menu'; menu.setAttribute('aria-hidden','true');
    const mmNav=document.createElement('nav');
    mmNav.className='mm-links'; mmNav.setAttribute('aria-label','Mobile navigation');
    navLinks.querySelectorAll('a').forEach((a,i)=>{ const c=a.cloneNode(true); c.style.setProperty('--nd',(90+i*55)+'ms'); c.addEventListener('click',()=>closeNav()); mmNav.appendChild(c); });
    const mmClose=document.createElement('button');
    mmClose.className='mm-close'; mmClose.type='button'; mmClose.setAttribute('aria-label','Close menu');
    mmClose.innerHTML='<i></i><i></i>';
    mmClose.addEventListener('click',()=>closeNav());
    menu.appendChild(mmClose); menu.appendChild(mmNav);
    document.body.appendChild(menu);
    burger=document.createElement('button');
    burger.className='burger'; burger.type='button';
    burger.setAttribute('aria-label','Menu'); burger.setAttribute('aria-expanded','false');
    burger.innerHTML='<i></i><i></i>';
    navActions.appendChild(burger);
    burger.addEventListener('click',()=>{
      menu.classList.add('open'); menu.setAttribute('aria-hidden','false');
      document.body.classList.add('nav-lock');
      burger.setAttribute('aria-expanded','true');
      const firstLink=menu.querySelector('a,button'); if(firstLink) setTimeout(()=>firstLink.focus(),60);
    });
  }

  /* ---------- scroll reveals (motion-safe only) ---------- */
  if(motionOK&&'IntersectionObserver' in window){
    const groups=new Map();
    const tag=(el)=>{ el.classList.add('rv'); const p=el.parentElement; if(!groups.has(p)) groups.set(p,0); const i=groups.get(p); groups.set(p,i+1); el.style.setProperty('--rvd',Math.min(i*85,510)+'ms'); };
    document.querySelectorAll(['.section .section-head','.card','.process li','.detail-list li','.proof-template > div','.quote-card','.founder-photo','.founder-meta','.cta-band','.form-shell','.legal-copy h2','.notice','.flow','.stat'].join(',')).forEach(tag);
    const hero=document.querySelector('.hero');
    if(hero){
      const seq=['.eyebrow','h1','.lead','.actions','.trust-line'];
      seq.forEach((s,i)=>{ const el=hero.querySelector(s); if(el){ el.classList.add('rv'); el.style.setProperty('--rvd',(i*110)+'ms'); } });
      const card=hero.querySelector('.intelligence-card');
      if(card){ card.classList.add('rv'); card.style.setProperty('--rvd','260ms'); }
    }
    const io=new IntersectionObserver(entries=>{
      entries.forEach(en=>{ if(en.isIntersecting){ en.target.classList.add('in'); io.unobserve(en.target); } });
    },{rootMargin:'0px 0px -5% 0px',threshold:0});
    document.querySelectorAll('.rv').forEach(el=>io.observe(el));
    const catchup=setInterval(()=>{
      const left=document.querySelectorAll('.rv:not(.in)');
      if(!left.length){ clearInterval(catchup); return; }
      left.forEach(el=>{ if(el.getBoundingClientRect().top<innerHeight*.98){ el.classList.add('in'); io.unobserve(el); } });
    },900);
    /* failsafe: whatever happens, nothing stays hidden forever
       (protects print, full-page renders, previews and JS hiccups) */
    setTimeout(()=>{ document.querySelectorAll('.rv:not(.in)').forEach(el=>el.classList.add('in')); },4500);
  }

  /* ---------- hero backdrop: ambient particle field + video slot ---------- */
  const backdrop=document.querySelector('.hero-backdrop');
  let canvasStop=null;
  if(backdrop&&motionOK&&!saveData){
    const cv=backdrop.querySelector('canvas');
    if(cv&&cv.getContext){
      const ctx=cv.getContext('2d');
      const DPR=Math.min(window.devicePixelRatio||1,1.5);
      let W=0,H=0,parts=[],running=false,raf=null;
      const mouse={x:-9999,y:-9999};
      function size(){
        const r=backdrop.getBoundingClientRect();
        W=Math.max(1,r.width); H=Math.max(1,r.height);
        cv.width=W*DPR; cv.height=H*DPR;
        ctx.setTransform(DPR,0,0,DPR,0,0);
        const target=Math.min(finePointer?110:44,Math.round(W*H/(finePointer?26000:34000)));
        while(parts.length<target) parts.push(spawn(true));
        parts.length=target;
      }
      function spawn(anywhere){
        return {
          x:Math.random()*W, y:anywhere?Math.random()*H:H+8,
          vx:(Math.random()-.5)*.12, vy:-(.05+Math.random()*.16),
          r:.6+Math.random()*1.5, a:.2+Math.random()*.6,
          tw:Math.random()*Math.PI*2, cream:Math.random()<.18
        };
      }
      function step(){
        if(!running) return;
        ctx.clearRect(0,0,W,H);
        for(let i=0;i<parts.length;i++){
          const p=parts[i];
          p.tw+=.015;
          p.x+=p.vx; p.y+=p.vy;
          if(finePointer){
            const dx=p.x-mouse.x,dy=p.y-mouse.y,d2=dx*dx+dy*dy;
            if(d2<16900&&d2>1){const d=Math.sqrt(d2),f=(130-d)/130*.24;p.x+=dx/d*f;p.y+=dy/d*f;}
          }
          if(p.y<-10||p.x<-10||p.x>W+10) parts[i]=spawn(false);
          const glow=p.a*(0.72+0.28*Math.sin(p.tw));
          ctx.beginPath();
          ctx.fillStyle=p.cream?'rgba(242,239,227,'+(glow*.4).toFixed(3)+')':'rgba(209,254,23,'+glow.toFixed(3)+')';
          ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fill();
        }
        ctx.lineWidth=.5;
        for(let i=0;i<parts.length;i++){
          for(let j=i+1;j<parts.length;j++){
            const a=parts[i],b=parts[j];
            const dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy;
            if(d2<7200){
              ctx.strokeStyle='rgba(209,254,23,'+((1-d2/7200)*.10).toFixed(3)+')';
              ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
            }
          }
        }
        raf=requestAnimationFrame(step);
      }
      function play(){ if(!running){running=true;raf=requestAnimationFrame(step);} }
      function stop(){ running=false; if(raf) cancelAnimationFrame(raf); }
      canvasStop=stop;
      size();
      window.addEventListener('resize',size,{passive:true});
      if(finePointer){
        backdrop.parentElement.addEventListener('pointermove',e=>{
          const r=backdrop.getBoundingClientRect();
          mouse.x=e.clientX-r.left; mouse.y=e.clientY-r.top;
        },{passive:true});
        backdrop.parentElement.addEventListener('pointerleave',()=>{mouse.x=-9999;mouse.y=-9999;},{passive:true});
      }
      const vis=new IntersectionObserver(en=>{ en[0].isIntersecting?play():stop(); },{threshold:0});
      vis.observe(backdrop);
      document.addEventListener('visibilitychange',()=>{ document.hidden?stop():play(); });
    }
  }
  /* hero film: activates when data-src-* attributes are present on the video */
  const heroVideo=backdrop&&backdrop.querySelector('video');
  if(heroVideo&&motionOK&&!saveData){
    const portrait=window.matchMedia('(max-width:680px)').matches;
    const src=portrait?(heroVideo.dataset.srcMobile||heroVideo.dataset.srcDesktop):heroVideo.dataset.srcDesktop;
    if(src){
      heroVideo.src=src; heroVideo.muted=true;
      const attempt=heroVideo.play();
      if(attempt&&attempt.then){
        attempt.then(()=>{ heroVideo.classList.add('on'); if(canvasStop) canvasStop(); const c=backdrop.querySelector('canvas'); if(c) c.remove(); })
               .catch(()=>{ /* Low Power Mode etc. — poster + particles stay */ });
      }
    }
  }

  /* ---------- intelligence card: tilt + live status + feed + clock ---------- */
  const intel=document.querySelector('.intelligence-card');
  if(intel&&motionOK){
    if(finePointer){
      let raf=null;
      intel.addEventListener('pointermove',e=>{
        if(raf) return;
        raf=requestAnimationFrame(()=>{
          const r=intel.getBoundingClientRect();
          const x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
          intel.style.transform='perspective(1100px) rotateX('+(-y*5).toFixed(2)+'deg) rotateY('+(x*6).toFixed(2)+'deg)';
          raf=null;
        });
      });
      intel.addEventListener('pointerleave',()=>{ intel.style.transition='transform .5s cubic-bezier(.22,.61,.21,1)'; intel.style.transform=''; setTimeout(()=>{intel.style.transition='';},520); });
    }
    const rows=intel.querySelectorAll('.system-list li');
    const pools=[
      ['monitored','3 signals','clear','monitored'],
      ['running','cycle done','running','on schedule'],
      ['escalated','1 flagged','watching','escalated'],
      ['prepared','compiling','ready 06:00','prepared']
    ];
    const poolIdx=[0,0,0,0];
    if(rows.length){
      let i=0;
      setInterval(()=>{
        rows.forEach(r=>r.classList.remove('live'));
        const k=i%rows.length;
        rows[k].classList.add('live');
        if(i>0&&i%rows.length===k&&Math.random()<.55&&pools[k]){
          poolIdx[k]=(poolIdx[k]+1)%pools[k].length;
          const span=rows[k].querySelector('span');
          if(span) span.textContent=pools[k][poolIdx[k]];
        }
        i++;
      },2300);
    }
    /* Sydney clock */
    const clock=intel.querySelector('[data-clock]');
    if(clock){
      const fmt=new Intl.DateTimeFormat('en-AU',{timeZone:'Australia/Sydney',hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'});
      const tick=()=>{clock.textContent='SYD '+fmt.format(new Date())+' AEST';};
      tick(); setInterval(tick,1000);
    }
    /* typed feed line */
    const feed=intel.querySelector('[data-feed]');
    if(feed){
      const msgs=[
        'overnight sweep complete — 4 signals, 1 exception',
        'pipeline scan: 3 enquiries qualified, replies drafted',
        'AP run: 12 invoices coded, awaiting sign-off',
        'executive briefing compiled — delivery 06:00',
        'risk watch: no escalations in the last hour'
      ];
      let m=0,ch=0,erasing=false;
      function type(){
        const msg=msgs[m];
        if(!erasing){
          ch++; feed.textContent=msg.slice(0,ch);
          if(ch>=msg.length){ erasing=true; setTimeout(type,3600); return; }
          setTimeout(type,22+Math.random()*30);
        }else{
          ch-=3; if(ch<=0){ ch=0; erasing=false; m=(m+1)%msgs.length; }
          feed.textContent=msg.slice(0,Math.max(0,ch));
          setTimeout(type,erasing?12:420);
        }
      }
      type();
    }
  }else if(intel){
    const feed=intel.querySelector('[data-feed]');
    if(feed) feed.textContent='overnight sweep complete — 4 signals, 1 exception';
  }

  /* ---------- obsidian king: lazy interactive 3D ---------- */
  const kingStage=document.querySelector('[data-king]');
  if(kingStage&&motionOK&&!saveData&&'IntersectionObserver' in window){
    const io3d=new IntersectionObserver(en=>{
      if(!en[0].isIntersecting) return;
      io3d.disconnect();
      const s=document.createElement('script');
      s.type='module';
      s.src='https://cdn.jsdelivr.net/npm/@google/model-viewer@3.5.0/dist/model-viewer.min.js';
      s.onload=()=>{
        const mv=document.createElement('model-viewer');
        mv.setAttribute('src','/assets/hero/aiking-king.glb');
        mv.setAttribute('alt','The AIKING obsidian chess king');
        mv.setAttribute('camera-controls','');
        mv.setAttribute('auto-rotate','');
        mv.setAttribute('auto-rotate-delay','0');
        mv.setAttribute('rotation-per-second','16deg');
        mv.setAttribute('disable-zoom','');
        mv.setAttribute('disable-pan','');
        mv.setAttribute('interaction-prompt','none');
        mv.setAttribute('exposure','0.95');
        mv.setAttribute('shadow-intensity','0.7');
        mv.setAttribute('shadow-softness','0.9');
        mv.setAttribute('camera-orbit','0deg 78deg 105%');
        mv.addEventListener('load',()=>{
          const p=kingStage.querySelector('.king-poster');
          if(p) p.remove();
          kingStage.classList.add('ready');
        });
        kingStage.prepend(mv);
      };
      s.onerror=()=>{};
      document.head.appendChild(s);
    },{rootMargin:'480px 0px'});
    io3d.observe(kingStage);
  }

  /* ---------- Sky live voice line (activates only when an endpoint is configured) ---------- */
  const voiceMeta=document.querySelector('meta[name="sky-voice-endpoint"]');
  if(voiceMeta&&voiceMeta.content&&window.RTCPeerConnection&&navigator.mediaDevices){
    const vs=document.createElement('script');
    vs.src='/assets/sky-voice.js?v=20260720-brief2'; vs.defer=true; vs.onerror=()=>{};
    document.head.appendChild(vs);
  }

  /* ---------- smooth scroll (Lenis, desktop fine-pointer only) ---------- */
  if(motionOK&&finePointer&&!saveData){
    const s=document.createElement('script');
    s.src='https://cdn.jsdelivr.net/npm/lenis@1.1.14/dist/lenis.min.js';
    s.onload=()=>{
      if(!window.Lenis) return;
      const lenis=new window.Lenis({duration:1.05});
      function raf(t){ lenis.raf(t); requestAnimationFrame(raf); }
      requestAnimationFrame(raf);
      document.querySelectorAll('a[href^="#"]').forEach(a=>{
        a.addEventListener('click',e=>{
          const id=a.getAttribute('href');
          if(id.length>1){
            const t=document.querySelector(id);
            if(t){ e.preventDefault(); lenis.scrollTo(t,{offset:-88}); }
          }
        });
      });
    };
    s.onerror=()=>{};
    document.head.appendChild(s);
  }
})();
