// @ts-nocheck
import { PRODUCTS } from './catalog.ts';

const normalize = text => String(text || '').toLowerCase().replace(/[_\s]+/g, ' ').trim();
export function twoLines(text) {
  const lines = String(text || '').replace(/\*|#/g, '').split(/\n+/).map(s => s.trim()).filter(Boolean);
  if (lines.length < 2) {
    const sentences = lines.join(' ').split(/(?<=[.!?؟])\s+/);
    if (sentences.length > 1) lines.splice(0, lines.length, sentences[0], sentences.slice(1).join(' '));
  }
  return lines.slice(0, 2).map(line => line.length > 110 ? line.slice(0, 107).trimEnd() + '…' : line).join('\n');
}

export function fallbackReply(query) {
  const q = normalize(query), ar = /[\u0600-\u06ff]/.test(q);
  const reply = (en, arabic, products = [], fixed = false) => ({ text: ar ? arabic : en, products, fixed });
  if (/^(stop|unsubscribe|cancel promotions|توقف|إلغاء الاشتراك)[.!\s]*$/.test(q))
    return reply('Understood — I won’t send product suggestions in this reply.\nFor account requests: customercare@mansamworld.com.', 'حاضر، لن أرسل ترشيحات في هذا الرد.\nلطلبات الحساب: customercare@mansamworld.com.', [], true);
  if (/\b(order status|track|shipping|delivery|refund|return|cancel order|payment|complaint)\b|شحن|توصيل|استرجاع|طلباتي/.test(q))
    return reply('For order, delivery or return help, contact customercare@mansamworld.com.\nPlease include your order reference in your email.', 'للمساعدة بالطلب أو التوصيل أو الاسترجاع: customercare@mansamworld.com.\nيرجى ذكر رقم الطلب في بريدك.', [], true);
  if (/\b(price|cost|discount|sale|offer|budget)\b|سعر|خصم|عرض/.test(q))
    return reply('Current prices and available offers are shown in our online store.\nhttps://ae.mansamworld.com/', 'الأسعار والعروض المتاحة تظهر في متجرنا الإلكتروني.\nhttps://ae.mansamworld.com/', [], true);
  if (/\b(location|store|boutique|address)\b|فروع|موقع|عنوان/.test(q))
    return reply('Find Mansam boutique locations here.\nhttps://ae.mansamworld.com/boutiques', 'تجد مواقع بوتيكات منسم هنا.\nhttps://ae.mansamworld.com/boutiques', [], true);
  const keywords = [
    ['oud', /\b(oud|oudh)\b|عود/], ['rose', /\b(rose|roses)\b|ورد/],
    ['jasmine', /\bjasmine\b|ياسمين/], ['musk', /\bmusk\b|مسك/],
    ['vanilla', /\bvanilla\b|فانيلا/], ['citrus', /\bcitrus\b|حمضيات/],
    ['fresh', /\b(fresh|summer|daily)\b|منعش|صيف/],
    ['floral', /\b(floral|flowery|flowers?|florals)\b|زهري|زهرية|زهور/],
    ['sweet', /\b(sweet|gourmand)\b|حلو|سكرية/],
    ['woody', /\b(woody|woods?|woodsy)\b|خشبي|خشبية/],
    ['smoky', /\b(smoky|smokey|bold)\b|دخاني/],
    ['leather', /\bleather\b|جلد/],
  ].filter(([, pattern]) => pattern.test(q)).map(([note]) => note);
  const families = {
    floral: ['rose','jasmine','narcissus','lily','floral','orange blossom','neroli'],
    fresh: ['citrus','bergamot','neroli','orange blossom','rain'],
    sweet: ['vanilla','almond','benzoin','plum'],
    woody: ['wood','oud','sandalwood','cedar'],
    smoky: ['smok','leather','incense'],
  };
  const matches = (product, keyword) => product.notes.some(note =>
    (families[keyword] || [keyword]).some(term => normalize(note).includes(term)));
  const excluded = [...q.matchAll(/\b(?:no|not|without|avoid)\s+(oudh?|rose|jasmine|musk|vanilla|leather)\b/g)].map(m => m[1].replace('oudh','oud'));
  const ranked = PRODUCTS.map(p => ({p,score: normalize(q).includes(normalize(p.name)) ? 100 :
    keywords.filter(k => matches(p,k)).length}))
    .filter(({p,score}) => score > 0 && !excluded.some(k => p.notes.some(n => normalize(n).includes(k))))
    .sort((a,b) => b.score-a.score).slice(0,3).map(x => x.p);
  if (ranked.length) return reply('Here are Mansam perfumes matching your request.\nTap Shop Now to explore each fragrance.', 'هذه عطور منسم المطابقة لطلبك.\nاضغط «تسوق الآن» لاستكشاف كل عطر.', ranked);
  return reply('Welcome to Mansam — I can help you choose a perfume.\nDo you prefer fresh, floral, oud or musk scents?', 'أهلاً بك في منسم، أساعدك باختيار عطرك.\nتفضل الروائح المنعشة، الزهرية، العود أم المسك؟');
}

export async function prepareReply(message, config, fetcher) {
  const query = message.text?.body || message.interactive?.button_reply?.title
    || message.interactive?.list_reply?.title || message.button?.text || '';
  if (!query) return {text: 'Please send your perfume question as text.\nI can help with fragrance suggestions or shopping questions.', products: []};
  const fallback = fallbackReply(query);
  return fallback;
}

export function replyPayload(to, reply) {
  const base = {messaging_product:'whatsapp', recipient_type:'individual', to};
  const text = twoLines(reply.text), products = reply.products || [];
  const card = p => ({type:'cta_url',header:{type:'image',image:{link:p.image}},
    body:{text:p.name}, action:{name:'cta_url',parameters:{display_text:'Shop Now',url:p.url}}});
  if (products.length >= 2) return {...base,type:'interactive',interactive:{
    type:'carousel',body:{text},action:{cards:products.map((p,i)=>({card_index:i,...card(p)}))}}};
  if (products.length === 1) return {...base,type:'interactive',interactive:{
    ...card(products[0]),body:{text}}};
  return {...base,type:'text',text:{body:text,preview_url:false}};
}
