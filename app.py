import streamlit as st
import pandas as pd
import program, helper
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from collections import Counter
import re
import emoji
from gtts import gTTS

# PDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="WhatsApp Chat Analysis", layout="wide")
st.sidebar.title("📊 WhatsApp Chat Analysis")

# ---------------- PDF FUNCTION ----------------
def generate_pdf(summary, stats, top_words, topic_df, emoji_freq):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    text = c.beginText(40, height - 40)
    text.setFont("Helvetica-Bold", 14)
    text.textLine("WhatsApp Chat Analysis Report")
    text.textLine("")

    text.setFont("Helvetica", 11)
    text.textLine("📊 Basic Statistics")
    text.textLine("-" * 40)
    for k, v in stats.items():
        text.textLine(f"{k}: {v}")

    text.textLine("")
    text.textLine("🧠 Topic Insights")
    text.textLine("-" * 40)
    for _, row in topic_df.iterrows():
        text.textLine(f"{row['Topic']}: {row['Mentions']} messages")

    text.textLine("")
    text.textLine("🔑 Most Common Words")
    text.textLine("-" * 40)
    text.textLine(", ".join(top_words))

    text.textLine("")
    text.textLine("😀 Top Emojis")
    text.textLine("-" * 40)
    for e, c_ in emoji_freq[:5]:
        text.textLine(f"{e} used {c_} times")

    text.textLine("")
    text.textLine("📝 Auto Generated Summary")
    text.textLine("-" * 40)
    for line in summary.split("\n"):
        text.textLine(line)

    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ---------------- VOICE FUNCTION ----------------
def generate_voice(text):
    tts = gTTS(text=text, lang="en")
    audio_bytes = io.BytesIO()
    tts.write_to_fp(audio_bytes)
    audio_bytes.seek(0)
    return audio_bytes

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.sidebar.file_uploader("Upload WhatsApp chat (.txt)")

