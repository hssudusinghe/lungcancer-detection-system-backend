import bcrypt
from flask import Blueprint, request, jsonify
import numpy as np
import tensorflow as tf
from PIL import Image
from db.database import get_connection

patient_bp = Blueprint("patient_bp", __name__)

# model = tf.keras.models.load_model("lung_cancer_model.h5")

# class_names = [
#     "Adenocarcinoma",
#     "Large Cell Carcinoma",
#     "Normal"
# ]

# def prepare_image(image):
#     img = Image.open(image).resize((224, 224))
#     img = img.convert("RGB")
#     img_array = np.array(img) / 255.0
#     img_array = np.expand_dims(img_array, axis=0)
#     return img_array


# @patient_bp.route("/predict", methods=["POST"])
# def predict():
#     try:
#         # ================= INPUTS =================
#         file = request.files.get("image")
#         user_id = request.form.get("user_id")

#         if not file:
#             return jsonify({"error": "No image uploaded"}), 400

#         if not user_id:
#             return jsonify({"error": "User ID missing"}), 400

#         user_id = int(user_id)

#         # ================= IMAGE PREPROCESS =================
#         img_array = prepare_image(file)

#         # ================= MODEL PREDICTION =================
#         prediction = model.predict(img_array)[0]
#         class_idx = np.argmax(prediction)
#         confidence = float(prediction[class_idx])

#         # ================= RESULT LOGIC =================
#         if confidence < 0.6:
#             result = "Unknown / Not a lung scan"
#         else:
#             class_names = [
#                 "Lung Cancer Type A (Adenocarcinoma) - Requires medical attention",
#                 "Lung Cancer Type B (Large Cell Carcinoma) - Consult a doctor urgently",
#                 "Healthy Lungs - No signs of cancer detected"
#             ]
#             result = class_names[class_idx]

#         # ================= SAVE IMAGE FIRST =================
#         conn = get_connection()
#         cursor = conn.cursor()

#         file.seek(0)  # reset pointer before saving image
#         cursor.execute(
#             "INSERT INTO medical_images (medical_image) VALUES (%s)",
#             (file.read(),)
#         )
#         image_id = cursor.lastrowid

#         # ================= SAVE PREDICTION =================
#         cursor.execute(
#             "INSERT INTO prediction (result, user_id, medical_image_id) VALUES (%s, %s, %s)",
#             (result, user_id, image_id)
#         )
#         prediction_id = cursor.lastrowid

#         # ================= SAVE DETAILS =================
#         cursor.execute(
#             "INSERT INTO prediction_details (feature_name, value, prediction_id) VALUES (%s, %s, %s)",
#             ("confidence", str(confidence), prediction_id)
#         )

#         conn.commit()
#         cursor.close()
#         conn.close()

#         # ================= RESPONSE =================
#         return jsonify({
#             "predicted_class": result,
#             "confidence": confidence,
#             "user_id": user_id
#         })

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


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


# ================= API =================
@patient_bp.route("/predict", methods=["POST"])
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

        # ================= SAVE IMAGE =================
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO medical_images (medical_image) VALUES (%s)",
            (file.read(),)
        )

        image_id = cursor.lastrowid

        # ================= SAVE PREDICTION =================
        cursor.execute(
            "INSERT INTO prediction (result, user_id, medical_image_id) VALUES (%s, %s, %s)",
            (result, user_id, image_id)
        )

        prediction_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO prediction_details (feature_name, value, prediction_id) VALUES (%s, %s, %s)",
            ("confidence", str(confidence), prediction_id)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "predicted_class": result,
            "confidence": confidence,
            "user_id": user_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@patient_bp.route("/register", methods=["POST"])
