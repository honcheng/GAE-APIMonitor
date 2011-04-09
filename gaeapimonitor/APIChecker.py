# Copyright (c) 2009 Muh Hon Cheng
# Created by honcheng on 4/12/10.
# 
# Permission is hereby granted, free of charge, to any person obtaining 
# a copy of this software and associated documentation files (the 
# "Software"), to deal in the Software without restriction, including 
# without limitation the rights to use, copy, modify, merge, publish, 
# distribute, sublicense, and/or sell copies of the Software, and to 
# permit persons to whom the Software is furnished to do so, subject 
# to the following conditions:
# 
# The above copyright notice and this permission notice shall be 
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT 
# WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
# MERCHANTABILITY, FITNESS FOR A PARTICULAR 
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT 
# SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE 
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, 
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR 
# IN CONNECTION WITH THE SOFTWARE OR 
# THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 
# @author 		Muh Hon Cheng <honcheng@gmail.com>
# @copyright	2010	Muh Hon Cheng
# 


from django.utils import simplejson
import urllib
from google.appengine.api import urlfetch
from datastore import APIStorage
from google.appengine.ext import db
from time import time
import config
import tweepy
import datetime
import os
from google.appengine.ext.webapp import template
import googlediffmatchpatch
import re
import sys
import md5
import bitly
import logging
from google.appengine.api import taskqueue
from google.appengine.api import mail
from gaeapimonitor.googleurlshortener import Googl

