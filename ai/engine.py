import os
import sys
import json
import logging
from core import config, database

logger = logging.getLogger(__name__)

# Ensure local LLM requests bypass proxy
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"

def _fallback_chain():
    """Builds fallback chain dicts for AIAgent under omniroute."""
    chain = []
    for m in config.AI_LLM_FALLBACKS:
        if m and m != config.AI_LLM_MODEL and not m.startswith("auto/"):
            chain.append({"provider": "omniroute", "model": m})
    return chain

# --- Safe Hermes AIAgent Loader ---
def _load_hermes_agent():
    """Loads AIAgent safely with sys.path protection."""
    original_path = list(sys.path)
    try:
        if config.HERMES_AGENT_PATH not in sys.path:
            sys.path.insert(0, config.HERMES_AGENT_PATH)
            
        venv_site_packages = os.path.join(config.HERMES_AGENT_PATH, "venv/lib/python3.11/site-packages")
        if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
            sys.path.append(venv_site_packages)
            
        agent_dir = os.path.join(config.HERMES_AGENT_PATH, "agent")
        tools_dir = os.path.join(config.HERMES_AGENT_PATH, "tools")
        if os.path.exists(agent_dir) and agent_dir not in sys.path:
            sys.path.append(agent_dir)
        if os.path.exists(tools_dir) and tools_dir not in sys.path:
            sys.path.append(tools_dir)

        import model_tools
        model_tools.discover_builtin_tools()
        
        # Ensure our ai.tools are loaded
        import ai.tools
        
        from run_agent import AIAgent
        return AIAgent
    except Exception as e:
        logger.error(f"Failed to load Hermes AIAgent: {e}")
        return None
    finally:
        # Guarantee project root remains at the head of sys.path
        if config.BASE_DIR not in sys.path:
            sys.path.insert(0, config.BASE_DIR)

_AgentClass = _load_hermes_agent()

def process_admin_message(admin_text: str) -> str:
    """Processes administrative requests from the admin using autonomous LLM Agent."""
    system_prompt = (
        "شما دستیار هوشمند و مدیر ارشد فروشگاه موبایل Danifon هستید. "
        "با ادمین به زبان فارسی محاورهای، محترمانه و دقیق صحبت کنید.\n\n"
        "وظایف شما:\n"
        "1. ثبت دستگاه تک در موجودی انبار و یا تولید پست کانال تلگرام.\n"
        "اگر ادمین مشخصات یک دستگاه آیفون تک (مثل '13pro 128G 2sim Za 100% آبی تعویض 110.000') را فرستاد یا خواست آن را در کانال/انبار قرار دهد:\n"
        "شما باید ابتدا مشخصات گوشی (مدل، ظرفیت، پارت، سیم، باتری، رنگ، وضعیت بدنه/تعویض قطعات و قیمت) را دقیق استخراج کنید.\n"
        "سپس ابزار tool_add_device را صدا بزنید تا در دیتابیس انبار ثبت شود.\n"
        "سپس یک پست تلگرامی شیک با ایموجی 📱 جهت ارسال به کانال تولید کنید و ابزار tool_draft_channel_post را صدا بزنید.\n\n"
        "2. استعلام موجودی و گزارشگیری:\n"
        "در صورت درخواست گزارش یا استعلام، ابزارهای tool_get_report یا tool_search_inventory را صدا بزنید.\n\n"
        "3. آپدیت لیست قیمتهای روزانه بازار: از tool_update_market_prices استفاده کنید."
    )
    
    if _AgentClass:
        try:
            agent = _AgentClass(
                model=config.AI_LLM_MODEL,
                provider="omniroute",
                fallback_model=_fallback_chain() or None,
                ephemeral_system_prompt=system_prompt,
                enabled_toolsets=["admin_agent"]
            )
            response = agent.chat(admin_text)
            res_str = response.strip()
            if not any(err_kw in res_str for err_kw in ["HTTP 429", "HTTP 400", "HTTP 401", "HTTP 404", "API call failed", "cooling down", "No credentials"]):
                return res_str
            logger.warning(f"Admin AI Agent returned error ({res_str[:80]}), activating deterministic admin fallback")
        except Exception as e:
            logger.warning(f"Admin AI Agent exception ({e}), activating deterministic admin fallback")

    # Fallback execution for admin requests
    from ai import tools as ai_tools
    txt = admin_text.lower()

    if any(w in txt for w in ["گزارش", "مالی", "فروش", "داشبورد", "سود"]):
        rep_raw = ai_tools.tool_get_report()
        try:
            import json
            rep = json.loads(rep_raw)
            dash = rep.get("dashboard", {})
            return (
                f"📊 **گزارش مالی و انبار فروشگاه دانیفون**\n\n"
                f"📦 موجودی انبار: {dash.get('in_stock_count', 0)} دستگاه\n"
                f"🛍️ تعداد فروخته شده: {dash.get('sold_count', 0)} دستگاه\n"
                f"💵 درآمد کل: {dash.get('revenue', 0):,} تومان\n"
                f"💰 سود خالص: {dash.get('profit', 0):,} تومان"
            )
        except Exception:
            return f"📊 **گزارش سیستم:**\n{rep_raw}"

    if any(w in txt for w in ["موجودی", "جستجو", "سرچ", "چک"]):
        return ai_tools.tool_search_inventory(admin_text)

    return "✅ درخواست ادمین دریافت شد. برای دیدن پنل دکمهها از دستور /admin استفاده کنید."

