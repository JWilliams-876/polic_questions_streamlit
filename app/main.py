import streamlit as st
import pandas as pd
import random
from pathlib import Path
from rapidfuzz import fuzz

st.set_page_config(page_title="Policy Assessment", layout="wide")

st.title("Policy Knowledge Assessment")

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "policy_questions.xlsx"

@st.cache_data
def load_data(path):
    return pd.read_excel(path)

df = load_data(DATA_PATH)

df.columns = df.columns.str.strip().str.replace(" ", "")

# ---------------------------
# Sidebar Configuration
# ---------------------------
st.sidebar.header("User Profile")

division = st.sidebar.selectbox(
    "Division",
    ["Patrol", "Emergency Management", "Support Services", "Dispatch", "Business Office"]
)

role = None
if division == "Patrol":
    role = st.sidebar.selectbox("Role", ["LEO", "CSO"])

supervisor_status = st.sidebar.selectbox(
    "Supervisor Status",
    ["Supervisor", "Non-Supervisor"]
)

question_count = st.sidebar.slider("Number of Questions", 1, 20, 5)

# ---------------------------
# Filtering Logic
# ---------------------------
def division_match(row_divisions):
    if pd.isna(row_divisions):
        return False
    divisions = [d.strip() for d in str(row_divisions).split(",")]
    return division in divisions or "All Users" in divisions

filtered_df = df[df["Division"].apply(division_match)].copy()

if role and "Role" in filtered_df.columns:
    filtered_df = filtered_df[
        (filtered_df["Role"].isna()) |
        (filtered_df["Role"] == role)
    ]

if "Function" in filtered_df.columns:
    filtered_df["weight"] = 1.0
    if supervisor_status == "Supervisor":
        filtered_df.loc[
            filtered_df["Function"] == "Supervisor",
            "weight"
        ] = 1.6
else:
    filtered_df["weight"] = 1.0

# ---------------------------
# Initialize Session State
# ---------------------------
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
    st.session_state.current_question = 0
    st.session_state.score = 0
    st.session_state.selected_questions = []
if "responses" not in st.session_state:
    st.session_state.responses = []

# ---------------------------
# Start Quiz
# ---------------------------
if not st.session_state.quiz_started:
    if st.button("Start Assessment"):
        questions = filtered_df.to_dict("records")

        if len(questions) < question_count:
            st.warning("Not enough questions available for selection.")
        else:
            selected = random.choices(
                questions,
                weights=filtered_df["weight"].tolist(),
                k=question_count
            )

            st.session_state.selected_questions = selected
            st.session_state.quiz_started = True
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.rerun()

# ---------------------------
# Quiz In Progress
# ---------------------------
if st.session_state.quiz_started:

    q_index = st.session_state.current_question
    total = len(st.session_state.selected_questions)

    if q_index < total:
        question_data = st.session_state.selected_questions[q_index]
    
        st.subheader(f"Question {q_index + 1} of {total}")
    
        st.info(
            f"Policy {question_data.get('PolicyNumber', 'N/A')} – "
            f"{question_data.get('PolicyName', 'N/A')}"
        )
    
        st.write(question_data["Question"])
    
        input_key = f"answer_input_{q_index}"

        user_answer = st.text_input(
            "Your Answer",
            key=input_key
        )
    
        if st.button("Submit Answer"):
    
            correct_answer = str(question_data["Answer"]).strip().lower()
            submitted_answer = user_answer.strip().lower()
            
            # Build list of acceptable answers
            accepted_answers = [correct_answer]
            
            if "AcceptedAnswers" in question_data and pd.notna(question_data["AcceptedAnswers"]):
                additional = str(question_data["AcceptedAnswers"]).lower()
                accepted_answers.extend([a.strip() for a in additional.split(",")])
            
            # Check if submitted answer matches or is contained
            is_correct = any(
                fuzz.token_set_ratio(submitted_answer, ans) >= 60
                for ans in accepted_answers
            )
    
            if is_correct:
                st.session_state.score += 1

            # -----------------------------------
            # Special YES/NO Handling
            # -----------------------------------
            yes_no_correct = None
            
            if correct_answer.startswith("yes"):
                yes_no_correct = "yes"
            elif correct_answer.startswith("no"):
                yes_no_correct = "no"
            
            if yes_no_correct:
                is_correct = submitted_answer in ["yes", "y"] if yes_no_correct == "yes" else submitted_answer in ["no", "n"]
            else:
                # Fuzzy match for non yes/no questions
                is_correct = any(
                    fuzz.token_set_ratio(submitted_answer, ans) >= 60
                    for ans in accepted_answers
                )
    
            # Store response
            st.session_state.responses.append({
                "Policy Number": question_data.get("PolicyNumber", ""),
                "Policy Name": question_data.get("PolicyName", ""),
                "Question": question_data["Question"],
                "Submitted Answer": user_answer,
                "Correct Answer": question_data["Answer"],
                "Result": "Correct" if is_correct else "Incorrect"
            })
    
            # Clear answer field
            st.session_state.current_question += 1
            st.rerun()
    else:
        st.subheader("Assessment Complete")
    
        total_score = st.session_state.score
        percentage = (total_score / total) * 100
    
        st.markdown(f"### Final Score: {total_score} / {total}")
        st.markdown(f"### Score Percentage: {percentage:.1f}%")
    
        st.markdown("---")
        st.subheader("Detailed Results")
    
        results_df = pd.DataFrame(st.session_state.responses)
    
        st.dataframe(results_df, use_container_width=True)
    
        if st.button("Restart Assessment"):
            st.session_state.quiz_started = False
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.session_state.selected_questions = []
            st.session_state.responses = []
            st.rerun()

    
    





