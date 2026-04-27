import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="GCL Premium Calculator", layout="wide")

st.title("GCL Premium Calculator")
st.markdown("Upload customer data, select Product and Cover Type, and calculate premium.")

@st.cache_data
def load_rates():
    rates_df = pd.read_csv("normalized_rates.csv")
    return rates_df

def clean_string(value):
    if pd.isna(value):
        return None
    return str(value).strip().lower()

def validate_customer_file(df):
    required_cols = ["Customer_ID", "Customer_Name", "Age", "Tenure_Months", "Loan_Amount"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    return True

def find_rate(rates_df, product, cover_type, age, tenure):
    matched = rates_df[
        (rates_df["product"].astype(str).str.strip().str.lower() == clean_string(product)) &
        (rates_df["cover_type"].astype(str).str.strip().str.lower() == clean_string(cover_type)) &
        (rates_df["age_min"] <= age) &
        (rates_df["age_max"] >= age) &
        (rates_df["tenure_months"] == tenure)
    ]

    if matched.empty:
        return None

    return matched.iloc[0]["rate_per_lakh"]

def calculate_premium_row(row, rates_df, selected_product, selected_cover):
    try:
        age = int(row["Age"])
        tenure = int(row["Tenure_Months"])
        loan_amount = float(row["Loan_Amount"])

        if loan_amount <= 0:
            return pd.Series({
                "Selected_Product": selected_product,
                "Selected_Cover_Type": selected_cover,
                "Rate_Per_Lakh": None,
                "Premium": None,
                "Status": "Invalid Loan Amount"
            })

        rate = find_rate(rates_df, selected_product, selected_cover, age, tenure)

        if rate is None:
            return pd.Series({
                "Selected_Product": selected_product,
                "Selected_Cover_Type": selected_cover,
                "Rate_Per_Lakh": None,
                "Premium": None,
                "Status": "Rate not found"
            })

        premium = (loan_amount / 100000) * rate

        return pd.Series({
            "Selected_Product": selected_product,
            "Selected_Cover_Type": selected_cover,
            "Rate_Per_Lakh": round(rate, 2),
            "Premium": round(premium, 2),
            "Status": "Success"
        })

    except Exception as e:
        return pd.Series({
            "Selected_Product": selected_product,
            "Selected_Cover_Type": selected_cover,
            "Rate_Per_Lakh": None,
            "Premium": None,
            "Status": f"Error: {str(e)}"
        })

rates_df = load_rates()

products = sorted(rates_df["product"].dropna().unique().tolist())
covers = sorted(rates_df["cover_type"].dropna().unique().tolist())

st.sidebar.header("Calculation Settings")
selected_product = st.sidebar.selectbox("Select Product", products)
selected_cover = st.sidebar.selectbox("Select Cover Type", covers)

uploaded_file = st.file_uploader("Upload customer Excel file", type=["xlsx"])

st.markdown("### Required columns in upload file")
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

            st.subheader("Calculated Output")
            st.dataframe(result_df)

            success_count = (result_df["Status"] == "Success").sum()
            fail_count = (result_df["Status"] != "Success").sum()

            col1, col2 = st.columns(2)
            col1.metric("Successful Rows", int(success_count))
            col2.metric("Failed Rows", int(fail_count))

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
