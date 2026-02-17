import streamlit as st
import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz

st.set_page_config(page_title="Policy Assessment", layout="wide")
st.title("Policy Knowledge Assessment")

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "policy_questions.xlsx"

@st.cache_data
def load_data(path):
    return pd.read_excel(path)

df = load_data(DATA_PATH)

# Normalize column names
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

question_count = st.sidebar.slider("Number of Questions", 1, 100, 20)

# ---------------------------
# Filtering Logic
# ---------------------------
def division_match(row_divisions):
    if pd.isna(row_divisions):
        return False
    divisions = [d.strip() for d in str(row_divisions).split(",")]
    return division in divisions or "AllUsers" in divisions or "All Users" in divisions

filtered_df = df[df["Division"].apply(division_match)].copy()

if role and "Role" in filtered_df.columns:
    filtered_df = filtered_df[
        (filtered_df["Role"].isna()) |
        (filtered_df["Role"] == role)
    ]

# Apply weighting
filtered_df["weight"] = 1.0
if "Function" in filtered_df.columns and supervisor_status == "Supervisor":
    filtered_df.loc[
        filtered_df["Function"] == "Supervisor",
        "weight"
    ] = 1.6

# ---------------------------
# Initialize Session State
# ---------------------------
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
    st.session_state.current_question = 0
    st.session_state.selected_questions = []
    st.session_state.responses = []

# ---------------------------
# Start Quiz
# ---------------------------
if not st.session_state.quiz_started:
    if st.button("Start Assessment"):

        if len(filtered_df) < question_count:
            st.warning("Not enough questions available for selection.")
        else:
            selected_dfs = []

            if "Chapter" in filtered_df.columns:
                chapters = filtered_df["Chapter"].dropna().unique()
                questions_per_chapter = question_count // len(chapters)

                # Balanced first pass
                for chapter in chapters:
                    chapter_df = filtered_df[filtered_df["Chapter"] == chapter]
                    sample_size = min(len(chapter_df), questions_per_chapter)

                    if sample_size > 0:
                        sampled = chapter_df.sample(
                            n=sample_size,
                            weights="weight",
                            replace=False
                        )
                        selected_dfs.append(sampled)

                combined_df = pd.concat(selected_dfs) if selected_dfs else pd.DataFrame()

                # Fill remaining slots
                remaining_needed = question_count - len(combined_df)

                if remaining_needed > 0:
                    remaining_pool = filtered_df.drop(combined_df.index, errors="ignore")

                    additional = remaining_pool.sample(
                        n=remaining_needed,
                        weights="weight",
                        replace=False
                    )
                    combined_df = pd.concat([combined_df, additional])

                final_df = combined_df.sample(frac=1).reset_index(drop=True)

            else:
                # If no Chapter column, simple weighted sampling
                final_df = filtered_df.sample(
                    n=question_count,
                    weights="weight",
                    replace=False
                ).reset_index(drop=True)

            st.session_state.selected_questions = final_df.to_dict("records")
            st.session_state.quiz_started = True
            st.session_state.current_question = 0
            st.session_state.responses = []
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
        user_answer = st.text_input("Your Answer", key=input_key)

        if st.button("Submit Answer"):

            correct_answer = str(question_data["Answer"]).strip().lower()
            submitted_answer = user_answer.strip().lower()

            # Build accepted answers list
            accepted_answers = [correct_answer]

            if "AcceptedAnswers" in question_data and pd.notna(question_data["AcceptedAnswers"]):
                additional = str(question_data["AcceptedAnswers"]).lower()
                accepted_answers.extend([a.strip() for a in additional.split(",")])

            # YES/NO detection
            yes_no_correct = None
            if correct_answer.startswith("yes"):
                yes_no_correct = "yes"
            elif correct_answer.startswith("no"):
                yes_no_correct = "no"

            if yes_no_correct:
                is_correct = submitted_answer.startswith(yes_no_correct)
            else:
                is_correct = any(
                    max(
                        fuzz.token_set_ratio(submitted_answer, ans),
                        fuzz.partial_ratio(submitted_answer, ans)
                    ) >= 85
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

            st.session_state.current_question += 1
            st.rerun()

    else:
        st.subheader("Assessment Complete")

        results_df = pd.DataFrame(st.session_state.responses)

        total_score = int((results_df["Result"] == "Correct").sum())
        total = len(results_df)
        percentage = (total_score / total) * 100 if total else 0

        st.markdown(f"### Final Score: {total_score} / {total}")
        st.markdown(f"### Score Percentage: {percentage:.1f}%")

        st.markdown("---")
        st.subheader("Detailed Results")

        st.dataframe(results_df, use_container_width=True)

        if st.button("Restart Assessment"):
            st.session_state.quiz_started = False
            st.session_state.current_question = 0
            st.session_state.selected_questions = []
            st.session_state.responses = []
            st.rerun()
