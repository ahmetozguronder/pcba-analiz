import streamlit as st
import pandas as pd
import io
import re

# Sayfa yapılandırması
st.set_page_config(page_title="Özdisan PCBA Analiz", layout="wide", page_icon="⚡")

# --- BAŞLIK BÖLÜMÜ ---
st.markdown("<h1 style='text-align: center; color: #E63946;'>ÖZDISAN PCBA ANALİZ MERKEZİ</h1>", unsafe_content_usage=True)
st.markdown("<p style='text-align: center;'>BOM Listesi ve Altium PKP Dosyası Karşılaştırma Paneli</p>", unsafe_content_usage=True)
st.divider()

# Dosya Yükleme Alanları
col_left, col_right = st.columns(2)
with col_left:
    bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
with col_right:
    pkp_file = st.file_uploader("2. PKP / Koordinat Dosyasını Seç (TXT)", type=['txt'])

def explode_designators(df, col_name):
    """Hücre içindeki virgüllü yapıları ayırır ve her birini bir satır yapar."""
    df = df.copy()
    df[col_name] = df[col_name].astype(str).str.split(r'[,;\s]+')
    df = df.explode(col_name).reset_index(drop=True)
    df[col_name] = df[col_name].str.strip()
    df = df[df[col_name] != ""]
    return df

if bom_file and pkp_file:
    try:
        # --- 1. BOM OKUMA ---
        df_bom_raw = pd.read_excel(bom_file)
        df_bom_raw.columns = [str(c).strip().upper() for c in df_bom_raw.columns]
        
        # Ürün kodu sütununu bul (Özdisan formatına uygun sütunları arar)
        potential_code_cols = ['PART NUMBER', 'STOCK CODE', 'COMMENT', 'DESCRIPTION', 'ÜRÜN KODU', 'MALZEME KODU']
        code_col = next((c for c in potential_code_cols if c in df_bom_raw.columns), df_bom_raw.columns[0])

        if 'DESIGNATOR' in df_bom_raw.columns:
            # Referansları standartlaştır
            df_bom_raw['DESIGNATOR'] = df_bom_raw['DESIGNATOR'].astype(str).str.upper()
            
            # Eşleşme için patlatılmış liste
            df_bom_exploded = explode_designators(df_bom_raw, 'DESIGNATOR')
            
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
                        ref = parts[0].strip().upper()
                        if len(ref) > 1 and "=" not in ref and "-" not in ref:
                            pkp_list.append(ref)
            
            df_pkp = pd.DataFrame(pkp_list, columns=['DESIGNATOR'])

            # --- 3. ÖZET TABLO OLUŞTURMA ---
            # Adet hesabı
            df_bom_raw['ADET'] = df_bom_raw['DESIGNATOR'].apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() else 0)
            
            # Gruplandırılmış tablo (Ürün + Adet + Tüm Referanslar)
            summary_df = df_bom_raw.groupby(code_col).agg({
                'ADET': 'sum',
                'DESIGNATOR': lambda x: ', '.join(x)
            }).reset_index()
            summary_df.columns = ['MALZEME KODU / AÇIKLAMA', 'TOPLAM ADET', 'REFERANSLAR']

            # Genel Eşleşme Analizi
            merged = pd.merge(df_bom_exploded, df_pkp, on='DESIGNATOR', how='outer', indicator='DURUM')

            # --- 4. GÖRSEL PANEL ---
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("BOM Toplam Parça", summary_df['TOPLAM ADET'].sum())
            with m2:
                st.metric("PKP Dizilecek", len(df_pkp))
            with m3:
                fark = summary_df['TOPLAM ADET'].sum() - len(df_pkp)
                st.metric("Eksik/Fazla", fark, delta_color="inverse" if fark != 0 else "normal")

            tabs = st.tabs(["📊 Özdisan Malzeme Listesi", "✅ Eşleşenler", "❌ BOM'da Olup PKP'de Olmayan", "⚠️ PKP'de Olup BOM'da Olmayan"])

            with tabs[0]:
                st.subheader("Malzeme ve Referans Özet Tablosu")
                st.dataframe(summary_df, use_container_width=True)
                
                # Excel İndirme
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    summary_df.to_excel(writer, index=False)
                st.download_button("📥 Özdisan Malzeme Listesini İndir (.xlsx)", output.getvalue(), "ozdisan_malzeme_ozet.xlsx")

            with tabs[1]:
                match_df = merged[merged['DURUM'] == 'both'][['DESIGNATOR']]
                st.success(f"{len(match_df)} adet komponent tam eşleşti.")
                st.dataframe(match_df, use_container_width=True)

            with tabs[2]:
                bom_only = merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']]
                st.error(f"{len(bom_only)} adet parça PKP dosyasında eksik!")
                st.dataframe(bom_only, use_container_width=True)

            with tabs[3]:
                pkp_only = merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']]
                st.warning(f"{len(pkp_only)} adet parça BOM listesinde yok!")
                st.dataframe(pkp_only, use_container_width=True)

        else:
            st.error("Yüklenen Excel dosyasında 'DESIGNATOR' sütunu bulunamadı!")

    except Exception as e:
        st.error(f"Beklenmedik bir hata oluştu: {e}")
