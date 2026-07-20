/* Sky Intelligence — live voice line widget.
   Loaded by site.js ONLY when <meta name="sky-voice-endpoint"> is present.
   Speaks the same SDP-proxy contract as sky-realtime-web-demo:
   POST the WebRTC offer (application/sdp) to the endpoint, receive the
   answer; audio flows over WebRTC, events over the "oai-events" channel.
   The endpoint holds the OpenAI key; nothing secret lives here. */
(function(){
  const meta=document.querySelector('meta[name="sky-voice-endpoint"]');
  const endpoint=meta&&meta.content;
  if(!endpoint||!window.RTCPeerConnection||!navigator.mediaDevices) return;
  if(document.querySelector('.skyv-launch')) return;

  const MAX_SECONDS=180; /* public demo hard cap per call */
  let pc=null,dc=null,mic=null,state='idle',timer=null,tickT=null,remaining=MAX_SECONDS;
  let callSeq=0; /* epoch: bumped by cleanup() so an in-flight startCall() aborts after any await */
  let discT=null; /* ICE 'disconnected' grace timer — the state often self-heals */

  /* ---------- ui ---------- */
  const audio=document.createElement('audio');
  audio.autoplay=true; audio.setAttribute('playsinline','');

  const launch=document.createElement('button');
  launch.type='button'; launch.className='skyv-launch';
  launch.setAttribute('aria-haspopup','dialog');
  launch.innerHTML='<i></i><span>Talk to Sky — live</span>';

  const panel=document.createElement('div');
  panel.className='skyv-panel'; panel.hidden=true;
  panel.setAttribute('role','dialog');
  panel.setAttribute('aria-label','Sky Intelligence live voice line');
  panel.innerHTML=
    '<div class="skyv-head"><span class="skyv-title">Sky Intelligence<b>Live line</b></span>'+
    '<button type="button" class="skyv-close" aria-label="Close voice panel">×</button></div>'+
    '<button type="button" class="skyv-orb" aria-label="Start voice call"><i></i><i></i><i></i><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a3.4 3.4 0 0 0-3.4 3.4v5.2a3.4 3.4 0 1 0 6.8 0V6.4A3.4 3.4 0 0 0 12 3Z"/><path d="M5.6 11.6a6.4 6.4 0 1 0 12.8 0M12 18v3.2"/></svg></button>'+
    '<p class="skyv-status" aria-live="polite" data-skyv-status>Press to open the line</p>'+
    '<div class="skyv-tools" hidden><button type="button" class="skyv-mute" data-skyv-mute>Mute</button><span class="skyv-clock" data-skyv-clock></span><button type="button" class="skyv-end" data-skyv-end>End call</button></div>'+
    '<p class="skyv-note">Live AI demonstration — a real conversation with the Sky system. Please don’t share confidential details. <button type="button" class="skyv-brief" data-open-briefing>Prefer writing? Request a private briefing</button></p>';

  document.body.appendChild(launch);
  document.body.appendChild(panel);

  const orb=panel.querySelector('.skyv-orb');
  const status=panel.querySelector('[data-skyv-status]');
  const tools=panel.querySelector('.skyv-tools');
  const muteBtn=panel.querySelector('[data-skyv-mute]');
  const clock=panel.querySelector('[data-skyv-clock]');

  function setState(s,msg){
    state=s;
    panel.dataset.state=s;
    if(msg!==undefined) status.textContent=msg;
    tools.hidden=!(s==='live'||s==='speaking'||s==='listening'||s==='muted');
    orb.setAttribute('aria-label',s==='idle'||s==='error'||s==='ended'?'Start voice call':'Voice call in progress');
  }
  function fmt(n){ return Math.floor(n/60)+':'+String(n%60).padStart(2,'0'); }

  /* ---------- call lifecycle ---------- */
  function cleanup(){
    callSeq++;
    clearTimeout(timer); clearInterval(tickT); clearTimeout(discT); timer=tickT=discT=null;
    if(dc){ try{dc.close();}catch(_){} dc=null; }
    if(pc){ try{pc.close();}catch(_){} pc=null; }
    if(mic){ mic.getTracks().forEach(t=>t.stop()); mic=null; }
    remaining=MAX_SECONDS; clock.textContent='';
    if(muteBtn){ muteBtn.textContent='Mute'; }
  }
  function endCall(msg){
    cleanup();
    setState('ended',msg||'Line closed. Thanks for talking with Sky.');
  }
  async function startCall(){
    if(state!=='idle'&&state!=='error'&&state!=='ended') return;
    const seq=++callSeq;
    setState('connecting','Opening the line…');
    let stream=null;
    try{
      stream=await navigator.mediaDevices.getUserMedia({audio:true});
    }catch(_){
      if(seq===callSeq) setState('error','Microphone permission needed — check your browser settings.');
      return;
    }
    if(seq!==callSeq){ stream.getTracks().forEach(t=>t.stop()); return; }
    mic=stream;
    try{
      pc=new RTCPeerConnection();
      mic.getTracks().forEach(t=>pc.addTrack(t,mic));
      pc.addEventListener('track',e=>{ if(e.streams&&e.streams[0]) audio.srcObject=e.streams[0]; });
      pc.addEventListener('connectionstatechange',()=>{
        if(!pc) return;
        const cs=pc.connectionState;
        if(cs==='failed'){ endCall('The line dropped. Press the orb to reconnect.'); }
        else if(cs==='disconnected'){ clearTimeout(discT); discT=setTimeout(()=>{ if(pc&&(pc.connectionState==='disconnected'||pc.connectionState==='failed')) endCall('The line dropped. Press the orb to reconnect.'); },4000); }
        else if(cs==='connected'){ clearTimeout(discT); discT=null; }
      });
      dc=pc.createDataChannel('oai-events');
      dc.addEventListener('message',e=>{
        let ev=null; try{ev=JSON.parse(e.data);}catch(_){return;}
        const t=ev&&ev.type||'';
        const muted=mic&&mic.getAudioTracks().length>0&&!mic.getAudioTracks().some(tr=>tr.enabled);
        if(t==='input_audio_buffer.speech_started'){ if(!muted) setState('listening','Listening…'); }
        else if(t.indexOf('response.')===0&&t.indexOf('delta')>-1) setState('speaking','Sky is speaking');
        else if(t==='response.done'||t==='response.audio.done'||t==='output_audio_buffer.stopped'){ if(muted) setState('muted','Muted — Sky can’t hear you'); else setState('live','On the line — just talk'); }
      });
      const offer=await pc.createOffer();
      await pc.setLocalDescription(offer);
      if(seq!==callSeq) return;
      const res=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/sdp'},body:offer.sdp});
      if(seq!==callSeq) return;
      if(!res.ok) throw new Error('session '+res.status);
      const answer=await res.text();
      if(seq!==callSeq) return;
      await pc.setRemoteDescription({type:'answer',sdp:answer});
      if(seq!==callSeq) return;
      setState('live','On the line — just talk');
      remaining=MAX_SECONDS; clock.textContent=fmt(remaining);
      tickT=setInterval(()=>{ remaining--; clock.textContent=fmt(remaining); if(remaining<=0) endCall('Time’s up for this demo call — request a briefing to go deeper.'); },1000);
    }catch(_){
      if(seq!==callSeq) return;
      cleanup();
      setState('error','The live line isn’t available right now — request a briefing instead.');
    }
  }

  /* ---------- wiring ---------- */
  launch.addEventListener('click',()=>{ panel.hidden=false; launch.classList.add('open'); setTimeout(()=>orb.focus(),40); });
  panel.querySelector('.skyv-close').addEventListener('click',()=>{ endCall(); panel.hidden=true; launch.classList.remove('open'); setState('idle','Press to open the line'); launch.focus(); });
  orb.addEventListener('click',()=>{ if(state==='idle'||state==='error'||state==='ended') startCall(); });
  panel.querySelector('[data-skyv-end]').addEventListener('click',()=>endCall());
  muteBtn.addEventListener('click',()=>{
    if(!mic) return;
    const on=mic.getAudioTracks().some(t=>t.enabled);
    mic.getAudioTracks().forEach(t=>{t.enabled=!on;});
    muteBtn.textContent=on?'Unmute':'Mute';
    if(on) setState('muted','Muted — Sky can’t hear you'); else setState('live','On the line — just talk');
  });
  /* the "prefer writing" button reuses the briefing modal via its global hook */
  panel.querySelector('.skyv-brief').addEventListener('click',function(){
    const opener=document.querySelector('[data-open-briefing]');
    endCall(); panel.hidden=true; launch.classList.remove('open'); setState('idle','Press to open the line');
    if(opener&&opener!==this) opener.click();
  });
  window.addEventListener('pagehide',cleanup);
  /* bfcache restore: the pagehide cleanup killed the call, so never wake as a zombie 'live' UI */
  window.addEventListener('pageshow',e=>{ if(e.persisted&&state!=='idle'){ cleanup(); setState('idle','Press to open the line'); } });
  document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&!panel.hidden){ endCall(); panel.hidden=true; launch.classList.remove('open'); setState('idle','Press to open the line'); launch.focus(); } });
  setState('idle','Press to open the line');
})();
