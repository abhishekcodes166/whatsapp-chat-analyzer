import pandas as pd
import re
from urlextract import URLExtract

def preprocess(data):
    """
    WhatsApp format supported:
    [19/08/23, 7:53:34 PM] User: Message
    """

    # ---------- CORRECT REGEX PATTERN ----------
    pattern = r"\[(\d{1,2}/\d{1,2}/\d{2}),\s(\d{1,2}:\d{2}:\d{2}\s(?:AM|PM))\]"

    # split data
    messages = re.split(pattern, data)[1:]

    dates = []
    texts = []

    # messages list format:
    # [date, time, text, date, time, text, ...]
    for i in range(0, len(messages), 3):
        date_part = messages[i]
        time_part = messages[i + 1]
        msg_part  = messages[i + 2]

        dates.append(date_part + " " + time_part)
        texts.append(msg_part.strip())

    df = pd.DataFrame({
        "date": dates,
        "message": texts
    })

    # ---------- SAFE DATETIME PARSING ----------
    df["date"] = pd.to_datetime(
        df["date"],
        format="%d/%m/%y %I:%M:%S %p",
        errors="coerce"
    )

    # ---------- USER & MESSAGE SPLIT ----------
    users = []
    messages_only = []

    for msg in df["message"]:
        if ": " in msg:
            user, message = msg.split(": ", 1)
            users.append(user.strip())
            messages_only.append(message.strip())
        else:
            users.append("System")
            messages_only.append(msg.strip())

    df["user"] = users
    df["message_only"] = messages_only

    df.drop(columns=["message"], inplace=True)

    # ---------- TIME FEATURES ----------
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month_name()
    df["month_num"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["hour"] = df["date"].dt.hour
    df["minute"] = df["date"].dt.minute

    return df
