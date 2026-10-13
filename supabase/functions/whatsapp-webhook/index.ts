// @ts-nocheck
// Meta signatures authenticate this endpoint; no Supabase user JWT is expected.
const IMAGE = 'https://ae.mansamworld.com/images/products/480/Safaa_Al_Nada_3.jpg';

export async function validSignature(raw, signature, secret) {
  if (!/^sha256=[0-9a-f]{64}$/.test(signature || '') || !secret) return false;
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']);
  const bytes = Uint8Array.from(signature.slice(7).match(/../g), hex => parseInt(hex, 16));
  return crypto.subtle.verify('HMAC', key, bytes, raw);
}

export function makeHandler(config, fetcher = fetch, waitUntil = null) {
  const dbUrl = `${config.url}/rest/v1/whatsapp_reply_events`;
  const dbHeaders = { apikey: config.dbKey, Authorization: `Bearer ${config.dbKey}`,
    'Content-Type': 'application/json' };
  async function db(method, query, body) {
    return fetcher(dbUrl + query, { method, headers: dbHeaders,
      body: JSON.stringify(body), signal: AbortSignal.timeout(10000) });
  }
  async function finish(id, state, outgoingId = null) {
    const response = await db('PATCH', `?message_id=eq.${encodeURIComponent(id)}`,
      { state, outgoing_id: outgoingId });
    if (!response.ok) throw new Error('Inbox update failed');
  }
  async function send(message) {
    try {
      const response = await fetcher(
        `https://graph.facebook.com/${config.version}/${config.phoneId}/messages`, {
          method: 'POST', headers: { Authorization: `Bearer ${config.token}`,
            'Content-Type': 'application/json' }, signal: AbortSignal.timeout(20000),
          body: JSON.stringify({ messaging_product: 'whatsapp', to: message.from,
            type: 'template', template: { name: 'shop_now', language: { code: 'en' },
              components: [{ type: 'header', parameters: [{ type: 'image',
                image: { link: config.image || IMAGE } }] }] } }),
        });
      if (!response.ok) {
        await finish(message.id, 'failed');
        console.error('WhatsApp template rejected: HTTP', response.status);
        return;
      }
      const result = await response.json();
      await finish(message.id, 'accepted', result.messages?.[0]?.id || null);
    } catch {
      // A timed-out send might have succeeded: do not send it again automatically.
      console.error('WhatsApp send/update uncertain; review inbox before retry');
      try { await finish(message.id, 'uncertain'); } catch { /* retain claimed state */ }
    }
  }
  return async function handler(request) {
    const url = new URL(request.url);
    if (request.method === 'GET') {
      if (!config.verifyToken) return new Response('Not configured', { status: 503 });
      if (url.searchParams.get('hub.mode') !== 'subscribe'
          || url.searchParams.get('hub.verify_token') !== config.verifyToken
          || !url.searchParams.has('hub.challenge')) {
        return new Response('Verification failed', { status: 403 });
      }
      return new Response(url.searchParams.get('hub.challenge'), {
        headers: { 'Content-Type': 'text/plain' },
      });
    }
    if (request.method !== 'POST') return new Response('Method not allowed', { status: 405 });
    if (!config.appSecret || !config.dbKey || !config.url || !config.phoneId)
      return new Response('Not configured', { status: 503 });
    const raw = await request.arrayBuffer();
    if (raw.byteLength > 1048576) return new Response('Payload too large', { status: 413 });
    if (!await validSignature(raw, request.headers.get('x-hub-signature-256'), config.appSecret))
      return new Response('Invalid signature', { status: 401 });
    let payload;
    try {
      payload = JSON.parse(new TextDecoder().decode(raw));
      if (payload.object !== 'whatsapp_business_account' || !Array.isArray(payload.entry))
        throw new Error('Invalid payload');
      for (const entry of payload.entry) {
        if (!Array.isArray(entry.changes)) throw new Error('Invalid changes');
        for (const change of entry.changes) {
          if (!change.value || (change.value.messages && !Array.isArray(change.value.messages)))
            throw new Error('Invalid messages');
        }
      }
    } catch { return new Response('Invalid payload', { status: 400 }); }
    if (config.enabled && !config.token) return new Response('Messaging token missing', { status: 503 });
    const jobs = [];
    try {
      for (const entry of payload.entry) for (const change of entry.changes) {
        const value = change.value;
        if (value.metadata?.phone_number_id !== config.phoneId) continue;
        for (const message of value.messages || []) {
          const age = Date.now() / 1000 - Number(message?.timestamp);
          if (!message?.id || !/^\d{5,20}$/.test(message.from || '')
              || !Number.isFinite(age) || age < -60 || age >= 86400
              || ['reaction', 'system', 'unsupported'].includes(message.type)
              || message.errors) continue;
          const response = await db('POST', '', { message_id: message.id,
            recipient: message.from, state: config.enabled ? 'claimed' : 'disabled',
            incoming_at: new Date(Number(message.timestamp) * 1000).toISOString() });
          if (response.status === 409) continue;
          if (!response.ok) throw new Error('Inbox insert failed');
          if (config.enabled) jobs.push(send(message));
        }
      }
    } catch {
      // Already claimed messages must finish even when a later insert fails.
      if (jobs.length && waitUntil) waitUntil(Promise.allSettled(jobs));
      else await Promise.allSettled(jobs);
      console.error('WhatsApp inbox storage failed');
      return new Response('Storage unavailable', { status: 503 });
    }
    const complete = Promise.allSettled(jobs);
    if (waitUntil) waitUntil(complete); else await complete;
    return Response.json({ status: 'received' });
  };
}

if (typeof Deno !== 'undefined') {
  const env = name => Deno.env.get(name) || '';
  const secretKeys = JSON.parse(env('SUPABASE_SECRET_KEYS') || '{}');
  const config = {
    url: env('SUPABASE_URL'), dbKey: secretKeys.default || Object.values(secretKeys)[0]
      || env('SUPABASE_SERVICE_ROLE_KEY'),
    verifyToken: env('WHATSAPP_VERIFY_TOKEN'), appSecret: env('META_APP_SECRET'),
    token: env('WHATSAPP_ACCESS_TOKEN'), phoneId: env('WHATSAPP_PHONE_NUMBER_ID'),
    enabled: env('WHATSAPP_AUTO_REPLY_ENABLED').toLowerCase() === 'true',
    version: env('WHATSAPP_API_VERSION') || 'v25.0', image: env('WHATSAPP_TEMPLATE_IMAGE_URL') || IMAGE,
  };
  Deno.serve(makeHandler(config, fetch, promise => EdgeRuntime.waitUntil(promise)));
}
