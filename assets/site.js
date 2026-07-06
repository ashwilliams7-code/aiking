
(function(){
  const email='ash@aiking.info';
  const doc=document.documentElement;
  doc.classList.add('js');
  const motionOK=window.matchMedia('(prefers-reduced-motion: no-preference)').matches;

  /* ---------- modal + briefing form (unchanged behaviour) ---------- */
  const modal=document.querySelector('[data-briefing-modal]');
  const year=document.querySelector('[data-year]');
  if(year) year.textContent=new Date().getFullYear();
  function openModal(){ if(!modal) return; modal.hidden=false; document.body.classList.add('modal-open'); const first=modal.querySelector('input,select,textarea,button'); if(first) setTimeout(()=>first.focus(),30); }
  function closeModal(){ if(!modal) return; modal.hidden=true; document.body.classList.remove('modal-open'); }
  document.querySelectorAll('[data-open-briefing]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();openModal();}));
  document.querySelectorAll('[data-close-briefing]').forEach(el=>el.addEventListener('click',closeModal));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeModal();closeNav();}});
  if(modal){modal.addEventListener('click',e=>{if(e.target.matches('[data-close-briefing], .modal-backdrop')) closeModal();});}
  function val(fd,name){return (fd.get(name)||'').toString().trim();}
  function setResult(form,href){const result=form.querySelector('.form-result'); if(!result) return; const link=result.querySelector('a'); if(link) link.href=href; result.hidden=false; result.scrollIntoView({behavior:'smooth',block:'nearest'});}
  document.querySelectorAll('.briefing-form').forEach(form=>{
    form.addEventListener('submit',e=>{
      e.preventDefault(); if(!form.reportValidity()) return; const fd=new FormData(form);
      const lines=['Private Executive Briefing request','','Name: '+val(fd,'name'),'Role: '+val(fd,'role'),'Organisation: '+val(fd,'organisation'),'Email: '+val(fd,'email'),'Current AI maturity: '+(val(fd,'maturity')||'Not specified'),'Preferred timeframe: '+val(fd,'timeframe'),'','Strategic or operational outcome being explored:',val(fd,'outcome'),'','Confidentiality note: submitted through the AIKING private briefing form.'];
      const href='mailto:'+email+'?subject='+encodeURIComponent('AIKING Private Executive Briefing request')+'&body='+encodeURIComponent(lines.join('\n'));
      form.dataset.generatedMailto=href; setResult(form,href);
    });
  });

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
  function closeNav(){ if(menu&&menu.classList.contains('open')){ menu.classList.remove('open'); menu.setAttribute('aria-hidden','true'); document.body.classList.remove('nav-lock'); if(burger) burger.setAttribute('aria-expanded','false'); } }
  if(header&&navLinks&&navActions){
    menu=document.createElement('div');
    menu.className='mobile-menu'; menu.setAttribute('aria-hidden','true');
    const mmNav=document.createElement('nav');
    mmNav.className='mm-links'; mmNav.setAttribute('aria-label','Mobile navigation');
    navLinks.querySelectorAll('a').forEach((a,i)=>{ const c=a.cloneNode(true); c.style.setProperty('--nd',(90+i*55)+'ms'); c.addEventListener('click',closeNav); mmNav.appendChild(c); });
    const mmClose=document.createElement('button');
    mmClose.className='mm-close'; mmClose.type='button'; mmClose.setAttribute('aria-label','Close menu');
    mmClose.innerHTML='<i></i><i></i>';
    mmClose.addEventListener('click',closeNav);
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
    });
  }

  /* ---------- scroll reveals (motion-safe only) ---------- */
  if(motionOK&&'IntersectionObserver' in window){
    const groups=new Map();
    const tag=(el)=>{ el.classList.add('rv'); const p=el.parentElement; if(!groups.has(p)) groups.set(p,0); const i=groups.get(p); groups.set(p,i+1); el.style.setProperty('--rvd',Math.min(i*85,510)+'ms'); };
    document.querySelectorAll(['.section .section-head','.card','.process li','.detail-list li','.proof-template > div','.quote-card','.founder-photo','.founder-meta','.cta-band','.form-shell','.legal-copy h2','.notice'].join(',')).forEach(tag);
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
  }

  /* ---------- intelligence card: pointer tilt + live status ticks ---------- */
  const intel=document.querySelector('.intelligence-card');
  if(intel&&motionOK){
    if(window.matchMedia('(pointer:fine)').matches){
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
    if(rows.length){
      let i=0;
      setInterval(()=>{ rows.forEach(r=>r.classList.remove('live')); rows[i%rows.length].classList.add('live'); i++; },2300);
    }
  }
})();
