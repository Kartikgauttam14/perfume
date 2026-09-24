// Mansam Luxury Fragrance AI Concierge — Client Controller with Voice & Text Capabilities

let currentLang = "en";
let conversationHistory = [];
let isAudioEnabled = true;
let isRecording = false;
let recognition = null;
let currentUtterance = null;

const translations = {
    en: {
        brandTagline: "Haute Parfumerie Saudienne • Founded in Riyadh",
        tabChat: "Concierge",
        tabGalaxy: "The Galaxy",
        tabAdvisor: "VIP Advisor",
        audioOn: "Voice On",
        audioOff: "Voice Off",
        langToggle: "العربية",
        chatHeading: "Personal Fragrance Consultation",
        chatSub: "Discover your signature scent guided by 9th-century Arabian olfactory wisdom and modern French craftsmanship.",
        welcomeMsg: "Welcome to <strong>Mansam</strong>. It is my pleasure to guide you through our collection of fine fragrances. How may I assist your olfactory journey today?",
        inputPlaceholder: "Type or click the microphone to speak...",
        galaxyTitle: "The Mansam Galaxy (7 Emotional Dimensions)",
        galaxyDesc: "In Kitab Kimiya' al-'Itr, Abu Yusuf Al-Kindi demonstrated that aromatic compounds elicit specific emotional responses. Select a mood below to explore its matching creations.",
        modalTitle: "Request VIP Advisor Callback",
        modalDesc: "Receive personalized consultation from our fragrance master within 48 hours or connect instantly via WhatsApp.",
        lblFullName: "Full Name",
        lblPhone: "Phone / WhatsApp",
        lblCity: "City / Boutique Preference",
        btnSubmitTicket: "Generate VIP Ticket",
        voiceListening: "Listening to your voice command... Speak now",
        voiceProcessing: "Processing voice input...",
        voiceUnsupported: "Voice recognition is not supported in this browser. Please use Chrome, Edge, or Safari.",
        suggestions: [
            "Tell me about Shatha Biladi",
            "What is the Galaxy system?",
            "Where are your KSA boutiques?",
            "What is the 12ml complimentary offer?"
        ]
    },
    ar: {
        brandTagline: "دار العطور السعودية الفاخرة • الرياض",
        tabChat: "المستشار العطري",
        tabGalaxy: "مجرة مَنسم",
        tabAdvisor: "مستشار خاص",
        audioOn: "صوت مفعل",
        audioOff: "صوت مكتوم",
        langToggle: "English",
        chatHeading: "استشارة عطرية خاصة",
        chatSub: "اكتشف عطرك المميز المستوحى من حكمة الكندي وفلسفة العطور العربية العريقة مع دقة الصياغة الفرنسية.",
        welcomeMsg: "أهلاً بك في <strong>مَنسم</strong>. يسعدني مرافقتكم في رحلتكم لاكتشاف أروع الإبداعات العطرية. كيف يمكنني خدمتكم اليوم؟",
        inputPlaceholder: "اكتب رسالتك أو اضغط على الميكروفون للتحدث...",
        galaxyTitle: "مجرة مَنسم (الأبعاد العاطفية السبعة)",
        galaxyDesc: "استندت مَنسم إلى كتاب 'كيمياء العطر والتصعيدات' للعالم الكندي لابتكار تصنيف عاطفي فريد يرشدكم إلى العطر المناسب لحالتكم الشعورية.",
        modalTitle: "طلب تواصل مع مستشار العطور",
        modalDesc: "احصل على استشارة مخصصة خلال 48 ساعة أو تواصل فوراً عبر تطبيق وتساب.",
        lblFullName: "الاسم الكريم",
        lblPhone: "رقم الجوال / وتساب",
        lblCity: "المدينة / البوتيك المفضل",
        btnSubmitTicket: "إصدار بطاقة كونسيرج",
        voiceListening: "جاري الاستماع لصوتك... تفضل بالتحدث الآن",
        voiceProcessing: "جاري معالجة الصوت...",
        voiceUnsupported: "التعرف على الصوت غير مدعوم في هذا المتصفح. يرجى استخدام Chrome أو Edge.",
        suggestions: [
            "حدثني عن عطر شذى بلادي",
            "ما هي فكرة مجرة منسم العاطفية؟",
            "أين تقع بوتيكات منسم في السعودية؟",
            "ما هو عرض الـ 12 مل المجاني؟"
        ]
    }
};