import re
from services import pricing_service

def _normalize_persian_digits(text: str) -> str:
    persian_arabic = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"
    english = "01234567890123456789"
    trans = str.maketrans(persian_arabic, english)
    return text.translate(trans)

def _parse_user_specs(text: str) -> dict:
    text_clean = _normalize_persian_digits(text).lower()
    
    # 1. Model Detection (checking longest / specific names first)
    models = [
        ("iPhone 17 Pro Max", [r"17\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس|مکس)"]),
        ("iPhone 17 Pro", [r"17\s*(?:pro|پرو)"]),
        ("iPhone 17 Air", [r"17\s*(?:air|ایر)"]),
        ("iPhone 17", [r"\b17\b|ایفون 17|آیفون 17"]),
        
        ("iPhone 16 Pro Max", [r"16\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس|مکس)"]),
        ("iPhone 16 Pro", [r"16\s*(?:pro|پرو)"]),
        ("iPhone 16 Plus", [r"16\s*(?:plus|پلاس)"]),
        ("iPhone 16", [r"\b16\b|ایفون 16|آیفون 16"]),
        
        ("iPhone 15 Pro Max", [r"15\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس|مکس|poor\s*max)"]),
        ("iPhone 15 Pro", [r"15\s*(?:pro|پرو)"]),
        ("iPhone 15 Plus", [r"15\s*(?:plus|پلاس)"]),
        ("iPhone 15", [r"\b15\b|ایفون 15|آیفون 15"]),
        
        ("iPhone 14 Pro Max", [r"14\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس|مکس)"]),
        ("iPhone 14 Pro", [r"14\s*(?:pro|پرو)"]),
        ("iPhone 14 Plus", [r"14\s*(?:plus|پلاس)"]),
        ("iPhone 14", [r"\b14\b|ایفون 14|آیفون 14"]),
        
        ("iPhone 13 Pro Max", [r"13\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس|مکس)"]),
        ("iPhone 13 Pro", [r"13\s*(?:pro|پرو)"]),
        ("iPhone 13 Mini", [r"13\s*(?:mini|مینی)"]),
        ("iPhone 13", [r"\b13\b|ایفون 13|آیفون 13"]),
        
        ("iPhone 12 Pro Max", [r"12\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس|مکس)"]),
        ("iPhone 12 Pro", [r"12\s*(?:pro|پرو)"]),
        ("iPhone 12 Mini", [r"12\s*(?:mini|مینی)"]),
        ("iPhone 12", [r"\b12\b|ایفون 12|آیفون 12"]),
        
        ("iPhone 11 Pro Max", [r"11\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس|مکس)"]),
        ("iPhone 11 Pro", [r"11\s*(?:pro|پرو)"]),
        ("iPhone 11", [r"\b11\b|ایفون 11|آیفون 11"]),
        
        ("iPhone XS Max", [r"xs\s*(?:max|مکس)"]),
        ("iPhone XS", [r"\bxs\b|ایفون xs|آیفون xs"]),
        ("iPhone XR", [r"\bxr\b|ایفون xr|آیفون xr"]),
        ("iPhone X", [r"\bx\b|ایفون x|آیفون x"]),
        ("iPhone 8 Plus", [r"8\s*(?:plus|پلاس|پرومکس|پرو)"]),
        ("iPhone 8", [r"\b8\b"]),
    ]
    
    detected_model = None
    for name, patterns in models:
        for pat in patterns:
            if re.search(pat, text_clean):
                detected_model = name
                break
        if detected_model:
            break
            
    if not detected_model:
        detected_model = "iPhone 13 Pro Max"

    # 2. Capacity Detection
    cap_match = re.search(r"(?:^|[^\d])(64|128|256|512|1024|1t|1tb)(?:g|gb|گیگ|گیگابایت|[^\d]|$)", text_clean)
    capacity = "128"
    if cap_match:
        c = cap_match.group(1).upper()
        if c in ["1T", "1TB", "1024"]:
            capacity = "1TB"
        else:
            capacity = c

    # 3. Battery Percentage Detection
    battery = 85
    batt_match = re.search(r"(?:باتری|باتري|باطری|battery|batt|bat|b|هلس|درصد|%)\s*:?\s*(\d{2,3})|(\d{2,3})\s*(?:%|درصد)", text_clean)
    if batt_match:
        for g in batt_match.groups():
            if g and 50 <= int(g) <= 100:
                battery = int(g)
                break
    else:
        digits = re.findall(r"\b(\d{2,3})\b", text_clean)
        for d in digits:
            val = int(d)
            if 60 <= val <= 100 and d != capacity:
                battery = val
                break

    # 4. Color Detection
    colors = [
        ("آبی سیرا", ["آبی سیرا", "sierra blue"]),
        ("آبی", ["آبی", "ابی", "blue"]),
        ("مشکی", ["مشکی", "سیاه", "black", "dark"]),
        ("سفید", ["سفید", "white", "سیلور", "silver"]),
        ("گلد", ["گلد", "طلایی", "gold"]),
        ("بنفش", ["بنفش", "purple", "deep purple"]),
        ("سبز", ["سبز", "green", "alpine green"]),
        ("نچرال", ["نچرال", "natural"]),
        ("تیتانیوم", ["تیتانیوم", "titanium"]),
        ("خاکستری", ["خاکستری", "گری", "space gray", "gray"]),
    ]
    detected_color = "نامشخص"
    for canonical_color, keywords in colors:
        if any(kw in text_clean for kw in keywords):
            detected_color = canonical_color
            break

    # 5. Part Number Detection
    parts_list = [
        ("ZA/A", ["za/a", "zaa", r"\bza\b"]),
        ("CH/A", ["ch/a", "cha", r"\bch\b"]),
        ("LL/A", ["ll/a", "lla", r"\bll\b"]),
        ("LA/A", ["la/a", "laa", r"\bla\b"]),
        ("JA/A", ["ja/a", "jaa", r"\bja\b"]),
        ("HN/A", ["hn/a", "hna", r"\bhn\b"]),
        ("AE/A", ["ae/a", "aea", r"\bae\b"]),
        ("TH/A", ["th/a", "tha", r"\bth\b"]),
    ]
    detected_part = "نامشخص"
    for canonical_part, keywords in parts_list:
        matched = False
        for kw in keywords:
            if kw.startswith(r"\b"):
                if re.search(kw, text_clean):
                    detected_part = canonical_part
                    matched = True
                    break
            else:
                if kw in text_clean:
                    detected_part = canonical_part
                    matched = True
                    break
        if matched:
            break

    # 6. SIM Card Detection
    if any(k in text_clean for k in ["دو سیم", "دوسیم", "2sim", "2 سیم", "دو سيم"]):
        sim = "دو سیمکارت"
    elif any(k in text_clean for k in ["تک سیم", "تکسیم", "1sim", "1 سیم", "تک سيم"]):
        sim = "تک سیمکارت"
    elif detected_part in ["CH/A", "ZA/A"]:
        sim = "دو سیمکارت"
    elif detected_part in ["LL/A", "LA/A", "JA/A"]:
        sim = "تک سیمکارت"
    else:
        sim = "نامشخص"

    # 7. Registry Detection
    unreg_keywords = [
        "بدون رجیستر", "بدون ریجستر", "بدون کد", "بدونکد", "بدونرجیستر", "بدونریجستر",
        "بدون ريجستر", "بدون ریجستری", "بدون رجیستری",
        "bedon code", "bedone code", "bedon reg", "bedone reg",
        "no code", "no reg", "unregistered", "without reg", "without code",
        "کد ملی", "پاسپورت", "مسافری", "ثبت مرچنت"
    ]
    
    reg_keywords = [
        "با رجیستر", "با ریجستر", "با کد", "کددار", "کد دار", "رجیستر شده", "ریجستر شده",
        "ریجستری شده", "رجیستری شده", "با ریجستری", "با رجیستری", "با کدهای",
        "registered", "with reg", "with code"
    ]
    
    is_unregistered = any(k in text_clean for k in unreg_keywords)
    is_registered = any(k in text_clean for k in reg_keywords)
    
    if is_unregistered:
        register = "Unregistered"
    elif is_registered:
        register = "Registered"
    else:
        register = "Registered"

    return {
        "model": detected_model,
        "capacity": capacity,
        "battery": battery,
        "register": register,
        "color": detected_color,
        "part": detected_part,
        "sim": sim,
        "condition": "Clean"
    }

