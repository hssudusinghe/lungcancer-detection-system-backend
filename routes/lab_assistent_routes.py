import base64

from flask import Blueprint, request, jsonify
from db.database import get_connection
import bcrypt

lab_assistent_bp = Blueprint("lab_assistent_bp", __name__)


@lab_assistent_bp.route("/register", methods=["POST"])
def register_lab_assistent():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        name = request.form.get("name")
        hospital_name = request.form.get("hospital_name")
        contact_no = request.form.get("contact_no")
        email = request.form.get("email")
        password = request.form.get("password")
        profile_image = request.files.get("profile_image")

        if not all([name, hospital_name, contact_no, email, password, profile_image]):
            return jsonify({"message": "All fields are required"}), 400

        cursor.execute(
            "SELECT * FROM lab_assistant WHERE email=%s",
            (email,)
        )

        if cursor.fetchone():
            return jsonify({"message": "Email already exists"}), 409

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        image_data = profile_image.read()

        sql = """
        INSERT INTO lab_assistant
        (name, hospital_name, contact_no, email, password, profile_image)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(sql, (
            name,
            hospital_name,
            contact_no,
            email,
            hashed_password,
            image_data
        ))

        conn.commit()

        return jsonify({
            "message": "Lab assistant registered successfully"
        }), 201

    except Exception as e:
        print("ERROR:", e)
        return jsonify({
            "message": "Server error",
            "error": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@lab_assistent_bp.route("/login", methods=["POST"])
def lab_assistent_login():
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
            "SELECT * FROM lab_assistant WHERE email=%s",
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
            "user_id": user["lab_assistant_id"],
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

@lab_assistent_bp.route("/get-by-id/<int:user_id>", methods=["GET"])
def get_lab_assistent(user_id):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT lab_assistant_id, name, hospital_name, contact_no, email, profile_image
            FROM lab_assistant
            WHERE lab_assistant_id=%s
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Lab assistant not found"}), 404

        image = None
        if user["profile_image"]:
            import base64
            image = base64.b64encode(user["profile_image"]).decode("utf-8")
            image = f"data:image/jpeg;base64,{image}"

        return jsonify({
            "user_id": user["lab_assistant_id"],
            "name": user["name"],
            "hospital_name": user["hospital_name"],
            "contact_no": str(user["contact_no"]),
            "email": user["email"],
            "profile_image": image
        }), 200

    except Exception as e:
        print("GET ERROR:", e)
        return jsonify({"message": "Server error"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@lab_assistent_bp.route("/update/<int:user_id>", methods=["PUT"])
def update_lab_assistent(user_id):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # GET DATA
        name = request.form.get("name")
        hospital_name = request.form.get("hospital_name")
        contact_no = request.form.get("contact_no")
        email = request.form.get("email")
        password = request.form.get("password")
        profile_image = request.files.get("profile_image")

        # CHECK USER
        cursor.execute(
            "SELECT * FROM lab_assistant WHERE lab_assistant_id=%s",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "User not found"}), 404

        # BUILD UPDATE FIELDS
        fields = []
        values = []

        if name:
            fields.append("name=%s")
            values.append(name)

        if hospital_name:
            fields.append("hospital_name=%s")
            values.append(hospital_name)

        if contact_no:
            fields.append("contact_no=%s")
            values.append(contact_no)

        if email:
            fields.append("email=%s")
            values.append(email)

        # PASSWORD HASH (only if given)
        if password:
            import bcrypt
            hashed = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            )
            fields.append("password=%s")
            values.append(hashed)

        # IMAGE UPDATE
        if profile_image:
            fields.append("profile_image=%s")
            values.append(profile_image.read())

        if not fields:
            return jsonify({"message": "Nothing to update"}), 400

        # FINAL QUERY
        sql = f"""
        UPDATE lab_assistant
        SET {", ".join(fields)}, updated_at=CURRENT_TIMESTAMP
        WHERE lab_assistant_id=%s
        """

        values.append(user_id)

        cursor.execute(sql, values)
        conn.commit()

        return jsonify({
            "message": "Lab assistant updated successfully"
        }), 200

    except Exception as e:
        print("UPDATE ERROR:", e)
        return jsonify({
            "message": "Server error",
            "error": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@lab_assistent_bp.route("/change-password/<int:lab_assistant_id>", methods=["PUT"])
def change_password(lab_assistant_id):
    conn = None
    cursor = None

    try:
        data = request.get_json()
        current_password = data.get("current_password")
        new_password = data.get("new_password")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM lab_assistant WHERE lab_assistant_id=%s", (lab_assistant_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Lab assistant not found"}), 404

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
            "UPDATE lab_assistant SET password=%s WHERE lab_assistant_id=%s",
            (hashed, lab_assistant_id)
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