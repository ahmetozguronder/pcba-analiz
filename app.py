import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="PCBA Akıllı Analiz", layout="wide")
st.title("🔍 PCBA BOM & PKP Karşılaştırıcı")

bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP Dosyasını Seç (TXT)", type=['txt'])

def explode_designators(df, col_name):
    """Hücre içindeki 'D1, D2, D3' gibi virgüllü yapıları ayırıp alt alta satır yapar."""
    # Sütundaki değerleri stringe çevir, virgüllere göre böl ve listeye at
    df[col_name] = df[col_name].astype(str).str.split(r'[,;\s]+')
    # Listeyi patlat (explode) ederek her elemanı yeni bir satır yap
    df = df.explode(col_name).reset_index(drop=True)
    # Boşlukları temizle
    df[col_name] = df[col_name].str.strip()
    # Boş kalan satırları temizle
    df = df[df[col_name] != ""]
    return df

if bom_file and pkp_file:
    try:
        # --- 1. BOM OKUMA VE AYRIŞTIRMA ---
        df_bom_raw = pd.read_excel(bom_file)
        df_bom_raw.columns = [str(c).strip().upper() for c in df_bom_raw.columns]
        
        if 'DESIGNATOR' in df_bom_raw.columns:
            # Virgülle birleşik olanları (D1, D2...) ayırıyoruz
            df_bom = explode_designators(df_bom_raw[['DESIGNATOR']], 'DESIGNATOR')
            df_bom['DESIGNATOR'] = df_bom['DESIGNATOR'].str.upper()
        else:
            st.error("BOM dosyasında 'DESIGNATOR' sütunu bulunamadı!")
            st.stop()

        # --- 2. PKP OKUMA ---
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
                    ref = parts[0].strip()
                    if len(ref) > 1 and "=" not in ref and "-" not in ref:
                        pkp_list.append(ref.upper())
        
        df_pkp = pd.DataFrame(pkp_list, columns=['DESIGNATOR'])

        # --- 3. KIYASLAMA ---
        merged = pd.merge(
            df_bom, 
            df_pkp, 
            on='DESIGNATOR', 
            how='outer', 
            indicator='DURUM',
            suffixes=('_BOM', '_PKP')
        )

        # --- 4. GÖRSEL PANEL ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("BOM (Ayrıştırılmış)", len(df_bom))
        c2.metric("PKP (Altium)", len(df_pkp))
        c3.metric("Tam Eşleşen ✅", len(merged[merged['DURUM'] == 'both']))

        t1, t2, t3 = st.tabs(["✅ Tam Eşleşenler", "❌ Sadece BOM'da Var", "⚠️ Sadece PKP'de Var"])

        with t1:
            st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']], use_container_width=True)
        with t2:
            st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']], use_container_width=True)
        with t3:
            st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']], use_container_width=True)

    except Exception as e:
        st.error(f"Hata: {e}")

