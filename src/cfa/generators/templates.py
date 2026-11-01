"""
templates.py — Synthetic text template pools.

Structure
---------
EN_REVIEW_TEMPLATES  : dict[theme_id][sentiment] -> list[str]   (15 themes × 3 × 5 = 225)
SUPPORT_TEMPLATES    : dict[sender_type][sentiment] -> list[str] (2 × 3 × 5 = 30)
MULTILINGUAL_TEMPLATES: dict[lang][sentiment] -> list[str]       (3 langs × 3 × 5 = 45)
SARCASTIC_TEMPLATES  : list[str]                                 (10)

Placeholders:  {product_name}  {category}  {weeks}  {months}
These are filled by transactions.py at generation time.
"""

EN_REVIEW_TEMPLATES: dict = {

    # ── THEME-000001: Product Quality ─────────────────────────────────────────
    "THEME-000001": {
        "positive": [
            "The {product_name} is built exceptionally well. Solid materials and a great finish throughout.",
            "Impressed by the quality of the {product_name}. It feels premium and very well-constructed.",
            "Outstanding durability. My {product_name} has held up perfectly after {months} months of daily use.",
            "The craftsmanship on this {product_name} is top-notch. Every detail feels carefully made.",
            "Five stars for quality. The {product_name} far exceeded my expectations for a {category} product.",
        ],
        "neutral": [
            "The {product_name} has decent quality. Not exceptional but gets the job done.",
            "Average build quality for a {category} product. The {product_name} is acceptable for the price.",
            "The {product_name} feels solid enough but nothing remarkable about the construction.",
            "Mixed feelings about the build. Some parts of the {product_name} feel premium, others less so.",
            "Adequate materials for the price. The {product_name} is exactly what you would expect at this level.",
        ],
        "negative": [
            "Very disappointed with the build quality of the {product_name}. It feels flimsy and cheap.",
            "The {product_name} broke after just {weeks} weeks. The quality is far below what was advertised.",
            "Poor materials on the {product_name}. The finish started peeling within days of purchase.",
            "Terrible construction. My {product_name} arrived with visible defects right out of the box.",
            "Do not buy if you want something that lasts. The {product_name} fell apart within {weeks} weeks.",
        ],
    },

    # ── THEME-000002: Customer Service ────────────────────────────────────────
    "THEME-000002": {
        "positive": [
            "The customer service team was incredibly helpful when I had an issue with my {product_name}.",
            "Support resolved my problem in minutes. Best customer service experience I have had.",
            "The agent I spoke with was patient and knowledgeable. Solved my {product_name} issue immediately.",
            "Five-star support. Quick response, friendly staff, and my issue was fixed on the first contact.",
            "I was skeptical but the customer service team went above and beyond to help me. Very impressed.",
        ],
        "neutral": [
            "Customer service was okay. My {product_name} issue was eventually resolved after a few follow-ups.",
            "Support was average. Took a while but they did get back to me with a solution.",
            "Mixed experience with customer service. The first agent was unhelpful but the second fixed my issue.",
            "Service was neither great nor terrible. Problem was resolved but it took longer than expected.",
            "Standard customer service. Nothing to complain about but nothing outstanding either.",
        ],
        "negative": [
            "Terrible customer service. Waited days for a response and my {product_name} issue was never resolved.",
            "The support team was rude and unhelpful. I am still waiting for a solution to my problem.",
            "Extremely frustrating experience with support. They kept asking me to repeat the same information.",
            "Customer service is a joke. Three different agents, three different answers, still no solution.",
            "I have been trying to get help with my {product_name} for two weeks with absolutely no resolution.",
        ],
    },

    # ── THEME-000003: Pricing & Value ─────────────────────────────────────────
    "THEME-000003": {
        "positive": [
            "Great value for money. The {product_name} delivers more than what I paid for.",
            "Competitive pricing compared to similar {category} products. Well worth the investment.",
            "I was hesitant about the price but the {product_name} is absolutely worth every dollar.",
            "Excellent bang for your buck. The {product_name} performs like a product that costs twice as much.",
            "Pricing is fair and the quality matches it. I feel good about my purchase of the {product_name}.",
        ],
        "neutral": [
            "The {product_name} is priced reasonably for what it offers. Not a bargain but fair.",
            "Pricing feels about right. The {product_name} is neither overpriced nor a great deal.",
            "Average value for the cost. You get what you pay for with the {product_name}.",
            "The price seems a bit high for a {category} product but the quality justifies it somewhat.",
            "Decent value. Cheaper alternatives exist but the {product_name} is probably worth the extra cost.",
        ],
        "negative": [
            "Overpriced for what you get. The {product_name} is not worth the asking price.",
            "I paid a premium for the {product_name} and feel completely ripped off. Not value for money.",
            "Way too expensive compared to competitors. I expected much more at this price.",
            "Poor value. The {product_name} underperforms relative to its price tag.",
            "They charge too much and deliver too little. Definitely not worth the premium for the {product_name}.",
        ],
    },

    # ── THEME-000004: Delivery & Shipping ─────────────────────────────────────
    "THEME-000004": {
        "positive": [
            "Fast and reliable shipping. My {product_name} arrived two days ahead of schedule.",
            "The delivery was seamless. Packaged well and arrived right on time.",
            "Impressed by the shipping speed. Got my {product_name} the next day in perfect condition.",
            "Tracking was accurate and delivery was early. Great shipping experience overall.",
            "Excellent logistics. The {product_name} was delivered on time and in perfect condition.",
        ],
        "neutral": [
            "Shipping was on time, nothing special. The {product_name} arrived as expected.",
            "Delivery was okay. Took about a week which is average for this type of order.",
            "Standard shipping experience. No issues but nothing impressive about the delivery either.",
            "Tracking updates were inconsistent but the {product_name} arrived on the estimated date.",
            "Adequate shipping. The product arrived in acceptable condition within the expected window.",
        ],
        "negative": [
            "My {product_name} arrived a week late with no communication about the delay. Very frustrating.",
            "The delivery was damaged and took forever to arrive. Terrible shipping experience.",
            "Shipping was incredibly slow. I could have driven there faster than this took.",
            "No tracking updates for five days and then the {product_name} showed up damaged.",
            "Package arrived crushed. It looks like no care was taken in shipping the {product_name}.",
        ],
    },

    # ── THEME-000005: Website & App UX ────────────────────────────────────────
    "THEME-000005": {
        "positive": [
            "The website is clean and easy to navigate. Found what I needed for my {product_name} quickly.",
            "The app is excellent. Intuitive interface and the {product_name} features are easy to access.",
            "Great user experience on the website. Smooth checkout and easy product comparison.",
            "The mobile app is fast and well-designed. Ordering my {product_name} was a breeze.",
            "Very user-friendly platform. I appreciate how easy it is to find support for the {product_name}.",
        ],
        "neutral": [
            "The website works fine but is a bit dated. Gets the job done for ordering the {product_name}.",
            "Average app experience. Some features are intuitive, others take time to figure out.",
            "The website is functional but not particularly well designed. Acceptable for basic use.",
            "The app does what it needs to do. Nothing exciting but no major complaints either.",
            "Mixed experience with the website. Some pages are great, others feel clunky.",
        ],
        "negative": [
            "The website is confusing and hard to navigate. I could not find the right support page.",
            "The app crashes constantly and is extremely frustrating to use.",
            "Terrible website experience. Checkout process is broken and I had to try three times.",
            "The mobile app is slow, buggy, and keeps logging me out. Needs a complete overhaul.",
            "I gave up trying to use the website and had to call support instead. The UX is that bad.",
        ],
    },

    # ── THEME-000006: Return & Refund Policy ─────────────────────────────────
    "THEME-000006": {
        "positive": [
            "The return process was incredibly easy. I had my refund within days of sending back the {product_name}.",
            "Hassle-free returns. They accepted my return without any questions and processed the refund quickly.",
            "The refund policy is fair and the process was smooth. Very happy with how my return was handled.",
            "Exceptional return experience. Quick, easy, and completely stress-free.",
            "Got a full refund without any trouble. The returns team was professional and efficient.",
        ],
        "neutral": [
            "The return process was okay. Took a couple of weeks but eventually got my refund.",
            "Average returns experience. Had to fill out several forms but it worked out in the end.",
            "The refund policy is reasonable. Not the most generous but they did honor my return.",
            "Return process was somewhat slow but they did come through with a full refund eventually.",
            "Standard returns experience. Nothing exceptional but it did get resolved.",
        ],
        "negative": [
            "Nightmare return process. I have been waiting six weeks for my refund with no resolution.",
            "They refused my return despite it being within the policy window. Absolutely unacceptable.",
            "The return process is intentionally complicated. I suspect they make it hard so people give up.",
            "Waited a month for a refund that never came. Had to file a dispute with my bank.",
            "Very unfair return policy. They charged a restocking fee that was never disclosed at purchase.",
        ],
    },

    # ── THEME-000007: Product Availability ────────────────────────────────────
    "THEME-000007": {
        "positive": [
            "The {product_name} was in stock and shipped immediately. Great availability.",
            "Pleasantly surprised to find the {product_name} available when other sites were out of stock.",
            "Stock levels are well managed. Never had trouble finding the {product_name} when I needed it.",
            "The inventory system works well. Got exactly what I ordered without any substitutions.",
            "Good product availability. My {product_name} variant was in stock and ready to ship.",
        ],
        "neutral": [
            "Product availability was okay. The {product_name} was on backorder for a week but arrived.",
            "Stock levels are inconsistent. Sometimes the {product_name} is available, sometimes not.",
            "Had to wait a few days for restocking but it was fine. Availability is hit or miss.",
            "The {product_name} was listed as available but took longer to ship than expected.",
            "Mixed experience with availability. Some variants were in stock, others were not.",
        ],
        "negative": [
            "The {product_name} has been out of stock for months. Very frustrated with the availability.",
            "Ordered the {product_name} only to be told it was out of stock after payment. Very misleading.",
            "Constantly showing as available but taking weeks to ship. The stock status is inaccurate.",
            "Terrible inventory management. I had to reorder three times before my {product_name} shipped.",
            "The most popular variant is always out of stock. They clearly cannot keep up with demand.",
        ],
    },

    # ── THEME-000008: Technical Support ───────────────────────────────────────
    "THEME-000008": {
        "positive": [
            "Technical support was outstanding. They walked me through the setup step by step.",
            "The tech support team was knowledgeable and resolved my {product_name} issue on the first call.",
            "Excellent technical assistance. The agent diagnosed the problem remotely and fixed it quickly.",
            "Best technical support I have experienced. Patient, skilled, and thorough.",
            "Tech support resolved a complex configuration issue in under twenty minutes. Very impressed.",
        ],
        "neutral": [
            "Technical support was acceptable. Eventually resolved my issue after a few back-and-forths.",
            "The support team has basic knowledge. They could not solve my advanced issue but did try.",
            "Tech support was okay. Had to wait a while but they did eventually walk me through the fix.",
            "Average technical assistance. Some agents are more helpful than others.",
            "My tech issue was resolved but it took several contacts and a lot of patience.",
        ],
        "negative": [
            "Technical support was useless. They just sent me a generic guide that did not help at all.",
            "Had to call technical support four times for the same issue. Still unresolved.",
            "The tech support team has no idea how their own product works. Very frustrating.",
            "Technical assistance was condescending and unhelpful. I felt I knew more than the agent.",
            "Completely incompetent technical support. My {product_name} is still broken after three calls.",
        ],
    },

    # ── THEME-000009: Account & Billing ───────────────────────────────────────
    "THEME-000009": {
        "positive": [
            "Billing is clear and accurate. My invoices for the {product_name} have always been correct.",
            "Account management is easy. Everything is transparent and my billing history is clear.",
            "Great billing experience. No hidden fees and my account dashboard is easy to understand.",
            "Quick resolution of a billing discrepancy. The team corrected the error within 24 hours.",
            "Excellent account management tools. Easy to update payment methods and track spending.",
        ],
        "neutral": [
            "Billing is generally accurate. Had one small discrepancy that was eventually corrected.",
            "Account management is okay. The dashboard could be more intuitive but it works.",
            "Billing is fine. The invoices are a bit confusing but the amounts are correct.",
            "Average experience with account management. Nothing exceptional but no major complaints.",
            "The billing system works but could use improvement. Too many steps to update payment info.",
        ],
        "negative": [
            "Was charged twice for my {product_name}. Getting a refund has been a nightmare.",
            "Mysterious charges on my account that nobody can explain. Very concerning.",
            "The billing system is broken. I have been trying to update my payment method for a week.",
            "Incorrect invoice three months in a row. Billing accuracy is clearly not a priority.",
            "My account was charged after I cancelled. It took three contacts to reverse the charge.",
        ],
    },

    # ── THEME-000010: Communication & Updates ─────────────────────────────────
    "THEME-000010": {
        "positive": [
            "Excellent communication throughout the process. I was kept informed at every step.",
            "Proactive updates about my order and delivery. Very professional communication.",
            "The team communicated clearly and promptly. No surprises with my {product_name} order.",
            "Loved the regular status updates. Felt well informed throughout the entire process.",
            "Great communication. Even when there was a delay, they notified me immediately.",
        ],
        "neutral": [
            "Communication was adequate. Got the necessary updates but nothing proactive.",
            "Average communication. Some emails were helpful, others were unnecessary.",
            "Updates were okay. I had to check the status myself a few times but eventually got notified.",
            "Communication could be improved. The updates came but often later than I would have liked.",
            "Standard communication experience. Not great, not bad. Just the basics.",
        ],
        "negative": [
            "Terrible communication. I had to contact support multiple times just to get a status update.",
            "Never received any notification about the delay. Found out by tracking the package myself.",
            "Zero proactive communication. I was left completely in the dark about my order status.",
            "No response to my emails for over a week. The lack of communication is unprofessional.",
            "They promised to follow up and never did. Complete failure in communication.",
        ],
    },

    # ── THEME-000011: Packaging ────────────────────────────────────────────────
    "THEME-000011": {
        "positive": [
            "The {product_name} came in beautifully designed packaging. Very premium unboxing experience.",
            "Packaging is sturdy and well-designed. The {product_name} arrived in perfect condition.",
            "Eco-friendly packaging that still protects the product perfectly. Love this approach.",
            "The packaging for the {product_name} is thoughtful and keeps the product safe during shipping.",
            "Great unboxing experience. The packaging quality reflects the quality of the {product_name} inside.",
        ],
        "neutral": [
            "Packaging is fine. Not fancy but it protected the {product_name} during shipping.",
            "Standard packaging. Nothing to complain about but nothing impressive either.",
            "The packaging is adequate for its purpose. A bit wasteful but the product arrived safely.",
            "Average packaging design. The {product_name} was well protected but the box was plain.",
            "Packaging is functional. Does the job without being impressive.",
        ],
        "negative": [
            "The packaging was completely inadequate. The {product_name} arrived damaged as a result.",
            "Way too much plastic packaging for such a small product. Very environmentally unfriendly.",
            "The box was crushed when it arrived. The packaging offers very little protection.",
            "Cheap packaging that does not reflect the premium price of the {product_name} at all.",
            "The product was rattling around in an oversized box with minimal protection. Terrible.",
        ],
    },

    # ── THEME-000012: Installation & Setup ────────────────────────────────────
    "THEME-000012": {
        "positive": [
            "The {product_name} was incredibly easy to set up. Had it running in under five minutes.",
            "Installation was a breeze. The instructions were clear and the {product_name} just worked.",
            "Very smooth setup process. Everything connected perfectly on the first try.",
            "The setup guide for the {product_name} is one of the best I have seen. Simple and clear.",
            "No technical expertise needed. My whole family was able to set up the {product_name} easily.",
        ],
        "neutral": [
            "Setup was manageable but could be simpler. Took about twenty minutes and a few restarts.",
            "Installation was okay. The instructions were average and I needed to look up a couple of steps.",
            "The {product_name} setup process is neither great nor terrible. Just follow the steps carefully.",
            "Average installation experience. The guide is functional but assumes some technical knowledge.",
            "Setup was fine in the end but the initial configuration was a bit confusing.",
        ],
        "negative": [
            "Installation is a nightmare. Spent three hours trying to set up the {product_name} with no success.",
            "The setup instructions are completely unclear. I had to watch multiple tutorials just to get started.",
            "The {product_name} would not connect during setup. Support was no help either.",
            "Terrible first-time experience. The setup process is overly complicated for no reason.",
            "Failed to install after following instructions exactly. The setup process is broken.",
        ],
    },

    # ── THEME-000013: Performance & Reliability ───────────────────────────────
    "THEME-000013": {
        "positive": [
            "The {product_name} performs flawlessly. Fast, reliable, and consistent every single time.",
            "Exceptional performance. My {product_name} handles everything I throw at it without issues.",
            "Rock-solid reliability. Never had a single problem after {months} months of heavy use.",
            "The performance of the {product_name} is outstanding. Consistently exceeds my expectations.",
            "Best in class performance for a {category} product. The {product_name} is incredibly reliable.",
        ],
        "neutral": [
            "Performance is acceptable. The {product_name} does what it needs to do without major issues.",
            "Average reliability. It works most of the time but occasionally needs a restart.",
            "The {product_name} performs adequately for everyday tasks but struggles with demanding uses.",
            "Performance is okay but not exceptional. I expected more from a product at this price.",
            "Decent reliability. Has had a few hiccups but nothing major in the first {months} months.",
        ],
        "negative": [
            "The {product_name} is unreliable and frequently crashes. Cannot depend on it at all.",
            "Performance has degraded significantly after a few months. Very disappointed.",
            "Constant issues with the {product_name}. It freezes at least twice a day.",
            "Terrible reliability. My {product_name} has failed completely after just {weeks} weeks.",
            "The performance does not come close to what was advertised. Extremely slow and unreliable.",
        ],
    },

    # ── THEME-000014: Feature Requests ────────────────────────────────────────
    "THEME-000014": {
        "positive": [
            "Love the existing features of the {product_name}. Would be perfect with a dark mode option.",
            "Great product. Adding voice control would make the {product_name} absolutely perfect.",
            "The {product_name} is excellent. I would love to see scheduled automation in a future update.",
            "Already satisfied with the {product_name} but multi-user support would make it exceptional.",
            "Happy customer. The only thing missing is better integration with other {category} devices.",
        ],
        "neutral": [
            "The {product_name} is okay but missing several features that competitors offer as standard.",
            "Would rate higher if the {product_name} had better customisation options.",
            "Decent product but the feature set feels dated. Needs more modern functionality.",
            "The {product_name} does the basics but lacks advanced features that would justify the price.",
            "Some useful features but also some glaring omissions compared to alternatives.",
        ],
        "negative": [
            "Missing too many basic features for a product at this price. Far behind competitors.",
            "Bought the {product_name} expecting a feature that does not actually exist despite being listed.",
            "The feature set is extremely limited and they have not added anything new in months.",
            "Cannot believe this basic feature is still missing. Very disappointing at this price.",
            "The {product_name} advertises features that do not actually work. Very misleading marketing.",
        ],
    },

    # ── THEME-000015: Onboarding Experience ───────────────────────────────────
    "THEME-000015": {
        "positive": [
            "The onboarding experience for the {product_name} was excellent. Guided through every step.",
            "Fantastic first-time experience. The welcome tutorial made everything clear immediately.",
            "The onboarding guides are detailed and easy to follow. Got started in minutes.",
            "Best onboarding I have seen for a {category} product. Thoughtful and thorough.",
            "The new user experience is outstanding. I felt confident using the {product_name} from day one.",
        ],
        "neutral": [
            "Onboarding was okay. Covered the basics but left out some important features.",
            "The first-time setup guide is adequate but not particularly thorough.",
            "Average onboarding experience. I had to refer to external guides for some features.",
            "The onboarding covers the essentials but could be more comprehensive.",
            "Decent getting-started experience but the depth could be improved significantly.",
        ],
        "negative": [
            "The onboarding experience was confusing and poorly organized. Very frustrating as a new user.",
            "No proper onboarding guide for the {product_name}. I was completely lost on day one.",
            "Terrible new user experience. Assumed knowledge that a first-time user would not have.",
            "The onboarding tutorial is outdated and does not match the current version of the product.",
            "Very poor first impression due to the confusing onboarding. Almost returned the {product_name}.",
        ],
    },
}

