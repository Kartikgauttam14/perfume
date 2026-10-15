import test from 'node:test';
import assert from 'node:assert/strict';
import {sendTemplateTests} from '../supabase/functions/whatsapp-template-admin/send-test.ts';
const campaign={template_name:'test',language:'en',cards:[{image:'https://shop/image.jpg'},{image:'https://shop/image2.jpg'},{image:'https://shop/image3.jpg'}]};
const config={dbUrl:'https://db',dbKey:'private',phoneId:'phone'};
test('two recipients receive one approved carousel each; repeating batch never resends',async()=>{
  const rows=new Map(),sent=[];
  const fetcher=async(url,opts)=>{
    if(url.startsWith('https://shop/'))return new Response(new Uint8Array([1]));
    const body=opts.body?JSON.parse(opts.body):null;
    if(opts.method==='POST') {
      if(rows.has(body.message_id))return new Response(null,{status:409});
      rows.set(body.message_id,body);return new Response(null,{status:201});
    }
    const id=decodeURIComponent(url.split('eq.')[1].split('&')[0]);
    if(opts.method==='GET')return Response.json([rows.get(id)]);
    Object.assign(rows.get(id),body);return new Response(null,{status:204});
  };
  const graph=async(path,opts)=>{
    if(path.endsWith('/media'))return {id:'media'};
    const body=JSON.parse(opts.body);sent.push(body);return {messages:[{id:'out'+sent.length}]};
  };
  const input={batch_id:'test-batch-001',recipients:['10000000001','10000000002']};
  const first=await (await sendTemplateTests(input,config,campaign,graph,fetcher)).json();
  assert.equal(first.results.length,2);assert.ok(first.results.every(r=>r.state==='accepted'));
  const second=await (await sendTemplateTests(input,config,campaign,graph,fetcher)).json();
  assert.ok(second.results.every(r=>r.duplicate_suppressed));assert.equal(sent.length,2);
  assert.equal(sent[0].template.components[0].cards.length,3);
});
test('invalid numbers and missing batch id never send',async()=>{
  const never=()=>{throw new Error('must not call')};
  assert.equal((await sendTemplateTests({recipients:['invalid']},config,campaign,never,never)).status,400);
});
