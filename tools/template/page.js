
(function(){
  var SONG=window.__SONG||{};
  var SPELL=SONG.spell;
  var KEY=(SONG.slug||'song');
  var OFF={alto:9,concert:0,tenor:2};
  function nm(pc,mode){return SPELL[mode][(pc+OFF[mode])%12];}
  function acc(s){return s.replace(/([♯♭])/g,'<i class="ac">$1</i>');}
  function chordHTML(el,mode){
    if(el.hasAttribute('data-nc'))return '<span class="r">N.C.</span>';
    var h='',q=el.getAttribute('data-q')||'',b=el.getAttribute('data-b');
    if(!el.hasAttribute('data-so')){
      h+='<span class="r">'+acc(nm(+el.getAttribute('data-r'),mode))+'</span>';
      if(q)h+='<span class="q">'+acc(q)+'</span>';
    }
    if(b!==null)h+='<span class="sl">/'+acc(nm(+b,mode))+'</span>';
    return h;
  }
  window.__chordHTML=chordHTML;
  function setMode(mode){
    if(!SPELL[mode])return;
    var i,els=document.querySelectorAll('.ch');
    for(i=0;i<els.length;i++)els[i].innerHTML=chordHTML(els[i],mode);
    els=document.querySelectorAll('[data-mode]');
    for(i=0;i<els.length;i++)els[i].hidden=els[i].getAttribute('data-mode')!==mode;
    try{localStorage.setItem(KEY+'-mode',mode);}catch(e){}
    if(window.__renderNow)window.__renderNow();
  }
  var radios=document.querySelectorAll('input[name="keymode"]');
  Array.prototype.forEach.call(radios,function(r){r.addEventListener('change',function(){if(r.checked)setMode(r.value);});});
  var saved=null;try{saved=localStorage.getItem(KEY+'-mode');}catch(e){}
  var checked=document.querySelector('input[name="keymode"]:checked');
  if(saved&&SPELL[saved]&&saved!=='alto'){var rr=document.getElementById('k-'+saved);if(rr){rr.checked=true;setMode(saved);}}
  else if(checked&&checked.value!=='alto'){setMode(checked.value);}



  function fullChordHTML(el,mode){
    if(el.hasAttribute('data-nc'))return '<span class="r">N.C.</span>';
    var h='',q=el.getAttribute('data-q')||'',b=el.getAttribute('data-b');
    h+='<span class="r">'+acc(nm(+el.getAttribute('data-r'),mode))+'</span>';
    if(q)h+='<span class="q">'+acc(q)+'</span>';
    if(b!==null)h+='<span class="sl">/'+acc(nm(+b,mode))+'</span>';
    return h;
  }
  function curMode(){var c=document.querySelector('input[name="keymode"]:checked');return c?c.value:'alto';}
  function fmt(t){t=Math.max(0,Math.floor(t||0));return Math.floor(t/60)+':'+('0'+(t%60)).slice(-2);}
  function lastIdx(arr,t){var lo=0,hi=arr.length-1,r=-1;while(lo<=hi){var m=(lo+hi)>>1;if(arr[m]<=t+1e-3){r=m;lo=m+1;}else hi=m-1;}return r;}

  var audio=document.getElementById('aud');
  var bars=Array.prototype.slice.call(document.querySelectorAll('.chart .bar'));
  var BT=bars.map(function(b){return parseFloat(b.getAttribute('data-t'));});
  var BB=bars.map(function(b){var v=b.getAttribute('data-beats');return v?v.split(',').map(parseFloat):null;});
  var chs=Array.prototype.slice.call(document.querySelectorAll('.chart .ch'));
  var CT=chs.map(function(c){return parseFloat(c.getAttribute('data-t'));});
  var secEls=Array.prototype.slice.call(document.querySelectorAll('.chart .sec'));
  var ST=secEls.map(function(s){return parseFloat(s.querySelector('.bar').getAttribute('data-t'));});
  var secName=secEls.map(function(s){return s.querySelector('.sec-h h2').textContent;});
  var nowCh=document.getElementById('nowCh'),nextCh=document.getElementById('nextCh'),posLab=document.getElementById('posLab');
  var dots=document.getElementById('dots'),dotEls=dots.querySelectorAll('i');
  var playBtn=document.getElementById('play'),icon=document.getElementById('icon');
  var seek=document.getElementById('seek'),tCur=document.getElementById('tCur'),tDur=document.getElementById('tDur');
  var loopBtn=document.getElementById('loop'),statusEl=document.getElementById('status');
  var player=document.getElementById('player'),errEl=document.getElementById('err');
  var reduce=false;try{reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;}catch(e){}
  var curC=-2,curB=-2,curBeat=-2,dragging=false,raf=null,lock=null,userScrollUntil=0;
  var loopOn=false,loopA=0,loopB=0,wantT=null,blobbing=false;
  var wantAt=0;
  function seekTo(t){wantT=t;wantAt=performance.now();audio.currentTime=t;}
  function checkSeek(t){
    if(wantT===null||blobbing)return;
    var el=(performance.now()-wantAt)/1000;
    if(el<0.8)return;
    var exp=wantT+(audio.paused?0:Math.max(0,el-0.3)*audio.playbackRate);
    if(Math.abs(t-exp)>2){ensureSeekable(true);}else wantT=null;
  }
  function ensureSeekable(force){
    var d=audio.duration;
    if(!isFinite(d)||blobbing||location.protocol==='file:'||String(audio.currentSrc||audio.src).indexOf('blob:')===0)return;
    if(!force){try{var s=audio.seekable;if(s.length&&s.end(s.length-1)>=d-1)return;}catch(e){}}
    blobbing=true;statusEl.textContent='正在载入伴奏…';
    fetch(audio.currentSrc||audio.src,{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('http');return r.blob();}).then(function(b){
      var t=wantT!==null?wantT:audio.currentTime,was=!audio.paused;
      var once=function(){audio.removeEventListener('loadedmetadata',once);wantT=null;audio.currentTime=t;update(t,true);if(was)play();statusEl.textContent='';};
      audio.addEventListener('loadedmetadata',once);
      audio.src=URL.createObjectURL(b);audio.load();
    }).catch(function(){blobbing=false;statusEl.textContent='';});
  }

  function renderNow(){
    var mode=curMode(),i=Math.max(0,curC);
    var el=chs[i];
    nowCh.innerHTML=fullChordHTML(el,mode);
    nowCh.className='now-ch'+(el.classList.contains('out')?' out':'');
    var label=nowCh.textContent,j=i+1;
    while(j<chs.length&&fullChordHTML(chs[j],mode)===fullChordHTML(el,mode))j++;
    nextCh.innerHTML=j<chs.length?fullChordHTML(chs[j],mode):'—';
  }
  window.__renderNow=renderNow;

  function maybeScroll(bar){
    if(Date.now()<userScrollUntil)return;
    var r=bar.getBoundingClientRect(),vh=window.innerHeight||document.documentElement.clientHeight;
    var ph=player.getBoundingClientRect().height;
    if(r.top<60||r.bottom>vh-ph-16){
      window.scrollBy({top:r.top-Math.max(70,(vh-ph)*0.32),behavior:reduce?'auto':'smooth'});
    }
  }

  function update(t,forceScroll){
    var c=Math.max(0,lastIdx(CT,t));
    if(c!==curC){
      if(curC>=0)chs[curC].classList.remove('now');
      curC=c;chs[c].classList.add('now');renderNow();
    }
    var b=Math.max(0,lastIdx(BT,t));
    if(b!==curB){
      if(curB>=0)bars[curB].classList.remove('on');
      curB=b;var bar=bars[b];bar.classList.add('on');
      posLab.textContent=bar.getAttribute('data-sec')+' · '+bar.getAttribute('data-lab');
      if(!audio.paused||forceScroll)maybeScroll(bar);
    }
    var beats=BB[b],beat=-1;
    if(beats){beat=Math.max(0,lastIdx(beats,t));}
    if(beat!==curBeat){
      curBeat=beat;dots.hidden=beat<0;
      for(var k=0;k<dotEls.length;k++)dotEls[k].classList.toggle('on',k===beat);
    }
    tCur.textContent=fmt(t);
    if(!dragging)seek.value=t;
  }

  function frame(){
    var t=audio.currentTime;
    if(loopOn&&t>=loopB-0.03){seekTo(loopA);t=loopA;}
    checkSeek(t);
    update(t);
    raf=audio.paused?null:requestAnimationFrame(frame);
  }
  function setIcon(playing){
    icon.setAttribute('d',playing?'M6.5 4.5h4v15h-4zM13.5 4.5h4v15h-4z':'M7 4.5v15l13-7.5z');
    playBtn.setAttribute('aria-label',playing?'暂停':'播放');
  }
  function wake(){try{if(navigator.wakeLock&&!lock){navigator.wakeLock.request('screen').then(function(l){lock=l;l.addEventListener('release',function(){lock=null;});}).catch(function(){});}}catch(e){}}
  function unwake(){if(lock){try{lock.release();}catch(e){}lock=null;}}
  function play(){var p=audio.play();if(p&&p.catch)p.catch(function(){statusEl.textContent='点一下播放键开始';});}

  audio.addEventListener('play',function(){setIcon(true);wake();if(!raf)raf=requestAnimationFrame(frame);});
  audio.addEventListener('pause',function(){setIcon(false);unwake();});
  audio.addEventListener('ended',function(){setIcon(false);unwake();});
  audio.addEventListener('waiting',function(){statusEl.textContent='加载中…';});
  audio.addEventListener('playing',function(){statusEl.textContent='';});
  audio.addEventListener('seeked',function(){if(audio.paused){update(audio.currentTime);setTimeout(function(){checkSeek(audio.currentTime);},900);}});
  audio.addEventListener('loadedmetadata',ensureSeekable);
  audio.addEventListener('loadedmetadata',function(){if(isFinite(audio.duration)){seek.max=audio.duration;tDur.textContent=fmt(audio.duration);}});
  audio.addEventListener('error',function(){errEl.hidden=false;statusEl.textContent='';});
  document.getElementById('pick').addEventListener('change',function(e){
    var f=e.target.files&&e.target.files[0];if(!f)return;
    try{audio.src=URL.createObjectURL(f);errEl.hidden=true;audio.load();}catch(err){}
  });

  playBtn.addEventListener('click',function(){if(audio.paused)play();else audio.pause();});
  seek.addEventListener('input',function(){dragging=true;var t=parseFloat(seek.value);tCur.textContent=fmt(t);update(t,true);});
  seek.addEventListener('change',function(){dragging=false;seekTo(parseFloat(seek.value));});

  function setLoopFor(t){
    var si=Math.max(0,lastIdx(ST,t));
    loopA=ST[si];loopB=si+1<ST.length?ST[si+1]:(isFinite(audio.duration)?audio.duration:443);
    loopBtn.textContent='循环：'+secName[si]+' '+fmt(loopA)+'–'+fmt(loopB);
  }
  loopBtn.addEventListener('click',function(){
    loopOn=!loopOn;loopBtn.setAttribute('aria-pressed',loopOn?'true':'false');
    if(loopOn)setLoopFor(audio.currentTime);else loopBtn.textContent='循环本段';
  });

  var rateBtns=document.querySelectorAll('.spd button');
  function setRate(r){
    audio.playbackRate=r;
    try{audio.preservesPitch=true;audio.webkitPreservesPitch=true;}catch(e){}
    Array.prototype.forEach.call(rateBtns,function(b){b.setAttribute('aria-pressed',parseFloat(b.getAttribute('data-rate'))===r?'true':'false');});
    try{localStorage.setItem(KEY+'-rate',String(r));}catch(e){}
  }
  Array.prototype.forEach.call(rateBtns,function(b){b.addEventListener('click',function(){setRate(parseFloat(b.getAttribute('data-rate')));});});
  try{var sr=parseFloat(localStorage.getItem(KEY+'-rate'));if(sr===0.75||sr===0.9)setRate(sr);}catch(e){}
  audio.addEventListener('loadedmetadata',function(){var p=document.querySelector('.spd button[aria-pressed="true"]');if(p)audio.playbackRate=parseFloat(p.getAttribute('data-rate'));});

  bars.forEach(function(b,i){b.addEventListener('click',function(){
    var t=Math.max(0,BT[i]-0.03);
    if(loopOn&&(t<loopA||t>=loopB))setLoopFor(BT[i]);
    seekTo(t);update(BT[i]);
    if(audio.paused)play();
  });});

  Array.prototype.forEach.call(document.querySelectorAll('.chip'),function(a){
    a.addEventListener('click',function(e){
      var t=document.getElementById(a.getAttribute('href').slice(1));
      if(t){e.preventDefault();userScrollUntil=Date.now()+4000;t.scrollIntoView({block:'start',behavior:reduce?'auto':'smooth'});}
    });
  });
  ['touchmove','wheel'].forEach(function(ev){window.addEventListener(ev,function(){userScrollUntil=Date.now()+4000;},{passive:true});});
  document.addEventListener('keydown',function(e){
    var tag=(e.target&&e.target.tagName)||'';
    if(e.key===' '&&tag!=='INPUT'&&tag!=='BUTTON'&&tag!=='LABEL'){e.preventDefault();if(audio.paused)play();else audio.pause();}
  });
  document.addEventListener('visibilitychange',function(){if(!document.hidden&&!audio.paused)wake();});
  update(0);
})();
