from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory, session
import sqlite3, os, hashlib, json, datetime
import hmac
from functools import wraps
from io import BytesIO
from blockchain.blockchain import BlockchainClient
from utils.qr_generator import create_qr
from utils.hashing import certificate_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "certificates.db")
QR_DIR = os.path.join(BASE_DIR, "static", "qr")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-this-secret-key")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "authority")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Authority@123")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")

# Blockchain connection is optional at startup. The UI remains usable if Ganache is not running.
blockchain = BlockchainClient()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id TEXT UNIQUE NOT NULL,
            student_name TEXT NOT NULL,
            course TEXT NOT NULL,
            institute TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            start_date TEXT NOT NULL DEFAULT '',
            end_date TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            certificate_hash TEXT NOT NULL,
            transaction_hash TEXT,
            qr_filename TEXT,
            created_at TEXT NOT NULL
            )
    """)
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(certificates)")}
    for column in ("start_date", "end_date", "description"):
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE certificates ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    conn.commit()
    conn.close()

def authority_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("authority_authenticated"):
            flash("Please sign in as the certificate authority to view certificates.", "danger")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view

@app.before_request
def protect_qr_files():
    if request.path.startswith("/static/qr/") and not session.get("authority_authenticated"):
        flash("Please sign in as the certificate authority to view certificates.", "danger")
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if hmac.compare_digest(username, ADMIN_USERNAME) and hmac.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session["authority_authenticated"] = True
            flash("Certificate authority signed in.", "success")
            return redirect(url_for("index"))
        flash("Username or password is incorrect.", "danger")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("login"))

@app.route("/")
@authority_required
def index():
    conn = db()
    certificates = conn.execute("SELECT * FROM certificates ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", certificates=certificates, blockchain=blockchain.status())

@app.route("/issue", methods=["GET", "POST"])
@authority_required
def issue():
    if request.method == "POST":
        student_name = request.form["student_name"].strip()
        course = request.form["course"].strip()
        institute = request.form["institute"].strip()
        issue_date = request.form["issue_date"].strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        description = request.form.get("description", "").strip()

        try:
            program_start = datetime.date.fromisoformat(start_date)
            program_end = datetime.date.fromisoformat(end_date)
        except ValueError:
            flash("Enter valid program start and end dates.", "danger")
            return redirect(url_for("issue"))
        if program_end < program_start:
            flash("Program end date cannot be earlier than its start date.", "danger")
            return redirect(url_for("issue"))
        if not description or len(description) > 500:
            flash("Add a program description of up to 500 characters.", "danger")
            return redirect(url_for("issue"))

        certificate_id = "CERT-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[-12:]
        payload = {
            "certificate_id": certificate_id,
            "student_name": student_name,
            "course": course,
            "institute": institute,
            "issue_date": issue_date,
            "start_date": start_date,
            "end_date": end_date,
            "description": description
        }
        cert_hash = certificate_hash(payload)

        tx_hash = None
        if blockchain.connected:
            try:
                tx_hash = blockchain.issue_certificate(certificate_id, cert_hash)
            except Exception as exc:
                flash(f"Blockchain transaction failed: {exc}", "danger")

        verify_path = url_for("verify", certificate_id=certificate_id)
        verify_url = f"{PUBLIC_BASE_URL}{verify_path}" if PUBLIC_BASE_URL else request.url_root.rstrip("/") + verify_path
        qr_filename = create_qr(verify_url, QR_DIR, certificate_id)

        conn = db()
        conn.execute("""INSERT INTO certificates
            (certificate_id, student_name, course, institute, issue_date, start_date, end_date,
             description, certificate_hash, transaction_hash, qr_filename, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (certificate_id, student_name, course, institute, issue_date, start_date, end_date,
             description, cert_hash, tx_hash, qr_filename,
             datetime.datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        conn.close()

        flash(f"Certificate {certificate_id} issued successfully.", "success")
        return redirect(url_for("certificate", certificate_id=certificate_id))
    return render_template("issue.html")

@app.route("/certificate/<certificate_id>")
@authority_required
def certificate(certificate_id):
    conn = db()
    cert = conn.execute("SELECT * FROM certificates WHERE certificate_id=?", (certificate_id,)).fetchone()
    conn.close()
    if not cert:
        return "Certificate not found", 404
    return render_template("certificate.html", cert=cert)

@app.route("/certificate/<certificate_id>/delete", methods=["POST"])
@authority_required
def delete_certificate(certificate_id):
    conn = db()
    cert = conn.execute(
        "SELECT qr_filename FROM certificates WHERE certificate_id=?",
        (certificate_id,)
    ).fetchone()
    if not cert:
        conn.close()
        flash("Certificate not found.", "danger")
        return redirect(url_for("index"))

    conn.execute("DELETE FROM certificates WHERE certificate_id=?", (certificate_id,))
    conn.commit()
    conn.close()

    qr_filename = cert["qr_filename"] or ""
    if qr_filename and os.path.basename(qr_filename) == qr_filename:
        try:
            os.remove(os.path.join(QR_DIR, qr_filename))
        except FileNotFoundError:
            pass
        except OSError:
            flash("The certificate was deleted, but its QR image could not be removed.", "danger")

    flash(
        f"Certificate {certificate_id} was deleted from the local registry. "
        "Any blockchain record remains immutable.",
        "success"
    )
    return redirect(url_for("index"))

@app.route("/certificate/<certificate_id>/download")
@authority_required
def download_certificate(certificate_id):
    conn = db()
    cert = conn.execute("SELECT * FROM certificates WHERE certificate_id=?", (certificate_id,)).fetchone()
    conn.close()
    if not cert:
        return "Certificate not found", 404

    pdf_buffer = BytesIO()
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(pdf_buffer, pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle(f"Certificate {cert['certificate_id']}")
    pdf.setAuthor("BlockCert Certificate Authority")
    pdf.setSubject(f"Certificate issued to {cert['student_name']}")

    ink = colors.HexColor("#12314a")
    cyan = colors.HexColor("#087f84")
    gold = colors.HexColor("#d0aa59")
    muted = colors.HexColor("#59616b")
    pdf.setFillColor(cyan)
    pdf.rect(0, 0, page_width, page_height, stroke=0, fill=1)

    def draw_sweep(start, control_one, control_two, end, color, width):
        path = pdf.beginPath()
        path.moveTo(*start)
        path.curveTo(*control_one, *control_two, *end)
        pdf.setStrokeColor(color)
        pdf.setLineWidth(width)
        pdf.setLineCap(1)
        pdf.drawPath(path, stroke=1, fill=0)

    left_sweep = ((0, page_height * 0.56), (45, 430), (210, 565), (470, page_height))
    right_sweep = ((page_width, 315), (795, 170), (625, 34), (485, 0))
    for sweep in (left_sweep, right_sweep):
        draw_sweep(*sweep, ink, 64)
        draw_sweep(*sweep, cyan, 52)
        draw_sweep(*sweep, gold, 12)

    panel = pdf.beginPath()
    panel.moveTo(0, page_height * 0.56)
    panel.curveTo(45, 430, 210, 565, 470, page_height)
    panel.lineTo(page_width, page_height)
    panel.lineTo(page_width, 315)
    panel.curveTo(795, 170, 625, 34, 485, 0)
    panel.lineTo(0, 0)
    panel.close()
    pdf.setFillColor(colors.white)
    pdf.drawPath(panel, stroke=0, fill=1)

    pdf.saveState()
    pdf.clipPath(panel, stroke=0, fill=0)
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(3.2)
    pdf.rect(36, 18, page_width - 68, page_height - 36, stroke=1, fill=0)
    pdf.setStrokeColor(ink)
    pdf.setLineWidth(1.35)
    pdf.rect(45, 27, page_width - 86, page_height - 54, stroke=1, fill=0)
    pdf.setFillColor(gold)
    for pin_x, pin_y in ((36, 18), (page_width - 32, 18),
                         (36, page_height - 18), (page_width - 32, page_height - 18)):
        pdf.circle(pin_x, pin_y, 3.8, stroke=0, fill=1)
    pdf.restoreState()

    qr_path = os.path.join(QR_DIR, cert["qr_filename"] or "")
    qr_x = page_width - 108
    qr_y = 50
    qr_size = 72
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(colors.HexColor("#c9ced8"))
    pdf.setLineWidth(0.7)
    pdf.roundRect(qr_x - 4, qr_y - 11, qr_size + 8, qr_size + 24, 3, stroke=1, fill=1)
    if os.path.isfile(qr_path):
        pdf.drawImage(qr_path, qr_x, qr_y, width=qr_size, height=qr_size,
                      preserveAspectRatio=True, mask="auto")
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica-Bold", 6)
    pdf.drawCentredString(qr_x + qr_size / 2, qr_y - 9, "SCAN TO VERIFY")

    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 50)
    pdf.drawCentredString(page_width / 2, 478, "CERTIFICATE")
    pdf.setFillColor(ink)
    pdf.setFont("Times-Italic", 20)
    pdf.drawCentredString(page_width / 2, 450, "of Completion")

    institution_font = 30
    institution_lines = simpleSplit(cert["institute"], "Helvetica-Bold", institution_font, 560)
    if len(institution_lines) > 1:
        institution_font = 18
        institution_lines = simpleSplit(cert["institute"], "Helvetica-Bold", institution_font, 560)
    while len(institution_lines) > 2 and institution_font > 10:
        institution_font -= 1
        institution_lines = simpleSplit(cert["institute"], "Helvetica-Bold", institution_font, 560)
    if len(institution_lines) > 2:
        institution_lines = institution_lines[:2]
        last_line = institution_lines[-1]
        while last_line and pdfmetrics.stringWidth(last_line + "...", "Helvetica-Bold", institution_font) > 560:
            last_line = last_line[:-1]
        institution_lines[-1] = last_line.rstrip() + "..."
    pdf.setFillColor(ink)
    pdf.setFont("Helvetica-Bold", institution_font)
    institution_y = 430 if len(institution_lines) > 1 else 424
    for line in institution_lines:
        pdf.drawCentredString(page_width / 2, institution_y, line)
        institution_y -= institution_font + 1
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1.2)
    pdf.line(page_width / 2 - 28, 403, page_width / 2 + 28, 403)

    pdf.setFillColor(muted)
    pdf.setFont("Times-Roman", 18)
    presented_y = 390
    pdf.drawCentredString(page_width / 2, presented_y, "This is to certify that")

    name_font = 38
    name_lines = simpleSplit(cert["student_name"], "Times-Italic", name_font, 600)
    while len(name_lines) > 2 and name_font > 22:
        name_font -= 2
        name_lines = simpleSplit(cert["student_name"], "Times-Italic", name_font, 600)
    if len(name_lines) > 2:
        name_lines = name_lines[:2]
        last_line = name_lines[-1]
        while last_line and pdfmetrics.stringWidth(last_line + "...", "Times-Italic", name_font) > 600:
            last_line = last_line[:-1]
        name_lines[-1] = last_line.rstrip() + "..."

    name_y = 344
    name_step = name_font + 2
    pdf.setFillColor(ink)
    pdf.setFont("Times-Italic", name_font)
    for line in name_lines:
        pdf.drawCentredString(page_width / 2, name_y, line)
        name_y -= name_step

    rule_y = 344 - (len(name_lines) - 1) * name_step - 18
    pdf.setStrokeColor(colors.HexColor("#293346"))
    pdf.setLineWidth(0.8)
    pdf.line(205, rule_y, page_width - 205, rule_y)
    recognition_y = rule_y - 24
    pdf.setFillColor(muted)
    pdf.setFont("Times-Roman", 18)
    pdf.drawCentredString(page_width / 2, recognition_y, "has successfully completed")

    course_font = 18
    course_lines = simpleSplit(cert["course"], "Times-Bold", course_font, 590)
    while len(course_lines) > 2 and course_font > 14:
        course_font -= 2
        course_lines = simpleSplit(cert["course"], "Times-Bold", course_font, 590)
    if len(course_lines) > 2:
        course_lines = course_lines[:2]
        last_line = course_lines[-1]
        while last_line and pdfmetrics.stringWidth(last_line + "...", "Times-Bold", course_font) > 590:
            last_line = last_line[:-1]
        course_lines[-1] = last_line.rstrip() + "..."

    course_y = recognition_y - 28
    course_step = course_font + 3
    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", course_font)
    for line in course_lines:
        pdf.drawCentredString(page_width / 2, course_y, line)
        course_y -= course_step

    if cert["description"]:
        description_font = 15
        description_width = 570
        description_lines = simpleSplit(
            cert["description"], "Times-Roman", description_font, description_width
        )
        description_y = course_y - 7
        available_height = max(0, description_y - 165)
        while (len(description_lines) * (description_font + 2) > available_height
               and description_font > 6):
            description_font -= 1
            description_width = min(640, description_width + 16)
            description_lines = simpleSplit(
                cert["description"], "Times-Roman", description_font, description_width
            )
        pdf.setFillColor(muted)
        pdf.setFont("Times-Roman", description_font)
        for line in description_lines:
            pdf.drawCentredString(page_width / 2, description_y, line)
            description_y -= description_font + 2

    pdf.setStrokeColor(colors.HexColor("#c5ccda"))
    pdf.line(155, 157, page_width - 155, 157)
    metadata = (
        (225, "ISSUE DATE", cert["issue_date"]),
        (page_width / 2, "PROGRAM PERIOD", f"{cert['start_date'] or 'Not provided'} to {cert['end_date'] or 'Not provided'}"),
        (617, "CERTIFICATE ID", cert["certificate_id"]),
    )
    for center_x, label, value in metadata:
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(center_x, 145, label)
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(center_x, 131, value)

    pdf.setStrokeColor(ink)
    pdf.setLineWidth(0.7)
    pdf.line(138, 83, 268, 83)
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawCentredString(203, 56, "AUTHORIZED SIGNATORY")

    seal_path = os.path.join(BASE_DIR, "static", "certificate-award-seal.png")
    if os.path.isfile(seal_path):
        pdf.drawImage(seal_path, page_width / 2 - 41, 37, width=82, height=82,
                      preserveAspectRatio=True, mask="auto")

    pdf.setFillColor(muted)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(112, 9, "SHA-256")
    pdf.setFillColor(ink)
    pdf.setFont("Courier", 7)
    pdf.drawString(151, 9, cert["certificate_hash"])
    if cert["transaction_hash"]:
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Bold", 6)
        pdf.drawString(112, 31, "BLOCKCHAIN TX")
        pdf.setFillColor(ink)
        pdf.setFont("Courier", 6)
        pdf.drawString(184, 31, cert["transaction_hash"][:76])
    pdf.save()
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"{cert['certificate_id']}.pdf"
    )

