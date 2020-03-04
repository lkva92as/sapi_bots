import json
import time
import requests
from TwitterAPI import TwitterAPI
from datetime import datetime
from datetime import timedelta
from slackclient import SlackClient
from collections import OrderedDict

#load secrets
f = json.load(open('secrets.json', 'r'))
slack_token = f['slack_token']
BOT_ID = f['bot_id']

#twitter secrets
consumer_key = f['consumer_key']
consumer_secret = f['consumer_secret']
access_token=f['access_token']
access_token_secret=f['access_token_secret']

api = TwitterAPI(consumer_key, consumer_secret, access_token, access_token_secret)

#SLACK STUFF
AT_BOT = "<@" + BOT_ID + ">"
slack_client = SlackClient(slack_token)
BOT_NAME = 'autocountbot'


GENERAL_CHANNEL = "#general"
ALERT_CHANNEL = "#twitteralert"

HANDLES = {818910970567344128: 'VP',
            25073877: 'realDonaldTrump',
            822215679726100480: 'POTUS',
            836598396165230594: 'predickit',
            822215673812119553: 'WhiteHouse'}

# 836598396165230594: 'predickit'

last_status = 0


def get_since_last():
    global last_update_time
    global since_last
    try:
        since_last = datetime.now() - last_update_time
    except NameError:
        print "since_last not defined yet"
    # else:
    #     print str(since_last.total_seconds())  + " seconds since last update"


def load_data():
    global lithium_data
    global last_update_time
    global since_last
    print "Loading the data from realcount.club ...."
    url = 'http://realcount.club/data.php'
    lithium_req = requests.get(url)
    lithium_data = lithium_req.json()
    lithium_data = OrderedDict(sorted(lithium_data.items(), key=lambda t: t[0].lower()))
    last_update_time = datetime.now()
    get_since_last()
    # print lithium_data


def reload_data():
    # print "Checking for last update ...."
    get_since_last()

    if since_last > timedelta(minutes=10):
        load_data()
    # else:
    #     print "Too soon to update from realcount.club again."


def get_counts():
    quickcount = ""
    global lithium_data
    global tweet
    tweet = {}
    print "Updating counts ...."
    reload_data()

    # call twitter api for each
    for key in lithium_data:
        tweet[key]=api.request('users/lookup', {'screen_name':key}).json()[0]
        lithium_data[key]['count'] = tweet[key]['statuses_count'] - lithium_data[key]['num']

    quickcount = cycle_keys()
    return quickcount


def post_message(channel, response, username=None, pic=None):
    if username is None:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)
    else:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=False, username=username, icon_url=pic)
    # print(response)


def cycle_keys():
    quickcount = ""
    for key in lithium_data:
        quickcount += "<" + lithium_data[key]['link'] + "|*" + key + "*> " + str(lithium_data[key]['count']) + "      "

    quickcount = quickcount.replace("realDonaldTrump", "RDT")
    quickcount = quickcount.replace("WhiteHouse", "WH")
    quickcount += "<http://realcount.club/|more>"
    print quickcount
    return quickcount


def on_delete(item):
    print "deletion"
    global lithium_data
    user_id = item['delete']['status']['user_id']
    status_id = item['delete']['status']['id']
    # url = "https://twitter.com/" + HANDLES[user_id] + "/status/" + str(status_id)
    url = "http://didtrumptweetit.com/" + str(status_id) + "/"
    response = HANDLES[user_id] + " DELETION!!!"
    print(response)
    print(url)

    general_response = response + "\n" + url

    if HANDLES[user_id] == 'realDonaldTrump':
        post_message(GENERAL_CHANNEL,general_response)

    try:
        lithium_data[HANDLES[user_id]]['count'] -=1
    except:
        print "no lithium_data key for " + HANDLES[user_id]

    quickcount = cycle_keys()

    if HANDLES[user_id] == 'realDonaldTrump':
        post_message(GENERAL_CHANNEL,quickcount)

    post_message(ALERT_CHANNEL,response+"\n"+quickcount+"\nDeleted tweet: "+url)


def on_status(item):
    global lithium_data
    global last_status
    if item['id'] > last_status:
        last_status = item['id']
        print("\n status")
        print(json.dumps(item))

        # item['user']['id']
        at_name = "@" + item['user']['screen_name'] + " tweet!"
        url = "https://twitter.com/" + item['user']['screen_name'] + "/status/"+str(item['id'])
        response = url

        if item['user']['screen_name'] == "realDonaldTrump" and 'retweeted_status' not in item:
            post_message(GENERAL_CHANNEL, response, at_name, item['user']['profile_image_url'])

        if item['user']['screen_name'] == "pi_greybox":
            post_message(GENERAL_CHANNEL, response, at_name, item['user']['profile_image_url'])
            post_message(ALERT_CHANNEL, response, "New Grey Box Post!", item['user']['profile_image_url'])
            return

        try:
            lithium_data[item['user']['screen_name']]['count'] = item['user']['statuses_count'] - lithium_data[item['user']['screen_name']]['num']
        except:
            try:
                lithium_data[item['user']['screen_name']]['count'] +=1
            except:
                print("no lithium_data key for " + item['user']['screen_name'])

        quickcount = cycle_keys()

        if item['user']['screen_name'] == "realDonaldTrump":
            post_message(GENERAL_CHANNEL, quickcount, at_name, item['user']['profile_image_url'])

        text = item['text']
        alertresponse = url + "\n" + text + "\n" + quickcount
        post_message(ALERT_CHANNEL, alertresponse, at_name, item['user']['profile_image_url'])



# print list(HANDLES.keys())

if __name__ == '__main__':
    load_data()
    quickcount = get_counts()
    post_message("#test", "Loading up streambot...")
    post_message("#test", quickcount)
    # print "Showing all tweets from my timeline"

    r = api.request('statuses/filter', {'follow':list(HANDLES.keys())})
    for item in r:
        if 'delete' in item:
            on_delete(item)
        if 'user' in item:
            if item['user']['id'] in list(HANDLES.keys()):
                on_status(item)
        # try:
        #     reload_data()
        # except:
        #     pass
            # else:
            #     try:
            #         reload_data()
            #     except:
            #         pass
            #     print('\n')
            #     print(json.dumps(item))
