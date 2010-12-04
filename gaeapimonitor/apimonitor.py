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


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from django.utils import simplejson
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
import tweepy
from gaeapimonitor.APIChecker import APIChecker
from gaeapimonitor.datastore import APIStorage

class CheckAPI(webapp.RequestHandler):
	def get(self):
		self.parse()
	
	def post(self):
		#self.response.out.write(self.request.get('has_changed'))
		#self.response.out.write('<br><br>')
		self.parse()	
	
	def parse(self):
		url = self.request.get('url')
		http_method = self.request.get('http_method')
		if http_method=='':
			http_method = 'GET';
		form_fields = self.request.get('form_fields')
		twitter_user = self.request.get('twitter_user')
		has_changed = bool(self.request.get('has_changed'))
		is_down = bool(self.request.get('is_down'))
		valid_json = bool(self.request.get('valid_json'))
		"""
		if has_changed_txt=='':
			has_changed = None;
		else:
			has_changed = bool(self.request.get('has_changed'))
		"""
		time_threshold_txt = self.request.get('time_threshold')
		if time_threshold_txt=='':
			time_threshold = None;
		else:
			time_threshold = float(self.request.get('time_threshold'))
		
		alert_type_txt = self.request.get('alert_type')
		if alert_type_txt=='':
			alert_type = None
		else:
			alert_type = int(alert_type_txt)
			
		label = self.request.get('label')
		
		parameters = {}
		if form_fields!='':
			parameters = simplejson.loads(form_fields)	
		checker = APIChecker()
		
		data = checker.checkAPI(url, parameters, http_method, twitter_user, label, alert_type=alert_type, has_changed=has_changed, time_threshold=time_threshold, is_down=is_down, valid_json=valid_json)
		json_data = simplejson.dumps(data)
		self.response.out.write(json_data)

class AddAPITracking(webapp.RequestHandler):
	def get(self):
		self.response.out.write('abc')
		checker = APIChecker()
		html_content = checker.addAPIForm()
		self.response.out.write(html_content)

class TrackAPIChangesByID(webapp.RequestHandler):
	def get(self):
		api_id = int(self.request.get('id'))
		taskqueue.add(url='/apimonitor/track/id', params={ "id": api_id})
		
	def post(self):
		api_id = int(self.request.get('id'))
		checker = APIChecker()
		data = checker.trackAPIChangeByID(api_id)
		self.response.out.write(data)
		

class TrackAPIChanges(webapp.RequestHandler):
	def get(self):
		taskqueue.add(url='/apimonitor/track')
		
	def post(self):
		checker = APIChecker()
		#data = checker.trackAPIChanges()
		#self.response.out.write(data)
		apis = checker.getTrackedAPIs()
		for api in apis:
			api_id = int(api.key().id())
			taskqueue.add(url='/apimonitor/track/id', params={ "id": api_id})
		
	
def main():
	application = webapp.WSGIApplication([
	  ('/apimonitor/addapi', CheckAPI),
	  ('/apimonitor/add', AddAPITracking),
	  ('/apimonitor/track', TrackAPIChanges),
	  ('/apimonitor/track/id', TrackAPIChangesByID),
      ], debug=True)
	util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
