import qrcode

def generate_qr(data, filename="qr.png"):
    img = qrcode.make(data)
    img.save(filename)
    return filename
