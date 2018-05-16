"""File server"""
from flask import Flask, request, Response, json
from http import HTTPStatus
import uuid

app = Flask(__name__)

class DataStore:
    """simple in-memory filestore"""
    def __init__(self):
        self.users = {}         # username => password dictionary
        self.user_files = {}    # username => filename => file contents dictionary
        self.sessions = {}      # sessionId => username dictionary

    def get_user_creds(self, user):
        return self.users.get(user, None)

    def put_user_credentials(self, user, cred):
        self.users[user] = cred
        self.user_files[user] = {} # initialize files dictionary for the user when the user is registered

    def get_user_file(self, user, filename):
        try:
            return self.user_files[user][filename]
        except:
            return None

    def put_user_file(self, user, filename, data):
        self.user_files[user][filename] = data

    def delete_user_file(self, user, filename):
        try:
            del self.user_files[user][filename]
            return True
        except:
            return False

    def get_all_file_names(self, user):
        fileNames = []
        for fileName in self.user_files[user]:
            fileNames.append(fileName)
        return fileNames

    def get_session_user(self, session):
        return self.sessions.get(session, None)

    def put_session_user(self, session, user):
        self.sessions[session] = user

db = DataStore()

@app.route('/register', methods=['POST'])
def register():
    if not request.is_json:
        return('', HTTPStatus.BAD_REQUEST)

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if db.get_user_creds(username) is not None:
        data = {
                    'error'  : 'Username already exists.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.BAD_REQUEST, mimetype='application/json')
        return resp
    elif username is not None and \
         password is not None and \
         len(username) > 3 and len(username) < 20 and \
         str(username).isalnum() and \
         len(password) >= 8:
        db.put_user_credentials(username, password)
        resp = Response(status=HTTPStatus.NO_CONTENT)
        return resp
    else:
        data = {
                    'error'  : 'Invalid username/password. '
                               'Usernames must be at least 3 characters and no more than 20, and may only contain alphanumeric characters. '
                               'Passwords must be at least 8 characters.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.BAD_REQUEST, mimetype='application/json')
        return resp

@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return('', HTTPStatus.BAD_REQUEST)

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    storedCreds = db.get_user_creds(username)

    if storedCreds is None or storedCreds != password:
        data = {
                    'error'  : 'Invalid username/password.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.FORBIDDEN, mimetype='application/json')
        return resp
    else:
        sessionId = str(uuid.uuid1()) # TBD: there could be a better way to generate session IDs
        db.put_session_user(sessionId, username)
        data = {
                    'token'  : sessionId
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.OK, mimetype='application/json')
        return resp

@app.route('/files/<filename>', methods=['PUT'])
def createAFile(filename):
    xSession = request.headers.get('X-Session', None)

    if xSession is None:
        data = {
                    'error'  : 'X-Session required header is missing.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.BAD_REQUEST, mimetype='application/json')
        return resp

    fileContents = request.data

    user = db.get_session_user(xSession)
    if user is None:
        data = {
                    'error'  : 'Invalid session.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.FORBIDDEN, mimetype='application/json')
        return resp

    db.put_user_file(user, filename, fileContents)

    resp = Response(status=HTTPStatus.CREATED, headers={'Location': '/files/'+filename})
    return resp

@app.route('/files/<filename>', methods=['GET'])
def getAFile(filename):
    xSession = request.headers.get('X-Session', None)

    if xSession is None:
        data = {
                    'error'  : 'X-Session required header is missing.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.BAD_REQUEST, mimetype='application/json')
        return resp

    user = db.get_session_user(xSession)
    if user is None:
        data = {
                    'error'  : 'Invalid session.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.FORBIDDEN, mimetype='application/json')
        return resp

    fileContents = db.get_user_file(user, filename)
    if fileContents is None:
        data = {
                    'error'  : 'Invalid filename.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.NOT_FOUND, mimetype='application/json')
        return resp

    resp = Response(fileContents, status=HTTPStatus.OK, mimetype='application/octet-stream')
    return resp

@app.route('/files/<filename>', methods=['DELETE'])
def deleteAFile(filename):
    xSession = request.headers.get('X-Session', None)

    if xSession is None:
        data = {
                    'error'  : 'X-Session required header is missing.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.BAD_REQUEST, mimetype='application/json')
        return resp

    user = db.get_session_user(xSession)
    if user is None:
        data = {
                    'error'  : 'Invalid session.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.FORBIDDEN, mimetype='application/json')
        return resp

    if db.delete_user_file(user, filename):
        resp = Response(status=HTTPStatus.NO_CONTENT)
        return resp
    else:
        data = {
                    'error'  : 'Invalid filename.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.NOT_FOUND, mimetype='application/json')
        return resp

@app.route('/files', methods=['GET'])
def getAllFiles():
    xSession = request.headers.get('X-Session', None)

    if xSession is None:
        data = {
                    'error'  : 'X-Session required header is missing.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.BAD_REQUEST, mimetype='application/json')
        return resp

    user = db.get_session_user(xSession)
    if user is None:
        data = {
                    'error'  : 'Invalid session.'
                }
        js = json.dumps(data)
        resp = Response(js, status=HTTPStatus.FORBIDDEN, mimetype='application/json')
        return resp

    fileNames = db.get_all_file_names(user)
    js = json.dumps(fileNames)
    resp = Response(js, status=HTTPStatus.OK, mimetype='application/json')
    return resp

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)  