/**
 * citizenI18n.ts — Comprehensive Multilingual Localization for Citizen & Family Portal.
 * ======================================================================================
 * Supports all 7 official languages enabled in Nyaya Mitra:
 * - en: English (Authoritative Record)
 * - hi: Hindi (हिन्दी)
 * - kn: Kannada (ಕನ್ನಡ)
 * - te: Telugu (తెలుగు)
 * - ta: Tamil (தமிழ்)
 * - mr: Marathi (मराठी)
 * - bn: Bengali (বাংলা)
 */

export interface CitizenPortalTranslation {
  topBar: {
    languageLabel: string;
    offline: string;
    online: string;
    synced: string;
    lowDataOn: string;
    lowDataOff: string;
    notifPrefsTitle: string;
  };
  derivedNotice: {
    label: string;
    text: string;
  };
  banner: {
    familyPortal: string;
    citizenPortal: string;
    refPrefix: string;
    legalStatusOf: string;
    welcome: string;
    statutoryRight: string;
  };
  statusBadges: {
    underReview: string;
    eligible479: string;
    counselAssigned: string;
    readyForFiling: string;
    filedInCourt: string;
    courtOrderReceived: string;
    releaseExecuted: string;
  };
  cards: {
    legalAidStatusTitle: string;
    assignedLawyerTitle: string;
    counselInProgress: string;
    freeDlsaDesk: string;
    nextHearingTitle: string;
    awaitingSchedule: string;
    courtRecordBadge: string;
  };
  procedural: {
    courtFilingTitle: string;
    filingRecord: string;
    formallyLodged: string;
    awaitingSubmission: string;
    reference: string;
    jurisdiction: string;
    custodyReleaseTitle: string;
    custodyStatus: string;
    inCustody: string;
    policeStation: string;
    verification: string;
  };
  aiSection: {
    inspectAuthoritative: string;
    showDerived: string;
    statutoryCautionTitle: string;
  };
  missingDocs: {
    title: string;
    actionRequired: string;
    subtitle: string;
    urgent: string;
    supporting: string;
    whyNeeded: string;
    howToSubmit: string;
  };
  entitledDocs: {
    title: string;
    authorizedSuffix: string;
    subtitle: string;
    verified: string;
    size: string;
    textSummaryBtn: string;
    provenanceBtn: string;
  };
  actionCenter: {
    title: string;
    auditableDesk: string;
    subtitle: string;
    contactCounselTitle: string;
    contactCounselSub: string;
    flagDiscrepancyTitle: string;
    flagDiscrepancySub: string;
    requestDocTitle: string;
    requestDocSub: string;
    askHelpTitle: string;
    askHelpSub: string;
    pastSubmissionsTitle: string;
    trackingId: string;
  };
  nalsaBanner: {
    title: string;
    desc: string;
    phoneBtn: string;
  };
  actionModal: {
    title: string;
    requestType: string;
    optContact: string;
    optDiscrepancy: string;
    optDoc: string;
    optHelp: string;
    fieldLabel: string;
    fieldCustody: string;
    fieldParent: string;
    fieldAddress: string;
    fieldOffense: string;
    docLabel: string;
    docChargeSheet: string;
    docRemand: string;
    docFir: string;
    docCustodyCert: string;
    subjectLabel: string;
    subjectPlaceholder: string;
    detailsLabel: string;
    detailsPlaceholder: string;
    cancelBtn: string;
    submitBtn: string;
    submitting: string;
    doneBtn: string;
    successMsg: string;
  };
  notifModal: {
    title: string;
    phoneLabel: string;
    smsLabel: string;
    whatsappLabel: string;
    inAppLabel: string;
    statutoryNoticeLabel: string;
    statutoryNoticeText: string;
    closeBtn: string;
    saveBtn: string;
    saving: string;
    savedMsg: string;
  };
  textSummaryModal: {
    recordType: string;
    size: string;
    summaryLabel: string;
    syncing: string;
    extractLabel: string;
    certNotice: string;
    closeBtn: string;
  };
  emptyStates: {
    loadingRecord: string;
    noActiveCase: string;
    noCaseDesc: string;
    callNalsa: string;
    tollFreeLabel: string;
  };
}

