import streamlit as st
import pandas as pd
st.cache_data.clear()
st.set_page_config(page_title="PCBA Karşılaştırıcı", layout="wide")

st.title("🔌 PCBA BOM & PKP Analiz Aracı")
st.info("BOM ve PKP dosyalarındaki Designator (C1, R1 vb.) sütunlarının aynı isimde olduğundan emin olun.")

# Dosya Yükleme Alanları
col1, col2, col3 = st.columns(3)
with col1:
    bom_file = st.file_uploader("BOM Listesi (Excel)", type=['xlsx'])
with col2:
    pkp_file = st.file_uploader("PKP Koordinat (Excel)", type=['xlsx'])
with col3:
    stok_file = st.file_uploader("Güncel Stok (Excel)", type=['xlsx'])

if bom_file and pkp_file and stok_file:
    try:
        # Verileri Oku
        bom = pd.read_excel(bom_file)
        pkp = pd.read_excel(pkp_file)
        stok = pd.read_excel(stok_file)

        # Temizlik
        for df in [bom, pkp, stok]:
            df.columns = df.columns.astype(str).str.strip()

        # Eşleştirme: BOM + PKP
        # NOT: 'Designator' sütunu her iki dosyada da ortak olmalı
        birlesik = pd.merge(bom, pkp, on='Designator', how='outer', indicator='Durum')
        
        # Stokla Birleştirme
        # NOT: 'Part Number' sütunu BOM ve Stok dosyasında ortak olmalı
        final = pd.merge(birlesik, stok, on='Part Number', how='left')

        # Durum Analizi Fonksiyonu
        def analiz(row):
            if row['Durum'] == 'left_only': return "❌ PKP'de Yok"
            if row['Durum'] == 'right_only': return "⚠️ BOM'da Yok"
            if pd.isna(row.get('Stok Adedi')) or row.get('Stok Adedi', 0) <= 0: return "📉 Stok Yetersiz"
            return "✅ Hazır"

        final['Analiz_Sonucu'] = final.apply(analiz, axis=1)

        # Tabloyu Göster
        st.subheader("Analiz Sonuçları")
        st.dataframe(final, use_container_width=True)

        # Excel İndirme
        csv = final.to_csv(index=False).encode('utf-8-sig')
        st.download_button("Sonuçları CSV Olarak İndir", csv, "analiz_sonucu.csv", "text/csv")

    except Exception as e:

        st.error(f"Bir hata oluştu: {e}. Lütfen sütun başlıklarını kontrol edin.")