document.addEventListener("DOMContentLoaded", () => {
    const savedLang = localStorage.getItem("mansam_lang");
    const langModal = document.getElementById("langSelectModal");
    
    // Load audio preference
    const savedAudio = localStorage.getItem("mansam_audio");
    if (savedAudio !== null) {
        isAudioEnabled = savedAudio === "true";
    }
    updateAudioToggleUI();

    if (savedLang && (savedLang === "ar" || savedLang === "en")) {
        applyLanguage(savedLang, false);
        if (langModal) langModal.classList.remove("active");
    } else {
        if (langModal) langModal.classList.add("active");
    }
    
    initSpeechRecognition();
    loadGalaxy();
});

// ==========================================
// Language Selection & UI Management
// ==========================================

function selectLanguage(lang) {
    applyLanguage(lang, true);
    closeLangModal();
    
    // Focus input for instant conversation
    const input = document.getElementById("userInput");
    if (input) input.focus();
}

function openLangModal() {
    const langModal = document.getElementById("langSelectModal");
    if (langModal) langModal.classList.add("active");
}

function closeLangModal() {
    const langModal = document.getElementById("langSelectModal");
    if (langModal) langModal.classList.remove("active");
}

function applyLanguage(lang, clearChat = false) {
    currentLang = lang;
    localStorage.setItem("mansam_lang", currentLang);
    document.body.dir = currentLang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = currentLang;

    const t = translations[currentLang];
    document.getElementById("brandTagline").innerText = t.brandTagline;
    document.getElementById("tabChat").innerText = t.tabChat;
    document.getElementById("tabGalaxy").innerText = t.tabGalaxy;
    document.getElementById("tabAdvisor").innerText = t.tabAdvisor;
    document.getElementById("langToggle").innerText = t.langToggle;
    document.getElementById("chatHeading").innerText = t.chatHeading;
    document.getElementById("chatSub").innerText = t.chatSub;
    document.getElementById("userInput").placeholder = t.inputPlaceholder;
    document.getElementById("galaxyTitle").innerText = t.galaxyTitle;
    document.getElementById("galaxyDesc").innerText = t.galaxyDesc;
    document.getElementById("modalTitle").innerText = t.modalTitle;
    document.getElementById("modalDesc").innerText = t.modalDesc;
    document.getElementById("lblFullName").innerText = t.lblFullName;
    document.getElementById("lblPhone").innerText = t.lblPhone;
    document.getElementById("lblCity").innerText = t.lblCity;
    document.getElementById("btnSubmitTicket").innerText = t.btnSubmitTicket;

    updateAudioToggleUI();

    const suggContainer = document.getElementById("suggestionsContainer");
    if (suggContainer) {
        suggContainer.innerHTML = t.suggestions
            .map(s => `<button class="chip" onclick="sendQuickPrompt(this)">${s}</button>`)
            .join("");
    }

    if (clearChat) {
        conversationHistory = [];
        const chatMessages = document.getElementById("chatMessages");
        if (chatMessages) {
            chatMessages.innerHTML = `
                <div class="message bot-message">
                    <div class="msg-avatar">M</div>
                    <div class="msg-content">
                        <div class="msg-header-row">
                            <p id="welcomeMsg">${t.welcomeMsg}</p>
                            <button class="speak-btn" onclick="speakMessage(this)" title="Listen to audio">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                                </svg>
                            </button>
                        </div>
                        <span class="msg-meta">Mansam Advisor • Verified SSOT</span>
                    </div>
                </div>
            `;
        }
    } else {
        const welcomeEl = document.getElementById("welcomeMsg");
        if (welcomeEl) welcomeEl.innerHTML = t.welcomeMsg;
    }

    loadGalaxy();
}

