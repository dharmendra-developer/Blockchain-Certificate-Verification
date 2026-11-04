from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix
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
# On Render, set DATA_DIR=/var/data and attach a Persistent Disk at /var/data.
# Locally, keep the original database folder.
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "database"))
DB_PATH = os.path.join(DATA_DIR, "certificates.db")
QR_DIR = os.path.join(DATA_DIR, "qr")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-this-secret-key")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "true").lower() == "true",
)
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

# Gunicorn imports app.py without running the __main__ block. Initialize on import.
init_db()

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

        # Do not label a certificate as blockchain-issued unless the Sepolia
        # transaction was actually submitted and confirmed.
        if not blockchain.connected or not blockchain.account:
            flash("Blockchain is not ready. Configure Sepolia RPC, contract address, and test-wallet PRIVATE_KEY before issuing certificates.", "danger")
            return redirect(url_for("issue"))
        try:
            tx_hash = blockchain.issue_certificate(certificate_id, cert_hash)
        except Exception as exc:
            app.logger.exception("Blockchain certificate issuance failed")
            flash("Blockchain transaction failed. Check Sepolia test ETH, RPC, contract address, and wallet configuration. No certificate was saved.", "danger")
            return redirect(url_for("issue"))

        public_root = PUBLIC_BASE_URL or request.url_root.rstrip("/")
        verify_url = public_root + url_for("verify", certificate_id=certificate_id)
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

    ink = colors.HexColor("#17399f")
    blue = colors.HexColor("#1b73d4")
    cyan = colors.HexColor("#19bad0")
    gold = colors.HexColor("#e7ca63")
    muted = colors.HexColor("#4c5668")
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, page_width, page_height, stroke=0, fill=1)

    def draw_polygon(points, fill_color):
        path = pdf.beginPath()
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
        path.close()
        pdf.setFillColor(fill_color)
        pdf.drawPath(path, stroke=0, fill=1)

    edge_shapes = [
        ([(0, page_height), (90, page_height), (55, page_height - 78),
          (145, page_height - 164), (98, page_height - 205),
          (0, page_height - 126)], ink),
        ([(0, page_height - 82), (36, page_height - 82),
          (105, page_height - 165), (79, page_height - 165)], cyan),
        ([(0, 0), (126, 0), (54, 105), (0, 198)], ink),
        ([(25, 0), (43, 0), (0, 70)], blue),
        ([(0, 23), (42, 23), (98, 102), (71, 102)], cyan),
    ]
    for shape, shape_color in edge_shapes:
        draw_polygon(shape, shape_color)
        draw_polygon([(page_width - x, y) for x, y in shape], shape_color)

    pdf.setStrokeColor(ink)
    pdf.setLineWidth(0.8)
    pdf.rect(38, 28, page_width - 76, page_height - 56, stroke=1, fill=0)

    institution_lines = simpleSplit(cert["institute"], "Helvetica-Bold", 10, 560)[:2]
    institution_y = 548
    pdf.setFillColor(ink)
    pdf.setFont("Helvetica-Bold", 12)
    for line in institution_lines:
        pdf.drawCentredString(page_width / 2, institution_y, line)
        institution_y -= 13

    qr_path = os.path.join(QR_DIR, cert["qr_filename"] or "")
    qr_x = 748
    qr_y = 54
    qr_size = 42
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(colors.HexColor("#c9ced8"))
    pdf.setLineWidth(0.7)
    pdf.roundRect(qr_x - 6, qr_y - 12, qr_size + 12, qr_size + 24, 3, stroke=1, fill=1)
    if os.path.isfile(qr_path):
        pdf.drawImage(qr_path, qr_x, qr_y, width=qr_size, height=qr_size,
                      preserveAspectRatio=True, mask="auto")
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica-Bold", 6)
    pdf.drawCentredString(qr_x + qr_size / 2, qr_y - 7, "SCAN TO VERIFY")

    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 42)
    pdf.drawCentredString(page_width / 2, 478, "CERTIFICATE")
    pdf.setFillColor(ink)
    pdf.setFont("Times-Italic", 20)
    pdf.drawCentredString(page_width / 2, 450, "of Completion")

    pdf.setFillColor(muted)
    pdf.setFont("Times-Roman", 14)
    pdf.drawCentredString(page_width / 2, 385, "This is to certify that")

    name_lines = simpleSplit(cert["student_name"], "Times-Italic", 42, 570)[:2]
    name_y = 337
    pdf.setFillColor(ink)
    pdf.setFont("Times-Italic", 42)
    for line in name_lines:
        pdf.drawCentredString(page_width / 2, name_y, line)
        name_y -= 43

    pdf.setStrokeColor(colors.HexColor("#293346"))
    pdf.setLineWidth(0.8)
    pdf.line(205, 280, page_width - 205, 280)
    pdf.setFillColor(muted)
    pdf.setFont("Times-Roman", 12)
    pdf.drawCentredString(page_width / 2, 254, "has successfully completed")

    course_lines = simpleSplit(cert["course"], "Times-Bold", 20, 590)[:2]
    course_y = 226
    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 20)
    for line in course_lines:
        pdf.drawCentredString(page_width / 2, course_y, line)
        course_y -= 23

    if cert["description"]:
        description_lines = simpleSplit(cert["description"], "Times-Roman", 11, 570)
        if len(description_lines) > 2:
            description_lines = description_lines[:2]
            last_line = description_lines[-1]
            while last_line and pdfmetrics.stringWidth(last_line + "...", "Times-Roman", 11) > 570:
                last_line = last_line[:-1]
            description_lines[-1] = last_line.rstrip() + "..."
        description_y = 182
        pdf.setFillColor(muted)
        pdf.setFont("Times-Roman", 11)
        for line in description_lines:
            pdf.drawCentredString(page_width / 2, description_y, line)
            description_y -= 14

    pdf.setStrokeColor(colors.HexColor("#c5ccda"))
    pdf.line(155, 149, page_width - 155, 149)
    metadata = (
        (225, "ISSUE DATE", cert["issue_date"]),
        (page_width / 2, "PROGRAM PERIOD", f"{cert['start_date'] or 'Not provided'} to {cert['end_date'] or 'Not provided'}"),
        (617, "CERTIFICATE ID", cert["certificate_id"]),
    )
    for center_x, label, value in metadata:
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(center_x, 137, label)
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(center_x, 123, value)

    pdf.setStrokeColor(ink)
    pdf.setLineWidth(0.7)
    pdf.line(112, 91, 294, 91)
    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 10)
    pdf.drawCentredString(203, 76, cert["institute"][:42])
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawCentredString(203, 64, "AUTHORIZED SIGNATORY")

    pdf.setStrokeColor(ink)
    pdf.line(548, 91, 730, 91)
    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 10)
    pdf.drawCentredString(639, 76, cert["issue_date"])
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawCentredString(639, 64, "DATE OF ISSUE")

    seal_x = page_width / 2
    seal_y = 88
    draw_polygon([(seal_x - 15, 71), (seal_x - 4, 42), (seal_x + 3, 50),
                  (seal_x + 12, 42), (seal_x + 16, 72)], gold)
    pdf.setFillColor(gold)
    pdf.setStrokeColor(colors.HexColor("#b69b3f"))
    pdf.setLineWidth(1.2)
    pdf.circle(seal_x, seal_y, 29, stroke=1, fill=1)
    pdf.setStrokeColor(colors.white)
    pdf.setLineWidth(0.8)
    pdf.circle(seal_x, seal_y, 23, stroke=1, fill=0)
    pdf.setFillColor(ink)
    pdf.setFont("Times-Bold", 12)
    pdf.drawCentredString(seal_x, seal_y + 2, "BC")
    pdf.setFont("Helvetica-Bold", 6)
    pdf.drawCentredString(seal_x, seal_y - 9, "VERIFIED")

    pdf.setFillColor(muted)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(112, 35, "SHA-256")
    pdf.setFillColor(ink)
    pdf.setFont("Courier", 7)
    pdf.drawString(151, 35, cert["certificate_hash"])
    if cert["transaction_hash"]:
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Bold", 6)
        pdf.drawString(112, 24, "BLOCKCHAIN TX")
        pdf.setFillColor(ink)
        pdf.setFont("Courier", 6)
        pdf.drawString(184, 24, cert["transaction_hash"][:76])
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

    valid = False
    message = "Certificate exists locally, but blockchain verification is unavailable."
    if chain_record and "error" not in chain_record:
        valid = bool(chain_record.get("exists") and chain_record["certificateHash"] == cert["certificate_hash"])
        message = "Blockchain hash matches." if valid else "Blockchain record is missing or the hash does not match."
    elif blockchain.connected:
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

@app.route("/health")
def health():
    return {"status": "ok", "blockchain_connected": blockchain.connected}, 200

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
