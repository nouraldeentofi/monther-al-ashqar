#!/usr/bin/env python3
"""Build Monther Al-Ashqar's site as crawlable static pages.

Reads monther-portfolio.html (the single-file source), renders every page in
English and Arabic with a headless browser, and writes ./site with:
  - one real HTML page per section and per project, in both languages
  - search and AI metadata: titles, descriptions, canonical, hreflang, Open Graph
  - schema.org JSON-LD (Person, WebSite, ProfilePage, FAQPage, breadcrumbs)
  - llms.txt and llms-full.txt (plain-language profile for AI assistants)
  - robots.txt (open to search engines and AI crawlers) and sitemap.xml

Set SITE_URL to the final domain before building.
Run:  python3 build.py
"""
import html, json, os, posixpath, re, shutil
from playwright.sync_api import sync_playwright

SITE_URL = "https://nouraldeentofi.github.io/monther-al-ashqar"   # change to his own domain later, no trailing slash

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "monther-portfolio.html")
OUT = os.path.join(HERE, "site")

NAME_EN, NAME_AR = "Monther Al-Ashqar", "منذر الأشقر"
LINKEDIN = "https://www.linkedin.com/in/montheral-ashqar/"
LINKEDIN_OLD = "https://www.linkedin.com/in/monther-al-ashqar-77543563/"

# Every spelling people are likely to type, in both scripts.
ALT_NAMES = [
    "Monther Al-Ashqar", "Monther Al Ashqar", "Monther Alashqar", "Monther AlAshqar", "Monther Ashqar",
    "Munther Al-Ashqar", "Munther Al Ashqar", "Munther Alashqar", "Munther Ashqar",
    "Monzer Al-Ashqar", "Monzer Alashqar", "Munzer Al-Ashqar", "Munzir Al-Ashqar", "Mondher Al-Ashqar",
    "Mounther Al-Ashqar", "Monthir Al-Ashqar", "Monther El-Ashqar", "Monther Elashqar",
    "Monther Al-Ashkar", "Munther Al-Ashkar", "Monther Alashkar", "Monther Al-Ashgar", "Monther Al-Ashqer",
    "Eng. Monther Al-Ashqar",
    "منذر الأشقر", "منذر الاشقر", "منذر أشقر", "منذر اشقر", "منذر الأشقر الأشقر",
    "منزر الأشقر", "منزر الاشقر", "منظر الأشقر", "مُنذر الأشقر",
    "المهندس منذر الأشقر", "م. منذر الأشقر",
]
ALT_NAMES = [n for n in dict.fromkeys(ALT_NAMES) if n != "منذر الأشقر الأشقر"]

SERVICES = [
    ("Project management", "إدارة المشاريع"),
    ("Programme and portfolio management", "إدارة البرامج والمحافظ"),
    ("Owner's representation", "تمثيل المالك"),
    ("Project management consultancy (PMC)", "استشارات إدارة المشاريع"),
    ("Technical and design management", "الإدارة الفنية والتصميمية"),
    ("FIDIC contract administration", "إدارة عقود فيديك FIDIC"),
    ("Claims, variations and extension of time", "المطالبات والأوامر التغييرية وتمديد المدة"),
    ("Delay analysis and programme recovery", "تحليل التأخير واستعادة البرنامج الزمني"),
    ("Project controls and earned value management", "ضبط المشاريع وإدارة القيمة المكتسبة"),
    ("Design coordination and BIM clash detection", "تنسيق التصميم وكشف التعارضات بـ BIM"),
    ("Value engineering and constructability reviews", "الهندسة القيمية ومراجعات قابلية التنفيذ"),
    ("Technical bid preparation", "إعداد العطاءات الفنية"),
    ("Construction supervision", "الإشراف على التنفيذ"),
    ("Commissioning and handover", "التشغيل والتسليم"),
]
KNOWS = [
    ("FIDIC", "فيديك"), ("Construction project management", "إدارة مشاريع البناء"), ("Mega-projects", "المشاريع الكبرى"),
    ("Civil engineering", "الهندسة المدنية"), ("Structural engineering", "الهندسة الإنشائية"), ("Marine works", "الأعمال البحرية"),
    ("Dredging and reclamation", "التجريف والردم"), ("Deep foundations", "الأساسات العميقة"), ("Infrastructure", "البنية التحتية"),
    ("Hospitality projects", "مشاريع الضيافة"), ("Healthcare facilities", "المنشآت الصحية"), ("Royal palaces", "القصور الملكية"),
    ("Risk management", "إدارة المخاطر"), ("Oracle Primavera", "بريمافيرا"), ("Earned value management", "القيمة المكتسبة"),
    ("BIM coordination", "تنسيق BIM"), ("Value engineering", "الهندسة القيمية"), ("Quality assurance and control", "ضبط الجودة وتوكيدها"),
    ("Authority approvals", "الموافقات الرسمية"), ("Stakeholder management", "إدارة أصحاب المصلحة"),
]
OCCUPATIONS = [
    ("Senior Project Manager", "مدير مشاريع أول"), ("Owner's Representative", "ممثل المالك"),
    ("Technical & Design Manager", "مدير فني وتصميم"), ("Project Manager", "مدير مشروع"),
    ("Construction Project Manager", "مدير مشاريع إنشائية"), ("Resident Engineer", "مهندس مقيم"),
    ("Civil Engineer", "مهندس مدني"),
]