class APIChecker(object):
	def __init__(self):
		pass
	
	def shortenUrl(self, link):
		
		googl_api = Googl(config.googl_apikey)
		try:
			googl_component = googl_api.shorten(link)
			logging.debug("goo.gl : %s", googl_component)
			shorten_link = googl_component['id']
			return shorten_link
		except Exception, e:
			logging.error("error getting goo.gl link %s : %s", link, e)
			try:
				bitly_api = bitly.BitLy(login=config.bitly_username, apikey=config.bitly_apikey) 
				escaped_link = link.replace("&","%26")
				bitly_component = bitly_api.shorten(escaped_link)
				logging.debug("bit.ly : %s", bitly_component)
				shorten_link = bitly_component['results'][link]['shortUrl']
				return shorten_link
			except Exception, e2:
				logging.error("error getting bit.ly link %s : %s", link, e2)
				return link
		
	def tweetStatus(self, status):
		auth = tweepy.OAuthHandler(config.twitterbot_consumer_key, config.twitterbot_consumer_secret)
		auth.set_access_token(config.twitterbot_access_token, config.twitterbot_access_token_secret)
		try:
			bot = tweepy.API(auth)
			result = bot.update_status(status)
		except tweepy.TweepError, e:
			if len(e.args)==2:
				auth2 = tweepy.OAuthHandler(config.twitterbot_consumer_key, config.twitterbot_consumer_secret)
				auth2.set_access_token(config.twitterbot_access_token_alternative, config.twitterbot_access_token_secret_alternative)
				bot2 = tweepy.API(auth2)
				bot2.update_status(status)
				message, response = e
				logging.warning("Tweepy error : %s, %s", message, response)
			elif len(e.args)==1:
				auth2 = tweepy.OAuthHandler(config.twitterbot_consumer_key, config.twitterbot_consumer_secret)
				auth2.set_access_token(config.twitterbot_access_token_alternative, config.twitterbot_access_token_secret_alternative)
				bot2 = tweepy.API(auth2)
				bot2.update_status(status)
				logging.warning('Tweepy error : %s', e)
			else:
				logging.debug('Tweepy error - unknown')
		except Exception, e:
			#pass
			logging.warning("failed to send out alerts with APIMonitor, attempt to use APIMonitor2 %s" % e)
			try:
				pass
				#auth2 = tweepy.OAuthHandler(config.twitterbot_consumer_key, config.twitterbot_consumer_secret)
				#auth2.set_access_token(config.twitterbot_access_token_alternative, config.twitterbot_access_token_secret_alternative)
				#bot2 = tweepy.API(auth2)
				#bot2.update_status(status)
			except:
				pass
			#	logging.warning("failed to send out alerts with APIMonitor and APIMonitor2 %s" % error2)
			#	mail.send_mail(sender="APIMonitor <appengineapimonitor@gmail.com>",
			#	              to="honcheng <honcheng@gmail.com>",
			#	              subject="APIMonitor Alert",
			#	              body=status)

	
	def addAPIForm(self):
		path = os.path.join(os.path.dirname(__file__), 'addform.html')
		form_content = template.render(path, None)
		return form_content
		
	def loadJSONContent(self, url, form_fields, http_method):
		query_url, response, status_code, response_time = self.loadContent(url, form_fields, http_method, 1)
		try:
			json_content = simplejson.loads(response)
		except:
			json_content = 0
		return query_url, json_content, status_code, response_time
		
	def loadContent(self, url, form_fields, http_method, n_tries):
		
		try:
			response_time = 0
			start_time = time()
			if http_method=='POST':
				form_data = urllib.urlencode(form_fields)
				result = urlfetch.fetch(url=url,
			                        payload=form_data,
			                        method=urlfetch.POST,
			                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
			else :
				for i in range(0,len(form_fields.keys())):
					key = form_fields.keys()[i]
					value = form_fields[key]
					if i==0:
						url += "?%s=%s" % (key, value)
					else:
						url += "&%s=%s" % (key, value)
				result = urlfetch.fetch(url)
			end_time = time()
			response_time = round(end_time - start_time, 2)

			if result.status_code==200 or result.status_code==301:
				#try:
				#	response = simplejson.loads(result.content)
				#except:
				#	response = 0
				return url, result.content, result.status_code, response_time
			else:
				return url, 0, result.status_code, response_time
		except:
			#return self.loadContent(url, form_fields, http_method, n_tries+1)
			
			if n_tries!=config.n_times_to_retry_408_before_sending_alerts:
				return self.loadContent(url, form_fields, http_method, n_tries+1)
			else:
				return url, 0, 408, 0
	
	def trackAPIChangeByID(self, api_id, n_trial):
		api = APIStorage.get_by_id(api_id)
		if api.api_id==None:
			api_id = "%s-%s" % (api.url, datetime.datetime.now())
			api_id = md5.new(api_id).hexdigest()
			api.api_id = api_id
			api.put()
		return self.trackAPIChange(api, n_trial)
	
	def removeAPIByID(self, api_id):
		apis = db.GqlQuery("SELECT * FROM APIStorage WHERE api_id=:api_id", api_id=api_id)
		for api in apis:
			api.delete()
	
	def checkAPIChangeByID(self, api_id):
		apis = db.GqlQuery("SELECT * FROM APIStorage WHERE api_id=:api_id", api_id=api_id)
		for api in apis:
			parameters = simplejson.loads(api.form_fields)
			query_url, response, status_code, response_time = self.loadContent(api.url, parameters, api.http_method, 1)
			if response!=0:
				response = response.decode('utf8','replace')
				response = response.encode('ascii','replace')
			changes = ''
			if api.has_changed:
				comparer = googlediffmatchpatch.diff_match_patch()
				a = self.stripWhiteSpace(self.stripHTMLTags(api.last_valid_response_before_changes))
				b = self.stripWhiteSpace(self.stripHTMLTags(api.last_valid_response))
				
				try:
					diffs = comparer.diff_main(a,b)
					comparer.diff_cleanupSemantic(diffs)
					for diff in diffs:
						status = diff[0]
						if status==1:
							text = diff[1]
							#if not changes.has_key('added'):
							#	changes['added'] = []
							#changes['added'].append(text)
							changes += '<b>ADDED</b> %s <br>' % text
						elif status==-1:
							text = diff[1]
							#if not changes.has_key('removed'):
							#	changes['removed'] = []
							#changes['removed'].append(text)
							changes += '<b>REMOVED</b> %s <br>' % text
				except Exception,e:
					pass
					#logging.warning('>>> %s ' % e)
					#logging.warning("error comparing responses OLD[%s] NEW[%s]" % (api.last_valid_response,api.last_valid_response_before_changes))	
			#logging.warning("changes <>>>>>>> %s" % changes)
			return api, response, status_code, changes
		return -1, -1, -1, {}
			
	def trackAPIChange(self, api, n_trial):
		data = ''
		parameters = simplejson.loads(api.form_fields)
		response = self.checkAPI(api.url, parameters, api.http_method, api.twitter_user, api.label, expiry_time=api.expiry_time, alert_type=api.alert_type, has_changed=api.has_changed, valid_json=api.valid_json, is_down=api.is_down, time_threshold=api.time_threshold, min_percentage_changed=api.min_percentage_changed, n_trial=n_trial)
		#data += ">>> %s" % response

		if api.label=='':
			#url_id = "%s | id:%s" % (api.url.split("://")[1], api.key().id())
			url_id = api.url.split("://")[1]
		else: 
			#url_id = "%s | id:%s" % (api.label, api.key().id())
			url_id = api.label
		message = url_id
		
		if api.is_down:
			if response['status_code']==200 or response['status_code']==301:
				if api.last_status_code!=200 and api.last_status_code!=301:
					message += ' | OK (status changed from %s to %s)' % (api.last_status_code, response['status_code'])
				#api.last_status_code = response['status_code']
				#api.put()
			elif response['status_code']==408:
				logging.info("STATUS: %s (%s)" % (response['status_code'], n_trial) )
				if n_trial==config.n_times_to_retry_408_before_sending_alerts:
					if api.last_status_code!=408:
						message +=  ' | request timeout (408)'
						#api.last_status_code = response['status_code']
						#api.put()
					else:
						return
				else:
					_id = int(api.key().id())
					taskqueue.add(url=config.url_track_id, params={ "id": _id, "n_trial": n_trial+1})
					#api.last_status_code = response['status_code']
					#api.put()
					return
			else:
				logging.debug("STATUS: %s (%s)" % (response['status_code'], n_trial) )
				if response['status_code']==500:
					message +=  ' | internal server error (500)'
				elif response['status_code']==502:
					message +=  ' | bad gateway (502)'
				elif response['status_code']==503:
					message +=  ' | service unavailable (503)'
				elif response['status_code']==504:
					message +=  ' | gateway timeout (504)'
				elif response['status_code']==404:
					message +=  ' | not found (404)'
				else:
					message +=  ' | status:%s' % response['status_code']
				#api.last_status_code = response['status_code']
				#api.put()
		else:
			pass
			#api.last_status_code = response['status_code']
			#api.put()
		
		if api.has_changed:
			try:
				if response['has_changed']:
					if response.has_key('percentage_change'):
						if response['percentage_change'] > api.min_percentage_changed:
							message +=  ' | content changed %s%%' % response['percentage_change']
							if response.has_key('added'):
								items = response['added']
								for item in items:
									message +=  ' (+) %s' % item
							if response.has_key('removed'):
								items = response['removed']
								for item in items:
									message +=  ' (-) %s' % item
			except:
				pass
		
		if response['status_code'] not in [404, 408, 500, 502, 503, 504]: #!=408 and response['status_code']!=500 and response['status_code']!=502 and response['status_code']!=503:	
			if api.valid_json:
				if not response['valid_json']:
					message +=  ' | invalid JSON'
				
		if api.time_threshold!=0.0:
			try:
				if not response['within_time_threshold']:
					message +=  ' | rtime:%s>%s' % (response['response_time'], api.time_threshold)
			except:
				pass
		
		if api.expiry_time!=0:
			try:
				if response['expired']:
					message += ' | content expired, age:%s>%s' % (response['age'], api.expiry_time)
			except:
				pass
		if message!=url_id:
			twitter_users = api.twitter_user.strip().split(",")
			
			if api.api_id!=None:
				if os.environ.get('HTTP_HOST'): 
					host = os.environ['HTTP_HOST'] 
				else: 
					host = os.environ['SERVER_NAME']
				link = "http://%s%s?id=%s" % (host,config.url_check, api.api_id)
				shorten_link = self.shortenUrl(link)
				if message.find('|')!=-1:	
					message = message.replace('|','%s |' % shorten_link,1)
				else:
					message += ' %s' % shorten_link
			elif api.http_method=="GET":
				link = api.url
				for i in range(0,len(parameters.keys())):
					key = parameters.keys()[i]
					value = parameters[key]
					if i==0:
						link += "?%s=%s" % (key, value)
					else:
						link += "&%s=%s" % (key, value)
				shorten_link = self.shortenUrl(link)
				if message.find('|')!=-1:	
					message = message.replace('|','%s |' % shorten_link,1)
				else:
					message += ' %s' % shorten_link
			
			if api.label=='':
				message += " | params:%s" % api.form_fields 
			if len(message)>140:
				message = message[:140]
			for user in twitter_users:
				user = user.strip()
				status = "D %s %s" % (user, message)
				logging.info("TWEET : %s", status)	
				self.tweetStatus(status)
				data += "<br><br>%s<br><br>" % status
		else:
			data += 'no update %s' % response
		return data
	
	def getTrackedAPIs(self):
		apis = db.GqlQuery("SELECT * FROM APIStorage")
		return apis
			
	def trackAPIChanges(self):
		apis = db.GqlQuery("SELECT * FROM APIStorage")
		data = ''
		for api in apis:
			data += self.trackAPIChange(api, 1)	
		return data
	
	def stripHTMLTags(self, data):
		if not data:
			return ''
		p = re.compile(r'<.*?>')
		return p.sub('', data)
	
	def stripWhiteSpace(self, data):
		if not data:
			return ''
		p = re.compile(r'\s+')
		return p.sub(' ', data)
			
	def checkAPI(self, url, form_fields, http_method, twitter_user, label, expiry_time=0, alert_type=1, has_changed=False, valid_json=True, is_down=True, time_threshold=0.0, min_percentage_changed=0.0, n_trial=1):
		if expiry_time==None:
			expiry_time = 0
		form_fields['os'] = 'appengine'
		query_url, response, status_code, response_time = self.loadContent(url, form_fields, http_method, n_trial)
		result = {}
		result['url'] = url
		result['form_fields'] = simplejson.dumps(form_fields)
		result['http_method'] = http_method
		
		form_fields2 = form_fields
		try:
			del form_fields2['os']
		except:
			pass
		form_fields_dump = simplejson.dumps(form_fields2)
		
		try:
			json_response = simplejson.loads(response)
			result['valid_json'] = True
		except:
			result['valid_json'] = False
		
		apis = db.GqlQuery("SELECT * FROM APIStorage WHERE url=:url AND form_fields=:form_fields AND http_method=:http_method AND twitter_user=:twitter_user", url=url, form_fields=form_fields_dump, http_method=http_method, twitter_user=twitter_user)
		

		if not response:
			result['valid_json'] = False
			result['status_code'] = status_code
			result['response_time'] = response_time
			for api_storage in apis:
				if n_trial==config.n_times_to_retry_408_before_sending_alerts:
					api_storage.last_status_code = status_code
					api_storage.put()
					#logging.warning(">>>>>>>>>>>>>>status %s %s" % (api_storage.last_status_code, status_code))
			return result
		else:
			count = 0
			data = ''
			count = apis.count()
			for api_storage in apis:
				
				should_update = False
				
				response = response.decode('utf8','replace')
				response = response.encode('ascii','replace')
				if api_storage.has_changed:
					last_valid_response = api_storage.last_valid_response
					#response = response.decode('utf8','replace')
					#response = response.encode('ascii','replace')
					md5hash = md5.new(response).hexdigest()
					
					if last_valid_response==response:
						result['has_changed'] = False
					elif last_valid_response==md5hash:
						result['has_changed'] = False
						response = md5hash
					else:
						result['has_changed'] = True
						should_update = True

						comparer = googlediffmatchpatch.diff_match_patch()
						if result['valid_json']:
							diffs = comparer.diff_main(last_valid_response,response)
							comparer.diff_cleanupSemantic(diffs)
						else:
							# assume that invalid JSON are HTML
							a = self.stripWhiteSpace(self.stripHTMLTags(last_valid_response))
							b = self.stripWhiteSpace(self.stripHTMLTags(response))
							try:
								diffs = comparer.diff_main(a,b)
								comparer.diff_cleanupSemantic(diffs)
							except:
								response = md5hash
								a = self.stripWhiteSpace(self.stripHTMLTags(last_valid_response))
								b = self.stripWhiteSpace(self.stripHTMLTags(response))
								diffs = comparer.diff_main(a,b)
								comparer.diff_cleanupSemantic(diffs)
						for diff in diffs:
							status = diff[0]
							if status==1:
								text = diff[1]
								if not result.has_key('added'):
									result['added'] = []
								result['added'].append(text)
							elif status==-1:
								text = diff[1]
								if not result.has_key('removed'):
									result['removed'] = []
								result['removed'].append(text)

						levenshtein_value = comparer.diff_levenshtein(diffs)
						if len(last_valid_response)>=len(response):
							percentage = float(levenshtein_value)/len(last_valid_response) * 100
						else:
							percentage = float(levenshtein_value)/len(response) * 100
						result['levenshtein'] = levenshtein_value
						if percentage>1:
							result['percentage_change'] = round(percentage,1)
						else:
							result['percentage_change'] = round(percentage,4)
				
				if api_storage.time_threshold!=0.0:
					if response_time > api_storage.time_threshold:
						result['within_time_threshold'] = False
					else:
						result['within_time_threshold'] = True
				
				if api_storage.expiry_time!=0:
					update_time = api_storage.update_time
					current_time = datetime.datetime.now()
					result['age'] = (current_time - update_time).seconds
					if result['age'] > api_storage.expiry_time:
						result['expired'] = True
					else:
						result['expired'] = False
				if api_storage.has_changed != has_changed:
					api_storage.has_changed = has_changed
					should_update = True	
				if api_storage.valid_json != valid_json:
					api_storage.valid_json = valid_json
					should_update = True	
				if api_storage.label != label:
					api_storage.label = label
					should_update = True
				if api_storage.is_down != is_down:
					api_storage.is_down = is_down
					should_update = True
				if api_storage.alert_type != alert_type:
					api_storage.alert_type = alert_type
					should_update = True
				if api_storage.time_threshold != time_threshold:
					api_storage.expiry_time = expiry_time
					should_update = True
				if api_storage.last_valid_response != response: #simplejson.dumps(response):
					api_storage.last_valid_response_before_changes = api_storage.last_valid_response
					api_storage.last_valid_response = response #simplejson.dumps(response)
					should_update = True
				if api_storage.last_status_code != status_code:
					api_storage.last_status_code = status_code
					should_update = True
				
				if twitter_user!='' and should_update:
					try:
						
						api_storage.put()
					except:
						logging.warning("unable to write to datastore")
				
				result['id'] = api_storage.key().id()
			if count==0:
				
				if time_threshold!=0.0:
					if response_time > time_threshold:
						result['within_time_threshold'] = False
					else:
						result['within_time_threshold'] = True
				
				api_id = "%s-%s" % (url, datetime.datetime.now())
				api_id = md5.new(api_id).hexdigest()
				
				api_storage = APIStorage()
				api_storage.api_id = api_id
				api_storage.url = url
				api_storage.http_method = http_method
				api_storage.form_fields = form_fields_dump
				api_storage.has_changed = has_changed
				api_storage.valid_json = valid_json
				api_storage.is_down = is_down
				api_storage.twitter_user = twitter_user
				api_storage.label = label
				api_storage.alert_type = alert_type
				api_storage.time_threshold = time_threshold
				api_storage.expiry_time = expiry_time
				api_storage.min_percentage_changed = min_percentage_changed
				try:
					response = response.decode('utf8','replace')
					response = response.encode('ascii','replace')
					api_storage.last_valid_response = response#simplejson.dumps(response)
				except:
					md5hash = md5.new(response).hexdigest()
					api_storage.last_valid_response = md5hash
				if twitter_user!='':
					api_storage.put()
				result['new_entry'] = True
				result['id'] = api_storage.key().id()
			else:
				result['new_entry'] = False
		
			result['status_code'] = status_code
			result['response_time'] = response_time
			return result