def _format_fallback_quote(user_specs: dict) -> str:
    res = pricing_service.calculate_price(
        model=user_specs.get("model", "iPhone 15 Pro"),
        capacity=user_specs.get("capacity", "256"),
        battery=int(user_specs.get("battery", 85)),
        register=user_specs.get("register", "Registered"),
        condition=user_specs.get("condition", "Clean")
    )
    if not res.get("success"):
        return res.get("error", "متاسفانه امکان برآورد قیمت وجود ندارد.")
    
    buy_range_fmt = res.get("buy_range_str") or f"{pricing_service._fmt(res['buy_price'])} تومان"
    sell_price_fmt = pricing_service._fmt(res['sell_price'])
    bd = res.get("breakdown", {})
    
    reg_label = "بدون رجیستر (بدون کد)" if user_specs.get("register") == "Unregistered" else "رجیستر شده (کددار)"
    quote_text = (
        f"📱 **فاکتور برآورد قیمت هوشمند دانیفون**\n\n"
        f"▫️ **مدل دستگاه:** {user_specs.get('model')} ({user_specs.get('capacity')}GB)\n"
        f"▫️ **سلامت باتری:** {user_specs.get('battery')}%\n"
        f"▫️ **وضعیت رجیستری:** {reg_label}\n"
        f"▫️ **وضعیت ظاهری:** {user_specs.get('condition', 'سالم (Clean)')}\n\n"
        f"💰 **حدود قیمت تخمینی خرید ما از شما:** {buy_range_fmt}\n"
        f"🏷️ **قیمت پایه بازار:** {sell_price_fmt} تومان\n\n"
        f"📌 *توضیحات:* قیمتگذاری بر اساس بنچمارک دیتابیس خریدهای واقعی دانیفون در بازه ۵ میلیونی انجام شده است.\n"
        f"📞 جهت تایید نهایی معامله و هماهنگی با کارشناس تماس بگیرید: @{config.EXPERT_USERNAME}"
    )
    return quote_text

