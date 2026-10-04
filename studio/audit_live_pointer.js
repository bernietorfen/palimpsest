async(page)=>{
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.goto('http://127.0.0.1:8083/instrument.html');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time!==undefined);
  await page.getByRole('button',{name:'Begin silently',exact:true}).click();
  await page.waitForFunction(()=>document.body.dataset.running==='true');
  const first=await page.locator('.voice-key').nth(0).boundingBox();
  const third=await page.locator('.voice-key').nth(2).boundingBox();
  const stage=await page.locator('.live-stage').boundingBox();
  const last=await page.locator('.voice-key').last().boundingBox();
  check(stage.y>=-2&&stage.y+stage.height<page.viewportSize().height,'Playing view did not keep the material visible');
  if(page.viewportSize().width<640)check(last.y+last.height<=page.viewportSize().height+1,'The mobile voice keys extend below the playing viewport');
  await page.mouse.move(first.x+first.width/2,first.y+first.height/2);await page.mouse.down();
  await page.waitForFunction(()=>document.querySelectorAll('.voice-key')[0].getAttribute('aria-pressed')==='true');
  await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>2);
  await page.mouse.move(third.x+third.width/2,third.y+third.height/2,{steps:9});
  await page.waitForFunction(()=>document.querySelectorAll('.voice-key')[2].getAttribute('aria-pressed')==='true');
  const slide=await page.locator('.voice-key').evaluateAll(buttons=>buttons.map(b=>b.getAttribute('aria-pressed')));
  check(slide.filter(x=>x==='true').length===1&&slide[2]==='true','Sliding did not transfer the held voice');
  await page.mouse.up();
  check(await page.locator('.voice-key[aria-pressed="true"]').count()===0,'Released pointer left a voice held');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  await page.locator('#playing').evaluate(e=>e.scrollIntoView({block:'start'}));
  await page.screenshot({path:'output/playwright/live-mobile-playing-001.jpg',type:'jpeg',quality:77});
  await page.addScriptTag({path:'.tools/browser/node_modules/axe-core/axe.min.js'});
  const a11y=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return{violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:r.incomplete.map(v=>v.id)};});
  return{browser:page.context().browser().browserType().name(),viewport:page.viewportSize(),stage,last,slide,a11y,
    overflow:await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth),scope:'Pointer capture and drag, responsive playing layout, automated accessibility scan. Mouse-driven pointer events on the emulated viewport; not a physical touchscreen test.'};
}