export const CITIZEN_PORTAL_I18N: Record<string, CitizenPortalTranslation> = {
  en: {
    topBar: {
      languageLabel: "Language (भाषा):",
      offline: "Offline",
      online: "Online",
      synced: "Synced",
      lowDataOn: "⚡ Low-Data: ON",
      lowDataOff: "Low-Data: OFF",
      notifPrefsTitle: "Notification Preferences & Consent",
    },
    derivedNotice: {
      label: "Accessibility Notice:",
      text: "Translated text is a derived display provided for informational accessibility. The original English court docket remains the authoritative source of legal truth.",
    },
    banner: {
      familyPortal: "Family & Guardian Assistance Portal",
      citizenPortal: "Citizen Legal Aid Portal",
      refPrefix: "Ref:",
      legalStatusOf: "Legal Status of",
      welcome: "Welcome,",
      statutoryRight: "Under Article 39A of the Constitution of India and Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023, you are entitled to free legal aid representation and periodic judicial custody review without fee.",
    },
    statusBadges: {
      underReview: "UNDER INITIAL REVIEW",
      eligible479: "ELIGIBLE UNDER SEC 479",
      counselAssigned: "COUNSEL ASSIGNED",
      readyForFiling: "DRAFT APPROVED • PENDING FILING",
      filedInCourt: "FILED IN COURT",
      courtOrderReceived: "COURT BAIL ORDER ISSUED",
      releaseExecuted: "PRISON RELEASE EXECUTED",
    },
    cards: {
      legalAidStatusTitle: "Legal Aid Status",
      assignedLawyerTitle: "Assigned Defense Lawyer",
      counselInProgress: "Counsel Allocation in Progress",
      freeDlsaDesk: "Free DLSA Legal Assistance Desk",
      nextHearingTitle: "Next Court Hearing",
      awaitingSchedule: "Awaiting Schedule",
      courtRecordBadge: "Authoritative Court Record",
    },
    procedural: {
      courtFilingTitle: "Court Filing Status",
      filingRecord: "Filing Record:",
      formallyLodged: "FORMALLY LODGED",
      awaitingSubmission: "AWAITING SUBMISSION",
      reference: "Reference:",
      jurisdiction: "Jurisdiction:",
      custodyReleaseTitle: "Custody & Release Status",
      custodyStatus: "Custody Status:",
      inCustody: "IN CUSTODY",
      policeStation: "Police Station:",
      verification: "Verification:",
    },
    aiSection: {
      inspectAuthoritative: "Inspect Authoritative English",
      showDerived: "Show Derived Translation",
      statutoryCautionTitle: "Statutory Caution",
    },
    missingDocs: {
      title: "Documents Needed From Your Side",
      actionRequired: "Action Required",
      subtitle: "To assist the legal-aid counsel in proceeding with court bail representations, please prepare the following documents:",
      urgent: "URGENT",
      supporting: "SUPPORTING",
      whyNeeded: "Why needed:",
      howToSubmit: "How to submit:",
    },
    entitledDocs: {
      title: "Verified Case Records Entitled To You",
      authorizedSuffix: "Authorized",
      subtitle: "Authorized case records verified by the Legal Services Authority. Text summaries allow instant reading on low bandwidth:",
      verified: "VERIFIED",
      size: "Size:",
      textSummaryBtn: "Text Summary",
      provenanceBtn: "Provenance",
    },
    actionCenter: {
      title: "Citizen Action Center",
      auditableDesk: "Auditable DLSA Desk",
      subtitle: "Submit official requests directly to the DLSA Secretary and Jail Welfare Officer:",
      contactCounselTitle: "Contact DLSA Counsel",
      contactCounselSub: "Request panel advocate consultation",
      flagDiscrepancyTitle: "Flag Discrepancy",
      flagDiscrepancySub: "Report incorrect dates or details",
      requestDocTitle: "Request Document Copy",
      requestDocSub: "Request certified order or report copy",
      askHelpTitle: "Ask For Legal Aid Help",
      askHelpSub: "Urgent welfare / medical consultation",
      pastSubmissionsTitle: "Your Past Submissions",
      trackingId: "Tracking ID:",
    },
    nalsaBanner: {
      title: "National Legal Services Helpline (NALSA 24x7)",
      desc: "Toll-free government assistance for undertrials and family members under the Legal Services Authorities Act.",
      phoneBtn: "15100 (Toll-Free)",
    },
    actionModal: {
      title: "Submit Citizen Request",
      requestType: "Request Type",
      optContact: "Request DLSA Panel Counsel Contact",
      optDiscrepancy: "Report Discrepancy / Flag Error",
      optDoc: "Request Certified Document Copy",
      optHelp: "Ask for Urgent Legal Aid Help",
      fieldLabel: "Field with Discrepancy",
      fieldCustody: "Custody Period / Admission Date",
      fieldParent: "Parent / Guardian Name",
      fieldAddress: "Permanent Address",
      fieldOffense: "Recorded Offence Sections",
      docLabel: "Document Requested",
      docChargeSheet: "Police Charge Sheet",
      docRemand: "Judicial Remand Order",
      docFir: "First Information Report (FIR)",
      docCustodyCert: "Prison Custody Certificate",
      subjectLabel: "Subject",
      subjectPlaceholder: "Brief summary of what you require...",
      detailsLabel: "Details",
      detailsPlaceholder: "Provide specific details for the DLSA desk...",
      cancelBtn: "Cancel",
      submitBtn: "Submit to DLSA",
      submitting: "Submitting...",
      doneBtn: "Done",
      successMsg: "Request submitted successfully to DLSA Legal Aid Desk.",
    },
    notifModal: {
      title: "Notification Preferences & Consent",
      phoneLabel: "Registered Mobile Phone",
      smsLabel: "SMS Statutory Hearing & Status Notices",
      whatsappLabel: "WhatsApp Legal Aid Assistance Notices",
      inAppLabel: "In-App Status Alerts",
      statutoryNoticeLabel: "Statutory Notice:",
      statutoryNoticeText: "Notification delivery is recorded under the Legal Services Authorities Act, 1987. No commercial carrier charges are applied.",
      closeBtn: "Close",
      saveBtn: "Save Preferences",
      saving: "Saving...",
      savedMsg: "Preferences & statutory consent updated successfully.",
    },
    textSummaryModal: {
      recordType: "Record Type:",
      size: "Size:",
      summaryLabel: "Plain-Language Summary:",
      syncing: "Syncing...",
      extractLabel: "Document Extract / Record Snippet:",
      certNotice: "This document is certified by the Legal Services Authority. Certified paper copies may also be inspected at the DLSA Front Office during court working hours.",
      closeBtn: "Close Preview",
    },
    emptyStates: {
      loadingRecord: "Loading authorized legal aid record...",
      noActiveCase: "No Active Case Linked to This Account",
      noCaseDesc: "No active legal aid case is currently linked to your credentials. If you or an undertrial family member requires legal representation, please contact the National Legal Services Helpline (15100) or visit your local District Legal Services Authority (DLSA) office.",
      callNalsa: "Call NALSA Helpline: 15100",
      tollFreeLabel: "24x7 Toll-Free Free Legal Aid",
    },
  },

  hi: {
    topBar: {
      languageLabel: "भाषा:",
      offline: "ऑफ़लाइन",
      online: "ऑनलाइन",
      synced: "सिंक किया गया",
      lowDataOn: "⚡ कम डेटा: चालू",
      lowDataOff: "कम डेटा: बंद",
      notifPrefsTitle: "अधिसूचना प्राथमिकताएं और सहमति",
    },
    derivedNotice: {
      label: "सुलभता सूचना:",
      text: "अनुवादित पाठ सूचनात्मक सुलभता के लिए व्युत्पन्न प्रदर्शन है। मूल अंग्रेजी अदालत डॉकेट कानूनी सत्य का आधिकारिक स्रोत बना रहेगा।",
    },
    banner: {
      familyPortal: "परिवार एवं संरक्षक सहायता पोर्टल",
      citizenPortal: "नागरिक कानूनी सहायता पोर्टल",
      refPrefix: "संदर्भ संख्या:",
      legalStatusOf: "कानूनी स्थिति:",
      welcome: "स्वागत है,",
      statutoryRight: "भारतीय संविधान के अनुच्छेद 39A और भारतीय नागरिक सुरक्षा संहिता (BNSS), 2023 की धारा 479 के तहत, आप निःशुल्क कानूनी सहायता प्रतिनिधित्व और आवधिक न्यायिक हिरासत समीक्षा के हकदार हैं।",
    },
    statusBadges: {
      underReview: "प्रारंभिक समीक्षाधीन",
      eligible479: "धारा 479 के तहत पात्र",
      counselAssigned: "वकील नियुक्त",
      readyForFiling: "प्रारूप स्वीकृत • दाखिला लंबित",
      filedInCourt: "अदालत में दायर",
      courtOrderReceived: "अदालत जमानत आदेश जारी",
      releaseExecuted: "जेल से रिहाई निष्पादित",
    },
    cards: {
      legalAidStatusTitle: "कानूनी सहायता स्थिति",
      assignedLawyerTitle: "नियुक्त बचाव पक्ष के वकील",
      counselInProgress: "वकील आवंटन प्रक्रिया जारी",
      freeDlsaDesk: "निःशुल्क डीएलएसए कानूनी सहायता केंद्र",
      nextHearingTitle: "अगली अदालत सुनवाई",
      awaitingSchedule: "तिथि प्रतीक्षित",
      courtRecordBadge: "आधिकारिक अदालत रिकॉर्ड",
    },
    procedural: {
      courtFilingTitle: "अदालत दाखिला स्थिति",
      filingRecord: "दाखिला रिकॉर्ड:",
      formallyLodged: "औपचारिक रूप से दायर",
      awaitingSubmission: "जमा करना शेष",
      reference: "संदर्भ:",
      jurisdiction: "न्यायाधिकार क्षेत्र:",
      custodyReleaseTitle: "हिरासत और रिहाई स्थिति",
      custodyStatus: "हिरासत स्थिति:",
      inCustody: "न्यायिक हिरासत में",
      policeStation: "थाना:",
      verification: "सत्यापन:",
    },
    aiSection: {
      inspectAuthoritative: "आधिकारिक अंग्रेजी देखें",
      showDerived: "अनुवादित प्रदर्शन देखें",
      statutoryCautionTitle: "वैधानिक चेतावनी",
    },
    missingDocs: {
      title: "आपकी ओर से आवश्यक दस्तावेज़",
      actionRequired: "कार्रवाई आवश्यक",
      subtitle: "कानूनी सहायता वकील को अदालत में जमानत याचिका प्रस्तुत करने में सहायता हेतु कृपया निम्नलिखित दस्तावेज़ तैयार करें:",
      urgent: "अति आवश्यक",
      supporting: "सहायक",
      whyNeeded: "क्यों आवश्यक है:",
      howToSubmit: "कैसे जमा करें:",
    },
    entitledDocs: {
      title: "सत्यापित मामला रिकॉर्ड (हकदार)",
      authorizedSuffix: "अधिकृत",
      subtitle: "विधिक सेवा प्राधिकरण द्वारा सत्यापित आधिकारिक रिकॉर्ड। टेक्स्ट सारांश कम नेटवर्क में भी तुरंत खुलते हैं:",
      verified: "सत्यापित",
      size: "आकार:",
      textSummaryBtn: "टेक्स्ट सारांश",
      provenanceBtn: "स्रोत प्रमाण",
    },
    actionCenter: {
      title: "नागरिक कार्रवाई केंद्र",
      auditableDesk: "लेखापरीक्षित डीएलएसए डेस्क",
      subtitle: "डीएलएसए सचिव और जेल कल्याण अधिकारी को सीधे आधिकारिक अनुरोध भेजें:",
      contactCounselTitle: "डीएलएसए वकील से संपर्क करें",
      contactCounselSub: "पैनल अधिवक्ता से परामर्श का अनुरोध करें",
      flagDiscrepancyTitle: "विसंगति की रिपोर्ट करें",
      flagDiscrepancySub: "गलत तारीख या जानकारी दर्ज करें",
      requestDocTitle: "दस्तावेज़ प्रति का अनुरोध",
      requestDocSub: "प्रमाणित आदेश या रिपोर्ट की प्रति मांगें",
      askHelpTitle: "कानूनी सहायता मांगें",
      askHelpSub: "तत्काल कल्याण / चिकित्सा परामर्श",
      pastSubmissionsTitle: "आपके पूर्व अनुरोध",
      trackingId: "ट्रैकिंग आईडी:",
    },
    nalsaBanner: {
      title: "राष्ट्रीय विधिक सेवा हेल्पलाइन (नालसा 24x7)",
      desc: "विधिक सेवा प्राधिकरण अधिनियम के तहत विचाराधीन बंदियों और परिवारों हेतु निःशुल्क सरकारी हेल्पलाइन।",
      phoneBtn: "15100 (टोल-फ्री)",
    },
    actionModal: {
      title: "नागरिक अनुरोध प्रस्तुत करें",
      requestType: "अनुरोध प्रकार",
      optContact: "डीएलएसए पैनल अधिवक्ता से संपर्क का अनुरोध",
      optDiscrepancy: "रिकॉर्ड में विसंगति या त्रुटि की सूचना दें",
      optDoc: "प्रमाणित दस्तावेज़ प्रति का अनुरोध करें",
      optHelp: "तत्काल कानूनी सहायता का अनुरोध करें",
      fieldLabel: "विसंगति वाला फ़ील्ड",
      fieldCustody: "हिरासत अवधि / दाखिला तिथि",
      fieldParent: "माता-पिता / अभिभावक का नाम",
      fieldAddress: "स्थायी पता",
      fieldOffense: "दर्ज की गई अपराध धाराएं",
      docLabel: "अनुरोधित दस्तावेज़",
      docChargeSheet: "पुलिस आरोप-पत्र (चार्जशीट)",
      docRemand: "न्यायिक रिमांड आदेश",
      docFir: "प्राथमिकी (एफआईआर)",
      docCustodyCert: "जेल हिरासत प्रमाण पत्र",
      subjectLabel: "विषय",
      subjectPlaceholder: "अपनी आवश्यकता का संक्षिप्त विवरण लिखें...",
      detailsLabel: "विवरण",
      detailsPlaceholder: "डीएलएसए डेस्क हेतु आवश्यक विस्तृत जानकारी दें...",
      cancelBtn: "रद्द करें",
      submitBtn: "डीएलएसए को भेजें",
      submitting: "जमा हो रहा है...",
      doneBtn: "पूर्ण",
      successMsg: "अनुरोध डीएलएसए कानूनी सहायता केंद्र को सफलतापूर्वक भेज दिया गया है।",
    },
    notifModal: {
      title: "अधिसूचना प्राथमिकताएं और सहमति",
      phoneLabel: "पंजीकृत मोबाइल नंबर",
      smsLabel: "एसएमएस द्वारा सुनवाई व स्थिति सूचनाएं",
      whatsappLabel: "व्हाट्सएप कानूनी सहायता सूचनाएं",
      inAppLabel: "ऐप के भीतर स्थिति अलर्ट",
      statutoryNoticeLabel: "वैधानिक सूचना:",
      statutoryNoticeText: "अधिसूचना वितरण विधिक सेवा प्राधिकरण अधिनियम, 1987 के तहत दर्ज किया जाता है। कोई व्यावसायिक शुल्क नहीं लिया जाता।",
      closeBtn: "बंद करें",
      saveBtn: "प्राथमिकताएं सहेजें",
      saving: "सहेजा जा रहा है...",
      savedMsg: "प्राथमिकताएं और वैधानिक सहमति सफलतापूर्वक सहेजी गईं।",
    },
    textSummaryModal: {
      recordType: "रिकॉर्ड प्रकार:",
      size: "आकार:",
      summaryLabel: "सरल भाषा में सारांश:",
      syncing: "सिंक हो रहा है...",
      extractLabel: "दस्तावेज़ अंश / मुख्य अंश:",
      certNotice: "यह दस्तावेज़ विधिक सेवा प्राधिकरण द्वारा प्रमाणित है। प्रमाणित मुद्रित प्रतियां अदालत समय में डीएलएसए कार्यालय से भी प्राप्त की जा सकती हैं।",
      closeBtn: "पूर्वावलोकन बंद करें",
    },
    emptyStates: {
      loadingRecord: "अधिकृत कानूनी सहायता रिकॉर्ड लोड हो रहा है...",
      noActiveCase: "इस खाते से कोई सक्रिय मामला संबद्ध नहीं है",
      noCaseDesc: "आपके क्रेडेंशियल्स से वर्तमान में कोई सक्रिय कानूनी सहायता मामला जुड़ा नहीं है। यदि आपको या आपके परिवार के किसी विचाराधीन बंदी को कानूनी प्रतिनिधित्व की आवश्यकता है, तो कृपया राष्ट्रीय विधिक सेवा हेल्पलाइन (15100) पर संपर्क करें।",
      callNalsa: "नालसा हेल्पलाइन पर कॉल करें: 15100",
      tollFreeLabel: "24x7 टोल-फ्री निःशुल्क कानूनी सहायता",
    },
  },

  kn: {
    topBar: {
      languageLabel: "ಭಾಷೆ:",
      offline: "ಆಫ್‌ಲೈನ್",
      online: "ಆನ್‌ಲೈನ್",
      synced: "ಸಿಂಕ್ ಮಾಡಲಾಗಿದೆ",
      lowDataOn: "⚡ ಕಡಿಮೆ ಡೇಟಾ: ಆನ್",
      lowDataOff: "ಕಡಿಮೆ ಡೇಟಾ: ಆಫ್",
      notifPrefsTitle: "ಅಧಿಸೂಚನೆ ಆದ್ಯತೆಗಳು ಮತ್ತು ಒಪ್ಪಿಗೆ",
    },
    derivedNotice: {
      label: "ಲಭ್ಯತೆ ಸೂಚನೆ:",
      text: "ಅನುವಾದಿತ ಪಠ್ಯವು ಮಾಹಿತಿ ಸೌಲಭ್ಯಕ್ಕಾಗಿ ಪಡೆದ ಪ್ರದರ್ಶನವಾಗಿದೆ. ಮೂಲ ಇಂಗ್ಲಿಷ್ ನ್ಯಾಯಾಲಯದ ದಾಖಲೆಯು ಕಾನೂನು ಸತ್ಯದ ಅಧಿಕೃತ ಮೂಲವಾಗಿ ಉಳಿಯುತ್ತದೆ.",
    },
    banner: {
      familyPortal: "ಕುಟುಂಬ ಮತ್ತು ಪೋಷಕರ ಸಹಾಯ ಪೋರ್ಟಲ್",
      citizenPortal: "ನಾಗರಿಕ ಕಾನೂನು ನೆರವು ಪೋರ್ಟಲ್",
      refPrefix: "ಉಲ್ಲೇಖ ಸಂಖ್ಯೆ:",
      legalStatusOf: "ಕಾನೂನು ಸ್ಥಿತಿ:",
      welcome: "ಸ್ವಾಗತ,",
      statutoryRight: "ಭಾರತೀಯ ಸಂವಿಧಾನದ 39A ವಿಧಿ ಮತ್ತು ಭಾರತೀಯ ನಾಗರಿಕ ಸುರಕ್ಷಾ ಸಂಹಿತೆ (BNSS), 2023 ರ ಸೆಕ್ಷನ್ 479 ರ ಅಡಿಯಲ್ಲಿ, ನೀವು ಉಚಿತ ಕಾನೂನು ನೆರವು ಮತ್ತು ಆವರ್ತಕ ನ್ಯಾಯಾಂಗ ಕಸ್ಟಡಿ ಪರಿಶೀಲನೆಗೆ ಅರ್ಹರಾಗಿದ್ದೀರಿ.",
    },
    statusBadges: {
      underReview: "ಪ್ರಾಥಮಿಕ ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ",
      eligible479: "ಸೆಕ್ಷನ್ 479 ರ ಅಡಿಯಲ್ಲಿ ಅರ್ಹ",
      counselAssigned: "ವಕೀಲರನ್ನು ನೇಮಿಸಲಾಗಿದೆ",
      readyForFiling: "ಕರಡು ಅನುಮೋದಿಸಲಾಗಿದೆ • ಸಲ್ಲಿಕೆ ಬಾಕಿ",
      filedInCourt: "ನ್ಯಾಯಾಲಯದಲ್ಲಿ ಸಲ್ಲಿಸಲಾಗಿದೆ",
      courtOrderReceived: "ನ್ಯಾಯಾಲಯದ ಜಾಮೀನು ಆದೇಶ ನೀಡಲಾಗಿದೆ",
      releaseExecuted: "ಜೈಲಿನಿಂದ ಬಿಡುಗಡೆ ಮಾಡಲಾಗಿದೆ",
    },
    cards: {
      legalAidStatusTitle: "ಕಾನೂನು ನೆರವು ಸ್ಥಿತಿ",
      assignedLawyerTitle: "ನೇಮಕಗೊಂಡ ರಕ್ಷಣಾ ವಕೀಲರು",
      counselInProgress: "ವಕೀಲರ ಹಂಚಿಕೆ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ",
      freeDlsaDesk: "ಉಚಿತ ಡಿಎಲ್ಎಸ್ಎ ಕಾನೂನು ನೆರವು ಕೇಂದ್ರ",
      nextHearingTitle: "ಮುಂದಿನ ನ್ಯಾಯಾಲಯದ ವಿಚಾರಣೆ",
      awaitingSchedule: "ದಿನಾಂಕ ನಿರೀಕ್ಷೆಯಲ್ಲಿದೆ",
      courtRecordBadge: "ಅಧಿಕೃತ ನ್ಯಾಯಾಲಯ ದಾಖಲೆ",
    },
    procedural: {
      courtFilingTitle: "ನ್ಯಾಯಾಲಯದ ಸಲ್ಲಿಕೆ ಸ್ಥಿತಿ",
      filingRecord: "ಸಲ್ಲಿಕೆ ದಾಖಲೆ:",
      formallyLodged: "ಔಪಚಾರಿಕವಾಗಿ ದಾಖಲಿಸಲಾಗಿದೆ",
      awaitingSubmission: "ಸಲ್ಲಿಸುವುದು ಬಾಕಿ",
      reference: "ಉಲ್ಲೇಖ:",
      jurisdiction: "ನ್ಯಾಯವ್ಯಾಪ್ತಿ:",
      custodyReleaseTitle: "ಕಸ್ಟಡಿ ಮತ್ತು ಬಿಡುಗಡೆ ಸ್ಥಿತಿ",
      custodyStatus: "ಕಸ್ಟಡಿ ಸ್ಥಿತಿ:",
      inCustody: "ನ್ಯಾಯಾಂಗ ಬಂಧನದಲ್ಲಿದ್ದಾರೆ",
      policeStation: "ಪೊಲೀಸ್ ಠಾಣೆ:",
      verification: "ಪರಿಶೀಲನೆ:",
    },
    aiSection: {
      inspectAuthoritative: "ಅಧಿಕೃತ ಇಂಗ್ಲಿಷ್ ನೋಡಿ",
      showDerived: "ಅನುವಾದಿತ ವಿವರ ನೋಡಿ",
      statutoryCautionTitle: "ಶಾಸನಬದ್ಧ ಎಚ್ಚರಿಕೆ",
    },
    missingDocs: {
      title: "ನಿಮ್ಮ ಕಡೆಯಿಂದ ಅಗತ್ಯವಿರುವ ದಾಖಲೆಗಳು",
      actionRequired: "ಕ್ರಮ ಅಗತ್ಯವಿದೆ",
      subtitle: "ಜಾಮೀನು ಅರ್ಜಿ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿ ಕಾನೂನು ನೆರವು ವಕೀಲರಿಗೆ ಸಹಾಯ ಮಾಡಲು ದಯವಿಟ್ಟು ಈ ದಾಖಲೆಗಳನ್ನು ಸಿದ್ಧಪಡಿಸಿ:",
      urgent: "ತುರ್ತು",
      supporting: "ಪೂರಕ",
      whyNeeded: "ಏಕೆ ಬೇಕು:",
      howToSubmit: "ಹೇಗೆ ಸಲ್ಲಿಸಬೇಕು:",
    },
    entitledDocs: {
      title: "ಪರಿಶೀಲಿಸಿದ ಪ್ರಕರಣ ದಾಖಲೆಗಳು",
      authorizedSuffix: "ಅಧಿಕೃತ",
      subtitle: "ಕಾನೂನು ಸೇವೆಗಳ ಪ್ರಾಧಿಕಾರದಿಂದ ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟ ಅಧಿಕೃತ ದಾಖಲೆಗಳು:",
      verified: "ಪರಿಶೀಲಿಸಲಾಗಿದೆ",
      size: "ಗಾತ್ರ:",
      textSummaryBtn: "ಸಾರಾಂಶ",
      provenanceBtn: "ಮೂಲ ಪುರಾವೆ",
    },
    actionCenter: {
      title: "ನಾಗರಿಕ ಕ್ರಿಯಾ ಕೇಂದ್ರ",
      auditableDesk: "ಡಿಎಲ್ಎಸ್ಎ ಡೆಸ್ಕ್",
      subtitle: "ಡಿಎಲ್ಎಸ್ಎ ಕಾರ್ಯದರ್ಶಿ ಮತ್ತು ಜೈಲು ಕಲ್ಯಾಣಾಧಿಕಾರಿಗೆ ನೇರವಾಗಿ ಅಧಿಕೃತ ವಿನಂತಿ ಸಲ್ಲಿಸಿ:",
      contactCounselTitle: "ಡಿಎಲ್ಎಸ್ಎ ವಕೀಲರನ್ನು ಸಂಪರ್ಕಿಸಿ",
      contactCounselSub: "ಪ್ಯಾನಲ್ ವಕೀಲರೊಂದಿಗೆ ಸಮಾಲೋಚನೆಗೆ ವಿನಂತಿ",
      flagDiscrepancyTitle: "ದೋಷವನ್ನು ವರದಿ ಮಾಡಿ",
      flagDiscrepancySub: "ತಪ್ಪು ದಿನಾಂಕ ಅಥವಾ ವಿವರಗಳನ್ನು ಸರಿಪಡಿಸಿ",
      requestDocTitle: "ದಾಖಲೆಯ ಪ್ರತಿ ವಿನಂತಿಸಿ",
      requestDocSub: "ಪ್ರಮಾಣೀಕೃತ ಆದೇಶ ಅಥವಾ ವರದಿಯ ಪ್ರತಿ",
      askHelpTitle: "ಕಾನೂನು ನೆರವು ಕೇಳಿ",
      askHelpSub: "ತುರ್ತು ಕಲ್ಯಾಣ / ವೈದ್ಯಕೀಯ ನೆರವು",
      pastSubmissionsTitle: "ನಿಮ್ಮ ಹಿಂದಿನ ಸಲ್ಲಿಕೆಗಳು",
      trackingId: "ಟ್ರ್ಯಾಕಿಂಗ್ ಐಡಿ:",
    },
    nalsaBanner: {
      title: "ರಾಷ್ಟ್ರೀಯ ಕಾನೂನು ಸೇವೆಗಳ ಸಹಾಯವಾಣಿ (ನಾಲ್ಸಾ 24x7)",
      desc: "ವಿಚಾರಣಾಧೀನ ಕೈದಿಗಳು ಮತ್ತು ಕುಟುಂಬಗಳಿಗಾಗಿ ಉಚಿತ ಸರ್ಕಾರಿ ಸಹಾಯವಾಣಿ.",
      phoneBtn: "15100 (ಟೋಲ್-ಫ್ರೀ)",
    },
    actionModal: {
      title: "ನಾಗರಿಕ ವಿನಂತಿ ಸಲ್ಲಿಸಿ",
      requestType: "ವಿನಂತಿಯ ಪ್ರಕಾರ",
      optContact: "ಡಿಎಲ್ಎಸ್ಎ ಪ್ಯಾನಲ್ ವಕೀಲರ ಸಂಪರ್ಕ ವಿನಂತಿ",
      optDiscrepancy: "ದಾಖಲೆಗಳಲ್ಲಿನ ದೋಷ ವರದಿ ಮಾಡಿ",
      optDoc: "ಪ್ರಮಾಣೀಕೃತ ದಾಖಲೆಯ ಪ್ರತಿ ವಿನಂತಿಸಿ",
      optHelp: "ತುರ್ತು ಕಾನೂನು ನೆರವು ವಿನಂತಿ",
      fieldLabel: "ದೋಷವಿರುವ ಕ್ಷೇತ್ರ",
      fieldCustody: "ಕಸ್ಟಡಿ ಅವಧಿ / ದಾಖಲಾತಿ ದಿನಾಂಕ",
      fieldParent: "ಪೋಷಕರ ಹೆಸರು",
      fieldAddress: "ಖಾಯಂ ವಿಳಾಸ",
      fieldOffense: "ದಾಖಲಾದ ಅಪರಾಧ ಸೆಕ್ಷನ್‌ಗಳು",
      docLabel: "ವಿನಂತಿಸಿದ ದಾಖಲೆ",
      docChargeSheet: "ಪೊಲೀಸ್ ಚಾರ್ಜ್‌ಶೀಟ್",
      docRemand: "ನ್ಯಾಯಾಂಗ ರಿಮಾಂಡ್ ಆದೇಶ",
      docFir: "ಎಫ್‌ಐಆರ್ (FIR)",
      docCustodyCert: "ಜೈಲು ಕಸ್ಟಡಿ ಪ್ರಮಾಣಪತ್ರ",
      subjectLabel: "ವಿಷಯ",
      subjectPlaceholder: "ನಿಮ್ಮ ಅಗತ್ಯತೆಯ ಸಂಕ್ಷಿಪ್ತ ವಿವರ...",
      detailsLabel: "ವಿವರಗಳು",
      detailsPlaceholder: "ಡಿಎಲ್ಎಸ್ಎ ಡೆಸ್ಕ್‌ಗಾಗಿ ನಿರ್ದಿಷ್ಟ ವಿವರಗಳನ್ನು ನೀಡಿ...",
      cancelBtn: "ರದ್ದುಮಾಡಿ",
      submitBtn: "ಡಿಎಲ್ಎಸ್ಎಗೆ ಸಲ್ಲಿಸಿ",
      submitting: "ಸಲ್ಲಿಸಲಾಗುತ್ತಿದೆ...",
      doneBtn: "ಮುಕ್ತಾಯ",
      successMsg: "ವಿನಂತಿಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಡಿಎಲ್ಎಸ್ಎ ಡೆಸ್ಕ್‌ಗೆ ಸಲ್ಲಿಸಲಾಗಿದೆ.",
    },
    notifModal: {
      title: "ಅಧಿಸೂಚನೆ ಆದ್ಯತೆಗಳು ಮತ್ತು ಒಪ್ಪಿಗೆ",
      phoneLabel: "ನೋಂದಾಯಿತ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ",
      smsLabel: "ಎಸ್‌ಎಂಎಸ್ ಮೂಲಕ ವಿಚಾರಣೆ ಮತ್ತು ಸ್ಥಿತಿ ಸೂಚನೆಗಳು",
      whatsappLabel: "ವಾಟ್ಸಾಪ್ ಕಾನೂನು ನೆರವು ಸೂಚನೆಗಳು",
      inAppLabel: "ಆ್ಯಪ್ ಒಳಗಿನ ಸ್ಥಿತಿ ಎಚ್ಚರಿಕೆಗಳು",
      statutoryNoticeLabel: "ಶಾಸನಬದ್ಧ ಸೂಚನೆ:",
      statutoryNoticeText: "ಕಾನೂನು ಸೇವೆಗಳ ಪ್ರಾಧಿಕಾರಗಳ ಕಾಯಿದೆ, 1987 ರ ಅಡಿಯಲ್ಲಿ ಅಧಿಸೂಚನೆಗಳನ್ನು ದಾಖಲಿಸಲಾಗುತ್ತದೆ.",
      closeBtn: "ಮುಚ್ಚಿ",
      saveBtn: "ಆದ್ಯತೆಗಳನ್ನು ಉಳಿಸಿ",
      saving: "ಉಳಿಸಲಾಗುತ್ತಿದೆ...",
      savedMsg: "ಆದ್ಯತೆಗಳು ಮತ್ತು ಒಪ್ಪಿಗೆಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ನವೀಕರಿಸಲಾಗಿದೆ.",
    },
    textSummaryModal: {
      recordType: "ದಾಖಲೆಯ ಪ್ರಕಾರ:",
      size: "ಗಾತ್ರ:",
      summaryLabel: "ಸರಳ ಭಾಷೆಯ ಸಾರಾಂಶ:",
      syncing: "ಸಿಂಕ್ ಆಗುತ್ತಿದೆ...",
      extractLabel: "ದಾಖಲೆಯ ಸಾರಾಂಶ:",
      certNotice: "ಈ ದಾಖಲೆಯನ್ನು ಕಾನೂನು ಸೇವೆಗಳ ಪ್ರಾಧಿಕಾರವು ಪ್ರಮಾಣೀಕರಿಸಿದೆ.",
      closeBtn: "ಮುಚ್ಚಿ",
    },
    emptyStates: {
      loadingRecord: "ಅಧಿಕೃತ ಕಾನೂನು ನೆರವು ದಾಖಲೆ ಲೋಡ್ ಆಗುತ್ತಿದೆ...",
      noActiveCase: "ಈ ಖಾತೆಗೆ ಯಾವುದೇ ಸಕ್ರಿಯ ಪ್ರಕರಣ ಲಿಂಕ್ ಆಗಿಲ್ಲ",
      noCaseDesc: "ನಿಮ್ಮ ರುಜುವಾತುಗಳಿಗೆ ಯಾವುದೇ ಸಕ್ರಿಯ ಕಾನೂನು ನೆರವು ಪ್ರಕರಣವು ಪ್ರಸ್ತುತ ಲಿಂಕ್ ಆಗಿಲ್ಲ. ಸಹಾಯಕ್ಕಾಗಿ 15100 ಗೆ ಕರೆ ಮಾಡಿ.",
      callNalsa: "ನಾಲ್ಸಾ ಸಹಾಯವಾಣಿಗೆ ಕರೆ ಮಾಡಿ: 15100",
      tollFreeLabel: "24x7 ಉಚಿತ ಕಾನೂನು ನೆರವು",
    },
  },

  te: {
    topBar: {
      languageLabel: "భాష:",
      offline: "ఆఫ్‌లైన్",
      online: "ఆన్‌లైన్",
      synced: "సింక్ చేయబడింది",
      lowDataOn: "⚡ తక్కువ డేటా: ఆన్",
      lowDataOff: "తక్కువ డేటా: ఆఫ్",
      notifPrefsTitle: "నోటిఫికేషన్ ప్రాధాన్యతలు మరియు సమ్మతి",
    },
    derivedNotice: {
      label: "యాక్సెసిబిలిటీ నోటీసు:",
      text: "అనువదించబడిన వచనం సమాచార సౌలభ్యం కోసం అందించబడిన ప్రదర్శన. అసలు ఆంగ్ల కోర్టు రికార్డు అధికారిక చట్టపరమైన మూలంగా ఉంటుంది.",
    },
    banner: {
      familyPortal: "కుటుంబ మరియు సంరక్షకుల సహాయ పోర్టల్",
      citizenPortal: "పౌర న్యాయ సహాయ పోర్టల్",
      refPrefix: "రిఫరెన్స్ నం:",
      legalStatusOf: "చట్టపరమైన స్థితి:",
      welcome: "స్వాగతం,",
      statutoryRight: "భారత రాజ్యాంగంలోని ఆర్టికల్ 39A మరియు భారతీయ నాగరిక్ సురక్ష సంహిత (BNSS), 2023 లోని సెక్షన్ 479 ప్రకారం, మీరు ఉచిత న్యాయ సహాయ ప్రాతినిధ్యం మరియు ఆవర్తన జ్యుడీషియల్ కస్టడీ సమీక్షకు అర్హులు.",
    },
    statusBadges: {
      underReview: "ప్రారంభ సమీక్షలో ఉంది",
      eligible479: "సెక్షన్ 479 కింద అర్హత ఉంది",
      counselAssigned: "న్యాయవాది కేటాయించబడ్డారు",
      readyForFiling: "డ్రాఫ్ట్ ఆమోదించబడింది • దాఖలు పెండింగ్",
      filedInCourt: "కోర్టులో దాఖలు చేయబడింది",
      courtOrderReceived: "కోర్టు బెయిల్ ఆర్డర్ జారీ చేయబడింది",
      releaseExecuted: "జైలు విడుదల అమలు చేయబడింది",
    },
    cards: {
      legalAidStatusTitle: "న్యాయ సహాయ స్థితి",
      assignedLawyerTitle: "కేటాయించిన డిఫెన్స్ లాయర్",
      counselInProgress: "న్యాయవాది కేటాయింపు ప్రక్రియలో ఉంది",
      freeDlsaDesk: "ఉచిత DLSA న్యాయ సహాయ డెస్క్",
      nextHearingTitle: "తదుపరి కోర్టు విచారణ",
      awaitingSchedule: "తేదీ నిర్ణయించబడాలి",
      courtRecordBadge: "అధికారిక కోర్టు రికార్డు",
    },
    procedural: {
      courtFilingTitle: "కోర్టు దాఖలు స్థితి",
      filingRecord: "దాఖలు రికార్డు:",
      formallyLodged: "లాంఛనంగా దాఖలు చేయబడింది",
      awaitingSubmission: "సమర్పణ పెండింగ్‌లో ఉంది",
      reference: "రిఫరెన్స్:",
      jurisdiction: "పరిధి:",
      custodyReleaseTitle: "కస్టడీ మరియు విడుదల స్థితి",
      custodyStatus: "కస్టడీ స్థితి:",
      inCustody: "జ్యుడీషియల్ కస్టడీలో ఉన్నారు",
      policeStation: "పోలీస్ స్టేషన్:",
      verification: "ధృవీకరణ:",
    },
    aiSection: {
      inspectAuthoritative: "అధికారిక ఆంగ్లం చూడండి",
      showDerived: "అనువాద వివరణ చూడండి",
      statutoryCautionTitle: "చట్టబద్ధమైన హెచ్చరిక",
    },
    missingDocs: {
      title: "మీ వైపు నుండి అవసరమైన పత్రాలు",
      actionRequired: "చర్య అవసరం",
      subtitle: "బెయిల్ దరఖాస్తు కోసం న్యాయ సహాయ న్యాయవాదికి సహాయం చేయడానికి దయచేసి ఈ పత్రాలను సిద్ధం చేయండి:",
      urgent: "అత్యవసరం",
      supporting: "సహాయక",
      whyNeeded: "ఎందుకు అవసరం:",
      howToSubmit: "ఎలా సమర్పించాలి:",
    },
    entitledDocs: {
      title: "ధృవీకరించబడిన కేసు రికార్డులు",
      authorizedSuffix: "అధికారిక",
      subtitle: "లీగల్ సర్వీసెస్ అథారిటీ ద్వారా ధృవీకరించబడిన అధికారిక రికార్డులు:",
      verified: "ధృవీకరించబడింది",
      size: "పరిమాణం:",
      textSummaryBtn: "సారాంశం",
      provenanceBtn: "మూల రుజువు",
    },
    actionCenter: {
      title: "పౌర కార్యాచరణ కేంద్రం",
      auditableDesk: "DLSA డెస్క్",
      subtitle: "DLSA సెక్రటరీ మరియు జైలు సంక్షేమ అధికారికి నేరుగా అధికారిక అభ్యర్థనలను సమర్పించండి:",
      contactCounselTitle: "DLSA న్యాయవాదిని సంప్రదించండి",
      contactCounselSub: "ప్యానెల్ న్యాయవాదితో సంప్రదింపుల అభ్యర్థన",
      flagDiscrepancyTitle: "తేడాలను నివేదించండి",
      flagDiscrepancySub: "తప్పు తేదీలు లేదా వివరాలను నివేదించండి",
      requestDocTitle: "పత్రం కాపీని అభ్యర్థించండి",
      requestDocSub: "ధృవీకరించబడిన ఆర్డర్ లేదా నివేదిక కాపీ",
      askHelpTitle: "న్యాయ సహాయం కోరండి",
      askHelpSub: "అత్యవసర సంక్షేమం / వైద్య సహాయం",
      pastSubmissionsTitle: "మీ మునుపటి అభ్యర్థనలు",
      trackingId: "ట్రాకింగ్ ID:",
    },
    nalsaBanner: {
      title: "జాతీయ న్యాయ సేవల హెల్ప్‌లైన్ (NALSA 24x7)",
      desc: "విచారణలో ఉన్న ఖైదీలు మరియు కుటుంబాల కోసం ఉచిత ప్రభుత్వ హెల్ప్‌లైన్.",
      phoneBtn: "15100 (టోల్-ఫ్రీ)",
    },
    actionModal: {
      title: "పౌర అభ్యర్థనను సమర్పించండి",
      requestType: "అభ్యర్థన రకం",
      optContact: "DLSA ప్యానెల్ న్యాయవాది సంప్రదింపుల అభ్యర్థన",
      optDiscrepancy: "రికార్డులలో తేడాలు లేదా లోపాలను నివేదించండి",
      optDoc: "ధృవీకరించబడిన పత్రం కాపీని అభ్యర్థించండి",
      optHelp: "అత్యవసర న్యాయ సహాయం కోరండి",
      fieldLabel: "లోపం ఉన్న ఫీల్డ్",
      fieldCustody: "కస్టడీ వ్యవధి / అడ్మిషన్ తేదీ",
      fieldParent: "తల్లిదండ్రుల / సంరక్షకుల పేరు",
      fieldAddress: "శాశ్వత చిరునామా",
      fieldOffense: "నమోదైన నేర సెక్షన్లు",
      docLabel: "అభ్యర్థించిన పత్రం",
      docChargeSheet: "పోలీస్ ఛార్జ్ షీట్",
      docRemand: "జ్యుడీషియల్ రిమాండ్ ఆర్డర్",
      docFir: "ఎఫ్ఐఆర్ (FIR)",
      docCustodyCert: "జైలు కస్టడీ సర్టిఫికేట్",
      subjectLabel: "విషయం",
      subjectPlaceholder: "మీ అవసరానికి సంబంధించిన సంక్షిప్త వివరాలు...",
      detailsLabel: "వివరాలు",
      detailsPlaceholder: "DLSA డెస్క్ కోసం నిర్దిష్ట వివరాలను అందించండి...",
      cancelBtn: "రద్దు చేయండి",
      submitBtn: "DLSA కి సమర్పించండి",
      submitting: "సమర్పిస్తోంది...",
      doneBtn: "పూర్తయింది",
      successMsg: "అభ్యర్థన విజయవంతంగా DLSA డెస్క్‌కి సమర్పించబడింది.",
    },
    notifModal: {
      title: "నోటిఫికేషన్ ప్రాధాన్యతలు మరియు సమ్మతి",
      phoneLabel: "నమోదిత మొబైల్ ఫోన్",
      smsLabel: "SMS ద్వారా విచారణ మరియు స్థితి నోటీసులు",
      whatsappLabel: "వాట్సాప్ న్యాయ సహాయ నోటీసులు",
      inAppLabel: "యాప్‌లోని స్థితి హెచ్చరికలు",
      statutoryNoticeLabel: "చట్టబద్ధమైన నోటీసు:",
      statutoryNoticeText: "న్యాయ సేవల అధికారుల చట్టం, 1987 ప్రకారం నోటిఫికేషన్‌లు నమోదు చేయబడతాయి.",
      closeBtn: "మూసివేయండి",
      saveBtn: "ప్రాధాన్యతలను సేవ్ చేయండి",
      saving: "సేవ్ చేస్తోంది...",
      savedMsg: "ప్రాధాన్యతలు విజయవంతంగా అప్‌డేట్ చేయబడ్డాయి.",
    },
    textSummaryModal: {
      recordType: "రికార్డు రకం:",
      size: "పరిమాణం:",
      summaryLabel: "సరళమైన సారాంశం:",
      syncing: "సింక్ అవుతోంది...",
      extractLabel: "పత్రం సారాంశం:",
      certNotice: "ఈ పత్రం లీగల్ సర్వీసెస్ అథారిటీ ద్వారా ధృవీకరించబడింది.",
      closeBtn: "మూసివేయండి",
    },
    emptyStates: {
      loadingRecord: "అధికారిక న్యాయ సహాయ రికార్డు లోడ్ అవుతోంది...",
      noActiveCase: "ఈ ఖాతాకు ఎటువంటి సక్రియ కేసు లింక్ చేయబడలేదు",
      noCaseDesc: "మీ ఆధారాలకు ప్రస్తుతం ఎటువంటి చట్టపరమైన సహాయ కేసు లింక్ చేయబడలేదు. సహాయం కోసం 15100 కి కాల్ చేయండి.",
      callNalsa: "NALSA హెల్ప్‌లైన్‌కి కాల్ చేయండి: 15100",
      tollFreeLabel: "24x7 ఉచిత చట్టపరమైన సహాయం",
    },
  },

  ta: {
    topBar: {
      languageLabel: "மொழி:",
      offline: "ஆஃப்லைன்",
      online: "ஆன்லைன்",
      synced: "ஒத்திசைக்கப்பட்டது",
      lowDataOn: "⚡ குறைந்த தரவு: ஆன்",
      lowDataOff: "குறைந்த தரவு: ஆஃப்",
      notifPrefsTitle: "அறிவிப்பு விருப்பத்தேர்வுகள் மற்றும் ஒப்புதல்",
    },
    derivedNotice: {
      label: "அணுகல்தன்மை அறிவிப்பு:",
      text: "மொழிபெயர்க்கப்பட்ட உரை தகவல் அணுகலுக்காக பெறப்பட்ட காட்சியாகும். அசல் ஆங்கில நீதிமன்றப் பதிவே சட்டப்பூர்வ அதிகாரப்பூர்வ ஆதாரமாகும்.",
    },
    banner: {
      familyPortal: "குடும்பம் மற்றும் பாதுகாவலர் உதவி தளம்",
      citizenPortal: "குடிமக்கள் சட்ட உதவி தளம்",
      refPrefix: "குறிப்பு எண்:",
      legalStatusOf: "சட்டப்பூர்வ நிலை:",
      welcome: "வரவேற்கிறோம்,",
      statutoryRight: "இந்திய அரசியலமைப்பின் 39A பிரிவு மற்றும் பாரதிய நாகரிக் சுரக்ஷா சன்ஹிதா (BNSS), 2023 இன் பிரிவு 479 இன் கீழ், நீங்கள் இலவச சட்ட உதவி மற்றும் நீதிமன்ற காவல் மறுஆய்வுக்கு தகுதியுடையவர்.",
    },
    statusBadges: {
      underReview: "ஆரம்ப பரிசீலனையில் உள்ளது",
      eligible479: "பிரிவு 479 இன் கீழ் தகுதி",
      counselAssigned: "வழக்கறிஞர் நியமிக்கப்பட்டார்",
      readyForFiling: "வரைவு அங்கீகரிக்கப்பட்டது • தாக்கல் நிலுவை",
      filedInCourt: "நீதிமன்றத்தில் தாக்கல் செய்யப்பட்டது",
      courtOrderReceived: "நீதிமன்ற ஜாமீன் ஆணை வழங்கப்பட்டது",
      releaseExecuted: "சிறை விடுதலை நிறைவேற்றப்பட்டது",
    },
    cards: {
      legalAidStatusTitle: "சட்ட உதவி நிலை",
      assignedLawyerTitle: "நியமிக்கப்பட்ட வழக்கறிஞர்",
      counselInProgress: "வழக்கறிஞர் நியமனம் நடைபெறுகிறது",
      freeDlsaDesk: "இலவச DLSA சட்ட உதவி மையம்",
      nextHearingTitle: "அடுத்த நீதிமன்ற விசாரணை",
      awaitingSchedule: "தேதி எதிர்பார்க்கப்படுகிறது",
      courtRecordBadge: "அதிகாரப்பூர்வ நீதிமன்ற பதிவு",
    },
    procedural: {
      courtFilingTitle: "நீதிமன்ற தாக்கல் நிலை",
      filingRecord: "தாக்கல் பதிவு:",
      formallyLodged: "முறையாக தாக்கல் செய்யப்பட்டது",
      awaitingSubmission: "சமர்ப்பிக்கப்பட வேண்டியுள்ளது",
      reference: "குறிப்பு:",
      jurisdiction: "நீதித்துறை வரம்பு:",
      custodyReleaseTitle: "காவல் மற்றும் விடுதலை நிலை",
      custodyStatus: "காவல் நிலை:",
      inCustody: "நீதிமன்ற காவலில் உள்ளார்",
      policeStation: "காவல் நிலையம்:",
      verification: "சரிபார்ப்பு:",
    },
    aiSection: {
      inspectAuthoritative: "அதிகாரப்பூர்வ ஆங்கிலத்தைப் பார்க்கவும்",
      showDerived: "மொழிபெயர்ப்பைப் பார்க்கவும்",
      statutoryCautionTitle: "சட்டப்பூர்வ எச்சரிக்கை",
    },
    missingDocs: {
      title: "உங்களிடமிருந்து தேவைப்படும் ஆவணங்கள்",
      actionRequired: "நடவடிக்கை தேவை",
      subtitle: "ஜாமீன் மனு தாக்கல் செய்ய சட்ட உதவி வழக்கறிஞருக்கு உதவ இந்த ஆவணங்களை தயார் செய்யவும்:",
      urgent: "அவசரம்",
      supporting: "ஆதரவு ஆவணம்",
      whyNeeded: "ஏன் தேவை:",
      howToSubmit: "எவ்வாறு சமர்ப்பிக்க வேண்டும்:",
    },
    entitledDocs: {
      title: "சரிபார்க்கப்பட்ட வழக்கு பதிவுகள்",
      authorizedSuffix: "அங்கீகரிக்கப்பட்டது",
      subtitle: "சட்ட சேவைகள் ஆணையத்தால் சரிபார்க்கப்பட்ட அதிகாரப்பூர்வ பதிவுகள்:",
      verified: "சரிபார்க்கப்பட்டது",
      size: "அளவு:",
      textSummaryBtn: "சுருக்கம்",
      provenanceBtn: "ஆதார சான்று",
    },
    actionCenter: {
      title: "குடிமக்கள் செயல் மையம்",
      auditableDesk: "DLSA மையம்",
      subtitle: "DLSA செயலாளர் மற்றும் சிறை நல அலுவலருக்கு நேரடியாக அதிகாரப்பூர்வ கோரிக்கைகளை சமர்ப்பிக்கவும்:",
      contactCounselTitle: "DLSA வழக்கறிஞரைத் தொடர்பு கொள்ளவும்",
      contactCounselSub: "வழக்கறிஞருடன் ஆலோசனை கோருதல்",
      flagDiscrepancyTitle: "முரண்பாட்டை தெரிவிக்கவும்",
      flagDiscrepancySub: "தவறான தேதிகள் அல்லது விவரங்களை தெரிவிக்கவும்",
      requestDocTitle: "ஆவண நகல் கோருதல்",
      requestDocSub: "சான்றளிக்கப்பட்ட ஆணை அல்லது அறிக்கை நகல்",
      askHelpTitle: "சட்ட உதவி கேட்கவும்",
      askHelpSub: "அவசர நல்வாழ்வு / மருத்துவ உதவி",
      pastSubmissionsTitle: "உங்கள் முந்தைய கோரிக்கைகள்",
      trackingId: "கண்காணிப்பு ஐடி:",
    },
    nalsaBanner: {
      title: "தேசிய சட்ட சேவைகள் உதவி எண் (NALSA 24x7)",
      desc: "விசாரணை கைதிகள் மற்றும் குடும்பங்களுக்கான இலவச அரசு உதவி எண்.",
      phoneBtn: "15100 (கட்டணமில்லா எண்)",
    },
    actionModal: {
      title: "குடிமக்கள் கோரிக்கையை சமர்ப்பிக்கவும்",
      requestType: "கோரிக்கை வகை",
      optContact: "DLSA வழக்கறிஞர் தொடர்பு கோரிக்கை",
      optDiscrepancy: "பதிவுகளில் முரண்பாட்டை தெரிவிக்கவும்",
      optDoc: "சான்றளிக்கப்பட்ட ஆவண நகல் கோருதல்",
      optHelp: "அவசர சட்ட உதவி கோருதல்",
      fieldLabel: "முரண்பாடு உள்ள புலம்",
      fieldCustody: "காவல் காலம் / சேர்க்கை தேதி",
      fieldParent: "பெற்றோர் / பாதுகாவலர் பெயர்",
      fieldAddress: "நிரந்தர முகவரி",
      fieldOffense: "பதிவு செய்யப்பட்ட குற்றப் பிரிவுகள்",
      docLabel: "கோரப்பட்ட ஆவணம்",
      docChargeSheet: "காவல்துறை குற்றப்பத்திரிகை",
      docRemand: "நீதிமன்ற காவல் ஆணை",
      docFir: "முதல் தகவல் அறிக்கை (FIR)",
      docCustodyCert: "சிறை காவல் சான்றிதழ்",
      subjectLabel: "பொருள்",
      subjectPlaceholder: "உங்கள் தேவையின் சுருக்கம்...",
      detailsLabel: "விவரங்கள்",
      detailsPlaceholder: "DLSA மையத்திற்கான குறிப்பிட்ட விவரங்கள்...",
      cancelBtn: "ரத்து செய்",
      submitBtn: "DLSA க்கு சமர்ப்பிக்கவும்",
      submitting: "சமர்ப்பிக்கப்படுகிறது...",
      doneBtn: "முடிந்தது",
      successMsg: "கோரிக்கை வெற்றிகரமாக DLSA மையத்திற்கு சமர்ப்பிக்கப்பட்டது.",
    },
    notifModal: {
      title: "அறிவிப்பு விருப்பத்தேர்வுகள் மற்றும் ஒப்புதல்",
      phoneLabel: "பதிவுசெய்யப்பட்ட மொபைல் எண்",
      smsLabel: "SMS மூலம் விசாரணை மற்றும் நிலை அறிவிப்புகள்",
      whatsappLabel: "வாட்ஸ்அப் சட்ட உதவி அறிவிப்புகள்",
      inAppLabel: "செயலி வழி அறிவிப்புகள்",
      statutoryNoticeLabel: "சட்டப்பூர்வ அறிவிப்பு:",
      statutoryNoticeText: "சட்ட சேவைகள் அதிகாரசபை சட்டம், 1987 இன் கீழ் அறிவிப்புகள் பதிவு செய்யப்படுகின்றன.",
      closeBtn: "மூடு",
      saveBtn: "விருப்பங்களைச் சேமிக்கவும்",
      saving: "சேமிக்கப்படுகிறது...",
      savedMsg: "விருப்பத்தேர்வுகள் வெற்றிகரமாக புதுப்பிக்கப்பட்டன.",
    },
    textSummaryModal: {
      recordType: "பதிவு வகை:",
      size: "அளவு:",
      summaryLabel: "எளிய மொழி சுருக்கம்:",
      syncing: "ஒத்திசைக்கப்படுகிறது...",
      extractLabel: "ஆவண சுருக்கம்:",
      certNotice: "இந்த ஆவணம் சட்ட சேவைகள் ஆணையத்தால் சான்றளிக்கப்பட்டது.",
      closeBtn: "மூடு",
    },
    emptyStates: {
      loadingRecord: "அங்கீகரிக்கப்பட்ட சட்ட உதவி பதிவு ஏற்றப்படுகிறது...",
      noActiveCase: "இந்தக் கணக்கில் எந்த வழக்கும் இணைக்கப்படவில்லை",
      noCaseDesc: "உங்களின் விவரங்களுடன் தற்போது எந்த சட்ட உதவி வழக்கும் இணைக்கப்படவில்லை. உதவிக்கு 15100 ஐ அழைக்கவும்.",
      callNalsa: "NALSA உதவி எண்ணை அழைக்கவும்: 15100",
      tollFreeLabel: "24x7 கட்டணமில்லா இலவச சட்ட உதவி",
    },
  },

  mr: {
    topBar: {
      languageLabel: "भाषा:",
      offline: "ऑफलाइन",
      online: "ऑनलाइन",
      synced: "सिंक केले",
      lowDataOn: "⚡ कमी डेटा: चालू",
      lowDataOff: "कमी डेटा: बंद",
      notifPrefsTitle: "सूचना प्राधान्ये आणि संमती",
    },
    derivedNotice: {
      label: "माहिती व सुलभता सूचना:",
      text: "भाषांतरित मजकूर माहितीच्या सुलभतेसाठी प्रदान केला आहे. मूळ इंग्रजी न्यायालयीन दस्तऐवज कायदेशीर सत्याचा अधिकृत स्रोत राहील.",
    },
    banner: {
      familyPortal: "कुटुंब व पालक साहाय्य पोर्टल",
      citizenPortal: "नागरिक विधी साहाय्य पोर्टल",
      refPrefix: "संदर्भ क्रमांक:",
      legalStatusOf: "कायदेशीर स्थिती:",
      welcome: "स्वागत आहे,",
      statutoryRight: "भारतीय संविधानाच्या अनुच्छेद 39A आणि भारतीय नागरिक सुरक्षा संहिता (BNSS), 2023 च्या कलम 479 अन्वये, आपण विनामूल्य विधी साहाय्य आणि न्यायालयीन कोठडीच्या नियतकालिक पुनरावलोकनासाठी पात्र आहात.",
    },
    statusBadges: {
      underReview: "प्रारंभिक पुनरावलोकनाधीन",
      eligible479: "कलम 479 अन्वये पात्र",
      counselAssigned: "वकील नियुक्त",
      readyForFiling: "मसुदा मंजूर • दाखल करणे बाकी",
      filedInCourt: "न्यायालयात दाखल",
      courtOrderReceived: "न्यायालय जामीन आदेश जारी",
      releaseExecuted: "तुरुंगातून सुटका अंमलात",
    },
    cards: {
      legalAidStatusTitle: "विधी साहाय्य स्थिती",
      assignedLawyerTitle: "नियुक्त बचाव वकील",
      counselInProgress: "वकील वाटप प्रक्रिया सुरू आहे",
      freeDlsaDesk: "मोफत डीएलएसए विधी साहाय्य कक्ष",
      nextHearingTitle: "पुढील न्यायालयीन सुनावणी",
      awaitingSchedule: "तारीख प्रतीक्षेत",
      courtRecordBadge: "अधिकृत न्यायालयीन नोंद",
    },
    procedural: {
      courtFilingTitle: "न्यायालय दाखल स्थिती",
      filingRecord: "दाखल नोंद:",
      formallyLodged: "औपचारिकपणे दाखल",
      awaitingSubmission: "सादर करणे बाकी",
      reference: "संदर्भ:",
      jurisdiction: "अधिकारक्षेत्र:",
      custodyReleaseTitle: "कोठडी व सुटका स्थिती",
      custodyStatus: "कोठडी स्थिती:",
      inCustody: "न्यायालयीन कोठडीत",
      policeStation: "पोलीस ठाणे:",
      verification: "पडताळणी:",
    },
    aiSection: {
      inspectAuthoritative: "अधिकृत इंग्रजी पहा",
      showDerived: "भाषांतरित माहिती पहा",
      statutoryCautionTitle: "वैधानिक सूचना",
    },
    missingDocs: {
      title: "आपल्याकडून आवश्यक कागदपत्रे",
      actionRequired: "कारवाई आवश्यक",
      subtitle: "जामीन अर्जाच्या प्रक्रियेत वकिलांना मदत करण्यासाठी कृपया खालील कागदपत्रे तयार ठेवा:",
      urgent: "तातडीचे",
      supporting: "पूरक",
      whyNeeded: "का आवश्यक आहे:",
      howToSubmit: "कसे सादर करावे:",
    },
    entitledDocs: {
      title: "सत्यापित केस रेकॉर्ड्स (हक्क)",
      authorizedSuffix: "अधिकृत",
      subtitle: "विधी सेवा प्राधिकरणाद्वारे सत्यापित अधिकृत नोंदी:",
      verified: "सत्यापित",
      size: "आकार:",
      textSummaryBtn: "मजकूर सारांश",
      provenanceBtn: "स्रोत पुरावा",
    },
    actionCenter: {
      title: "नागरिक कृती केंद्र",
      auditableDesk: "डीएलएसए कक्ष",
      subtitle: "डीएलएसए सचिव आणि तुरुंग कल्याण अधिकाऱ्यांना थेट अधिकृत विनंत्या पाठवा:",
      contactCounselTitle: "डीएलएसए वकिलांशी संपर्क साधा",
      contactCounselSub: "पॅनेल वकिलांशी सल्लामसलतीची विनंती",
      flagDiscrepancyTitle: "तफावत नोंदवा",
      flagDiscrepancySub: "चुकीच्या तारखा किंवा तपशील कळवा",
      requestDocTitle: "कागदपत्राची प्रत मागा",
      requestDocSub: "प्रमाणित आदेश किंवा अहवाल प्रत",
      askHelpTitle: "विधी साहाय्य मागा",
      askHelpSub: "तातडीची वैद्यकीय / कायदेशीर मदत",
      pastSubmissionsTitle: "आपल्या मागील विनंत्या",
      trackingId: "ट्रॅकिंग आयडी:",
    },
    nalsaBanner: {
      title: "राष्ट्रीय विधी सेवा हेल्पलाइन (नालसा 24x7)",
      desc: "न्यायाधीन बंदी आणि कुटुंबीयांसाठी मोफत सरकारी हेल्पलाइन.",
      phoneBtn: "15100 (टोल-फ्री)",
    },
    actionModal: {
      title: "नागरिक विनंती सादर करा",
      requestType: "विनंतीचा प्रकार",
      optContact: "डीएलएसए पॅनेल वकील संपर्क विनंती",
      optDiscrepancy: "रेकॉर्डमधील तफावत / त्रुटी कळवा",
      optDoc: "प्रमाणित दस्तऐवज प्रत विनंती",
      optHelp: "तातडीच्या विधी साहाय्याची विनंती",
      fieldLabel: "तफावत असलेले फील्ड",
      fieldCustody: "कोठडी कालावधी / दाखल तारीख",
      fieldParent: "पालकांचे नाव",
      fieldAddress: "कायमचा पत्ता",
      fieldOffense: "नोंदवलेली गुन्हे कलमे",
      docLabel: "मागितलेले कागदपत्र",
      docChargeSheet: "पोलीस आरोपपत्र (चार्जशीट)",
      docRemand: "न्यायालयीन रिमांड आदेश",
      docFir: "एफआयआर (FIR)",
      docCustodyCert: "तुरुंग कोठडी प्रमाणपत्र",
      subjectLabel: "विषय",
      subjectPlaceholder: "आपल्या गरजेचा संक्षिप्त सारांश...",
      detailsLabel: "तपशील",
      detailsPlaceholder: "डीएलएसए कक्षासाठी आवश्यक सविस्तर माहिती द्या...",
      cancelBtn: "रद्द करा",
      submitBtn: "डीएलएसए कडे पाठवा",
      submitting: "सादर करत आहे...",
      doneBtn: "पूर्ण",
      successMsg: "विनंती यशस्वीरित्या डीएलएसए कक्षाकडे पाठवली गेली आहे.",
    },
    notifModal: {
      title: "सूचना प्राधान्ये आणि संमती",
      phoneLabel: "नोंदणीकृत मोबाइल क्रमांक",
      smsLabel: "एसएमएस द्वारे सुनावणी आणि स्थिती सूचना",
      whatsappLabel: "व्हॉट्सॲप विधी साहाय्य सूचना",
      inAppLabel: "ॲपमधील सूचना",
      statutoryNoticeLabel: "वैधानिक सूचना:",
      statutoryNoticeText: "विधी सेवा प्राधिकरण कायदा, 1987 अन्वये सूचनांची नोंद ठेवली जाते.",
      closeBtn: "बंद करा",
      saveBtn: "प्राधान्ये जतन करा",
      saving: "जतन करत आहे...",
      savedMsg: "प्राधान्ये यशस्वीरित्या अद्यतनित केली गेली.",
    },
    textSummaryModal: {
      recordType: "रेकॉर्ड प्रकार:",
      size: "आकार:",
      summaryLabel: "सोप्या भाषेतील सारांश:",
      syncing: "सिंक होत आहे...",
      extractLabel: "दस्तऐवज सारांश:",
      certNotice: "हे दस्तऐवज विधी सेवा प्राधिकरणाद्वारे प्रमाणित आहे.",
      closeBtn: "बंद करा",
    },
    emptyStates: {
      loadingRecord: "अधिकृत विधी साहाय्य रेकॉर्ड लोड होत आहे...",
      noActiveCase: "या खात्याशी कोणतीही सक्रिय केस जोडलेली नाही",
      noCaseDesc: "आपल्या खात्याशी कोणतीही सक्रिय केस जोडलेली नाही. मदतीसाठी 15100 वर कॉल करा.",
      callNalsa: "नालसा हेल्पलाइनवर कॉल करा: 15100",
      tollFreeLabel: "24x7 टोल-फ्री मोफत विधी साहाय्य",
    },
  },

  bn: {
    topBar: {
      languageLabel: "ভাষা:",
      offline: "অফলাইন",
      online: "অনলাইন",
      synced: "সিঙ্ক হয়েছে",
      lowDataOn: "⚡ কম ডেটা: চালু",
      lowDataOff: "কম ডেটা: বন্ধ",
      notifPrefsTitle: "বিজ্ঞপ্তি পছন্দ ও সম্মতি",
    },
    derivedNotice: {
      label: "অ্যাক্সেসযোগ্যতা বিজ্ঞপ্তি:",
      text: "অনূদিত পাঠ্যটি তথ্যগত সুবিধার জন্য প্রদত্ত একটি ব্যুৎপন্ন প্রদর্শন। মূল ইংরেজি আদালতের ডকেটটি আইনি সত্যের প্রামাণিক উৎস হিসেবে থাকবে।",
    },
    banner: {
      familyPortal: "পরিবার ও অভিভাবক সহায়তা পোর্টাল",
      citizenPortal: "নাগরিক আইনি সহায়তা পোর্টাল",
      refPrefix: "রেফারেন্স নং:",
      legalStatusOf: "আইনি অবস্থা:",
      welcome: "স্বাগতম,",
      statutoryRight: "ভারতের সংবিধানের অনুচ্ছেদ 39A এবং ভারতীয় নাগরিক সুরক্ষা সংহিতা (BNSS), 2023-এর ধারা 479-এর অধীনে, আপনি বিনামূল্যে আইনি সহায়তা এবং পর্যায়ক্রমিক বিচারিক হেফাজত পর্যালোচনার অধিকারী।",
    },
    statusBadges: {
      underReview: "প্রাথমিক পর্যালোচনাধীন",
      eligible479: "ধারা 479-এর অধীনে যোগ্য",
      counselAssigned: "আইনজীবী নিযুক্ত",
      readyForFiling: "খসড়া অনুমোদিত • দাখিল বাকি",
      filedInCourt: "আদালতে দাখিল করা হয়েছে",
      courtOrderReceived: "আদালতের জামিন আদেশ জারি",
      releaseExecuted: "কারাগার থেকে মুক্তি সম্পন্ন",
    },
    cards: {
      legalAidStatusTitle: "আইনি সহায়তার অবস্থা",
      assignedLawyerTitle: "নিযুক্ত আইনজীবী",
      counselInProgress: "আইনজীবী বরাদ্দ প্রক্রিয়াধীন",
      freeDlsaDesk: "বিনামূল্যে ডিএলএসএ আইনি সহায়তা কেন্দ্র",
      nextHearingTitle: "পরবর্তী আদালত শুনানি",
      awaitingSchedule: "তারিখ প্রতীক্ষিত",
      courtRecordBadge: "প্রামাণিক আদালত রেকর্ড",
    },
    procedural: {
      courtFilingTitle: "আদালত দাখিল অবস্থা",
      filingRecord: "দাখিল রেকর্ড:",
      formallyLodged: "আনুষ্ঠানিকভাবে দাখিল",
      awaitingSubmission: "জমা দেওয়া বাকি",
      reference: "রেফারেন্স:",
      jurisdiction: "এখতিয়ার:",
      custodyReleaseTitle: "হেফাজত ও মুক্তি অবস্থা",
      custodyStatus: "হেফাজতের অবস্থা:",
      inCustody: "বিচারিক হেফাজতে আছেন",
      policeStation: "থানা:",
      verification: "যাচাইকরণ:",
    },
    aiSection: {
      inspectAuthoritative: "প্রামাণিক ইংরেজি দেখুন",
      showDerived: "অনূদিত বিবরণ দেখুন",
      statutoryCautionTitle: "সংবিধিবদ্ধ সতর্কতা",
    },
    missingDocs: {
      title: "আপনার পক্ষ থেকে প্রয়োজনীয় নথি",
      actionRequired: "পদক্ষেপ প্রয়োজন",
      subtitle: "জামিনের আবেদন প্রক্রিয়ায় আইনি সহায়তা আইনজীবীকে সহায়তা করার জন্য অনুগ্রহ করে এই নথিগুলি প্রস্তুত করুন:",
      urgent: "জরুরি",
      supporting: "সহায়ক",
      whyNeeded: "কেন প্রয়োজন:",
      howToSubmit: "কীভাবে জমা দেবেন:",
    },
    entitledDocs: {
      title: "যাচাইকৃত মামলার রেকর্ড",
      authorizedSuffix: "অনুমোদিত",
      subtitle: "আইন সেবা কর্তৃপক্ষ কর্তৃক যাচাইকৃত প্রামাণিক রেকর্ড:",
      verified: "যাচাইকৃত",
      size: "আকার:",
      textSummaryBtn: "সংক্ষিপ্ত বিবরণ",
      provenanceBtn: "উৎস প্রমাণ",
    },
    actionCenter: {
      title: "নাগরিক পদক্ষেপ কেন্দ্র",
      auditableDesk: "ডিএলএসএ কেন্দ্র",
      subtitle: "ডিএলএসএ সচিব এবং জেল কল্যাণ কর্মকর্তার কাছে সরাসরি দাপ্তরিক অনুরোধ জমা দিন:",
      contactCounselTitle: "ডিএলএসএ আইনজীবীর সাথে যোগাযোগ",
      contactCounselSub: "আইনজীবীর সাথে পরামর্শের অনুরোধ",
      flagDiscrepancyTitle: "ত্রুটি বা অসঙ্গতি জানান",
      flagDiscrepancySub: "ভুল তারিখ বা তথ্য সংশোধন করুন",
      requestDocTitle: "নথির অনুলিপির অনুরোধ",
      requestDocSub: "প্রমাণিত আদেশ বা রিপোর্টের অনুলিপি",
      askHelpTitle: "আইনি সাহায্য চান",
      askHelpSub: "জরুরি কল্যাণ / চিকিৎসা সহায়তা",
      pastSubmissionsTitle: "আপনার পূর্ববর্তী আবেদনগুলি",
      trackingId: "ট্র্যাকিং আইডি:",
    },
    nalsaBanner: {
      title: "জাতীয় আইনি পরিষেবা হেল্পলাইন (নালসা 24x7)",
      desc: "আইনি পরিষেবা কর্তৃপক্ষ আইনের অধীনে বিচারাধীন বন্দি এবং পরিবারের জন্য বিনামূল্যে সরকারি হেল্পলাইন।",
      phoneBtn: "15100 (টোল-ফ্রি)",
    },
    actionModal: {
      title: "নাগরিক আবেদন জমা দিন",
      requestType: "আবেদনের ধরন",
      optContact: "ডিএলএসএ আইনজীবীর সাথে যোগাযোগের অনুরোধ",
      optDiscrepancy: "রেকর্ডে অমিল বা ত্রুটি জানান",
      optDoc: "প্রমাণিত নথির অনুলিপির অনুরোধ",
      optHelp: "জরুরি আইনি সহায়তার অনুরোধ",
      fieldLabel: "ত্রুটিপূর্ণ ক্ষেত্র",
      fieldCustody: "হেফাজতের সময়কাল / ভর্তির তারিখ",
      fieldParent: "পিতা-মাতা / অভিভাবকের নাম",
      fieldAddress: "স্থায়ী ঠিকানা",
      fieldOffense: "রেকর্ডকৃত অপরাধ ধারা",
      docLabel: "অনুরোধকৃত নথি",
      docChargeSheet: "পুলিশ চার্জশিট",
      docRemand: "বিচারিক রিমান্ড আদেশ",
      docFir: "এফআইআর (FIR)",
      docCustodyCert: "কারাগার হেফাজত সনদ",
      subjectLabel: "বিষয়",
      subjectPlaceholder: "আপনার প্রয়োজনের সংক্ষিপ্ত বিবরণ...",
      detailsLabel: "বিস্তারিত",
      detailsPlaceholder: "ডিএলএসএ ডেস্কের জন্য প্রয়োজনীয় বিস্তারিত তথ্য দিন...",
      cancelBtn: "বাতিল",
      submitBtn: "ডিএলএসএ-তে জমা দিন",
      submitting: "জমা দেওয়া হচ্ছে...",
      doneBtn: "সম্পন্ন",
      successMsg: "অনুরোধটি সফলভাবে ডিএলএসএ ডেস্কে জমা দেওয়া হয়েছে।",
    },
    notifModal: {
      title: "বিজ্ঞপ্তি পছন্দ ও সম্মতি",
      phoneLabel: "নিবন্ধিত মোবাইল নম্বর",
      smsLabel: "এসএমএসের মাধ্যমে শুনানি ও স্থিতি বিজ্ঞপ্তি",
      whatsappLabel: "হোয়াটসঅ্যাপ আইনি সহায়তা বিজ্ঞপ্তি",
      inAppLabel: "অ্যাপের ভেতরের বিজ্ঞপ্তি",
      statutoryNoticeLabel: "সংবিধিবদ্ধ বিজ্ঞপ্তি:",
      statutoryNoticeText: "আইনি পরিষেবা কর্তৃপক্ষ আইন, 1987-এর অধীনে বিজ্ঞপ্তি বিতরণ রেকর্ড করা হয়।",
      closeBtn: "বন্ধ করুন",
      saveBtn: "পছন্দ সংরক্ষণ করুন",
      saving: "সংরক্ষণ করা হচ্ছে...",
      savedMsg: "পছন্দ ও সম্মতি সফলভাবে আপডেট করা হয়েছে।",
    },
    textSummaryModal: {
      recordType: "রেকর্ডের ধরন:",
      size: "আকার:",
      summaryLabel: "সহজ ভাষার সারসংক্ষেপ:",
      syncing: "সিঙ্ক হচ্ছে...",
      extractLabel: "নথির সারসংক্ষেপ:",
      certNotice: "এই নথিটি আইনি পরিষেবা কর্তৃপক্ষ কর্তৃক প্রত্যয়িত।",
      closeBtn: "বন্ধ করুন",
    },
    emptyStates: {
      loadingRecord: "অনুমোদিত আইনি সহায়তা রেকর্ড লোড হচ্ছে...",
      noActiveCase: "এই অ্যাকাউন্টের সাথে কোনো সক্রিয় মামলা যুক্ত নেই",
      noCaseDesc: "আপনার তথ্যের সাথে বর্তমানে কোনো সক্রিয় আইনি সহায়তা মামলা যুক্ত নেই। সহায়তার জন্য 15100 নম্বরে কল করুন।",
      callNalsa: "নালসা হেল্পলাইনে কল করুন: 15100",
      tollFreeLabel: "24x7 টোল-ফ্রি বিনামূল্যে আইনি সহায়তা",
    },
  },
};

export function getCitizenTranslation(langCode: string): CitizenPortalTranslation {
  return CITIZEN_PORTAL_I18N[langCode] || CITIZEN_PORTAL_I18N["en"];
}
