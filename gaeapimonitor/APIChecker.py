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

class APIChecker(object):
	def __init__(self):
		pass
		
	def tweetStatus(self, status):
		auth = tweepy.OAuthHandler(config.twitterbot_consumer_key, config.twitterbot_consumer_secret)
		auth.set_access_token(config.twitterbot_access_token, config.twitterbot_access_token_secret)
		try:
			bot = tweepy.API(auth)
			bot.update_status(status)
		except:
			pass
	
	def addAPIForm(self):
		data = '<html>'
		data += '<body>'
		data += '<form method="POST" action="/apimonitor/addapi">'
		data += '<table>'
		data += '<tr><td>url</td><td><input name="url" size="58" /></td></tr>'
		data += '<tr><td>parameters (in JSON)<br>e.g.<br>{"v":"3.1.1"} or<br>{"v":"3.2", "e":"l"}</td><td><textarea rows="10" cols="42" name="form_fields"></textarea></td></tr>'
		data += '<tr><td>http method</td>'
		data += '<td>'
		data += '<select name="http_method">'
		data += '<option value="GET">GET</option>'
		data += '<option value="POST">POST</option>'
		data += '</select>'
		data += '</td>'
		data += '<tr><td>time limit</td><td><input name="time_threshold" size="58" value="0.0"/></td></tr>'
		data += '<tr><td>alerts</td><td>'
		data += '<input type="checkbox" name="has_changed" value=1>content changes<br>'
		data += '<input type="checkbox" name="valid_json" value=1 checked>invalid JSON<br>'
		data += '<input type="checkbox" name="is_down" value=1 checked>api down<br>'
		data += '</td></tr>'
		data += '<tr><td>twitter user</td><td><input name="twitter_user" size="58" /></td></tr>'
		data += '<tr><td>label (optional)</td><td><input name="label" size="58" /></td></tr>'
		data += '<tr><td>alert type</td>'
		data += '<td>'
		data += '<select name="alert_type">'
		data += '<option value=1>direct message</option>'
		data += '<option value=0>reply</option>'
		data += '</select>'
		data += '</td>'
		data += '<tr><td><input type="submit" value="Submit" /></td></tr>'
		data += '</table>'
		return data
		
	def loadJSONContent(self, url, form_fields, http_method):
		
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
				try:
					response = simplejson.loads(result.content)
				except:
					response = 0
				return url, response, result.status_code, response_time
			else:
				return url, 0, result.status_code, response_time
		except:
			return url, 0, 500, 0
	
	def trackAPIChangeByID(self, api_id):
		api = APIStorage.get_by_id(api_id)
		return self.trackAPIChange(api)
	
	def trackAPIChange(self, api):
		data = ''
		parameters = simplejson.loads(api.form_fields)
		response = self.checkAPI(api.url, parameters, api.http_method, api.twitter_user, api.label, alert_type=api.alert_type, has_changed=api.has_changed, valid_json=api.valid_json, is_down=api.is_down, time_threshold=api.time_threshold)
		#data += ">>> %s" % response
		
		if api.label=='':
			url_id = "%s | id:%s" % (api.url.split("://")[1], api.key().id())
		else: 
			url_id = "%s | id:%s" % (api.label, api.key().id())
		message = url_id
		
		if response['status_code']==200 or response['status_code']==301:
			pass
		else:
			message +=  ' | status:%s' % response['status_code']
		
		
		if api.has_changed:
			try:
				if response['has_changed']:
					message +=  ' | content changed'
			except:
				pass
				
		if api.valid_json:
			if not response['valid_json']:
				message +=  ' | x JSON'
				
		if api.time_threshold!=0.0:
			try:
				if not response['within_time_threshold']:
					message +=  ' | rtime:%s>%s' % (response['response_time'], api.time_threshold)
			except:
				pass
		
		if message!=url_id:
			twitter_users = api.twitter_user.strip().split(",")
			if api.label=='':
				message += " | params:%s" % api.form_fields 
			if len(message)>140:
				message = message[:140]
			for user in twitter_users:
				user = user.strip()
				status = "D %s %s" % (user, message)	
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
			data += self.trackAPIChange(api)	
		return data
			
	def checkAPI(self, url, form_fields, http_method, twitter_user, label, alert_type=1, has_changed=False, valid_json=True, is_down=True, time_threshold=0.0):
		form_fields['os'] = 'appengine'
		query_url, response, status_code, response_time = self.loadJSONContent(url, form_fields, http_method)
		result = {}
		result['url'] = url
		result['form_fields'] = simplejson.dumps(form_fields)
		result['http_method'] = http_method
		if not response:
			result['valid_json'] = False
			result['status_code'] = status_code
			result['response_time'] = response_time
			return result
		else:
			form_fields2 = form_fields
			try:
				del form_fields2['os']
			except:
				pass
			form_fields_dump = simplejson.dumps(form_fields2)
			apis = db.GqlQuery("SELECT * FROM APIStorage WHERE url=:url AND form_fields=:form_fields AND http_method=:http_method AND twitter_user=:twitter_user", url=url, form_fields=form_fields_dump, http_method=http_method, twitter_user=twitter_user)
			count = 0
			data = ''
			count = apis.count()
			for api_storage in apis:
				
				if api_storage.has_changed:
					last_valid_response = api_storage.last_valid_response
					new_json_response = simplejson.dumps(response)
					if last_valid_response==new_json_response:
						result['has_changed'] = False
					else:
						result['has_changed'] = True
				
				if api_storage.time_threshold!=0.0:
					if response_time > api_storage.time_threshold:
						result['within_time_threshold'] = False
					else:
						result['within_time_threshold'] = True
				
				api_storage.has_changed = has_changed
				api_storage.valid_json = valid_json
				api_storage.label = label
				api_storage.is_down = is_down
				api_storage.alert_type = alert_type
				api_storage.time_threshold = time_threshold
				api_storage.last_valid_response = simplejson.dumps(response)
				if twitter_user!='':
					api_storage.put()
				
				result['id'] = api_storage.key().id()
			if count==0:
				
				if time_threshold!=0.0:
					if response_time > time_threshold:
						result['within_time_threshold'] = False
					else:
						result['within_time_threshold'] = True
				
				api_storage = APIStorage()
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
				api_storage.last_valid_response = simplejson.dumps(response)
				if twitter_user!='':
					api_storage.put()
				result['new_entry'] = True
				result['id'] = api_storage.key().id()
			else:
				result['new_entry'] = False
		
			result['valid_json'] = True
			result['status_code'] = status_code
			result['response_time'] = response_time
			return result