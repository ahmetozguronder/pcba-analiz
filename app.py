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
            # --- ANALİZ HAZIRLIĞI ---
            df_bom_raw['DESIGNATOR'] = df_bom_raw['DESIGNATOR'].astype(str).str.upper()
            df_bom_raw['ADET'] = df_bom_raw['DESIGNATOR'].apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() else 0)
            
            # Özet Tablo Oluşturma
            summary_df = df_bom_raw.groupby(code_col).agg({
                'ADET': 'sum',
                'DESIGNATOR': lambda x: ', '.join(x)
            }).reset_index()
            
            # Müşteri Aksiyon Sütunu (Default olarak mevcut kod yazılıyor)
            summary_df['MÜŞTERİ ONAYI / GÜNCEL KOD'] = summary_df[code_col]
            summary_df.columns = ['BOM KODU', 'ADET', 'REFERANSLAR', 'MÜŞTERİ ONAYI / GÜNCEL KOD']

            # --- DİNAMİK EDİTÖR ---
            st.subheader("🔵 Özdisan Malzeme Onay Paneli")
            st.markdown("""
            *Aşağıdaki tabloda **'MÜŞTERİ ONAYI / GÜNCEL KOD'** sütununa tıklayarak eksik kodları tamamlayabilir veya link ekleyebilirsiniz.*
            """)

            # Tabloyu düzenlenebilir yapıyoruz
            edited_df = st.data_editor(
                summary_df,
                use_container_width=True,
                column_config={
                    "MÜŞTERİ ONAYI / GÜNCEL KOD": st.column_config.TextColumn(
                        "Güncel Kod / Link Girişi",
                        help="Eksikse Özdisan kodunu veya ürün linkini buraya yazın.",
                        width="large"
                    ),
                    "ADET": st.column_config.NumberColumn(disabled=True),
                    "BOM KODU": st.column_config.TextColumn(disabled=True),
                    "REFERANSLAR": st.column_config.TextColumn(disabled=True)
                },
                hide_index=True
            )

            if st.button("✅ Listeyi Onayla ve Analizi Tamamla", type="primary"):
                st.balloons()
                st.success("BOM Listesi başarıyla güncellendi ve onaylandı!")
                
                # Onaylanmış listeyi indirme butonu
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    edited_df.to_excel(writer, index=False)
                st.download_button("📥 Onaylı Listeyi İndir (.xlsx)", output.getvalue(), "onayli_ozdisan_listesi.xlsx")

            # --- EŞLEŞME ANALİZİ (Görsel Sekmeler) ---
            st.divider()
            df_pkp = pd.DataFrame()
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
            
            df_bom_exploded = explode_designators(df_bom_raw, 'DESIGNATOR')
            merged = pd.merge(df_bom_exploded, df_pkp, on='DESIGNATOR', how='outer', indicator='DURUM')

            tabs = st.tabs(["✅ Eşleşenler", "❌ Sadece BOM'da Var", "⚠️ Sadece PKP'de Var"])
            with tabs[0]: st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']], use_container_width=True)
            with tabs[1]: st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']], use_container_width=True)
            with tabs[2]: st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']], use_container_width=True)

        else:
            st.error("BOM dosyasında 'DESIGNATOR' sütunu bulunamadı!")

    except Exception as e:
        st.error(f"Sistem Hatası: {e}")
