import streamlit as st
import pandas as pd
from io import BytesIO
from premium_engine import validate_customer_file, calculate_premium_row

st.set_page_config(page_title="GCL Premium Calculator", layout="wide")

st.title("GCL Premium Calculator")
st.markdown("Upload customer data, select Product and Cover Type, and calculate premium.")

@st.cache_data
def load_rates():
    rates_df = pd.read_csv("normalized_rates.csv")
    return rates_df

rates_df = load_rates()

products = sorted(rates_df["product"].dropna().unique().tolist())
covers = sorted(rates_df["cover_type"].dropna().unique().tolist())

st.sidebar.header("Calculation Settings")
selected_product = st.sidebar.selectbox("Select Product", products)
selected_cover = st.sidebar.selectbox("Select Cover Type", covers)

st.subheader("Upload Customer Excel File")
uploaded_file = st.file_uploader("Upload .xlsx file", type=["xlsx"])

st.markdown("### Required input columns")
st.code("Customer_ID, Customer_Name, Age, Tenure_Months, Loan_Amount")

if uploaded_file is not None:
    try:
        customer_df = pd.read_excel(uploaded_file)

        st.subheader("Uploaded Data Preview")
        st.dataframe(customer_df.head())

        validate_customer_file(customer_df)

        if st.button("Calculate Premium"):
            result_df = customer_df.copy()

            calc_output = result_df.apply(
                lambda row: calculate_premium_row(
                    row=row,
                    rates_df=rates_df,
                    selected_product=selected_product,
                    selected_cover=selected_cover
                ),
                axis=1
            )

            result_df = pd.concat([result_df, calc_output], axis=1)

            st.subheader("Calculated Premium Output")
            st.dataframe(result_df)

            success_count = (result_df["Status"] == "Success").sum()
            fail_count = (result_df["Status"] != "Success").sum()

            col1, col2 = st.columns(2)
            col1.metric("Successful Rows", success_count)
            col2.metric("Failed Rows", fail_count)

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                result_df.to_excel(writer, index=False, sheet_name="Premium_Output")

            st.download_button(
                label="Download Output Excel",
                data=output.getvalue(),
                file_name="premium_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error: {str(e)}")