def generate_expert_quote(user_specs: dict) -> str:
    """Generates AI-native structured price estimate proposal based on spec dictionary using Gemini LLM reasoning."""
    import json
    import requests
    try:
        url = "http://127.0.0.1:20128/v1/chat/completions"
        
        # Load relevant Knowledge Base benchmarks for context
        kb_path = config.KNOWLEDGE_BASE_PATH
        kb_summary = []
        if os.path.exists(kb_path):
            with open(kb_path, "r", encoding="utf-8") as f:
                kb_raw = json.load(f)
                model_q = user_specs.get("model", "iPhone").lower()
                for item in kb_raw:
                    if any(w in str(item.get("model")).lower() for w in model_q.split()):
                        kb_summary.append(item)
                    if len(kb_summary) >= 8:
                        break
                if not kb_summary:
                    kb_summary = kb_raw[:8]

        # Retrieve continuous learning feedback from AdminFeedback database
        recent_feedback_logs = database.get_recent_admin_feedback(limit=5)
        learning_context = []
        for fb in recent_feedback_logs:
            act = fb.get("agent_action", "")
            resp = fb.get("admin_response", "")
            c_data = fb.get("corrected_data", "")
            try:
                c_json = json.loads(c_data) if isinstance(c_data, str) and c_data.startswith("{") else {}
                insight = c_json.get("analysis", {}).get("analysis_insight", resp)
                learning_context.append(f"▫️ درخواست: {act} | پاسخ/اصلاح کارشناس: {resp} | تحلیل هوش مصنوعی: {insight}")
            except Exception:
                learning_context.append(f"▫️ مشخصات: {act} | نظر کارشناس: {resp}")

        feedback_str = "\n".join(learning_context) if learning_context else "سابقهای از اصلاحات تا کنون ثبت نشده است."

        sys_prompt = (
            "شما کارشناس ارشد و هوش مصنوعی قیمتگذاری فروشگاه آیفون دانیفون (DaniFone.ir) هستید.\n"
            "وظیفه شما آنالیز دقیق دیتابیس خریدهای واقعی و برآورد قیمت خرید و فروش گوشی مشتری بر اساس قوانین رسمی بازار ایران است.\n\n"
            "قوانین و فرمولهای تخصصی قیمتگذاری (DaniFone Market Skill Rules):\n"
            "1. تفکیک کامل قیمت خرید از قیمت فروش آکبند/ویترین:\n"
            "   - مبنای اصلی محاسبه قیمت خرید از مشتری، دیتابیس معاملات واقعی (Knowledge Base) دانیفون است.\n"
            "   - قیمت خرید پیشنهادی نباید قیمت فروش ویترین/آکبند باشد؛ قیمت خرید کارکرده حداقل ۱۵٪ تا ۲۰٪ پایینتر از آکبند است.\n\n"
            "2. قانون ارائه قیمت به صورت بازه ۵ میلیونی (5-Million Price Range Strategy):\n"
            "   - جهت ترغیب مشتری و بازاریابی روانشناختی، قیمت خرید از مشتری حتماً باید به صورت بازه ۵ میلیونی (مثلاً ۱۳۰ تا ۱۳۵ میلیون تومان یا 130,000,000 تا 135,000,000 تومان) ارائه شود.\n\n"
            "3. استعلام دیتابیس خریدهای واقعی (Knowledge Base):\n"
            "   - با توجه به دادههای معاملات اخیر دانیفون که در پیام کاربر ارسال شده، بنچمارک پایه مدل مربوطه را استخراج کنید.\n\n"
            "4. قانون رجیستری و تعرفه عوارض گمرکی (Official Customs Rates):\n"
            "   - اگر دستگاه بدون کد (بدون رجیستر) باشد، کسر قیمت برابر است با: [تعرفه رسمی گمرک مدل + 20,000,000 تومان هزینه پاسپورت]\n"
            "   - نرخهای رسمی عوارض گمرکی دانیفون:\n"
            "     * iPhone 17 Pro Max: 116,500,000 تومان | iPhone 17 Pro: 107,250,000 تومان | iPhone 17 Air: 94,050,000 تومان | iPhone 17: 75,050,000 تومان\n"
            "     * iPhone 16 Pro Max: 73,900,000 تومان | iPhone 16 Pro: 68,100,000 تومان | iPhone 16 Plus: 72,400,000 تومان | iPhone 16: 59,250,000 تومان\n"
            "     * iPhone 15 Pro Max: 67,850,000 تومان | iPhone 15 Pro: 59,350,000 تومان | iPhone 15 Plus: 57,700,000 تومان | iPhone 15: 51,850,000 تومان\n"
            "     * iPhone 14 Pro Max: 19,300,000 تومان | iPhone 14 Pro: 19,150,000 تومان | iPhone 14 Plus: 17,550,000 تومان | iPhone 14: 16,750,000 تومان\n"
            "   - استثنا: برای سری 11، 12 و 13 بدون رجیستر، خرید صورت نمیگیرد و اعلام کنید: 'سری 13 و پایینتر فقط نسخه کددار خریداری میشود.'\n\n"
            "5. افت قیمت قطعات تعویضشده (Back Glass / LCD / Camera Depreciation):\n"
            "   - افت قیمت بر اساس بازه قیمتی دستگاه محاسبه میشود:\n"
            "     * پایه زیر 100 میلیون تومان: 5,000,000 تومان به ازای هر قطعه تعویضی\n"
            "     * پایه 100 تا 200 میلیون تومان: 8,500,000 تومان به ازای هر قطعه تعویضی\n"
            "     * پایه 200 تا 300 میلیون تومان: 13,500,000 تومان به ازای هر قطعه تعویضی\n"
            "     * پایه بالای 300 میلیون تومان: 40,000,000 تومان به ازای هر قطعه تعویضی\n\n"
            "6. پاداش باتری فابریک و تعدیل سلامت باتری:\n"
            "   - به ازای هر ۱٪ اختلاف سلامت باتری با بنچمارک پایه، ۳۵۰,۰۰۰ تومان کم یا زیاد میشود.\n"
            "   - سلامت زیر 80%: هزینه تعویض کسر میگردد.\n\n"
            "7. سوابق یادگیری مداوم از اصلاحات و انحرافات قبلی (Continuous Learning History):\n"
            f"{feedback_str}\n\n"
            "خروجی مورد انتظار:\n"
            "یک پاسخ شیک، تحلیلی و رسمی در قالب فاکتور ارزشگذاری هوشمند دانیفون به همراه جدول مشخصات، محاسبات، بازه قیمت خرید ۵ میلیونی از مشتری و قیمت فروش ویترین."
        )

        user_prompt = (
            f"مشخصات دستگاه مشتری:\n"
            f"▫️ مدل: {user_specs.get('model')}\n"
            f"▫️ ظرفیت: {user_specs.get('capacity')}GB\n"
            f"▫️ سلامت باتری: {user_specs.get('battery')}%\n"
            f"▫️ وضعیت رجیستری: {user_specs.get('register')}\n"
            f"▫️ پارتنامبر: {user_specs.get('part', 'ZA/A')}\n"
            f"▫️ وضعیت ظاهری و قطعات: {user_specs.get('condition', 'Clean')}\n\n"
            f"دیتابیس معاملات اخیر مرتبط دانیفون:\n"
            f"{json.dumps(kb_summary, ensure_ascii=False)}"
        )

        payload = {
            "model": "antigravity/gemini-3.5-flash-low",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "stream": False
        }

        resp = requests.post(url, json=payload, timeout=25)
        if resp.status_code == 200:
            res_data = resp.json()
            content = res_data["choices"][0]["message"]["content"].strip()
            if content and len(content) > 50:
                return content

        logger.warning(f"Direct OmniRoute call status {resp.status_code}, falling back to template quote")
        return _format_fallback_quote(user_specs)
    except Exception as e:
        logger.warning(f"Error in direct AI quote generation: {e}, falling back to template quote")
        return _format_fallback_quote(user_specs)

def generate_expert_quote_raw(user_text: str) -> str:
    """Generates structured price estimate proposal based on user input text with full AI Agent analysis."""
    specs = _parse_user_specs(user_text)
    return generate_expert_quote(specs)
