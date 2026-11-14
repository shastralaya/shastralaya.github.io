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
  for(const form of document.querySelectorAll('[data-page-jump-form]'))form.addEventListener('submit',event=>{
    event.preventDefault();
    const number=Number(form.elements.namedItem('page')?.value);
    const total=Number(form.dataset.pageTotal);
    const base=form.dataset.pageBase||'';
    if(!Number.isSafeInteger(number)||number<1||number>total||!/^\/(?:texts|works)\/[a-z0-9-]+\/$/.test(base)){
      form.elements.namedItem('page')?.setCustomValidity('Enter a valid reading page number');
      form.reportValidity();return;
    }
    location.assign(`${base}${number}/`);
  });
  for(const input of document.querySelectorAll('[data-page-jump-form] input'))input.addEventListener('input',()=>input.setCustomValidity(''));
  document.querySelector('[data-chapter-jump]')?.addEventListener('change',e=>{
    const target=e.currentTarget.value;
    if(/^\/gita\/(?:[1-9]|1[0-8])\/$/.test(target))location.assign(target);
  });
  // Shared reading preferences: explicit settings survive page navigation.
  const readingPage=document.querySelector('[data-reading-page]');
  if(readingPage){
    const book=readingPage.dataset.bookId;
    const part=Number(readingPage.dataset.part);
    const total=Number(readingPage.dataset.partTotal);
    const fontHost=readingPage.querySelector('[data-reader-text]')||readingPage;
    let size=Number(storage.get('shastralaya-font'))||0;
    size=Math.max(-3,Math.min(6,size));
    const applyFont=()=>fontHost.style.setProperty('--reading-size',`${(1.27+size*.105).toFixed(3)}rem`);
    applyFont();
    for(const b of readingPage.querySelectorAll('[data-font-step]'))b.addEventListener('click',()=>{
      size=Math.max(-3,Math.min(6,size+Number(b.dataset.fontStep||0)));
      applyFont();storage.set('shastralaya-font',String(size));
    });
    const linesButton=readingPage.querySelector('[data-lines-toggle]');
    const savedLines=storage.get(`shastralaya-lines:${book}`);
    let originalLines=savedLines==='true'||(savedLines===null&&readingPage.dataset.defaultLines==='true');
    const setLines=()=>{
      readingPage.classList.toggle('reader-original-lines',originalLines);
      linesButton?.setAttribute('aria-pressed',String(originalLines));
      if(linesButton)linesButton.textContent=originalLines?'Flowing text':'Original lines';
    };
    setLines();
    linesButton?.addEventListener('click',()=>{
      originalLines=!originalLines;
      storage.set(`shastralaya-lines:${book}`,String(originalLines));setLines();
    });
    const widthButton=readingPage.querySelector('[data-width-toggle]');
    let wide=storage.get('shastralaya-reader-wide')==='true';
    const setWide=()=>{
      readingPage.classList.toggle('reader-wide',wide);
      widthButton?.setAttribute('aria-pressed',String(wide));
      if(widthButton)widthButton.textContent=wide?'Narrower page':'Wider page';
    };
    setWide();
    widthButton?.addEventListener('click',()=>{
      wide=!wide;storage.set('shastralaya-reader-wide',String(wide));setWide();
    });
    const focusButton=readingPage.querySelector('[data-focus-toggle]');
    const setFocus=on=>{
      document.body.classList.toggle('focus-reading',on);
      focusButton?.setAttribute('aria-pressed',String(on));
      if(focusButton)focusButton.textContent=on?'Exit focus':'Focus';
    };
    focusButton?.addEventListener('click',()=>setFocus(!document.body.classList.contains('focus-reading')));
    document.addEventListener('keydown',e=>{
      if(e.key==='Escape'&&document.body.classList.contains('focus-reading'))setFocus(false);
    });
    // The bookmark records the last opened page, never a guessed chapter.
    if(book&&Number.isInteger(part)&&part>=1&&part<=total){
      storage.set(`shastralaya-last:${book}`,String(part));
      const bar=document.createElement('div');bar.className='reading-progress';bar.setAttribute('aria-hidden','true');document.body.append(bar);
      let ticking=false;
      const update=()=>{
        const max=Math.max(1,document.documentElement.scrollHeight-innerHeight);
        bar.style.width=`${Math.max(0,Math.min(100,scrollY/max*100)).toFixed(1)}%`;
        ticking=false;
      };
      const schedule=()=>{if(!ticking){ticking=true;requestAnimationFrame(update)}};
      addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);schedule();
    }
  }
  for(const node of document.querySelectorAll('[data-continue-book]')){
    const book=node.dataset.continueBook;
    const number=Number(storage.get(`shastralaya-last:${book}`));
    if(!Number.isInteger(number)||number<1)continue;
    const prefix=book==='gita'?'/gita/':location.pathname;
    const link=document.createElement('a');link.href=`${prefix}${number}/`;
    link.textContent=`Continue from ${book==='gita'?'chapter':'reading page'} ${number} →`;
    node.append('Your last place: ',link);node.hidden=false;
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
    const status=document.querySelector('[data-verse-status]');
    const target=document.querySelector('[data-verse-results]');
    let records=[];
    let loaded=false;
    let pending=0;
    const render=()=>{
      if(!loaded)return;
      const q=normalized(verseSearch.value.trim());
      target.replaceChildren();
      if(q.length<2){status.textContent='Enter at least two characters or a Gītā verse reference.';return;}
      let found=0;
      for(const row of records){
        const haystack=normalized(row.text+' '+row.book+' '+row.ref);
        if(!(row.kind==='gita'&&row.ref===q)&&!haystack.includes(q))continue;
        found++;
        if(found>60)continue;
        const link=document.createElement('a');
        link.className='search-result';
        link.href=row.url;
        const ref=document.createElement('strong');
        ref.textContent=row.book+' · '+row.ref;
        const excerpt=document.createElement('p');
        excerpt.className=row.kind==='gretil'?'iast-line':'';
        excerpt.lang=row.kind==='gretil'?'sa-Latn':'sa';
        excerpt.textContent=row.text;
        link.append(ref,excerpt);target.append(link);
      }
      status.textContent=`${found} ${found===1?'passage':'passages'} found${found>60?' · showing first 60':''}`;
    };
    status.textContent='Loading published source index…';
    fetch('/search/library.json',{cache:'force-cache'}).then(r=>{
      if(!r.ok)throw Error('Corpus index unavailable');
      return r.json();
    }).then(rows=>{
      if(!Array.isArray(rows)||rows.length<701)throw Error('Corpus index incomplete');
      records=rows;
      loaded=true;
      let timer;
      verseSearch.addEventListener('input',()=>{
        clearTimeout(timer);timer=setTimeout(render,110);
      });
      status.textContent='Search the complete published Sanskrit reading collection.';
      render();
    }).catch(()=>status.textContent='The source index could not be loaded. Try again later.');
  }

  // The CSS line box is not the painted bounds of a Devanagari ligature.
  // Center the actual ink using the resolved browser font, on every device.
  const ornamentGlyph=document.querySelector('.hero-art .art-script');
  if(ornamentGlyph){
    const centerOrnament=()=>{
      const style=getComputedStyle(ornamentGlyph);
      const canvas=document.createElement('canvas');
      const ctx=canvas.getContext('2d');
      if(!ctx)return;
      ctx.font=`${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
      const m=ctx.measureText(ornamentGlyph.textContent.trim());
      const values=[m.width,m.actualBoundingBoxLeft,m.actualBoundingBoxRight,
        m.actualBoundingBoxAscent,m.actualBoundingBoxDescent,
        m.fontBoundingBoxAscent,m.fontBoundingBoxDescent];
      if(!values.every(Number.isFinite))return; // Safe CSS fallback on older browsers.
      // Horizontal advance center -> painted center; line-box center -> ink center.
      const dx=(m.width+m.actualBoundingBoxLeft-m.actualBoundingBoxRight)/2;
      const dy=(m.actualBoundingBoxAscent-m.actualBoundingBoxDescent
        -m.fontBoundingBoxAscent+m.fontBoundingBoxDescent)/2;
      ornamentGlyph.style.setProperty('--art-ink-x',`${dx.toFixed(2)}px`);
      ornamentGlyph.style.setProperty('--art-ink-y',`${dy.toFixed(2)}px`);
    };
    centerOrnament();
    document.fonts?.ready?.then(centerOrnament).catch(()=>{});
    window.addEventListener('resize',centerOrnament,{passive:true});
  }
})();
