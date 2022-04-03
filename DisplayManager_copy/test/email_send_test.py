import email, smtplib, ssl

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


port = 465  # For starttls
smtp_server = "smtp.gmail.com"
sender_email = "kdiehl.pictureframe@gmail.com"
receiver_email = "kdiehl.pictureframe@gmail.com"
#receiver_email = 'katrina@higham.com'

password = r'mM3GTBvfBBJVn4r' #input("Type your password and press enter:")


subject = "An email with attachment from Python"
body = "This is an email with attachment sent from Python"

# Create a multipart message and set headers
message = MIMEMultipart()
message["From"] = sender_email
message["To"] = receiver_email
message["Subject"] = subject
#message["Bcc"] = receiver_email  # Recommended for mass emails

# Add body to email
message.attach(MIMEText(body, "plain"))


# File attachment
filename = 'PictureFrame2020img.jpg'
with open(filename, "rb") as attachment:
    # Add file as application/octet-stream
    # Email client can usually download this automatically as attachment
    part = MIMEBase("application", "octet-stream")
    part.set_payload(attachment.read())

# Encode file in ASCII characters to send by email    
encoders.encode_base64(part)

# Add header as key/value pair to attachment part
part.add_header(
    "Content-Disposition",
    "attachment; filename= {}".format(filename),
)

# Add attachment to message and convert message to string
#message.attach(part)
text = message.as_string()


print(text)

if 1:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, text)