
(function(){
  const email='ash@aiking.info';
  const modal=document.querySelector('[data-briefing-modal]');
  const year=document.querySelector('[data-year]');
  if(year) year.textContent=new Date().getFullYear();
  function openModal(){ if(!modal) return; modal.hidden=false; document.body.classList.add('modal-open'); const first=modal.querySelector('input,select,textarea,button'); if(first) setTimeout(()=>first.focus(),30); }
  function closeModal(){ if(!modal) return; modal.hidden=true; document.body.classList.remove('modal-open'); }
  document.querySelectorAll('[data-open-briefing]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();openModal();}));
  document.querySelectorAll('[data-close-briefing]').forEach(el=>el.addEventListener('click',closeModal));
  document.addEventListener('keydown',e=>{if(e.key==='Escape') closeModal();});
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
})();