if uploaded_file is not None:
    data = uploaded_file.read().decode("utf-8")
    df = program.preprocess(data)

    st.subheader("📄 Cleaned Chat Data")
    st.dataframe(df)

    user_list = df["user"].unique().tolist()
    if "System" in user_list:
        user_list.remove("System")
    user_list.sort()
    user_list.insert(0, "Overall")

    selected_user = st.sidebar.selectbox("Show analysis for", user_list)

    if st.sidebar.button("Show Analysis"):

        temp_df = df if selected_user == "Overall" else df[df["user"] == selected_user]

        # ---------------- BASIC STATS ----------------
        num_messages, num_words, media, links = helper.fetch_stats(selected_user, df)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Messages", num_messages)
        col2.metric("Words", num_words)
        col3.metric("Media", media)
        col4.metric("Links", links)

        # ---------------- BUSIEST USERS ----------------
        if selected_user == "Overall":
            st.subheader("🔥 Busiest Users")
            busiest = helper.find_busiest_user(df)

            col1, col2 = st.columns(2)
            with col1:
                fig, ax = plt.subplots()
                ax.bar(busiest.index, busiest.values)
                plt.xticks(rotation=45)
                st.pyplot(fig)

            with col2:
                for i in range(len(busiest)):
                    st.write(f"{busiest.index[i]} : {(busiest.values[i]/num_messages)*100:.2f}%")

        # ---------------- WORD CLOUD ----------------
        st.subheader("☁️ Word Cloud")

        stop_words = {
            "hai","ha","haan","to","the","is","am","are","was","were",
            "a","an","and","or","but","if","in","on","at","of","for",
            "me","my","you","your","i","we","he","she","they",
            "ka","ki","ke","ko","se","mai","main","bhai","bro",
            "nhi","nahi","yes","no","ok","this","that","it"
        }

        words = []
        for msg in temp_df["message_only"].dropna():
            msg = msg.lower()
            if "deleted" in msg or "http" in msg:
                continue
            msg = re.sub(r"[^a-zA-Z0-9\s]", " ", msg)
            for w in msg.split():
                if w not in stop_words and len(w) > 2 and not w.isdigit():
                    words.append(w)

        if words:
            wc = WordCloud(width=800, height=400, background_color="white").generate(" ".join(words))
            fig, ax = plt.subplots()
            ax.imshow(wc)
            ax.axis("off")
            st.pyplot(fig)

        # ---------------- TOP WORDS ----------------
        st.subheader("🔑 Top Words")
        common_words = Counter(words).most_common(20)
        st.dataframe(common_words)

        # ---------------- EMOJI ANALYSIS ----------------
        st.subheader("😀 Emoji Analysis")
        emojis = [ch for msg in temp_df["message_only"].dropna() for ch in msg if emoji.is_emoji(ch)]
        emoji_freq = Counter(emojis).most_common(10)
        st.dataframe(emoji_freq)

        # ---------------- BEST DAY ----------------
        st.subheader("📅 Best Day to Chat")
        df["day_name"] = df["date"].dt.day_name()
        day_activity = df.groupby("day_name").count()["message_only"]
        best_day = day_activity.idxmax()
        st.bar_chart(day_activity)
        st.success(f"Most chats happen on **{best_day}**.")

        # ---------------- HEATMAP ----------------
        st.subheader("🔥 Activity Heatmap (Day × Hour)")
        heatmap = df.pivot_table(
            index="day_name",
            columns="hour",
            values="message_only",
            aggfunc="count"
        ).fillna(0)
        st.dataframe(heatmap)

        # ---------------- LONGEST SILENCE ----------------
        st.subheader("🤐 Longest Silence")
        df_sorted = df.sort_values("date")
        gap = df_sorted["date"].diff().max()
        st.warning(f"Longest silence: **{gap}**")

        # ---------------- RESPONSE TIME ----------------
        st.subheader("⏱️ Average Response Time (minutes)")
        response = {}
        prev_user, prev_time = None, None

        for _, row in df_sorted.iterrows():
            if prev_user and row["user"] != prev_user:
                diff = (row["date"] - prev_time).total_seconds() / 60
                if diff < 1440:
                    response.setdefault(row["user"], []).append(diff)
            prev_user, prev_time = row["user"], row["date"]

        avg_response = {u: sum(t)/len(t) for u, t in response.items()}
        st.dataframe(pd.DataFrame(avg_response.items(), columns=["User", "Avg Response (min)"]))

        # ---------------- QUESTIONS ----------------
        st.subheader("❓ Questions vs Statements")
        q = temp_df["message_only"].str.contains(r"\?", na=False).sum()
        s = len(temp_df) - q
        st.metric("Questions", q)
        st.metric("Statements", s)

        # ---------------- TOPIC DETECTION ----------------
        st.subheader("🧠 Topic Detection")
        topics = {
            "Study": ["exam", "notes", "class"],
            "Coding": ["code", "python", "loop"],
            "Fun": ["lol", "😂", "🤣"],
            "Links": ["http", "www"]
        }

        topic_count = {k: 0 for k in topics}
        for msg in temp_df["message_only"].dropna().str.lower():
            for t, keys in topics.items():
                if any(k in msg for k in keys):
                    topic_count[t] += 1

        topic_df = pd.DataFrame(topic_count.items(), columns=["Topic", "Mentions"])
        st.bar_chart(topic_df.set_index("Topic"))

        # ---------------- AUTO SUMMARY ----------------
        st.subheader("🤖 Auto Chat Summary")

        top_topic = topic_df.sort_values("Mentions", ascending=False).iloc[0]["Topic"]
        top_words = [w[0] for w in common_words[:5]]
        most_active_user = df["user"].value_counts().idxmax()

        summary = (
            f"This WhatsApp chat is most active on {best_day}. "
            f"The dominant discussion topic is {top_topic}. "
            f"The most frequently used words include {', '.join(top_words)}. "
            f"{most_active_user} is the most active participant. "
            f"Overall, the chat shows healthy engagement with messages, media, and shared links."
        )

        st.success(summary)

        # ---------------- VOICE SUMMARY ----------------
        st.subheader("🔊 Voice Summary")
        audio_bytes = generate_voice(summary)
        st.audio(audio_bytes, format="audio/mp3")

        # ---------------- PDF DOWNLOAD ----------------
        st.subheader("📄 Download PDF Report")

        stats = {
            "Total Messages": num_messages,
            "Total Words": num_words,
            "Media Shared": media,
            "Links Shared": links,
            "Best Day": best_day,
            "Top Topic": top_topic
        }

        pdf = generate_pdf(summary, stats, top_words, topic_df, emoji_freq)

        st.download_button(
            "Download PDF Report",
            data=pdf,
            file_name="whatsapp_chat_report.pdf",
            mime="application/pdf"
        )

        # ---------------- CSV DOWNLOAD ----------------
        st.subheader("⬇️ Download CSV")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Cleaned CSV", csv, "chat_analysis.csv", "text/csv")
