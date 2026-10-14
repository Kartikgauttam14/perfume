// @ts-nocheck
// Keep gateway JWT verification ON: the gateway verifies signature and expiration.
// The handler additionally restricts the signed token to this project's service_role.
export function administrator(request, config) {
  const auth = request.headers.get('authorization') || '';
  if (config.adminKey && auth === `Bearer ${config.adminKey}`) return true;
  if (!config.projectRef || !auth.startsWith('Bearer ')) return false;
  try {
    const claims = JSON.parse(atob(auth.slice(7).split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
    return claims.role === 'service_role' && claims.ref === config.projectRef
      && claims.exp > Date.now()/1000;
  } catch { return false; }
}
export function makeTemplateAdmin(config, campaign, fetcher = fetch) {
  const api = 'https://graph.facebook.com/v26.0/';
  async function graph(path, options = {}) {
    const response = await fetcher(api + path, {...options,
      headers: {Authorization: `Bearer ${config.token}`, ...options.headers},
      signal: AbortSignal.timeout(20000)});
    const result = await response.json();
    if (!response.ok) throw Object.assign(new Error('Meta request failed'),
      {code: Number(result.error?.code) || 0, subcode: Number(result.error?.error_subcode) || 0});
    return result;
  }
  async function imageHandle(card) {
    const response = await fetcher(card.image, {signal: AbortSignal.timeout(15000)});
    if (!response.ok || !response.headers.get('content-type')?.startsWith('image/jpeg'))
      throw new Error('Product image unavailable');
    const bytes = await response.arrayBuffer();
    if (bytes.byteLength > 5000000) throw new Error('Image too large');
    const params = new URLSearchParams({file_name:'perfume.jpg',
      file_length:String(bytes.byteLength),file_type:'image/jpeg'});
    const session = await graph(`${config.appId}/uploads?${params}`, {method:'POST'});
    const uploaded = await graph(session.id, {method:'POST',body:bytes,
      headers:{Authorization:`OAuth ${config.token}`,file_offset:'0','Content-Type':'application/octet-stream'}});
    if (!uploaded.h) throw new Error('Image handle unavailable');
    return uploaded.h;
  }
  return async request => {
    if (!administrator(request, config))
      return new Response('Administrator authentication required',{status:403});
    if (!config.token) return new Response('Meta token missing',{status:503});
    if (!['GET','POST'].includes(request.method)) return new Response('Method not allowed',{status:405});
    try {
      const existing = await graph(`${config.waba}/message_templates?name=${campaign.template_name}&fields=id,name,status,language&limit=10`);
      const template = existing.data?.find(t=>t.name===campaign.template_name && t.language===campaign.language);
      if (template || request.method==='GET') return Response.json({template:template || null});
      const cards = [];
      for (const card of campaign.cards) cards.push({components:[
        {type:'HEADER',format:'IMAGE',example:{header_handle:[await imageHandle(card)]}},
        {type:'BODY',text:card.name},
        {type:'BUTTONS',buttons:[{type:'URL',text:card.button,url:card.url}]},
      ]});
      const created = await graph(`${config.waba}/message_templates`,{method:'POST',
        headers:{'Content-Type':'application/json'},body:JSON.stringify({
          name:campaign.template_name,language:campaign.language,category:'MARKETING',
          components:[{type:'BODY',text:campaign.body},{type:'CAROUSEL',cards}],
        })});
      return Response.json({template:{id:created.id,name:campaign.template_name,
        status:created.status,language:campaign.language}});
    } catch (error) {
      // Never expose tokens, upload handles or full Meta response bodies.
      return Response.json({error:'Template submission/check failed',meta_code:error.code || 0,
        meta_subcode:error.subcode || 0},{status:502});
    }
  };
}

// CAMPAIGN_DATA is embedded below for the dashboard's standalone editor.

const CAMPAIGN_DATA = {"template_name": "mansam_floral_collection", "language": "en", "body": "Discover three floral fragrances from Mansam.\nSwipe to find your favourite and tap Shop Now.", "cards": [{"name": "Hams Min Al Sahraa", "image": "https://ae.mansamworld.com/images/products/480/Hams_Min_Al_Sahraa_3.jpg", "button": "Shop Now", "url": "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Hams_Min_Al_Sahraa_/44"}, {"name": "Nasseem Al Ward", "image": "https://ae.mansamworld.com/images/products/480/Nasseem_Al_Ward_3.jpg", "button": "Shop Now", "url": "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Nasseem_Al_Ward/47"}, {"name": "Qublat Ward", "image": "https://ae.mansamworld.com/images/products/480/Qublat_3.jpg", "button": "Shop Now", "url": "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Qublat_Ward/49"}]};

if (typeof Deno !== 'undefined') {
  Deno.serve(makeTemplateAdmin({
    adminKey: Deno.env.get('SUPABASE_SERVICE_ROLE_KEY'),
    projectRef: 'fpyaudimfmhthepqohdm',
    token: Deno.env.get('WHATSAPP_ACCESS_TOKEN'),
    appId: '1075092785431646', waba: '1667300438368749',
  }, CAMPAIGN_DATA));
}
