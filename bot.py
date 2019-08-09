#encoding: utf-8
import logging

DEFAULT_RESPONSE = u"Disculpa, no entendí. ¿Deseas volver a empezar?"
DEFAULT_POSSIBLE_ANSWERS = [u"Sí", u"No"]

class Bot(object):
	def __init__(self, send_callback, users_dao, tree):
		self.send_callback = send_callback
		self.users_dao = users_dao
		self.tree = tree

	def handle(self, user_psid, user_message, is_admin=False):
		logging.info("Se invocó metodo handle")

		if is_admin:
			#Registra mensaje enviado por admin
			self.users_dao.add_user_event(user_psid, 'admin', user_message)
			return

		#Grabando el mensaje antes de cargar el history
		#nos aseguramos que el mensaje que envia el usuario haga parte del history
		#como ultimo valor
		#Registra mensaje enviado por el usuario
		self.users_dao.add_user_event(user_psid, 'user', user_message)

		if self.users_dao.admin_messages_exist(user_psid):
			#Si hay mensajes enviados por el administrador, no tiene sentido
			#seguir evaluando el arbol, ya que la conversación ahora es manual
			return

		#obtener historial de eventos/mensajes
		# history = [
		# 	(u"Hola! Por favor selecciona una opción para poder ayudarte.", "bot"),
		# 	(u"Cursos disponibles", "user"),
		# 	(u"Tenemos varios cursos! Todos ellos son muy interesantes y totalmente prácticos. Por favor selecciona la opción que te resulte más interesante.", "bot"),
		# 	(user_message, "user")
		# ]

		history = self.users_dao.get_user_events(user_psid)

		#Inicializamos arbol
		tree = self.tree
		new_conversation = True
		response_text = ""

		for text, author in history:
			logging.info("text: %s", text)
			logging.info("author: %s", author)

			if author == 'bot':
				# print type(text)
				# print type(tree['say'])
				new_conversation = False
				bot_asked_about_restart = False
				if text == DEFAULT_RESPONSE:
					bot_asked_about_restart = True
				elif 'say' in tree and text == tree['say'] and 'answers' in tree:
					#Acotamos el arbol
					tree = tree['answers']

			elif author == 'user':
				if new_conversation:
					#determinar una respuesta en funcion del mensaje escrito por el usuario y el arbol yaml
					response_text = tree['say']
					possible_answers = tree['answers'].keys()
					possible_answers.sort()
				else:
					if bot_asked_about_restart and text == u'Sí':
						#reiniciamos el arbol, con el arbol original
						tree = self.tree
						response_text = tree['say']
						possible_answers = tree['answers'].keys()
						possible_answers.sort()

						self.users_dao.remove_user_events(user_psid)
						break

					key = get_key_if_valid(text, tree)
					if key is None:
						response_text = DEFAULT_RESPONSE
						possible_answers = DEFAULT_POSSIBLE_ANSWERS
					else:
						tree = tree[key]
						if 'say' in tree:
							response_text = tree['say']
						if 'answers' in tree:
							possible_answers = tree['answers'].keys()
							possible_answers.sort()
						else:
							possible_answers = None

		self.send_callback(user_psid, response_text, possible_answers)
		self.users_dao.add_user_event(user_psid, 'bot', response_text)		

def get_key_if_valid(text, dictionary):
	for key in dictionary:
		if key.lower() == text.lower():
			return key

	return None