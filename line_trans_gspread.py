# 開発環境用

# 環境変数読み込み準備
import os
from dotenv import load_dotenv
load_dotenv()

# Googleスプレッドシート部分
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def auth(): 
    SP_CREDENTIAL_FILE = {
        "type": "service_account",
        "project_id": os.environ['SHEET_PROJECT_ID'],
        "private_key_id": os.environ['SHEET_PRIVATE_KEY_ID'],
        "private_key": os.environ['SHEET_PRIVATE_KEY'],
        "client_email": os.environ['SHEET_CLIENT_EMAIL'],
        "client_id": os.environ['SHEET_CLIENT_ID'],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url":  os.environ['SHEET_CLIENT_X509_CERT_URL']
    }

    # APIを使用する範囲の指定
    SP_SCOPE = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    SP_SHEET_KEY = '1E6YfUx7IBmoCZYml94OVdwnoZzMVKGroSArptnta_D0'   # スプレッドシートのURL(~d/.../edit~の"..."部分)
    SP_SHEET = 'sheet1'  # 記入するシート名

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(SP_CREDENTIAL_FILE, SP_SCOPE)    # 認証情報すり合わせ
    gc = gspread.authorize(credentials)
    worksheet = gc.open_by_key(SP_SHEET_KEY).worksheet(SP_SHEET)    # SP_SHEET_KEYのSP_SHEETの情報を開いて、データを持ってくる

    return worksheet


# 翻訳部分
from googletrans import Translator
translator = Translator()

sp_list = []

def trans(text):
    lang_dict = {
        "ja": "japanese",
        "en": "english",
        "es": "spanish",
        "ca": "catalan",
        "it": "italian",
        "pt": "portuguese",
    }
    # detected = translator.detect(text)  # 何語のテキストか判定
    # print(f"{lang_dict[detected.lang].title()}: {text}\n--------------------")
    trans_list = []     # Line返信用
    sp_list = []        # Spread sheet用の言語リスト

    # 一言語ずつ取り出して、翻訳する
    for lang, language in lang_dict.items():
        translated = translator.translate(text, dest=lang)  # 翻訳する
        trans_list.append(f"{language.title()}:  {translated.text}")
        sp_list.append(translated.text)
    trans_list = "\n\n".join(trans_list)

    # 翻訳結果をスプレッドシートに入力する
    worksheet = auth()
    df = pd.DataFrame(worksheet.get_all_records())
    df = df.append({'日本語': sp_list[0], '英語': sp_list[1], 'スペイン語': sp_list[2], 'カタルーニャ語': sp_list[3], 'イタリア語': sp_list[4], 'ポルトガル語': sp_list[5], }, ignore_index=True)
    worksheet.update([df.columns.values.tolist()]+df.values.tolist())

    return trans_list


langs = ['日本語', '英語', 'スペイン語', 'カタルーニャ語', 'イタリア語', 'ポルトガル語', ]
# テキストが言語名であれば、クイズを出す
def quiz(text):

    col = langs.index(text) + 1 # 指定した言語列
    worksheet = auth()
    quiz_lang = worksheet.col_values(col)

    import random
    quiz_list = random.sample(quiz_lang[1:], 3)
    quiz = []
    for i, q in enumerate(quiz_list):
        quiz.append(f'{i+1}. {q}')
    quiz = "\n".join(quiz)

    return quiz

# LINE Messaging API部分
# Flaskでの実装
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
handler = WebhookHandler(CHANNEL_SECRET)


@app.route("/")
def hello_world():
    a = "hello world"
    return a

# Webhookからのリクエストをチェックする
@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーから署名検証のための値を取得
    signature = request.headers['X-Line-Signature']

    # リクエストボディを取得する
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    # 署名を検証し、問題なければhandleに定義されている関数を呼び出す
    try:
        handler.handle(body, signature)
    # 署名検証で失敗した場合、例外を出す
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    # handleの処理を終えればOK
    return "OK"

# LINEのメッセージの取得と返信内容の設定（おうむ返し）
# LINEでMessageEvent(普通のメッセージを送信された場合)が起こった場合、以下の関数を実行する
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text

    worksheet = auth()
    cell = worksheet.find(text)
    if cell:
        print(f'値:{cell.value}、列のindex:{cell.col}、行のindex:{cell.row}')
    else:
        print('すでに翻訳したことがあります。')

    # 指定された言語の復習クイズを出す
    if text in langs:
        preview_quiz = quiz(text)

        line_bot_api.reply_message(
            event.reply_token,  # イベントの応答に用いるトークン
            TextSendMessage(text=f'{text}の復習です！！\n\n{preview_quiz}')    
        )
    else:

        worksheet = auth()
        cell = worksheet.find(text) # すでにスプレッドシートにあるか確認
        if cell:
            result = worksheet.row_values(cell.row)
            translated = []
            for i,j in enumerate(result):
                translated.append(f"{langs[i]}: {j}")
            translated = "\n\n".join(translated)

            line_bot_api.reply_message(
                event.reply_token,  # イベントの応答に用いるトークン
                TextSendMessage(text=f'前にも調べていますよー。\n\n{translated}')    
            )

        else:
            # 翻訳したものを返す
            translated = trans(text)

            line_bot_api.reply_message(
                event.reply_token,  # イベントの応答に用いるトークン
                TextSendMessage(text=translated)    
            )



if __name__ == "__main__":
    app.run()


