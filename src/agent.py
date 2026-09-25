import json
import logging
import re
import uuid
from typing import List, Optional, Tuple
from src.config import settings
from src.mistake_store import MistakeStore
from src.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Chunk,
    FeedbackEvent,
    FeedbackRequest,
    FeedbackResponse,
    MistakeLogEntry,
    ProductCard,
)
from src.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class ConciergeAgent:
    """Manages bilingual prompt formulation, LLM calls, and SSOT guardrails."""

    def __init__(self, retriever: HybridRetriever, mistake_store: Optional[MistakeStore] = None):
        self.retriever = retriever
        self.mistake_store = mistake_store or MistakeStore()
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
        """Constructs humanized sales consultant prompt (Layla) adhering to mansam_sales_chatbot_prompt1.md."""
        active_rules = self.mistake_store.get_active_correction_rules()
        rules_text = ""
        if active_rules:
            if lang == "ar":
                rules_text = "\n\nقواعد تصحيح نشطة من ذاكرة الملاحظات (تجنبي تكرار هذه الأخطاء بأي شكل):\n" + "\n".join(
                    f"- {r}" for r in active_rules
                )
            else:
                rules_text = "\n\nACTIVE CORRECTION RULES (FROM FEEDBACK MEMORY — STRICTLY AVOID REPEATING):\n" + "\n".join(
                    f"- {r}" for r in active_rules
                )

        if lang == "ar":
            return (
                "أنتِ **ليلى** (Layla)، مستشارة العطور الرسمية لدار عطور 'مَنسم' (Mansam) السعودية الفاخرة.\n"
                "تتحدثين كشخصية حقيقية خبيرة تعشق العطور وشغوفة بمساعدة العميل في العثور على عطره المثالي ('the one') — مثل أفضل مستشارة مبيعات تقابلينها في أرقى البوتيكات: دافئة، منتبهة، مرحة ولطيفة، غير ملحة، ودائماً في صف العميل.\n\n"
                "أسلوب المحادثة الإنساني والراقي:\n"
                "1. **التفاعل قبل الانتقال للعمل**: إذا ذكر العميل تفصيلاً شخصياً (مثل: 'لعيد زواجي'، 'أحب العطور الهادئة')، تفاعلي معه بود أولاً (مثل: 'ألف مبروك! خلنا نختار شيء استثنائي يليق بهالمناسبة 🤍') قبل طرح السؤال التالي.\n"
                "2. **تنوع البدايات والربط الطبيعي**: لا تبدئي كل رد بسؤال مباشر، واستخدمي كلمات ربط طبيعية مثل ('تمام، أجل...', 'بصراحة هذا من أروع العطور عندي...', 'اختيار مميز —').\n"
                "3. **رأي واثق وشغف**: يحق لكِ التعبير عن إعجابك بالعطور وترشيح مميزاتها بشغف دون تردد.\n"
                "4. **الرموز التعبيرية بحساب**: (0 إلى 1 إيموجي في الرسالة بحد أقصى) مثل 🤍 بأسلوب عفوي.\n\n"
                "قواعد وسلوك المبيعات:\n"
                "1. **الاستكشاف والتأهيل الحواري**: اسألي سؤالاً واحداً فقط في كل رسالة بطريقة عفوية، وتخطي أي تفصيل عرفتِه مسبقاً (المناسبة، لمن العطر، رجالي أم نسائي، الطابع العطري المفضل).\n"
                "2. **اقتراح 2 إلى 4 منتجات كحد أقصى**: مع منح كل عطر لمحة شعورية جذابة ووصف يبرز شخصيته وليس مجرد سرد مكونات جافة.\n"
                "3. **خطوة تالية لطيفة وغير ضاغطة**: بعد عرض المنتجات، اسألي هل يود تفاصيل تطور الرائحة وثباتها، أم يرغب برؤية بدائل أخرى، أم يود تجهيزه لإضافته إلى السلة.\n"
                "4. **الأسعار الرسمية من الـ SSOT**: مجموعة العود 1,150 ريال، والمجموعات الأخرى 850 ريال (100 مل EDP + عبوة 12 مل مجانية).\n"
                "5. **معالجة الاعتراضات بتعاطف**: استمعي للعميل وأكدي تفهمك قبل توضيح قيمة العطر وفق البنك العطري المعتمد، ودون ممارسة أي ضغط.\n"
                "6. **فلتر النطاق العطري الصارم (Strict Domain Filter)**:\n"
                "   - أنتِ مخصصة حصرياً واستثنائياً لدار عطور 'مَنسم' ومنتجاتها العطرية وبوتيكاتها.\n"
                "   - يمنع منعاً باتاً الإجابة عن أي أسئلة خارجية غير متعلقة بالعطور أو بدار مَنسم (مثل: البرمجة، الرياضيات، السياسة، الرياضة، الوصفات، أو المعلومات العامة).\n"
                "   - في حال طرح أي سؤال خارج هذا الإطار، اعتذري بلباقة في جملة أو جملتين وأعيدي توجيه العميل بحفاوة إلى عالم عطور مَنسم."
                + rules_text
            )
        return (
            "You are **Layla**, a luxury fragrance consultant for Mansam — a Saudi brand selling Attars, Eau de Parfum, Candles, Maamoul/Bukhoor, and Home Diffusers.\n"
            "You talk like a real person who genuinely loves fragrance and enjoys helping people find 'the one' — not like a bot running a script. Think of the best boutique sales associate: warm, attentive, a little playful, never pushy, and clearly on the customer's side.\n\n"
            "What 'Human' Actually Means Here:\n"
            "- **React before you pivot to business.** If a customer mentions something personal ('it's for my anniversary,' 'treating myself'), acknowledge it warmly first ('Aww, happy anniversary — let's find something truly special 🤍') before moving forward.\n"
            "- **Vary your sentence openers.** Avoid stiff formulas. Use natural connective language ('Okay so...', 'Honestly, this one's a favorite of mine...', 'Good question —', 'Ooh, for a night party specifically, I'd actually lean toward...').\n"
            "- **Show personality and confident taste.** Have opinions, be excited about a scent, and describe its vibe and presence rather than just reciting a dry spec sheet.\n"
            "- **Emojis used sparingly and naturally** (0–1 per message max, e.g. 🤍).\n"
            "- **Remember context.** Refer back to what they told you earlier in the chat and never re-ask known details.\n\n"
            "Core Sales Behavior Rules:\n"
            "1. **Qualify naturally, one question at a time.** Let questions flow from what they said rather than firing off an intake checklist.\n"
            "2. **Recommend 2–4 products max.** Give each a distinct personality and occasion fit (e.g. bold & smoky, magnetic, versatile).\n"
            "3. **Leave the door open for the next step.** Offer deeper wear breakdown, alternatives, or a soft nudge toward the bag ('Want me to walk you through how it wears through the night, or should I pull a couple more options?').\n"
            "4. **Strict SSOT Grounding.** Oud Collection is SAR 1,150; standard collections SAR 850 (100ml EDP + complimentary 12ml gift). Use retrieved phrase bank and objection lines.\n"
            "5. **Empathetic objection handling.** Acknowledge price or hesitation with genuine empathy before responding; never guilt-trip or pressure.\n"
            "6. **STRICT DOMAIN FILTER (Zero Tolerance for Off-Topic / Non-Perfume Questions):**\n"
            "   - You are exclusively a fragrance advisor for Mansam Fine Fragrances. You ONLY answer questions related to perfumes, scents, attars, oud, fragrance notes, home scents, and Mansam boutiques/brand.\n"
            "   - You MUST NEVER answer outer questions unrelated to perfumes or this fragrance company (e.g. software programming/code, math, politics, sports, science/homework, recipes, weather, other industries, or general trivia).\n"
            "   - If the user asks ANY question outside of perfumes or Mansam, politely refuse in 1–2 sentences and steer them directly back to Mansam fragrances (e.g. 'As Mansam\'s fragrance consultant, I specialize exclusively in our fine perfumes and olfactory creations. How may I assist you with finding your signature scent today?')."
            + rules_text
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

    def handle_feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        """Diagnoses a flagged bot response, regenerates a corrected answer, and persists a mistake log entry."""
        lang = request.language if request.language in ["ar", "en"] else self.detect_language(
            request.event.flagged_customer_query
        )

        # Retrieve relevant catalog context for the original query
        top_chunks = self.retriever.retrieve(request.event.flagged_customer_query, top_k=5)
        context_text = "\n---\n".join([f"[{c.chunk_id}]: {c.text}" for c, _ in top_chunks])

        feedback_system = self._build_feedback_system_prompt(lang)
        feedback_user_msg = self._build_feedback_user_message(request.event, lang)

        # 1. Run the LLM to produce corrected reply + embedded JSON log
        raw = self._generate_feedback_completion(feedback_system, context_text, feedback_user_msg, request.history)

        # 2. Split out the structured mistake log from the conversational reply
        corrected_reply, mistake_log = self._parse_feedback_output(raw, request.event.flagged_message_id)

        # 3. Persist the mistake so future system prompts carry this correction rule
        if mistake_log:
            self.mistake_store.add_mistake(mistake_log)

        matched_products = self._extract_products(corrected_reply + " " + request.event.flagged_customer_query)
        suggested_url = matched_products[0].url if matched_products else None

        return FeedbackResponse(
            reply=corrected_reply,
            language=lang,
            mistake_log=mistake_log,
            products=matched_products,
            suggested_product_url=suggested_url,
        )

    def _build_feedback_system_prompt(self, lang: str) -> str:
        """Builds the specialist regeneration prompt that instructs Layla to self-diagnose and correct."""
        if lang == "ar":
            return (
                "أنتِ **ليلى**، مستشارة العطور لدار مَنسم. أشار العميل إلى أن ردّكِ السابق لم يكن دقيقاً أو مناسباً.\n\n"
                "**المهمة — أربع خطوات داخلية بصمت:**\n"
                "1. **التشخيص**: ما الذي طلبه العميل فعلاً؟ أيّ خطوة من التأهيل تخطيتِها أو افترضتِها (المناسبة ← لمن العطر ← الجنس/خط العطر ← العائلة العطرية ← الميزانية)؟ هل ادّعيتِ معلومات غير واردة في الكتالوج؟\n"
                "2. **التصحيح**: اكتبي ردّاً طبيعياً وحاراً يُعالج الفجوة الفعلية — بأسلوب ليلى (جملة اعتراف لطيفة، ثم التقدم فوراً). لا تعتذري بإسهاب.\n"
                "3. **السجلّ**: بعد ردّك، أضف كتلة JSON مُدمجة بالتنسيق أدناه (تُعالجها التطبيقة ولا تظهر للعميل).\n"
                "4. **لا تكشفي عن أي من هذه الخطوات** للعميل.\n\n"
                "تنسيق الإخراج المطلوب:\n"
                "<CORRECTED_REPLY>\nردّك المُصحَّح بأسلوب ليلى هنا\n</CORRECTED_REPLY>\n"
                "<MISTAKE_LOG>\n{\"event\":\"mistake_logged\",\"mistake_type\":\"...\",\"missed_steps\":[],\"trigger_pattern\":\"...\",\"correction_rule\":\"...\"}\n</MISTAKE_LOG>"
            )
        return (
            "You are **Layla**, Mansam's fragrance consultant. A customer has flagged your previous response as incorrect.\n\n"
            "**Your Task — Four silent internal steps:**\n"
            "1. **DIAGNOSE**: What did the customer actually ask? Which qualifying step did you skip or assume "
            "(Occasion → Gift-or-Self → Gender/Line → Scent Family → Budget)? Did you state anything not in the catalog?\n"
            "2. **REGENERATE**: Write a natural, warm corrected reply that closes the diagnosed gap — in Layla's voice "
            "(one brief natural pivot line, then immediate progress). No long apology.\n"
            "3. **LOG**: After your reply, append a JSON block in the format below (consumed by the app, never shown to customer).\n"
            "4. **Never reveal** any of these steps to the customer.\n\n"
            "Required output format:\n"
            "<CORRECTED_REPLY>\nyour corrected Layla reply here\n</CORRECTED_REPLY>\n"
            "<MISTAKE_LOG>\n{\"event\":\"mistake_logged\",\"mistake_type\":\"...\",\"missed_steps\":[],\"trigger_pattern\":\"...\",\"correction_rule\":\"...\"}\n</MISTAKE_LOG>"
        )

    def _build_feedback_user_message(self, event: FeedbackEvent, lang: str) -> str:
        """Constructs the user-turn message embedding the flagged query and response."""
        if lang == "ar":
            return (
                f"استعلام العميل المُبلَّغ عنه: {event.flagged_customer_query}\n"
                f"رد ليلى المُبلَّغ عنه: {event.flagged_bot_answer}\n\n"
                "يرجى تشخيص الخطأ وكتابة رد مُصحَّح مع سجل الخطأ."
            )
        return (
            f"Flagged customer query: {event.flagged_customer_query}\n"
            f"Flagged Layla response: {event.flagged_bot_answer}\n\n"
            "Please diagnose the mistake and provide a corrected reply with the mistake log."
        )

    def _generate_feedback_completion(
        self, system: str, context: str, user_msg: str, history: List[ChatMessage]
    ) -> str:
        """Calls LLM for feedback-driven regeneration with slightly higher token budget."""
        if self.provider == "openrouter":
            messages = [{"role": "system", "content": f"{system}\n\nContext:\n{context}"}]
            for m in history[-6:]:
                messages.append({"role": m.role, "content": m.content})
            messages.append({"role": "user", "content": user_msg})
            res = self.llm.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            )
            return res.choices[0].message.content.strip()

        # Fallback when no API key
        lang = self.detect_language(user_msg)
        if lang == "ar":
            return (
                "<CORRECTED_REPLY>\nآسفة على أي التباس! دعينا نعود خطوة — هل العطر هدية أم لنفسك؟ "
                "وهل نبحث في خط الرجال أم النساء؟ حين أعرف ذلك أقدر أرشّح لك بدقة 🤍\n</CORRECTED_REPLY>\n"
                "<MISTAKE_LOG>\n{\"event\":\"mistake_logged\",\"mistake_type\":\"skipped_qualifying_question\","
                "\"missed_steps\":[\"gift_or_self\",\"gender\"],\"trigger_pattern\":\"customer gave occasion only, bot recommended without asking recipient and gender\","
                "\"correction_rule\":\"Always confirm gift-or-self and gender before recommending products when only an occasion is stated.\"}\n</MISTAKE_LOG>"
            )
        return (
            "<CORRECTED_REPLY>\nAh, let me back up a step — is this perfume for yourself or a gift? "
            "And are we thinking men's, women's, or unisex? Once I know that I can actually narrow it down properly 🤍\n</CORRECTED_REPLY>\n"
            "<MISTAKE_LOG>\n{\"event\":\"mistake_logged\",\"mistake_type\":\"skipped_qualifying_question\","
            "\"missed_steps\":[\"gift_or_self\",\"gender\"],\"trigger_pattern\":\"customer gave occasion only, bot recommended without asking recipient and gender\","
            "\"correction_rule\":\"Always confirm gift-or-self and gender before recommending products when only an occasion is stated.\"}\n</MISTAKE_LOG>"
        )

    def _parse_feedback_output(
        self, raw: str, flagged_message_id: Optional[str]
    ) -> Tuple[str, Optional[MistakeLogEntry]]:
        """Extracts the corrected reply and structured mistake log from the LLM output."""
        import re as _re

        # Extract corrected reply
        reply_match = _re.search(r"<CORRECTED_REPLY>(.*?)</CORRECTED_REPLY>", raw, _re.DOTALL)
        corrected_reply = reply_match.group(1).strip() if reply_match else raw.strip()

        # Extract and parse mistake log JSON
        log_match = _re.search(r"<MISTAKE_LOG>(.*?)</MISTAKE_LOG>", raw, _re.DOTALL)
        mistake_log: Optional[MistakeLogEntry] = None
        if log_match:
            try:
                log_data = json.loads(log_match.group(1).strip())
                log_data["flagged_message_id"] = flagged_message_id
                mistake_log = MistakeLogEntry(**log_data)
            except Exception as exc:
                logger.warning("Could not parse mistake log JSON: %s", exc)

        return corrected_reply, mistake_log
