import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="PCBA Kesin Analiz", layout="wide")

st.title("🔍 PCBA Karşılaştırma Paneli")

bom_file = st.file_uploader("1. BOM Listesi (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP Dosyası (TXT, CSV)", type=['txt', 'csv'])

if bom_file and pkp_file:
    try:
        # --- BOM OKUMA ---
        df_bom = pd.read_excel(bom_file)
        # Sütun isimlerini temizle
        df_bom.columns = [str(c).strip().upper() for c in df_bom.columns]
        
        # --- PKP OKUMA (Gelişmiş Manuel Ayıklama) ---
        raw_pkp = pkp_file.getvalue()
        try:
            content_pkp = raw_pkp.decode("utf-8")
        except:
            content_pkp = raw_pkp.decode("iso-8859-9")
        
        lines = content_pkp.splitlines()
        header_idx = next((i for i, l in enumerate(lines) if "Designator" in l), None)
        
        if header_idx is not None:
            # Sadece Designator sütununu çekmek için her satırın ilk kelimesini alıyoruz
            # Bu sayede Altium'daki açıklama (Description) kısmındaki karmaşa bizi bozamaz
            pkp_list = []
            for line in lines[header_idx + 1:]:
                parts = line.split() # Satırı boşluklara göre böl
                if len(parts) > 0:
                    pkp_list.append(parts[0]) # İlk kelime her zaman Designator'dır
            
            df_pkp = pd.DataFrame(pkp_list, columns=['DESIGNATOR'])
            
            # --- STANDARTLAŞTIRMA (Hatanın Çözüldüğü Yer) ---
            # .str. ekleyerek tüm sütuna işlem yapıyoruz
            df_bom['DESIGNATOR'] = df_bom['DESIGNATOR'].astype(str).str.strip().upper()
            df_pkp['DESIGNATOR'] = df_pkp['DESIGNATOR'].astype(str).str.strip().upper()

            # --- ANALİZ ---
            merged = pd.merge(df_bom[['DESIGNATOR']], df_pkp[['DESIGNATOR']], 
                              on='DESIGNATOR', how='outer', indicator='Sonuç')

            # Sekmelerle Görünüm
            tab1, tab2, tab3 = st.tabs(["✅ Eşleşenler", "❌ Sadece BOM'da", "⚠️ Sadece PKP'de"])

            with tab1:
                success_df = merged[merged['Sonuç'] == 'both']
                st.success(f"Toplam {len(success_df)} referans başarıyla eşleşti.")
                st.dataframe(success_df[['DESIGNATOR']], use_container_width=True)

            with tab2:
                bom_only = merged[merged['Sonuç'] == 'left_only']
                st.error(f"BOM'da olup PKP'de olmayan {len(bom_only)} parça.")
                st.dataframe(bom_only[['DESIGNATOR']], use_container_width=True)

            with tab3:
                pkp_only = merged[merged['Sonuç'] == 'right_only']
                st.warning(f"PKP'de olup BOM'da olmayan {len(pkp_only)} parça.")
                st.dataframe(pkp_only[['DESIGNATOR']], use_container_width=True)

    except Exception as e:
        st.error(f"Hata detayı: {e}")
