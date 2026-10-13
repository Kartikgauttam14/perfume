import test from 'node:test';
import assert from 'node:assert/strict';
import {fallbackReply, prepareReply, replyPayload, twoLines} from '../supabase/functions/whatsapp-webhook/reply.ts';

test('different notes select relevant products; greetings and support do not promote',()=>{
  for (const note of ['rose','oud','jasmine','leather']) {
    const reply=fallbackReply(`Show me ${note} perfumes`);
    assert.ok(reply.products.length);
    assert.ok(reply.products.every(p=>p.notes.some(n=>n.toLowerCase().includes(note))));
    assert.equal(reply.text.split('\n').length,2);
  }
  for (const q of ['hi','Where is my order? order status','refund please','price','stop'])
    assert.equal(fallbackReply(q).products.length,0);
  assert.ok(fallbackReply('rose without oud').products.every(p=>!p.notes.includes('Oud')));
});

test('exact product gets a single image/URL button; multi-product gets carousel',()=>{
  const single=replyPayload('10000000000',fallbackReply('Safaa Al Nada'));
  // Direct-name requests should show that product, not unrelated products.
  assert.equal(single.interactive.type,'cta_url');
  assert.match(single.interactive.header.image.link,/Safaa_Al_Nada_3.jpg$/);
  assert.match(single.interactive.action.parameters.url,/\/42$/);
  const many=replyPayload('10000000000',fallbackReply('rose'));
  assert.equal(many.interactive.type,'carousel');
  assert.deepEqual(many.interactive.action.cards.map(c=>c.card_index),[0,1,2]);
});

test('all offered scent choices return three relevant perfume cards, including Floral follow-up',async()=>{
  for (const choice of ['Floral','Fresh','Oud','Musk','Sweet','Woody','Smoky','زهري','منعش']) {
    const reply=await prepareReply({text:{body:choice}});
    assert.equal(reply.products.length,3,choice);
    const payload=replyPayload('10000000000',reply);
    assert.equal(payload.interactive.type,'carousel',choice);
    assert.equal(payload.interactive.action.cards.length,3,choice);
    assert.equal(payload.interactive.body.text.split('\n').length,2,choice);
  }
  assert.ok(fallbackReply('Floral').products.every(p=>p.notes.some(n=>/rose|jasmine|narcissus|lily|floral|blossom|neroli/i.test(n))));
  assert.ok(fallbackReply('Fresh').products.every(p=>p.notes.some(n=>/citrus|bergamot|neroli|blossom|rain/i.test(n))));
});

test('short replies never exceed two lines or 110 characters per line',()=>{
  assert.equal(twoLines('First line.\nSecond line.\nUnwanted line.'),'First line.\nSecond line.');
  assert.ok(twoLines('x'.repeat(1000)).length<=110);
});

test('no AI request is made; media gets a text clarification',async()=>{
  const reply=await prepareReply({text:{body:'jasmine'}},{conciergeUrl:'https://own-site/api/chat'},async()=>{throw new Error('timeout')});
  assert.ok(reply.products.length>0);
  const media=await prepareReply({type:'audio'},{},async()=>{throw new Error('should not call')});
  assert.equal(media.products.length,0);
});