PAGE_META = {
    "home": (
        "Monther Al-Ashqar (منذر الأشقر), Senior Project Manager and Owner's Representative in Doha, Qatar. 30 years on GCC mega-projects, QR 5.8B+ delivered. FIDIC, claims, project controls. PMP, PMI-RMP, UPDA Grade A.",
        "منذر الأشقر (Monther Al-Ashqar)، مدير مشاريع أول وممثل للمالك في الدوحة، قطر. 30 عاماً في المشاريع الخليجية الكبرى، ومشاريع بأكثر من 5.8 مليار ريال قطري. عقود FIDIC والمطالبات وضبط المشاريع."),
    "experience": (
        "Monther Al-Ashqar's experience: 23 years with Dar Al-Handasah in Doha, from site engineer to Acting Senior Project Manager, and Technical & Design Manager at MACC in Riyadh.",
        "خبرة منذر الأشقر: 23 عاماً في دار الهندسة بالدوحة من مهندس موقع إلى مدير مشاريع أول بالإنابة، ومدير فني وتصميم لدى MACC في الرياض."),
    "projects": (
        "Projects managed by Monther Al-Ashqar in Qatar and Saudi Arabia: Salwa Beach Resort, Old Doha Port, Gewan Island, Doha Expo 2023, The Pearl-Qatar, Royal Palaces in Riyadh and more.",
        "مشاريع أدارها منذر الأشقر في قطر والسعودية: منتجع شاطئ سلوى، ميناء الدوحة القديم، جزيرة جيوان، إكسبو الدوحة 2023، جزيرة اللؤلؤة، والقصور الملكية في الرياض."),
    "credentials": (
        "Monther Al-Ashqar's registrations and certifications: UPDA Grade A (Qatar), Saudi Council of Engineers, PMP, PMI-RMP, PMI-ACP, P3O, M_o_R, with recognition from Ashghal and the Supreme Committee.",
        "اعتمادات منذر الأشقر: تسجيل UPDA الفئة A في قطر، والهيئة السعودية للمهندسين، وشهادات PMP وPMI-RMP وPMI-ACP وP3O وM_o_R، وتقدير من أشغال واللجنة العليا."),
    "notes": (
        "Field notes by Monther Al-Ashqar: short observations from thirty years on site, in Arabic and English, on consultants, contractors, authority and approvals.",
        "ملاحظات منذر الأشقر من الموقع: أفكار قصيرة من ثلاثين عاماً بين المالك والاستشاري والمقاول، بالعربية والإنجليزية."),
    "contact": (
        "Contact Monther Al-Ashqar, Senior Project Manager in Doha, Qatar: email montherashqar@gmail.com, phone and WhatsApp +974 6652 8836, LinkedIn.",
        "تواصل مع منذر الأشقر، مدير مشاريع أول في الدوحة: البريد montherashqar@gmail.com، الهاتف وواتساب ‎+974 6652 8836، وLinkedIn."),
}
SECTION_PATH = {"home": "", "experience": "experience/", "projects": "projects/", "credentials": "credentials/",
                "notes": "field-notes/", "contact": "contact/"}
SECTION_NAME = {"home": ("Home", "الرئيسية"), "experience": ("Experience", "الخبرة"), "projects": ("Projects", "المشاريع"),
                "credentials": ("Credentials", "الاعتمادات"), "notes": ("Field notes", "من الموقع"), "contact": ("Contact", "تواصل")}

