#!/usr/bin/env python

import os.path
import re
import sys
from typing import Optional

import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from wordcloud import WordCloud
import numpy as np
import emoji
import regex
from nltk.corpus import stopwords as nltk_stopwords
import getopt


def __starts_with_date_and_time(s: str) -> bool:
    """checks if chat line contains the whats-app timestamp"""
    pattern = r"^\d{2}/\d{2}/\d{4}, \d{2}:\d{2} -"
    result = re.match(pattern, s)
    if result:
        return True
    return False


def __contains_author(s: str) -> bool:
    """checks if chat line contains an author"""
    patterns = [
        r"([\w]+):",
        r"([\w]+[\s]+[\w]+):",
        r"([\w]+[\s]+[\w]+[\s]+[\w]+):",
        r"([\w]+)[\u263a-\U0001f999]+:"
    ]
    pattern = "^" + "|".join(patterns)
    result = re.match(pattern, s)
    if result:
        return True
    return False


def __get_data_point(line: str) -> (str, str, str):
    """transforms chat line into date_time, author and message"""
    split_line = line.split(" - ")
    date_time = pd.to_datetime(split_line[0], format="%d/%m/%Y, %H:%M")
    message = " ".join(split_line[1:])
    if __contains_author(message):
        split_message = message.split(": ")
        author = split_message[0].replace(":", "")
        message = " ".join(split_message[1:])
    else:
        author = None
    return date_time, author, message


def __parse_chat(chat_path: str) -> pd.DataFrame:
    """read in chat history from file, parse it into (date_time, author, message) and create a DataFrame"""
    parsed_data = []

    with open(chat_path, encoding="utf-8") as input_file:
        input_file.readline()
        message_buffer = []
        date_time, author = None, None
        while True:
            line = input_file.readline()
            if not line:
                break
            line = line.strip()
            if __starts_with_date_and_time(line):
                if len(message_buffer) > 0 and not (
                        len(parsed_data) > 0 and parsed_data[-1][0] == date_time and parsed_data[-1][1] == author and
                        parsed_data[-1][2] == "<Media omitted>"):
                    parsed_data.append([date_time, author, " ".join(message_buffer)])
                message_buffer.clear()
                date_time, author, message = __get_data_point(line)
                if author:
                    message_buffer.append(message)
            else:
                message_buffer.append(line)

    data_frame = pd.DataFrame(parsed_data, columns=["date_time", "Author", "Message"])

    print(f"Parsed chat data from {chat_path}")
    return data_frame


def __setup_extra_columns(data_frame: pd.DataFrame):
    """add extra columns to the dataframe"""
    data_frame["date_time"] = pd.to_datetime(data_frame["date_time"])
    data_frame["Weekday"] = pd.Categorical(data_frame["date_time"].apply(lambda x: x.day_name()),
                                           categories=__get_weekdays(), ordered=True)
    data_frame["Month"] = data_frame["date_time"].apply(lambda x: x.month_name())
    data_frame["Date"] = [d.date() for d in data_frame["date_time"]]
    data_frame["Hour"] = [d.time().hour for d in data_frame["date_time"]]
    data_frame["Url count"] = data_frame.Message.apply(lambda x: re.findall(r"(https?://\S+)", x)).str.len()
    data_frame["Letter count"] = data_frame["Message"].apply(lambda s: len(s))
    data_frame["Word count"] = data_frame["Message"].apply(lambda s: len(s.split(" ")))
    data_frame["Emoji"] = data_frame["Message"].apply(__count_emojis)


def __count_emojis(text: str) -> list[str]:
    emoji_list = []
    data = regex.findall(r"\X", text)
    for word in data:
        if any(char in emoji.UNICODE_EMOJI for char in word):
            emoji_list.append(word)

    return emoji_list


def __remove_urls(text: str) -> str:
    url_pattern = re.compile(r"https?://\S+|www\.\S+")
    return url_pattern.sub(r"", text)


def __read_in_wordlist(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return f.read().split()


def __get_stopwords(language: str, banned_path: Optional[str]) -> set[str]:
    banned_words = list(nltk_stopwords.words(language))
    banned_words.extend(["Media", "omitted"])
    if banned_path:
        extra = __read_in_wordlist(banned_path)
        banned_words.extend(extra)
        print(f"Got list of banned words: {banned_path}")
    return set(banned_words)


def __get_weekdays() -> list[str]:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def __get_months() -> list[str]:
    return ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
            "November"]


def export_data(data_frame: pd.DataFrame, chat_name: str):
    export_file_name = f"chat_analysis_{chat_name}/export.csv"
    # noinspection PyTypeChecker
    data_frame.to_csv(export_file_name)
    print(f"Exported data to {export_file_name}", end=" ")


def plot_messages_by_date(data_frame: pd.DataFrame, chat_name: str):
    messages_by_date = data_frame.groupby("Date")["Message"].count()

    messages_by_date.plot(kind="line", figsize=(20, 10), lw="3", color="#003f5c", title="Messages by date")

    file_location = f"chat_analysis_{chat_name}/Messages_by_date.png"
    plt.savefig(file_location)
    plt.clf()
    print(f"Generated {file_location}", end=" ")