def register_patient():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # GET FORM DATA
        name = request.form.get("name")
        age = request.form.get("age")
        nic = request.form.get("nic")
        contact_no = request.form.get("contact_no")
        gender = request.form.get("gender")
        email = request.form.get("email")
        password = request.form.get("password")

        profile_image = request.files.get("profile_image")

        # VALIDATION
        if not all([name, age, nic, contact_no, gender, email, password, profile_image]):
            return jsonify({"message": "All fields are required"}), 400

        # CHECK EMAIL EXISTS
        cursor.execute("SELECT * FROM user WHERE email=%s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already exists"}), 409

        # HASH PASSWORD
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # IMAGE TO BLOB
        image_data = profile_image.read()

        # INSERT QUERY
        sql = """
        INSERT INTO user 
        (name, age, nic, contact_no, gender, email, password, profile_image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            name,
            int(age),
            nic,
            contact_no,
            gender,
            email,
            hashed_password,
            image_data
        )

        cursor.execute(sql, values)
        conn.commit()

        return jsonify({"message": "Patient registered successfully"}), 201

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@patient_bp.route("/login", methods=["POST"])
def patient_login():
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
            "SELECT * FROM user WHERE email=%s",
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
            "user_id": user["user_id"],
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

@patient_bp.route("/get-by-id/<int:user_id>", methods=["GET"])
def get_patient(user_id):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                user_id,
                name,
                age,
                nic,
                contact_no,
                gender,
                email,
                profile_image
            FROM user 
            WHERE user_id=%s
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Patient not found"}), 404

        import base64

        profile_image = None
        if user["profile_image"]:
            profile_image = base64.b64encode(user["profile_image"]).decode("utf-8")
            profile_image = f"data:image/jpeg;base64,{profile_image}"

        return jsonify({
            "user_id": user["user_id"],
            "name": user["name"],
            "age": user["age"],
            "nic": user["nic"],
            "contact_no": user["contact_no"],
            "gender": user["gender"],
            "email": user["email"],
            "profile_image": profile_image
        }), 200

    except Exception as e:
        print("GET USER ERROR:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@patient_bp.route("/update/<int:user_id>", methods=["PUT"])
def update_patient(user_id):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # GET DATA
        name = request.form.get("name")
        age = request.form.get("age")
        nic = request.form.get("nic")
        contact_no = request.form.get("contact_no")
        gender = request.form.get("gender")
        email = request.form.get("email")
        password = request.form.get("password")

        profile_image = request.files.get("profile_image")

        # ===== VALIDATION =====
        errors = {}

        if not name:
            errors["name"] = "Name is required"

        if not age or not age.isdigit():
            errors["age"] = "Valid age required"

        if not nic:
            errors["nic"] = "NIC is required"

        if not contact_no:
            errors["contact_no"] = "Contact number required"
        elif not contact_no.startswith("+94") and not contact_no.startswith("0"):
            errors["contact_no"] = "Invalid Sri Lankan number"

        if not gender:
            errors["gender"] = "Gender required"

        if not email or "@" not in email:
            errors["email"] = "Valid email required"

        # RETURN VALIDATION ERRORS
        if errors:
            return jsonify({"errors": errors}), 400

        # CHECK USER EXISTS
        cursor.execute("SELECT * FROM user WHERE user_id=%s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "User not found"}), 404

        # CHECK EMAIL DUPLICATE (except current user)
        cursor.execute(
            "SELECT * FROM user WHERE email=%s AND user_id != %s",
            (email, user_id)
        )
        if cursor.fetchone():
            return jsonify({"message": "Email already in use"}), 409

        # PASSWORD UPDATE (optional)
        if password:
            if len(password) < 6:
                return jsonify({"message": "Password must be at least 6 characters"}), 400

            hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        else:
            hashed_password = user["password"]

        # IMAGE UPDATE (optional)
        if profile_image:
            image_data = profile_image.read()
        else:
            image_data = user["profile_image"]

        # UPDATE QUERY
        sql = """
        UPDATE user SET
            name=%s,
            age=%s,
            nic=%s,
            contact_no=%s,
            gender=%s,
            email=%s,
            password=%s,
            profile_image=%s
        WHERE user_id=%s
        """

        cursor.execute(sql, (
            name,
            int(age),
            nic,
            contact_no,
            gender,
            email,
            hashed_password,
            image_data,
            user_id
        ))

        conn.commit()

        return jsonify({"message": "Patient updated successfully"}), 200

    except Exception as e:
        print("UPDATE ERROR:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@patient_bp.route("/change-password/<int:patient_id>", methods=["PUT"])
def change_password(patient_id):
    conn = None
    cursor = None

    try:
        data = request.get_json()
        current_password = data.get("current_password")
        new_password = data.get("new_password")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM user WHERE user_id=%s", (patient_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Patient not found"}), 404

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
            "UPDATE user SET password=%s WHERE user_id=%s",
            (hashed, patient_id)
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

@patient_bp.route("/reports/<int:user_id>", methods=["GET"])
def get_reports(user_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
SELECT 
    p.prediction_id,
    p.result,
    p.created_at,
    p.respond_type,   
    m.image_id,
    m.medical_image,
    p.user_id,
    u.name AS user_name
FROM prediction p
JOIN medical_images m ON p.medical_image_id = m.image_id
JOIN user u ON p.user_id = u.user_id
WHERE p.user_id = %s
ORDER BY p.created_at DESC;
""", (user_id,))

        reports = cursor.fetchall()

        cursor.close()
        conn.close()

          # Convert image to base64
        import base64
        for report in reports:
            if report["medical_image"]:
                report["medical_image"] = base64.b64encode(report["medical_image"]).decode("utf-8")

        return jsonify(reports)

    except Exception as e:
        return jsonify({"error": str(e)}), 500  


