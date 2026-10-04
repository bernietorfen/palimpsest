// Attribute production policy reports without changing the delivered policy.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {chromium} from '../.tools/browser/node_modules/playwright/index.mjs';
const output=process.argv[2],base=process.argv[3];if(!output||fs.existsSync(output))throw Error('New output required');fs.mkdirSync(output,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--no-sandbox']}),page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});let phase='navigation';const consoleErrors=[];
page.on('console',m=>{if(m.type()==='error')consoleErrors.push({phase,text:m.text(),location:m.location()});});
await page.addInitScript(()=>{window.policy=[];window.insertedStyles=[];addEventListener('securitypolicyviolation',e=>window.policy.push({phase:window.auditPhase,directive:e.effectiveDirective,source:e.sourceFile,line:e.lineNumber,sample:e.sample}));new MutationObserver(records=>{for(const record of records)for(const node of record.addedNodes)if(node.nodeType===1){const styles=node.matches?.('style')?[node]:[...node.querySelectorAll?.('style')||[]];for(const style of styles)window.insertedStyles.push({phase:window.auditPhase,text:style.textContent});}}).observe(document,{childList:true,subtree:true});});
const at=async value=>{phase=value;await page.evaluate(value=>window.auditPhase=value,value);};
try{
 await page.goto(base+'/observer.html');await page.waitForFunction(()=>document.body.dataset.ready==='true');await page.evaluate(()=>document.fonts.ready);
 await at('screenshot-opening');await page.screenshot({caret:'initial',path:output+'/opening.jpg',type:'jpeg',quality:70});
 await at('keyboard-and-crossings');await page.locator('#origin-next').click();await page.locator('#origin-shift').focus();await page.keyboard.press('End');await page.keyboard.press('ArrowLeft');
 await at('screenshot-focused-input');await page.locator('#moving-origin').screenshot({caret:'initial',path:output+'/focused.jpg',type:'jpeg',quality:70});
 await at('export');const ready=page.waitForEvent('download');await page.locator('#origin-export').click();await(await ready).saveAs(output+'/position.svg');
 await at('parse-export-inside-exhibition');const exported=fs.readFileSync(output+'/position.svg','utf8');const embeddedStyle=await page.evaluate(text=>new DOMParser().parseFromString(text,'image/svg+xml').querySelector('style').textContent,exported);await page.waitForTimeout(100);const embeddedStyleSha256Base64=crypto.createHash('sha256').update(embeddedStyle).digest('base64');
 await at('mobile');await page.setViewportSize({width:393,height:852});await page.locator('#moving-origin').scrollIntoViewIfNeeded();
 await at('screenshot-mobile');await page.screenshot({caret:'initial',path:output+'/mobile.jpg',type:'jpeg',quality:70});
 await at('axe-injection');await page.evaluate(fs.readFileSync('.tools/browser/node_modules/axe-core/axe.min.js','utf8'));
 await at('axe-execution');const axe=await page.evaluate(async()=>{const result=await window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return{violations:result.violations.map(v=>v.id),incomplete:result.incomplete.map(v=>v.id)};});
 await at('settled');await page.waitForTimeout(100);const report={base,consoleErrors,axe,embeddedStyleSha256Base64,...await page.evaluate(()=>({policy:window.policy,insertedStyles:window.insertedStyles}))};for(const style of report.insertedStyles)style.sha256Base64=crypto.createHash('sha256').update(style.text).digest('base64');fs.writeFileSync(output+'/report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{await browser.close();}
