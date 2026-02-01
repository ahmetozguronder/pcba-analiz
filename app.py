import streamlit as st
import pandas as pd
import io
import re

# Sayfa yapılandırması
st.set_page_config(page_title="Özdisan PCBA Analiz", layout="wide", page_icon="⚡")

# --- 1. GÖRSEL DÜZENLEME (CSS) ---
# Tabloyu beyazlatır ve başlıkları belirginleştirir
st.markdown("""
    <style>
    [data-testid="stDataEditor"] div {
        background-color: #ffffff !important;
    }
    [data-testid="stDataEditor"] th {
        background-color: #f0f2f6 !important;
        color: #31333F !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MAVİ ÖZDİSAN BAŞLIĞI VE SAĞ ÜST NOT ---
col_title, col_note = st.columns([2.5, 1])

with col_title:
    st.markdown("<h1 style='color: #0056b3; margin-bottom: 0;'>ÖZDISAN PCBA ANALİZ MERKEZİ</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 18px; color: #555;'>BOM Listesi ve PKP Dosyası Karşılaştırma Paneli</p>", unsafe_allow_html=True)

with col_note:
    st.info("**💡 ÖNEMLİ NOT:**\n\nHızlı teklif süreci için lütfen listelerinizde **Özdisan Stok Kodlarını** belirtiniz.")

st.divider()

# Dosya Yükleme Alanları
bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
pkp_file = st.file_uploader("2. PKP Dosyasını Seç (TXT)", type=['txt'])

def explode_designators(df, col_name):
    """Hücre içindeki 'D1, D2' gibi yapıları ayırıp alt alta satır yapar."""
    df_copy = df.copy()
    df_copy[col_name] = df_copy[col_name].astype(str).str.split(r'[,;\s]+')
    df_copy = df_copy.explode(col_name).reset_index(drop=True)
    df_copy[col_name] = df_copy[col_name].str.strip()
    df_copy = df_copy[df_copy[col_name] != ""]
    return df_copy

if bom_file and pkp_file:
    try:
        # --- 3. BOM OKUMA VE HAZIRLIK ---
        df_bom_raw = pd.read_excel(bom_file)
        df_bom_raw.columns = [str(c).strip().upper() for c in df_bom_raw.columns]
        
        # Ürün Kodu Sütun Tespiti
        potential_code_cols = ['PART NUMBER', 'STOCK CODE', 'COMMENT', 'DESCRIPTION', 'ÜRÜN KODU', 'MALZEME KODU']
        code_col = next((c for c in potential_code_cols if c in df_bom_raw.columns), df_bom_raw.columns[0])

        if 'DESIGNATOR' in df_bom_raw.columns:
            # Temizlik ve Adet Hesaplama
            df_bom_raw['DESIGNATOR'] = df_bom_raw['DESIGNATOR'].astype(str).str.upper()
            df_bom_raw['ADET_SAYISI'] = df_bom_raw['DESIGNATOR'].apply(lambda x: len(re.split(r'[,;\s]+', x.strip())) if x.strip() else 0)
            
            # --- 4. DÜZENLENEBİLİR MÜŞTERİ PANELİ (GÜNCEL GRUPLAMA) ---
            summary_df = df_bom_raw.groupby(code_col).agg({
                'ADET_SAYISI': 'sum',
                'DESIGNATOR': lambda x: ', '.join(x.unique())
            }).reset_index()
            
            # Sütun isimlerini manuel set ediyoruz
            summary_df.columns = ['BOM_KODU', 'TOPLAM_ADET', 'REFERANSLAR']
            
            # HÜCRE SEVİYESİNDE SEMBOL EKLEME (✍️)
            # Prefix hatası almamak için metnin başına doğrudan ekliyoruz
            summary_df['✍️ GÜNCELLEME (KOD VEYA LİNK)'] = summary_df['BOM_KODU'].apply(lambda x: f"✍️ {x}")
            
            # Sütunları istenen sıraya diz
            summary_df = summary_df[['✍️ GÜNCELLEME (KOD VEYA LİNK)', 'BOM_KODU', 'TOPLAM_ADET', 'REFERANSLAR']]

            st.markdown("""
            <div style="background-color: #e8f4f8; padding: 15px; border-radius: 8px; border: 1px solid #bce8f1; margin-bottom: 10px;">
                <h4 style="color: #31708f; margin-top: 0;">🛠️ Düzenleme Paneli</h4>
                <p style="color: #31708f; font-size: 14px;">
                    En soldaki <b>'✍️ GÜNCELLEME'</b> sütununa çift tıklayarak eksik kodları tamamlayabilirsiniz. Değişiklik yapmazsanız orijinal kodlar geçerli sayılır.
                </p>
            </div>
            """, unsafe_allow_html=True)

            edited_df = st.data_editor(
                summary_df,
                use_container_width=True,
                column_config={
                    "✍️ GÜNCELLEME (KOD VEYA LİNK)": st.column_config.TextColumn("✍️ DÜZENLEME ALANI", width="large"),
                    "BOM_KODU": st.column_config.TextColumn("ORİJİNAL BOM KODU", disabled=True),
                    "TOPLAM_ADET": st.column_config.NumberColumn("TOPLAM ADET", disabled=True),
                    "REFERANSLAR": st.column_config.TextColumn("REFERANSLAR", disabled=True)
                },
                hide_index=True
            )

            if st.button("🚀 Listeyi Onayla ve Analizi Göster", type="primary", use_container_width=True):
                st.balloons()
                st.success("BOM Listesi Onaylandı!")

            # --- 5. PKP OKUMA VE KIYASLAMA ---
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
            
            merged = pd.merge(
                df_bom_exploded, 
                df_pkp, 
                on='DESIGNATOR', 
                how='outer', 
                indicator='DURUM'
            )

            # --- 6. SONUÇ METRİKLERİ VE TABLAR ---
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("BOM (Toplam Parça)", len(df_bom_exploded))
            c2.metric("PKP (Altium)", len(df_pkp))
            c3.metric("Tam Eşleşen ✅", len(merged[merged['DURUM'] == 'both']))

            t1, t2, t3 = st.tabs(["✅ Tam Eşleşenler", "❌ Sadece BOM'da Var", "⚠️ Sadece PKP'de Var"])

            with t1:
                st.dataframe(merged[merged['DURUM'] == 'both'][['DESIGNATOR']], use_container_width=True)
            with t2:
                st.dataframe(merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']], use_container_width=True)
            with t3:
                st.dataframe(merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']], use_container_width=True)

            # İndirme Butonu
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Veriyi indirirken hücre başındaki kalem sembolünü temizliyoruz
                export_df = edited_df.copy()
                export_df['✍️ GÜNCELLEME (KOD VEYA LİNK)'] = export_df['✍️ GÜNCELLEME (KOD VEYA LİNK)'].str.replace('✍️ ', '', regex=False)
                export_df.to_excel(writer, index=False)
            st.download_button("📥 Onaylı Özdisan Listesini İndir (.xlsx)", output.getvalue(), "ozdisan_onayli_bom.xlsx", use_container_width=True)

        else:
            st.error("BOM dosyasında 'DESIGNATOR' sütunu bulunamadı!")

    except Exception as e:
        st.error(f"Sistem Hatası: {e}")
