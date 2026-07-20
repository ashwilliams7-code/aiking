
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
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  }

  /* ---------- modal + briefing form ---------- */
  const modal=document.querySelector('[data-briefing-modal]');
  const year=document.querySelector('[data-year]');
  if(year) year.textContent=new Date().getFullYear();
  let modalTrigger=null;
  function openModal(trigger){ if(!modal) return; modalTrigger=trigger||null; modal.hidden=false; document.body.classList.add('modal-open'); const first=modal.querySelector('input,select,textarea,button'); if(first) setTimeout(()=>first.focus(),30); }
  function closeModal(){ if(!modal||modal.hidden) return; modal.hidden=true; document.body.classList.remove('modal-open'); if(modalTrigger){modalTrigger.focus();modalTrigger=null;} }
  document.querySelectorAll('[data-open-briefing]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();openModal(el);}));
  document.querySelectorAll('[data-close-briefing]').forEach(el=>el.addEventListener('click',()=>closeModal()));
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){closeModal();closeNav();}
    if(e.key==='Tab'){
      if(modal&&!modal.hidden){trapFocus(modal.querySelector('.modal-panel')||modal,e);}
      else if(menu&&menu.classList.contains('open')){trapFocus(menu,e);}
    }
  });
  if(modal){modal.addEventListener('click',e=>{if(e.target.matches('[data-close-briefing], .modal-backdrop')) closeModal();});}
  function val(fd,name){return (fd.get(name)||'').toString().trim();}
  function setResult(form,href){const result=form.querySelector('.form-result'); if(!result) return; const link=result.querySelector('a'); if(link) link.href=href; result.hidden=false; result.scrollIntoView({behavior:'smooth',block:'nearest'});}
  document.querySelectorAll('.briefing-form').forEach(form=>{
    form.addEventListener('submit',e=>{
      e.preventDefault(); if(!form.reportValidity()) return; const fd=new FormData(form);
      const lines=['Private briefing request','','Name: '+val(fd,'name'),'Role: '+val(fd,'role'),'Company: '+val(fd,'organisation'),'Email: '+val(fd,'email'),'Where AI sits today: '+(val(fd,'maturity')||'Not specified'),'Timeframe: '+val(fd,'timeframe'),'','What AI should change in the business:',val(fd,'outcome'),'','Confidential — submitted through the AIKING private briefing form.'];
      const href='mailto:'+email+'?subject='+encodeURIComponent('AIKING — Private briefing request')+'&body='+encodeURIComponent(lines.join('\n'));
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
