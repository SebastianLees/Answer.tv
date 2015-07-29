from shutil import copyfile

def profileImgCopy(username):
    shadowman = 'static/profileimg/shadowman.png'
    firstProfileImg = 'static/profileimg/'
    copyfile(shadowman, firstProfileImg + username)



