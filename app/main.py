import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Policy Question Generator", layout="wide")

st.title("Policy Question Generator")

uploaded_file = st.file_uploader("Upload your policy question CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.sidebar.header("User Selection")

    division = st.sidebar.selectbox(
        "Select Your Division",
        ["Patrol", "Emergency Management", "Support Services", "Dispatch", "Business Office"]
    )

    role = None
    if division == "Patrol":
        role = st.sidebar.selectbox("Select Role", ["LEO", "CSO"])

    supervisor_status = st.sidebar.selectbox(
        "Supervisor Status",
        ["Supervisor", "Non-Supervisor"]
    )

    # Filtering
    def division_match(row_divisions):
        if pd.isna(row_divisions):
            return False
        divisions = [d.strip() for d in str(row_divisions).split(",")]
        return division in divisions or "All Users" in divisions

    filtered_df = df[df["Division"].apply(division_match)]

    # Role weighting
    if role and "Role" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Role"].isna()) |
            (filtered_df["Role"] == role)
        ]

    # Supervisor weighting (60% increase)
    if "Function" in filtered_df.columns:
        filtered_df["weight"] = 1.0

        if supervisor_status == "Supervisor":
            filtered_df.loc[
                filtered_df["Function"] == "Supervisor",
                "weight"
            ] = 1.6

        questions = filtered_df["Question"].tolist()
        weights = filtered_df["weight"].tolist()

        if questions:
            selected_question = random.choices(questions, weights=weights, k=1)[0]

            st.subheader("Generated Question")
            st.write(selected_question)
        else:
            st.warning("No questions match your selections.")

else:
    st.info("Upload a CSV file to begin.")
