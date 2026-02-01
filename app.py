import streamlit as st
import pandas as pd
import io
import re

# Sayfa yapılandırması
st.set_page_config(page_title="Özdisan PCBA Analiz", layout="wide", page_icon="⚡")

# --- CSS: ŞIK VE KÜÇÜK METRİK KARTLARI ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] th { font-weight: bold !important; }
    [data-testid="stDataEditor"] th:last-child { background-color: #0056b3 !important; color: white !important; }
    
    .metric-row {
        display: flex;
        justify-content: flex-start;
        gap: 15px;
        margin-bottom: 25px;
    }
    .compact-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px 20px;
        min-width: 180px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-top: 3px solid #0056b3;
    }
    .card-label { font-size: 13px; color: #666; margin-bottom: 4px; font-weight: 500; }
    .card-value { font-size: 22px; font-weight: 700; color: #1f1f1f; }
    </style>
    """, unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown("<h1 style='color: #0056b3; margin-bottom: 0;'>ÖZDISAN PCBA ANALİZ MERKEZİ</h1>", unsafe_allow_html=True)
st.divider()

# Dosya Yükleme
bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP Dosyasını Seç (TXT)", type=['txt'])

def explode_designators(df, col_name):
    df_copy = df.copy()
    df_copy[col_name] = df_copy[col_name].astype(str).str.upper().str.split(r'[,;\s]+')
    df_copy = df_copy.explode(col_name).reset_index(drop=True)
    df_copy[col_name] = df_copy[col_name].str.strip()
    return df_copy[df_copy[col_name] != ""]

if bom_file and pkp_file:
    try:
        # 1. VERİLERİ OKU
        df_bom_raw = pd.read_excel(bom_file)
        df_bom_raw.columns = [str(c).strip().upper() for c in df_bom_raw.columns]
        
        pkp_content = pkp_file.getvalue().decode("utf-8", errors="ignore")
        pkp_list = [l.split()[0].strip().upper() for l in pkp_content.splitlines() if "Designator" not in l and l.split()]
        df_pkp = pd.DataFrame(pkp_list, columns=['DESIGNATOR']).drop_duplicates()

        potential_code_cols = ['PART NUMBER', 'STOCK CODE', 'COMMENT', 'DESCRIPTION', 'ÜRÜN KODU', 'MALZEME KODU']
        code_col = next((c for c in potential_code_cols if c in df_bom_raw.columns), df_bom_raw.columns[0])

        if 'DESIGNATOR' in df_bom_raw.columns:
            # 2. ANALİZ
            df_bom_for_analysis = explode_designators(df_bom_raw[[code_col, 'DESIGNATOR']], 'DESIGNATOR')
            merged = pd.merge(df_bom_for_analysis, df_pkp, on='DESIGNATOR', how='outer', indicator='DURUM')

            # --- 📊 ADIM 1: ANALİZ SONUÇLARI ---
            st.subheader("📊 1. Adım: Mevcut Eşleşme Analizi")
            
            count_both = len(merged[merged['DURUM'] == 'both'])
            bom_only_df = merged[merged['DURUM'] == 'left_only']
            count_bom_only = len(bom_only_df)
            count_pkp_only = len(merged[merged['DURUM'] == 'right_only'])

            st.markdown(f"""
                <div class="metric-row">
                    <div class="compact-card" style="border-top-color: #28a745;">
                        <div class="card-label">✅ Tam Eşleşen</div>
                        <div class="card-value">{count_both}</div>
                    </div>
                    <div class="compact-card" style="border-top-color: #dc3545;">
                        <div class="card-label">❌ Sadece BOM (Eksik)</div>
                        <div class="card-value">{count_bom_only}</div>
                    </div>
                    <div class="compact-card" style="border-top-color: #ffc107;">
                        <div class="card-label">⚠️ Sadece PKP (Fazla)</div>
                        <div class="card-value">{count_pkp_only}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            t1, t2, t3 = st.tabs(["✅ Eşleşenler", "❌ Sadece BOM", "⚠️ Sadece PKP"])
            with t1: st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']].sort_values('DESIGNATOR'), use_container_width=True, hide_index=True)
            with t2: st.dataframe(bom_only_df[['DESIGNATOR']].sort_values('DESIGNATOR'), use_container_width=True, hide_index=True)
            with t3: st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']].sort_values('DESIGNATOR'), use_container_width=True, hide_index=True)

            st.divider()

            # --- 🛠️ ADIM 2: DÜZENLEME PANELİ ---
            col_head, col_note = st.columns([1, 2])
            with col_head:
                st.subheader("🛠️ 2. Adım: BOM Düzenleme")
            with col_note:
                st.info("**💡 ÖNEMLİ NOT:** Hızlı teklif için lütfen **Özdisan Stok Kodları** kullanın.")

            df_bom_raw['ADET'] = df_bom_raw['DESIGNATOR'].astype(str).apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() not in ["nan", ""] else 0)
            summary_df = df_bom_raw.groupby(code_col).agg({'ADET': 'sum', 'DESIGNATOR': lambda x: ', '.join(x.astype(str).unique())}).reset_index()
            summary_df.columns = ['BOM_KODU', 'TOPLAM_ADET', 'REFERANSLAR']
            summary_df['AYIRICI'] = "➡️" 
            summary_df['DÜZENLEME ALANI'] = summary_df['BOM_KODU']
            summary_df = summary_df[['BOM_KODU', 'TOPLAM_ADET', 'REFERANSLAR', 'AYIRICI', 'DÜZENLEME ALANI']]

            if 'confirmed' not in st.session_state: st.session_state.confirmed = False

            edited_df = st.data_editor(
                summary_df,
                use_container_width=True,
                disabled=st.session_state.confirmed, 
                column_config={
                    "BOM_KODU": st.column_config.TextColumn("ORİJİNAL BOM KODU", disabled=True),
                    "TOPLAM_ADET": st.column_config.NumberColumn("ADET", disabled=True, width="small"),
                    "REFERANSLAR": st.column_config.TextColumn("REFERANSLAR", disabled=True),
                    "AYIRICI": st.column_config.TextColumn("", disabled=True, width=20),
                    "DÜZENLEME ALANI": st.column_config.TextColumn("✍️ DÜZENLEME ALANI", width="large")
                },
                hide_index=True
            )

            # --- 🚀 ADIM 3: ONAY VE İNDİRME ---
            col_btn1, col_btn2, col_msg = st.columns([1, 1, 3])
            
            with col_btn1:
                if st.button("✅ Listeyi Onayla", type="primary", use_container_width=True):
                    if count_bom_only > 0:
                        # Hangi referansların eksik olduğunu belirle
                        missing_refs = bom_only_df['DESIGNATOR'].tolist()
                        ref_text = ", ".join(missing_refs[:10]) # İlk 10 tanesini göster
                        if len(missing_refs) > 10: ref_text += " ..."
                        
                        st.error(f"⚠️ ONAYLANAMADI! PKP dosyasında şu referanslar eksik: **{ref_text}**")
                    else:
                        st.session_state.confirmed = True
                        st.rerun()
            
            with col_btn2:
                if st.session_state.confirmed:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        edited_df.drop(columns=['AYIRICI']).to_excel(writer, index=False)
                    st.download_button("📥 Onaylı Listeyi İndir", output.getvalue(), "ozdisan_onayli_bom.xlsx", use_container_width=True)
            
            with col_msg:
                if st.session_state.confirmed:
                    st.success("✔️ Liste onaylandı.")

        else: st.error("BOM dosyasında 'DESIGNATOR' sütunu bulunamadı!")
            
    except Exception as e:
        st.error(f"Sistem Hatası: {e}")
