# ================================================================
# IT HELPDESK ANALYTICS — ULTRA PREMIUM v20.0
# Perfect Arabic RTL + English Headings + Accurate Data
# Author: tarique14321495
# Enhanced with 10 New Features:
# 1. Added Agent filter in sidebar.
# 2. Added Sub Category filter in sidebar.
# 3. New tab for Sub Category analysis.
# 4. Added crosstab analysis for Department vs Main Category in Departments tab.
# 5. Added pie chart for Service distribution in Overview tab.
# 6. Added new KPIs: Average Tickets per Agent and Unique Sub Categories.
# 7. Added word cloud visualization for Main Categories in Issues tab (using matplotlib).
# 8. Added CSV export for filtered data in Raw Data tab.
# 9. Added heatmap for Department vs Issue in Trends tab.
# 10. Added sunburst chart for hierarchical view (Department > Service > Main Category) in Overview tab.
# Note: Word cloud feature removed due to missing 'wordcloud' module in the environment.
# New: Added advanced analytics as per user requirements in a new tab 'Analytics Summary'
# New: Added download button for analytics data as Excel (in Arabic format) for PPT use
# New: Added charts to the Excel file (Pie for priority, Bar for depts/causes/tech)
# ================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io, os, requests
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, PageBreak, Image, HRFlowable,
                                KeepTogether, FrameBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from openpyxl import Workbook
from openpyxl.chart import PieChart, BarChart, Reference
try:
    from arabic_reshaper import reshape
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False
    def reshape(t): return str(t)
    def get_display(t): return str(t)

st.set_page_config(page_title="IT Helpdesk Analytics", page_icon="🖥️",
                   layout="wide", initial_sidebar_state="expanded")
# ── PERFECT ARABIC FONT LOADER ───────────────────────────────────
@st.cache_resource
def load_arabic_fonts():
    """Load multiple Arabic font weights"""
    fonts_loaded = {}
   
    font_urls = {
        'Amiri-Regular': [
            "https://github.com/aliftype/amiri/raw/main/Amiri-Regular.ttf",
            "https://fonts.gstatic.com/s/amiri/v27/J7aRnpd8CGxBHqUpvrIw74NL.ttf",
        ],
        'Amiri-Bold': [
            "https://github.com/aliftype/amiri/raw/main/Amiri-Bold.ttf",
            "https://fonts.gstatic.com/s/amiri/v27/J7acnpd8CGxBHqUpvrIGJBEoRdI.ttf",
        ],
    }
   
    for font_name, urls in font_urls.items():
        path = f"/tmp/{font_name}.ttf"
        if not os.path.exists(path):
            for url in urls:
                try:
                    r = requests.get(url, timeout=20)
                    if r.status_code == 200:
                        with open(path, 'wb') as f:
                            f.write(r.content)
                        break
                except:
                    continue
       
        try:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(font_name, path))
                fonts_loaded[font_name] = True
        except:
            fonts_loaded[font_name] = False
   
    return fonts_loaded
FONTS = load_arabic_fonts()
FONT_OK = FONTS.get('Amiri-Regular', False)
AR_FONT = 'Amiri-Regular' if FONT_OK else 'Helvetica'
AR_FONT_BOLD = 'Amiri-Bold' if FONTS.get('Amiri-Bold', False) else 'Helvetica-Bold'
def ar(text, max_len=None):
    """Convert Arabic text to display correctly with proper RTL"""
    t = str(text).strip()
    if not t or t in ['nan', '', 'None']:
        return ''
   
    # Truncate if needed
    if max_len and len(t) > max_len:
        t = t[:max_len-2] + '..'
   
    # Check if Arabic characters present
    if ARABIC_SUPPORT and any('\u0600' <= c <= '\u06FF' for c in t):
        try:
            reshaped = reshape(t)
            return get_display(reshaped)
        except:
            return t
    return t
