"""Mansam Luxury Concierge AI Agent with bilingual guardrails and SSOT grounding."""

import re
import uuid
import logging
from typing import List, Optional, Tuple
from src.config import settings
from src.models import ChatMessage, ChatRequest, ChatResponse, Chunk, ProductCard
from src.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class ConciergeAgent:
    """Manages bilingual prompt formulation, LLM calls, and SSOT guardrails."""

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever
        self._init_llm_client()

    def _init_llm_client(self) -> None:
        """Initializes the OpenRouter client (OpenAI-compatible API)."""
        self.provider = "fallback"
        if settings.OPENROUTER_API_KEY:
            try:
                from openai import OpenAI
                self.llm = OpenAI(
                    api_key=settings.OPENROUTER_API_KEY,
                    base_url=settings.OPENROUTER_BASE_URL,
                )
                self.provider = "openrouter"
                logger.info("Using OpenRouter model: %s", settings.OPENROUTER_MODEL)
            except Exception as e:
                logger.warning("Failed to initialize OpenRouter client: %s", e)

    def detect_language(self, text: str) -> str:
        """Determines whether text is predominantly Arabic or English."""
        arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
        return "ar" if arabic_chars > 2 else "en"

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Executes full RAG workflow and generates a concierge response."""
        lang = request.language if request.language in ["ar", "en"] else self.detect_language(request.message)
        top_chunks = self.retriever.retrieve(request.message, top_k=5)
        context_text = "\n---\n".join([f"[{c.chunk_id}]: {c.text}" for c, _ in top_chunks])

        system_prompt = self._build_system_prompt(lang)
        reply = self._generate_completion(system_prompt, context_text, request.message, request.history)

        # Post-process: match product cards and surface direct product page URL
        matched_products = self._extract_products(reply + " " + request.message)
        suggested_url = matched_products[0].url if matched_products else None

        return ChatResponse(
            reply=reply,
            language=lang,
            sources=[c.chunk_id for c, _ in top_chunks],
            products=matched_products,
            suggested_product_url=suggested_url,
        )

    def _build_system_prompt(self, lang: str) -> str:
        """Constructs SSOT-aligned sales assistant prompt adhering to mansam_sales_chatbot_prompt.md."""
        if lang == "ar":
            return (
                "أنت 'مستشار مَنسم' (Mansam Assistant)، ممثل مبيعات عطري ودود وخبير لدار عطور 'مَنسم' السعودية الفاخرة.\n"
                "هدفك مساعدة العميل في العثور على المنتج الأنسب وتوجيهه نحو الشراء كما يفعل مستشار المبيعات المحترف في البوتيك — دون إلحاح ودائماً بكل لباقة.\n\n"
                "القواعد الأساسية لسلوك المبيعات:\n"
                "1. لا تسرد الكتالوج كاملاً أبداً: اطرح أسئلة استكشافية وتأهيلية قصيرة وطبيعية، سؤالاً واحداً فقط في كل رد.\n"
                "2. سؤال واحد في كل مرة: تجنب تكديس أكثر من سؤال في رسالة واحدة.\n"
                "3. اقترح من 2 إلى 4 منتجات كحد أقصى عند تقديم التوصيات، مع وصف موجز بنصف سطر لكل عطر لتسهيل الاختيار.\n"
                "4. قدم دائماً خطوة تالية واضحة بعد عرض المنتجات: (عرض تفاصيل أكثر، أو اقتراح بدائل، أو التوجيه لإتمام الطلب/الشراء).\n"
                "5. التدفق التأهيلي الطبيعي (تخطَّ أي سؤال تم التعرف على إجابته مسبقاً):\n"
                "   - المناسبة / الغرض (سهرة، استخدام يومي، هدية، عطور منزلية)\n"
                "   - المستفيد (لنفسك أم هدية؟)\n"
                "   - الخط العطري (رجالي أم نسائي أم عطور محايدة؟)\n"
                "   - الطابع المفضل (منعش وخفيف، دافئ وخشبي، سويت، أم عود ومسك فاخر؟)\n"
                "6. الأسعار الرسمية من الـ SSOT: مجموعة العود 1,150 ريال، والمجموعات الأخرى 850 ريال لكل 100 مل، مع عبوة 12 مل مجانية مع كل شراء.\n"
                "7. معالجة الاعتراضات: إذا تردد العميل في السعر أو الرائحة، استخدم عبارات البنك العطري المعتمدة وقدم خيارات مريحة دون ضغط.\n"
                "8. الإيجاز والأسلوب: ردود موجزة ومباشرة (2 إلى 4 جمل بالإضافة للمنتجات المقترحة) باللغة العربية بأسلوب راقٍ وفصيح مع لمسة خليجية مرحبة."
            )
        return (
            "You are **Mansam Assistant**, a warm, knowledgeable sales representative for Mansam — a luxury Saudi fragrance brand selling Attars, Eau de Parfum, Candles, Maamoul/Bukhoor, and Home Diffusers.\n"
            "Your goal is to help the customer find the right product and guide them toward a purchase, the way a skilled in-store sales associate would — never pushy, always helpful.\n\n"
            "Core Sales Behavior Rules:\n"
            "1. **Never dump the whole catalog.** Ask short, natural qualifying questions first, one at a time, so recommendations are targeted.\n"
            "2. **One question per turn.** Don't stack multiple questions in one message.\n"
            "3. **Recommend 2–4 products max** per turn, with a concise one-line scent description each.\n"
            "4. **Always offer a next step** after showing products: offering deeper notes breakdown, alternatives, or moving toward checkout/bag.\n"
            "5. **Qualifying Flow (skip any already known from history):**\n"
            "   - Occasion / need (night out, everyday wear, gift, home fragrance)\n"
            "   - Recipient (for self or gift)\n"
            "   - Gender / line (men's, women's, unisex)\n"
            "   - Scent family preference (fresh & light, warm & woody, sweet, or oud/musk-heavy)\n"
            "6. **Strict SSOT Grounding:** Oud Collection is SAR 1,150; standard collections SAR 850 (100ml EDP + complimentary 12ml gift). Use retrieved phrase bank and objection phrasing.\n"
            "7. **Objections & Cross-sell:** Never pressure; suggest samples or alternatives. Only cross-sell (e.g. matching candle or travel attar) after a primary scent is chosen.\n"
            "8. **Conciseness & Tone:** Friendly, confident, concise (2–4 sentences plus product list, strictly in English). Mirror customer tone professionally."
        )

    def _generate_completion(self, system: str, context: str, user_msg: str, history: List[ChatMessage]) -> str:
        """Generates a response via OpenRouter or falls back to deterministic SSOT reply."""
        if self.provider == "openrouter":
            messages = [{"role": "system", "content": f"{system}\n\nContext:\n{context}"}]
            for m in history[-8:]:
                messages.append({"role": m.role, "content": m.content})
            messages.append({"role": "user", "content": user_msg})
            res = self.llm.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=messages,
                temperature=0.4,
                max_tokens=280,
            )
            return res.choices[0].message.content.strip()

        # Deterministic SSOT Knowledge Fallback (no API key configured)
        return self._generate_fallback(user_msg, context)

    def _generate_fallback(self, query: str, context: str) -> str:
        """Context-grounded fallback response when no external API key is configured."""
        lang = self.detect_language(query)
        # Extract best snippet from context
        snippets = [s for s in context.split("\n---") if len(s.strip()) > 20]
        primary_snippet = snippets[0].split("]: ", 1)[-1].strip() if snippets else ""

        if lang == "ar":
            return (
                f"أهلاً بك في مَنسم، دار العطور السعودية الفاخرة.\n\n"
                f"{primary_snippet}\n\n"
                f"يسعدنا دائماً استقبالكم في بوتيكاتنا الستة أو خدمتكم عبر وتساب المستشار الخاص."
            )
        return (
            f"Welcome to Mansam, the distinguished Saudi fine fragrance house.\n\n"
            f"{primary_snippet}\n\n"
            f"Every Mansam EDP (100ml) includes a complimentary 12ml travel fragrance. "
            f"How may I further assist your olfactory journey?"
        )

    def _extract_products(self, text: str) -> List[ProductCard]:
        """Identifies mentioned Mansam fragrances and returns structured cards with direct store URLs."""
        catalog = [
            ("Shatha Biladi", "Oud Collection", 1150.0, ["Sandalwood", "Citrus", "Musk", "Oud"], "Pride", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Shatha_Biladi/43"),
            ("Hams Min Al Sahraa", "Oud Collection", 1150.0, ["Royal Rose", "Musk", "Oud", "Fruits"], "Nobility", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Hams_Min_Al_Sahraa_/44"),
            ("Nasseem Al Ward", "Oud Collection", 1150.0, ["Rose", "Jasmine", "Oud", "Patchouli"], "Happiness", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Nasseem_Al_Ward/47"),
            ("Qublat Ward", "Oud Collection", 1150.0, ["Amber", "Bergamot", "Rose", "Oud"], "Passion", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Qublat_Ward/49"),
            ("Safaa Al Nada", "Oud Collection", 1150.0, ["Narcissus", "Jasmine", "Oud"], "Desire", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Safaa_Al_Nada/42"),
            ("Al Hawa Ghallab", "Oud Collection", 1150.0, ["Amber", "Oud", "Taif Rose"], "Nobility", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Al_Hawa_Ghallab/45"),
            ("Mamlakati", "Oud Collection", 1150.0, ["Royal Amber", "Aged Oud", "Spices"], "Nobility", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Mamlakati/46"),
            ("Al Shaghaf Al Ahmar", "Oud Collection", 1150.0, ["Red Rose", "Oud", "Saffron"], "Nobility", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Al_Shaghaf_Al_Ahmar/48"),
            ("Aala Taj Warda", "Nayat Collection", 850.0, ["Rum", "Coffee", "Vanilla", "Lily"], "Pleasure", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Aala_Taj_Warda/51"),
            ("Horr Fi Al Riyah", "Nayat Collection", 850.0, ["Almond", "Lily", "Amberwood", "Benzoin"], "Generosity", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Horr_fi_al_Riyah/50"),
            ("Tahta Al Noujoum", "Nayat Collection", 850.0, ["Neroli", "Orange Blossom", "Rum Musk"], "Happiness", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Tahta_Al_Noujoum/53"),
            ("Hadeeth Al Rooh", "Nayat Collection", 850.0, ["Pink Pepper", "Warm Spices", "Oriental Woods"], "Pleasure", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Hadeeth_Al_Rooh/52"),
            ("Fakhamat Al Warda", "Nayat Collection", 850.0, ["Crown Rose", "Patchouli", "Amber"], "Pleasure", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Fakhamat_Al_Warda/54"),
            ("Aala Sathi Al Qamar", "Nayat Collection", 850.0, ["White Florals", "Musk", "Vanilla"], "Pleasure", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Aala_Sathi_Al_Qamar/55"),
            ("Sarhan", "Qanun Collection", 850.0, ["Cardamom", "Smoked Wood", "Musk"], "Pride", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Sarhan/56"),
            ("Amtar", "Buzuq Collection", 850.0, ["Rain Accord", "Cedarwood", "Bergamot"], "Generosity", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Amtar/57"),
            ("Thawrat Al Ahasseess", "Riqq Collection", 850.0, ["Dark Amber", "Leather", "Plum"], "Passion", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Thawrat_Al_Ahasseess/58"),
            ("Khatiiiiiir", "Riqq Collection", 850.0, ["Smoky Leather", "Incense", "Musk"], "Passion", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Khatiiiiiir/59"),
            ("Min Ana", "Nayat Collection", 850.0, ["White Musk", "Jasmine", "Amber"], "Desire", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Min_Ana_/67"),
            ("Hamsa", "Nayat Collection", 850.0, ["Soft Florals", "Sandalwood", "Musk"], "Nobility", "https://ae.mansamworld.com/productDetails/Eau_de_Parfum_100ml/Hamsa/68"),
        ]
        cards = []
        normalized_text = text.lower().replace("_", " ")
        for name, collection, price, notes, mood, url in catalog:
            if name.lower() in normalized_text or name.lower().replace(" ", "") in normalized_text.replace(" ", ""):
                cards.append(
                    ProductCard(
                        name=name,
                        collection=collection,
                        price_sar=price,
                        size="100 ml EDP (+12ml Free)",
                        notes=notes,
                        mood=mood,
                        url=url,
                    )
                )
        return cards[:3]

    def _build_ticket_link(self) -> Tuple[str, str]:
        """Generates a VIP ticket ID and WhatsApp advisor dispatch link (used by /api/ticket endpoint)."""
        ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
        wa_number = settings.KSA_WHATSAPP.replace("+", "").replace(" ", "")
        wa_link = f"https://wa.me/{wa_number}?text=Mansam%20VIP%20Ticket%20{ticket_id}"
        return ticket_id, wa_link
