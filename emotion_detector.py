import cv2
import numpy as np
from deepface import DeepFace # DeepFace is a powerful library for facial analysis
import os

# --- Configuration for DeepFace (optional, for model paths etc.) ---
# DeepFace models might download on first use.
# You can specify model paths if you want to manage them manually.

def analyze_facial_emotion_from_webcam():
    """
    Conceptual function to capture video from webcam, detect faces,
    and analyze emotions using DeepFace.

    NOTE: This function is designed for LOCAL EXECUTION and will likely
    NOT work directly when deployed on Streamlit Cloud due to:
    - Browser security restrictions on webcam access within iframes.
    - Computational intensity for real-time video processing.
    - Streamlit's server-side execution model (video frames need to be streamed).

    For actual deployment with webcam, consider:
    - Using Streamlit's `st.camera_input` to capture a single image, then analyze it.
    - Building a dedicated client-side (JavaScript) component to handle webcam.
    - Running the Streamlit app locally.
    """
    cap = cv2.VideoCapture(0) # 0 for default webcam

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return "Webcam not accessible."

    st.write("Starting webcam feed... (Check your browser for permission prompt)")
    st.write("Press 'q' to quit the webcam feed.")

    emotion_history = []
    frame_count = 0
    processing_interval = 5 # Analyze every 5th frame to reduce load

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame.")
                break

            frame_count += 1
            if frame_count % processing_interval == 0:
                # Convert frame to RGB (DeepFace expects RGB)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                try:
                    # Analyze emotions in the frame
                    # actions=['emotion'] tells DeepFace to only focus on emotion
                    demographies = DeepFace.analyze(
                        img_path=rgb_frame,
                        actions=['emotion'],
                        enforce_detection=False # Set to False to avoid errors if no face is detected
                    )

                    if demographies:
                        # DeepFace returns a list of dictionaries, one for each detected face
                        # We'll consider the first detected face for simplicity
                        dominant_emotion = demographies[0]['dominant_emotion']
                        emotion_scores = demographies[0]['emotion']
                        emotion_history.append(dominant_emotion)

                        # Draw bounding box and emotion on the frame
                        x, y, w, h = demographies[0]['face_box']['x'], demographies[0]['face_box']['y'], \
                                     demographies[0]['face_box']['w'], demographies[0]['face_box']['h']
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(frame, dominant_emotion, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                        print(f"Detected emotion: {dominant_emotion}")
                        # You would typically send this data back to Streamlit
                        # or update a Streamlit component here.
                        # For real-time display in Streamlit, you'd use st.image(frame, channels="BGR")
                        # but this requires constant frame updates which is tricky.

                except ValueError as e:
                    # This often happens if no face is detected in the frame
                    # print(f"No face detected or error during analysis: {e}")
                    pass # Silently pass if no face or minor error

            # Display the frame (for local testing)
            cv2.imshow('Webcam Feed - Emotion Detection (Press Q to quit)', frame)

            # Break the loop on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Webcam feed stopped.")

    if emotion_history:
        # Return a summary of detected emotions
        from collections import Counter
        emotion_counts = Counter(emotion_history)
        most_common_emotion = emotion_counts.most_common(1)[0][0]
        return f"Overall dominant emotion: {most_common_emotion}"
    else:
        return "No emotions detected during the session."

# Example of how you might use it if running this file directly for testing
if __name__ == "__main__":
    # This part will only run when you execute emotion_detector.py directly
    # not when imported by app.py
    print("Running conceptual webcam emotion detection locally...")
    result = analyze_facial_emotion_from_webcam()
    print(result)