FAQ_EN = [
    ("Who is Monther Al-Ashqar?", "Monther Al-Ashqar (also written Munther Al-Ashqar; in Arabic منذر الأشقر) is a civil engineer and Senior Project Manager based in Doha, Qatar, with about 30 years on construction projects in Qatar and Saudi Arabia. He spent 23 years with Dar Al-Handasah, rising to Acting Senior Project Manager on the owner's side, then led technical and design delivery for MACC in Riyadh."),
    ("What does he do?", "Project and programme management, owner's representation, and technical and design management on mega-projects, including FIDIC contract administration, claims, variations, extension of time, delay analysis, programme recovery, EVM and project controls, design coordination, BIM clash detection, value engineering and technical bid preparation."),
    ("Which projects has he delivered?", "A QR 5.8 billion portfolio of ten projects at Dar Al-Handasah, including Salwa Beach Resort (QR 2.58B), Old Doha Port (QR 700M), Salwa's water and adventure park (QR 600M), Gewan Island marine works (QR 540M) and Doha Expo 2023 (QR 400M), plus The Pearl-Qatar marine works, Doha International Airport and the FIFA World Cup 2022 Fan Festival zone. At MACC he governed design on a Royal Palaces programme worth over SAR 5 billion."),
    ("Is he registered to practise in Qatar and Saudi Arabia?", "Yes. He holds Grade A civil engineering supervision registration from Qatar's Ministry of Municipality (UPDA), engineer registration with the Saudi Council of Engineers, and membership of the Jordan Engineers Association."),
    ("Which certifications does he hold?", "PMP, PMI-RMP and PMI-ACP from the Project Management Institute, P3O and M_o_R Foundation from AXELOS, and ISO 9001, 14001 and 45001 internal auditor training."),
    ("How can I contact him?", "By email at montherashqar@gmail.com, by phone or WhatsApp on +974 6652 8836, or on LinkedIn at linkedin.com/in/montheral-ashqar."),
]
FAQ_AR = [
    ("من هو منذر الأشقر؟", "منذر الأشقر (ويُكتب بالإنجليزية Monther Al-Ashqar أو Munther Al-Ashqar) مهندس مدني ومدير مشاريع أول مقيم في الدوحة، قطر، بخبرة تقارب 30 عاماً في مشاريع البناء في قطر والسعودية. أمضى 23 عاماً في دار الهندسة حتى أصبح مدير مشاريع أول بالإنابة من جانب المالك، ثم قاد التسليم الفني والتصميمي لدى شركة MACC في الرياض."),
    ("ما مجال عمله؟", "إدارة المشاريع والبرامج، وتمثيل المالك، والإدارة الفنية والتصميمية للمشاريع الكبرى، بما في ذلك إدارة عقود FIDIC، وتقييم المطالبات والأوامر التغييرية وتمديد المدة، وتحليل التأخير واستعادة البرامج الزمنية، والقيمة المكتسبة وضبط المشاريع، وتنسيق التصميم، وكشف التعارضات بـ BIM، والهندسة القيمية، وإعداد العطاءات الفنية."),
    ("ما أبرز المشاريع التي أنجزها؟", "محفظة بقيمة 5.8 مليار ريال قطري من عشرة مشاريع في دار الهندسة، منها منتجع شاطئ سلوى (2.58 مليار)، وميناء الدوحة القديم (700 مليون)، وحديقة سلوى المائية (600 مليون)، والأعمال البحرية لجزيرة جيوان (540 مليون)، وإكسبو الدوحة 2023 (400 مليون)، إضافة إلى الأعمال البحرية لجزيرة اللؤلؤة ومطار الدوحة الدولي ومنطقة مهرجان المشجعين لكأس العالم 2022. وفي MACC تولّى حوكمة التصميم لبرنامج قصور ملكية تتجاوز قيمته 5 مليارات ريال سعودي."),
    ("هل هو مسجّل لممارسة المهنة في قطر والسعودية؟", "نعم. يحمل تسجيل الإشراف على الأعمال المدنية من الفئة A من وزارة البلدية في قطر (UPDA)، وتسجيل مهندس لدى الهيئة السعودية للمهندسين، وعضوية نقابة المهندسين الأردنيين."),
    ("ما الشهادات المهنية التي يحملها؟", "PMP وPMI-RMP وPMI-ACP من معهد إدارة المشاريع، وP3O وM_o_R Foundation من AXELOS، ودورة المدقق الداخلي لأنظمة ISO 9001 و14001 و45001."),
    ("كيف يمكن التواصل معه؟", "عبر البريد الإلكتروني montherashqar@gmail.com، أو بالهاتف وواتساب على +974 6652 8836، أو على LinkedIn: linkedin.com/in/montheral-ashqar."),
]


