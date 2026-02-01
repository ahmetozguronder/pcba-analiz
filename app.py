import streamlit as st
import pandas as pd
import io
import re

# Sayfa yapılandırması
st.set_page_config(page_title="Özdisan PCBA Analiz", layout="wide", page_icon="⚡")

# --- CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] th { font-weight: bold !important; }
    [data-testid="stDataEditor"] th:last-child { background-color: #0056b3 !important; color: white !important; }
    .table-spacer { margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. BAŞLIK ---
st.markdown("<h1 style='color: #0056b3; margin-bottom: 0;'>ÖZDISAN PCBA ANALİZ MERKEZİ</h1>", unsafe_allow_html=True)
st.divider()

bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP Dosyasını Seç (TXT)", type=['txt'])

# --- HATANIN DÜZELTİLDİĞİ FONKSİYON ---
def explode_designators(df, col_name):
    df_copy = df.copy()
    # Sütun içindeki değerleri listeye çeviriyoruz
    df_copy[col_name] = df_copy[col_name].astype(str).str.split(r'[,;\s]+')
    # Listeleri satırlara patlatıyoruz
    df_copy = df_copy.explode(col_name).reset_index(drop=True)
    # Series üzerinde .str.upper() kullanarak hatayı gideriyoruz
    df_copy[col_name] = df_copy[col_name].str.strip().str.upper()
    return df_copy[df_copy[col_name] != ""]

if bom_file and pkp_file:
    try:
        df_bom_raw = pd.read_excel(bom_file)
        df_bom_raw.columns = [str(c).strip().upper() for c in df_bom_raw.columns]
        potential_code_cols = ['PART NUMBER', 'STOCK CODE', 'COMMENT', 'DESCRIPTION', 'ÜRÜN KODU', 'MALZEME KODU']
        code_col = next((c for c in potential_code_cols if c in df_bom_raw.columns), df_bom_raw.columns[0])

        if 'DESIGNATOR' in df_bom_raw.columns:
            # Hazırlık
            df_bom_raw['DESIGNATOR'] = df_bom_raw['DESIGNATOR'].astype(str).str.upper()
            df_bom_raw['ADET_SAYISI'] = df_bom_raw['DESIGNATOR'].apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() else 0)
            
            summary_df = df_bom_raw.groupby(code_col).agg({'ADET_SAYISI': 'sum', 'DESIGNATOR': lambda x: ', '.join(x.unique())}).reset_index()
            summary_df.columns = ['BOM_KODU', 'TOPLAM_ADET', 'REFERANSLAR']
            summary_df['AYIRICI'] = "➡️" 
            summary_df['DÜZENLEME ALANI'] = summary_df['BOM_KODU']
            summary_df = summary_df[['BOM_KODU', 'TOPLAM_ADET', 'REFERANSLAR', 'AYIRICI', 'DÜZENLEME ALANI']]

            st.subheader("🛠️ BOM Düzenleme Paneli")
            if 'confirmed' not in st.session_state: st.session_state.confirmed = False

            edited_df = st.data_editor(
                summary_df,
                use_container_width=True,
                disabled=st.session_state.confirmed, 
                column_config={
                    "BOM_KODU": st.column_config.TextColumn("ORİJİNAL BOM KODU", disabled=True),
                    "TOPLAM_ADET": st.column_config.NumberColumn("TOPLAM ADET", disabled=True),
                    "REFERANSLAR": st.column_config.TextColumn("REFERANSLAR", disabled=True),
                    "AYIRICI": st.column_config.TextColumn("", disabled=True, width=20),
                    "DÜZENLEME ALANI": st.column_config.TextColumn("✍️ DÜZENLEME ALANI", width="large")
                },
                hide_index=True
            )

            # --- ANALİZ VE HATA KONTROLÜ ---
            pkp_content = pkp_file.getvalue().decode("utf-8", errors="ignore")
            pkp_list = [l.split()[0].strip().upper() for l in pkp_content.splitlines() if "Designator" not in l and l.split()]
            df_pkp = pd.DataFrame(pkp_list, columns=['DESIGNATOR'])
            
            df_bom_exploded = explode_designators(df_bom_raw, 'DESIGNATOR')
            merged = pd.merge(df_bom_exploded, df_pkp, on='DESIGNATOR', how='outer', indicator='DURUM')
            
            # BOM'da olup PKP'de olmayanlar
            missing_in_pkp = merged[merged['DURUM'] == 'left_only']['DESIGNATOR'].unique()

            # --- BUTONLAR ---
            col_btn1, col_btn2, col_msg = st.columns([1, 1, 3])
            
            with col_btn1:
                if st.button("✅ Listeyi Onayla", type="primary", use_container_width=True):
                    if len(missing_in_pkp) > 0:
                        st.session_state.confirmed = False
                        st.error(f"⚠️ HATA: BOM listesindeki {', '.join(missing_in_pkp)} referansları PKP dosyasında bulunamadı!")
                    else:
                        st.session_state.confirmed = True
                        st.rerun()
            
            with col_btn2:
                if st.session_state.confirmed:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        edited_df.drop(columns=['AYIRICI']).to_excel(writer, index=False)
                    st.download_button("📥 Listeyi İndir", output.getvalue(), "ozdisan_onayli_bom.xlsx", use_container_width=True)
            
            with col_msg:
                if st.session_state.confirmed:
                    st.success("✔️ Liste Onaylandı.")

            # --- ANALİZ SONUÇLARI ---
            if st.session_state.confirmed:
                st.markdown('<div class="table-spacer"></div>', unsafe_allow_html=True)
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.metric("BOM Kalemi", len(df_bom_exploded))
                m2.metric("PKP Kalemi", len(df_pkp))
                m3.metric("Tam Eşleşen", len(merged[merged['DURUM'] == 'both']))

                t1, t2, t3 = st.tabs(["✅ Eşleşenler", "❌ Sadece BOM", "⚠️ Sadece PKP"])
                with t1: st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']], use_container_width=True)
                with t2: st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']], use_container_width=True)
                with t3: st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']], use_container_width=True)

        else: st.error("DESIGNATOR sütunu bulunamadı!")
    except Exception as e: st.error(f"Hata: {e}")
