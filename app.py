# app.pyコピー（ユーザー別ワークシート　実装用）


# 環境変数読み込み準備
import os
from dotenv import load_dotenv
from linebot.models.events import FollowEvent
load_dotenv()

# Googleスプレッドシート部分
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from googletrans import Translator
translator = Translator()

sp_list = []
lang_dict = {
    "ja": "日本語",
    "en": "English",
    "es": "Español",
    "ca": "Català",
    "it": "Italiano",
    "pt": "Português",
    'fr': 'Français',
}

langs = ['日本語', '英語', 'スペイン語', 'カタルーニャ語', 'イタリア語', 'ポルトガル語', 'フランス語']

class GSSWorksheet():
    def __init__(self, title):
        SP_CREDENTIAL_FILE = {
            "type": "service_account",
            "project_id": os.environ['SHEET_PROJECT_ID'],
            "private_key_id": os.environ['SHEET_PRIVATE_KEY_ID'],
            "private_key": os.environ['SHEET_PRIVATE_KEY'].replace('\\n', '\n'),
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

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(SP_CREDENTIAL_FILE, SP_SCOPE)    # 認証情報すり合わせ
        
        global gc
        gc = gspread.authorize(credentials)

        # ここから要確認！！-------------------------------------------------------------------
        gc = gc.open("LANG")#操作するスプレッドシートを指定する

        try :
            #新たにワークシートを作成し、Worksheetオブジェクトをworksheetに格納します。
            worksheet = gc.add_worksheet(title=title, rows="100", cols="7")
        except :
            #すでにワークシートが存在しているときは、そのワークシートのWorksheetオブジェクトを格納します。
            worksheet = gc.worksheet(title)

        self.worksheet = worksheet #worksheetをメンバに格納
        self.JA = 1 #書き込む行を指定しているメンバ
        self.EN = 2 
        self.ES = 3 
        self.CA = 4 
        self.IT = 5 
        self.PT = 6 
        self.FR = 7
        # Worksheetオブジェクト.update_cell(行番号, 列番号, "テキスト")で指定したセルにテキストを書き込む
        self.worksheet.update_cell(1, self.JA, "日本語")
        self.worksheet.update_cell(1, self.EN, "English")
        self.worksheet.update_cell(1, self.ES, "Español")
        self.worksheet.update_cell(1, self.CA, "Català")
        self.worksheet.update_cell(1, self.IT, "Italiano")
        self.worksheet.update_cell(1, self.PT, "Português")                
        self.worksheet.update_cell(1, self.FR, "Français")

    def last_row(self):
        row_count = 1
        while self.worksheet.cell(row_count, self.JA).value != "":
            row_count += 1
        return row_count

    def delete_worksheet(self):
        gc.del_worksheet(self.worksheet)

    def input_to_sheet(self, list):
        # cell_list = self.worksheet.range(self.last_row(), 1, self.last_row(), 7)
        # for i,j in enumerate(list):
        #     cell_list[i + 1].value = j
        # self.worksheet.update_cells(cell_list)
        self.worksheet.append(list)
        return self.worksheet
        # self.worksheet.update_cell(self.last_row(), self.JA, )



    # 翻訳部分
    sp_list = []

    def trans(self, text):
        # detected = translator.detect(text)  # 何語のテキストか判定
        # print(f"{lang_dict[detected.lang].title()}: {text}\n--------------------")
        trans_list = []
        sp_list = []        # Spread sheet用の言語リスト

        # 一言語ずつ取り出して、翻訳する
        for lang, language in lang_dict.items():
            translated = translator.translate(text, dest=lang)  # 翻訳する
            trans_list.append(f"{language.title()}:  {translated.text}")
            sp_list.append(translated.text)
        trans_list = "\n\n".join(trans_list)
        print(sp_list)

        # 翻訳結果をスプレッドシートに入力する
        self.input_to_sheet(sp_list)
        # df = pd.DataFrame(self.worksheet.get_all_records())
        # df = df.append({'日本語': sp_list[0], 'English': sp_list[1], 'Español': sp_list[2], 'Català': sp_list[3], 'Italiano': sp_list[4], 'Português': sp_list[5], 'Français': sp_list[6]}, ignore_index=True)
        # self.worksheet.update([df.columns.values.tolist()] + df.values.tolist())

        return trans_list

    # テキストが言語名であれば、クイズを出す
    def quiz(self, text):
        col = langs.index(text) + 1 # 指定した言語列
        quiz_lang = self.worksheet.col_values(col)

        import random
        quiz_list = random.sample(quiz_lang[1:], 3)
        quiz = []
        for i, q in enumerate(quiz_list):
            quiz.append(f'{i+1}. {q}')
        quiz = "\n".join(quiz)

        return quiz


worksheets = {}  # 辞書の初期化(ユーザー固有のワークシートを格納するため)

# LINE Messaging API部分
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
    profile = line_bot_api.get_profile(event.source.user_id)

    try:
        # ユーザーからテキストメッセージが送信されるたび、そのユーザーidに対応するWorksheetオブジェクトをworksheetに格納する
        worksheet = worksheets[profile.user_id]
    except KeyError:
        # 辞書にインスタンスが登録されていなければ、もう一度登録する
        worksheets[profile.user_id] = GSSWorksheet(profile.display_name)
        worksheet = worksheets[profile.user_id]
    
    line_bot_api.reply_message(
        event.reply_token,  # イベントの応答に用いるトークン
        TextSendMessage(text="{text}\n\n")    
    )

    # 指定された言語の復習クイズを出す
    if text in langs:
        review_quiz = worksheet.quiz(text)

        line_bot_api.reply_message(
            event.reply_token,  # イベントの応答に用いるトークン
            TextSendMessage(text=f'{text}の復習です！！\n\n{review_quiz}')    
        )
    else:
        cell = worksheet.find(text) # すでにスプレッドシートにあるか確認
        if cell:
            result = worksheet.row_values(cell.row) # スプレッドシートにあれば、その行を取り出し
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
            translated = worksheet.trans(text)  # trans()では、スプレッドシートへの書き込みも行う

            line_bot_api.reply_message(
                event.reply_token,  # イベントの応答に用いるトークン
                TextSendMessage(text=translated)    
            )


@handler.add(FollowEvent)
def handle_follow(event):
    profile = line_bot_api.get_profile(event.source.user_id)

    # 友達登録時に、新しいworksheetのインスタンスを生成し、辞書に格納する
    worksheets[profile.user_id] = GSSWorksheet(profile.display_name)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='友達追加ありがとうございます！！\n\n日本語、英語、スペイン語、カタルーニャ語、イタリア語、ポルトガル語、フランス語の相互翻訳ができます。\n\知りたい言葉を入力して、送信してください。７ヶ国語それぞれで返信がきます。\n\nまた、調べた言葉は、あなた専用のスプレッドシートに入力されます。\n\nさらに、スプレッドシートを元に復習ができます。日本語で、言語名を送信してください。\n例えば、「英語」と入力すれば、ランダムで3つ調べた英語の単語が返信されます。\n\n語学の勉強にお役立てください！！')
    )

