import os
import requests
from flask import Flask, request, redirect, session, url_for, render_template
from flask_bootstrap import Bootstrap
from requests_oauthlib import OAuth2Session

app = Flask(__name__)
Bootstrap(app)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'supersecretkey'
# Flag for development. Avoids errors if the OAuth redirect uri is not https.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client_id = 'YOUR_CLIENT_ID'
client_secret = 'YOUR_CLIENT_SECRET'
authorize_url = 'https://login.ingest.io/authorize'
token_url = 'https://login.ingest.io/token'


# -- functions --
def get_videos():
    """ Returns a list of 'published' and 'scheduled' videos.
    """
    with requests.Session() as sess:
        sess.headers['Authorization'] = 'Bearer {}'.format(session['token'])
        sess.headers['Accept'] = 'application/vnd.ingest.v1+json'
        sess.params['status'] = 'published,scheduled'

    resp = sess.get('https://api.ingest.io/videos')
    if resp.ok:
        return resp.json()
    resp.raise_for_status()


def get_video(id):
    """ Returns a video by ID
    """
    with requests.Session() as sess:
        sess.headers['Authorization'] = 'Bearer {}'.format(session['token'])
        sess.headers['Accept'] = 'application/vnd.ingest.v1+json'

    url = 'https://api.ingest.io/videos/{}'.format(id)
    resp = sess.get(url)
    if resp.ok:
        return resp.json()
    resp.raise_for_status()


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


def logout_user():
    """ Clears session and revokes user token.
    """
    session.pop('logged_in', None)
    with requests.Session() as sess:
        sess.headers['Authorization'] = 'Bearer {}'.format(session['token'])
        sess.headers['Accept'] = 'application/vnd.ingest.v1+json'

    resp = sess.delete('https://api.ingest.io/users/me/revoke')
    if resp.ok:
        session.pop('oauth_token', None)
        session.pop('token', None)
        session.pop('oauth_state', None)
    resp.raise_for_status()


# --- routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route("/login")
def login():
    # requests authentication with a 'read_videos' scope because that's all
    # we need for now.
    ingest = OAuth2Session(client_id, scope='read_videos')
    authorization_url, state = ingest.authorization_url(authorize_url)

    # State is used to prevent CSRF, when getting a token on OAuth2 step 2
    session['oauth_state'] = state
    return redirect(authorization_url)


@app.route("/oauth/ingest", methods=['GET'])
def callback():
    ingest = OAuth2Session(client_id, state=session['oauth_state'])
    token = ingest.fetch_token(token_url, client_secret=client_secret,
                               authorization_response=request.url)

    session['oauth_token'] = token
    session['token'] = token['access_token']
    session['logged_in'] = True

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    if session['token']:
        logout_user()
    return redirect(url_for('index'))


@app.route('/videos')
def show_videos():
    if session['logged_in']:
        videos = get_videos()
        return render_template('videos.html', videos=videos)
    else:
        return redirect(url_for('index'))


@app.route('/videos/<id>')
def show_video(id):
    if session['logged_in']:
        video = get_video(id)
        play_url = get_video_play_url(video)
        return render_template('video.html', video=video, play_url=play_url)
    else:
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()
