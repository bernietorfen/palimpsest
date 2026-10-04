async(page)=>{
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.locator('#reply-comparison').waitFor({state:'visible'});
  const [drawing]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Save the paired drawing ↓',exact:true}).click()]);
  await drawing.saveAs('output/playwright/live-paired-reply.svg');
  const [sculpture]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Save sculpture ↓',exact:true}).click()]);
  await sculpture.saveAs('output/playwright/live-browser-sculpture.stl');
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.startsWith('Sculpture saved'));
  const state=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  check(state.materialRunning==='false','Sculpture export did not freeze its material');
  const [snapshot]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Save material ↓',exact:true}).click()]);
  await snapshot.saveAs('output/playwright/live-browser-sculpture-material.json');
  const proof=await page.context().newPage();
  await proof.goto('file:///workspace/palimpsest/output/playwright/live-paired-reply.svg');
  const svg=await proof.locator('svg').first().evaluate(root=>({width:root.getAttribute('width'),height:root.getAttribute('height'),paths:root.querySelectorAll('path').length,metadata:JSON.parse(root.querySelector('metadata').textContent)}));
  check(svg.width==='1400'&&svg.height==='1050'&&svg.paths===8&&svg.metadata.comparison.samples>0,'The paired drawing is not self-contained');
  await proof.locator('svg').first().screenshot({path:'output/playwright/live-paired-reply-proof.jpg',type:'jpeg',quality:76});
  await proof.close();
  check(errors.length===0,'Export browser errors: '+errors.join('; '));
  return{drawing:{filename:drawing.suggestedFilename(),width:svg.width,height:svg.height,paths:svg.paths,samples:svg.metadata.comparison.samples,rms:svg.metadata.comparison.rms_hz},
    sculpture:{filename:sculpture.suggestedFilename(),state},errors};
}
