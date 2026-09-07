"""
services/language_service.py — Configurable Multi-Language Service for Nyaya Mitra.
==================================================================================
Supports multiple Indian languages (Hindi, Kannada, Telugu, Tamil, Marathi, Bengali, English).
Preserves the authoritative English legal record while providing derived accessibility displays.
Enforces the core rule: Machine translation is never treated as a source of legal truth.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nyaya_mitra.language_service")

# ── Supported Languages Configuration ─────────────────────────────────────────

SUPPORTED_LANGUAGES: List[Dict[str, Any]] = [
    {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "is_authoritative": True,
        "legal_authority_note": "Primary Authoritative Legal Record",
    },
    {
        "code": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "is_authoritative": False,
        "legal_authority_note": "Derived Display for Accessibility Only",
    },
    {
        "code": "kn",
        "name": "Kannada",
        "native_name": "ಕನ್ನಡ",
        "is_authoritative": False,
        "legal_authority_note": "Derived Display for Accessibility Only",
    },
    {
        "code": "te",
        "name": "Telugu",
        "native_name": "తెలుగు",
        "is_authoritative": False,
        "legal_authority_note": "Derived Display for Accessibility Only",
    },
    {
        "code": "ta",
        "name": "Tamil",
        "native_name": "தமிழ்",
        "is_authoritative": False,
        "legal_authority_note": "Derived Display for Accessibility Only",
    },
    {
        "code": "mr",
        "name": "Marathi",
        "native_name": "मराठी",
        "is_authoritative": False,
        "legal_authority_note": "Derived Display for Accessibility Only",
    },
    {
        "code": "bn",
        "name": "Bengali",
        "native_name": "বাংলা",
        "is_authoritative": False,
        "legal_authority_note": "Derived Display for Accessibility Only",
    },
]

SUPPORTED_CODES = {l["code"] for l in SUPPORTED_LANGUAGES}

# ── Canonical Statutory Legal Glossaries ──────────────────────────────────────

STATUS_TRANSLATIONS: Dict[str, Dict[str, Dict[str, str]]] = {
    "UNDER_REVIEW": {
        "title": {
            "en": "Case Registered & Under Initial Review",
            "hi": "मामला पंजीकृत और कानूनी सहायता समीक्षाधीन",
            "kn": "ಪ್ರಕರಣ ದಾಖಲಾಗಿದೆ ಮತ್ತು ಆರಂಭಿಕ ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ",
            "te": "కేసు నమోదు చేయబడింది మరియు ప్రాథమిక సమీక్షలో ఉంది",
            "ta": "வழக்கு பதிவு செய்யப்பட்டு ஆரம்ப பரிசீலனையில் உள்ளது",
            "mr": "खटला नोंदवला गेला असून प्राथमिक पुनरावलोकनाधीन आहे",
            "bn": "মামলা নথিভুক্ত এবং প্রাথমিক পর্যালোচনার অধীন",
        },
        "detail": {
            "en": "The legal aid system has registered case details and verified detention records.",
            "hi": "कानूनी सहायता प्रणाली ने मामले का विवरण दर्ज किया है और हिरासत रिकॉर्ड सत्यापित किए हैं।",
            "kn": "ಕಾನೂನು ನೆರವು ವ್ಯವಸ್ಥೆಯು ಪ್ರಕರಣದ ವಿವರಗಳನ್ನು ದಾಖಲಿಸಿದೆ ಮತ್ತು ಬಂಧನ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿದೆ.",
            "te": "న్యాయ సహాయ వ్యవస్థ కేసు వివరాలను నమోదు చేసి నిర్బంధ రికార్డులను ధృవీకరించింది.",
            "ta": "சட்ட உதவி அமைப்பு வழக்கு விவரங்களை பதிவு செய்து தடுப்புக் காவல் பதிவுகளை சரிபார்த்துள்ளது.",
            "mr": "विधी सेवा यंत्रणेने खटल्याचा तपशील नोंदवला असून कोठडी नोंदी पडताळल्या आहेत.",
            "bn": "আইনি সহায়তা ব্যবস্থা মামলার বিবরণ নথিভুক্ত করেছে এবং আটক রেকর্ড যাচাই করেছে।",
        },
    },
    "ELIGIBLE_FOR_REVIEW": {
        "title": {
            "en": "Statutory Bail Eligibility Identified (Sec 479 BNSS)",
            "hi": "धारा 479 बीएनएसएस के तहत वैधानिक पात्रता चिह्नित",
            "kn": "ಕಲಂ 479 BNSS ಅಡಿಯಲ್ಲಿ ಶಾಸನಬದ್ಧ ಜಾಮೀನು ಅರ್ಹತೆ ಗುರುತಿಸಲಾಗಿದೆ",
            "te": "సెక్షన్ 479 BNSS కింద చట్టబద్ధమైన బెయిల్ అర్హత గుర్తించబడింది",
            "ta": "பிரிவு 479 BNSS கீழ் சட்டப்பூர்வ பிணை தகுதி அடையாளம் காணப்பட்டுள்ளது",
            "mr": "कलम 479 BNSS अंतर्गत वैधानिक जामीन पात्रता निश्चित",
            "bn": "ধারা ৪৭৯ BNSS এর অধীনে বিধিবদ্ধ জামিনের যোগ্যতা চিহ্নিত",
        },
        "detail": {
            "en": "Case meets statutory detention threshold under Section 479 BNSS, 2023. Legal aid counsel assignment in progress.",
            "hi": "धारा 479 BNSS के तहत वैधानिक जमानत समीक्षा के लिए पात्र चिह्नित। अधिवक्ता आवंटन प्रक्रियाधीन है।",
            "kn": "ಪ್ರಕರಣವು ಕಲಂ 479 BNSS ಅಡಿಯಲ್ಲಿ ಶಾಸನಬದ್ಧ ಅವಧಿಯನ್ನು ತಲುಪಿದೆ. ವಕೀಲರ ನಿಯೋಜನೆ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ.",
            "te": "కేసు సెక్షన్ 479 BNSS కింద చట్టబద్ధమైన వ్యవధిని పూర్తి చేసింది. న్యాయవాది కేటాయింపు పురోగతిలో ఉంది.",
            "ta": "வழக்கு பிரிவு 479 BNSS கீழ் சட்டப்பூர்வ கால அளவை எட்டியுள்ளது. வழக்கறிஞர் நியமனம் பரிசீலனையில் உள்ளது.",
            "mr": "खटला कलम 479 BNSS अंतर्गत आवश्यक कोठडी कालावधी पूर्ण करतो. विधी साहाय्य वकील नियुक्ती सुरू आहे.",
            "bn": "মামলাটি ধারা ৪৭৯ BNSS এর অধীনে বিধিবদ্ধ হেফাজতের সময়সীমা পূরণ করেছে। আইনি সহায়ক আইনজীবী নিয়োগ প্রক্রিয়াধীন।",
        },
    },
    "COUNSEL_ASSIGNED": {
        "title": {
            "en": "Legal-Aid Defense Counsel Assigned",
            "hi": "कानूनी सहायता अधिवक्ता नियुक्त",
            "kn": "ಕಾನೂನು ನೆರವು ರಕ್ಷಣಾ ವಕೀಲರನ್ನು ನಿಯೋಜಿಸಲಾಗಿದೆ",
            "te": "లీగల్-ఎయిడ్ డిఫెన్స్ న్యాయవాది కేటాయించబడ్డారు",
            "ta": "சட்ட உதவி வழக்கறிஞர் நியமிக்கப்பட்டுள்ளார்",
            "mr": "विधी सहाय्य बचाव वकील नियुक्त",
            "bn": "আইনি সহায়তা প্রতিরক্ষা আইনজীবী নিযুক্ত",
        },
        "detail": {
            "en": "A panel defense counsel has been appointed by DLSA to examine records and prepare court representations.",
            "hi": "डीएलएसए द्वारा पैरवी और आवेदन तैयार करने के लिए अधिवक्ता नियुक्त किया गया है।",
            "kn": "ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಲು ಮತ್ತು ನ್ಯಾಯಾಲಯದ ಅರ್ಜಿ ಸಿದ್ಧಪಡಿಸಲು DLSA ವಕೀಲರನ್ನು ನೇಮಿಸಿದೆ.",
            "te": "రికార్డులను పరిశీలించి కోర్టు పిటిషన్ సిద్ధం చేయడానికి DLSA ప్యానెల్ న్యాయవాదిని నియమించింది.",
            "ta": "ஆவணங்களை ஆராய்ந்து நீதிமன்ற மனு தயாரிக்க DLSA குழு வழக்கறிஞரை நியமித்துள்ளது.",
            "mr": "नोंदींची तपासणी करून न्यायालयात अर्ज सादर करण्यासाठी DLSA ने वकील नियुक्त केला आहे.",
            "bn": "নথিপত্র পরীক্ষা এবং আদালতের আবেদন প্রস্তুত করার জন্য DLSA প্যানেল আইনজীবী নিযুক্ত করেছে।",
        },
    },
    "READY_FOR_FILING": {
        "title": {
            "en": "Draft Petition Approved (Awaiting Court Filing)",
            "hi": "प्रारूप याचिका स्वीकृत (अदालत में दायर होने की प्रतीक्षा)",
            "kn": "ಕರಡು ಅರ್ಜಿ ಅನುಮೋದಿಸಲಾಗಿದೆ (ನ್ಯಾಯಾಲಯ ಸಲ್ಲಿಕೆ ನಿರೀಕ್ಷೆಯಲ್ಲಿದೆ)",
            "te": "డ్రాఫ్ట్ పిటిషన్ ఆమోదించబడింది (కోర్టు దాఖలు కోసం వేచి ఉంది)",
            "ta": "வரைவு மனு அங்கீகரிக்கப்பட்டது (நீதிமன்ற தாக்கல் நிலுவையில் உள்ளது)",
            "mr": "मसुदा याचिका मंजूर (न्यायालयात दाखल करण्याची प्रतीक्षा)",
            "bn": "খসড়া আবেদন অনুমোদিত (আদালতে দাখিলের অপেক্ষায়)",
        },
        "detail": {
            "en": "Draft bail petition reviewed and approved by supervising legal officer. Registry submission pending.",
            "hi": "पर्यवेक्षी अधिकारी द्वारा प्रारूप स्वीकृत। अदालत में याचिका दायर करने की प्रक्रिया चल रही है।",
            "kn": "ಮೇಲ್ವಿಚಾರಣಾ ಅಧಿಕಾರಿಯಿಂದ ಕರಡು ಅರ್ಜಿ ಅನುಮೋದಿಸಲಾಗಿದೆ. ನ್ಯಾಯಾಲಯಕ್ಕೆ ಸಲ್ಲಿಸುವ ಪ್ರಕ್ರಿಯೆ ಬಾಕಿ ಇದೆ.",
            "te": "పర్యవేక్షణ అధికారి ద్వారా పిటిషన్ ఆమోదించబడింది. కోర్టులో దాఖలు చేసే ప్రక్రియ జరుగుతోంది.",
            "ta": "மேற்பார்வை அதிகாரியால் வரைவு மனு அங்கீகரிக்கப்பட்டது. நீதிமன்ற பதிவேட்டில் சமர்ப்பிக்க நிலுவையில் உள்ளது.",
            "mr": "पर्यवेक्षक अधिकाऱ्याने मसुदा याचिका मंजूर केली आहे. न्यायालयात दाखल करण्याची प्रक्रिया सुरू आहे.",
            "bn": "তত্ত্বাবধায়ক কর্মকর্তা খসড়া আবেদন অনুমোদন করেছেন। আদালতে দাখিলের প্রক্রিয়া চলছে।",
        },
    },
    "FILED_IN_COURT": {
        "title": {
            "en": "Petition Formally Filed in Court",
            "hi": "अदालत की रजिस्ट्री में याचिका दायर",
            "kn": "ನ್ಯಾಯಾಲಯದ ರಿಜಿಸ್ಟ್ರಿಯಲ್ಲಿ ಅರ್ಜಿ ಅಧಿಕೃತವಾಗಿ ದಾಖಲಾಗಿದೆ",
            "te": "కోర్టు రిజిస్ట్రీలో పిటిషన్ అధికారికంగా దాఖలైంది",
            "ta": "நீதிமன்ற பதிவேட்டில் மனு முறைப்படி தாக்கல் செய்யப்பட்டது",
            "mr": "न्यायालयीन नोंदणीत याचिका औपचारिकपणे दाखल",
            "bn": "আদালত রেজিস্ট্রিতে আবেদন আনুষ্ঠানিকভাবে দাখিল করা হয়েছে",
        },
        "detail": {
            "en": "The bail petition has been formally lodged with court registry. Awaiting court hearing and judicial determination.",
            "hi": "जमानत याचिका अदालत की रजिस्ट्री में औपचारिक रूप से दायर कर दी गई है। सुनवाई की प्रतीक्षा है।",
            "kn": "ಜಾಮೀನು ಅರ್ಜಿಯನ್ನು ನ್ಯಾಯಾಲಯದ ರಿಜಿಸ್ಟ್ರಿಯಲ್ಲಿ ಸಲ್ಲಿಸಲಾಗಿದೆ. ವಿಚಾರಣೆ ನಿರೀಕ್ಷೆಯಲ್ಲಿದೆ.",
            "te": "బెయిల్ పిటిషన్ కోర్టులో అధికారికంగా దాఖలు చేయబడింది. విచారణ కోసం వేచి ఉంది.",
            "ta": "பிணை மனு நீதிமன்ற பதிவேட்டில் முறைப்படி தாக்கல் செய்யப்பட்டுள்ளது. விசாரணை நிலுவையில் உள்ளது.",
            "mr": "जामीन याचिका न्यायालयात अधिकृतपणे दाखल झाली आहे. सुनावणीची प्रतीक्षा आहे.",
            "bn": "জামিন আবেদনটি আনুষ্ঠানিকভাবে আদালতে দায়ের করা হয়েছে। শুনানির অপেক্ষায়।",
        },
    },
    "COURT_ORDER_RECEIVED": {
        "title": {
            "en": "Court Bail Order Issued",
            "hi": "अदालत का जमानत आदेश प्राप्त",
            "kn": "ನ್ಯಾಯಾಲಯದ ಜಾಮೀನು ಆದೇಶ ಹೊರಡಿಸಲಾಗಿದೆ",
            "te": "కోర్టు బెయిల్ ఉత్తర్వు జారీ చేయబడింది",
            "ta": "நீதிமன்ற பிணை உத்தரவு பிறப்பிக்கப்பட்டுள்ளது",
            "mr": "न्यायालयाचा जामीन आदेश जारी",
            "bn": "আদালতের জামিন আদেশ জারি হয়েছে",
        },
        "detail": {
            "en": "The competent court has passed an order on the bail petition. Order transmission to jail authority underway.",
            "hi": "सक्षम अदालत ने आदेश पारित कर दिया है। जेल अधीक्षक को आदेश प्रेषण प्रक्रिया में है।",
            "kn": "ಸಕ್ಷಮ ನ್ಯಾಯಾಲಯವು ಆದೇಶ ಹೊರಡಿಸಿದೆ. ಜೈಲು ಅಧಿಕಾರಿಗಳಿಗೆ ಆದೇಶ ರವಾನೆ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ.",
            "te": "సమర్థ న్యాయస్థానం ఉత్తర్వు జారీ చేసింది. జైలు అధికారులకు ఉత్తర్వుల బదిలీ జరుగుతోంది.",
            "ta": "நீதிமன்றம் பிணை உத்தரவு பிறப்பித்துள்ளது. சிறை அதிகாரிகளுக்கு உத்தரவு அனுப்பப்படுகிறது.",
            "mr": "सक्षम न्यायालयाने आदेश दिला आहे. तुरुंग प्रशासनाकडे आदेश पाठवला जात आहे.",
            "bn": "আদালত জামিন আদেশ প্রদান করেছে। কারাগার কর্তৃপক্ষের কাছে আদেশ পাঠানোর প্রক্রিয়া চলছে।",
        },
    },
    "RELEASE_EXECUTED": {
        "title": {
            "en": "Prison Release Executed",
            "hi": "जेल रिहाई प्रक्रिया पूर्ण",
            "kn": "ಕಾರಾಗೃಹ ಬಿಡುಗಡೆ ಪ್ರಕ್ರಿಯೆ ಪೂರ್ಣಗೊಂಡಿದೆ",
            "te": "జైలు విడుదల ప్రక్రియ పూర్తయింది",
            "ta": "சிறை விடுதலை நடைமுறை நிறைவடைந்தது",
            "mr": "तुरुंग सुटका प्रक्रिया पूर्ण",
            "bn": "কারাগার মুক্তি প্রক্রিয়া সম্পন্ন",
        },
        "detail": {
            "en": "Prison authorities have verified the court bail order and confirmed formal release from custody.",
            "hi": "जेल प्रशासन ने अदालत के आदेश का सत्यापन कर हिरासत से रिहाई की पुष्टि कर दी है।",
            "kn": "ಜೈಲು ಆಡಳಿತವು ನ್ಯಾಯಾಲಯದ ಆದೇಶವನ್ನು ಪರಿಶೀಲಿಸಿ ಬಂಧನದಿಂದ ಬಿಡುಗಡೆ ದೃಢಪಡಿಸಿದೆ.",
            "te": "జైలు అధికారులు కోర్టు ఉత్తర్వును ధృవీకరించి విడుదల చేసినట్లు నిర్ధారించారు.",
            "ta": "சிறைத்துறை நீதிமன்ற உத்தரவை சரிபார்த்து விடுதலையை உறுதி செய்துள்ளது.",
            "mr": "तुरुंग प्रशासनाने न्यायालयाच्या आदेशाची पडताळणी करून सुटका निश्चित केली आहे.",
            "bn": "কারাগার প্রশাসন আদালতের আদেশ যাচাই করে মুক্তি নিশ্চিত করেছে।",
        },
    },
}

DOCUMENT_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "fir": {
        "en": "First Information Report (FIR Copy)",
        "hi": "प्राथमिकी सूचना रिपोर्ट (एफआईआर प्रति)",
        "kn": "ಪ್ರಥಮ ಮಾಹಿತಿ ವರದಿ (ಎಫ್ಐಆರ್ ಪ್ರತಿ)",
        "te": "ప్రథమ సమాచార నివేదిక (ఎఫ్ఐఆర్ కాపీ)",
        "ta": "முதல் தகவல் அறிக்கை (FIR நகல்)",
        "mr": "प्रथम माहिती अहवाल (एफआयआर प्रत)",
        "bn": "এফআইআর কপি (প্রথম তথ্য বিবরণী)",
    },
    "charge_sheet": {
        "en": "Police Charge Sheet",
        "hi": "पुलिस आरोप पत्र (चार्जशीट)",
        "kn": "ಪೊಲೀಸ್ ಆರೋಪಪಟ್ಟಿ (ಚಾರ್ಜ್ ಶೀಟ್)",
        "te": "పోలీస్ చార్జిషీట్",
        "ta": "காவல்துறை குற்றப்பத்திரிகை",
        "mr": "पोलीस दोषारोपपत्र (चार्जशीट)",
        "bn": "পুলিশ চার্জশিট",
    },
    "remand_order": {
        "en": "Judicial Remand Order",
        "hi": "न्यायिक हिरासत आदेश (रिमांड आदेश)",
        "kn": "ನ್ಯಾಯಾಂಗ ಬಂಧನ ಆದೇಶ (ರಿಮಾಂಡ್ ಆರ್ಡರ್)",
        "te": "జ్యుడీషియల్ రిమాండ్ ఉత్తర్వు",
        "ta": "நீதிமன்ற காவலாணை (ரிமாண்ட் உத்தரவு)",
        "mr": "न्यायालयीन कोठडी आदेश (रिमांड ऑर्डर)",
        "bn": "জুডিশিয়াল রিমান্ড আদেশ",
    },
    "custody_certificate": {
        "en": "Prison Custody Certificate",
        "hi": "जेल अभिरक्षा प्रमाणपत्र",
        "kn": "ಕಾರಾಗೃಹ ಬಂಧನ ಪ್ರಮಾಣಪತ್ರ",
        "te": "జైలు నిర్బంధ ధృవీకరణ పత్రం",
        "ta": "சிறைக் காவல் சான்றிதழ்",
        "mr": "तुरुंग कोठडी प्रमाणपत्र",
        "bn": "কারাগার হেফাজত সনদপত্র",
    },
    "bail_application": {
        "en": "Bail Application Copy",
        "hi": "जमानत आवेदन प्रति",
        "kn": "ಜಾಮೀನು ಅರ್ಜಿ ಪ್ರತಿ",
        "te": "బెయిల్ పిటిషన్ కాపీ",
        "ta": "பிணை விண்ணப்ப நகல்",
        "mr": "जामीन अर्ज प्रत",
        "bn": "জামিন আবেদন কপি",
    },
    "court_order": {
        "en": "Court Order / Bail Decision",
        "hi": "अदालत का आदेश / जमानत निर्णय",
        "kn": "ನ್ಯಾಯಾಲಯದ ಆದೇಶ / ಜಾಮೀನು ತೀರ್ಪು",
        "te": "కోర్టు ఉత్తర్వు / బెయిల్ నిర్ణయం",
        "ta": "நீதிமன்ற உத்தரவு / பிணை தீர்ப்பு",
        "mr": "न्यायालयाचा आदेश / जामीन निकाल",
        "bn": "আদালতের আদেশ / জামিন রায়",
    },
}

DISCLAIMER_NOTICE = (
    "Original Authoritative Record: English. The translated version is a derived display "
    "provided solely for accessibility and convenience. It is NOT a source of legal truth. "
    "Under institutional guidelines, the original English court docket and signed orders prevail."
)

# ── Service Functions ─────────────────────────────────────────────────────────

def get_supported_languages() -> List[Dict[str, Any]]:
    """Return configured Indian languages registry."""
    return SUPPORTED_LANGUAGES


def get_status_translation(status_code: str, lang: str = "en") -> Dict[str, str]:
    """Retrieve canonical title and detail translation for a legal status."""
    st = STATUS_TRANSLATIONS.get(status_code, STATUS_TRANSLATIONS["UNDER_REVIEW"])
    titles = st["title"]
    details = st["detail"]
    
    title_text = titles.get(lang) or titles.get("en", "Case Status Under Review")
    detail_text = details.get(lang) or details.get("en", "Legal aid details are being examined.")
    
    return {
        "title": title_text,
        "detail": detail_text,
        "authoritative_title": titles["en"],
        "authoritative_detail": details["en"],
        "is_derived": (lang != "en"),
        "language": lang,
        "disclaimer": DISCLAIMER_NOTICE if lang != "en" else "",
    }


def get_document_title_translation(doc_type: str, lang: str = "en") -> Dict[str, str]:
    """Retrieve document title translation."""
    dt = DOCUMENT_TRANSLATIONS.get(doc_type, {})
    title = dt.get(lang) or dt.get("en") or doc_type.replace("_", " ").title()
    authoritative = dt.get("en") or doc_type.replace("_", " ").title()
    return {
        "title": title,
        "authoritative_title": authoritative,
        "is_derived": (lang != "en"),
        "language": lang,
    }


def generate_derived_display(
    authoritative_text: str,
    target_lang: str = "en",
    category: str = "EXPLANATION",
) -> Dict[str, Any]:
    """
    Generate or format derived display text for a given authoritative English text.
    Preserves original English text alongside the derived display.
    """
    if target_lang == "en" or not authoritative_text:
        return {
            "authoritative_text": authoritative_text,
            "derived_display_text": authoritative_text,
            "language_code": "en",
            "language_name": "English",
            "is_derived_display": False,
            "disclaimer": "",
        }

    lang_entry = next((l for l in SUPPORTED_LANGUAGES if l["code"] == target_lang), None)
    lang_name = lang_entry["name"] if lang_entry else target_lang

    # Attempt LLM translation via explainer if appropriate, or dictionary fallback
    derived_text = authoritative_text
    try:
        from app.llm_client import generate
        prompt = (
            f"Translate the following plain-language legal explanation into {lang_name} ({target_lang}). "
            f"Keep simple vocabulary suitable for a family member. Provide ONLY the translated text:\n\n"
            f"{authoritative_text}"
        )
        derived_text = generate(prompt=prompt, system="You are an expert legal aid multilingual assistant.")
    except Exception as e:
        logger.warning(f"Derived translation failed for {target_lang}: {e}. Falling back to English.")
        derived_text = authoritative_text

    return {
        "authoritative_text": authoritative_text,
        "derived_display_text": derived_text,
        "language_code": target_lang,
        "language_name": lang_name,
        "is_derived_display": True,
        "disclaimer": DISCLAIMER_NOTICE,
    }