function switchView(view) {
    document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));

    if (view === "chat") {
        document.getElementById("chatView").classList.add("active");
        document.getElementById("tabChat").classList.add("active");
    } else if (view === "galaxy") {
        document.getElementById("galaxyView").classList.add("active");
        document.getElementById("tabGalaxy").classList.add("active");
    }
}

function toggleLanguage() {
    const nextLang = currentLang === "en" ? "ar" : "en";
    applyLanguage(nextLang, true);
}

// ==========================================
// Voice Input (Speech-to-Text / Voice Command)
// ==========================================

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Web Speech API not supported on this browser.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
        isRecording = true;
        const voiceBtn = document.getElementById("voiceBtn");
        const voiceIndicator = document.getElementById("voiceIndicator");
        const statusText = document.getElementById("voiceStatusText");
        
        if (voiceBtn) voiceBtn.classList.add("recording");
        if (voiceIndicator) voiceIndicator.style.display = "flex";
        if (statusText) statusText.innerText = translations[currentLang].voiceListening;
    };

    recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
        }
        const input = document.getElementById("userInput");
        if (input) input.value = transcript;
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        stopVoiceRecording();
    };

    recognition.onend = () => {
        stopVoiceRecording();
        const input = document.getElementById("userInput");
        if (input && input.value.trim().length > 0) {
            // Auto-send the transcribed voice command
            sendMessage();
        }
    };
}

function toggleVoiceRecording() {
    if (!recognition) {
        initSpeechRecognition();
        if (!recognition) {
            alert(translations[currentLang].voiceUnsupported);
            return;
        }
    }

    if (isRecording) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
}

function startVoiceRecording() {
    if (!recognition) return;
    try {
        // Stop any ongoing speech playback before recording
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        recognition.lang = currentLang === "ar" ? "ar-SA" : "en-US";
        recognition.start();
    } catch (e) {
        console.warn("Recognition already started", e);
    }
}

function stopVoiceRecording() {
    isRecording = false;
    const voiceBtn = document.getElementById("voiceBtn");
    const voiceIndicator = document.getElementById("voiceIndicator");
    if (voiceBtn) voiceBtn.classList.remove("recording");
    if (voiceIndicator) voiceIndicator.style.display = "none";
    if (recognition) {
        try { recognition.stop(); } catch (e) {}
    }
}

// ==========================================
// Audio Output (Text-to-Speech / Speech Synthesis)
// ==========================================

