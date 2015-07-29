username = 'USER'
password = 'PASSWORD'
USERS = {username:password}
GROUPS = {}

def groupfinder(userid, request):
        return GROUPS.get(userid, [])

def canView(loggedin, permission, channelFollowing, username):
    if permission == "public":
        return True
    if permission == "me":
       loggedin = loggedin.lower()
       if loggedin == username:
            return True
    if permission == "following":
        followers = channelFollowing.split()
        if loggedin in followers:
            return True
        elif loggedin == username:
            return True
        else:
            return False
   
def canAsk(loggedin, permission, channelFollowing, username):
    if permission == "public":
        return True
    if permission == "me":
       loggedin = loggedin.lower()
       if loggedin == username:
            return True
    if permission == "following":
        followers = channelFollowing.split()
        if loggedin in followers:
            return True
        elif loggedin == username:
            return True
        else:
            return False