def plot_messages_by_weekday(data_frame: pd.DataFrame, chat_name: str):
    messages_by_weekday = (data_frame.set_index("Weekday")["Message"]
                           .groupby(level=0)
                           .value_counts()
                           .groupby(level=0)
                           .sum()
                           .reset_index(name="count"))
    messages_by_weekday.sort_values(by="Weekday")

    fig = px.line_polar(messages_by_weekday, r="count", theta="Weekday", line_close=True, width=2000, height=1000,
                        title="Messages by weekday")
    fig.update_traces(fill="toself")
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
            )),
        showlegend=False
    )

    filename = f"chat_analysis_{chat_name}/Messages_by_weekday.png"
    fig.write_image(filename)
    print(f"Generated {filename}", end=" ")


def plot_messages_by_hour(data_frame: pd.DataFrame, chat_name: str):
    messages_by_hour = (data_frame.set_index("Hour")["Message"]
                        .groupby(level=0)
                        .value_counts()
                        .groupby(level=0)
                        .sum()
                        .reset_index(name="count"))

    fig = px.bar(messages_by_hour, x="Hour", y="count",
                 labels={"hour": "24 Hour Period"},
                 height=1000, width=2000)
    fig.update_traces(marker_color="#003f5c",
                      marker_line_width=1.5)
    fig.update_layout(title_text="Messages by hour")

    filename = f"chat_analysis_{chat_name}/Messages_by_hour.png"
    fig.write_image(filename)
    print(f"Generated {filename}", end=" ")


def plot_messages_by_month_and_weekday(data_frame: pd.DataFrame, chat_name: str):
    messages_by_month_and_weekday = data_frame.groupby(["Month", "Weekday"])["Message"].value_counts().reset_index(
        name="count")

    pt = messages_by_month_and_weekday.pivot_table(index="Month", columns="Weekday", values="count").reindex(
        index=__get_months(), columns=__get_weekdays())
    fig = px.imshow(pt,
                    labels=dict(x="Day of Week", y="Months", color="Count"),
                    x=__get_weekdays(),
                    y=__get_months(),
                    title="Messages by weekday by month"
                    )
    fig.update_layout(
        width=2000, height=1000)

    filename = f"chat_analysis_{chat_name}/Messages_by_month_and_weekday.png"
    fig.write_image(filename)
    print(f"Generated {filename}", end=" ")


def get_basic_facts(data_frame: pd.DataFrame):
    total_messages = data_frame.shape[0]
    media_messages = data_frame[data_frame["Message"] == "<Media omitted>"].shape[0]
    average_message_words = data_frame["Word count"].mean()
    average_message_letters = data_frame["Letter count"].mean()
    average_message_day = data_frame.groupby("Date")["Message"].count().mean()

    print(f"\nTotal Messages:              {total_messages}")
    print(f"Media Message:               {media_messages}")
    print(f"Average Words by Messages:   {round(average_message_words)}")
    print(f"Average Letters by Messages: {round(average_message_letters)}")
    print(f"Average Message Per Day:     {round(average_message_day)}")


def plot_messages_by_author(data_frame: pd.DataFrame, chat_name: str):
    messages_by_author = data_frame["Author"].value_counts()

    messages_by_author.plot(kind="barh", figsize=(20, 10), title="Messages by author",
                            color=["#ffa600", "#ff764a", "#ef5675", "#bc5090", "#7a5195", "#374c80", "#003f5c"])

    filename = f"chat_analysis_{chat_name}/Messages_by_author.png"
    plt.savefig(filename)
    plt.clf()
    print(f"Generated {filename}", end=" ")


def __get_alias_dict(names: list[str]) -> dict[str, list[str]]:
    d = {}
    for name in names:
        name_variations = name.split()
        name_variations.extend(name.lower().split())
        name_variations.extend([name, name.lower()])
        d[name] = name_variations
    return d


def plot_mentions_by_name(data_frame: pd.DataFrame, chat_name: str):
    mentions = []
    names = data_frame["Author"].unique().tolist()
    alias_dict = __get_alias_dict(names)
    for name in alias_dict:
        try:
            mentions.append([name, data_frame["Message"].str.contains(
                '|'.join(alias_dict[name])).value_counts().loc[True]])
        except KeyError:
            continue
    mentions_by_name = pd.DataFrame(mentions, columns=["Name", "Number of mentions"]).sort_values(
        by="Number of mentions",
        ascending=False)

    mentions_by_name.plot(kind="barh", x="Name", y="Number of mentions", figsize=(20, 10), title="Mentions by name",
                          color=["#ffa600", "#ff764a", "#ef5675", "#bc5090", "#7a5195", "#374c80", "#003f5c"],
                          legend=False)

    filename = f"chat_analysis_{chat_name}/Mentions_by_name.png"
    plt.savefig(filename)
    plt.clf()
    print(f"Generated {filename}", end=" ")


