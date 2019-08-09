#encoding: utf-8
import webapp2
import json
import logging
from google.appengine.api import urlfetch
from bot import Bot
import yaml
from user_events import UserEventsDao

VERIFY_TOKEN = "facebook_verification_token"
ACCESS_TOKEN = "EAAHrZAm4bLAYBAM9Yuqk8JzhDZAqMAZAqZAxIZAEDnZCbuedd0MHcDpaWiNA4WxJaCa6L4aTu8NsBWmCkSiwTP0dZCQH4bCJJLwdgvaXcdZApupNETQzDZCNwJeb9k4fo6Om3iR4Utbth2WpSncKK3sJ6uu7nL9qJ6ulKLV63OYqwNAZDZD"

class MainPage(webapp2.RequestHandler):
    def __init__(self, request=None, response=None):
        super(MainPage, self).__init__(request, response)
        logging.info("Instanciando bot")
        tree = yaml.load(open('tree.yaml'))
        logging.info("Tree : %r", tree)
        self.bot = Bot(send_message, UserEventsDao(), tree)
        # dao = UserEventsDao()
        #dao.add_user_event("123", "user", "abc")
        # dao.add_user_event("123", "bot", "def")
        # dao.add_user_event("123", "user", "ghi")
        # dao.add_user_event("123", "bot", "jkl")
        # dao.add_user_event("123", "user", "mnñ")
        # data = dao.get_user_events("123")
        # logging.info("eventos: %r", data)
        # dao.remove_user_events("123")

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'

        mode = self.request.get("hub.mode")
        if mode == "subscribe":
            challenge = self.request.get("hub.challenge")
            verify_token = self.request.get("hub.verify_token")
            if verify_token == VERIFY_TOKEN:
                self.response.write(challenge)
        else:
            self.response.write("Ok")
            #self.bot.handle(0, "response")


    def post(self):
        logging.info("Data obtenida desde messenger %s", self.request.body)
        data = json.loads(self.request.body)
        #logging.info("Data obtenida desde messenger %r", data)

        if data["object"] == "page":

            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:
                    sender_psid = messaging_event["sender"]["id"]
                    recipient_psid = messaging_event["recipient"]["id"]

                    if messaging_event.get("message"):
                        is_admin = False

                        message = messaging_event["message"]
                        message_text = message["text"]
                        #message_text = messaging_event["message"]["text"]
                        #message_text = message.get["text", '']
                        logging.info("Message: %s", message_text)

                        if message.get('is_echo'):
                            if message.get('app_id'): #campo adicional que facebook envia si escribe el bot
                                continue
                            else: #escribe un admin
                                is_admin = True

                        if is_admin:
                            user_id = recipient_psid
                        else:
                            user_id = sender_psid

                        self.bot.handle(user_id, message_text, is_admin)

                        #response = "You sent the message: {}. Now send me an image!".format(message_text)
                        #bot handle
                        #send_message(sender_psid, response)

                    if messaging_event.get("postback"):
                        message_text = messaging_event["postback"]['payload']
                        #bot handle
                        self.bot.handle(sender_psid, message_text)
                        logging.info("Postback: %s", message_text)

def send_message(sender_psid, message_text, possible_answers):

    headers = {
        "Content-Type": "application/json"
    }
    #Respuesta tipo texto
    # response = {
    #     "text": message_text
    # }
    #Respuesta tipo Boton, máximo 3 opciones
    #Cada opción máximo 20 caracteres
    #possible_answers = ["Opcion A", "Opcion B", "Opcion C"]
    valid_possible_answers = possible_answers is not None and len(possible_answers) <= 3
    if valid_possible_answers:
        response = get_postback_buttons_message(message_text, possible_answers)
    elif message_text.startswith('https'):
        response = get_url_buttons_message(message_text)
    #elif response is None:
    else:
       response = {"text": message_text} 

    request_body = {
        #"messaging_type": "RESPONSE",
        "recipient" : {
            "id": sender_psid
        },
        "message": response
    }
    data = json.dumps(request_body)

    logging.info("Enviando mensaje a %r: %s", sender_psid, message_text)
    
    r = urlfetch.fetch("https://graph.facebook.com/v2.6/me/messages?access_token=%s" % ACCESS_TOKEN, 
                        method=urlfetch.POST, headers=headers, payload=data)

    if r.status_code != 200:
        logging.error("Error %r enviando mensaje: %s", r.status_code, r.content)


def get_postback_buttons_message(message_text, possible_answers):
    buttons = []
    for answer in possible_answers:
        buttons.append({
            "type": "postback",
            "title": answer,
            "payload": answer
        })

    return get_buttons_template(message_text, buttons)

def get_url_buttons_message(message_text):
    urls = message_text.split()
    elements = []
    buttons = []
    url_default = ""
    index = 0
    for url in urls:
        if index < 1:
            url_default = url
        index = index + 1
        buttons.append({
            "type": "web_url",
            "url": url,
            #"title": "Ver enlace"
            "title": url
        })

    elements.append({
        "title":"Enlaces",
        #"image_url":"https://petersfancybrownhats.com/company_image.png",
        "subtitle":"Recomendados",
        "default_action": {
            "type": "web_url",
            "url": url_default,
            #"webview_height_ratio": "tall",
            "webview_height_ratio": "full",
        },
        "buttons": buttons
    })

    return get_default_template(elements)

def get_buttons_template(message_text, buttons):
    return {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "button",
                "text": message_text,
                "buttons": buttons,
            }
        }
    }

def get_default_template(elements):
    return {
        "attachment":{
            "type":"template",
            "payload":{
                "template_type":"generic",
                "elements": elements
            }
        }
    }


def get_open_graph_template(elements):
    return {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "open_graph",
                "elements": elements
            }
        }
    }


class PrivacyPolicyPage(webapp2.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        htmlContent = open('privacy-policy.html').read()
        self.response.write(htmlContent)

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/privacy-policy', PrivacyPolicyPage),    
], debug=True)

