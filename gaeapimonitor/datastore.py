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

from google.appengine.ext import db

class APIStorage(db.Model):
	api_id = db.StringProperty()
	url = db.StringProperty()
	form_fields = db.StringProperty()
	http_method = db.StringProperty()
	has_changed = db.BooleanProperty(default=False)
	min_percentage_changed = db.FloatProperty(default=0.0)
	last_valid_response = db.TextProperty()
	valid_json = db.BooleanProperty(default=True)
	is_down = db.BooleanProperty(default=True)
	time_threshold = db.FloatProperty(default=0.0)
	twitter_user = db.StringProperty()
	alert_type = db.IntegerProperty() # 0 for status, 1 for DM
	label = db.StringProperty()
	update_time = db.DateTimeProperty(auto_now=True)
	expiry_time = db.IntegerProperty(default=0)
	last_status_code = db.IntegerProperty(default=200)
	last_valid_response_before_changes = db.TextProperty()
