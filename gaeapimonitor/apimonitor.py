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
import gaeapimonitor.config
from gaeapimonitor.googleurlshortener import Googl
import logging

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
		min_percentage_changed = self.request.get('min_percentage_changed')
		if min_percentage_changed=='':
			min_percentage_changed = None;
		else:
			min_percentage_changed = float(self.request.get('min_percentage_changed'))
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
			alert_type = 1
		else:
			alert_type = int(alert_type_txt)
			
		expiry_time = int(self.request.get('expiry_time'))
			
		label = self.request.get('label')
		
		parameters = {}
		if form_fields!='':
			parameters = simplejson.loads(form_fields)	
		checker = APIChecker()
		
		data = checker.checkAPI(url, parameters, http_method, twitter_user, label, expiry_time=expiry_time, alert_type=alert_type, has_changed=has_changed, time_threshold=time_threshold, is_down=is_down, valid_json=valid_json, min_percentage_changed=min_percentage_changed, n_trial=1)
		json_data = simplejson.dumps(data)
		self.response.out.write(json_data)

class AddAPITracking(webapp.RequestHandler):
	def get(self):
		checker = APIChecker()
		html_content = checker.addAPIForm()
		self.response.out.write(html_content)

class TrackAPIChangesByID(webapp.RequestHandler):
	
	def track(self):
		api_id = int(self.request.get('id'))
		n_trial = int(self.request.get('n_trial'))
		checker = APIChecker()
		data = checker.trackAPIChangeByID(api_id, n_trial)
		self.response.out.write(data)
	
	def get(self):
		self.track()
		#api_id = int(self.request.get('id'))
		#taskqueue.add(url='/apimonitor/track/id', params={ "id": api_id})
		
	def post(self):
		self.track()
	
class RemoveAPIByID(webapp.RequestHandler):
	def get(self):
		api_id = self.request.get('id')
		checker = APIChecker()
		checker.removeAPIByID(api_id)

class CheckAPIChangesByID(webapp.RequestHandler):
	def get(self):
		api_id = self.request.get('id')
		checker = APIChecker()
		api, response, response_before_changes, status_code, changes = checker.checkAPIChangeByID(api_id)
		
		if response==0:
			response = ""
		
		if api==-1:
			self.response.out.write("this alert does not exists")
		else:	
			htmlContent = "<html><head><title>%s</title></head>" % api.url
			htmlContent += "<body spacing='0' marginwidth='0' marginheight='0' >"
			htmlContent += """<SCRIPT TYPE=\"text/javascript\">
						<!--
						function removeAlert()
						{
							var response = confirm(\"Are you sure you want to remove this alert?\")
							if (response)
							{
								window.location = "remove?id=%s";
							}
						}
						//-->
						</SCRIPT>""" % api_id
			#changed_text = ''
			#if changes!=-1:
			#	if changes.has_key('added'):
			#		added = changes['added']
			#		changed_text += '<br><b>ADDED</b>'
			#		for item in added:
			#			changed_text += '<br>%s' % item
			#	if changes.has_key('removed'):
			#		removed = changes['removed']
			#		changed_text += '<br><b>REMOVED</b>'
			#		for item in removed:
			#			changed_text += '<br>%s' % item
			
			htmlContent += "<form><table width='100%%' border='0' cellspacing=0><tr bgcolor=#CCCCCC height=35 ><td><input type='button' value='remove alert' onClick='removeAlert()'/></td></tr>"
			htmlContent += "<tr bgcolor=#CCCCCC height=1><td >%s</td></tr><tr bgcolor=#BBBBBB height=1><td ></td></tr></table></form>" % changes
			
			#htmlContent += "<iframe src='%s' width='100%%' height ='100%%' frameborder=0 scrolling='auto'>" % "http://www.google.com"
			#htmlContent += "<p>Your browser does not support iframes.</p>"
			#htmlContent += "</iframe>"
			htmlContent += "%s" % response
			if response_before_changes is not None:
				htmlContent += "<form><table width='100%%' border='0' cellspacing=0><tr bgcolor=#CCCCCC height=35 ><td>Before changes</td></tr>"
				htmlContent += "</table></form>"
				htmlContent += "%s" % response_before_changes
			htmlContent += "</body>"
			htmlContent += "</html>"
		
			self.response.out.write(htmlContent)

class TrackAPIChanges(webapp.RequestHandler):
	def get(self):
		taskqueue.add(url=gaeapimonitor.config.url_track)
		
	def post(self):
		checker = APIChecker()
		#data = checker.trackAPIChanges()
		#self.response.out.write(data)
		apis = checker.getTrackedAPIs()
		for api in apis:
			if api.should_monitor:
				api_id = int(api.key().id())
				taskqueue.add(url=gaeapimonitor.config.url_track_id, params={ "id": api_id, "n_trial": 1})

class Test(webapp.RequestHandler):
	def get(self):
		#shortener = Googl(gaeapimonitor.config.googl_apikey)
		#url = shortener.shorten('http://honcheng-test.appspot.com/apimonitor/check?id=da60b0629e84a530cf79ce84c6fa18b8&test=1')
		url = ShortUrl(response)
		self.response.out.write("Test %s" % url)	
	
def main():
	application = webapp.WSGIApplication([
	  ('/apimonitor/test', Test),
	  (gaeapimonitor.config.url_addapi, CheckAPI),
	  (gaeapimonitor.config.url_add, AddAPITracking),
	  (gaeapimonitor.config.url_track, TrackAPIChanges),
	  (gaeapimonitor.config.url_track_id, TrackAPIChangesByID),
	  (gaeapimonitor.config.url_check, CheckAPIChangesByID),
	  (gaeapimonitor.config.url_remove, RemoveAPIByID),
      ], debug=True)
	util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
