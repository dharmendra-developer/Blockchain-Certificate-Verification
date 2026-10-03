import os
import qrcode

def create_qr(data, output_dir, certificate_id):
    filename = f"{certificate_id}.png"
    path = os.path.join(output_dir, filename)
    img = qrcode.make(data)
    img.save(path)
    return filename
