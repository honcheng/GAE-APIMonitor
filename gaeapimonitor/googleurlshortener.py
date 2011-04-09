from django.utils import simplejson
import urllib
from google.appengine.api import urlfetch

class Googl():  
	def __init__(self, apikey):  
		self.apikey = apikey

	def shorten(self,longUrl):  
		url = "https://www.googleapis.com/urlshortener/v1/url?key=%s" % self.apikey  
		form_fields = {}
		form_fields['longUrl'] = longUrl
		form_data = simplejson.dumps(form_fields)
		result = urlfetch.fetch(url=url,
	                        payload=form_data,
	                        method=urlfetch.POST,
	                        headers={'Content-Type': 'application/json'})
 
		json = simplejson.loads(result.content)  
		return json