if __name__ == "__main__":
    port = os.getenv("PORT")    # Heroku上にある環境変数
    app.run(host="0.0.0.0", port=port)



"""

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
        "private_key": os.environ['SHEET_PRIVATE_KEY'].replace('\\n', '\n'),
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
        "ja": "日本語",
        "en": "English",
        "es": "Español",
        "ca": "Català",
        "it": "Italiano",
        "pt": "Português",
        'fr': 'Français',
    }

    # detected = translator.detect(text)  # 何語のテキストか判定
    # print(f"{lang_dict[detected.lang].title()}: {text}\n--------------------")
    trans_list = []
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
    df = df.append({'日本語': sp_list[0], '英語': sp_list[1], 'スペイン語': sp_list[2], 'カタルーニャ語': sp_list[3], 'イタリア語': sp_list[4], 'ポルトガル語': sp_list[5], 'フランス語': sp_list[6]}, ignore_index=True)
    worksheet.update([df.columns.values.tolist()]+df.values.tolist())

    return trans_list

langs = ['日本語', '英語', 'スペイン語', 'カタルーニャ語', 'イタリア語', 'ポルトガル語', 'フランス語']

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
    # if cell:
    #     print(f'値:{cell.value}、列のindex:{cell.col}、行のindex:{cell.row}')
    # else:
    #     print('すでに翻訳したことがあります。')

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
    port = os.getenv("PORT")    # Heroku上にある環境変数
    app.run(host="0.0.0.0", port=port)

"""