def rel(from_dir, to_path):
    """Relative link from a page directory ('ar/projects/x/') to a site path ('projects/')."""
    r = posixpath.relpath("/" + to_path, "/" + from_dir)
    if to_path == "" or to_path.endswith("/"):
        r = r.rstrip("/") + "/"
    return "./" if r in ("./", "/") else r


def page_path(route, lang):
    base = "ar/" if lang == "ar" else ""
    if route.startswith("p-"):
        return base + "projects/" + DATA["SLUG"][route[2:]] + "/"
    return base + SECTION_PATH[route]


def abs_url(path):
    return SITE_URL + "/" + path


def clip(text, n=158):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def person_ld(lang):
    D = DATA
    creds = []
    for g in D["C"]:
        for c in g["items"]:
            cred = {"@type": "EducationalOccupationalCredential", "name": c["n"][0],
                    "credentialCategory": "registration" if "Grade" in c["n"][0] or "Engineer" in c["n"][0] or c["n"][0] == "Member" else "certification",
                    "recognizedBy": {"@type": "Organization", "name": c["by"][0]}}
            if c.get("to"):
                cred["validUntil"] = f'{c["to"][0]}-{c["to"][1]:02d}'
            creds.append(cred)
    return {
        "@type": "Person", "@id": SITE_URL + "/#person",
        "name": NAME_AR if lang == "ar" else NAME_EN,
        "alternateName": ALT_NAMES,
        "givenName": "منذر" if lang == "ar" else "Monther",
        "familyName": "الأشقر" if lang == "ar" else "Al-Ashqar",
        "honorificPrefix": "Eng.",
        "jobTitle": [o[1] if lang == "ar" else o[0] for o in OCCUPATIONS[:3]],
        "description": PAGE_META["home"][1 if lang == "ar" else 0],
        "url": abs_url("ar/" if lang == "ar" else ""),
        "email": "mailto:montherashqar@gmail.com",
        "telephone": "+97466528836",
        "address": {"@type": "PostalAddress", "addressLocality": "Doha", "addressCountry": "QA"},
        "workLocation": [{"@type": "Place", "name": "Qatar"}, {"@type": "Place", "name": "Saudi Arabia"},
                         {"@type": "Place", "name": "Gulf Cooperation Council (GCC)"}],
        "knowsLanguage": [{"@type": "Language", "name": "Arabic", "alternateName": "ar"},
                          {"@type": "Language", "name": "English", "alternateName": "en"}],
        "knowsAbout": [k[0] for k in KNOWS] + [k[1] for k in KNOWS],
        "hasOccupation": [{"@type": "Occupation", "name": o[0], "alternateName": o[1],
                           "occupationLocation": [{"@type": "Country", "name": "Qatar"}, {"@type": "Country", "name": "Saudi Arabia"}],
                           "skills": ", ".join(s[0] for s in SERVICES[:8])} for o in OCCUPATIONS],
        "hasCredential": creds,
        "alumniOf": [
            {"@type": "CollegeOrUniversity", "name": "Al Isra University", "address": {"@type": "PostalAddress", "addressCountry": "JO"}},
            {"@type": "Organization", "name": "Dar Al-Handasah", "alternateName": "Dar"},
            {"@type": "Organization", "name": "Modern Architecture Contracting Company", "alternateName": "MACC"},
            {"@type": "Organization", "name": "Qatar Building Engineering Company", "alternateName": "QBEC"},
        ],
        "memberOf": {"@type": "Organization", "name": "Jordan Engineers Association"},
        "award": [r["n"][0] + ", " + r["by"][0] for r in D["R"]],
        "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": s[0], "alternateName": s[1],
                        "areaServed": ["Qatar", "Saudi Arabia", "GCC"], "provider": {"@id": SITE_URL + "/#person"}}} for s in SERVICES],
        "sameAs": [LINKEDIN, LINKEDIN_OLD],
        **({"image": abs_url(DATA["CONFIG"]["photo"])} if (DATA["CONFIG"].get("photo") or "").endswith((".jpg", ".jpeg", ".png", ".webp")) else {}),
    }


