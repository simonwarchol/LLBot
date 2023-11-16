import datetime
import json
import pandas as pd
import random
import urllib3
from io import StringIO

# Reads from `.env file`
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright
import dataframe_image as dfi
import openai


config = dotenv_values("/Users/swarchol/Research/LLBot/.env")
print("config", config)

openai.api_key = config["OPENAI_API_KEY"]



player_list_imessage = {
    "Simon": {"id": "55444"},
    "Nick": {"id": "58714"},
    "Jake": {"id": "56189"},
    "Rob": {"id": "64659"},
    "Katter": {"id": "58619"},
    "CC": {"id": "64157"},
    "Katie": {"id": "53779"},
    "Cat": {"id": "71256"},
    "Yasmina": {"id": "72221"},
    "Kate": {"id": "68591"},
    "Luke": {"id": "68635"},
    "Sagar": {"id": "74612"},
    "Scott": {"id": "74615"},
    "Julia": {"id": "71455"},
    "Enshu": {"id": "82484"},
}
player_list_sms = {
    "Simon": {"id": "55444"},
    "Sagar": {"id": "74612"},
    "Scott": {"id": "74615"},
    "Matt": {"id": "77804"},
    "Jordan": {"id": "77500"},
    "Kevin": {"id": "77498"},
    "Michael": {"id": "77503"},
}

recipients_imessage = {
    "name": config["CHAT_NAME_IMESSAGE"],
    "handle": config["CHAT_ID_IMESSAGE"],
}
recipients_sms = {
    "name": config["CHAT_NAME_SMS"],
    "handle": config["CHAT_ID_SMS"],
}


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


