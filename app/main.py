import streamlit as st
import pandas as pd
import random
from pathlib import Path

st.set_page_config(page_title="Policy Question Generator", layout="wide")

st.title("Policy Question Generator")

# ---------------------------
# Load Excel from repository
# ---------------------------
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "policy_questions.xlsx"

@st.cache_data
def load_data(path):
    return pd.read_excel(path)

try:
    df = load_data(DATA_PATH)
except Exception as e:
    st.error(f"Error loading Excel file: {e}")
    st.stop()

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

# ---------------------------
# Filtering
# ---------------------------
def division_match(row_divisions):
    if pd.isna(row_divisions):
        return False
    divisions = [d.strip() for d in str(row_divisions).split(",")]
    return division in divisions or "All Users" in divisions

filtered_df = df[df["Division"].apply(division_match)].copy()

# Role filtering
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
        selected_question = random.choices(
            questions,
            weights=weights,
            k=1
        )[0]
    
        st.subheader("Generated Question")
        st.write(selected_question)
    
        # ---------------------------
        # Answer Input Section
        # ---------------------------
        st.markdown("---")
        st.subheader("Your Answer")
    
        user_answer = st.text_area(
            "Type your response below:",
            height=150
        )
    
        if st.button("Submit Answer"):
            if user_answer.strip() == "":
                st.warning("Please enter a response before submitting.")
            else:
                st.success("Answer submitted successfully.")
                st.write("**Recorded Response:**")
                st.write(user_answer)

else:
    st.error("Missing required 'Function' column in Excel file.")