function toggleAudio() {
    isAudioEnabled = !isAudioEnabled;
    localStorage.setItem("mansam_audio", isAudioEnabled);
    if (!isAudioEnabled && window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
    updateAudioToggleUI();
}

function updateAudioToggleUI() {
    const audioIcon = document.getElementById("audioIcon");
    const audioLabel = document.getElementById("audioLabel");
    const t = translations[currentLang];
    
    if (audioIcon && audioLabel) {
        if (isAudioEnabled) {
            audioIcon.innerText = "🔊";
            audioLabel.innerText = t.audioOn;
        } else {
            audioIcon.innerText = "🔇";
            audioLabel.innerText = t.audioOff;
        }
    }
}

function cleanTextForSpeech(text) {
    return text
        .replace(/<[^>]*>/g, "") // Remove HTML tags
        .replace(/\*\*([^*]+)\*\*/g, "$1") // Remove bold
        .replace(/\*([^*]+)\*/g, "$1") // Remove italics
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // Links to text
        .replace(/https?:\/\/\S+/g, "") // Remove raw URLs
        .replace(/[#_`~]/g, "") // Remove markdown symbols
        .trim();
}

let currentAudio = null;

function stopAudioPlayback() {
    if (currentAudio) {
        try {
            currentAudio.pause();
            currentAudio.currentTime = 0;
        } catch (e) {}
        currentAudio = null;
    }
    if (window.speechSynthesis) {
        try { window.speechSynthesis.cancel(); } catch (e) {}
    }
    document.querySelectorAll(".speak-btn.speaking").forEach(b => b.classList.remove("speaking"));
}

function speakText(rawText, buttonEl = null) {
    if (buttonEl && buttonEl.classList.contains("speaking")) {
        stopAudioPlayback();
        return;
    }

    stopAudioPlayback();

    const cleanText = cleanTextForSpeech(rawText);
    if (!cleanText) return;

    if (buttonEl) buttonEl.classList.add("speaking");

    // Primary: High-fidelity natural TTS endpoint (Works for Arabic & English flawlessly on all OS/devices)
    const ttsUrl = `/api/tts?text=${encodeURIComponent(cleanText)}&lang=${currentLang}`;
    currentAudio = new Audio(ttsUrl);

    currentAudio.onended = () => {
        if (buttonEl) buttonEl.classList.remove("speaking");
        currentAudio = null;
    };

    currentAudio.onerror = (err) => {
        console.warn("Server TTS audio error, trying browser SpeechSynthesis fallback:", err);
        fallbackBrowserSpeech(cleanText, buttonEl);
    };

    currentAudio.play().catch((err) => {
        console.warn("Audio play blocked or unavailable, trying SpeechSynthesis:", err);
        fallbackBrowserSpeech(cleanText, buttonEl);
    });
}

function fallbackBrowserSpeech(cleanText, buttonEl) {
    if (!window.speechSynthesis) {
        if (buttonEl) buttonEl.classList.remove("speaking");
        return;
    }

    try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = currentLang === "ar" ? "ar-SA" : "en-US";
        utterance.rate = 0.95;

        const voices = window.speechSynthesis.getVoices();
        const prefix = currentLang === "ar" ? "ar" : "en";
        const voice = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(prefix));
        if (voice) utterance.voice = voice;

        utterance.onend = () => {
            if (buttonEl) buttonEl.classList.remove("speaking");
        };
        utterance.onerror = () => {
            if (buttonEl) buttonEl.classList.remove("speaking");
        };

        window.speechSynthesis.speak(utterance);
    } catch (e) {
        if (buttonEl) buttonEl.classList.remove("speaking");
    }
}

function speakMessage(btn) {
    const msgContent = btn.closest(".msg-content");
    if (!msgContent) return;
    const textElement = msgContent.querySelector("p");
    if (textElement) {
        speakText(textElement.innerText, btn);
    }
}

// ==========================================
// Chat Messaging Flow
// ==========================================

async function sendMessage() {
    const input = document.getElementById("userInput");
    const text = input.value.trim();
    if (!text) return;

    appendMessage("user", text);
    input.value = "";
    conversationHistory.push({ role: "user", content: text });

    const loadingId = appendLoading();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                history: conversationHistory,
                language: currentLang
            })
        });

        const data = await response.json();
        removeLoading(loadingId);

        appendMessage("bot", data.reply, data.products, data.suggested_product_url);
        conversationHistory.push({ role: "assistant", content: data.reply });

        // Auto-play audio response if audio is enabled
        if (isAudioEnabled) {
            speakText(data.reply);
        }

    } catch (err) {
        removeLoading(loadingId);
        const errMsg = currentLang === "ar" ? "نعتذر، حدث خطأ أثناء المعالجة." : "Pardon, a connection error occurred.";
        appendMessage("bot", errMsg);
    }
}

function handleKeyPress(e) {
    if (e.key === "Enter") sendMessage();
}

function sendQuickPrompt(btn) {
    document.getElementById("userInput").value = btn.innerText;
    sendMessage();
}