def page_ld(route, lang, title, desc, path):
    D = DATA
    graph = [person_ld(lang),
             {"@type": "WebSite", "@id": SITE_URL + "/#website", "url": SITE_URL + "/", "name": NAME_EN,
              "alternateName": [NAME_AR, "Munther Al-Ashqar", "Monther Alashqar"], "inLanguage": ["en", "ar"],
              "publisher": {"@id": SITE_URL + "/#person"}, "about": {"@id": SITE_URL + "/#person"}}]
    web = {"@type": "ProfilePage" if route == "home" else "WebPage", "@id": abs_url(path) + "#page", "url": abs_url(path),
           "name": title, "description": desc, "inLanguage": lang, "isPartOf": {"@id": SITE_URL + "/#website"},
           "about": {"@id": SITE_URL + "/#person"}, "dateModified": "2026-10-11"}
    if route == "home":
        web["mainEntity"] = {"@id": SITE_URL + "/#person"}
    crumbs = [{"@type": "ListItem", "position": 1, "name": SECTION_NAME["home"][1 if lang == "ar" else 0], "item": abs_url(page_path("home", lang))}]
    if route != "home":
        sec = "projects" if route.startswith("p-") else route
        crumbs.append({"@type": "ListItem", "position": 2, "name": SECTION_NAME[sec][1 if lang == "ar" else 0], "item": abs_url(page_path(sec, lang))})
        if route.startswith("p-"):
            crumbs.append({"@type": "ListItem", "position": 3, "name": title.split(" | ")[0], "item": abs_url(path)})
        graph.append({"@type": "BreadcrumbList", "itemListElement": crumbs})
    if route == "projects":
        web["mainEntity"] = {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": next(p for p in D["P"] if p["k"] == k)[lang]["n"],
             "url": abs_url(page_path("p-" + k, lang))} for i, k in enumerate(D["ORDER"])]}
    if route.startswith("p-"):
        k = route[2:]
        p = next(x for x in D["P"] if x["k"] == k)
        d = D["DETAIL"][k]
        li = 1 if lang == "ar" else 0
        web["mainEntity"] = {"@type": "CreativeWork", "additionalType": "https://schema.org/Project",
                             "name": p[lang]["n"], "description": d["ov"][li],
                             "locationCreated": {"@type": "Place", "name": d["place"][li]},
                             "temporalCoverage": f'{p["s"][0]}-{p["s"][1]:02d}/{p["e"][0]}-{p["e"][1]:02d}',
                             "contributor": {"@id": SITE_URL + "/#person"},
                             "keywords": ", ".join(x[li] for x in d["sc"])}
    graph.append(web)
    if route == "home":
        faq = FAQ_AR if lang == "ar" else FAQ_EN
        graph.append({"@type": "FAQPage", "@id": abs_url(path) + "#faq", "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    return {"@context": "https://schema.org", "@graph": graph}


def head_meta(route, lang, title, desc, path, alt_path):
    keywords = ", ".join(ALT_NAMES[:14] + [s[1 if lang == "ar" else 0] for s in SERVICES[:8]] +
                         (["الدوحة", "قطر", "السعودية", "الرياض"] if lang == "ar" else ["Doha", "Qatar", "Saudi Arabia", "Riyadh", "GCC"]))
    en_path = path if lang == "en" else alt_path
    ar_path = path if lang == "ar" else alt_path
    ld = json.dumps(page_ld(route, lang, title, desc, path), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    e = html.escape
    return f'''<meta name="description" content="{e(desc)}">
<meta name="author" content="{NAME_EN}">
<meta name="keywords" content="{e(keywords)}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<meta name="theme-color" content="#074247">
<link rel="canonical" href="{abs_url(path)}">
<link rel="alternate" hreflang="en" href="{abs_url(en_path)}">
<link rel="alternate" hreflang="ar" href="{abs_url(ar_path)}">
<link rel="alternate" hreflang="x-default" href="{abs_url(en_path)}">
<link rel="alternate" type="text/plain" title="Profile for AI assistants" href="{SITE_URL}/llms.txt">
<meta property="og:type" content="{'profile' if route == 'home' else 'website'}">
<meta property="og:site_name" content="{NAME_EN}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{abs_url(path)}">
<meta property="og:locale" content="{'ar_AR' if lang == 'ar' else 'en_US'}">
<meta property="og:locale:alternate" content="{'en_US' if lang == 'ar' else 'ar_AR'}">
<meta property="profile:first_name" content="Monther">
<meta property="profile:last_name" content="Al-Ashqar">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%23074247'/%3E%3Crect x='6' y='6' width='52' height='52' fill='none' stroke='%236EF8F9' stroke-width='3'/%3E%3Ctext x='32' y='41' font-family='Arial' font-weight='800' font-size='24' fill='%236EF8F9' text-anchor='middle'%3EMA%3C/text%3E%3C/svg%3E">
<script type="application/ld+json">{ld}</script>
'''


# ---------------------------------------------------------------- llms.txt
def llms_txt(routes):
    D = DATA
    L = [f"# {NAME_EN} ({NAME_AR})", "",
         f"> Civil engineer and Senior Project Manager / Owner's Representative based in Doha, Qatar, with about 30 years on GCC mega-projects in Qatar and Saudi Arabia (QR 5.8B+ portfolio at Dar Al-Handasah; SAR 5B+ Royal Palaces programme at MACC, Riyadh).",
         "", "Also written as: " + ", ".join(ALT_NAMES) + ".", "",
         "Services: " + "; ".join(s[0] for s in SERVICES) + ".", "",
         "Contact: montherashqar@gmail.com · +974 6652 8836 (phone and WhatsApp) · " + LINKEDIN, "",
         "## Pages", ""]
    for r in ["home", "experience", "projects", "credentials", "notes", "contact"]:
        L.append(f"- [{SECTION_NAME[r][0]}]({abs_url(page_path(r, 'en'))}): {PAGE_META[r][0]}")
    L += ["", "## Projects", ""]
    for k in D["ORDER"] + ["fifa", "dadu"]:
        p = next(x for x in D["P"] if x["k"] == k)
        v = f'{p["v"][0]}, ' if p.get("v") else ""
        L.append(f'- [{p["en"]["n"]}]({abs_url(page_path("p-" + k, "en"))}): {v}{D["ROLE"][p["role"]]["en"]}, {p["s"][0]}–{p["e"][0]}')
    L += ["", "## Arabic", "", f"- [الصفحة الرئيسية بالعربية]({abs_url('ar/')}): {PAGE_META['home'][1]}",
          "", "## Optional", "", f"- [Full profile in English and Arabic]({SITE_URL}/llms-full.txt)", ""]
    return "\n".join(L)


def months(s, e):
    return (e[0] - s[0]) * 12 + (e[1] - s[1]) + 1


MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def per(s, e):
    return f"{MON[s[1]-1]} {s[0]} – {MON[e[1]-1]} {e[0]}"


def llms_full():
    D = DATA
    L = [f"# {NAME_EN} — {NAME_AR}", "",
         "Civil engineer. Senior Project Manager, Owner's Representative and Technical & Design Manager. Based in Doha, Qatar. Projects in Qatar and Saudi Arabia.",
         "", "Also written as: " + ", ".join(ALT_NAMES) + ".", "",
         f"Website: {SITE_URL}/  ·  Arabic: {SITE_URL}/ar/  ·  LinkedIn: {LINKEDIN}",
         "Email: montherashqar@gmail.com (also montherashqar@yahoo.com)  ·  Phone and WhatsApp: +974 6652 8836", "",
         "## Summary", "",
         "About 30 years on construction sites in the GCC (1996–2025). 23 years with Dar Al-Handasah in Doha, from site engineer to Acting Senior Project Manager, administering FIDIC contracts on the owner's side across a QR 5.807B portfolio of ten projects. Then Technical & Design Manager at MACC in Riyadh (Dec 2024 – Dec 2025, fixed term, completed) on a Royal Palaces programme worth over SAR 5B, with three live sites, 13 concurrent tenders and a team of 50+ engineers: rework down 22%, design freeze six weeks earlier, milestone delivery up 25%, 100% of projects on track at handover.",
         "", "Positioning: consultant rigour applied to contractor execution. He has worked both sides of the table.", "",
         "## Services", ""] + [f"- {s[0]} ({s[1]})" for s in SERVICES] + ["", "## Experience", ""]
    for r in D["ROLES"]:
        L += [f"### {r['t'][0]} — {r['org'][0]}", f"{per(r['s'], r['e'])} · {r['place'][0]}", "", r["sum"][0], ""]
        L += [f"- {x[0]}" for x in r["pts"]] + [""]
    L += ["## Projects", ""]
    for k in D["ORDER"] + ["fifa", "dadu"]:
        p = next(x for x in D["P"] if x["k"] == k)
        d = D["DETAIL"][k]
        L += [f"### {p['en']['n']}", f"Value: {p['v'][0] if p.get('v') else 'not stated'} · Role: {D['ROLE'][p['role']]['en']} · {per(p['s'], p['e'])} · {d['place'][0]} · Employer: {D['EMP'][d['emp']][0]}",
              f"Page: {abs_url(page_path('p-' + k, 'en'))}", "", d["ov"][0], ""]
        L += [f"- {x[0]}" for x in d["sc"]] + [""]
    L += ["## Registrations and certifications", ""]
    for g in D["C"]:
        for c in g["items"]:
            extra = []
            if c.get("id"):
                extra.append("No. " + c["id"])
            if c.get("to"):
                extra.append(f'valid to {MON[c["to"][1]-1]} {c["to"][0]}')
            L.append(f'- {c["n"][0]} — {c["by"][0]}' + (" (" + ", ".join(extra) + ")" if extra else ""))
    L += ["", "## Recognition", ""] + [f'- {r["n"][0]}, {r["by"][0]} ({MON[r["d"][1]-1]} {r["d"][0]})' for r in D["R"]]
    L += ["", "## Education and languages", "", "- B.Sc. Civil Engineering, Al Isra University, Jordan (1996)", "- Arabic (native), English (full professional)",
          "", "## Field notes (LinkedIn articles)", ""] + [f"- {a['t']}" for a in D["ARTICLES"]]
    L += ["", "## Frequently asked", ""]
    for q, a in FAQ_EN:
        L += [f"**{q}**", a, ""]
    L += ["---", "", f"# {NAME_AR}", "",
          "مهندس مدني، مدير مشاريع أول وممثل للمالك ومدير فني وتصميم. مقيم في الدوحة، قطر، ومشاريعه في قطر والسعودية.", "",
          "يُكتب الاسم أيضاً: منذر الأشقر، منذر الاشقر، منذر أشقر، منزر الأشقر، Monther Al-Ashqar، Munther Al-Ashqar، Monther Alashqar.", "",
          "## الخدمات", ""] + [f"- {s[1]}" for s in SERVICES] + ["", "## الخبرة", ""]
    for r in D["ROLES"]:
        L += [f"### {r['t'][1]} — {r['org'][1]}", f"{r['s'][0]}–{r['e'][0]} · {r['place'][1]}", "", r["sum"][1], ""]
        L += [f"- {x[1]}" for x in r["pts"]] + [""]
    L += ["## المشاريع", ""]
    for k in D["ORDER"] + ["fifa", "dadu"]:
        p = next(x for x in D["P"] if x["k"] == k)
        d = D["DETAIL"][k]
        L += [f"### {p['ar']['n']}", f"القيمة: {p['v'][1] if p.get('v') else 'غير مذكورة'} · الدور: {D['ROLE'][p['role']]['ar']} · {p['s'][0]}–{p['e'][0]} · {d['place'][1]}",
              f"الصفحة: {abs_url(page_path('p-' + k, 'ar'))}", "", d["ov"][1], ""]
        L += [f"- {x[1]}" for x in d["sc"]] + [""]
    L += ["## أسئلة شائعة", ""]
    for q, a in FAQ_AR:
        L += [f"**{q}**", a, ""]
    return "\n".join(L)


ROBOTS = """# Search engines and AI assistants are welcome to read this site.
User-agent: *
Allow: /

User-agent: Googlebot
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: Bingbot
Allow: /
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Claude-SearchBot
Allow: /
User-agent: Claude-User
Allow: /
User-agent: anthropic-ai
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /
User-agent: Applebot
Allow: /
User-agent: Applebot-Extended
Allow: /
User-agent: meta-externalagent
Allow: /
User-agent: CCBot
Allow: /
User-agent: DuckAssistBot
Allow: /
User-agent: YandexBot
Allow: /

Sitemap: {site}/sitemap.xml
"""


def sitemap(routes):
    rows = []
    for r in routes:
        en, ar = page_path(r, "en"), page_path(r, "ar")
        for path in (en, ar):
            pri = "1.0" if r == "home" else ("0.8" if not r.startswith("p-") else "0.6")
            rows.append(f'''  <url><loc>{abs_url(path)}</loc><lastmod>2026-10-11</lastmod><priority>{pri}</priority>
    <xhtml:link rel="alternate" hreflang="en" href="{abs_url(en)}"/>
    <xhtml:link rel="alternate" hreflang="ar" href="{abs_url(ar)}"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{abs_url(en)}"/></url>''')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n")


# ---------------------------------------------------------------- build
def main():
    global DATA
    src = open(SRC, encoding="utf-8").read()
    cut = src.index("<script>try{if(!matchMedia")
    head_src, body_src = src[:cut], src[cut:]
    head_src = re.sub(r"<title>.*?</title>\n?", "", head_src, count=1)

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception:   # Playwright's own Chromium is not installed: use the system Chrome
            browser = pw.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, reduced_motion="reduce")
        ctx.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
        pg = ctx.new_page()

        def render(route, lang, extra_head="", root="", alt=""):
            doc = (f'<!doctype html>\n<html lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}" data-static data-build '
                   f'data-root="{root}" data-route="{route}" data-alt="{alt}">\n<head>\n<meta charset="utf-8">\n'
                   f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<title>{NAME_EN}</title>\n'
                   f'{extra_head}{head_src}</head>\n<body>\n{body_src}\n</body>\n</html>\n')
            pg.set_content(doc, wait_until="domcontentloaded")
            pg.wait_for_timeout(60)
            return pg

        # 1) read the data and the list of routes from the page itself
        render("home", "en")
        DATA = pg.evaluate("window.__MA")
        routes = ["home", "experience", "projects", "credentials", "notes", "contact"] + \
                 ["p-" + k for k in DATA["ORDER"] + ["fifa", "dadu"]]

        # 2) render every page in both languages
        count = 0
        for route in routes:
            for lang in ("en", "ar"):
                path = page_path(route, lang)
                other = "ar" if lang == "en" else "en"
                alt_path = page_path(route, other)
                root = rel(path, "")
                root = "" if root == "./" else root
                alt = rel(path, alt_path)
                render(route, lang, root=root, alt=alt)
                title = pg.title()
                if route.startswith("p-"):
                    k = route[2:]
                    p = next(x for x in DATA["P"] if x["k"] == k)
                    d = DATA["DETAIL"][k]
                    li = 1 if lang == "ar" else 0
                    who = "منذر الأشقر" if lang == "ar" else "Monther Al-Ashqar"
                    role = DATA["ROLE"][p["role"]][lang]
                    v = (p["v"][li] + (" · " if lang == "en" else " · ")) if p.get("v") else ""
                    desc = clip(f"{p[lang]['n']} · {v}{role} · {who}. {d['ov'][li]}")
                else:
                    desc = PAGE_META[route][1 if lang == "ar" else 0]
                # keep only this page's content, then serialise
                pg.evaluate("""() => {
                    document.querySelectorAll('.page[hidden]').forEach(e => e.remove());
                    document.documentElement.removeAttribute('data-build');
                    const t = document.querySelector('.top'); if (t) t.removeAttribute('style');
                }""")
                meta = head_meta(route, lang, title, desc, path, alt_path)
                out = pg.content()
                out = re.sub(r"(<title>.*?</title>)", lambda m: m.group(1) + "\n" + meta, out, count=1, flags=re.S)
                dest = os.path.join(OUT, path, "index.html")
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, "w", encoding="utf-8").write(out)
                count += 1
        browser.close()

    # 3) files for crawlers and AI assistants
    open(os.path.join(OUT, "llms.txt"), "w", encoding="utf-8").write(llms_txt(routes))
    open(os.path.join(OUT, "llms-full.txt"), "w", encoding="utf-8").write(llms_full())
    open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(ROBOTS.format(site=SITE_URL))
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(sitemap(routes))
    photo = (DATA["CONFIG"].get("photo") or "")
    if photo and not re.match(r"^(data:|https?:|/)", photo) and os.path.exists(os.path.join(HERE, photo)):
        shutil.copyfile(os.path.join(HERE, photo), os.path.join(OUT, photo))
    print(f"built {count} pages into {OUT}")


if __name__ == "__main__":
    main()
