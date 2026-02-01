import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="PCBA Analiz - TXT Destekli", layout="wide")

st.title("📂 PCBA BOM (Excel) & PKP (TXT/Excel) Kıyaslama")

col1, col2 = st.columns(2)
with col1:
    bom_file = st.file_uploader("1. BOM Listesini Yükle (Excel)", type=['xlsx'])
with col2:
    pkp_file = st.file_uploader("2. PKP Dosyasını Yükle (TXT, CSV veya Excel)", type=['txt', 'csv', 'xlsx'])

if bom_file and pkp_file:
    try:
        # --- BOM OKUMA ---
        df_bom = pd.read_excel(bom_file)
        df_bom.columns = [str(c).strip().upper() for c in df_bom.columns]

        # --- PKP OKUMA (Esnek Format) ---
        if pkp_file.name.endswith('.xlsx'):
            df_pkp = pd.read_excel(pkp_file)
        else:
            # TXT veya CSV okuma: Boşluklara (sep='\s+') göre ayırır
            # Bu yöntem genelde P&P makinelerinin çıktısı için en iyisidir
            content = pkp_file.getvalue().decode("utf-8")
            df_pkp = pd.read_csv(io.StringIO(content), sep=None, engine='python')

        df_pkp.columns = [str(c).strip().upper() for c in df_pkp.columns]

        st.divider()
        c1, c2 = st.columns(2)
        
        # Sütun Seçimi
        bom_ref_col = c1.selectbox("BOM Referans Sütunu:", df_bom.columns, 
                                   index=list(df_bom.columns).index('DESIGNATOR') if 'DESIGNATOR' in df_bom.columns else 0)
        
        pkp_ref_col = c2.selectbox("PKP Referans Sütunu (Koordinat Dosyası):", df_pkp.columns, 
                                   index=list(df_pkp.columns).index('DESIGNATOR') if 'DESIGNATOR' in df_pkp.columns else 0)

        if st.button("Kıyaslamayı Başlat"):
            # Değerleri standartlaştır
            df_bom[bom_ref_col] = df_bom[bom_ref_col].astype(str).str.strip().upper()
            df_pkp[pkp_ref_col] = df_pkp[pkp_ref_col].astype(str).str.strip().upper()

            # Merge işlemi
            merged = pd.merge(df_bom, df_pkp, left_on=bom_ref_col, right_on=pkp_ref_col, how='outer', indicator='DURUM')

            # Analiz sonuçlarını Türkçeleştir
            mapping = {'left_only': '❌ BOM\'da var, PKP\'de yok', 
                       'right_only': '⚠️ PKP\'de var, BOM\'da yok', 
                       'both': '✅ Tam Eşleşme'}
            merged['ANALİZ SONUCU'] = merged['DURUM'].map(mapping)

            # İstatistikler
            st.success("Analiz Bitti!")
            
            # Sonuçları göster
            filter_err = st.checkbox("Sadece Uyuşmazlıkları Göster", value=True)
            display_df = merged[merged['DURUM'] != 'both'] if filter_err else merged
            
            st.dataframe(display_df.drop(columns=['DURUM']), use_container_width=True)

    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        st.info("İpucu: TXT dosyasının sütunları düzgün ayrılmamış olabilir.")