function appendMessage(role, text, products = [], suggestedUrl = null) {
    const container = document.getElementById("chatMessages");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role === "user" ? "user-message" : "bot-message"}`;

    let html = `
        <div class="msg-avatar">${role === "user" ? "U" : "M"}</div>
        <div class="msg-content">
            <div class="msg-header-row">
                <p>${text.replace(/\n/g, "<br>")}</p>
                ${role === "bot" ? `
                    <button class="speak-btn" onclick="speakMessage(this)" title="Listen to audio">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                            <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                        </svg>
                    </button>
                ` : ""}
            </div>
    `;

    if (products && products.length > 0) {
        html += `<div class="product-showcase">`;
        products.forEach(p => {
            const shopLabel = currentLang === "ar" ? "تسوق الآن" : "Shop Now";
            html += `
                <div class="product-card">
                    <div class="prod-name">${p.name}</div>
                    <div class="prod-collection">${p.collection} • ${p.mood || ''}</div>
                    <div class="prod-price">${p.price_sar} SAR</div>
                    <div class="prod-notes">${p.notes.join(", ")}</div>
                    ${p.url ? `<a href="${p.url}" target="_blank" class="prod-shop-btn">${shopLabel}</a>` : ""}
                </div>
            `;
        });
        html += `</div>`;
    }

    if (suggestedUrl && (!products || products.length === 0)) {
        const label = currentLang === "ar" ? "اكتشف المنتج المقترح" : "View Suggested Product";
        html += `
            <a href="${suggestedUrl}" target="_blank" class="prod-cta-btn" style="margin-top:0.75rem;">
                ${label}
            </a>
        `;
    }

    html += `
            <span class="msg-meta">${role === "user" ? "Client" : "Mansam Advisor • Verified SSOT"}</span>
        </div>
    `;

    msgDiv.innerHTML = html;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function appendLoading() {
    const id = "loading-" + Date.now();
    const container = document.getElementById("chatMessages");
    const div = document.createElement("div");
    div.id = id;
    div.className = "message bot-message";
    div.innerHTML = `
        <div class="msg-avatar">M</div>
        <div class="msg-content">
            <p style="color:var(--text-muted); font-style:italic;">${currentLang === "ar" ? "جاري البحث في الأرشيف العطري..." : "Consulting olfactory archives..."}</p>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ==========================================
// Galaxy & VIP Ticket
// ==========================================

async function loadGalaxy() {
    try {
        const res = await fetch("/api/galaxy");
        const data = await res.json();
        const grid = document.getElementById("galaxyGrid");
        grid.innerHTML = data.map(cat => `
            <div class="galaxy-card" onclick="queryGalaxyMood('${cat.name_en}')">
                <h3 class="mood-title">${currentLang === 'ar' ? cat.name_ar : cat.name_en}</h3>
                <p class="mood-profile">${cat.olfactive_profile}</p>
                <div class="mood-perfumes">
                    ${cat.fragrances.map(f => `<span class="perfume-tag">${f}</span>`).join("")}
                </div>
            </div>
        `).join("");
    } catch (e) {
        console.error("Galaxy load failed", e);
    }
}

function queryGalaxyMood(moodName) {
    switchView("chat");
    const prompt = currentLang === "ar" 
        ? `حدثني عن عطور بُعد '${moodName}' في مجرة منسم`
        : `Tell me about the fragrances in the '${moodName}' dimension of the Galaxy.`;
    document.getElementById("userInput").value = prompt;
    sendMessage();
}

function openTicketModal() {
    document.getElementById("ticketModal").classList.add("active");
}

function closeTicketModal() {
    document.getElementById("ticketModal").classList.remove("active");
}

async function submitTicket(e) {
    e.preventDefault();
    const name = document.getElementById("custName").value;
    const phone = document.getElementById("custPhone").value;
    const city = document.getElementById("custCity").value;

    const res = await fetch("/api/ticket", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_name: name, phone: phone, city: city })
    });

    const data = await res.json();
    document.getElementById("ticketForm").style.display = "none";
    document.getElementById("ticketResult").style.display = "block";
    document.getElementById("resultTicketId").innerText = data.ticket_id;
    document.getElementById("resultWaLink").href = data.whatsapp_link;
}
