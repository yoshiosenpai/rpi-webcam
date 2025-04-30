import io
import time
import datetime
import pytz
from flask import Flask, Response, request, session, redirect, url_for, render_template
from picamera2 import Picamera2
from PIL import Image, ImageDraw, ImageFont


app = Flask(__name__)
app.secret_key = "super_random_secret_key"  # CHANGE ME


picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(main={"size": (1280, 720)})
picam2.configure(preview_config)
picam2.start()


font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = ImageFont.truetype(font_path, size=30)


logo_path = "/home/pi/webcam/raspberry-pi.png"
try:
    logo = Image.open(logo_path).convert("RGBA").resize((50, 50))
except Exception as e:
    print("Error loading logo:", e)
    logo = None


flip_horizontal = False

def generate_frames():
    global flip_horizontal
    frame_count = 0
    start_time = time.time()

    while True:
        frame = picam2.capture_array()
        img = Image.fromarray(frame).convert("RGB")

        if flip_horizontal:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

        draw = ImageDraw.Draw(img)
        local_timezone = pytz.timezone("Asia/Kuala_Lumpur") # Malaysia timezone
        # local_timezone = pytz.timezone("America/New_York") # New York timezone
        # local_timezone = pytz.timezone("Europe/London") # London timezone
        # local_timezone = pytz.timezone("Asia/Tokyo") # Tokyo timezone
        # local_timezone = pytz.timezone("Australia/Sydney") # Sydney timezone
        # local_timezone = pytz.timezone("Europe/Berlin") # Berlin timezone
        # local_timezone = pytz.timezone("America/Los_Angeles") # Los Angeles timezone 
        timestamp = datetime.datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')
        draw.text((70 + 2, 10 + 2), f"Camera - {timestamp}", fill="black", font=font)
        draw.text((70, 10), f"Camera - {timestamp}", fill="lime", font=font)

        if logo:
            img.paste(logo, (10, 5), mask=logo)

        stream = io.BytesIO()
        img.save(stream, format="JPEG", quality=85, optimize=True)
        stream.seek(0)

        frame_count += 1
        elapsed_time = time.time() - start_time

        if elapsed_time >= 1.0:
            app.config['FPS'] = frame_count
            frame_count = 0
            start_time = time.time()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + stream.read() + b"\r\n")
        stream.close()

@app.route('/')
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template('webcam.html', fps=app.config.get('FPS', 0))

@app.route('/login', methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "1234":
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Invalid Credentials. Try again."
    return render_template('login.html', error=error)

@app.route('/logout', methods=["POST"])
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route('/flip', methods=["POST"])
def flip():
    global flip_horizontal
    if session.get("logged_in"):
        flip_horizontal = not flip_horizontal
    return redirect(url_for("index"))

@app.route('/fps')
def fps():
    return str(app.config.get('FPS', 0))

@app.route('/video_feed')
def video_feed():
    user_agent = request.headers.get('User-Agent', '')
    if "obs" in user_agent.lower():
        return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, threaded=True)