@patient_bp.route("/report-latest/<int:user_id>", methods=["GET"])
def get_reports_latest_one(user_id):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                p.prediction_id,
                p.result,
                p.created_at,
                p.respond_type,
                m.image_id,
                m.medical_image,
                p.user_id,
                u.name AS user_name
            FROM prediction p
            JOIN medical_images m 
                ON p.medical_image_id = m.image_id
            JOIN user u 
                ON p.user_id = u.user_id
            WHERE p.user_id = %s
            ORDER BY p.created_at DESC
            LIMIT 1
        """, (user_id,))

        report = cursor.fetchone()

        cursor.close()
        conn.close()

         # Convert image to base64
        import base64
        if report["medical_image"]:
           report["medical_image"] = base64.b64encode(report["medical_image"]).decode("utf-8")

        return jsonify(report)

    except Exception as e:
        return jsonify({"error": str(e)}), 500     
    

@patient_bp.route("/report/<int:prediction_id>", methods=["GET"])
def get_full_report(prediction_id):
    conn = None
    cursor = None
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Get prediction + image
    cursor.execute("""
        SELECT 
            p.prediction_id,
            p.result,
            p.created_at,
            p.respond_type,  
            m.image_id,
            m.medical_image,
            p.user_id,
            u.name AS user_name
        FROM prediction p
        JOIN medical_images m ON p.medical_image_id = m.image_id
        JOIN user u ON p.user_id = u.user_id
        WHERE p.prediction_id = %s
    """, (prediction_id,))

    report = cursor.fetchone()

    if not report:
        return jsonify({"error": "Report not found"}), 404

    cursor.execute("""
        SELECT feature_name, value
        FROM prediction_details
        WHERE prediction_id = %s
    """, (prediction_id,))

    features = cursor.fetchall()

    cursor.close()
    conn.close()

    # Convert image to base64
    import base64
    if report["medical_image"]:
        report["medical_image"] = base64.b64encode(report["medical_image"]).decode("utf-8")

    return jsonify({
        "report": report,
        "features": features
    })

@patient_bp.route("/reports-all", methods=["GET"])
def get_all_reports():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
SELECT 
    p.prediction_id,
    p.result,
    p.created_at,
    p.respond_type,   
    m.image_id,
    m.medical_image,
    p.user_id,
    u.name AS user_name
FROM prediction p
JOIN medical_images m ON p.medical_image_id = m.image_id
JOIN user u ON p.user_id = u.user_id
ORDER BY p.created_at DESC;
""", ())

        reports = cursor.fetchall()

        cursor.close()
        conn.close()

          # Convert image to base64
        import base64
        for report in reports:
            if report["medical_image"]:
                report["medical_image"] = base64.b64encode(report["medical_image"]).decode("utf-8")

        return jsonify(reports)

    except Exception as e:
        return jsonify({"error": str(e)}), 500 

@patient_bp.route("/feedback/<int:user_id>", methods=["GET"])
def get_feedback_by_user(user_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
        SELECT 
            feedback_id,
            doctor_name,
            comment,
            prediction_id,
            user_id,
            created_at
        FROM feedback
        WHERE user_id = %s
        ORDER BY created_at DESC
        """

        cursor.execute(sql, (user_id,))
        feedbacks = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": feedbacks
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500 

@patient_bp.route("/feedback/latest/<int:user_id>", methods=["GET"])
def get_latest_feedback_by_user(user_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
        SELECT 
            feedback_id,
            doctor_name,
            comment,
            prediction_id,
            user_id,
            created_at
        FROM feedback
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """

        cursor.execute(sql, (user_id,))
        feedback = cursor.fetchone()

        cursor.close()
        conn.close()

        if not feedback:
            return jsonify({
                "success": False,
                "message": "No feedback found"
            }), 404

        return jsonify({
            "success": True,
            "data": feedback
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500  

@patient_bp.route("/complete-feedback/<int:prediction_id>", methods=["GET"])
def get_feedback_by_prediction(prediction_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
        SELECT 
            feedback_id,
            doctor_name,
            comment,
            prediction_id,
            user_id,
            created_at
        FROM feedback
        WHERE prediction_id = %s
        ORDER BY created_at DESC
        """

        cursor.execute(sql, (prediction_id,))
        feedback = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": feedback
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500                                                        
