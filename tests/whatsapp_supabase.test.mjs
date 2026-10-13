import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHandler } from '../supabase/functions/whatsapp-webhook/index.ts';

const config = {url:'https://test.supabase.co',dbKey:'test-db-key',verifyToken:'test-verify',
  appSecret:'test-secret',token:'test-token',phoneId:'123',enabled:true,version:'v25.0'};
async function signed(payload) {
  const body = JSON.stringify(payload);
  const key = await crypto.subtle.importKey('raw',new TextEncoder().encode(config.appSecret),
    {name:'HMAC',hash:'SHA-256'},false,['sign']);
  const sig = await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(body));
  const hex = Array.from(new Uint8Array(sig),b=>b.toString(16).padStart(2,'0')).join('');
  return new Request('https://test/functions/v1/whatsapp-webhook',{
    method:'POST',body,headers:{'x-hub-signature-256':`sha256=${hex}`}});
}
function payload(messages, phone='123') {
  return {object:'whatsapp_business_account',entry:[{changes:[{value:{
    metadata:{phone_number_id:phone},messages,statuses:[{id:'status1',status:'delivered'}]
  }}]}]};
}
function message(id='m1',type='text',age=0) {
  return {id,from:'10000000000',type,timestamp:String(Math.floor(Date.now()/1000)-age)};
}
function backend(failSend=false) {
  const rows=new Map(),sent=[];
  const fetcher=async (url,options)=>{
    const body=JSON.parse(options.body);
    if(url.includes('graph.facebook.com')) {
      sent.push(body);
      if(failSend) throw new Error('Timeout');
      return Response.json({messages:[{id:'out1'}]});
    }
    if(options.method==='POST') {
      if(rows.has(body.message_id)) return new Response('',{status:409});
      rows.set(body.message_id,body);
      return new Response('',{status:201});
    }
    const id=decodeURIComponent(url.split('eq.')[1]);
    Object.assign(rows.get(id),body);
    return new Response(null,{status:204});
  };
  return {rows,sent,fetcher};
}
test('verification challenge and invalid tokens',async()=>{
  const h=makeHandler(config);
  const good=await h(new Request('https://test/?hub.mode=subscribe&hub.verify_token=test-verify&hub.challenge=987'));
  assert.equal(good.status,200);assert.equal(await good.text(),'987');
  assert.equal((await h(new Request('https://test/?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=987'))).status,403);
});
test('reject unsigned requests and malformed signed data',async()=>{
  const h=makeHandler(config);
  assert.equal((await h(new Request('https://test/',{method:'POST',body:'{}'}))).status,401);
  assert.equal((await h(await signed({object:'whatsapp_business_account',entry:[{changes:null}]}))).status,400);
});
test('once per message, image header, statuses do not trigger replies',async()=>{
  const b=backend(),h=makeHandler(config,b.fetcher);
  assert.equal((await h(await signed(payload([message()])))).status,200);
  assert.equal((await h(await signed(payload([message()])))).status,200);
  assert.equal(b.sent.length,1);assert.equal(b.sent[0].template.name,'shop_now');
  assert.equal(b.sent[0].template.language.code,'en');
  assert.match(b.sent[0].template.components[0].parameters[0].image.link,/Safaa_Al_Nada_3.jpg$/);
  assert.equal(b.rows.get('m1').state,'accepted');
});
test('media messages trigger replies, old events/reactions/wrong phone do not',async()=>{
  const b=backend(),h=makeHandler(config,b.fetcher);
  await h(await signed(payload([message('image','image'),message('old','text',86401),message('reaction','reaction')])));
  await h(await signed(payload([message('other')],'other')));
  assert.equal(b.sent.length,1);
});
test('disabled mode records events without sending or replay on enable',async()=>{
  const b=backend();await makeHandler({...config,enabled:false},b.fetcher)(await signed(payload([message()])));
  await makeHandler(config,b.fetcher)(await signed(payload([message()])));
  assert.equal(b.sent.length,0);assert.equal(b.rows.get('m1').state,'disabled');
});
test('uncertain delivery is retained without duplicate retry',async()=>{
  const b=backend(true),h=makeHandler(config,b.fetcher);
  await h(await signed(payload([message()])));await h(await signed(payload([message()])));
  assert.equal(b.sent.length,1);assert.equal(b.rows.get('m1').state,'uncertain');
});
test('database outage requests Meta retry and never sends',async()=>{
  const h=makeHandler(config,async()=>new Response('',{status:503}));
  assert.equal((await h(await signed(payload([message()])))).status,503);
});