# ── Support message templates (by sender_type → sentiment) ───────────────────

SUPPORT_TEMPLATES: dict = {
    "customer": {
        "positive": [
            "Thank you so much for the help. The issue is now resolved and the {product_name} is working perfectly.",
            "Just wanted to follow up — the solution worked great. Really appreciate the quick response.",
            "I am very happy with how this was handled. The team went above and beyond to help me.",
            "Problem solved. Thank you to everyone involved. I am a very satisfied customer.",
            "The replacement arrived and everything is perfect now. Great service from start to finish.",
        ],
        "neutral": [
            "Hello, I am reaching out about an issue I am having with my recent order. Could you help?",
            "I have a question about my {product_name}. Can you clarify how to set up the advanced features?",
            "I need some information about the return policy for a product I purchased recently.",
            "Could you check on the status of my order? It has been a few days and I have not had an update.",
            "I would like to report a minor issue with my {product_name} and get some guidance on how to fix it.",
        ],
        "negative": [
            "Hi, I am having a serious problem with my {product_name}. It stopped working and I need urgent help.",
            "This is unacceptable. I have been waiting over a week and my issue still has not been resolved.",
            "I want to escalate this. Three agents have told me three different things and nothing is fixed.",
            "I need a refund immediately. This product is defective and I want this sorted today.",
            "Why is nobody helping me? I have sent four emails and made two calls with no solution.",
        ],
    },
    "agent": {
        "positive": [
            "Thank you for contacting us. I have reviewed your case and I am happy to resolve this right away.",
            "Great news! I have processed your request and everything should be sorted within 24 hours.",
            "I am delighted to let you know that your issue has been fully resolved. Please reach out if you need anything else.",
            "Your replacement {product_name} has been dispatched and you should receive it within 3 business days.",
            "I appreciate your patience. I have applied the fix and your account has been updated successfully.",
        ],
        "neutral": [
            "Thank you for getting in touch. I am looking into your case and will get back to you shortly.",
            "I understand your concern. Let me check the details and I will provide an update within 24 hours.",
            "I have raised this with our technical team and they will review your issue and respond.",
            "Your request has been logged and assigned a priority. Expect a response within 2 business days.",
            "I am gathering the information needed to resolve your case. Thank you for your patience.",
        ],
        "negative": [
            "I sincerely apologize for the inconvenience caused. We are working to resolve this as quickly as possible.",
            "I understand how frustrating this must be and I am sorry for the delay. We are prioritizing your case.",
            "My apologies for the poor experience you have had. This does not reflect our service standards.",
            "I am very sorry to hear about this issue. I want to assure you we will make this right.",
            "I apologize that we have not met your expectations. I am escalating this to ensure it is resolved today.",
        ],
    },
}

