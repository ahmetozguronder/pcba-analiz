import streamlit as st
import pandas as pd

# Sayfa ayarları
st.set_page_config(page_title="PCBA Analiz Aracı", layout="wide")

st.title("🔍 PCBA BOM & PKP Karşılaştırıcı")
st.markdown("BOM ve PKP dosyalarındaki referansları (Designator) saniyeler içinde eşleştirin.")

# 1. Dosya Yükleme Alanı
col1, col2 = st.columns(2)
with col1:
    bom_file = st.file_uploader("1. BOM Listesini Yükle (Excel)", type=['xlsx'])
with col2:
    pkp_file = st.file_uploader("2. PKP (Koordinat) Dosyasını Yükle (Excel)", type=['xlsx'])

if bom_file and pkp_file:
    try:
        # Verileri oku
        df_bom = pd.read_excel(bom_file)
        df_pkp = pd.read_excel(pkp_file)

        # Sütun başlıklarını temizle (Gizli boşlukları ve karakterleri siler)
        df_bom.columns = df_bom.columns.astype(str).str.strip()
        df_pkp.columns = df_pkp.columns.astype(str).str.strip()

        # Kritik Kontrol: Designator sütunu var mı?
        if 'Designator' not in df_bom.columns or 'Designator' not in df_pkp.columns:
            st.error("Hata: Her iki dosyada da tam olarak 'Designator' isimli bir sütun başlığı bulunmalıdır.")
            st.info(f"BOM Sütunları: {list(df_bom.columns)}")
            st.info(f"PKP Sütunları: {list(df_pkp.columns)}")
        else:
            # Eşleştirme yap
            merged = pd.merge(df_bom, df_pkp, on='Designator', how='outer', indicator='Durum')

            # Durum isimlerini Türkçeleştir
            mapping = {
                'left_only': '❌ Sadece BOM\'da Var (PKP Eksik)',
                'right_only': '⚠️ Sadece PKP\'de Var (BOM Eksik)',
                'both': '✅ Tam Eşleşme'
            }
            merged['Analiz_Sonucu'] = merged['Durum'].map(mapping)

            # Özet İstatistikler
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Benzersiz Parça", len(merged))
            c2.metric("✅ Tam Eşleşen", len(merged[merged['Durum'] == 'both']))
            c3.metric("🚨 Hatalı / Eksik", len(merged[merged['Durum'] != 'both']))

            # Filtreleme
            secim = st.radio("Tablo Görünümü:", ["Hepsi", "Sadece Hataları Göster"], horizontal=True)
            
            final_df = merged.copy()
            if secim == "Sadece Hataları Göster":
                final_df = merged[merged['Durum'] != 'both']

            # Sonucu Göster (Gereksiz teknik sütunu gizle)
            st.dataframe(final_df.drop(columns=['Durum']), use_container_width=True)

            # Excel Çıktısı
            csv = final_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Analiz Sonucunu İndir (.csv)", csv, "analiz.csv", "text/csv")

    except Exception as e:
        st.error(f"Beklenmedik bir hata oluştu: {e}")

else:
    st.info("Lütfen karşılaştırmak istediğiniz Excel dosyalarını yukarıdaki alanlara yükleyin.")
