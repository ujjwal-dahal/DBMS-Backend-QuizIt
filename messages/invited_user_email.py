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
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            /* Reset & base */
            body {{
                margin: 0;
                background-color: #121212;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #f0f0f0;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
                line-height: 1.5;
            }}
            a {{
                color: #3aaf7c;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}

            .container {{
                max-width: 600px;
                background-color: #1e1e1e;
                margin: 40px auto;
                padding: 32px 30px;
                border-radius: 12px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.9);
                border: 1px solid #2c2c2c;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #3aaf7c;
                padding-bottom: 18px;
                margin-bottom: 28px;
            }}
            .header h2 {{
                margin: 0;
                font-weight: 700;
                font-size: 26px;
                color: #3aaf7c;
                letter-spacing: 0.03em;
            }}

            .content p {{
                margin: 16px 0;
                font-size: 16px;
                color: #ddd;
            }}

            .room-code {{
                background-color: #272727;
                border: 1.5px solid #3aaf7c;
                padding: 14px 24px;
                font-size: 22px;
                font-weight: 700;
                text-align: center;
                border-radius: 10px;
                margin: 30px 0;
                color: #9afac4;
                font-family: 'Courier New', Courier, monospace;
                user-select: all;
                letter-spacing: 3px;
                box-shadow: 0 0 6px #3aaf7c88;
            }}

            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #3aaf7c, #2d8668);
                color: white !important;
                padding: 14px 36px;
                border-radius: 30px;
                font-weight: 700;
                font-size: 17px;
                box-shadow: 0 6px 14px rgba(58, 175, 124, 0.55);
                transition: background 0.3s ease;
                cursor: pointer;
                text-align: center;
                margin: 0 auto;
            }}
            .button:hover {{
                background: linear-gradient(135deg, #2d8668, #3aaf7c);
            }}

            .footer {{
                margin-top: 48px;
                text-align: center;
                font-size: 13px;
                color: #777;
                font-style: italic;
                letter-spacing: 0.02em;
            }}

            /* Responsive */
            @media screen and (max-width: 640px) {{
                .container {{
                    margin: 20px 12px;
                    padding: 24px 20px;
                }}
                .room-code {{
                    font-size: 18px;
                    padding: 12px 18px;
                }}
                .button {{
                    font-size: 15px;
                    padding: 12px 28px;
                }}
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
                <div class="room-code" title="Room Code">{room_code}</div>
                <p>Use this code to enter the room and compete with your friends!</p>
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{QUIZIT_URL}/quiz/{quiz_id}/waiting?roomCode={room_code}" class="button" target="_blank" rel="noopener noreferrer">Join Room</a>
                </p>
                <p>Enjoy and good luck!</p>
            </div>
            <div class="footer">
                &mdash; The QuizIt Team
            </div>
        </div>
    </body>
    </html>
    """
    return email_body
