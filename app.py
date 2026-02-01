import streamlit as st
import pandas as pd
import io
import re

# Sayfa yapılandırması
st.set_page_config(page_title="Özdisan PCBA Analiz", layout="wide", page_icon="⚡")

# --- ÜST BÖLÜM (MAVİ TONLU BAŞLIK VE NOT) ---
col_title, col_note = st.columns([2.5, 1])

with col_title:
    st.markdown("<h1 style='color: #0056b3; margin-bottom: 0;'>ÖZDISAN PCBA ANALİZ MERKEZİ</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 18px; color: #555;'>BOM Listesi ve PKP Dosyası Karşılaştırma Paneli</p>", unsafe_allow_html=True)

with col_note:
    st.info("**💡 ÖNEMLİ NOT:**\n\nHızlı teklif süreci için lütfen listelerinizde **Özdisan Stok Kodlarını** belirtiniz.")

st.divider()

col_left, col_right = st.columns(2)
with col_left:
    bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
with col_right:
    pkp_file = st.file_uploader("2. PKP / Koordinat Dosyasını Seç (TXT)", type=['txt'])

def check_code_quality(code):
    """Kodun kalitesini kontrol eder ve müşteri için not üretir."""
    code_str = str(code).strip()
    # Eğer hücre boşsa veya 5 karakterden kısaysa (anlamsız açıklama varsayımı)
    if not code_str or len(code_str) < 5 or code_str.lower() in ['direnç', 'resistor', 'cap', 'kondansatör']:
        return "⚠️ Lütfen Özdisan Kodu veya Ürün Linki Ekleyiniz"
    return "✅ Kod Mevcut"

def explode_designators(df, col_name):
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
        
        potential_code_cols = ['PART NUMBER', 'STOCK CODE', 'COMMENT', 'DESCRIPTION', 'ÜRÜN KODU', 'MALZEME KODU']
        code_col = next((c for c in potential_code_cols if c in df_bom_raw.columns), df_bom_raw.columns[0])

        if 'DESIGNATOR' in df_bom_raw.columns:
            # --- Müşteriye Not Sütunu Oluşturma ---
            df_bom_raw['DURUM NOTU'] = df_bom_raw[code_col].apply(check_code_quality)
            
            df_bom_raw['DESIGNATOR'] = df_bom_raw['DESIGNATOR'].astype(str).str.upper()
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

            # --- 3. ÖZET TABLO ---
            df_bom_raw['ADET'] = df_bom_raw['DESIGNATOR'].apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() else 0)
            
            # Özet tabloda 'DURUM NOTU'nu da dahil ediyoruz
            summary_df = df_bom_raw.groupby([code_col, 'DURUM NOTU']).agg({
                'ADET': 'sum',
                'DESIGNATOR': lambda x: ', '.join(x)
            }).reset_index()
            summary_df.columns = ['MALZEME KODU / AÇIKLAMA', 'MÜŞTERİ AKSİYONU', 'TOPLAM ADET', 'REFERANSLAR']

            merged = pd.merge(df_bom_exploded, df_pkp, on='DESIGNATOR', how='outer', indicator='DURUM')

            # --- 4. GÖRSEL PANEL ---
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("BOM Toplam Parça", int(summary_df['TOPLAM ADET'].sum()))
            with m2: st.metric("PKP Dizilecek", len(df_pkp))
            with m3: st.metric("Fark", int(summary_df['TOPLAM ADET'].sum() - len(df_pkp)))

            tabs = st.tabs(["🔵 Özdisan Malzeme Listesi", "✅ Eşleşenler", "❌ BOM'da Var", "⚠️ PKP'de Var"])

            with tabs[0]:
                st.warning("⚠️ 'MÜŞTERİ AKSİYONU' sütununda uyarı olan satırlar için lütfen Özdisan Stok Kodu veya ürün linki sağlayınız.")
                # Renklendirme fonksiyonu (Opsiyonel: Tabloyu daha okunaklı kılar)
                def highlight_action(val):
                    color = 'orange' if '⚠️' in str(val) else 'white'
                    return f'background-color: {color}'
                
                st.dataframe(summary_df, use_container_width=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    summary_df.to_excel(writer, index=False)
                st.download_button("📥 Analizli Listeyi İndir (.xlsx)", output.getvalue(), "ozdisan_analiz_raporu.xlsx")

            with tabs[1]: st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']], use_container_width=True)
            with tabs[2]: st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']], use_container_width=True)
            with tabs[3]: st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']], use_container_width=True)
        else:
            st.error("BOM dosyasında 'DESIGNATOR' sütunu bulunamadı!")

    except Exception as e:
        st.error(f"Sistem Hatası: {e}")
