from dotenv import load_dotenv
import os

load_dotenv()

QUIZIT_URL = os.getenv("QUIZIT_URL")


def invite_message(invitor_name: str, room_code: str, quiz_id: str):
    email_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <style>
            body {{
                background-color: #121212;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #dddddd;
                padding: 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 600px;
                margin: auto;
                background-color: #1e1e1e;
                padding: 32px 28px;
                border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.8);
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #3aaf7c;
                padding-bottom: 16px;
            }}
            .header h2 {{
                color: #3aaf7c;
                font-size: 24px;
                margin: 0;
            }}
            .content {{
                margin-top: 24px;
                color: #cccccc;
                font-size: 15px;
            }}
            .content p {{
                margin: 16px 0;
            }}
            .room-code {{
                background-color: #2b2b2b;
                padding: 14px 0;
                font-size: 20px;
                font-weight: bold;
                text-align: center;
                border-radius: 8px;
                margin: 24px 0;
                color: #9afac4;
                font-family: monospace;
                user-select: all;
                letter-spacing: 3px;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #3aaf7c, #2d8668);
                color: #fff !important;
                padding: 12px 30px;
                border-radius: 30px;
                text-decoration: none;
                font-weight: bold;
                font-size: 16px;
                box-shadow: 0 4px 10px rgba(58, 175, 124, 0.4);
                transition: background 0.3s ease;
            }}
            .button:hover {{
                background: linear-gradient(135deg, #2d8668, #3aaf7c);
            }}
            .footer {{
                margin-top: 40px;
                text-align: center;
                font-size: 13px;
                color: #888888;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>You're Invited to Join QuizIt</h2>
            </div>
            <div class="content">
                <p>Hi there,</p>
                <p><strong>{invitor_name}</strong> has invited you to a live quiz match on <strong>QuizIt</strong>.</p>
                <div class="room-code">{room_code}</div>
                <p>Use this code to enter the room and compete with your friends!</p>
                <p style="text-align: center;">
                    <a href="{QUIZIT_URL}/quiz/{quiz_id}/waiting?roomCode={room_code}" class="button">Join Room</a>
                </p>
                <p>Enjoy and good luck!</p>
            </div>
            <div class="footer">
                – The QuizIt Team<br>
            </div>
        </div>
    </body>
    </html>
    """
    return email_body
