async (page) => {
  await page.addScriptTag({path:'/workspace/palimpsest/.tools/browser/node_modules/axe-core/axe.min.js'});
  return await page.evaluate(async () => {
    const result = await axe.run(document, {
      runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']},
      resultTypes:['violations','incomplete']
    });
    return {
      url:location.href,
      viewport:{width:innerWidth,height:innerHeight},
      axeVersion:result.testEngine.version,
      violations:result.violations.map(({id,impact,description,nodes})=>({id,impact,description,nodes:nodes.map(({target,failureSummary})=>({target,failureSummary}))})),
      incomplete:result.incomplete.map(({id,nodes})=>({id,targets:nodes.map(node=>node.target)})),
      note:'Automated WCAG checks supplement the rendered, keyboard and media-control inspection.'
    };
  });
}
