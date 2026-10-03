from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory, session
import sqlite3, os, hashlib, json, datetime
import hmac
from functools import wraps
from io import BytesIO
from blockchain.blockchain import BlockchainClient
from utils.qr_generator import create_qr
from utils.hashing import certificate_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
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
            flash("Please sign in as the certificate authority to issue certificates.", "danger")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if hmac.compare_digest(username, ADMIN_USERNAME) and hmac.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session["authority_authenticated"] = True
            flash("Certificate authority signed in.", "success")
            return redirect(url_for("issue"))
        flash("Username or password is incorrect.", "danger")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("login"))

@app.route("/")
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

        verify_url = request.url_root.rstrip("/") + url_for("verify", certificate_id=certificate_id)
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
def certificate(certificate_id):
    conn = db()
    cert = conn.execute("SELECT * FROM certificates WHERE certificate_id=?", (certificate_id,)).fetchone()
    conn.close()
    if not cert:
        return "Certificate not found", 404
    return render_template("certificate.html", cert=cert)

@app.route("/certificate/<certificate_id>/download")
def download_certificate(certificate_id):
    conn = db()
    cert = conn.execute("SELECT * FROM certificates WHERE certificate_id=?", (certificate_id,)).fetchone()
    conn.close()
    if not cert:
        return "Certificate not found", 404

    pdf_buffer = BytesIO()
    page_width, page_height = landscape(letter)
    pdf = canvas.Canvas(pdf_buffer, pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle(f"Certificate {cert['certificate_id']}")
    pdf.setAuthor("BlockCert Certificate Authority")
    pdf.setSubject(f"Certificate issued to {cert['student_name']}")

    navy = colors.HexColor("#183047")
    gold = colors.HexColor("#b28a45")
    muted = colors.HexColor("#667085")
    paper = colors.HexColor("#fffdf8")
    pdf.setFillColor(paper)
    pdf.rect(0, 0, page_width, page_height, stroke=0, fill=1)
    pdf.setStrokeColor(navy)
    pdf.setLineWidth(2)
    pdf.rect(24, 24, page_width - 48, page_height - 48, stroke=1, fill=0)
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(0.8)
    pdf.rect(33, 33, page_width - 66, page_height - 66, stroke=1, fill=0)

    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(page_width / 2, page_height - 72, "BLOCKCERT")
    pdf.setFillColor(gold)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(page_width / 2, page_height - 87, "DIGITAL CREDENTIAL")
    pdf.setStrokeColor(gold)
    pdf.line(page_width / 2 - 34, page_height - 98, page_width / 2 + 34, page_height - 98)

    pdf.setFillColor(navy)
    pdf.setFont("Times-Bold", 25)
    pdf.drawCentredString(page_width / 2, page_height - 142, "CERTIFICATE OF ACHIEVEMENT")
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(page_width / 2, page_height - 174, "THIS CERTIFICATE IS PRESENTED TO")

    student_name = cert["student_name"]
    name_size = 30
    while name_size > 18 and pdfmetrics.stringWidth(student_name, "Times-Bold", name_size) > page_width - 150:
        name_size -= 1
    pdf.setFillColor(navy)
    pdf.setFont("Times-Bold", name_size)
    pdf.drawCentredString(page_width / 2, page_height - 214, student_name)
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(1)
    pdf.line(page_width / 2 - 72, page_height - 227, page_width / 2 + 72, page_height - 227)

    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(page_width / 2, page_height - 253, "for successfully completing")
    course_lines = simpleSplit(cert["course"], "Times-Bold", 19, page_width - 170)
    pdf.setFillColor(navy)
    pdf.setFont("Times-Bold", 19)
    course_y = page_height - 284
    for line in course_lines[:2]:
        pdf.drawCentredString(page_width / 2, course_y, line)
        course_y -= 24

    issuer_y = course_y - 10
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(page_width / 2, issuer_y, "ISSUED BY")
    issuer_lines = simpleSplit(cert["institute"], "Helvetica-Bold", 12, page_width - 190)
    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 12)
    for index, line in enumerate(issuer_lines[:2]):
        pdf.drawCentredString(page_width / 2, issuer_y - 19 - index * 15, line)

    pdf.setFont("Helvetica-Bold", 7)
    pdf.setFillColor(muted)
    pdf.drawCentredString(page_width / 2, issuer_y - 19 - (len(issuer_lines[:2]) - 1) * 15 - 20, "PROGRAM PERIOD")
    period_value = f"{cert['start_date'] or 'Not provided'} to {cert['end_date'] or 'Not provided'}"
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(navy)
    period_y = issuer_y - 19 - (len(issuer_lines[:2]) - 1) * 15 - 34
    pdf.drawCentredString(page_width / 2, period_y, period_value)

    description_label_y = period_y - 21
    pdf.setFont("Helvetica-Bold", 7)
    pdf.setFillColor(muted)
    pdf.drawCentredString(page_width / 2, description_label_y, "PROGRAM DESCRIPTION")
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(navy)
    description_lines = simpleSplit(cert["description"] or "Program description not provided.", "Helvetica", 8, page_width - 190)
    description_y = description_label_y - 13
    for line in description_lines[:4]:
        pdf.drawCentredString(page_width / 2, description_y, line)
        description_y -= 10

    metadata_y = 112
    pdf.setStrokeColor(colors.HexColor("#d9d2c4"))
    pdf.line(68, metadata_y + 17, page_width - 68, metadata_y + 17)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.setFillColor(muted)
    pdf.drawString(72, metadata_y, "ISSUE DATE")
    pdf.drawString(205, metadata_y, "PROGRAM DATES")
    pdf.drawString(420, metadata_y, "CERTIFICATE ID")
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(navy)
    pdf.drawString(72, metadata_y - 13, cert["issue_date"])
    pdf.drawString(205, metadata_y - 13, f"{cert['start_date'] or '-'} to {cert['end_date'] or '-'}")
    pdf.drawString(420, metadata_y - 13, cert["certificate_id"])
    pdf.setFont("Helvetica-Bold", 7)
    pdf.setFillColor(muted)
    pdf.drawString(72, metadata_y - 34, "SHA-256 FINGERPRINT")
    pdf.setFont("Courier", 6.5)
    pdf.setFillColor(navy)
    pdf.drawString(72, metadata_y - 46, cert["certificate_hash"])
    if cert["transaction_hash"]:
        pdf.setFont("Helvetica-Bold", 7)
        pdf.setFillColor(muted)
        pdf.drawString(72, metadata_y - 61, "BLOCKCHAIN TRANSACTION")
        pdf.setFont("Courier", 6)
        pdf.setFillColor(navy)
        pdf.drawString(72, metadata_y - 72, cert["transaction_hash"][:80])

    qr_path = os.path.join(QR_DIR, cert["qr_filename"] or "")
    if os.path.isfile(qr_path):
        qr_size = 0.95 * inch
        pdf.drawImage(qr_path, page_width - 72 - qr_size, 63, width=qr_size, height=qr_size,
                      preserveAspectRatio=True, mask="auto")
        pdf.setFont("Helvetica-Bold", 6.5)
        pdf.setFillColor(muted)
        pdf.drawCentredString(page_width - 72 - qr_size / 2, 53, "SCAN TO VERIFY")

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
def qr(filename):
    return send_from_directory(QR_DIR, filename)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
