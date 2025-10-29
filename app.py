from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, send_file
import pyodbc
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from monitoring import init_app, start_cpu_metric_loop
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Azure SQL connection (same as your original)
server = 'facultyleaveserver.database.windows.net'
database = 'FacultyLeaveDB'
username = 'adminuser'
password = 'Nandhu@181'
driver = '{ODBC Driver 18 for SQL Server}'
conn = pyodbc.connect(f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}')

init_app(app)
start_cpu_metric_loop(interval_seconds=10)

# ---------- Helper functions ----------
def get_faculty_leaves(faculty_id, start_date=None, end_date=None):
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute("""
            SELECT id, date, days, reason, status, document
            FROM Leaves
            WHERE faculty_id=? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (faculty_id, start_date, end_date))
    else:
        cursor.execute("""
            SELECT id, date, days, reason, status, document
            FROM Leaves
            WHERE faculty_id=?
            ORDER BY date DESC
        """, (faculty_id,))
    rows = cursor.fetchall()
    cursor.close()
    return rows

def generate_pdf_for_leaves(faculty_name, leaves, title="Leave Report"):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin

    p.setFont("Helvetica-Bold", 16)
    p.drawString(margin, y, title)
    p.setFont("Helvetica", 10)
    y -= 25
    p.drawString(margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 25
    p.drawString(margin, y, f"Faculty: {faculty_name}")
    y -= 30

    # table headers
    p.setFont("Helvetica-Bold", 11)
    p.drawString(margin, y, "ID")
    p.drawString(margin + 40, y, "Date")
    p.drawString(margin + 140, y, "Days")
    p.drawString(margin + 190, y, "Reason")
    p.drawString(margin + 420, y, "Status")
    y -= 15
    p.line(margin, y, width - margin, y)
    y -= 10
    p.setFont("Helvetica", 10)

    for row in leaves:
        leave_id, date_val, days, reason, status, document = row
        # ensure y space
        if y < 80:
            p.showPage()
            y = height - margin
        p.drawString(margin, y, str(leave_id))
        p.drawString(margin + 40, y, (date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)))
        p.drawString(margin + 140, y, str(days))
        # wrap reason to multi-line if needed
        reason_text = (reason if reason else "")
        max_reason_len = 45
        if len(reason_text) <= max_reason_len:
            p.drawString(margin + 190, y, reason_text)
        else:
            # split into chunks
            chunks = [reason_text[i:i+max_reason_len] for i in range(0, len(reason_text), max_reason_len)]
            p.drawString(margin + 190, y, chunks[0])
            y -= 12
            for c in chunks[1:]:
                if y < 80:
                    p.showPage()
                    y = height - margin
                p.drawString(margin + 190, y, c)
        p.drawString(margin + 420, y, status)
        y -= 18

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def hod_generate_pdf_for_leaves(faculty_name, leaves, title="Leave Report"):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin

    # Title and metadata
    p.setFont("Helvetica-Bold", 16)
    p.drawString(margin, y, title)
    p.setFont("Helvetica", 10)
    y -= 25
    p.drawString(margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 25
    p.drawString(margin, y, f"Department: {faculty_name}")
    y -= 30

    # Table headers
    p.setFont("Helvetica-Bold", 11)
    p.drawString(margin, y, "ID")
    p.drawString(margin + 35, y, "Faculty")
    p.drawString(margin + 140, y, "Date")
    p.drawString(margin + 220, y, "Days")
    p.drawString(margin + 260, y, "Reason")
    p.drawString(margin + 460, y, "Status")
    y -= 15
    p.line(margin, y, width - margin, y)
    y -= 10
    p.setFont("Helvetica", 10)

    # Loop through leaves
    for row in leaves:
        try:
            leave_id, faculty_name_val, date_val, days, reason, status, document = row
        except ValueError:
            # Skip rows that don’t match expected format
            continue

        # Page overflow check
        if y < 80:
            p.showPage()
            y = height - margin
            p.setFont("Helvetica-Bold", 11)
            p.drawString(margin, y, "ID")
            p.drawString(margin + 35, y, "Faculty")
            p.drawString(margin + 140, y, "Date")
            p.drawString(margin + 220, y, "Days")
            p.drawString(margin + 260, y, "Reason")
            p.drawString(margin + 460, y, "Status")
            y -= 25
            p.setFont("Helvetica", 10)

        # Draw each field
        p.drawString(margin, y, str(leave_id))
        p.drawString(margin + 35, y, str(faculty_name_val)[:12])  # Truncate if too long
        p.drawString(margin + 140, y, date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val))
        p.drawString(margin + 220, y, str(days))

        # Wrap long reason text
        reason_text = reason or ""
        max_reason_len = 35
        if len(reason_text) <= max_reason_len:
            p.drawString(margin + 260, y, reason_text)
        else:
            chunks = [reason_text[i:i + max_reason_len] for i in range(0, len(reason_text), max_reason_len)]
            p.drawString(margin + 260, y, chunks[0])
            for chunk in chunks[1:]:
                y -= 12
                if y < 80:
                    p.showPage()
                    y = height - margin
                p.drawString(margin + 260, y, chunk)

        p.drawString(margin + 460, y, status)
        y -= 18

    # Add summary
    y -= 15
    p.setFont("Helvetica-Bold", 11)
    p.drawString(margin, y, f"Total Leaves: {len(leaves)}")

    # Save PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# ---------- Routes (login/register left mostly unchanged) ----------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']
        role = request.form['role']

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email=? AND password=? AND role=?", (email, password_input, role))
        user = cursor.fetchone()
        cursor.close()
        if user:
            session['user_id'] = user[0]
            session['role'] = role
            session['name'] = user[1]
            session['department'] = user[5] if len(user) > 5 else None
            # initialize empty draft for chat-based fill
            session['draft_leave'] = {}
            if role == 'faculty':
                return redirect('/faculty')
            elif role == 'hod':
                return redirect('/hod')
            elif role == 'admin':
                return redirect('/admin')
        else:
            error = "Invalid credentials"
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        department = request.form['department']

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Users (name, email, password, role, department)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, password, role, department))
            conn.commit()
            flash('User registered successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()

    return render_template('register.html')

# ---------- Faculty dashboard ----------
@app.route('/faculty', methods=['GET'])
def faculty_dashboard():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect('/login')
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, days, reason, status, document FROM Leaves WHERE faculty_id=?", (session['user_id'],))
    leaves = cursor.fetchall()
    cursor.close()
    # leaves will be passed to template (Jinja will iterate)
    return render_template('faculty_dashboard.html', faculty_name=session['name'], leaves=leaves)

# Original form-based submission
@app.route('/faculty/request_leave', methods=['POST'])
def request_leave():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect('/login')

    date = request.form['date']
    days = request.form['days']
    reason = request.form['reason']
    document = request.files.get('document')

    doc_path = None
    if document and document.filename != '':
        os.makedirs('static/uploads', exist_ok=True)
        safe_name = f"{session['user_id']}_{int(datetime.now().timestamp())}_{document.filename}"
        doc_path = os.path.join('static/uploads', safe_name)
        document.save(doc_path)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Leaves (faculty_id, faculty_name, department, date, days, reason, document, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (session['user_id'], session['name'], session.get('department'), date, days, reason, doc_path, 'Pending'))
    conn.commit()
    cursor.close()
    # clear any draft in session
    session['draft_leave'] = {}
    return redirect('/faculty')

# ---------- Chatbot endpoint (simple rule-based) ----------
@app.route('/faculty/chat', methods=['POST'])
def faculty_chat():
    if 'role' not in session or session['role'] != 'faculty':
        return jsonify({'error': 'not authenticated'}), 401

    data = request.json or {}
    message = (data.get('message') or "").strip()
    reply = "Sorry, I didn't understand that. Try: 'set date 2025-10-28', 'set days 3', 'set reason family function', 'show draft', 'submit', 'generate report', or 'download report from 2025-01-01 to 2025-12-31'."

    # ensure draft exists
    draft = session.get('draft_leave', {})

    msg_lower = message.lower()

    # simple parsing rules
    if msg_lower.startswith('set date'):
        # expected: set date YYYY-MM-DD
        parts = message.split()
        if len(parts) >= 3:
            try:
                date_str = parts[2]
                # validate date format
                datetime.strptime(date_str, '%Y-%m-%d')
                draft['date'] = date_str
                session['draft_leave'] = draft
                reply = f"Date set to {date_str}."
            except Exception:
                reply = "Please provide date in YYYY-MM-DD format. Example: set date 2025-10-28"
        else:
            reply = "Usage: set date YYYY-MM-DD"
    elif msg_lower.startswith('set days'):
        parts = message.split()
        if len(parts) >= 3:
            try:
                days = int(parts[2])
                draft['days'] = days
                session['draft_leave'] = draft
                reply = f"Number of days set to {days}."
            except Exception:
                reply = "Please provide a valid integer number of days. Example: set days 3"
        else:
            reply = "Usage: set days <number>"
    elif msg_lower.startswith('set reason') or msg_lower.startswith('reason'):
        # everything after 'set reason' is reason text
        if msg_lower.startswith('set reason'):
            reason_text = message[len('set reason'):].strip()
        else:
            reason_text = message[len('reason'):].strip()
        if reason_text:
            draft['reason'] = reason_text
            session['draft_leave'] = draft
            reply = f"Reason set."
        else:
            reply = "Please provide a reason. Example: set reason Family event"
    elif msg_lower == 'show draft' or msg_lower == 'show draft ':
        if draft:
            reply = "Current draft:\n" + "\n".join(f"{k}: {v}" for k, v in draft.items())
        else:
            reply = "No draft saved yet."
    elif msg_lower == 'clear draft':
        session['draft_leave'] = {}
        reply = "Draft cleared."
    elif msg_lower == 'submit' or msg_lower == 'submit request':
        # ensure required fields exist
        if 'date' in draft and 'days' in draft and 'reason' in draft:
            # no document via chat here; leave document None unless uploaded earlier via separate endpoint
            doc_path = draft.get('document_path')
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Leaves (faculty_id, faculty_name, department, date, days, reason, document, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], session['name'], session.get('department'), draft['date'], draft['days'], draft['reason'], doc_path, 'Pending'))
            conn.commit()
            cursor.close()
            session['draft_leave'] = {}
            reply = "Leave request submitted successfully."
        else:
            missing = [f for f in ['date', 'days', 'reason'] if f not in draft]
            reply = f"Missing fields: {', '.join(missing)}. Set them using 'set date', 'set days', 'set reason'."
    elif msg_lower.startswith('generate report') or msg_lower.startswith('download report'):
        # This instructs the front-end to call the report endpoint. Return an intent to generate a report.
        # Optional parsing: date range or leave id
        # possible messages:
        # "generate report" -> all
        # "generate report from 2025-01-01 to 2025-12-31"
        # "generate report id 12"
        if 'id' in msg_lower:
            # parse id
            parts = message.split()
            try:
                idx = parts.index('id')
                leave_id = int(parts[idx + 1])
                reply = "OK. Generating report for leave id " + str(leave_id) + "."
                return jsonify({'reply': reply, 'intent': 'generate_report', 'report_type': 'by_id', 'leave_id': leave_id})
            except Exception:
                reply = "To generate by id: 'generate report id <leave_id>'"
                return jsonify({'reply': reply})
        elif 'from' in msg_lower and 'to' in msg_lower:
            try:
                parts = msg_lower.split()
                idx_from = parts.index('from')
                idx_to = parts.index('to')
                start = parts[idx_from + 1]
                end = parts[idx_to + 1]
                # validate dates
                datetime.strptime(start, '%Y-%m-%d')
                datetime.strptime(end, '%Y-%m-%d')
                reply = f"Generating report from {start} to {end}."
                return jsonify({'reply': reply, 'intent': 'generate_report', 'report_type': 'range', 'start_date': start, 'end_date': end})
            except Exception:
                reply = "To generate by range: 'generate report from YYYY-MM-DD to YYYY-MM-DD'"
                return jsonify({'reply': reply})
        else:
            reply = "Generating full report of all your leaves."
            return jsonify({'reply': reply, 'intent': 'generate_report', 'report_type': 'all'})

    else:
        # fallback: echo + small help
        reply = "I can help set leave fields: 'set date YYYY-MM-DD', 'set days N', 'set reason ...', 'show draft', 'submit', or 'generate report'."

    return jsonify({'reply': reply, 'draft': session.get('draft_leave', {})})


# Endpoint to upload a document via chat (AJAX file upload)
@app.route('/faculty/upload_document', methods=['POST'])
def faculty_upload_document():
    if 'role' not in session or session['role'] != 'faculty':
        return jsonify({'error': 'not authenticated'}), 401
    if 'document' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    document = request.files['document']
    if document.filename == '':
        return jsonify({'error': 'empty filename'}), 400

    os.makedirs('static/uploads', exist_ok=True)
    safe_name = f"{session['user_id']}_{int(datetime.now().timestamp())}_{document.filename}"
    doc_path = os.path.join('static/uploads', safe_name)
    document.save(doc_path)

    # Save the path in current draft
    draft = session.get('draft_leave', {})
    draft['document_path'] = doc_path
    session['draft_leave'] = draft

    return jsonify({'success': True, 'doc_path': doc_path, 'message': 'Document uploaded and attached to draft.'})


# Generate PDF and return as download based on JSON request
@app.route('/faculty/generate_report', methods=['POST'])
def faculty_generate_report():
    if 'role' not in session or session['role'] != 'faculty':
        return jsonify({'error': 'not authenticated'}), 401

    data = request.json or {}
    report_type = data.get('report_type', 'all')

    if report_type == 'by_id':
        leave_id = data.get('leave_id')
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, days, reason, status, document FROM Leaves WHERE id=? AND faculty_id=?", (leave_id, session['user_id']))
        row = cursor.fetchall()
        cursor.close()
        if not row:
            return jsonify({'error': 'Leave not found or access denied.'}), 404
        leaves = row
        title = f"Leave Report - ID {leave_id}"
    elif report_type == 'range':
        start = data.get('start_date')
        end = data.get('end_date')
        try:
            # validate dates
            datetime.strptime(start, '%Y-%m-%d')
            datetime.strptime(end, '%Y-%m-%d')
        except Exception:
            return jsonify({'error': 'Invalid date format; use YYYY-MM-DD'}), 400
        leaves = get_faculty_leaves(session['user_id'], start_date=start, end_date=end)
        title = f"Leave Report ({start} to {end})"
    else:
        leaves = get_faculty_leaves(session['user_id'])
        title = "All Leaves Report"

    # Generate PDF in memory
    pdf_buffer = generate_pdf_for_leaves(session['name'], leaves, title=title)

    # Send as file
    filename = f"leave_report_{session['user_id']}_{int(datetime.now().timestamp())}.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


# HOD/Admin routes unchanged besides closing cursors
@app.route('/hod')
def hod_dashboard():
    if 'role' not in session or session['role'] != 'hod':
        return redirect('/login')
    cursor = conn.cursor()
    status_filter = request.args.get('status', 'All')
    if status_filter == 'All':
        cursor.execute("""
            SELECT L.id, L.faculty_name, L.department, L.date, L.days, L.reason, L.document, L.status
            FROM Leaves L
            WHERE L.department = ?
        """, (session['department'],))
    else:
        cursor.execute("""
            SELECT L.id, L.faculty_name, L.department, L.date, L.days, L.reason, L.document, L.status
            FROM Leaves L
            WHERE L.department = ? AND L.status = ?
        """, (session['department'], status_filter))


    leave_requests = cursor.fetchall()
    cursor.close()
    return render_template('hod_dashboard.html', hod_name=session['name'], leave_requests=leave_requests, selected_status=status_filter)

@app.route('/hod/approve/<int:leave_id>')
def approve_leave(leave_id):
    cursor = conn.cursor()
    cursor.execute("UPDATE Leaves SET status='Approved' WHERE id=?", (leave_id,))
    conn.commit()
    cursor.close()
    return redirect('/hod')

@app.route('/hod/reject/<int:leave_id>')
def reject_leave(leave_id):
    cursor = conn.cursor()
    cursor.execute("UPDATE Leaves SET status='Rejected' WHERE id=?", (leave_id,))
    conn.commit()
    cursor.close()
    return redirect('/hod')

@app.route('/admin')
def admin_dashboard():
    # Ensure only admin can access
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/login')
    
     

    cursor = conn.cursor()
    # Fetch all leave requests from all departments
    cursor.execute("""
        SELECT id, faculty_name, department, date, days, reason, document, status
        FROM Leaves
    """)
    all_leaves = cursor.fetchall()
    cursor.close()

    # Render admin dashboard
    return render_template(
        'admin_dashboard.html',
        admin_name=session.get('name'),
        all_leaves=all_leaves
    )


@app.route('/admin/chat', methods=['POST'])
def admin_chat():
    data = request.get_json()
    user_message = data.get('message', '').lower()

    if "report" in user_message:
        reply = "Sure! Click below to download the full leave report."
        intent = "admin/generate_report"
    elif "summary" in user_message or "status" in user_message:
        reply = "All departments’ leave data is updated in real-time. You can view it here."
        intent = None
    else:
        reply = "Hello Admin 👋 You can ask about reports, summaries, or system status."
        intent = None

    return jsonify({'reply': reply, 'intent': intent})

@app.route('/admin/generate_report')
def admin_generate_report():
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/login')


    cursor = conn.cursor()
    cursor.execute("""
        SELECT faculty_name, department, date, days, reason, status
        FROM Leaves
    """)
    leaves = cursor.fetchall()
    cursor.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "All Departments - Leave Report")
    y -= 30
    p.setFont("Helvetica", 10)

    for leave in leaves:
        faculty, dept, date, days, reason, status = leave
        p.drawString(50, y, f"Faculty: {faculty} | Dept: {dept} | Date: {date} | Days: {days} | Status: {status}")
        y -= 15
        p.drawString(70, y, f"Reason: {reason}")
        y -= 25
        if y < 50:  # new page
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="All_Departments_Leave_Report.pdf", mimetype='application/pdf')





@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/hod/generate_report', methods=['GET','POST'])
def hod_generate_report():
    if 'role' not in session or session['role'] != 'hod':
        return redirect('/login')

    filter_status = request.form.get('status', 'All')

    cursor = conn.cursor()
    if filter_status == "All":
        cursor.execute("""
            SELECT id, faculty_name, date, days, reason, status, document
            FROM Leaves
            WHERE department = ?
        """, (session['department'],))
    else:
        cursor.execute("""
            SELECT id, faculty_name, date, days, reason, status, document
            FROM Leaves
            WHERE department = ? AND status = ?
        """, (session['department'], filter_status))
    rows = cursor.fetchall()
    cursor.close()

    pdf_buffer = hod_generate_pdf_for_leaves(
        faculty_name=f"{session['department']} Department",
        leaves=rows,
        title=f"{session['department']} - {filter_status} Leave Report"
    )
    filename = f"{session['department']}_{filter_status}_report.pdf"
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

# ---------- HOD Chatbot (new) ----------
@app.route('/hod/chat', methods=['POST'])
def hod_chat():
    if 'role' not in session or session['role'] != 'hod':
        return jsonify({'error': 'not authenticated'}), 401

    data = request.json or {}
    message = (data.get('message') or "").strip().lower()
    reply = "I can help you view leaves or generate reports. Try: 'show approved', 'show rejected', 'show pending', 'generate report for approved', 'generate report from 2025-01-01 to 2025-02-01', etc."

    intent = None
    filter_status = None
    date_range = None

    # Filter by status
    if "show approved" in message:
        filter_status = "Approved"
        reply = "Here are approved leaves for your department."
    elif "show rejected" in message:
        filter_status = "Rejected"
        reply = "Here are rejected leaves for your department."
    elif "show pending" in message:
        filter_status = "Pending"
        reply = "Here are pending leaves for your department."
    elif "show all" in message or "all leaves" in message:
        filter_status = "All"
        reply = "Showing all leaves for your department."

    # Generate report logic
    elif "generate report" in message or "download report" in message:
        intent = "hod/generate_report"

        if "approved" in message:
            filter_status = "Approved"
            reply = "Generating report for approved leaves."
        elif "rejected" in message:
            filter_status = "Rejected"
            reply = "Generating report for rejected leaves."
        elif "pending" in message:
            filter_status = "Pending"
            reply = "Generating report for pending leaves."
        elif "from" in message and "to" in message:
            try:
                parts = message.split()
                start = parts[parts.index("from") + 1]
                end = parts[parts.index("to") + 1]
                datetime.strptime(start, "%Y-%m-%d")
                datetime.strptime(end, "%Y-%m-%d")
                date_range = (start, end)
                reply = f"Generating report from {start} to {end}."
            except Exception:
                reply = "Please use correct format: 'generate report from YYYY-MM-DD to YYYY-MM-DD'"
        else:
            reply = "Generating report for all leaves."

    # If filtering
    if filter_status:
        cursor = conn.cursor()
        if filter_status == "All":
            cursor.execute("""
                SELECT id, faculty_name, date, days, reason, status, document
                FROM Leaves
                WHERE department = ?
                ORDER BY date DESC
            """, (session['department'],))
        else:
            cursor.execute("""
                SELECT id, faculty_name, date, days, reason, status, document
                FROM Leaves
                WHERE department = ? AND status = ?
                ORDER BY date DESC
            """, (session['department'], filter_status))
        rows = cursor.fetchall()
        cursor.close()
        if rows:
            formatted = "<br>".join([f"{r[0]} - {r[1]} - {r[4]}" for r in rows[:5]])  # show first 5
            reply += f"<br><br><b>Top results:</b><br>{formatted}"
        else:
            reply += " No records found."

    # If intent = generate report
    if intent == "hod/generate_report":
        return jsonify({
            'reply': reply,
            'intent': 'hod/generate_report',
            'status': filter_status,
            'range': date_range
        })

    return jsonify({'reply': reply})


if __name__ == "__main__":
    # For development only; in production use a proper WSGI server
    app.run(debug=True)
