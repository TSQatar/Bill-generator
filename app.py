import streamlit as st
import pandas as pd
from processor import extract_data_from_image, format_bill_output, create_summary_dataframe
import io

st.set_page_config(page_title="TSQA Bill Extractor", page_icon="🧾", layout="wide")

st.title("🧾 TSQA Bill Extractor")
st.markdown("Upload screenshots from **Temu**, **Shein**, or **Noon** to generate a provisional bill.")

# Sidebar for configuration
with st.sidebar:
    st.header("Settings")
    store_name = st.selectbox(
        "Select Store",
        ["Temu", "Shein", "Noon"],
        index=0
    )
    api_key_input = st.text_input("Gemini API Key (Optional)", type="password", help="Leave empty if set in .env")

# Main content
uploaded_files = st.file_uploader("Upload Screenshots", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    if st.button("Generate Bill"):
        with st.status("Processing...", expanded=True) as status:
            st.write("📤 Reading image files...")
            all_items = []
            
            # Process each image
            for uploaded_file in uploaded_files:
                st.write(f"🤖 Analyzing {uploaded_file.name} with Gemini AI...")
                # Save temp file or pass bytes? 
                # processor.py uses Image.open() which accepts file-like objects.
                # Streamlit UploadedFile is a file-like object.
                items = extract_data_from_image(uploaded_file)
                all_items.extend(items)
            
            if not all_items:
                status.update(label="Failed", state="error", expanded=True)
                st.error("No items could be extracted. Please check the image quality or API key.")
            else:
                status.update(label="Complete!", state="complete", expanded=False)
                # Generate Output
                bill_text, subtotal = format_bill_output(all_items, store_name)
                df_summary = create_summary_dataframe(all_items)
                
                # Display Results
                st.subheader("Generated Bill")
                st.text_area("Copy this text:", value=bill_text, height=400)
                
                st.subheader("Summary Table")
                st.dataframe(df_summary, use_container_width=True)
                
                # Export Options
                # CSV
                csv = df_summary.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download CSV",
                    csv,
                    "bill_summary.csv",
                    "text/csv",
                    key='download-csv'
                )
                
                # Excel (requires openpyxl)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_summary.to_excel(writer, index=False, sheet_name='Sheet1')
                
                st.download_button(
                    label="Download Excel",
                    data=buffer,
                    file_name="bill_summary.xlsx",
                    mime="application/vnd.ms-excel"
                )

st.markdown("---")
st.caption("Powered by Google Gemini & TSQA")
