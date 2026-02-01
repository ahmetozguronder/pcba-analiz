import streamlit as st
import pandas as pd
import io
import re

# Sayfa yapılandırması
st.set_page_config(page_title="Özdisan PCBA Analiz", layout="wide", page_icon="⚡")

# --- CSS: BAŞLIK VE AYIRICI SÜTUN VURGUSU ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] th {
        font-weight: bold !important;
    }
    /* EN SAĞDAKİ DÜZENLEME SÜTUNU: Özdisan Mavisi */
    [data-testid="stDataEditor"] th:last-child {
        background-color: #0056b3 !important;
        color: white !important;
    }
    .table-spacer {
        margin-top: 50px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. BAŞLIK VE ÜST BİLGİ ---
col_title, col_note = st.columns([2.5, 1])
with col_title:
    st.markdown("<h1 style='color: #0056b3; margin-bottom: 0;'>ÖZDISAN PCBA ANALİZ MERKEZİ</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 18px; color: #555;'>BOM Listesi ve PKP Dosyası Karşılaştırma Paneli</p>", unsafe_allow_html=True)
with col_note:
    st.info("**💡 ÖNEMLİ NOT:**\n\nHızlı teklif süreci için lütfen listelerinizde **Özdisan Stok Kodlarını** belirtiniz.")

st.divider()

# Dosya Yükleme
bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP Dosyasını Seç (TXT)", type=['txt'])

def explode_designators(df, col_name):
    df_copy = df.copy()
    df_copy[col_name] = df_copy[col_name].astype(str).str.split(r'[,;\s]+')
    df_copy = df_copy.explode(col_name).reset_index(drop=True)
    df_copy[col_name] = df_copy[col_name].str.strip()
    df_copy = df_copy[df_copy[col_name] != ""]
    return df_copy

if bom_file and pkp_file:
    try:
        # --- 2. VERİ HAZIRLIK ---
        df_bom_raw = pd.read_excel(bom_file)
        df_bom_raw.columns = [str(c).strip().upper() for c in df_bom_raw.columns]
        potential_code_cols = ['PART NUMBER', 'STOCK CODE', 'COMMENT', 'DESCRIPTION', 'ÜRÜN KODU', 'MALZEME KODU']
        code_col = next((c for c in potential_code_cols if c in df_bom_raw.columns), df_bom_raw.columns[0])

        if 'DESIGNATOR' in df_bom_raw.columns:
            df_bom_raw['DESIGNATOR'] = df_bom_raw['DESIGNATOR'].astype(str).str.upper()
            df_bom_raw['ADET_SAYISI'] = df_bom_raw['DESIGNATOR'].apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() else 0)
            
            summary_df = df_bom_raw.groupby(code_col).agg({
                'ADET_SAYISI': 'sum',
                'DESIGNATOR': lambda x: ', '.join(x.unique())
            }).reset_index()
            
            summary_df.columns = ['BOM_KODU', 'TOPLAM_ADET', 'REFERANSLAR']
            summary_df['AYIRICI'] = "➡️" 
            summary_df['DÜZENLEME ALANI'] = summary_df['BOM_KODU']
            summary_df = summary_df[['BOM_KODU', 'TOPLAM_ADET', 'REFERANSLAR', 'AYIRICI', 'DÜZENLEME ALANI']]

            # --- 3. DÜZENLENEBİLİR TABLO ---
            st.subheader("🛠️ 1. Adım: BOM Listesini Gözden Geçirin")
            
            if 'confirmed' not in st.session_state:
                st.session_state.confirmed = False

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

            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                if st.button("✅ Listeyi Onayla", type="primary", use_container_width=True):
                    st.session_state.confirmed = True
                    st.rerun()
            
            with col_btn2:
                if st.session_state.confirmed:
                    st.markdown("<p style='color: #28a745; font-weight: bold; margin-top: 10px;'>✔️ Liste Onaylandı.</p>", unsafe_allow_html=True)

            # --- 4. ANALİZ VE İNDİRME (SADECE ONAYLANDIYSA) ---
            if st.session_state.confirmed:
                st.markdown('<div class="table-spacer"></div>', unsafe_allow_html=True)
                st.divider()
                
                # İndirme Butonunu Öne Çıkaralım
                st.subheader("📥 2. Adım: Onaylı Listeyi İndir")
                
                # Excel Dosyasını Hazırla (Ok sütununu atarak)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_export = edited_df.drop(columns=['AYIRICI'])
                    final_export.to_excel(writer, index=False)
                
                st.download_button(
                    label="💾 Onaylı BOM Dosyasını İndir (.xlsx)",
                    data=output.getvalue(),
                    file_name="ozdisan_onayli_bom_listesi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help="Bu dosyayı Özdisan teklif sürecinde kullanabilirsiniz."
                )

                st.divider()
                st.subheader("📊 3. Adım: Analiz ve Kıyaslama Detayları")

                # Analiz Hesaplamaları
                raw_bytes = pkp_file.getvalue()
                try: content = raw_bytes.decode("utf-8")
                except: content = raw_bytes.decode("iso-8859-9")
                
                lines = content.splitlines()
                h_idx = next((i for i, l in enumerate(lines) if "Designator" in l), None)
                
                pkp_list = []
                if h_idx is not None:
                    for line in lines[h_idx + 1:]:
                        parts = line.split()
                        if parts:
                            ref = parts[0].strip().upper()
                            if len(ref) > 1 and "=" not in ref and "-" not in ref:
                                pkp_list.append(ref)
                
                df_pkp = pd.DataFrame(pkp_list, columns=['DESIGNATOR'])
                df_bom_exploded = explode_designators(df_bom_raw, 'DESIGNATOR')
                merged = pd.merge(df_bom_exploded, df_pkp, on='DESIGNATOR', how='outer', indicator='DURUM')

                m1, m2, m3 = st.columns(3)
                m1.metric("BOM Parça", len(df_bom_exploded))
                m2.metric("PKP Parça", len(df_pkp))
                m3.metric("Tam Eşleşen ✅", len(merged[merged['DURUM'] == 'both']))

                t1, t2, t3 = st.tabs(["✅ Tam Eşleşenler", "❌ Sadece BOM", "⚠️ Sadece PKP"])
                with t1: st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']], use_container_width=True)
                with t2: st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']], use_container_width=True)
                with t3: st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']], use_container_width=True)

        else:
            st.error("BOM dosyasında 'DESIGNATOR' sütunu bulunamadı!")
    except Exception as e:
        st.error(f"Sistem Hatası: {e}")
