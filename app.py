import streamlit as st
import pandas as pd
import io
import re

# Sayfa yapılandırması
st.set_page_config(page_title="Özdisan PCBA Analiz", layout="wide", page_icon="⚡")

# --- CSS: GÖRSEL DÜZENLEME (Görseldeki gibi temiz kartlar için) ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] th { font-weight: bold !important; }
    [data-testid="stDataEditor"] th:last-child { background-color: #0056b3 !important; color: white !important; }
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        flex: 1;
        border-bottom: 4px solid #0056b3;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #1f1f1f;
        margin-top: 5px;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
    }
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

            # --- 📊 ADIM 1: ANALİZ SONUÇLARI (GÖRSELDEKİ GİBİ) ---
            st.subheader("📊 1. Adım: Mevcut Eşleşme Analizi")
            
            count_both = len(merged[merged['DURUM'] == 'both'])
            count_bom_only = len(merged[merged['DURUM'] == 'left_only'])
            count_pkp_only = len(merged[merged['DURUM'] == 'right_only'])

            # Özel Metrik Kutuları
            st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-card">
                        <div class="metric-label">✅ Tam Eşleşen</div>
                        <div class="metric-value">{count_both}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">❌ Sadece BOM (Eksik)</div>
                        <div class="metric-value" style="color: #d32f2f;">{count_bom_only}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">⚠️ Sadece PKP (Fazla)</div>
                        <div class="metric-value" style="color: #f57c00;">{count_pkp_only}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            t1, t2, t3 = st.tabs(["✅ Eşleşenler", "❌ Sadece BOM", "⚠️ Sadece PKP"])
            with t1: st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']].sort_values('DESIGNATOR'), use_container_width=True, hide_index=True)
            with t2: st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']].sort_values('DESIGNATOR'), use_container_width=True, hide_index=True)
            with t3: st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']].sort_values('DESIGNATOR'), use_container_width=True, hide_index=True)

            st.divider()

            # --- 🛠️ ADIM 2: DÜZENLEME PANELİ ---
            col_head, col_note = st.columns([1, 2])
            with col_head:
                st.subheader("🛠️ 2. Adım: BOM Düzenleme")
            with col_note:
                st.info("**💡 ÖNEMLİ NOT:** Hızlı teklif ve doğru eşleşme için lütfen **Özdisan Stok Kodları** ile çalışınız. Bu, **teklif sürecini** hızlandıracaktır.")

            df_bom_raw['ADET'] = df_bom_raw['DESIGNATOR'].astype(str).apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() != "nan" else 0)
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
                    "TOPLAM_ADET": st.column_config.NumberColumn("ADET", disabled=True),
                    "REFERANSLAR": st.column_config.TextColumn("REFERANSLAR", disabled=True),
                    "AYIRICI": st.column_config.TextColumn("", disabled=True, width=20),
                    "DÜZENLEME ALANI": st.column_config.TextColumn("✍️ DÜZENLEME ALANI (Özdisan Kodu)", width="large")
                },
                hide_index=True
            )

            # --- 🚀 ADIM 3: ONAY VE İNDİRME ---
            col_btn1, col_btn2, col_msg = st.columns([1, 1, 3])
            
            with col_btn1:
                if st.button("✅ Listeyi Onayla", type="primary", use_container_width=True):
                    if count_bom_only > 0:
                        st.error(f"⚠️ ONAYLANAMADI! BOM listesindeki {count_bom_only} referans PKP'de yok. Lütfen düzeltin.")
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
                    st.success("✔️ Onaylandı.")

        else:
            st.error("BOM dosyasında 'DESIGNATOR' sütunu bulunamadı!")
            
    except Exception as e:
        st.error(f"Sistem Hatası: {e}")
