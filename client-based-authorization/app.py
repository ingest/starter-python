from flask import Flask, render_template
from flask_bootstrap import Bootstrap
import requests

app = Flask(__name__)
Bootstrap(app)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'supersecretkey'

client_id = 'YOUR_CLIENT_ID'
client_secret = 'YOUR_CLIENT_SECRET'
token_url = 'https://login.ingest.io/token'


# --- Helper classes for Ingest API usage ---

class BearerTokenAuth(requests.auth.AuthBase):
    """ Extends requests.auth.AuthBase to use Bearer Token for
        authentication headers
    """
    def __init__(self, access_token):
        self._access_token = access_token

    def __call__(self, request):
        request.headers['Authorization'] = 'Bearer {}'.format(self._access_token)
        return request


class IngestClient(requests.Session):

    def __init__(self, client_id, client_secret, *args, **kwargs):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = self._authenticate()
        super(IngestClient, self).__init__(*args, **kwargs)

    def _authenticate(self):
        resp = requests.post(token_url, params={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'read_videos'
        })
        if resp.ok:
            return resp.json()['access_token']
        # TODO: handle authentication error

    def _request(self, *args, **kwargs):
        kwargs['auth'] = BearerTokenAuth(self._access_token)
        kwargs['headers'] = {
            'Accept': 'application/vnd.ingest.v1+json'
        }
        return super(IngestClient, self).request(*args, **kwargs)

    def request(self, *args, **kwargs):
        try:
            response = self._request(*args, **kwargs)
            if response.status_code != 401:
                return response
            # TODO: If Unauthorized, refresh token
        except RequestError as error:
            return error.response


class RequestError(Exception):

    def __init__(self, message, response):
        super(RequestError, self).__init__(message)
        self.response = response


# --- IngestClient instance
ingest = IngestClient(client_id=client_id, client_secret=client_secret)


# --- functions ---
def get_video_play_url(video):
    """ Find playback_url for video target named 'high', in case there isn't
        one, returns the first target on the list. Change this to the specific
        target name you wish to play.
    """
    if len(video['targets']) > 0:
        target = next((target for target in video['targets']
                      if target['name'] == 'high'), video['targets'][0])
        return target['playback_url']
    else:
        return ''


# --- routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/videos')
def show_videos():
    params = {'status': 'published,scheduled'}
    resp = ingest.request('GET', 'https://api.ingest.io/videos', params=params)
    if resp.ok:
        videos = resp.json()
        return render_template('videos.html', videos=videos)
    resp.raise_for_status
    return 'Request failed - ingest status code: {}'.format(resp.status_code)


@app.route('/videos/<id>')
def show_video(id):
    resp = ingest.request('GET', 'https://api.ingest.io/videos/{}'.format(id))
    if resp.ok:
        video = resp.json()
        play_url = get_video_play_url(video)
        return render_template('video.html', video=video, play_url=play_url)
    resp.raise_for_status
    return 'Request failed - ingest status code: {}'.format(resp.status_code)


if __name__ == '__main__':
    app.run()
