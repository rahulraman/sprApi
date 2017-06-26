import sys
import os.path

from google.appengine.ext import vendor

# Add any libraries installed in the "lib" folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# Add the vendor reference
vendor.add('lib')

remoteapi_CUSTOM_ENVIRONMENT_AUTHENTICATION = ('HTTP_X_APPENGINE_INBOUND_APPID',['spr-evolved','spr-reevolved'])
