from flask import Flask
from flask_cors import CORS
from routes.patient_routes import patient_bp
from routes.doctor_routes import doctor_bp
from routes.lab_assistent_routes import lab_assistent_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(patient_bp, url_prefix="/api/patient")
app.register_blueprint(doctor_bp, url_prefix="/api/doctor")
app.register_blueprint(lab_assistent_bp, url_prefix="/api/lab_assistant")

@app.route("/")
def home():
    return {"message": "Backend running"}

if __name__ == "__main__":
    app.run(debug=True)
