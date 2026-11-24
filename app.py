from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

APP_TITLE = "استرو رادار تقييم الموظفين - تطوير المبرمج استرو رادار"
HTML_CANDIDATES = [
    Path(__file__).parent / "astro-radar-offline.html",
    Path(__file__).parent / "public" / "astro-radar-offline.html",
]
DB_FILENAME = "astro-radar-db.encdb.json"
DB_PATH = Path(__file__).parent / DB_FILENAME
LEGACY_DB_PATH = Path(__file__).parent / "mizan-athar-db.encdb.json"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# RTL & High-Contrast Editorial Styling (Wide Desktop-First Layout)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');

      html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
        font-family: "IBM Plex Sans Arabic", "Cairo", "Tajawal", "Segoe UI", Tahoma, Arial, sans-serif;
      }

      [data-testid="stAppViewContainer"] {
        background-color: #f8fafc;
        color: #0f172a;
      }

      [data-testid="stMainBlockContainer"] {
        max-width: 100% !important;
        padding-top: 1.25rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-bottom: 1.5rem !important;
      }

      [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-left: 1px solid #e2e8f0;
      }

      .astro-hero {
        background: linear-gradient(135deg, #0f172a 0%, #134e4a 100%);
        color: #ffffff;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 0.9rem;
        border: 1px solid #115e59;
      }

      .astro-hero-kicker {
        font-size: 0.78rem;
        color: #99f6e4;
        font-weight: 600;
        margin-bottom: 0.35rem;
      }

      .astro-hero-title {
        font-size: 1.45rem;
        font-weight: 700;
        margin: 0 0 0.35rem 0;
        line-height: 1.35;
      }

      .astro-hero-sub {
        font-size: 0.88rem;
        color: #e2e8f0;
        margin: 0;
        line-height: 1.65;
      }

      .astro-notice-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.9rem;
      }

      .astro-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        font-size: 0.82rem;
        line-height: 1.6;
      }

      .astro-card-pc {
        background: #fef2f2;
        border-color: #fecaca;
        color: #7f1d1d;
      }

      .astro-card-save {
        background: #fffbeb;
        border-color: #fde68a;
        color: #78350f;
      }

      .astro-card-reload {
        background: #f0fdfa;
        border-color: #99f6e4;
        color: #134e4a;
      }

      .astro-card-title {
        font-weight: 700;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
      }

      .astro-mobile-blocker {
        display: none;
        background: #991b1b;
        color: #ffffff;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        font-weight: 600;
        line-height: 1.65;
      }

      @media (max-width: 1023px) {
        .astro-notice-grid {
          grid-template-columns: 1fr;
        }
        .astro-mobile-blocker {
          display: block;
        }
      }

      /* Make embedded HTML iframe span full container cleanly */
      iframe {
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        background: #f8fafc !important;
        width: 100% !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def locate_html_file() -> Path | None:
    for candidate in HTML_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def validate_vault_payload(raw_text: str) -> tuple[bool, dict[str, Any] | None, str]:
    try:
        parsed = json.loads(raw_text)
    except Exception:
        return False, None, "الملف المرفوع ليس ملف JSON صالحاً."

    if not isinstance(parsed, dict) or parsed.get("format") != "MIZAN_ATHAR_ENCDB_V1":
        return (
            False,
            None,
            "صيغة قاعدة البيانات غير متوافقة. يرجى رفع ملف مشفر بصيغة .encdb.json صادر من البرنامج.",
        )

    for key in ("saltBase64", "ivBase64", "ciphertextBase64"):
        if not parsed.get(key):
            return False, None, "بيانات التشفير داخل الملف غير مكتملة."

    return True, parsed, ""


def load_initial_vault_from_disk() -> tuple[str | None, dict[str, Any] | None]:
    for path in (DB_PATH, LEGACY_DB_PATH):
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                ok, parsed, _ = validate_vault_payload(content)
                if ok and parsed is not None:
                    return content, parsed
            except Exception:
                continue
    return None, None


def persist_vault_to_disk(raw_text: str) -> tuple[bool, str]:
    try:
        DB_PATH.write_text(raw_text, encoding="utf-8")
        return True, f"تم حفظ قاعدة البيانات في مسار التطبيق ({DB_FILENAME})."
    except Exception as exc:
        return (
            False,
            f"تم تحميل القاعدة في جلسة Streamlit الحالية (تعذر الكتابة المباشرة على القرص: {exc}).",
        )


def inject_preloaded_vault(html_text: str, vault_dict: dict[str, Any] | None) -> str:
    if not vault_dict:
        return html_text
    safe_json = json.dumps(vault_dict, ensure_ascii=False).replace("</", "<\\/")
    injection = f"<script>window.__ASTRO_PRELOADED_VAULT__ = {safe_json};</script>"
    if "</head>" in html_text:
        return html_text.replace("</head>", f"{injection}\n</head>", 1)
    return injection + "\n" + html_text


# ---------------------------------------------------------------------------
# Initialize Session State for Database Persistence Across Reloads
# ---------------------------------------------------------------------------
if "vault_raw_text" not in st.session_state:
    disk_raw, disk_parsed = load_initial_vault_from_disk()
    st.session_state["vault_raw_text"] = disk_raw
    st.session_state["vault_parsed"] = disk_parsed
    st.session_state["vault_source"] = "ملف القرص المحلي" if disk_parsed else None

html_path = locate_html_file()

# ---------------------------------------------------------------------------
# Sidebar: Encrypted Database Storage, Upload & Download Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### إدارة قاعدة البيانات والملفات")
    st.caption(
        "بيئة حاسوب فقط · يدعم تخزين واسترجاع قاعدة البيانات المشفرة AES-256-GCM"
    )

    st.warning(
        "تنبيه الجهاز: يعمل النظام بأقصى كفاءة في بيئة الحاسوب (مكتبي / لابتوب) ولا يُنصح باستخدامه أو تخزين البيانات على الموبايل أو التابلت."
    )

    current_parsed: dict[str, Any] | None = st.session_state.get("vault_parsed")
    current_raw: str | None = st.session_state.get("vault_raw_text")

    if current_parsed:
        st.success(
            f"قاعدة البيانات جاهزة ({current_parsed.get('recordCount', 0)} سجلات) · المصدر: {st.session_state.get('vault_source') or 'جلسة Streamlit'}"
        )
        saved_at = current_parsed.get("savedAt", "")
        if saved_at:
            st.caption(f"آخر تاريخ حفظ داخل الملف: {saved_at[:19].replace('T', ' ')}")
    else:
        st.info(
            "لا توجد قاعدة بيانات محمّلة حالياً في Streamlit؛ تُعرض البيانات الافتراضية حتى ترفع ملف `.encdb.json`."
        )

    st.divider()
    st.markdown("#### 1. تخزين / تحديث قاعدة البيانات في Streamlit")
    st.caption(
        "بعد إضافة موظف جديد أو تعديل التقييمات داخل البرنامج، احفظ الملف المشفر من «خزن المعلومات» ثم ارفعه هنا لتخزينه في بيئة Streamlit:"
    )

    uploaded_vault = st.file_uploader(
        "رفع ملف قاعدة البيانات المشفرة (.encdb.json / .json)",
        type=["json", "encdb"],
        key="vault_uploader",
        help="ارفع ملف astro-radar-db.encdb.json الصادر من نافذة خزن المعلومات لحفظه وتحميله عند إعادة التشغيل.",
    )

    if uploaded_vault is not None:
        raw_uploaded = uploaded_vault.getvalue().decode("utf-8", errors="replace")
        ok, parsed_uploaded, err_msg = validate_vault_payload(raw_uploaded)
        if not ok or parsed_uploaded is None:
            st.error(err_msg)
        else:
            if raw_uploaded != st.session_state.get("vault_raw_text"):
                st.session_state["vault_raw_text"] = raw_uploaded
                st.session_state["vault_parsed"] = parsed_uploaded
                st.session_state["vault_source"] = f"ملف مرفوع ({uploaded_vault.name})"
                disk_ok, disk_msg = persist_vault_to_disk(raw_uploaded)
                if disk_ok:
                    st.success(f"تم تخزين القاعدة بنجاح! {disk_msg}")
                else:
                    st.warning(disk_msg)
                st.rerun()

    st.divider()
    st.markdown("#### 2. تحميل الملفات على جهاز الحاسوب")

    if current_raw:
        st.download_button(
            label=f"تحميل قاعدة البيانات ({DB_FILENAME})",
            data=current_raw.encode("utf-8"),
            file_name=DB_FILENAME,
            mime="application/json",
            use_container_width=True,
            type="primary",
        )
    else:
        st.button(
            "لا توجد قاعدة بيانات مرفوعة للتحميل بعد",
            disabled=True,
            use_container_width=True,
        )

    if html_path is not None:
        html_bytes = html_path.read_bytes()
        st.download_button(
            label="تحميل ملف البرنامج المستقل (HTML)",
            data=html_bytes,
            file_name="astro-radar-offline.html",
            mime="text/html",
            use_container_width=True,
        )

    if current_parsed:
        st.divider()
        if st.button("مسح القاعدة المحمّلة من جلسة العرض", use_container_width=True):
            st.session_state["vault_raw_text"] = None
            st.session_state["vault_parsed"] = None
            st.session_state["vault_source"] = None
            st.rerun()

# ---------------------------------------------------------------------------
# Main Wide Viewport: Header, Mandatory Alerts, and Embedded HTML Application
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="astro-mobile-blocker">
      ⚠️ تنبيه هام: تم فتح الصفحة من شاشة صغيرة (موبايل أو تابلت). هذا التطبيق مصمم للعمل في بيئة الحاسوب المكتبي أو اللابتوب فقط، ولن يتم حفظ قاعدة البيانات المشفرة على الموبايل أو التابلت.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <section class="astro-hero">
      <div class="astro-hero-kicker">بيئة تشغيل Streamlit الموسّعة · نظام التقييم العادل ومقاومة التلاعب (100 نقطة)</div>
      <h1 class="astro-hero-title">{APP_TITLE}</h1>
      <p class="astro-hero-sub">
        واجهة تشغيل متكاملة بعرض الشاشة تربط تطبيق الويب المستقل بقاعدة البيانات المشفرة محلياً (AES-256-GCM) مع إمكانية رفع وتخزين وتحميل القاعدة عبر الجلسات.
      </p>
    </section>

    <section class="astro-notice-grid">
      <div class="astro-card astro-card-pc">
        <div class="astro-card-title">🖥️ بيئة الحاسوب فقط (PC / Laptop)</div>
        يعمل النظام وتخزين قاعدة البيانات المشفرة في بيئة الحاسوب المكتبي أو المحمول فقط، ولا يدعم التخزين على التابلت أو الموبايل.
      </div>
      <div class="astro-card astro-card-save">
        <div class="astro-card-title">💾 تنبيه عند إضافة موظف جديد أو تعديل</div>
        عند إضافة موظف جديد أو تعديل الدرجات، احفظ الملف المشفر من «خزن المعلومات» ثم ارفعه في الشريط الجانبي لتثبيت الإضافات في القاعدة.
      </div>
      <div class="astro-card astro-card-reload">
        <div class="astro-card-title">🔄 تنبيه عند إعادة تحميل الصفحة</div>
        عند إعادة التحميل، استخدم زر «فك تشفير القاعدة المحمّلة» أو ارفع ملف <code>{DB_FILENAME}</code> لإظهار آخر النتائج المحفوظة.
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

if html_path is None:
    st.error(
        "تعذر العثور على ملف `astro-radar-offline.html` في مجلد التطبيق أو مجلد `public/`. يرجى التأكد من رفع ملف HTML بجانب `app.py`."
    )
else:
    raw_html = html_path.read_text(encoding="utf-8")
    rendered_html = inject_preloaded_vault(raw_html, current_parsed)

    # Wide full-screen interactive container
    components.html(rendered_html, height=1120, scrolling=True)

    st.caption(
        f"ملف التشغيل النشط: {html_path.name} · التوقيت: {datetime.now().strftime('%Y-%m-%d %H:%M')} · جميع الحسابات والتشفير تتم محلياً بأمان."
    )
