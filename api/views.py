import json
from django.views.generic import View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from google.oauth2 import id_token
from google.auth.transport import requests
from .models import Profile

@method_decorator(csrf_exempt, name='dispatch')
class Authenticate(View):

    def post(self, request, **kwargs):

        responseBody = json.loads(request.body)

        idinfo = None

        if responseBody.get('token'):
            token = responseBody['token']

            try:
                idinfo = id_token.verify_oauth2_token(
                    token, requests.Request(),
                    '689997766659-hobsdn1iaid1sdc4r4v3pq494nsq8bn7.apps.googleusercontent.com'
                )

                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise ValueError('Wrong issuer.')

                userid = idinfo['sub']
                name = idinfo['name']
                email = idinfo['email']

                try:
                    Profile.objects.get(goodle_id=userid)
                except Profile.DoesNotExist:
                    new_profile = Profile(name=name, email=email, goodle_id=userid)
                    new_profile.save()

            except ValueError:
                pass
    
        if idinfo is None:
            response = HttpResponse()
            response.status_code = 401
        else:
            response = HttpResponse(json.dumps({'token': token}))
            response.status_code = 200

        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        response["Access-Control-Max-Age"] = "1000"
        response["Access-Control-Allow-Headers"] = "*"
        return response