# ── Multilingual templates (generic, not theme-specific) ─────────────────────

MULTILINGUAL_TEMPLATES: dict = {
    "es": {
        "positive": [
            "El {product_name} es excelente. Muy satisfecho con mi compra y lo recomendaría ampliamente.",
            "Calidad excepcional y envío rápido. El {product_name} superó todas mis expectativas.",
            "Muy contento con el {product_name}. Funciona perfectamente y la calidad es muy buena.",
            "Servicio al cliente sobresaliente. Resolvieron mi problema en menos de una hora.",
            "Producto fantástico. El {product_name} tiene una construcción sólida y un rendimiento excelente.",
        ],
        "neutral": [
            "El {product_name} cumple con su función. No es espectacular pero tampoco decepciona.",
            "Producto aceptable para el precio. El {product_name} hace lo que promete.",
            "Experiencia regular. El {product_name} funciona bien pero tardaron un poco en enviarlo.",
            "Calidad estándar. Esperaba algo mejor dado el precio del {product_name}.",
            "El producto llegó en tiempo y forma. Nada extraordinario pero sin quejas.",
        ],
        "negative": [
            "Muy decepcionante. El {product_name} se rompió después de pocos días de uso.",
            "Pésimo servicio al cliente. Nadie supo ayudarme a resolver mi problema.",
            "El {product_name} no vale lo que cuesta. Calidad muy por debajo de lo esperado.",
            "Muy mal empaquetado. El producto llegó dañado y el proceso de devolución fue un caos.",
            "No lo recomendaría. El {product_name} dejó de funcionar en menos de un mes.",
        ],
    },
    "fr": {
        "positive": [
            "Le {product_name} est vraiment excellent. Je suis très satisfait de mon achat.",
            "Qualité exceptionnelle et livraison rapide. Je recommande vivement ce produit.",
            "Le service client est remarquable. Ils ont résolu mon problème en quelques minutes.",
            "Très bon rapport qualité-prix. Le {product_name} dépasse largement mes attentes.",
            "Produit fantastique. Construction solide et performances impressionnantes.",
        ],
        "neutral": [
            "Le {product_name} est correct pour le prix. Rien d'exceptionnel mais satisfaisant.",
            "Expérience moyenne. Le produit fonctionne bien mais la livraison a pris plus de temps que prévu.",
            "Qualité standard. Le {product_name} fait ce qu'il promet sans plus.",
            "Service client acceptable. Mon problème a été résolu après plusieurs contacts.",
            "Produit convenable. Quelques points à améliorer mais globalement satisfaisant.",
        ],
        "negative": [
            "Très déçu par la qualité du {product_name}. Il est tombé en panne après quelques semaines.",
            "Service client catastrophique. Personne n'a pu m'aider après plusieurs tentatives.",
            "Rapport qualité-prix déplorable. Le {product_name} ne vaut vraiment pas ce prix.",
            "Livraison très lente et produit arrivé endommagé. Expérience vraiment désagréable.",
            "Je déconseille fortement ce produit. Le {product_name} est tombé en panne bien trop vite.",
        ],
    },
    "de": {
        "positive": [
            "Der {product_name} ist hervorragend. Ich bin sehr zufrieden mit meinem Kauf.",
            "Ausgezeichnete Qualität und schnelle Lieferung. Sehr empfehlenswert.",
            "Der Kundenservice war erstklassig. Mein Problem wurde sofort gelöst.",
            "Sehr gutes Preis-Leistungs-Verhältnis. Der {product_name} übertrifft meine Erwartungen.",
            "Fantastisches Produkt. Solide Verarbeitung und beeindruckende Leistung.",
        ],
        "neutral": [
            "Der {product_name} ist in Ordnung für den Preis. Nichts Besonderes aber zufriedenstellend.",
            "Durchschnittliche Erfahrung. Das Produkt funktioniert gut aber die Lieferung hat etwas gedauert.",
            "Standardqualität. Der {product_name} macht was er verspricht.",
            "Akzeptabler Kundenservice. Mein Problem wurde nach mehreren Kontakten gelöst.",
            "Solides Produkt. Ein paar Verbesserungen wären wünschenswert.",
        ],
        "negative": [
            "Sehr enttäuschend. Der {product_name} ist nach wenigen Wochen kaputt gegangen.",
            "Schrecklicher Kundenservice. Niemand konnte mir helfen trotz mehrerer Versuche.",
            "Das Preis-Leistungs-Verhältnis ist absolut unzumutbar. Der {product_name} ist viel zu teuer.",
            "Sehr langsame Lieferung und das Produkt kam beschädigt an. Sehr ärgerlich.",
            "Kann dieses Produkt nicht empfehlen. Der {product_name} hat viel zu früh aufgehört zu funktionieren.",
        ],
    },
}

# ── Sarcastic / ambiguous templates (is_ambiguous=True in main data) ──────────

SARCASTIC_TEMPLATES: list = [
    "Oh wow, yet another product that works exactly as advertised. The {product_name} is absolutely fine I guess. Technically.",
    "Sure, the {product_name} arrived. Whether it actually works is a completely separate question.",
    "I love spending my evenings troubleshooting a brand new {product_name}. Truly the experience I was hoping for.",
    "The customer service was so helpful that I ended up solving the problem entirely by myself. Five stars for effort.",
    "The {product_name} is perfect — if by perfect you mean it works about half the time on a good day.",
    "Delivery was amazing. It only took three weeks, two wrong addresses, and one phone call. Highly efficient.",
    "Outstanding quality. Until it broke after a week, but who is counting at this price point anyway.",
    "The website was a joy to use. Found what I needed eventually, after about forty minutes of searching.",
    "The refund process is refreshingly simple, if you enjoy explaining yourself to five different agents.",
    "So glad they sent a follow-up email to inform me that absolutely nothing has changed with my open ticket.",
]
