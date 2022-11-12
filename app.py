import datetime
import json
import random

import pandas as pd
import urllib3
# Reads from `.env file`
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright

config = dotenv_values("/Users/swarchol/Research/LLBot/.env")
print('config', config)

player_list = {'Simon': {'id': '55444'}, 'Nick': {'id': '58714'}, 'Luke': {'id': '68635'},
               'Jake': {'id': '56189'}, 'Rob': {'id': '64659'}, 'Katter': {'id': '58619'},
               'CC': {'id': '64157'}, 'Katie': {'id': '53779'}, 'Daniella': {'id': '68727'},
               'Cat': {'id': '71256'}, 'Yasmina': {'id': '72221'}, 'Kate': {'id': '68591'}}

recipients = {
    "name": config['CHAT_NAME'],
    "handle": config['CHAT_ID'],
}


def get_scores():
    global player_list
    todays_scores = []
    question_results = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://www.learnedleague.com/')
        page.fill('#sidebar input[name="username"]', config['LL_USERNAME'])
        page.fill('#sidebar input[name="password"]', config['LL_PW'])
        page.click('#sidebar input[type="submit"]')
        for player, id_dict in player_list.items():
            player_id = id_dict['id']
            page.goto('https://www.learnedleague.com/profiles.php?{id}'.format(id=player_id))
            username = str(page.inner_html('.namecss'))
            result_string = username
            rundle_string = page.inner_html('.std-left-key a')
            rundle_string = ' '.join(rundle_string.split()[0:2])
            scores = page.inner_html('div.fl_latest.fl_l_r.plresults')
            page.eval_on_selector_all("div.fl_latest.fl_l_r.plresults a[href^='/wiki/']",
                                      "elements => elements.map(element => element.href)")
            match_link = page.eval_on_selector_all("div.fl_latest.fl_l_r.plresults a[href^='/match.php?id=']",
                                                   "elements => elements.map(element => element.href)")[-1]
            dfs = pd.read_html(scores)
            if dfs and len(dfs) > 0:
                df = dfs[0].dropna()
                score = df.iloc[-1, :]['Result.1']
                record = df.iloc[-1, :]['Result']
                result_string += ': ' + str(record) + ' ' + str(score) + ' ' + str(rundle_string)
            todays_scores.append(result_string)
            page.goto(match_link)
            if question_results is None:
                question_results = []
                day_table = page.inner_html('table.QTable')
                day_table_df = pd.read_html('<table>' + day_table + '</table>')
                if day_table_df and len(day_table_df) > 0:
                    day_table_df = day_table_df[0].dropna()
                    for i in range(6):
                        question = str(day_table_df.iloc[i, 1]).replace(u'\xa0', u' ')
                        question_results.append({'question': question, 'smart': [], 'dumb': []})

            results_rows = page.query_selector_all('table.std.tbltop_inner tbody tr')
            user_row = None
            for row in results_rows:
                if username in row.inner_html():
                    user_row = row
                    break
            classes = row.eval_on_selector_all("td", "elements => elements.map(element => element.className)")[1:7]
            correct_questions = [e == 'c1' for e in classes]
            for i, correct in enumerate(correct_questions):
                if correct:
                    question_results[i]['smart'].append(username)
                else:
                    question_results[i]['dumb'].append(username)
    return sorted(todays_scores), question_results


def get_weekly_scores():
    global player_list
    todays_scores = []
    best_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://www.learnedleague.com/')
        page.fill('#sidebar input[name="username"]', config['LL_USERNAME'])
        page.fill('#sidebar input[name="password"]', config['LL_PW'])
        page.click('#sidebar input[type="submit"]')
        shuffled_list = list(player_list.items())
        random.shuffle(shuffled_list)

        for player, id_dict in shuffled_list:
            player_id = id_dict['id']
            page.goto('https://www.learnedleague.com/profiles.php?{id}'.format(id=player_id))
            person_name = page.inner_html('.namecss')
            print('personname, ', person_name)
            scores = page.inner_html('div.fl_latest.fl_l_r.plresults')
            dfs = pd.read_html(scores)
            if dfs and len(dfs) > 0:
                df = dfs[0].dropna()
                df['Match Day'] = [s[:len(s) // 2] for s in df['Match Day'].values]
                last_five_records = df.iloc[-5:, :]['Result'].tolist()
                last_five_scores = df.iloc[-5:, :]['Result.1'].tolist()
                last_five_day = df.iloc[-5:, :]['Match Day'].tolist()
                shuffled_records = list(enumerate(last_five_records))
                random.shuffle(shuffled_records)
                for i, record in shuffled_records:
                    if record == 'W':
                        score = int(last_five_scores[i][0])
                        best_list.append({'person': person_name, 'score': score, 'day': last_five_day[i],
                                          'full_score': last_five_scores[i]})
    random.shuffle(best_list)
    return best_list[0]


# Post request with requests python library
def post_text(text):
    global recipients
    encoded_body = json.dumps(
        {
            "sendStyle": "regular",
            "recipient": recipients,
            "body": {
                "message": text
            },
        }
    )
    http = urllib3.PoolManager()
    r = http.request('POST', 'http://localhost:3005/message',
                     headers={'Content-Type': 'application/json'},
                     body=encoded_body)

    print(r.read())


# Post request with requests python library


if __name__ == "__main__":
    dayno = datetime.datetime.today().weekday()
    if dayno >= 1 and dayno <= 5:
        scores, questions = get_scores()
        scores = '\n'.join(scores)
        post_text(scores)
        question_text = []
        for q in questions:
            if len(q['smart']) == 1:
                who = q['smart'][0]
                question_text.append('Only ' + who + ' got: ' + q['question'] + ' -- WOW!')
            if len(q['dumb']) == 1:
                who = q['dumb'][0]
                question_text.append('Only ' + who + ' missed: ' + q['question'] + ' -- WOW!')
        for qq in question_text:
            post_text(qq)
    if dayno == 5:
        best = get_weekly_scores()
        post_str = "🍰 ⋆ 🍉  🎀 Congrats to " + best[
            'person'] + " for winning '𝐿𝐿 𝐵𝒾𝑔 𝐵𝓇𝒶𝒾𝓃𝓈  F𝕽𝐸𝒜𝒦  🍪𝐹  𝒯𝐻𝐸 𝒲𝐸𝐸𝒦'!!!! " \
                        "Enter code `FREAK` at checkout on mypillow.com to claim your reward 🐘  🎀"
        post_text(post_str)
#