def get_scores(player_list):
    todays_scores = []
    question_results = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.learnedleague.com/")
        page.fill('#sidebar input[name="username"]', config["LL_USERNAME"])
        page.fill('#sidebar input[name="password"]', config["LL_PW"])
        page.click('#sidebar input[type="submit"]')
        for player, id_dict in player_list.items():
            player_id = id_dict["id"]
            page.goto(
                "https://www.learnedleague.com/profiles.php?{id}".format(id=player_id)
            )
            username = str(page.inner_html(".namecss"))
            result_string = username
            rundle_string = page.inner_html(".std-left-key a")
            rundle_string = " ".join(rundle_string.split()[0:2])
            scores = page.inner_html("div.fl_latest.fl_l_r.plresults")
            page.eval_on_selector_all(
                "div.fl_latest.fl_l_r.plresults a[href^='/wiki/']",
                "elements => elements.map(element => element.href)",
            )
            match_link = page.eval_on_selector_all(
                "div.fl_latest.fl_l_r.plresults a[href^='/match.php?id=']",
                "elements => elements.map(element => element.href)",
            )[-1]
            match_day_link = page.eval_on_selector_all(
                "div.fl_latest.fl_l_r.plresults a[href^='/match.php?']",
                "elements => elements.map(element => element.href)",
            )[-2]
            title = page.title()
            username = remove_prefix(title, "LL Profile: ")
            dfs = pd.read_html(StringIO(scores))
            if dfs and len(dfs) > 0:
                df = dfs[0].dropna()
                score = df.iloc[-1, :]["Result.1"]
                record = df.iloc[-1, :]["Result"]
                opponent = df.iloc[-1, :]["Opponent"]

                # result_string += ': ' + str(record) + ' ' + str(score) + ' ' + str(rundle_string)
                todays_scores.append(
                    {
                        "user": username,
                        "score": score,
                        "record": record,
                        "opponent": opponent,
                        "rundle": rundle_string,
                    }
                )
            page.goto(match_link)
            if question_results is None:
                question_results = []
                day_table = page.inner_html("table.QTable")
                day_table_df = pd.read_html(StringIO("<table>" + day_table + "</table>"))
                if day_table_df and len(day_table_df) > 0:
                    day_table_df = day_table_df[0].dropna()
                    for i in range(6):
                        question = str(day_table_df.iloc[i, 1]).replace("\xa0", " ")
                        question_results.append(
                            {"question": question, "smart": [], "dumb": []}
                        )

            results_rows = page.query_selector_all("table.std.tbltop_inner tbody tr")
            user_row = None
            for row in results_rows:
                if username in row.inner_html():
                    user_row = row
                    break
            classes = row.eval_on_selector_all(
                "td", "elements => elements.map(element => element.className)"
            )[1:7]
            correct_questions = [e == "c1" for e in classes]
            for i, correct in enumerate(correct_questions):
                if correct:
                    question_results[i]["smart"].append(username)
                else:
                    question_results[i]["dumb"].append(username)
            question_text = ""
            for q in question_results:
                if len(q["smart"]) == 1:
                    who = q["smart"][0]
                    question_text += (
                        "Only " + who + " got: " + q["question"] + " -- WOW!\n"
                    )

                if len(q["dumb"]) == 1:
                    who = q["dumb"][0]
                    question_text += (
                        "Only " + who + " missed: " + q["question"] + " -- WOW!\n"
                    )

        users = {item["user"] for item in todays_scores}
        head_to_head_string = ""
        h2h_users = set()
        for item in todays_scores:
            opponent = item["opponent"]
            if opponent in users and opponent not in h2h_users:
                # Find the opponent's record against the current user
                for opp_item in todays_scores:
                    if (
                        opp_item["user"] == opponent
                        and opp_item["opponent"] == item["user"]
                    ):
                        if item["record"] == "W":
                            head_to_head_string += f"{item['user']} won against {opponent}, {item['score']}\n"
                            h2h_users.add(item["user"])
                            h2h_users.add(opponent)
                        elif item["record"] == "T":
                            head_to_head_string += f"{item['user']} and {opponent} tied,  {item['score']}\n"
                            h2h_users.add(item["user"])
                            h2h_users.add(opponent)

        todays_scores.sort(key=lambda x: x["user"])
        # # "user": username,
        #                     "score": score,
        #                     "record": record,
        #                     "opponent": opponent,
        #                     "rundle": rundle_string
        scores_string = ""
        for item in todays_scores:
            scores_string += (
                f"{item['user']}: {item['record']} {item['score']} {item['rundle']}\n"
            )

    return scores_string, question_text, head_to_head_string


