#Media processing functions (Picture and Video) for answer.tv
#detect operating system to avoid PIL Import error
import os
system = os.name
if system == "nt":
    import Image, ImageOps
elif system == "posix":
    from PIL import Image, ImageOps
import boto
from boto.s3.key import Key
import boto.s3.connection
from boto.s3.connection import Location
from boto.s3.connection import S3Connection
import uuid
import urllib2 as urllib
import cStringIO
import hashlib
import re
import socket
import string
import random
import platform

try:
    import simplejson as json
except ImportError:
    import json


import ssl

"""
_old_match_hostname = ssl.match_hostname

def _new_match_hostname(cert, hostname):
    if hostname.endswith('.s3.amazonaws.com'):
        pos = hostname.find('.s3.amazonaws.com')
        hostname = hostname[:pos].replace('.', '') + hostname[pos:]
    return _old_match_hostname(cert, hostname)

ssl.match_hostname = _new_match_hostname

#Amazon web services configuration (via boto module)
s3 = S3Connection("USR",
                     "KEY")
b = s3.get_bucket('Bucket')
"""

#verify the image being uploaded is actually an image file
def verifyFile(Profilepic):
    Profilepic.seek(0, 2) # Seek to the end of the file.
    filesize = Profilepic.tell() # Get the position of EOF.
    Profilepic.seek(0) # Reset the file position to the beginning. 
    if filesize > 2097152:
        status = "File size it too large. please select a file smaller than 2mb."
    elif filesize < 3072:
        status = "File size it too small. please select a file larger than 3kb." 
    else:
        status = "True"    
    return status 

#verify the background / background pic image being uploaded is actually
#an image file
def verifyBkgFile(Bkgpic):
    Bkgpic.seek(0, 2) # Seek to the end of the file.
    filesize = Bkgpic.tell() # Get the position of EOF.
    Bkgpic.seek(0) # Reset the file position to the beginning. 
    if filesize > 2097152:
        status = "File size it too large. please select a file smaller than 2mb."
    elif filesize < 1010:
        status = "File size it too small. please select a file larger than 1kb." 
    else:
        status = "True"    
    return status 

#trim the profile img and upload to s3 bucket
def uploadImg(Profilepic, oldname, newname):
    try:
        Profilepicname = newname
        'Save tmp file'
        tmp_filepath = "atv/tmp/profile/" + Profilepicname
        tmp_output_file = open(tmp_filepath, 'wb')
        Profilepic.seek(0)
        while True:
            data = Profilepic.read(2<<16)
            if not data:
                break
            tmp_output_file.write(data)
        tmp_output_file.close()
        'resize'
        size = 200, 200
        im = Image.open(tmp_filepath)
        im = ImageOps.fit(im, size, Image.ANTIALIAS)
        im.save(tmp_filepath, "PNG")
        'Save img to S3'
        k = Key(b)
        k.key = "profileimg/" + Profilepicname 
        k.set_contents_from_filename(tmp_filepath, policy='public-read')
        status = ""
        'resize mini'
        size = 25, 25
        im = Image.open(tmp_filepath)
        im = ImageOps.fit(im, size, Image.ANTIALIAS)
        im.save(tmp_filepath, "PNG")
        'Save mini img to S3'
        k = Key(b)
        k.key = "miniprofileimg/" + Profilepicname
        k.set_contents_from_filename(tmp_filepath, policy='public-read')
        'delete tmp file'
        os.remove(tmp_filepath)      
        status = ""
        'delete old img files'
        k = Key(b)
        k.key = "profileimg/" + oldname
        b.delete_key(k)
        k = Key(b)
        k.key = "miniprofileimg/" + oldname
        b.delete_key(k)
        return status
    except:
        status = """File could not be uploaded - please check the file extension
                 and try again."""
        return status

#upload the bkg img to s3 bucket
def uploadBkgImg(Bkgpic, oldname, newname):
    try:
        Bkgpicname  = newname
        'Save tmp file'
        tmp_filepath = "atv/tmp/bkg/" + Bkgpicname
        tmp_output_file = open(tmp_filepath, 'wb')
        Bkgpic.seek(0)
        while True:
            data = Bkgpic.read(2<<16)
            if not data:
                break
            tmp_output_file.write(data)
        tmp_output_file.close()
        'resize'
        size = 942, 225
        im = Image.open(tmp_filepath)
        im = ImageOps.fit(im, size, Image.ANTIALIAS)
        im.save(tmp_filepath, "PNG")
        'Save main img to S3'
        k = Key(b)
        k.key = "permbks/" + Bkgpicname
        k.set_contents_from_filename(tmp_filepath, policy='public-read')
        'resize mini'
        size = 230, 55
        im = Image.open(tmp_filepath)
        im = ImageOps.fit(im, size, Image.ANTIALIAS)
        im.save(tmp_filepath, "PNG")
        'Save main mini img to S3'
        k = Key(b)
        k.key = "minipermbks/" + Bkgpicname
        k.set_contents_from_filename(tmp_filepath, policy='public-read')
        'delete tmp file'
        os.remove(tmp_filepath)
        status = ""
        'delete old img files'
        do_not_delete_list=["birdbox.png","blueflower.png","cars.png","cartographer.png","default.png","elastoplast.png",
                            "fireheart.png","food.png","glammer.png","greyfloral.png","knittednetting.png","molten.png",
                            "norwegianrose.png","pineapple.png","purplecrown.png","reddrop.png","redflower.png","retroleaf.png",
                            "seamless.png","shattered.png","stardust.png","stripes.png","whitebrick.png","wood.png"]
        if oldname in do_not_delete_list:
            pass
        else:
            k = Key(b)
            k.key = "permbks/" + oldname
            b.delete_key(k)
            k = Key(b)
            k.key = "minipermbks/" + oldname
            b.delete_key(k)
            return status
    except:
        status = """File could not be uploaded - please check the file extension
                 and try again."""
        return status


def createpics(user):
    try:
        users = image_name_generator(35) + ".png"
        profile_filepath = "atv/tmp/newimgs/profdefault.png"
        mini_profile_filepath = "atv/tmp/newimgs/miniprofdefault.png"
        bk_filepath = "atv/tmp/newimgs/bkgdefault.png"
        bkimg_filepath = "atv/tmp/newimgs/bkgimgdefault.png"
        k = Key(b)
        k.key = "profileimg/" + users
        k.set_contents_from_filename(profile_filepath, policy='public-read')
        k = Key(b)
        k.key = "miniprofileimg/" + users
        k.set_contents_from_filename(mini_profile_filepath, policy='public-read')
        k = Key(b)
        k.key = "permbks/" + users
        k.set_contents_from_filename(bk_filepath, policy='public-read')
        k = Key(b)
        k.key = "minipermbks/" + users
        k.set_contents_from_filename(bkimg_filepath, policy='public-read')
        return users
    except:
        pass

def image_name_generator(size=6, chars=string.ascii_uppercase + string.digits):
            return ''.join(random.choice(chars) for x in range(size))

