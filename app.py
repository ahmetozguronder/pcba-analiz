import streamlit as st
import pandas as pd
import io
import re

# Sayfa yapılandırması
st.set_page_config(page_title="PCBA Analiz - Kesin Çözüm", layout="wide")

st.title("🔍 PCBA BOM & PKP Karşılaştırıcı")
st.markdown("Altium ve Excel dosyaları arasındaki referans uyuşmazlıklarını sıfır hata ile bulur.")

# Dosya Yükleme
col_l, col_r = st.columns(2)
with col_l:
    bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
with col_r:
    pkp_file = st.file_uploader("2. PKP Dosyasını Seç (TXT)", type=['txt'])

def ultra_clean(text):
    """Metin içindeki boşluk, tab ve tüm özel karakterleri temizler."""
    if pd.isna(text): return ""
    # Sadece harfleri ve rakamları tutar (Örn: 'D 1' -> 'D1')
    return re.sub(r'[^A-Za-z0-9]', '', str(text)).upper()

if bom_file and pkp_file:
    try:
        # --- 1. BOM OKUMA ---
        df_bom_raw = pd.read_excel(bom_file)
        df_bom_raw.columns = [str(c).strip().upper() for c in df_bom_raw.columns]
        
        if 'DESIGNATOR' not in df_bom_raw.columns:
            st.error("BOM dosyasında 'DESIGNATOR' sütunu bulunamadı!")
        else:
            # --- 2. PKP OKUMA ---
            raw_bytes = pkp_file.getvalue()
            try:
                content = raw_bytes.decode("utf-8")
            except:
                content = raw_bytes.decode("iso-8859-9")
            
            lines = content.splitlines()
            h_idx = next((i for i, l in enumerate(lines) if "Designator" in l), None)
            
            pkp_refs = []
            if h_idx is not None:
                for line in lines[h_idx + 1:]:
                    parts = line.split()
                    if parts:
                        ref = parts[0].strip()
                        # Çizgileri ve başlık tekrarlarını engelle
                        if len(ref) > 1 and "=" not in ref and "-" not in ref:
                            pkp_refs.append(ref)
            
            df_pkp_raw = pd.DataFrame(pkp_refs, columns=['DESIGNATOR'])

            # --- 3. TEMİZLEME VE EŞLEŞTİRME ---
            # Orijinal isimleri kaybetmemek için temizlenmiş hallerini yeni sütuna yazıyoruz
            df_bom_raw['CLEAN'] = df_bom_raw['DESIGNATOR'].apply(ultra_clean)
            df_pkp_raw['CLEAN'] = df_pkp_raw['DESIGNATOR'].apply(ultra_clean)

            # Eşleştirme (Temizlenmiş sütunlar üzerinden)
            merged = pd.merge(
                df_bom_raw[['DESIGNATOR', 'CLEAN']], 
                df_pkp_raw[['DESIGNATOR', 'CLEAN']], 
                on='CLEAN', 
                how='outer', 
                indicator='DURUM',
                suffixes=('_BOM', '_PKP')
            )

            # --- 4. SONUÇLAR ---
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("BOM Listesi", len(df_bom_raw))
            c2.metric("PKP Listesi", len(df_pkp_raw))
            c3.metric("Tam Eşleşen", len(merged[merged['DURUM'] == 'both']))

            t1, t2, t3 = st.tabs(["✅ Tam Eşleşenler", "❌ Sadece BOM'da Var", "⚠️ Sadece PKP'de Var"])

            with t1:
                # Eşleşenleri göster (BOM'daki orijinal adıyla)
                st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR_BOM']].rename(columns={'DESIGNATOR_BOM': 'Designator'}), use_container_width=True)

            with t2:
                # Sadece BOM'da olanlar
                st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR_BOM']].rename(columns={'DESIGNATOR_BOM': 'Designator'}), use_container_width=True)

            with t3:
                # Sadece PKP'de olanlar
                st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR_PKP']].rename(columns={'DESIGNATOR_PKP': 'Designator'}), use_container_width=True)

    except Exception as e:
        st.error(f"Sistem Hatası: {e}")