def get_weekly_scores():
    global player_list
    todays_scores = []
    best_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.learnedleague.com/")
        page.fill('#sidebar input[name="username"]', config["LL_USERNAME"])
        page.fill('#sidebar input[name="password"]', config["LL_PW"])
        page.click('#sidebar input[type="submit"]')
        shuffled_list = list(player_list.items())
        random.shuffle(shuffled_list)

        for player, id_dict in shuffled_list:
            player_id = id_dict["id"]
            page.goto(
                "https://www.learnedleague.com/profiles.php?{id}".format(id=player_id)
            )
            person_name = page.inner_html(".namecss")
            print("personname, ", person_name)
            scores = page.inner_html("div.fl_latest.fl_l_r.plresults")
            dfs = pd.read_html(scores)
            if dfs and len(dfs) > 0:
                df = dfs[0].dropna()
                df["Match Day"] = [s[: len(s) // 2] for s in df["Match Day"].values]
                last_five_records = df.iloc[-5:, :]["Result"].tolist()
                last_five_scores = df.iloc[-5:, :]["Result.1"].tolist()
                last_five_day = df.iloc[-5:, :]["Match Day"].tolist()
                shuffled_records = list(enumerate(last_five_records))
                random.shuffle(shuffled_records)
                for i, record in shuffled_records:
                    if record == "W":
                        score = int(last_five_scores[i][0])
                        best_list.append(
                            {
                                "person": person_name,
                                "score": score,
                                "day": last_five_day[i],
                                "full_score": last_five_scores[i],
                            }
                        )
    random.shuffle(best_list)
    return best_list[0]


def get_eos_stats(player_list):
    todays_scores = []
    question_results = None
    season_stats = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.learnedleague.com/")
        page.fill('#sidebar input[name="username"]', config["LL_USERNAME"])
        page.fill('#sidebar input[name="password"]', config["LL_PW"])
        page.click('#sidebar input[type="submit"]')
        for player, id_dict in player_list.items():
            player_id = id_dict["id"]
            page.goto(
                "https://www.learnedleague.com/profiles.php?{id}".format(id=player_id)
            )
            username = str(page.inner_html(".namecss"))
            result_string = username
            rundle_string = page.inner_html(".std-left-key a")
            rundle_string = " ".join(rundle_string.split()[0:2])
            scores = page.inner_html("#Latest div table:first-of-type")
            dfs = pd.read_html("<table>" + scores + "</table>")
            if dfs and len(dfs) > 0:
                df = dfs[0].dropna()
                season_stats.append(
                    {
                        "Player": username,
                        "Rundle": rundle_string,
                        "Place": df["Rank"].values[0],
                        "Wins": df["W"].values[0],
                        "Losses": df["L"].values[0],
                        "Total Points": df["TMP"].values[0],
                        "Point Differential": df["MPD"].values[0],
                        "Correct Answers": df["TCA"].values[0],
                        "Accuracy": df["TCA"].values[0] / (6 * 25),
                    }
                )
    season_stats = sorted(season_stats, key=lambda x: x["Player"])
    season_stats_df = pd.DataFrame.from_dict(season_stats)
    return season_stats_df


# Post request with requests python library
def post_text(text, recipients):
    text = text.strip()
    print(text)
    encoded_body = json.dumps(
        {
            "sendStyle": "regular",
            "recipient": recipients,
            "body": {"message": text},
        }
    )
    http = urllib3.PoolManager()
    r = http.request('POST', 'http://localhost:3005/message',
                     headers={'Content-Type': 'application/json'},
                     body=encoded_body)

    print(r.read())

    # Post request with requests python library



def get_chatgpt_response(scores,qs,h2h):

    recap_prompt = """
    Please write a single-paragraph news blurb about the following daily results from a trivia league, which is divided into different leagues called "rundles" for the following players. 
    Be antagonistic and insulting to IndurskyJ if they are included in the scores.

    Results:
    """

    highlights_prompt = """
    In addition, add a paragraph of highlights, which calls out the following head-to-head matchups and any question(s) that a single player got correct or missed. 
    If no information for either is provided, do not include it in the output."""

    prompt = recap_prompt + scores +'\n' + highlights_prompt + '\n' + qs +'\n' + h2h

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k-0613",
        max_tokens=4000,
        temperature=1.2,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )
    return response["choices"][0]['message']['content']


if __name__ == "__main__":
   
    # eos_df = get_eos_stats(player_list_imessage)
    # dfi.export(eos_df, "imessage_eof.png")

    # eos_df = get_eos_stats(player_list_sms)
    # dfi.export(eos_df, "sms_eof.png")

    dayno = datetime.datetime.today().weekday()
    if dayno >= 1 and dayno <= 5:
        ############# IMESSAGE VERSION #############
        scores, questions, h2h = get_scores(player_list_imessage)
        post_text(scores, recipients_imessage)
        post_text(questions, recipients_imessage)
        post_text(h2h, recipients_imessage)
        # gpt_resp = get_chatgpt_response(scores, questions, h2h)
        # post_text(gpt_resp, recipients_imessage)

        # ############# Text VERSION #############
        scores, questions, h2h = get_scores(player_list_sms)
        post_text(scores, recipients_sms)
        post_text(questions, recipients_sms)
        post_text(h2h, recipients_sms)

        # Check if the current date is September 2, 2023
        # gpt_resp = get_chatgpt_response(scores, questions, h2h)

        # post_text(gpt_resp, recipients_sms)

