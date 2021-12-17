# WhatsApp Chat Analysis

*Inspired by [this Medium post](https://medium.com/mcd-unison/whatsapp-group-chat-analysis-with-python-3f5196280ba) by
Luis.*

<p align="center">
 <img src="https://github.com/YannickSpoerl/whatsapp-chat-analysis/blob/main/example.gif" alt="Example" width="800">
</p>

Analyses a WhatsApp chat (private or group) and creates various beautiful graphs about

- Number of messages sent by Author
- Number of images sent by Author
- Number of messages overtime
- Number of messages by hour
- Number of messages per weekday
- Number of messages per month and weekday
- Average message length by author
- Number of mentions by author
- Word cloud of most used words

## Usage

Within WhatsApp:

- Open chat
- Click on three dots in upper right corner
- Select "More"
- Select "Export chat"
- Select "Without media"
- Safe file to desired location

Install dependencies
`pip install -r ./requirements.txt`

Call script with
`python analyze.py --input my_saved_chat.txt`

## Options

`python analyze.py --input <path> [--name <chat name>] [--lang <language>] [--bannedwords <path>]`

- **-i, --input**: Specifies path to the input-file, **required**
- **-n, --name**: Specifies a custom name for chat, default will be filename, **optional**
- **-l, --lang**: Specifies chat language to filter words, default is "english", **optional**
- **-b, --bannedwords**: Path to custom list of banned words to filter out, **optional**