# ── PREMIUM CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
* {font-family:'Inter',sans-serif!important; box-sizing:border-box}
.stApp {background:linear-gradient(135deg,#0a0e27 0%,#1a1f3a 50%,#0a0e27 100%)!important}
.main .block-container {background:transparent!important; padding-top:.8rem!important; max-width:100%!important}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#0d1117,#161b22,#0d1117)!important; border-right:2px solid rgba(88,166,255,.2)!important; box-shadow:4px 0 20px rgba(0,0,0,.5)}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {color:#8ab4f8!important; font-size:.84rem!important; font-weight:500}
@keyframes premium-glow {0%,100% {box-shadow:0 8px 32px rgba(88,166,255,.15),inset 0 1px 0 rgba(255,255,255,.1)} 50% {box-shadow:0 12px 48px rgba(88,166,255,.25),inset 0 1px 0 rgba(255,255,255,.15)}}
@keyframes slide-up {from {opacity:0;transform:translateY(30px)} to {opacity:1;transform:translateY(0)}}
.premium-header {animation:premium-glow 4s ease-in-out infinite,slide-up .8s ease; background:linear-gradient(135deg,#1a1f3a,#2d3561,#1a1f3a); padding:28px 36px; border-radius:24px; margin-bottom:24px; border:2px solid rgba(88,166,255,.25); position:relative; overflow:hidden}
.premium-header::before {content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%; background:radial-gradient(circle,rgba(88,166,255,.08) 0%,transparent 70%); animation:rotate 20s linear infinite}
@keyframes rotate {from {transform:rotate(0deg)} to {transform:rotate(360deg)}}
.kpi-premium {background:linear-gradient(145deg,#1a1f3a,#2d3561); border:2px solid rgba(88,166,255,.2); border-top:4px solid #58a6ff; border-radius:20px; padding:24px 14px 20px; text-align:center; box-shadow:0 8px 32px rgba(0,0,0,.4),inset 0 1px 0 rgba(255,255,255,.05); transition:all .4s cubic-bezier(.175,.885,.32,1.275); margin-bottom:14px; position:relative; overflow:hidden}
.kpi-premium::before {content:''; position:absolute; top:0; left:-100%; width:100%; height:100%; background:linear-gradient(90deg,transparent,rgba(88,166,255,.1),transparent); transition:left .6s}
.kpi-premium:hover {transform:translateY(-8px) scale(1.03); box-shadow:0 16px 48px rgba(88,166,255,.3),inset 0 2px 0 rgba(255,255,255,.1); border-top-color:#79c0ff}
.kpi-premium:hover::before {left:100%}
.kpi-icon {font-size:1.8rem; margin-bottom:10px; display:block; filter:drop-shadow(0 2px 8px rgba(88,166,255,.4))}
.kpi-num {font-size:2.4rem; font-weight:900; color:#58a6ff; line-height:1; display:block; text-shadow:0 0 20px rgba(88,166,255,.5); letter-spacing:-1px}
.kpi-lbl {font-size:.7rem; color:#7d8590; margin-top:8px; display:block; letter-spacing:1.5px; text-transform:uppercase; font-weight:800}
.sec-premium {background:linear-gradient(90deg,rgba(88,166,255,.15),transparent); border-left:4px solid #58a6ff; border-radius:0 16px 16px 0; padding:14px 28px; margin:32px 0 20px; color:#c9d1d9; font-size:1.1rem; font-weight:900; box-shadow:0 4px 16px rgba(88,166,255,.1)}
.insight-card {background:linear-gradient(135deg,#161b22,#1c2128); border:2px solid rgba(88,166,255,.2); border-left:5px solid #58a6ff; border-radius:18px; padding:20px 24px; margin-bottom:14px; transition:all .3s ease; box-shadow:0 4px 16px rgba(0,0,0,.3)}
.insight-card:hover {border-left-color:#79c0ff; box-shadow:0 8px 32px rgba(88,166,255,.2); transform:translateX(4px)}
.insight-badge {display:inline-block; background:rgba(88,166,255,.15); color:#58a6ff; padding:4px 14px; border-radius:24px; font-size:.7rem; font-weight:900; letter-spacing:1.2px; text-transform:uppercase; margin-bottom:10px; border:1px solid rgba(88,166,255,.3)}
.insight-text {color:#c9d1d9; font-size:.92rem; line-height:1.8; font-weight:400}
.metric-premium {background:linear-gradient(145deg,#1a1f3a,#2d3561); border:2px solid rgba(88,166,255,.15); border-radius:18px; padding:22px; text-align:center; box-shadow:0 4px 16px rgba(0,0,0,.3)}
.stDownloadButton>button {background:linear-gradient(135deg,#1f6feb,#388bfd,#58a6ff)!important; color:white!important; border:none!important; border-radius:16px!important; padding:16px 38px!important; font-weight:900!important; font-size:1rem!important; box-shadow:0 8px 32px rgba(31,111,235,.4)!important; transition:all .4s!important; letter-spacing:.5px; text-transform:uppercase}
.stDownloadButton>button:hover {box-shadow:0 12px 48px rgba(31,111,235,.6)!important; transform:translateY(-4px) scale(1.05)!important; background:linear-gradient(135deg,#1f6feb,#58a6ff,#79c0ff)!important}
</style>""", unsafe_allow_html=True)
# ── COLUMN MAPPING (Arabic → English) ────────────────────────────
COLUMN_MAP = {
    'إدارة العميل': 'Department',
    'الخدمة': 'Service',
    'التصنيف الرئيسي': 'Main Category',
    'التصنيف الفرعي': 'Sub Category',
    'مسند الى': 'Assigned To',
    'التأثير': 'Impact',
    'تاريخ الإنشاء': 'Creation Date',
    'تاريخ ووقت الاغلاق': 'Closing Date',
    'تاريخ حل البلاغ': 'Resolution Date',
    'الحالة': 'Status'
}
# Original Arabic column names for data loading
C_DEPT_AR = 'إدارة العميل'
C_SVC_AR = 'الخدمة'
C_MAIN_AR = 'التصنيف الرئيسي'
C_SUB_AR = 'التصنيف الفرعي'
C_AGENT_AR = 'مسند الى'
C_IMPACT_AR = 'التأثير'
C_CREATE_AR = 'تاريخ الإنشاء'
C_CLOSE_AR = 'تاريخ ووقت الاغلاق'
C_RESOLVE_AR = 'تاريخ حل البلاغ'
C_STATUS_AR = 'الحالة'
# English names for PDF
C_DEPT = 'Department'
C_SVC = 'Service'
C_MAIN = 'Main Category'
C_SUB = 'Sub Category'
C_AGENT = 'Assigned To'
C_IMPACT = 'Impact'
C_CREATE = 'Creation Date'
C_CLOSE = 'Closing Date'
C_RESOLVE = 'Resolution Date'
C_STATUS = 'Status'
# ── TRANSLATIONS ─────────────────────────────────────────────────
T = {
    'AR': {
        'title':'لوحة تحليلات مكتب الدعم التقني','subtitle':'تقرير احترافي متقدم',
        'upload':'📂 رفع الملف','pdf_lang':'🌐 اللغة','dept_filter':'🏢 الإدارة',
        'svc_filter':'⚙️ الخدمة','main_filter':'🔥 الفئة','top_n':'🔢 أعلى',
        'theme':'🎨 النمط','all':'الكل','total_rec':'السجلات',
        'departments':'الإدارات','svc_types':'الخدمات','issue_types':'المشكلات',
        'agents':'الموظفون','tab_overview':'📊 عامة','tab_issues':'🔥 المشكلات',
        'tab_dept':'🏢 الإدارات','tab_agents':'👨‍💻 الموظفون','tab_trend':'📈 التوجهات',
        'tab_raw':'🗃️ البيانات','kpi_sec':'📌 المؤشرات','ai_insights':'🤖 الرؤى',
        'sub_filter': '📑 الفئة الفرعية', 'agent_filter': '👨‍💻 الموظف',
        'tab_sub': '📑 الفئات الفرعية', 'avg_tickets': 'متوسط التذاكر لكل موظف',
        'unique_subs': 'الفئات الفرعية الفريدة',
        'tab_analytics': '📈 تحليلات متقدمة',
        'download_excel': '⬇️ تحميل التحليلات كملف Excel (بالعربية)'
    },
    'EN': {
        'title':'IT Helpdesk Analytics','subtitle':'Premium Enterprise Report',
        'upload':'📂 Upload Data','pdf_lang':'🌐 Language','dept_filter':'🏢 Department',
        'svc_filter':'⚙️ Service','main_filter':'🔥 Category','top_n':'🔢 Top N',
        'theme':'🎨 Theme','all':'All','total_rec':'Records',
        'departments':'Departments','svc_types':'Services','issue_types':'Issues',
        'agents':'Agents','tab_overview':'📊 Overview','tab_issues':'🔥 Issues',
        'tab_dept':'🏢 Departments','tab_agents':'👨‍💻 Agents','tab_trend':'📈 Trends',
        'tab_raw':'🗃️ Data','kpi_sec':'📌 KPIs','ai_insights':'🤖 Insights',
        'sub_filter': '📑 Sub Category', 'agent_filter': '👨‍💻 Agent',
        'tab_sub': '📑 Sub Categories', 'avg_tickets': 'Avg Tickets/Agent',
        'unique_subs': 'Unique Sub Categories',
        'tab_analytics': '📈 Advanced Analytics',
        'download_excel': '⬇️ Download Analytics as Excel (in Arabic)'
    }
}
# ── SIDEBAR ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='text-align:center;padding:20px 0 12px'>"
                "<div style='background:linear-gradient(135deg,#1f6feb,#58a6ff);display:inline-block;"
                "border-radius:20px;padding:16px 20px;font-size:2.4rem;box-shadow:0 8px 32px rgba(31,111,235,.4)'>🖥️</div>"
                "</div>", unsafe_allow_html=True)
    lang = st.radio("🌐 Language", ["EN","AR"], horizontal=True)
    tx = T[lang]
    st.markdown(f"<h3 style='text-align:center;color:#58a6ff!important;margin:6px 0 14px;"
                f"font-size:1rem;font-weight:900;letter-spacing:1px'>{tx['title']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;font-size:.78rem;font-weight:700;color:{'#3fb950' if FONT_OK else '#d29922'}'>"
                f"{'✅ Arabic Font Ready' if FONT_OK else '⚠️ Loading Font'}</div>", unsafe_allow_html=True)
    st.markdown("---")
    uploaded = st.file_uploader(tx['upload'], type=["xlsx","xls"])
    if uploaded: st.success(f"✅ {uploaded.name}")
if not uploaded:
    st.markdown(
        f"<div style='min-height:88vh;display:flex;flex-direction:column;align-items:center;"
        f"justify-content:center;text-align:center;padding:48px'>"
        f"<div style='background:linear-gradient(135deg,#1f6feb,#58a6ff);border-radius:32px;"
        f"padding:28px;font-size:4.2rem;margin-bottom:32px;box-shadow:0 20px 60px rgba(31,111,235,.4)'>🖥️</div>"
        f"<h1 style='color:#58a6ff;font-size:3rem;font-weight:900;margin:0 0 16px;letter-spacing:-1px'>{tx['title']}</h1>"
        f"<p style='color:#7d8590;font-size:1.1rem;font-weight:500'>Upload Excel to begin analysis</p></div>",
        unsafe_allow_html=True)
    st.stop()
# ── LOAD DATA (WITH COLUMN RENAMING) ─────────────────────────────
@st.cache_data(show_spinner="⚙️ Processing data...")
def load_data(rb):
    bh = 2
    for h in [0,1,2,3]:
        try:
            t = pd.read_excel(io.BytesIO(rb), sheet_name=0, header=h)
            if C_DEPT_AR in t.columns: bh=h; break
        except: pass
   
    df = pd.read_excel(io.BytesIO(rb), sheet_name=0, header=bh)
   
    # Remove total rows
    if C_DEPT_AR in df.columns:
        df = df[~df[C_DEPT_AR].astype(str).str.contains('Grand Total|المجموع', na=False)]
   
    # Keep only relevant columns
    keep = [c for c in [C_DEPT_AR, C_SVC_AR, C_MAIN_AR, C_SUB_AR, C_AGENT_AR, C_IMPACT_AR, C_CREATE_AR, C_CLOSE_AR, C_RESOLVE_AR, C_STATUS_AR] if c in df.columns]
    df = df[keep].copy()
   
    # Forward fill for merged cells
    for c in [C_DEPT_AR, C_SVC_AR, C_MAIN_AR, C_SUB_AR]:
        if c in df.columns:
            df[c] = df[c].replace('', pd.NA).ffill()
   
    # Clean agent names
    if C_AGENT_AR in df.columns:
        df[C_AGENT_AR] = df[C_AGENT_AR].astype(str).str.strip()
        df[C_AGENT_AR] = df[C_AGENT_AR].replace({'nan':pd.NA,'Agent':pd.NA,'مسند الى':pd.NA,'':pd.NA})
   
    # Remove empty rows
    df.dropna(how='all', inplace=True)
    mc = [c for c in [C_DEPT_AR, C_SVC_AR, C_MAIN_AR] if c in df.columns]
    df = df.dropna(subset=mc, how='all')
    df.reset_index(drop=True, inplace=True)
   
    # Create short agent name
    if C_AGENT_AR in df.columns:
        df['_short'] = (df[C_AGENT_AR].str.replace('−متعاقد','',regex=False)
                        .str.replace('-متعاقد','',regex=False).str.strip())
    else:
        df['_short'] = pd.NA
   
    # ✅ RENAME COLUMNS TO ENGLISH
    df = df.rename(columns=COLUMN_MAP)
   
    # Convert Excel float dates to datetime if numeric
    excel_origin = pd.to_datetime('1899-12-30')
    for col in [C_CREATE, C_CLOSE, C_RESOLVE]:
        if col in df and pd.api.types.is_numeric_dtype(df[col]):
            df[col] = excel_origin + pd.to_timedelta(df[col], unit='D')
        else:
            df[col] = pd.to_datetime(df[col], errors='coerce')
   
    # Calculate accuracy stats
    acc = {
        'total': len(df),
        'dept_fill': round(df[C_DEPT].notna().sum()/len(df)*100,1) if C_DEPT in df.columns else 0,
        'svc_fill': round(df[C_SVC].notna().sum()/len(df)*100,1) if C_SVC in df.columns else 0,
        'main_fill': round(df[C_MAIN].notna().sum()/len(df)*100,1) if C_MAIN in df.columns else 0,
        'agent_fill': round(df[C_AGENT].notna().sum()/len(df)*100,1) if C_AGENT in df.columns else 0,
    }

    # Advanced analytics calculations
    # Filter closed tickets - include 'Closed', 'Resolved', 'Close (Not Incident)', 'Waiting for 3rd Party'
    closed_statuses = ['Closed', 'Resolved', 'Close (Not Incident)', 'Waiting for 3rd Party']
    df_closed = df[df['Status'].isin(closed_statuses)].copy()

    # Use Closing Date if not NaN, else Resolution Date
    df_closed['Effective Close Date'] = df_closed['Closing Date'].where(df_closed['Closing Date'].notna(), df_closed['Resolution Date'])

    # Drop if Effective Close Date NaN or Creation Date NaN
    df_closed = df_closed[df_closed['Effective Close Date'].notna() & df_closed['Creation Date'].notna()]

    # Resolution time in days
    df_closed['Resolution Time'] = (df_closed['Effective Close Date'] - df_closed['Creation Date']).dt.total_seconds() / 86400

    # Remove invalid (negative or NaN)
    df_closed = df_closed[df_closed['Resolution Time'] > 0].dropna(subset=['Resolution Time'])

    # Overall average
    overall_avg = df_closed['Resolution Time'].mean()

    # Average by priority
    avg_by_priority = df_closed.groupby('Impact')['Resolution Time'].mean()

    # Average by department (top 10 by count)
    dept_counts = df_closed['Department'].value_counts().head(10)
    avg_by_dept = df_closed.groupby('Department')['Resolution Time'].mean().reindex(dept_counts.index)

    # Average by cause (top 10)
    cause_counts = df_closed['Main Category'].value_counts().head(10)
    avg_by_cause = df_closed.groupby('Main Category')['Resolution Time'].mean().reindex(cause_counts.index)

    # Average by technician (top 10)
    tech_counts = df_closed['Assigned To'].value_counts().head(10)
    avg_by_tech = df_closed.groupby('Assigned To')['Resolution Time'].mean().reindex(tech_counts.index)

    # Monthly average
    df_closed['Month'] = df_closed['Creation Date'].dt.to_period('M')
    monthly_counts = df_closed['Month'].value_counts().sort_index()
    avg_monthly = df_closed.groupby('Month')['Resolution Time'].mean().sort_index()

    # Priority distribution
    priority_dist = df_closed['Impact'].value_counts(normalize=True) * 100

    # Top 10 causes pct
    top_causes_pct = (cause_counts / len(df_closed)) * 100

    # Per department non-low %
    non_low = df_closed[df_closed['Impact'] != 'Low']
    dept_non_low_counts = non_low.groupby('Department').size()
    dept_total = df_closed.groupby('Department').size()
    dept_non_low_pct = (dept_non_low_counts / dept_total * 100).reindex(dept_counts.index).fillna(0)

    # Per tech non-low counts (as number)
    tech_non_low_counts = non_low.groupby('Assigned To').size().reindex(tech_counts.index).fillna(0)

    # Monthly non-low pct
    monthly_non_low_counts = non_low.groupby('Month').size()
    monthly_non_low_pct = (monthly_non_low_counts / monthly_counts * 100).fillna(0)

    # Tech table
    tech_table = pd.DataFrame({
        'الفني': tech_counts.index,
        'عدد التذاكر': tech_counts,
        'متوسط وقت الحل': avg_by_tech
    }).reset_index(drop=True)

    # Percentages
    pct_24h = (df_closed['Resolution Time'] <= 1).mean() * 100
    pct_gt3d = (df_closed['Resolution Time'] > 3).mean() * 100
    pct_gt7d = (df_closed['Resolution Time'] > 7).mean() * 100

    analytics = {
        'overall_avg': overall_avg,
        'avg_by_priority': avg_by_priority,
        'avg_by_dept': avg_by_dept,
        'avg_by_cause': avg_by_cause,
        'avg_by_tech': avg_by_tech,
        'avg_monthly': avg_monthly,
        'priority_dist': priority_dist,
        'cause_counts': cause_counts,
        'top_causes_pct': top_causes_pct,
        'dept_counts': dept_counts,
        'dept_non_low_pct': dept_non_low_pct,
        'tech_counts': tech_counts,
        'tech_non_low_counts': tech_non_low_counts,
        'monthly_counts': monthly_counts,
        'monthly_non_low_pct': monthly_non_low_pct,
        'tech_table': tech_table,
        'pct_24h': pct_24h,
        'pct_gt3d': pct_gt3d,
        'pct_gt7d': pct_gt7d
    }
   
    return df, acc, analytics
try:
    rb = uploaded.read()
    df, acc, analytics = load_data(rb)
except Exception as e:
    st.error(f"❌ {e}"); st.stop()
if df.empty: st.error("❌ No data"); st.stop()
# ── SIDEBAR FILTERS ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    pdf_lang = st.radio(tx['pdf_lang'], ["English","العربية"], horizontal=True)
    st.markdown("---")
    ALL = tx['all']
    s_dep = st.selectbox(tx['dept_filter'], [ALL]+sorted(df[C_DEPT].dropna().unique().tolist()))
    s_svc = st.selectbox(tx['svc_filter'], [ALL]+sorted(df[C_SVC].dropna().unique().tolist()))
    s_mn = st.selectbox(tx['main_filter'], [ALL]+sorted(df[C_MAIN].dropna().unique().tolist()))
    # New Feature 1: Agent filter
    s_agent = st.selectbox(tx['agent_filter'], [ALL]+sorted(df[C_AGENT].dropna().unique().tolist()))
    # New Feature 2: Sub Category filter
    s_sub = st.selectbox(tx['sub_filter'], [ALL]+sorted(df[C_SUB].dropna().unique().tolist()))
    st.markdown("---")
    top_n = st.slider(tx['top_n'], 5, 30, 15)
    theme = st.selectbox(tx['theme'], ["plotly_dark","plotly_white","ggplot2"])
dff = df.copy()
if s_dep != ALL: dff = dff[dff[C_DEPT]==s_dep]
if s_svc != ALL: dff = dff[dff[C_SVC]==s_svc]
if s_mn != ALL: dff = dff[dff[C_MAIN]==s_mn]
# Apply new filters
if s_agent != ALL: dff = dff[dff[C_AGENT]==s_agent]
if s_sub != ALL: dff = dff[dff[C_SUB]==s_sub]
filtered = len(dff) < len(df)
_ag = dff[C_AGENT].dropna().value_counts()
_dp = dff[C_DEPT].dropna().value_counts()
_is = dff[C_MAIN].dropna().value_counts()
_sv = dff[C_SVC].dropna().value_counts()
ta_name = str(_ag.index[0]).replace('−متعاقد','').replace('-متعاقد','').strip() if len(_ag) else '—'
ta_cnt = int(_ag.iloc[0]) if len(_ag) else 0
td_name = str(_dp.index[0]) if len(_dp) else '—'
td_cnt = int(_dp.iloc[0]) if len(_dp) else 0
ti_name = str(_is.index[0]) if len(_is) else '—'
ti_cnt = int(_is.iloc[0]) if len(_is) else 0
cov = round(dff[C_AGENT].notna().sum()/max(len(dff),1)*100,1)
def sec(l):
    st.markdown(f"<div class='sec-premium'>{l}</div>", unsafe_allow_html=True)
def ccfg(fig, h=450):
    fig.update_layout(
        height=h, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12, color='#c9d1d9'),
        margin=dict(l=10,r=10,t=50,b=10),
        hoverlabel=dict(bgcolor='#161b22',font_size=12,font_color='#c9d1d9'),
        xaxis=dict(gridcolor='rgba(125,133,144,.1)',showgrid=True),
        yaxis=dict(gridcolor='rgba(125,133,144,.1)',showgrid=True))
    return fig
def fig_to_png(fig, w=900, h=420):
    try:
        return fig.to_image(format="png", width=w, height=h, scale=2)
    except:
        return None
# ══════════════════════════════════════════════════════════════════
# Function to generate Excel with analytics data in Arabic + Charts
# ══════════════════════════════════════════════════════════════════
def generate_analytics_excel(analytics, lang='AR'):
    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = 'متوسط عام'
    ws.append(['المتوسط العام للسنة'])
    ws.append([analytics['overall_avg']])

    # Avg by priority + Pie Chart
    ws = wb.create_sheet('حسب الأولوية')
    df = analytics['avg_by_priority'].reset_index().rename(columns={'Impact': 'الأولوية', 'Resolution Time': 'المتوسط (أيام)'})
    for r in df.to_records(index=False):
        ws.append(r)
    chart = PieChart()
    labels = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.title = "حسب الأولوية"
    ws.add_chart(chart, "D2")

    # Avg by dept + Bar Chart
    ws = wb.create_sheet('حسب الإدارة')
    df = analytics['avg_by_dept'].reset_index().rename(columns={'Department': 'الإدارة', 'Resolution Time': 'المتوسط (أيام)'})
    for r in df.to_records(index=False):
        ws.append(r)
    chart = BarChart()
    labels = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.title = "حسب الإدارة"
    ws.add_chart(chart, "D2")

    # Avg by cause + Bar Chart
    ws = wb.create_sheet('حسب السبب')
    df = analytics['avg_by_cause'].reset_index().rename(columns={'Main Category': 'السبب', 'Resolution Time': 'المتوسط (أيام)'})
    for r in df.to_records(index=False):
        ws.append(r)
    chart = BarChart()
    labels = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.title = "حسب السبب"
    ws.add_chart(chart, "D2")

    # Avg by tech + Bar Chart
    ws = wb.create_sheet('حسب الفني')
    df = analytics['avg_by_tech'].reset_index().rename(columns={'Assigned To': 'الفني', 'Resolution Time': 'المتوسط (أيام)'})
    for r in df.to_records(index=False):
        ws.append(r)
    chart = BarChart()
    labels = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.title = "حسب الفني"
    ws.add_chart(chart, "D2")

    # Monthly avg
    ws = wb.create_sheet('شهري')
    df = analytics['avg_monthly'].reset_index().rename(columns={'Month': 'الشهر', 'Resolution Time': 'المتوسط (أيام)'})
    for r in df.to_records(index=False):
        ws.append(r)

    # Priority dist + Pie Chart
    ws = wb.create_sheet('توزيع الأولويات')
    df = analytics['priority_dist'].reset_index().rename(columns={'index': 'الأولوية', 'Impact': 'النسبة (%)'})
    for r in df.to_records(index=False):
        ws.append(r)
    chart = PieChart()
    labels = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.title = "توزيع الأولويات"
    ws.add_chart(chart, "D2")

    # Top 10 causes + Bar Chart
    ws = wb.create_sheet('أعلى 10 أسباب')
    df = pd.DataFrame({'السبب': analytics['cause_counts'].index, 'العدد': analytics['cause_counts'], 'النسبة (%)': analytics['top_causes_pct']})
    for r in df.to_records(index=False):
        ws.append(r)
    chart = BarChart()
    labels = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.title = "أعلى 10 أسباب"
    ws.add_chart(chart, "E2")

    # Per dept
    ws = wb.create_sheet('لكل إدارة')
    df = pd.DataFrame({'الإدارة': analytics['dept_counts'].index, 'عدد التذاكر': analytics['dept_counts'], 'متوسط': analytics['avg_by_dept'], 'نسبة non-Low': analytics['dept_non_low_pct']})
    for r in df.to_records(index=False):
        ws.append(r)

    # Per tech
    ws = wb.create_sheet('لكل فني')
    df = pd.DataFrame({'الفني': analytics['tech_counts'].index, 'عدد التذاكر': analytics['tech_counts'], 'متوسط': analytics['avg_by_tech'], 'عدد non-Low': analytics['tech_non_low_counts']})
    for r in df.to_records(index=False):
        ws.append(r)

    # Monthly
    ws = wb.create_sheet('شهرياً')
    df = pd.DataFrame({'الشهر': analytics['monthly_counts'].index, 'عدد': analytics['monthly_counts'], 'متوسط': analytics['avg_monthly'], 'نسبة non-Low': analytics['monthly_non_low_pct']})
    for r in df.to_records(index=False):
        ws.append(r)

    # Tech table
    ws = wb.create_sheet('جدول الفنيين')
    df = analytics['tech_table']
    for r in df.to_records(index=False):
        ws.append(r)

    # Percentages
    ws = wb.create_sheet('نسب إضافية')
    df = pd.DataFrame({
        'نسبة البلاغات خلال 24 ساعة': [analytics['pct_24h']],
        'نسبة >3 أيام': [analytics['pct_gt3d']],
        'نسبة >7 أيام': [analytics['pct_gt7d']]
    })
    for r in df.to_records(index=False):
        ws.append(r)

    wb.save(output)
    output.seek(0)
    return output
# ══════════════════════════════════════════════════════════════════
# PERFECT PDF GENERATOR (English Headers + Arabic Content)
# ══════════════════════════════════════════════════════════════════
def generate_premium_pdf(df_data, stats, language="English"):
    buffer = io.BytesIO()
    total = len(df_data)
    is_ar = (language == "العربية")
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.6*inch)
    story = []
    # ── COLORS ───────────────────────────────────────────────────
    PRIMARY = colors.HexColor('#1f6feb')
    ACCENT = colors.HexColor('#58a6ff')
    SUCCESS = colors.HexColor('#3fb950')
    WARNING = colors.HexColor('#d29922')
    DANGER = colors.HexColor('#f85149')
    DARK = colors.HexColor('#0d1117')
    MEDIUM = colors.HexColor('#161b22')
    LIGHT = colors.HexColor('#c9d1d9')
    BG = colors.HexColor('#f6f8fa')
    WHITE = colors.white
    # ── STYLES ───────────────────────────────────────────────────
    base_font = AR_FONT if is_ar else 'Helvetica'
    bold_font = AR_FONT_BOLD if is_ar else 'Helvetica-Bold'
    ar_leading_multiplier = 1.8 if is_ar else 1.3
   
    cover_title = ParagraphStyle('CT',
        fontSize=32, textColor=PRIMARY, alignment=TA_CENTER, fontName=bold_font,
        spaceAfter=18, leading=32 * ar_leading_multiplier, letterSpacing=0)
   
    cover_sub = ParagraphStyle('CS',
        fontSize=16, textColor=ACCENT, alignment=TA_CENTER, fontName=base_font,
        spaceAfter=12, leading=16 * ar_leading_multiplier, letterSpacing=0)
   
    cover_meta = ParagraphStyle('CM',
        fontSize=9, textColor=colors.HexColor('#6e7681'),
        alignment=TA_CENTER, spaceAfter=6, fontName='Helvetica', leading=12)
   
    h1 = ParagraphStyle('H1',
        fontSize=18, textColor=PRIMARY, fontName=bold_font,
        spaceBefore=20, spaceAfter=14, leading=18 * ar_leading_multiplier,
        alignment=TA_RIGHT if is_ar else TA_LEFT)
   
    h2 = ParagraphStyle('H2',
        fontSize=14, textColor=ACCENT, fontName=bold_font,
        spaceBefore=16, spaceAfter=12, leading=14 * ar_leading_multiplier,
        alignment=TA_RIGHT if is_ar else TA_LEFT)
   
    h3 = ParagraphStyle('H3',
        fontSize=12, textColor=colors.HexColor('#6e7681'), fontName=bold_font,
        spaceBefore=12, spaceAfter=10, leading=12 * ar_leading_multiplier,
        alignment=TA_RIGHT if is_ar else TA_LEFT)
   
    body = ParagraphStyle('BD',
        fontSize=10, textColor=colors.HexColor('#24292f'),
        alignment=TA_RIGHT if is_ar else TA_JUSTIFY,
        leading=10 * ar_leading_multiplier, fontName=base_font,
        spaceBefore=8, spaceAfter=8)
   
    footer = ParagraphStyle('FT',
        fontSize=8, textColor=colors.HexColor('#6e7681'),
        alignment=TA_CENTER, fontName='Helvetica', leading=11)
    # ── TABLE HELPER ─────────────────────────────────────────────
    def tbl(data, widths, hdr_color, stripe=True):
        """Create table with English headers and Arabic-aware content"""
        processed_data = []
        for row_idx, row in enumerate(data):
            processed_row = []
            for cell_idx, cell in enumerate(row):
                cell_str = str(cell)
               
                # ✅ FIRST ROW (HEADERS) = ALWAYS ENGLISH
                if row_idx == 0:
                    processed_row.append(cell_str) # Keep headers as-is
                else:
                    # ✅ DATA ROWS = Arabic content with RTL if needed
                    if is_ar and any('\u0600' <= c <= '\u06FF' for c in cell_str):
                        processed_row.append(ar(cell_str, max_len=50))
                    else:
                        processed_row.append(cell_str[:50] if len(cell_str) > 50 else cell_str)
           
            processed_data.append(processed_row)
       
        t = Table(processed_data, colWidths=widths, repeatRows=1)
        v_padding = 10 if is_ar else 7
       
        styles = [
            ('BACKGROUND', (0,0), (-1,0), hdr_color),
            ('TEXTCOLOR', (0,0), (-1,0), WHITE),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # ✅ English headers
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,1), (-1,-1), base_font), # ✅ Arabic data
            ('FONTSIZE', (0,1), (-1,-1), 8.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d7de')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('TOPPADDING', (0,1), (-1,-1), v_padding),
            ('BOTTOMPADDING', (0,1), (-1,-1), v_padding),
        ]
       
        if stripe:
            styles.append(('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, BG]))
       
        t.setStyle(TableStyle(styles))
        return t
    def add_chart(fig, w_in=7.5, h_in=3.5):
        png = fig_to_png(fig, int(w_in*96), int(h_in*96))
        if png:
            story.append(Image(io.BytesIO(png), width=w_in*inch, height=h_in*inch))
    def metric_box(icon, label, value, color=PRIMARY):
        label_text = ar(label, max_len=40) if is_ar else label
        data = [[icon, label_text, value]]
        t = Table(data, colWidths=[0.5*inch, 3.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (1,0), BG),
            ('BACKGROUND', (2,0), (2,0), WHITE),
            ('FONTSIZE', (0,0), (0,0), 18),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
            ('FONTNAME', (1,0), (1,0), bold_font),
            ('FONTSIZE', (1,0), (1,0), 10),
            ('TEXTCOLOR', (1,0), (1,0), PRIMARY),
            ('ALIGN', (1,0), (1,0), 'RIGHT' if is_ar else 'LEFT'),
            ('FONTNAME', (2,0), (2,0), 'Helvetica-Bold'),
            ('FONTSIZE', (2,0), (2,0), 14),
            ('TEXTCOLOR', (2,0), (2,0), color),
            ('ALIGN', (2,0), (2,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING',(0,0), (-1,-1), 12),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING',(0,0),(-1,-1), 12),
            ('BOX', (0,0), (-1,-1), 1.5, color),
            ('ROUNDEDCORNERS', [12,12,12,12]),
        ]))
        return t
    # ══════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 1.2*inch))
    story.append(Paragraph(
        ar("تحليلات مكتب الدعم التقني") if is_ar else "IT HELPDESK ANALYTICS",
        cover_title))
    story.append(Paragraph(
        ar("تقرير الأداء الشامل والاحترافي") if is_ar else "COMPREHENSIVE PERFORMANCE REPORT",
        cover_sub))
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="50%", thickness=3, color=PRIMARY, spaceBefore=10, spaceAfter=20))
   
    now = datetime.now()
    story.append(Paragraph(f"<b>Report Date:</b> {now.strftime('%B %d, %Y')}", cover_meta))
    story.append(Paragraph(f"<b>Generated:</b> {now.strftime('%I:%M %p')}", cover_meta))
    story.append(Paragraph(f"<b>Data Source:</b> {uploaded.name}", cover_meta))
    story.append(Paragraph(f"<b>Total Records:</b> {total:,} tickets", cover_meta))
   
    story.append(Spacer(1, 0.5*inch))
   
    metrics = [
        ("🎫", "إجمالي التذاكر" if is_ar else "Total Support Tickets", f"{total:,}", ACCENT),
        ("🏢", "الإدارات" if is_ar else "Departments Analyzed", f"{df_data[C_DEPT].nunique()}", SUCCESS),
        ("👨‍💻", "الموظفون" if is_ar else "Active Support Agents", f"{df_data[C_AGENT].dropna().nunique()}", PRIMARY),
    ]
   
    for icon, label, val, clr in metrics:
        story.append(metric_box(icon, label, val, clr))
        story.append(Spacer(1, 0.12*inch))
   
    story.append(Spacer(1, 0.8*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#d0d7de'), spaceAfter=10))
    story.append(Paragraph(
        ar("سري — للاستخدام الداخلي فقط") if is_ar else "CONFIDENTIAL — Internal Use Only",
        footer))
    story.append(PageBreak())
    # ══════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════
    story.append(Paragraph(
        ar("الملخص التنفيذي") if is_ar else "EXECUTIVE SUMMARY",
        h1))
    story.append(Spacer(1, 0.15*inch))
   
    exec_text = ar(f"""
يقدم هذا التقرير تحليلا شاملا ومتقدما لأداء مكتب الدعم التقني ويغطي {total:,} تذكرة دعم تم معالجتها
يكشف التحليل عن مؤشرات الأداء التشغيلية الرئيسية وأنماط توزيع الخدمات ومؤشرات أداء الموظفين بدقة عالية
تظهر نتائج التحقق من جودة البيانات تغطية بنسبة {stats['dept_fill']}٪ للإدارات ومعدل تعيين بنسبة {stats['agent_fill']}٪
للموظفين مما يضمن رؤى موثوقة وقابلة للتنفيذ لاتخاذ القرارات الاستراتيجية
    """) if is_ar else f"""
This comprehensive report provides an advanced analytical assessment of IT Helpdesk operations,
covering {total:,} support tickets processed during the analysis period. The analysis reveals critical
operational performance indicators, service distribution patterns, and agent performance metrics with
high precision. Data quality verification demonstrates {stats['dept_fill']}% department coverage and
{stats['agent_fill']}% agent assignment rate, ensuring actionable insights for strategic decision-making.
    """
    story.append(Paragraph(exec_text.strip(), body))
    story.append(Spacer(1, 0.2*inch))
    # ══════════════════════════════════════════════════════════════
    # KPI TABLE (✅ ENGLISH HEADERS)
    # ══════════════════════════════════════════════════════════════
    story.append(Paragraph(
        ar("مؤشرات الأداء الرئيسية") if is_ar else "KEY PERFORMANCE INDICATORS",
        h2))
    story.append(Spacer(1, 0.1*inch))
   
    # ✅ HEADERS ALWAYS IN ENGLISH
    kpi_data = [
        ["Metric", "Value", "Coverage", "Status"], # ✅ English
        [ar("إجمالي التذاكر") if is_ar else "Total Tickets",
         f"{total:,}", "100%", "✓"],
        [ar("الإدارات الفريدة") if is_ar else "Unique Departments",
         f"{df_data[C_DEPT].nunique()}", f"{stats['dept_fill']}%",
         "✓" if stats['dept_fill']>90 else "⚠"],
        [ar("أنواع الخدمات") if is_ar else "Service Categories",
         f"{df_data[C_SVC].nunique()}", f"{stats['svc_fill']}%",
         "✓" if stats['svc_fill']>90 else "⚠"],
        [ar("فئات المشكلات") if is_ar else "Issue Categories",
         f"{df_data[C_MAIN].nunique()}", f"{stats['main_fill']}%",
         "✓" if stats['main_fill']>90 else "⚠"],
        [ar("الموظفون النشطون") if is_ar else "Active Agents",
         f"{df_data[C_AGENT].dropna().nunique()}", f"{stats['agent_fill']}%",
         "✓" if stats['agent_fill']>80 else "⚠"],
    ]
   
    story.append(tbl(kpi_data, [2.2*inch, 1.3*inch, 1.1*inch, 0.7*inch], PRIMARY))
    story.append(Spacer(1, 0.2*inch))
    # ══════════════════════════════════════════════════════════════
    # TOP PERFORMERS (✅ ENGLISH HEADERS)
    # ══════════════════════════════════════════════════════════════
    story.append(Paragraph(
        ar("أفضل الأداء والمقاييس الحرجة") if is_ar else "TOP PERFORMERS & CRITICAL METRICS",
        h2))
    story.append(Spacer(1, 0.1*inch))
   
    # ✅ HEADERS IN ENGLISH, DATA IN ARABIC
    top_data = [
        ["Category", "Top Item", "Volume", "% Share"], # ✅ English
        [ar("أكثر إدارة") if is_ar else "Busiest Department",
         ar(td_name, max_len=35),
         f"{int(td_cnt):,}" if len(_dp) else '0',
         f"{round(td_cnt/total*100,1)}%" if len(_dp) else '0%'],
        [ar("أكثر مشكلة") if is_ar else "Top Issue",
         ar(ti_name, max_len=35),
         f"{int(ti_cnt):,}" if len(_is) else '0',
         f"{round(ti_cnt/total*100,1)}%" if len(_is) else '0%'],
        [ar("أنشط موظف") if is_ar else "Most Active Agent",
         ar(ta_name, max_len=35),
         f"{int(ta_cnt):,}" if len(_ag) else '0',
         f"{round(ta_cnt/total*100,1)}%" if len(_ag) else '0%'],
    ]
   
    story.append(tbl(top_data, [1.6*inch, 2.6*inch, 0.9*inch, 0.9*inch], SUCCESS))
    story.append(PageBreak())
    # ══════════════════════════════════════════════════════════════
    # VISUAL ANALYTICS
    # ══════════════════════════════════════════════════════════════
    story.append(Paragraph(
        ar("التحليلات المرئية — توزيع الخدمات") if is_ar else "VISUAL ANALYTICS — DISTRIBUTION",
        h1))
    story.append(Spacer(1, 0.15*inch))
    svc_df = dff[C_SVC].value_counts().head(8).reset_index()
    svc_df.columns = ['Service','Count']
    fig_svc = px.pie(svc_df, values='Count', names='Service',
                     title='Service Type Distribution', hole=0.45,
                     template='plotly_white',
                     color_discrete_sequence=px.colors.sequential.Blues_r)
    fig_svc.update_traces(textposition='inside', textinfo='percent+label',
                          textfont_size=10, marker=dict(line=dict(color='white', width=2)))
    fig_svc.update_layout(paper_bgcolor='white', plot_bgcolor='white',
                          font_color='#24292f', margin=dict(l=10,r=10,t=40,b=10),
                          title_font_size=13, title_font_color='#1f6feb')
    add_chart(fig_svc, 7.5, 3)
    story.append(Spacer(1, 0.15*inch))
    dv = dff[C_DEPT].value_counts().head(12).reset_index()
    dv.columns = ['Department','Tickets']
    fig_dept = px.bar(dv, x='Tickets', y='Department', orientation='h',
                      text='Tickets', color='Tickets',
                      color_continuous_scale='Teal',
                      template='plotly_white',
                      title='Top 12 Departments by Volume')
    fig_dept.update_layout(yaxis={'categoryorder':'total ascending'},
                           showlegend=False, coloraxis_showscale=False,
                           paper_bgcolor='white', plot_bgcolor='white',
                           font_color='#24292f',
                           margin=dict(l=10,r=10,t=40,b=10),
                           title_font_size=13, title_font_color='#1f6feb')
    fig_dept.update_traces(textposition='outside', marker_line_width=0)
    add_chart(fig_dept, 7.5, 3.5)
    story.append(PageBreak())
    # ══════════════════════════════════════════════════════════════
    # DETAILED TABLES (✅ ENGLISH HEADERS)
    # ══════════════════════════════════════════════════════════════
    story.append(Paragraph(
        ar("التحليل التفصيلي — أعلى المشكلات") if is_ar else "DETAILED ANALYSIS — TOP ISSUES",
        h1))
    story.append(Spacer(1, 0.12*inch))
    # ✅ ENGLISH HEADERS
    issue_headers = ["#", "Issue Category", "Count", "%"]
    issue_rows = [issue_headers]
    for i,(name,cnt) in enumerate(_is.head(18).items(),1):
        pct = round(cnt/total*100,1)
        issue_rows.append([str(i), ar(name, max_len=45), f"{int(cnt):,}", f"{pct}%"])
   
    story.append(tbl(issue_rows, [0.3*inch, 3.8*inch, 0.8*inch, 0.6*inch], DANGER))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        ar("الإدارات — تحليل الحمل") if is_ar else "DEPARTMENTS — WORKLOAD",
        h2))
    story.append(Spacer(1, 0.1*inch))
   
    # ✅ ENGLISH HEADERS
    dept_headers = ["#", "Department", "Tickets", "%"]
    dept_rows = [dept_headers]
    for i,(name,cnt) in enumerate(_dp.head(18).items(),1):
        pct = round(cnt/total*100,1)
        dept_rows.append([str(i), ar(name, max_len=45), f"{int(cnt):,}", f"{pct}%"])
   
    story.append(tbl(dept_rows, [0.3*inch, 3.8*inch, 0.8*inch, 0.6*inch], ACCENT))
    story.append(PageBreak())
    # ══════════════════════════════════════════════════════════════
    # AGENT PERFORMANCE (✅ ENGLISH HEADERS)
    # ══════════════════════════════════════════════════════════════
    if not df_data[C_AGENT].dropna().empty:
        story.append(Paragraph(
            ar("أداء الموظفين وتوزيع أحمال العمل") if is_ar else "AGENT PERFORMANCE",
            h1))
        story.append(Spacer(1, 0.12*inch))
        # ✅ ENGLISH HEADERS
        agent_headers = ["#", "Agent Name", "Tickets", "%"]
        agent_rows = [agent_headers]
        for i,(name,cnt) in enumerate(_ag.head(20).items(),1):
            pct = round(cnt/total*100,1)
            agent_rows.append([str(i), ar(str(name), max_len=42), f"{int(cnt):,}", f"{pct}%"])
       
        story.append(tbl(agent_rows, [0.3*inch, 3.8*inch, 0.8*inch, 0.6*inch], SUCCESS))
        story.append(Spacer(1, 0.2*inch))
    # FOOTER
    story.append(Spacer(1, 0.4*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#d0d7de'), spaceAfter=10))
    story.append(Paragraph(
        f"IT Helpdesk Analytics | {now.strftime('%B %Y')} | Tarique Siddique",
        footer))
    doc.build(story)
    buffer.seek(0)
    return buffer
# ══════════════════════════════════════════════════════════════════
# DASHBOARD UI
# ══════════════════════════════════════════════════════════════════
badge = (' <span style="background:rgba(210,153,34,.15);color:#d29922;padding:4px 14px;'
         'border-radius:20px;font-size:.72rem;font-weight:900;border:1px solid rgba(210,153,34,.3)">🔽 FILTERED</span>') if filtered else ""
st.markdown(
    f"<div class='premium-header'>"
    "<div style='display:flex;align-items:center;gap:22px;position:relative;z-index:1'>"
    "<div style='background:linear-gradient(135deg,#1f6feb,#58a6ff);border-radius:22px;"
    "padding:18px 22px;font-size:2.6rem;box-shadow:0 8px 32px rgba(31,111,235,.4)'>🖥️</div>"
    "<div style='flex:1'>"
    f"<h1 style='color:#58a6ff;margin:0;font-size:2rem;font-weight:900;"
    f"letter-spacing:1px;text-shadow:0 2px 12px rgba(88,166,255,.3)'>{tx['title']}</h1>"
    f"<div style='color:#7d8590;margin-top:6px;font-size:.82rem;font-weight:600;letter-spacing:.3px'>{tx['subtitle']}</div>"
    "<div style='color:#7d8590;margin-top:10px;font-size:.84rem;display:flex;gap:16px;flex-wrap:wrap'>"
    f"<span>📄 <b style='color:#c9d1d9'>{uploaded.name}</b></span>"
    "<span style='color:#30363d'>│</span>"
    f"<span>🗂️ <b style='color:#c9d1d9'>{len(df):,}</b> total</span>"
    "<span style='color:#30363d'>│</span>"
    f"<span>🔽 <b style='color:#58a6ff'>{len(dff):,}</b> shown</span>"
    f"{badge}</div></div></div></div>",
    unsafe_allow_html=True)
# Add new tab for Analytics
tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8 = st.tabs([
    tx['tab_overview'], tx['tab_issues'], tx['tab_dept'],
    tx['tab_agents'], tx['tab_trend'], tx['tab_raw'], tx['tab_sub'], tx['tab_analytics']])
with tab1:
    sec("📌 KEY PERFORMANCE INDICATORS")
    k1,k2,k3,k4,k5,k6,k7 = st.columns(7)  # Expanded for new KPIs
    for col,(ico,val,lbl) in zip([k1,k2,k3,k4,k5,k6,k7],[
        ("🎫",len(dff),tx['total_rec']),
        ("🏢",dff[C_DEPT].nunique(),tx['departments']),
        ("⚙️",dff[C_SVC].nunique(),tx['svc_types']),
        ("🔥",dff[C_MAIN].nunique(),tx['issue_types']),
        ("👨‍💻",dff[C_AGENT].dropna().nunique(),tx['agents']),
        # New Feature 6: New KPIs
        ("📊", round(len(dff) / max(dff[C_AGENT].nunique(), 1), 2), tx['avg_tickets']),
        ("📑", dff[C_SUB].nunique(), tx['unique_subs']),
    ]):
        with col:
            st.markdown(
                f"<div class='kpi-premium'><span class='kpi-icon'>{ico}</span>"
                f"<span class='kpi-num'>{val:,}</span>"
                f"<span class='kpi-lbl'>{lbl}</span></div>",
                unsafe_allow_html=True)
    sec("🤖 INTELLIGENT INSIGHTS")
    i1,i2,i3 = st.columns(3)
    with i1:
        st.markdown(f"<div class='insight-card'><div class='insight-badge'>TOP DEPARTMENT</div>"
                    f"<div class='insight-text'><b style='color:#58a6ff'>{td_name[:30]}</b><br>"
                    f"{td_cnt:,} tickets • {round(td_cnt/len(dff)*100,1)}%</div></div>",
                    unsafe_allow_html=True)
    with i2:
        st.markdown(f"<div class='insight-card'><div class='insight-badge'>TOP ISSUE</div>"
                    f"<div class='insight-text'><b style='color:#f85149'>{ti_name[:30]}</b><br>"
                    f"{ti_cnt:,} occurrences • {round(ti_cnt/len(dff)*100,1)}%</div></div>",
                    unsafe_allow_html=True)
    with i3:
        st.markdown(f"<div class='insight-card'><div class='insight-badge'>COVERAGE</div>"
                    f"<div class='insight-text'><b style='color:#3fb950'>{cov}%</b> Assignment<br>"
                    f"Agent: <b>{ta_name[:25]}</b> • {ta_cnt:,} tickets</div></div>",
                    unsafe_allow_html=True)
    # New Feature 5: Pie chart for Service distribution
    sec("⚙️ SERVICE DISTRIBUTION")
    svc_df = dff[C_SVC].value_counts().reset_index()
    svc_df.columns = ['Service', 'Count']
    fig_svc = px.pie(svc_df, values='Count', names='Service', title='Service Distribution', template=theme)
    st.plotly_chart(fig_svc, use_container_width=True)
    # New Feature 10: Sunburst chart
    sec("🌞 HIERARCHICAL VIEW")
    sun_df = dff.groupby([C_DEPT, C_SVC, C_MAIN]).size().reset_index(name='Count')
    fig_sun = px.sunburst(sun_df, path=[C_DEPT, C_SVC, C_MAIN], values='Count', template=theme)
    st.plotly_chart(fig_sun, use_container_width=True)
with tab2:
    sec("🔥 ISSUE CATEGORY ANALYSIS")
    d = dff[C_MAIN].value_counts().head(top_n).reset_index(); d.columns=['Issue','Count']
    fig = px.bar(d,x='Count',y='Issue',orientation='h',color='Count',
                 color_continuous_scale='Reds',template=theme,text='Count')
    fig.update_layout(yaxis={'categoryorder':'total ascending'},showlegend=False,coloraxis_showscale=False)
    st.plotly_chart(ccfg(fig,max(400,top_n*35)),use_container_width=True)
    st.dataframe(d,use_container_width=True,height=450)
with tab3:
    sec("🏢 DEPARTMENT PERFORMANCE")
    d = dff[C_DEPT].value_counts().head(top_n).reset_index(); d.columns=['Dept','Tickets']
    fig = px.bar(d,x='Tickets',y='Dept',orientation='h',color='Tickets',
                 color_continuous_scale='Teal',template=theme,text='Tickets')
    fig.update_layout(yaxis={'categoryorder':'total ascending'},showlegend=False,coloraxis_showscale=False)
    st.plotly_chart(ccfg(fig,520),use_container_width=True)
    st.dataframe(d,use_container_width=True,height=450)
    # New Feature 4: Crosstab for Department vs Main Category
    sec("🔀 CROSSTAB: DEPT VS ISSUE")
    crosstab = pd.crosstab(dff[C_DEPT], dff[C_MAIN])
    st.dataframe(crosstab, use_container_width=True)
with tab4:
    if dff[C_AGENT].dropna().empty:
        st.info("⚠️ No agent data available")
    else:
        sec("👨‍💻 AGENT WORKLOAD")
        ag = (dff.dropna(subset=[C_AGENT])
                 .groupby([C_AGENT,'_short']).size()
                 .reset_index(name='Tickets')
                 .sort_values('Tickets',ascending=False)
                 .head(top_n))
        fig = px.bar(ag,x='Tickets',y='_short',orientation='h',color='Tickets',
                     color_continuous_scale='Viridis',template=theme,text='Tickets')
        fig.update_layout(yaxis={'categoryorder':'total ascending','title':'Agent'},
                          showlegend=False,coloraxis_showscale=False)
        st.plotly_chart(ccfg(fig,580),use_container_width=True)
        st.dataframe(ag[[C_AGENT,'Tickets']],use_container_width=True,height=450)
with tab5:
    sec("📈 TREND ANALYSIS")
    t1,t2 = st.columns(2)
    with t1:
        st.markdown("<div style='color:#58a6ff;font-weight:900;margin-bottom:16px'>🏢 Departments</div>",
                    unsafe_allow_html=True)
        td_data = dff[C_DEPT].value_counts().head(10)
        fig_td = go.Figure(go.Bar(x=td_data.values,y=td_data.index,orientation='h',
            marker=dict(color=td_data.values,colorscale='Teal'),text=td_data.values,textposition='outside'))
        fig_td.update_layout(yaxis={'categoryorder':'total ascending'},showlegend=False,height=450,
                             paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font_color='#c9d1d9')
        st.plotly_chart(fig_td,use_container_width=True)
    with t2:
        st.markdown("<div style='color:#f85149;font-weight:900;margin-bottom:16px'>🔥 Issues</div>",
                    unsafe_allow_html=True)
        ti_data = dff[C_MAIN].value_counts().head(10)
        fig_ti = go.Figure(go.Bar(x=ti_data.values,y=ti_data.index,orientation='h',
            marker=dict(color=ti_data.values,colorscale='Reds'),text=ti_data.values,textposition='outside'))
        fig_ti.update_layout(yaxis={'categoryorder':'total ascending'},showlegend=False,height=450,
                             paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font_color='#c9d1d9')
        st.plotly_chart(fig_ti,use_container_width=True)
    # New Feature 9: Heatmap for Department vs Issue
    sec("🌡️ HEATMAP: DEPT VS ISSUE")
    heat_df = pd.crosstab(dff[C_DEPT], dff[C_MAIN])
    fig_heat = px.imshow(heat_df, text_auto=True, aspect="auto", color_continuous_scale='YlGnBu', template=theme)
    st.plotly_chart(fig_heat, use_container_width=True)
with tab6:
    sec("🗃️ RAW DATA EXPLORER")
    sd = dff.drop(columns=['_short'],errors='ignore').copy()
    c1,c2 = st.columns([1,3])
    with c1: fc = st.selectbox("Column",[tx['all']]+sd.columns.tolist())
    with c2: sr = st.text_input("🔍 Search","")
    if sr:
        mask = (sd.apply(lambda c: c.astype(str).str.contains(sr,case=False,na=False)).any(axis=1)
                if fc==tx['all'] else sd[fc].astype(str).str.contains(sr,case=False,na=False))
        sd = sd[mask]
    st.markdown(f"<div style='color:#7d8590;margin-bottom:8px'>"
                f"<b style='color:#58a6ff'>{len(sd):,}</b> of {len(df):,} records</div>",
                unsafe_allow_html=True)
    st.dataframe(sd,use_container_width=True,height=550)
    # New Feature 8: CSV export
    csv = sd.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download Filtered CSV", csv, "filtered_data.csv", "text/csv", use_container_width=True)
# New Feature 3: Sub Category tab
with tab7:
    sec("📑 SUB CATEGORY ANALYSIS")
    sub_data = dff[C_SUB].value_counts().head(top_n).reset_index()
    sub_data.columns = ['Sub Category', 'Count']
    fig_sub = px.bar(sub_data, x='Count', y='Sub Category', orientation='h', color='Count',
                     color_continuous_scale='Oranges', template=theme, text='Count')
    fig_sub.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(ccfg(fig_sub, max(400, top_n*35)), use_container_width=True)
    st.dataframe(sub_data, use_container_width=True, height=450)
# New tab for Analytics Summary
with tab8:
    sec("📈 تحليلات متقدمة" if lang == 'AR' else "Advanced Analytics")
    # Display overall average
    st.markdown(f"### المتوسط العام للسنة: {analytics['overall_avg']:.2f} يوم")
    
    # Average by priority
    st.markdown("### المتوسط حسب الأولوية")
    st.dataframe(analytics['avg_by_priority'].reset_index().rename(columns={'Impact': 'الأولوية', 'Resolution Time': 'المتوسط (أيام)' }))
    
    # Average by department
    st.markdown("### المتوسط حسب الإدارة (أعلى 10)")
    st.dataframe(analytics['avg_by_dept'].reset_index().rename(columns={'Department': 'الإدارة', 'Resolution Time': 'المتوسط (أيام)' }))

    # Average by cause
    st.markdown("### المتوسط حسب السبب (أعلى 10)")
    st.dataframe(analytics['avg_by_cause'].reset_index().rename(columns={'Main Category': 'السبب', 'Resolution Time': 'المتوسط (أيام)' }))

    # Average by technician
    st.markdown("### المتوسط حسب الفني (أعلى 10)")
    st.dataframe(analytics['avg_by_tech'].reset_index().rename(columns={'Assigned To': 'الفني', 'Resolution Time': 'المتوسط (أيام)' }))

    # Monthly average
    st.markdown("### المتوسط الشهري")
    st.dataframe(analytics['avg_monthly'].reset_index().rename(columns={'Month': 'الشهر', 'Resolution Time': 'المتوسط (أيام)' }))

    # Priority distribution
    st.markdown("### توزيع الأولويات")
    st.dataframe(analytics['priority_dist'].reset_index().rename(columns={'index': 'الأولوية', 'Impact': 'النسبة (%)'}))

    # Top 10 causes
    st.markdown("### أعلى 10 أسباب")
    top_causes_df = pd.DataFrame({'السبب': analytics['cause_counts'].index, 'العدد': analytics['cause_counts'], 'النسبة (%)': analytics['top_causes_pct']})
    st.dataframe(top_causes_df)

    # Per department
    st.markdown("### لكل إدارة (عدد, متوسط, نسبة non-Low)")
    dept_df = pd.DataFrame({'الإدارة': analytics['dept_counts'].index, 'عدد التذاكر': analytics['dept_counts'], 'متوسط': analytics['avg_by_dept'], 'نسبة non-Low': analytics['dept_non_low_pct']})
    st.dataframe(dept_df)

    # Per technician
    st.markdown("### لكل فني (عدد, متوسط, عدد non-Low)")
    tech_df = pd.DataFrame({'الفني': analytics['tech_counts'].index, 'عدد التذاكر': analytics['tech_counts'], 'متوسط': analytics['avg_by_tech'], 'عدد non-Low': analytics['tech_non_low_counts']})
    st.dataframe(tech_df)

    # Monthly
    st.markdown("### شهرياً (عدد, متوسط, نسبة non-Low)")
    monthly_df = pd.DataFrame({'الشهر': analytics['monthly_counts'].index, 'عدد': analytics['monthly_counts'], 'متوسط': analytics['avg_monthly'], 'نسبة non-Low': analytics['monthly_non_low_pct']})
    st.dataframe(monthly_df)

    # Tech table
    st.markdown("### جدول الفنيين")
    st.dataframe(analytics['tech_table'])

    # Percentages
    st.markdown(f"### نسبة البلاغات المغلقة خلال 24 ساعة: {analytics['pct_24h']:.2f}%")
    st.markdown(f"### نسبة البلاغات >3 أيام: {analytics['pct_gt3d']:.2f}%")
    st.markdown(f"### نسبة البلاغات >7 أيام: {analytics['pct_gt7d']:.2f}%")

    # Download button for Excel with charts
    excel_buffer = generate_analytics_excel(analytics, lang)
    st.download_button(
        label=tx['download_excel'],
        data=excel_buffer,
        file_name="analytics_summary_with_charts.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
# ══════════════════════════════════════════════════════════════════
# PREMIUM PDF EXPORT
# ══════════════════════════════════════════════════════════════════
st.markdown("---")
sec("📄 PERFECT PDF — ENGLISH HEADERS + ARABIC DATA")
p1,p2 = st.columns([3,2])
with p1:
    st.markdown(
        f"<div class='insight-card' style='border-left:5px solid #1f6feb'>"
        f"<div class='insight-badge'>✅ 100% ACCURATE DATA</div>"
        f"<div class='insight-text'>"
        f"<b style='color:#3fb950'>English Headers • Arabic Content • Perfect RTL</b><br>"
        f"✓ Table Headers: <b>Metric, Value, Coverage, Status</b><br>"
        f"✓ Data Cells: Arabic with perfect RTL rendering<br>"
        f"✓ Column Names Auto-Mapped (Arabic → English)<br>"
        f"✓ Zero Overlap • Increased Line Height<br>"
        f"✓ Professional USA Client Design<br>"
        f"✓ Status: {'✅ Ready' if FONT_OK else '⚠️ Loading'}"
        f"</div></div>",
        unsafe_allow_html=True)
with p2:
    if st.button("📥 Generate Perfect PDF", use_container_width=True, type="primary"):
        with st.spinner(f"🎨 Creating perfect {pdf_lang} PDF..."):
            try:
                buf = generate_premium_pdf(dff, acc, pdf_lang)
                st.success(f"✅ Perfect {pdf_lang} PDF Generated!")
                st.download_button(
                    label=f"⬇️ DOWNLOAD PERFECT {pdf_lang.upper()} PDF",
                    data=buf,
                    file_name=f"IT_Helpdesk_Perfect_{pdf_lang}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
st.markdown(
    "<div style='text-align:center;margin-top:48px;padding-top:24px;border-top:1px solid rgba(88,166,255,.1)'>"
    "<div style='color:#7d8590;font-size:.92rem;font-weight:600'>Perfect English + Arabic Analytics</div>"
    "<div style='color:#58a6ff;font-size:.82rem;margin-top:6px;font-weight:500'>Crafted by Tarique Siddique 💙</div>"
    "</div>",
    unsafe_allow_html=True)
