import streamlit as st
from textblob import TextBlob
import matplotlib.pyplot as plt
import numpy as np
import os
import json
import requests
import cv2
from deepface import DeepFace

# --- DEPLOYMENT AUTHORIZATION CHECK ---
# This section serves as a deterrent for unauthorized public deployment.
# It checks for a specific environment variable. If not found or not set to "TRUE",
# the application will display a warning and stop.
# IMPORTANT: This is a software-level deterrent and not a foolproof security measure.
# Legal licensing (as outlined in README.md) is the primary method for controlling usage.
AUTHORIZED_DEPLOYMENT_FLAG = os.getenv("AI_INTERVIEW_COACH_AUTHORIZED_DEPLOYMENT", "FALSE").upper()

if AUTHORIZED_DEPLOYMENT_FLAG != "TRUE":
    st.error("""
    **Unauthorized Deployment Detected!**
    This AI Interview Coach application is intended for personal and educational use.
    Public deployment or redistribution requires explicit permission from the original author.

    If you are the authorized deployer, please ensure the environment variable
    `AI_INTERVIEW_COACH_AUTHORIZED_DEPLOYMENT` is set to `TRUE`.

    The application will not proceed without proper authorization.
    """)
    st.stop() # Halts the Streamlit application execution

# --- Configuration and API Key Setup ---
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_api_key: # Check if key is empty
        st.warning("GEMINI_API_KEY environment variable not set. "
                   "If running locally, please set it. "
                   "Assuming Canvas will inject it for deployment.")
except KeyError:
    st.warning("GEMINI_API_KEY not found in environment variables. Assuming Canvas will inject it.")
    gemini_api_key = ""

# --- Helper Functions ---

def generate_feedback(category: str, answer: str) -> str:
    """
    Sends the user's answer to Google Gemini API with an embedded prompt
    to generate comprehensive feedback.
    """
    if not answer.strip():
        return "Please provide an answer to receive feedback."

    prompt = f"""
    You are an AI Interview Coach. Your goal is to provide constructive and detailed feedback
    on interview answers. The user has provided an answer for a question in the '{category}' category.

    Please analyze the following aspects of the answer:
    1.  **Content and Relevance:** Is the answer directly addressing the question? Is it comprehensive?
    2.  **Structure and Clarity:** Is the answer well-organized, logical, and easy to understand?
    3.  **Conciseness:** Is the answer to the point without unnecessary jargon or rambling?
    4.  **Impact and Examples:** Does the answer provide specific examples or demonstrate impact where appropriate (e.g., STAR method for behavioral questions)?
    5.  **Strengths:** What did the user do well?
    6.  **Areas for Improvement:** What could the user improve? Be specific and actionable.
    7.  **Overall Score/Rating:** Provide a simple rating (e.g., 1-5, or Poor, Fair, Good, Excellent).

    Interview Category: {category}
    User's Answer: "{answer}"

    Please provide your feedback in a clear, markdown-formatted response.
    """

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"

    chatHistory = []
    chatHistory.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": chatHistory,
        "generationConfig": {
            "maxOutputTokens": 800,
            "temperature": 0.7,
        }
    }

    headers = {'Content-Type': 'application/json'}

    try:
        with st.spinner("Generating feedback with AI (Gemini)..."):
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()

            if result.get("candidates") and len(result["candidates"]) > 0 and \
               result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts") and \
               len(result["candidates"][0]["content"]["parts"]) > 0:
                feedback = result["candidates"][0]["content"]["parts"][0]["text"]
                return feedback
            else:
                st.error(f"Gemini API response structure unexpected: {result}")
                return "An error occurred while parsing Gemini feedback. Please try again."

    except requests.exceptions.RequestException as e:
        st.error(f"Gemini API Request Error: {e}")
        return "An error occurred while connecting to Gemini API. Please check your network or API key."
    except json.JSONDecodeError as e:
        st.error(f"Failed to decode JSON response from Gemini API: {e}")
        return "An error occurred while processing Gemini feedback. Please try again."
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return "An unexpected error occurred. Please try again."

def analyze_sentiment(text: str):
    """
    Performs sentiment analysis on the given text using TextBlob.
    Returns polarity (-1.0 to 1.0) and subjectivity (0.0 to 1.0).
    """
    if not text.strip():
        return {"polarity": 0.0, "subjectivity": 0.0}

    analysis = TextBlob(text)
    return {
        "polarity": analysis.sentiment.polarity,
        "subjectivity": analysis.sentiment.subjectivity
    }

