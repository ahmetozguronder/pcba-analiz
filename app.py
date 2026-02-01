import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="PCBA Tam Analiz", layout="wide")

st.title("🔍 PCBA Karşılaştırma Paneli")

bom_file = st.file_uploader("1. BOM Listesi (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP Dosyası (TXT, CSV)", type=['txt', 'csv'])

def smart_read_pkp(content):
    lines = content.splitlines()
    header_idx = -1
    for i, line in enumerate(lines):
        if "Designator" in line:
            header_idx = i
            break
    
    if header_idx == -1:
        return None

    # Altium'un karmaşık boşluk yapısını çözmek için tırnakları ve sütunları temizleyerek oku
    data_lines = lines[header_idx:]
    clean_data = "\n".join(data_lines)
    
    # on_bad_lines='skip' ile o 13-16 sütun farkı hatasını engelliyoruz
    df = pd.read_csv(io.StringIO(clean_content), sep=r'\s+', engine='python', on_bad_lines='skip')
    return df

if bom_file and pkp_file:
    try:
        # --- OKUMA ---
        df_bom = pd.read_excel(bom_file)
        df_bom.columns = [str(c).strip().capitalize() for c in df_bom.columns]
        
        raw_pkp = pkp_file.getvalue()
        try:
            content_pkp = raw_pkp.decode("utf-8")
        except:
            content_pkp = raw_pkp.decode("iso-8859-9")
        
        # PKP içeriğini temizleyerek oku
        lines = content_pkp.splitlines()
        header_line = next((i for i, l in enumerate(lines) if "Designator" in l), None)
        
        if header_line is not None:
            # Altium'un Description kısmındaki boşluklar tabloyu bozmasın diye 
            # sadece ilk 6 sütunu (Designator, Comment, Layer, Footprint, X, Y) almaya odaklanıyoruz
            df_pkp = pd.read_csv(io.StringIO("\n".join(lines[header_line:])), sep=r'\s+', engine='python', on_bad_lines='skip')
            df_pkp.columns = [str(c).strip().capitalize() for c in df_pkp.columns]
            
            # --- ANALİZ ---
            # Referansları temizle
            df_bom['Designator'] = df_bom['Designator'].astype(str).str.strip().upper()
            df_pkp['Designator'] = df_pkp['Designator'].astype(str).str.strip().upper()

            # Merge
            merged = pd.merge(df_bom, df_pkp, on='Designator', how='outer', indicator='Sonuç')

            # Sekmelerle Görünüm
            tab1, tab2, tab3 = st.tabs(["✅ Eşleşenler", "❌ Sadece BOM'da", "⚠️ Sadece PKP'de"])

            with tab1:
                success_df = merged[merged['Sonuç'] == 'both']
                st.write(f"Toplam {len(success_df)} referans başarıyla eşleşti.")
                st.dataframe(success_df, use_container_width=True)

            with tab2:
                bom_only = merged[merged['Sonuç'] == 'left_only']
                st.write(f"BOM'da olup PKP'de olmayan {len(bom_only)} parça bulundu.")
                st.dataframe(bom_only, use_container_width=True)

            with tab3:
                pkp_only = merged[merged['Sonuç'] == 'right_only']
                st.write(f"PKP'de olup BOM'da tanımlanmayan {len(pkp_only)} parça bulundu.")
                st.dataframe(pkp_only, use_container_width=True)

    except Exception as e:
        st.error(f"Hata detayı: {e}")
