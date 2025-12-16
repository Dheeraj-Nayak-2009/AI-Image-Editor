from flask import Flask, render_template, request, session, redirect, url_for
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import uuid

# Flask setup
app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

API_KEY = "REVERSE_ENGINEER_THE_'f(word)'_FUNCTION_TO_GET_THE_ENCODED_API"

def f(word):
  new_word = ""
  for char in word:
    new_char = chr(ord(char) - 1)
    new_word += new_char
  return new_word

# Gemini setup
client = genai.Client(api_key=f(API_KEY))

@app.route("/", methods=["GET", "POST"])
def index():
    original_image = session.get("original_image")
    edited_image = session.get("edited_image")
    error_message = None

    if request.method == "POST":
        file = request.files.get("file")
        prompt = request.form.get("prompt")

        # Case 1: New image uploaded
        if file and file.filename:
            try:
                filename = f"{uuid.uuid4().hex}_{file.filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                session["original_image"] = filename
                session["edited_image"] = None
                original_image = filename
                edited_image = None
            except Exception as e:
                error_message = f"Error saving image: {str(e)}"
                return render_template("index.html", original_image=original_image, edited_image=edited_image, error=error_message)

        # Case 2: No new file, but use last edited image as the new original
        elif not file or not file.filename:
            if session.get("edited_image"):
                session["original_image"] = session["edited_image"]
                original_image = session["original_image"]
                session["edited_image"] = None
                edited_image = None
            elif not session.get("original_image"):
                error_message = "Please upload an image first."
                return render_template("index.html", error=error_message)

        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], session["original_image"])
            image = Image.open(image_path)

            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                )
            )

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data is not None:
                        edited = Image.open(BytesIO(part.inline_data.data))
                        edited_filename = f"edited_{uuid.uuid4().hex}.png"
                        edited_path = os.path.join(app.config['UPLOAD_FOLDER'], edited_filename)
                        edited.save(edited_path)
                        session["edited_image"] = edited_filename
                        edited_image = edited_filename
            else:
                error_message = "No image was returned. Try refining your prompt."

        except Exception as e:
            error_message = f"Error: {str(e)}"

    return render_template("index.html",
                           original_image=session.get("original_image"),
                           edited_image=session.get("edited_image"),
                           error=error_message)

@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)

