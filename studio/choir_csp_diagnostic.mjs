// Attribute CSP violations to delivered application actions versus audit instrumentation.
import fs from 'node:fs';
import {webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
const output=process.argv[2],base=process.argv[3];if(!output||fs.existsSync(output))throw new Error('New evidence directory required');fs.mkdirSync(output,{recursive:true});
const browser=await webkit.launch(),page=await browser.newPage({viewport:{width:1200,height:900},reducedMotion:'reduce'});page.setDefaultTimeout(45000);let phase='load';const messages=[];
page.on('console',m=>{if(m.type()==='error')messages.push({phase,message:m.text(),location:m.location()});});
await page.addInitScript(()=>{window.policyViolations=[];addEventListener('securitypolicyviolation',e=>window.policyViolations.push({phase:window.diagnosticPhase,blockedURI:e.blockedURI,sourceFile:e.sourceFile,lineNumber:e.lineNumber,sample:e.sample,directive:e.effectiveDirective}));});
async function at(value){phase=value;await page.evaluate(v=>window.diagnosticPhase=v,value);}
try{
 await page.goto(base+'/');await page.waitForFunction(()=>document.querySelector('#choir-downloads a').textContent.includes('Film master'));
 await at('open-viewer');await page.locator('[data-choir-sculpture="encounter"]').click();await page.waitForFunction(()=>document.querySelector('#choir-sculpture-canvas').dataset.state==='ready');
 await at('screenshot-instrumentation');await page.screenshot({caret:'initial',path:output+'/viewer.jpg',type:'jpeg',quality:75});
 await at('close-viewer');await page.keyboard.press('Escape');await page.waitForFunction(()=>!document.querySelector('#choir-sculpture-dialog').open&&document.body.style.overflow==='');
 await at('film');await page.locator('[data-choir-seek="248"]').click();await page.waitForFunction(()=>document.querySelector('#ensemble-film').currentTime>249);await page.locator('#ensemble-film').evaluate(v=>v.pause());
 await at('axe-instrumentation');await page.evaluate(fs.readFileSync('.tools/browser/node_modules/axe-core/axe.min.js','utf8'));const axe=await page.evaluate(async()=>{const r=await window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations.map(v=>v.id)};});
 const report={base,messages,policyViolations:await page.evaluate(()=>window.policyViolations),axe};fs.writeFileSync(output+'/report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{await browser.close();}
