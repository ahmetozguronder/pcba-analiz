import streamlit as st
import pandas as pd
import io

# Sayfa yapılandırması
st.set_page_config(page_title="PCBA Analiz Merkezi", layout="wide")

st.title("🔍 PCBA BOM & PKP Karşılaştırıcı")
st.markdown("Altium ve diğer tasarım programlarından gelen dosyaları dinamik olarak analiz eder.")

# Dosya Yükleme Alanları
col_left, col_right = st.columns(2)
with col_left:
    bom_file = st.file_uploader("1. BOM Dosyasını Seç (Excel)", type=['xlsx'])
with col_right:
    pkp_file = st.file_uploader("2. PKP / Koordinat Dosyasını Seç (TXT)", type=['txt'])

if bom_file and pkp_file:
    try:
        # --- 1. BOM DOSYASINI OKUMA ---
        df_bom_raw = pd.read_excel(bom_file)
        # Sütun isimlerini standartlaştır
        df_bom_raw.columns = [str(c).strip().upper() for c in df_bom_raw.columns]
        
        # --- 2. PKP DOSYASINI DİNAMİK OKUMA ---
        raw_pkp_bytes = pkp_file.getvalue()
        try:
            content_pkp = raw_pkp_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content_pkp = raw_pkp_bytes.decode("iso-8859-9")
        
        lines = content_pkp.splitlines()
        # "Designator" kelimesinin geçtiği satırı bul (Header arama)
        header_idx = next((i for i, l in enumerate(lines) if "Designator" in l), None)
        
        if header_idx is None:
            st.error("PKP dosyasında 'Designator' sütun başlığı bulunamadı. Lütfen dosya içeriğini kontrol edin.")
        else:
            pkp_list = []
            # Header'dan sonraki satırları işle
            for line in lines[header_idx + 1:]:
                parts = line.split() # Boşluklara göre böl
                if len(parts) > 0:
                    designator_candidate = parts[0].strip()
                    # Ayırıcı çizgileri (====) ve çok kısa anlamsız karakterleri ele
                    if len(designator_candidate) > 1 and "=" not in designator_candidate:
                        pkp_list.append(designator_candidate)
            
            df_pkp_final = pd.DataFrame(pkp_list, columns=['DESIGNATOR'])

            # --- 3. VERİ TEMİZLEME VE BÜYÜK HARF YAPMA (KRİTİK NOKTA) ---
            # .str.upper() kullanarak Series hatasını engelliyoruz
            if 'DESIGNATOR' in df_bom_raw.columns:
                df_bom_clean = pd.DataFrame()
                df_bom_clean['DESIGNATOR'] = df_bom_raw['DESIGNATOR'].astype(str).str.strip().str.upper()
                
                df_pkp_final['DESIGNATOR'] = df_pkp_final['DESIGNATOR'].astype(str).str.strip().str.upper()

                # --- 4. KARŞILAŞTIRMA (MERGE) ---
                merged = pd.merge(
                    df_bom_clean, 
                    df_pkp_final, 
                    on='DESIGNATOR', 
                    how='outer', 
                    indicator='DURUM'
                )

                # --- 5. GÖRSEL PANEL VE SEKMELER ---
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.metric("BOM Satır Sayısı", len(df_bom_clean))
                m2.metric("PKP Komponent Sayısı", len(df_pkp_final))
                m3.metric("Tam Eşleşen", len(merged[merged['DURUM'] == 'both']))

                tab1, tab2, tab3 = st.tabs(["✅ Eşleşenler", "❌ Sadece BOM'da Var", "⚠️ Sadece PKP'de Var"])

                with tab1:
                    match_df = merged[merged['DURUM'] == 'both'][['DESIGNATOR']]
                    st.dataframe(match_df, use_container_width=True)

                with tab2:
                    bom_only = merged[merged['DURUM'] == 'left_only'][['DESIGNATOR']]
                    st.dataframe(bom_only, use_container_width=True)
                    if not bom_only.empty:
                        st.warning(f"Bu {len(bom_only)} parça PKP dosyasında bulunamadı!")

                with tab3:
                    pkp_only = merged[merged['DURUM'] == 'right_only'][['DESIGNATOR']]
                    st.dataframe(pkp_only, use_container_width=True)
                    if not pkp_only.empty:
                        st.info(f"Bu {len(pkp_only)} parça BOM listesinde tanımlı değil.")
            else:
                st.error("BOM dosyasında 'Designator' isimli bir sütun bulunamadı.")

    except Exception as e:
        st.error(f"Beklenmedik bir hata: {e}")
