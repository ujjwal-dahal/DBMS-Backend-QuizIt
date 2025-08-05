def reset_password_email_body(token: str):
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
                color: #ef9a9a;
                margin-bottom: 20px;
                font-weight: 700;
            }}
            p {{
                font-size: 16px;
                line-height: 1.5;
                margin-bottom: 30px;
                color: #cccccc;
            }}
            .token-code {{
                font-size: 36px;
                font-weight: 700;
                letter-spacing: 10px;
                background-color: #4a2c2c;
                padding: 15px 0;
                border-radius: 8px;
                color: #f48fb1;
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
            <h2>Password Reset Token</h2>
            <p>Please use the following token to reset your password. This token is valid for a limited time only.</p>
            <div class="token-code">{token}</div>
            <p>If you did not request a password reset, you can safely ignore this email.</p>
            <div class="footer">© 2025 QuizIt. All rights reserved.</div>
        </div>
    </body>
    </html>
    """
