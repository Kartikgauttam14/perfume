// @ts-nocheck
// Administrator-only, explicit one-time tests. Recipient numbers never live in source.
export async function sendTemplateTests(input, config, campaign, graph, fetcher) {
  const recipients = [...new Set(input.recipients || [])];
  if (!/^[a-zA-Z0-9-]{10,80}$/.test(input.batch_id || '') || !recipients.length
      || recipients.length > 2 || recipients.some(n=>typeof n!=='string' || !/^\d{8,15}$/.test(n)))
    return Response.json({error:'Provide a unique batch_id and one or two international numbers'},{status:400});
  if (!config.dbUrl || !config.dbKey || !config.phoneId)
    return Response.json({error:'Test inbox not configured'},{status:503});
  const headers = {apikey:config.dbKey,Authorization:`Bearer ${config.dbKey}`,'Content-Type':'application/json'};
  const db = (method,query,body) => fetcher(`${config.dbUrl}/rest/v1/whatsapp_reply_events${query}`,
    {method,headers,body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(10000)});
  const cards=[];
  for (let i=0;i<campaign.cards.length;i++) {
    const image=await fetcher(campaign.cards[i].image,{signal:AbortSignal.timeout(15000)});
    if (!image.ok) throw new Error('Product image unavailable');
    const form=new FormData();
    form.set('messaging_product','whatsapp');form.set('type','image/jpeg');
    form.set('file',new Blob([await image.arrayBuffer()],{type:'image/jpeg'}),'perfume.jpg');
    const media=await graph(`${config.phoneId}/media`,{method:'POST',body:form});
    if (!media.id) throw new Error('Product media upload failed');
    cards.push({card_index:i,components:[{type:'header',parameters:[{type:'image',image:{id:media.id}}]}]});
  }
  const results=[];
  for (const recipient of recipients) {
    const id=`campaign-test:${input.batch_id}:${recipient}`;
    const query=`?message_id=eq.${encodeURIComponent(id)}`;
    const now=new Date().toISOString();
    const claim=await db('POST','',{message_id:id,recipient,incoming_at:now,state:'claimed'});
    if (claim.status===409) {
      const previous=await db('GET',query+'&select=state,outgoing_id');
      const row=previous.ok?(await previous.json())[0]:null;
      results.push({recipient,state:row?.state || 'existing',outgoing_id:row?.outgoing_id || null,duplicate_suppressed:true});
      continue;
    }
    if (!claim.ok) {results.push({recipient,state:'not_sent',reason:'Storage unavailable'});continue;}
    let state='uncertain',outgoing_id=null,meta_code=0;
    try {
      const sent=await graph(`${config.phoneId}/messages`,{method:'POST',
        headers:{'Content-Type':'application/json'},body:JSON.stringify({messaging_product:'whatsapp',
          recipient_type:'individual',to:recipient,type:'template',template:{name:campaign.template_name,
            language:{code:campaign.language},components:[{type:'carousel',cards}]}})});
      outgoing_id=sent.messages?.[0]?.id || null;
      state=outgoing_id?'accepted':'uncertain';
    } catch(error) {meta_code=error.code || 0;state=meta_code?'failed':'uncertain';}
    const updated=await db('PATCH',query,{state,outgoing_id}).catch(()=>null);
    results.push({recipient,state,outgoing_id,meta_code,record_updated:!!updated?.ok});
  }
  return Response.json({batch_id:input.batch_id,results});
}
