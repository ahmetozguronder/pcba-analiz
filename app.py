import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Dinamik PCBA Analiz", layout="wide")

st.title("🔍 Akıllı BOM & PKP Karşılaştırıcı")
st.info("Bu sürüm dosya başındaki gereksiz satırları otomatik atlar ve 'Designator' sütununu kendisi bulur.")

# Dosya Yükleme
bom_file = st.file_uploader("1. BOM Dosyasını Yükle (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP / Koordinat Dosyasını Yükle (TXT, CSV)", type=['txt', 'csv'])

def find_header_and_read(file_content, target_col="DESIGNATOR"):
    """Dosya içindeki başlık satırını dinamik olarak bulur."""
    lines = file_content.splitlines()
    for i, line in enumerate(lines):
        # Satırı temizle ve hedef kelimeyi ara
        if target_col.upper() in line.upper():
            # Başlık satırını bulduk! Buradan itibaren dataframe oluştur.
            clean_content = "\n".join(lines[i:])
            # Birden fazla boşluk veya tab karakterine göre ayır
            df = pd.read_csv(io.StringIO(clean_content), sep=r'\s+', engine='python')
            return df
    return None

if bom_file and pkp_file:
    try:
        # --- BOM OKUMA ---
        df_bom = pd.read_excel(bom_file)
        df_bom.columns = [str(c).strip().upper() for c in df_bom.columns]

        # --- PKP OKUMA (Dinamik Arama) ---
        raw_pkp = pkp_file.getvalue()
        try:
            content_pkp = raw_pkp.decode("utf-8")
        except:
            content_pkp = raw_pkp.decode("iso-8859-9")

        df_pkp = find_header_and_read(content_pkp)

        if df_pkp is None:
            st.error("PKP dosyasında 'Designator' sütunu bulunamadı!")
        else:
            df_pkp.columns = [str(c).strip().upper() for c in df_pkp.columns]

            # --- EŞLEŞTİRME ---
            st.divider()
            
            # Sütunları standartlaştır (Büyük harf ve temiz veri)
            df_bom['DESIGNATOR'] = df_bom['DESIGNATOR'].astype(str).str.strip().upper()
            df_pkp['DESIGNATOR'] = df_pkp['DESIGNATOR'].astype(str).str.strip().upper()

            # Merge (Kıyaslama)
            # Sadece 'DESIGNATOR' üzerinden dış birleştirme yapıyoruz
            merged = pd.merge(df_bom[['DESIGNATOR']], df_pkp[['DESIGNATOR']], 
                              on='DESIGNATOR', how='outer', indicator='DURUM')

            # Sonuçları Gruplandır
            missing_in_pkp = merged[merged['DURUM'] == 'left_only']['DESIGNATOR'].tolist()
            missing_in_bom = merged[merged['DURUM'] == 'right_only']['DESIGNATOR'].tolist()

            # Görselleştirme
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.error(f"❌ PKP'de Eksik ({len(missing_in_pkp)} Adet)")
                st.write("BOM'da var ama koordinat listesinde yok:")
                st.caption(", ".join(missing_in_pkp) if missing_in_pkp else "Eksik yok.")

            with col_b:
                st.warning(f"⚠️ BOM'da Eksik ({len(missing_in_bom)} Adet)")
                st.write("Koordinat listesinde var ama BOM'da yok:")
                st.caption(", ".join(missing_in_bom) if missing_in_bom else "Eksik yok.")

            if not missing_in_pkp and not missing_in_bom:
                st.balloons()
                st.success("Tebrikler! İki dosya %100 uyumlu.")

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
