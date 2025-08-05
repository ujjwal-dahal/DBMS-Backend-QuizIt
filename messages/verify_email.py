def otp_email_body(otp: str):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            body {{
                background-color: #121212;
                color: #e0e0e0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                padding: 30px;
                margin: 0;
            }}
            .container {{
                max-width: 480px;
                margin: auto;
                background-color: #1e1e1e;
                border-radius: 10px;
                padding: 40px 30px;
                box-shadow: 0 0 15px rgba(0, 0, 0, 0.6);
                text-align: center;
            }}
            h2 {{
                color: #90caf9;
                margin-bottom: 20px;
                font-weight: 700;
            }}
            p {{
                font-size: 16px;
                line-height: 1.5;
                margin-bottom: 30px;
                color: #cccccc;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: 700;
                letter-spacing: 10px;
                background-color: #263238;
                padding: 15px 0;
                border-radius: 8px;
                color: #81d4fa;
                user-select: all;
                margin-bottom: 30px;
            }}
            .footer {{
                font-size: 12px;
                color: #555;
                margin-top: 40px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Email Verification OTP</h2>
            <p>Please use the following One-Time Password (OTP) to verify your email address. This OTP is valid for a limited time only.</p>
            <div class="otp-code">{otp}</div>
            <p>If you did not request this, please ignore this email.</p>
            <div class="footer">© 2025 QuizIt. All rights reserved.</div>
        </div>
    </body>
    </html>
    """
