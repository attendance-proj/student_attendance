from flask import Flask, request, jsonify, send_file
import psycopg2
import traceback
import io
import openpyxl

app = Flask(__name__)
app.url_map.strict_slashes = False

DATABASE_URL = "postgresql://postgres:Tushar%403105E@db.zzghodffauzifcicxkke.supabase.co:5432/postgres?sslmode=require"

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

@app.route('/')
def home():
    return jsonify({"message": "Smart Attendance API Running"})

# --- LOGIN ---
@app.route('/login', methods=['POST'])
@app.route('/api/login', methods=['POST'])
def login():
    conn = None
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "No data received"}), 400

        college_id = data.get('collegeId') or data.get('college_id')
        password = data.get('password')

        conn = get_db_connection()
        if conn is None:
            return jsonify({"success": False, "message": "DB Connection Failed"}), 500

        cursor = conn.cursor()
        query = 'SELECT full_name, role FROM "Users" WHERE college_id = %s AND password_hash = %s'
        cursor.execute(query, (college_id, password))

        result = cursor.fetchone()

        if result:
            user = {
                "name": result[0],
                "role": result[1]
            }
            return jsonify({"success": True, "role": user["role"], "name": user["name"]})
        else:
            return jsonify({"success": False, "message": "Invalid Credentials"}), 401

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- CLASS START ---
@app.route('/api/class/start', methods=['POST'])
def start_class():
    conn = None
    try:
        data = request.json
        conn = get_db_connection()

        if conn is None:
            return jsonify({"error": "DB Connection Failed"}), 500

        cursor = conn.cursor()

        cursor.execute(
            'UPDATE "Class_Sessions" SET is_active = FALSE WHERE course_code = %s',
            (data.get('courseCode'),)
        )

        cursor.execute("""
            INSERT INTO "Class_Sessions" (course_code, teacher_id, date, start_time, is_active)
            VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, TRUE)
        """, (data.get('courseCode'), data.get('teacherId')))

        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- MARK ATTENDANCE ---
@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    conn = None
    try:
        data = request.json
        conn = get_db_connection()

        if conn is None:
            return jsonify({"error": "DB Connection Failed"}), 500

        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id FROM "Class_Sessions"
            WHERE course_code = %s AND is_active = TRUE
            ORDER BY session_id DESC LIMIT 1
        """, (data.get('lectureId'),))

        session = cursor.fetchone()

        if not session:
            return jsonify({"success": False, "message": "No active class"}), 404

        session_id = session[0]

        cursor.execute("""
            SELECT log_id FROM "Attendance_Log"
            WHERE session_id = %s AND student_id = %s
        """, (session_id, data.get('studentId')))

        if cursor.fetchone():
            return jsonify({"success": True, "message": "Already marked"})

        cursor.execute("""
            INSERT INTO "Attendance_Log" (session_id, student_id, verification_mode, status)
            VALUES (%s, %s, %s, 'PRESENT')
        """, (session_id, data.get('studentId'), data.get('verificationMode')))

        conn.commit()
        return jsonify({"success": True, "message": "Recorded"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- EXPORT REPORT ---
@app.route('/api/teacher/export_report_get/<string:course_code>', methods=['GET'])
def export_report(course_code):
    conn = None
    try:
        conn = get_db_connection()

        if conn is None:
            return jsonify({"error": "DB Connection Failed"}), 500

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([f"Report for {course_code}"])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'report_{course_code}.xlsx'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)