def plot_media_sent_by_author(data_frame: pd.DataFrame, chat_name: str):
    media_sent_by_author = data_frame[(data_frame["Message"] == "<Media omitted>")]["Author"].value_counts()

    media_sent_by_author.plot(kind="barh",
                              figsize=(20, 10),
                              title="Media sent by author",
                              color=["#ffa600", "#ff764a", "#ef5675", "#bc5090", "#7a5195", "#374c80", "#003f5c"])

    filename = f"chat_analysis_{chat_name}/Media_sent_by_author.png"
    plt.savefig(filename)
    plt.clf()
    print(f"Generated {filename}", end=" ")


def __plot_cloud(wordcloud: WordCloud, chat_name: str):
    plt.figure(figsize=(40, 30))
    plt.imshow(wordcloud)
    plt.axis("off")

    filename = f"chat_analysis_{chat_name}/Word_cloud.png"
    plt.savefig(filename)
    print(f"Generated {filename}", end=" ")


def plot_word_cloud(data_frame: pd.DataFrame, chat_name, language: str, banned_words=None):
    chat_word_cloud = data_frame[["Message"]].copy()
    chat_word_cloud["Message"] = chat_word_cloud["Message"].apply(__remove_urls)
    chat_word_cloud["Message"] = chat_word_cloud["Message"].replace("nan", np.NaN)
    chat_word_cloud["Message"] = chat_word_cloud["Message"].replace("", np.NaN)
    text = " ".join(review for review in chat_word_cloud.Message.dropna())
    wordcloud = WordCloud(width=3000, height=2000, random_state=1,
                          background_color="black", colormap="Set2", collocations=False,
                          stopwords=__get_stopwords(language, banned_words)).generate(text)

    __plot_cloud(wordcloud, chat_name)


def plot_message_length_by_author(data_frame: pd.DataFrame, chat_name: str):
    message_length_by_author = data_frame.groupby("Author")["Word count"].mean().sort_values(ascending=False)

    message_length_by_author.plot(kind="barh",
                                  figsize=(20, 10),
                                  title="Message length by author",
                                  color=["#ffa600", "#ff764a", "#ef5675", "#bc5090", "#7a5195", "#374c80", "#003f5c"])
    filename = f"chat_analysis_{chat_name}/Message_length_by_author.png"
    plt.savefig(filename)
    plt.clf()
    print(f"Generated {filename}", end=" ")


def do_analysis(chat_path: str, chat_name: str, language: str, banned_words=None, selected_jobs=None):
    print(f"Processing chat {chat_name}")
    print(f"Chat language: {language}")

    if not os.path.exists(f"chat_analysis_{chat_name}"):
        os.mkdir(f"chat_analysis_{chat_name}")

    chat = __parse_chat(chat_path)
    __setup_extra_columns(chat)
    get_basic_facts(chat)

    available_jobs = {
        0: (plot_messages_by_author, [chat, chat_name]),
        1: (plot_media_sent_by_author, [chat, chat_name]),
        2: (plot_messages_by_date, [chat, chat_name]),
        3: (plot_messages_by_hour, [chat, chat_name]),
        4: (plot_messages_by_month_and_weekday, [chat, chat_name]),
        5: (plot_word_cloud, [chat, chat_name, language, banned_words]),
        6: (plot_messages_by_weekday, [chat, chat_name]),
        7: (plot_mentions_by_name, [chat, chat_name]),
        8: (plot_message_length_by_author, [chat, chat_name]),
        9: (export_data, [chat, chat_name])
    }
    if selected_jobs:
        selected_jobs = [int(j) for j in selected_jobs.split()]
    else:
        selected_jobs = available_jobs.keys()
    jobs = [available_jobs[job_id] for job_id in available_jobs.keys() if job_id in selected_jobs]

    print(f"\nStarting {len(jobs)} analysis jobs {selected_jobs} ...")
    for i, job in enumerate(jobs):
        job[0](*job[1])
        print(f"({i + 1}/{len(jobs)})")


def call_script():
    err_mssg = "Usage: python analyze.py --input <path> [--name <chat name>] [--lang <language>] [--bannedwords " \
               "<path>] [--jobs \"job-id1 job-id2 job-id3\"]"

    input_name = None
    input_path = None
    language = None
    banned_words = None
    jobs = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["input=", "name=", "lang=", "bannedwords=", "jobs="])
    except getopt.GetoptError:
        print(err_mssg)
        sys.exit(1)

    for opt, arg in opts:
        if opt == '-h':
            print(err_mssg)
            sys.exit()
        elif opt == "--input":
            input_path = arg
        elif opt == "--name":
            input_name = arg
        elif opt == "--lang":
            language = arg
        elif opt == "--bannedwords":
            banned_words = arg
        elif opt == "--jobs":
            jobs = arg

    if not language:
        language = "english"

    if not jobs:
        jobs = "0 1 2 3 4 5 6 7 8 9"

    if not input_path:
        print(err_mssg)
        sys.exit(1)

    if not os.path.exists(input_path):
        print(err_mssg)
        sys.exit(1)

    if not input_name:
        input_name = input_path.split("/")[-1]
        if len(input_name.split(".")) > 1:
            input_name = input_name.split(".")[-2]

    return input_path, input_name, language, banned_words, jobs


params = call_script()
if params:
    do_analysis(*params)