def analyze_emotion_from_image(image_bytes):
    """
    Analyzes facial emotion from a single image using DeepFace.
    Returns dominant emotion and emotion scores.
    """
    if image_bytes is None:
        return None, "No image provided."

    try:
        # Convert image bytes to numpy array
        np_array = np.frombuffer(image_bytes, np.uint8)
        # Decode image using OpenCV
        img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if img is None:
            return None, "Could not decode image. Please try another picture."

        # Analyze emotions using DeepFace
        with st.spinner("Analyzing facial emotions..."):
            demographies = DeepFace.analyze(
                img_path=img,
                actions=['emotion'],
                enforce_detection=False
            )

        if demographies:
            dominant_emotion = demographies[0]['dominant_emotion']
            emotion_scores = demographies[0]['emotion']
            return dominant_emotion, emotion_scores
        else:
            return None, "No face detected in the image."

    except Exception as e:
        st.error(f"Error analyzing image for emotions: {e}")
        return None, f"An error occurred during emotion analysis: {e}"

# --- Streamlit UI ---

st.set_page_config(page_title="AI Interview Coach", layout="wide")

st.title("🎓 AI Interview Coach")
st.markdown("""
Welcome to your personal AI Interview Coach! Practice your interview skills,
get instant feedback on your answers, and improve your confidence.
""")

# --- Interview Question Category Selection ---
st.header("1. Select Interview Category")
question_category = st.selectbox(
    "Choose a category for your practice question:",
    ("HR (Human Resources)", "Technical (Software Engineering)", "Behavioral (STAR Method)", "Product Management", "Data Science"),
    index=0
)

# --- Answer Input ---
st.header("2. Your Answer")
st.markdown("""
Type or paste your answer to an interview question below.
*(Voice recording integration (e.g., Whisper API) is a planned future enhancement.)*
""")

user_answer = st.text_area(
    "Enter your answer here:",
    height=250,
    placeholder=f"e.g., 'Tell me about yourself.' (for {question_category} category)"
)

# --- Submit Button ---
if st.button("Get Feedback", type="primary"):
    if not user_answer.strip():
        st.warning("Please enter your answer before getting feedback.")
    else:
        st.header("3. Feedback Report")
        ai_feedback = generate_feedback(question_category, user_answer)
        st.subheader("🤖 AI-Powered Feedback")
        st.markdown(ai_feedback)

        st.markdown("---")

        st.subheader("😊 Sentiment Analysis")
        sentiment_results = analyze_sentiment(user_answer)
        polarity = sentiment_results["polarity"]
        subjectivity = sentiment_results["subjectivity"]

        st.write(f"**Polarity (Emotion):** {polarity:.2f} (closer to 1.0 is positive, -1.0 is negative)")
        st.write(f"**Subjectivity (Opinion):** {subjectivity:.2f} (closer to 1.0 is opinion, 0.0 is factual)")

        fig, ax = plt.subplots(1, 2, figsize=(10, 4))

        ax[0].bar(['Polarity'], [polarity], color=['skyblue' if polarity >= 0 else 'salmon'])
        ax[0].set_ylim([-1, 1])
        ax[0].set_title('Sentiment Polarity')
        ax[0].axhline(0, color='grey', linewidth=0.8)
        ax[0].text(0, polarity, f'{polarity:.2f}', ha='center', va='bottom' if polarity >= 0 else 'top')

        ax[1].bar(['Subjectivity'], [subjectivity], color=['lightgreen'])
        ax[1].set_ylim([0, 1])
        ax[1].set_title('Sentiment Subjectivity')
        ax[1].text(0, subjectivity, f'{subjectivity:.2f}', ha='center', va='bottom')

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        st.markdown("---")

        st.subheader("👁️ Facial Emotion Detection")
        st.markdown("""
        Take a picture using your webcam to get an analysis of your facial emotions.
        This feature processes a single image, not real-time video, which is more
        suitable for web deployment like Streamlit Cloud.
        """)

        camera_image = st.camera_input("Smile for the camera!")

        if camera_image is not None:
            dominant_emotion, emotion_data = analyze_emotion_from_image(camera_image.getvalue())

            if dominant_emotion:
                st.success(f"**Dominant Emotion Detected: {dominant_emotion.capitalize()}**")
                st.write("Emotion Probabilities:")
                st.json(emotion_data)
            else:
                st.warning(emotion_data)

# --- Sidebar Content ---
st.sidebar.header("About This App")
st.sidebar.info("""
This AI Interview Coach helps you prepare for interviews by providing automated feedback.
It leverages:
- **Google Gemini API:** For comprehensive textual feedback.
- **TextBlob:** For sentiment analysis of your answer.
- **DeepFace & OpenCV:** For single-image facial emotion detection from your webcam.

Developed by a professional AI developer and Python engineer.
""")

st.sidebar.header("How to Use")
st.sidebar.markdown("""
1.  **Select a category** for the interview question.
2.  **Type your answer** in the text area.
3.  Click **"Get Feedback"** to receive an AI-generated report, including sentiment analysis.
4.  Optionally, **take a picture** with your webcam in the "Facial Emotion Detection" section to analyze your emotions.
""")

st.sidebar.header("Disclaimer")
st.sidebar.warning("""
This tool provides AI-generated feedback and is intended for practice purposes only.
It should not be considered a substitute for professional career advice.
""")
