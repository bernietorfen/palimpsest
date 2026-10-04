async (page) => {
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const response=await page.goto('https://site-inky-eight-42.vercel.app/');
  check(response.status()===200,'Production exhibition is not publicly readable');
  await page.waitForFunction(()=>document.querySelectorAll('#download-list a').length===7);
  const inventory=await page.locator('#download-list a').evaluateAll(links=>links.map(a=>({text:a.textContent,href:a.href})));
  await page.getByRole('button',{name:'Enter the film'}).click();
  await page.waitForFunction(()=>document.querySelector('#main-film').currentTime>.3);
  const film=await page.locator('#main-film').evaluate(async video=>{
    video.pause();video.textTracks[0].mode='hidden';
    await new Promise((resolve,reject)=>{let count=0;const timer=setInterval(()=>{if(video.textTracks[0].cues?.length){clearInterval(timer);resolve();}else if(++count>100){clearInterval(timer);reject(new Error('Captions did not load'));}},50);});
    return {duration:video.duration,width:video.videoWidth,height:video.videoHeight,captions:video.textTracks[0].cues.length,seekable:video.seekable.length};
  });
  check(film.duration===432&&film.width===1920&&film.height===1080&&film.captions===12,'Film or captions do not match the first edition');
  await page.getByRole('button',{name:'Explore the inscription sculpture in 3D',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#sculpture-canvas').dataset.state==='ready');
  const sculpture=await page.locator('#sculpture-canvas').evaluate(e=>({...e.dataset}));
  check(sculpture.triangles==='259772','The deployed sculpture is not the expected state');
  await page.keyboard.press('Escape');
  const range=await page.evaluate(async()=>{const r=await fetch('/assets/generated/probe-ABCDE.m4a',{headers:{Range:'bytes=0-1023'}});return{status:r.status,range:r.headers.get('content-range'),bytes:(await r.arrayBuffer()).byteLength};});
  check(range.status===206&&range.bytes===1024,'Public media range requests are not working');
  check(errors.length===0,'Production browser error: '+errors.join('; '));
  return {url:page.url(),status:response.status(),inventory,film,sculpture,range,errors,scope:'Anonymous production browser check; playback state, captions, actual glTF and byte ranges.'};
}
