// WebKit's Playwright screenshot hook appends a literal `body {}` stylesheet
// to synchronize animations. A strict deployed CSP correctly blocks that test
// hook. Keep those attributable warnings separate from application errors.
// The installed coreBundle.js/inPagePrepareForScreenshots and the recorded
// choir_csp_diagnostic establish the cause; no application policy is bypassed.
const screenshotStyleMessage="Refused to apply a stylesheet because its hash, its nonce, or 'unsafe-inline' does not appear in the style-src directive of the Content Security Policy.";
export function screenshotEvidence(page,engine,applicationErrors){
 const warnings=[];let active=null,count=0;
 page.on('console',message=>{
  if(message.type()!=='error')return;
  if(engine==='webkit'&&active&&message.text()===screenshotStyleMessage){active.warnings++;warnings.push({capture:active.number,cause:'Playwright WebKit screenshot synchronization stylesheet blocked by deployed CSP',message:message.text()});}
  else applicationErrors.push(message.text());
 });
 async function capture(target,options={}){
  if(active)throw new Error('Evidence screenshots must be sequential');const shot={number:++count,warnings:0};active=shot;
  try{const value=await target.screenshot({caret:'initial',...options});if(shot.warnings>1)throw new Error('Unexpected additional stylesheet violation during screenshot');return value;}finally{active=null;}
 }
 return {capture,warnings};
}