@app.route("/verify")
def verify_page():
    return render_template("verify.html", result=None)

@app.route("/verify/<certificate_id>")
def verify(certificate_id):
    conn = db()
    cert = conn.execute("SELECT * FROM certificates WHERE certificate_id=?", (certificate_id,)).fetchone()
    conn.close()
    if not cert:
        return render_template("verify.html", result={"valid": False, "message": "Certificate not found."})
    chain_record = None
    if blockchain.connected:
        try:
            chain_record = blockchain.get_certificate(certificate_id)
        except Exception as exc:
            chain_record = {"error": str(exc)}

    valid = True
    message = "Certificate found in local database."
    if chain_record and "error" not in chain_record:
        valid = chain_record["certificateHash"] == cert["certificate_hash"]
        message = "Blockchain hash matches." if valid else "Hash mismatch: record may have been altered."
    elif blockchain.connected:
        valid = False
        message = "Certificate is not present on the blockchain."

    return render_template("verify.html", result={
        "valid": valid, "message": message, "cert": cert, "chain": chain_record
    })

@app.route("/api/verify/<certificate_id>")
@authority_required
def api_verify(certificate_id):
    conn = db()
    cert = conn.execute("SELECT * FROM certificates WHERE certificate_id=?", (certificate_id,)).fetchone()
    conn.close()
    if not cert:
        return {"valid": False, "message": "Certificate not found."}, 404
    chain = None
    if blockchain.connected:
        try: chain = blockchain.get_certificate(certificate_id)
        except Exception as exc: chain = {"error": str(exc)}
    valid = bool(chain and "error" not in chain and chain["certificateHash"] == cert["certificate_hash"])
    return {"valid": valid, "certificate": dict(cert), "blockchain": chain}

@app.route("/qr/<filename>")
@authority_required
def qr(filename):
    return send_from_directory(QR_DIR, filename)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host=APP_HOST, port=5000)
