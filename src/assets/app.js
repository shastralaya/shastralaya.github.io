(()=>{
  'use strict';
  const root=document.documentElement;
  const storage={get(key){try{return localStorage.getItem(key)}catch{return null}},set(key,val){try{localStorage.setItem(key,val)}catch{}}};
  // Respect a saved choice, otherwise follow the operating system.
  // The corresponding inline script in <head> sets the theme before first paint.
  const systemTheme=window.matchMedia?window.matchMedia('(prefers-color-scheme: dark)'):null;
  const toggle=document.querySelector('[data-theme-toggle]');
  const applyTheme=(theme,persist=false)=>{
    const dark=theme==='dark';
    root.dataset.theme=dark?'dark':'light';
    if(persist)storage.set('shastralaya-theme',root.dataset.theme);
    const color=document.querySelector('meta[name="theme-color"]');
    if(color)color.setAttribute('content',dark?'#151e1b':'#f8f6ef');
    if(toggle){
      const label=dark?'Switch to light mode':'Switch to dark mode';
      toggle.setAttribute('aria-label',label);
      toggle.setAttribute('title',label);
      toggle.setAttribute('aria-pressed',String(dark));
      const icon=toggle.querySelector('[aria-hidden="true"]');
      if(icon)icon.textContent=dark?'☀':'☾';
    }
  };
  const storedTheme=storage.get('shastralaya-theme');
  applyTheme(storedTheme==='dark'||storedTheme==='light'?storedTheme:
    (systemTheme?.matches?'dark':'light'));
  toggle?.addEventListener('click',()=>applyTheme(root.dataset.theme==='dark'?'light':'dark',true));
  systemTheme?.addEventListener?.('change',event=>{
    const choice=storage.get('shastralaya-theme');
    if(choice!=='light'&&choice!=='dark')applyTheme(event.matches?'dark':'light');
  });
  const normalized=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/ṣ/g,'s').replace(/ṭ/g,'t').replace(/ḍ/g,'d').replace(/ṇ/g,'n').replace(/ṃ/g,'m').replace(/ḥ/g,'h');
  const search=document.querySelector('[data-library-search]');
  if(search){
    const cards=[...document.querySelectorAll('.book-card')];
    const tabs=[...document.querySelectorAll('[data-filter]')];
    const count=document.querySelector('[data-result-count]');
    const empty=document.querySelector('[data-empty-message]');
    let filter='all';
    const update=()=>{
      const needle=normalized(search.value.trim());let visible=0;
      for(const card of cards){const hit=(filter==='all'||card.dataset.kind===filter)&&normalized(card.dataset.search||card.textContent).includes(needle);card.hidden=!hit;if(hit)visible++;}
      count.textContent=`Showing ${visible} ${visible===1?'edition':'editions'}`;
      if(empty)empty.hidden=visible!==0;
    };
    search.addEventListener('input',update);
    for(const tab of tabs)tab.addEventListener('click',()=>{
      filter=tab.dataset.filter;
      for(const other of tabs){other.classList.toggle('selected',other===tab);other.setAttribute('aria-pressed',String(other===tab));}
      update();
    });
  }
  document.querySelector('[data-chapter-jump]')?.addEventListener('change',e=>{
    const target=e.currentTarget.value;
    if(/^\/gita\/(?:[1-9]|1[0-8])\/$/.test(target))location.assign(target);
  });
  const readerText=document.querySelector('.reader-main, .english-reader');
  if(readerText){
    const initial=Number(storage.get('shastralaya-font'))||0;
    let size=Math.max(-3,Math.min(6,initial));
    const apply=()=>{readerText.style.setProperty('--reading-size',`${(1.27+size*.105).toFixed(3)}rem`)};
    apply();
    for(const b of document.querySelectorAll('[data-font-step]'))b.addEventListener('click',()=>{
      size=Math.max(-3,Math.min(6,size+Number(b.dataset.fontStep||0)));apply();storage.set('shastralaya-font',String(size));
    });
  }
  for(const b of document.querySelectorAll('[data-copy-verse]'))b.addEventListener('click',async()=>{
    const article=b.closest('.verse');
    const verse=article?.querySelector('.verse-devanagari')?.textContent;
    if(!verse)return;
    const text=`Bhagavad Gītā ${b.dataset.ref}\n${verse}\n${location.href.split('#')[0]}#${article.id}`;
    try{await navigator.clipboard.writeText(text);const old=b.textContent;b.textContent='Copied ✓';setTimeout(()=>b.textContent=old,1700)}
    catch{b.textContent='Select and copy the text';}
  });
  const verseSearch=document.querySelector('[data-verse-search]');
  if(verseSearch){
    const status=document.querySelector('[data-verse-status]'), target=document.querySelector('[data-verse-results]');
    let verses=[],ready=false;
    const render=()=>{
      if(!ready)return;
      const q=normalized(verseSearch.value.trim());target.replaceChildren();
      if(q.length<2){status.textContent='Enter at least two characters or a verse reference.';return;}
      const matches=verses.filter(v=>`${v.chapter}.${v.verse}`===q||normalized(v.text).includes(q));
      status.textContent=`${matches.length} ${matches.length===1?'verse':'verses'} found${matches.length>75?' · Showing first 75':''}`;
      for(const v of matches.slice(0,75)){
        const a=document.createElement('a');a.className='search-result';a.href=`/gita/${v.chapter}/#v${v.verse}`;
        const ref=document.createElement('strong');ref.textContent=`Bhagavad Gītā ${v.chapter}.${v.verse}`;
        const body=document.createElement('p');body.lang='sa';body.textContent=v.text;
        a.append(ref,body);target.append(a);
      }
    };
    status.textContent='Loading Sanskrit verse index…';
    fetch('/search/verses.json',{cache:'force-cache'}).then(r=>{if(!r.ok)throw Error('Verse index unavailable');return r.json()}).then(rows=>{
      if(!Array.isArray(rows)||rows.length!==701)throw Error('Unexpected verse index');
      verses=rows;ready=true;verseSearch.addEventListener('input',render);status.textContent='Search 701 verses from the documented Gītā transcription.';
      if(verseSearch.value)render();
    }).catch(()=>status.textContent='The verse index could not be loaded. Try again later.');
  }
})();
