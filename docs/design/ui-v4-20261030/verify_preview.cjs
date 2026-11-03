const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--disable-gpu','--no-first-run']});
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file:///'+path.join(__dirname,'review.html').replaceAll('\\','/'));
 await page.waitForFunction(()=>window.WISEYE_DESIGN);
 await page.waitForTimeout(300);
 const screenshots=[],layoutChecks=[];
 async function capture(name){await page.locator('.toast').evaluate(x=>x.hidden=true);await page.waitForTimeout(180);await page.locator('#wiseye-design-v4 .app').screenshot({path:path.join(__dirname,name+'.png')});screenshots.push(name+'.png');
  if(['simulation-workbench','training-workbench','drone-control'].includes(name)){
   const bounds=await page.evaluate(()=>{
    const app=document.querySelector('#wiseye-design-v4 .app');const footer=app.querySelector('footer').getBoundingClientRect();
    const elements=[...app.querySelectorAll('#page-content button,#page-content input')].filter(x=>x.getClientRects().length);
    return {height:app.getBoundingClientRect().height,lowestControl:Math.max(...elements.map(x=>x.getBoundingClientRect().bottom)),footerTop:footer.top};
   });layoutChecks.push({name,...bounds,passed:bounds.lowestControl<=bounds.footerTop+2&&bounds.height<=1000});
  }
 }
 await capture('simulation-workbench');
 await page.locator('[data-action="sensor-infrared"]').first().click();await capture('sensor-parameters');
 await page.locator('[data-action="close-drawer"]').click();
 await page.locator('[data-go="scene"]').click();await capture('scene-arrangement');
 await page.locator('[data-go="fleet"]').click();await capture('fleet-management');
 await page.locator('[data-go="interfaces"]').click();await capture('data-interfaces');
 await page.locator('[data-go="settings"]').click();await capture('settings');
 await page.locator('[data-go="workbench"]').click();await page.locator('[data-control="drone"]').click();await capture('drone-control');
 await page.locator('[data-action="routes"]').click();await capture('route-editor');
 await page.locator('[data-app="train"]').click();await capture('training-workbench');
 const before=await page.locator('.gt').count();
 await page.locator('[data-check="gt"]').uncheck();const after=await page.locator('.gt').count();
 if(before<2||after!==0)throw Error('GT display toggle failed');
 await page.locator('[data-check="gt"]').check();
 await page.locator('[data-action="record"]').click();if(!await page.locator('[data-action="record"]').innerText().then(x=>x.includes('停止')))throw Error('Record state failed');
 await page.locator('[data-go="samples"]').click();await capture('sample-inspection');
 const responsive=[];
 for(const width of [1440,1024,736,390,320]){
   await page.setViewportSize({width,height:1080});
   for(const [app,which] of [['sim','workbench'],['sim','scene'],['sim','interfaces'],['train','collect'],['train','samples']]){
     await page.evaluate(({app,which})=>{const x=window.WISEYE_DESIGN;x.state.app=app;x.state.page=which;x.render()},{app,which});
     await page.waitForTimeout(50);
     const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
     responsive.push({width,page:which,overflow});
   }
 }
 const report={passed:errors.length===0&&responsive.every(x=>!x.overflow)&&layoutChecks.every(x=>x.passed),errors,screenshots,layoutChecks,responsive,notes:'Design-only local interactions. No backend/network requests or runtime modifications.'};
 fs.writeFileSync(path.join(__dirname,'preview-validation.json'),JSON.stringify(report,null,2));
 await browser.close();console.log(JSON.stringify(report,null,2));
 if(!report.passed)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
