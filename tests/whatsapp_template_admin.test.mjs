import test from 'node:test';
import assert from 'node:assert/strict';
import {makeTemplateAdmin,administrator} from '../supabase/functions/whatsapp-template-admin/index.ts';
const config={adminKey:'admin',token:'meta',appId:'app',waba:'waba'};
const campaign={template_name:'mansam_floral_collection',language:'en',body:'Discover perfumes.\nShop now.',
  cards:Array.from({length:3},(_,i)=>({name:`Perfume ${i}`,image:`https://shop/image${i}.jpg`,button:'Shop Now',url:`https://shop/product${i}`}))};
const request=method=>new Request('https://test',{method,headers:{authorization:'Bearer admin'}});
test('gateway-verified JWT claims must identify this project and administrator role',()=>{
  const token=claims=>'header.'+Buffer.from(JSON.stringify(claims)).toString('base64url')+'.signature';
  const check=claims=>administrator(new Request('https://test',{headers:{authorization:'Bearer '+token(claims)}}),{projectRef:'project'});
  const claims={role:'service_role',ref:'project',exp:Date.now()/1000+60};
  assert.equal(check(claims),true);
  assert.equal(check({...claims,role:'anon'}),false);
  assert.equal(check({...claims,ref:'other'}),false);
  assert.equal(check({...claims,exp:0}),false);
});
test('unauthorized callers cannot read or create templates',async()=>{
  const h=makeTemplateAdmin(config,campaign,()=>{throw new Error('must not call')});
  assert.equal((await h(new Request('https://test',{method:'POST'}))).status,403);
});
test('existing template is returned without uploads or duplicate creation',async()=>{
  let calls=0;const h=makeTemplateAdmin(config,campaign,async()=>{calls++;return Response.json({data:[{id:'123',name:campaign.template_name,language:'en',status:'PENDING'}]})});
  const result=await h(request('POST'));assert.equal((await result.json()).template.status,'PENDING');assert.equal(calls,1);
});
test('three media handles produce one three-card marketing submission',async()=>{
  let submitted;
  const h=makeTemplateAdmin(config,campaign,async(url,options)=>{
    if(url.startsWith('https://shop'))return new Response(new Uint8Array([1,2]),{headers:{'content-type':'image/jpeg'}});
    if(url.includes('message_templates?'))return Response.json({data:[]});
    if(url.includes('/uploads?'))return Response.json({id:'upload:123'});
    if(url.endsWith('upload:123')){assert.equal(options.headers.Authorization,'OAuth meta');return Response.json({h:'sample-handle'});}
    submitted=JSON.parse(options.body);return Response.json({id:'created',status:'PENDING'});
  });
  assert.equal((await h(request('POST'))).status,200);
  assert.equal(submitted.category,'MARKETING');assert.equal(submitted.components[1].cards.length,3);
});
