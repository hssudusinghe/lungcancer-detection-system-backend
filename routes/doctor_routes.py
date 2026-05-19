import base64

from flask import Blueprint, request, jsonify
import numpy as np
import tensorflow as tf
from PIL import Image
from db.database import get_connection
import bcrypt

doctor_bp = Blueprint("doctor_bp", __name__)

@doctor_bp.route("/register", methods=["POST"])
def register_doctor():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # GET DATA
        name = request.form.get("name")
        hospital_name = request.form.get("hospital_name")
        slmc_reg_no = request.form.get("slmc_reg_no")
        contact_no = request.form.get("contact_no")
        email = request.form.get("email")
        password = request.form.get("password")

        profile_image = request.files.get("profile_image")

        # VALIDATION
        if not all([name, hospital_name, slmc_reg_no, contact_no, email, password, profile_image]):
            return jsonify({"message": "All fields are required"}), 400

        # CHECK EMAIL
        cursor.execute("SELECT * FROM doctor WHERE email=%s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already exists"}), 409

        # PASSWORD HASH
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # IMAGE
        image_data = profile_image.read()

        # INSERT
        sql = """
        INSERT INTO doctor
        (name, hospital_name, slmc_reg_no, contact_no, email, password, profile_image)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(sql, (
            name,
            hospital_name,
            slmc_reg_no,
            contact_no,
            email,
            hashed_password,
            image_data
        ))

        conn.commit()

        return jsonify({"message": "Doctor registered successfully"}), 201

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@doctor_bp.route("/login", methods=["POST"])
def doctor_login():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            return jsonify({"message": "Email and password required"}), 400

        # GET USER
        cursor.execute(
            "SELECT * FROM doctor WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Invalid email"}), 401

        # CHECK PASSWORD
        if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            return jsonify({"message": "Invalid password"}), 401

        return jsonify({
            "message": "Login successful",
            "user_id": user["doctor_id"],
            "name": user["name"]
        }), 200

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()  

@doctor_bp.route("/get-by-id/<int:doctor_id>", methods=["GET"])
def get_doctor(doctor_id):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT doctor_id, name, hospital_name, slmc_reg_no,
                   contact_no, email, profile_image
            FROM doctor
            WHERE doctor_id=%s
        """, (doctor_id,))

        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Doctor not found"}), 404

        # Convert image to Base64
        profile_image = None

        if user["profile_image"]:
            profile_image = base64.b64encode(user["profile_image"]).decode("utf-8")
            profile_image = f"data:image/jpeg;base64,{profile_image}"

        return jsonify({
            "doctor_id": user["doctor_id"],
            "name": user["name"],
            "hospital_name": user["hospital_name"],
            "slmc_reg_no": user["slmc_reg_no"],
            "contact_no": user["contact_no"],
            "email": user["email"],
            "profile_image": profile_image
        }), 200

    except Exception as e:
        print("GET DOCTOR ERROR:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@doctor_bp.route("/update/<int:user_id>", methods=["PUT"])
def update_doctor(user_id):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # GET DATA
        name = request.form.get("name")
        hospital_name = request.form.get("hospital_name")
        slmc_reg_no = request.form.get("slmc_reg_no")
        contact_no = request.form.get("contact_no")
        email = request.form.get("email")
        password = request.form.get("password")
        profile_image = request.files.get("profile_image")

        # VALIDATION
        if not name or not hospital_name or not slmc_reg_no or not contact_no or not email:
            return jsonify({"message": "Required fields missing"}), 400

        # CHECK DOCTOR EXISTS
        cursor.execute(
            "SELECT * FROM doctor WHERE doctor_id=%s",
            (user_id,)
        )
        doctor = cursor.fetchone()

        if not doctor:
            return jsonify({"message": "Doctor not found"}), 404

        # EMAIL CHECK
        cursor.execute(
            "SELECT doctor_id FROM doctor WHERE email=%s AND doctor_id != %s",
            (email, user_id)
        )
        if cursor.fetchone():
            return jsonify({"message": "Email already used"}), 409

        # PASSWORD (optional)
        hashed_password = doctor["password"]
        if password and password.strip():
            hashed_password = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            )

        # IMAGE (optional)
        image_data = doctor["profile_image"]
        if profile_image:
            image_data = profile_image.read()

        # UPDATE QUERY
        sql = """
        UPDATE doctor SET
            name=%s,
            hospital_name=%s,
            slmc_reg_no=%s,
            contact_no=%s,
            email=%s,
            password=%s,
            profile_image=%s,
            updated_at=NOW()
        WHERE doctor_id=%s
        """

        cursor.execute(sql, (
            name,
            hospital_name,
            slmc_reg_no,
            contact_no,
            email,
            hashed_password,
            image_data,
            user_id
        ))

        conn.commit()

        return jsonify({
            "message": "Doctor profile updated successfully"
        }), 200

    except Exception as e:
        print("DOCTOR UPDATE ERROR:", e)
        return jsonify({
            "message": "Server error",
            "error": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@doctor_bp.route("/change-password/<int:doctor_id>", methods=["PUT"])
def change_password(doctor_id):
    conn = None
    cursor = None

    try:
        data = request.get_json()
        current_password = data.get("current_password")
        new_password = data.get("new_password")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM doctor WHERE doctor_id=%s", (doctor_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Doctor not found"}), 404

        import bcrypt

        # check current password
        if not bcrypt.checkpw(
            current_password.encode("utf-8"),
            user["password"].encode("utf-8")
        ):
            return jsonify({"message": "Current password is incorrect"}), 400

        # hash new password
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

        cursor.execute(
            "UPDATE doctor SET password=%s WHERE doctor_id=%s",
            (hashed, doctor_id)
        )

        conn.commit()

        return jsonify({"message": "Password updated successfully"}), 200

    except Exception as e:
        print("CHANGE PASSWORD ERROR:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@doctor_bp.route("/get-all-doctors", methods=["GET"])
def get_doctors():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT doctor_id, name, hospital_name, slmc_reg_no,
                   contact_no, email, profile_image
            FROM doctor
        """)

        doctors = cursor.fetchall()

        result = []

        for doc in doctors:
            profile_image = None

            if doc["profile_image"]:
                profile_image = base64.b64encode(doc["profile_image"]).decode("utf-8")
                profile_image = f"data:image/jpeg;base64,{profile_image}"

            result.append({
                "doctor_id": doc["doctor_id"],
                "name": doc["name"],
                "hospital_name": doc["hospital_name"],
                "slmc_reg_no": doc["slmc_reg_no"],
                "contact_no": doc["contact_no"],
                "email": doc["email"],
                "profile_image": profile_image
            })

        return jsonify(result), 200

    except Exception as e:
        print("GET DOCTOR ERROR:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@doctor_bp.route("/feedback", methods=["POST"])
def add_feedback():
    try:
        data = request.json

        conn = get_connection()
        cursor = conn.cursor()

        # 1. Insert feedback
        insert_sql = """
        INSERT INTO feedback 
        (doctor_name, comment, prediction_id, user_id)
        VALUES (%s, %s, %s, %s)
        """

        cursor.execute(insert_sql, (
            data["doctor_name"],
            data["comment"],
            data["prediction_id"],
            data["user_id"]
        ))

        # 2. Update prediction table status
        update_sql = """
        UPDATE prediction
        SET respond_type = 'complete',
            updated_at = NOW()
        WHERE prediction_id = %s
        """

        cursor.execute(update_sql, (data["prediction_id"],))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Feedback added and prediction marked as complete"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500 

model = tf.keras.models.load_model("lung_cancer_model.h5")

class_names = [
    "Adenocarcinoma",
    "Large Cell Carcinoma",
    "Normal",
    "Squamous Cell Carcinoma"
]

# ================= CHECK IF IMAGE LOOKS LIKE CT SCAN =================
def is_ct_scan(image):
    img = Image.open(image).convert("RGB")
    img = img.resize((224, 224))

    img_array = np.array(img)

    # Convert to grayscale difference check
    r = img_array[:, :, 0]
    g = img_array[:, :, 1]
    b = img_array[:, :, 2]

    # CT scans are usually grayscale (R,G,B nearly equal)
    diff_rg = np.mean(np.abs(r - g))
    diff_rb = np.mean(np.abs(r - b))

    # If differences are very small → likely grayscale scan
    if diff_rg < 10 and diff_rb < 10:
        return True

    return False


# ================= PREPARE IMAGE =================
def prepare_image(image):
    img = Image.open(image).resize((224, 224))
    img = img.convert("RGB")

    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    return img_array


@doctor_bp.route("/predict-without-database", methods=["POST"])
def predict():
    try:

        file = request.files.get("image")
        user_id = request.form.get("user_id")

        if not file:
            return jsonify({"error": "No image uploaded"}), 400

        if not user_id:
            return jsonify({"error": "User ID missing"}), 400

        user_id = int(user_id)

        # ================= VALIDATE IMAGE =================
        if not is_ct_scan(file):
            return jsonify({
                "error": "Please upload a valid lung CT scan image only"
            }), 400

        # reset pointer after validation
        file.seek(0)

        # ================= PREPROCESS =================
        img_array = prepare_image(file)

        # reset pointer again before saving
        file.seek(0)

        # ================= MODEL PREDICTION =================
        prediction = model.predict(img_array)[0]

        class_idx = np.argmax(prediction)
        confidence = float(prediction[class_idx])

        if confidence < 0.6:
            result = "Unknown / Low confidence"
        else:
            results = [
    "Lung Cancer Type A (Adenocarcinoma) - Requires medical attention",
    "Lung Cancer Type B (Large Cell Carcinoma) - Consult a doctor urgently",
    "Healthy Lungs - No signs of cancer detected",
    "Lung Cancer Type C (Squamous Cell Carcinoma) - Immediate medical consultation recommended"
                      ]

            result = results[class_idx]

        return jsonify({
            "predicted_class": result,
            "confidence": confidence,
            "user_id": user_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500             
