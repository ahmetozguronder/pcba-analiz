import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="PCBA Profesyonel Analiz", layout="wide")
st.title("🔍 PCBA BOM & PKP Karşılaştırıcı")

bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP Dosyasını Seç (TXT)", type=['txt'])

def explode_designators(df, col_name):
    """Hücre içindeki 'D1, D2' gibi yapıları ayırır ve her birini bir satır yapar."""
    # Orijinal sütunu koruyarak kopyala
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
        
        # Ürün kodu sütununu bulmaya çalış (PART NUMBER, COMMENT veya ITEM CODE olabilir)
        potential_code_cols = ['PART NUMBER', 'COMMENT', 'DESCRIPTION', 'ÜRÜN KODU', 'MALZEME KODU']
        code_col = next((c for c in potential_code_cols if c in df_bom_raw.columns), df_bom_raw.columns[1] if len(df_bom_raw.columns) > 1 else df_bom_raw.columns[0])

        if 'DESIGNATOR' in df_bom_raw.columns:
            # Önce adet hesabı için ham veriyi sakla
            # Virgülleri ayırmadan önce her satırda kaç komponent olduğunu say
            df_bom_raw['ADET'] = df_bom_raw['DESIGNATOR'].astype(str).apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() else 0)
            
            # Şimdi referansları eşleşme için patlat (explode)
            df_bom_exploded = explode_designators(df_bom_raw, 'DESIGNATOR')
            df_bom_exploded['DESIGNATOR'] = df_bom_exploded['DESIGNATOR'].str.upper()
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

        # --- 3. KIYASLAMA VE ÖZET TABLO ---
        merged = pd.merge(df_bom_exploded, df_pkp, on='DESIGNATOR', how='outer', indicator='DURUM')

        # Ürün Kodu Bazlı Özet (Pivot Tablo)
        # Sadece BOM'da olan parçalar üzerinden adet toplamı alıyoruz
        summary_df = df_bom_raw[[code_col, 'ADET']].groupby(code_col).sum().reset_index()
        summary_df.columns = ['ÜRÜN KODU / AÇIKLAMA', 'TOPLAM ADET']

        # --- 4. GÖRSEL PANEL ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("BOM Toplam Komponent", summary_df['TOPLAM ADET'].sum())
        m2.metric("PKP (Dizilecek) Komponent", len(df_pkp))
        m3.metric("Fark", summary_df['TOPLAM ADET'].sum() - len(df_pkp))

        # Sekmeler
        t0, t1, t2, t3 = st.tabs(["📊 Ürün Özet Listesi", "✅ Tam Eşleşenler", "❌ Sadece BOM'da Var", "⚠️ Sadece PKP'de Var"])

        with t0:
            st.subheader("BOM Malzeme ve Adet Listesi")
            st.dataframe(summary_df, use_container_width=True)
            
            # Excel İndirme Butonu
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                summary_df.to_excel(writer, index=False)
            st.download_button("Özet Listeyi İndir (.xlsx)", output.getvalue(), "bom_ozet.xlsx")

        with t1:
            st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']], use_container_width=True)
        with t2:
            st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']], use_container_width=True)
        with t3:
            st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']], use_container_width=True)

    except Exception as e:
        st.error(f"Hata: {e}")
