#Imports
from pyramid.response import Response
import datetime 
import transaction
from slugify import slugify
import os
import mailer
import time
from recaptcha import RecaptchaClient
import recaptcha
import string
import random
from misc import profileImgCopy
import media
import boto
from boto.s3.key import Key
import sqlalchemy as sa
from sqlalchemy_searchable import search
import security
import json
from datetime import datetime
import time 
import panda
from .security import USERS
from webhelpers.paginate import PageURL_WebOb, Page
from sqlalchemy.exc import DBAPIError
from passlib.hash import sha256_crypt
from sqlalchemy import and_
from random import randint

#Security / Login
from pyramid.security import (
    remember,
    forget,
    authenticated_userid,
    )

from pyramid.view import (
    view_config,
    forbidden_view_config,
    )

#Front end exceptions
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    HTTPInternalServerError,
    Response
    )

#Answer.tv SQAlchemy database models (as decribed in models.py)
from .models import (
    DBSession,
    MyModel,
    Channel,
    Question,
    Answer,
    TempChannel,
    TempPassword,
    TempEmail,
    Qvote,
    func,
    Images,
    )

#Amazon web services configuration (via boto module)
s3 = boto.connect_s3("USR",
                     "PASSWORD")

b = s3.get_bucket('BUCKET')

#Pandastream (video transcoder) configuration
panda = panda.Panda(
                    api_host='URL',
                    cloud_id='ID',
                    access_key='KEY',
                    secret_key='SECRET',
                    api_port=443, # Enables https
                    )

#Profile notifications (notification bar at the top of main answer.tv pages).
def notify(notificationlist):
    if notificationlist == None:
        return None 
    else:
        notifications = list(notificationlist)
        notificationsTranslate = []
        if "1" in notifications:
            notificationsTranslate.append("Welcome to answer.tv! Your profile is looking a little empty. Click the cog icon in the top right hand corner to add your info.")
        if "2" in notifications:
            notificationsTranslate.append("We have added a few people to your following list to help get you started.")
        if "3" in notifications:
            notificationsTranslate.append("notification3")
        if "4" in notifications:
            notificationsTranslate.append("notification4")
        if "5" in notifications:
            notificationsTranslate.append("notifiction5")
        return notificationsTranslate


#404 error page view
@view_config(context=HTTPNotFound, renderer='atv:templates/404.pt')
def fourofour_not_found(request):
        request.response.status = 404
        logged_in = authenticated_userid(request)
        if logged_in:
            logged_in_alias = logged_in.lower()
        else:
            logged_in_alias = ''
        currenturl= request.url
        return{'logged_in':logged_in, 'logged_in_alias':logged_in_alias,
               'currenturl':currenturl}

#500 error page view
#@view_config(context=Exception, renderer='atv:templates/500.pt')
#def not_found(request):
#       request.response.status = 500
#       logged_in = authenticated_userid(request)
#       logged_in_alias = ""
#       if logged_in:
#           logged_in_alias = logged_in.lower()
#       currenturl= request.url
#       return{'logged_in':logged_in, 'logged_in_alias':logged_in_alias,
#              'currenturl':currenturl}


#Default home page view
@view_config(route_name='home', renderer='templates/explore.pt', permission='view')
def home(request):
    #try:
        logged_in = authenticated_userid(request)
        if logged_in:
            return HTTPFound(location = request.route_url('stream'))
        logged_in_alias='' 
        page = int(request.params.get('page', 1)) 
        trendinglist = Question.get_explore_trending(request,
                                        logged_in_alias, page)
        latestlist = Question.get_explore_latest(request,
                                        logged_in_alias, page)
        ourpicklist = Question.get_explore_ourpicks(request,
                                        logged_in_alias, page)
        latestchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc(Channel.created)).limit(20)
        
        hotchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc((Channel.akarma * 10) + Channel.qkarma)).limit(20)
        
        return {
                'trendinglist':trendinglist,
                'latestlist':latestlist,
                'ourpicklist':ourpicklist,
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias,
                'latestchannels':latestchannels,
                'hotchannels':hotchannels,  
                }
    #except DBAPIError:
    #    raise Exception()


#Login page view    
@view_config(route_name='login', renderer='templates/login.pt',
             permission='view')
@view_config(route_name='loginb', renderer='templates/login.pt',
             permission='view')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    try:
        login_url = request.route_url('login')
        referrer = request.url
        now = int(round(time.time()/60/60))
        logged_in = authenticated_userid(request)
        currenturl = '/'
        if logged_in:
            return HTTPFound(location = request.route_url('home'))
        if referrer == login_url:
            referrer = '/' # never use the login form itself as came_from
        came_from = request.params.get('came_from', referrer)
        url = request.application_url + '/login',
        headers= ''
        login = ''
        password = ''
        message = ''
        if 'form.submitted' in request.params:
            login = request.params['login']
            login_lower = login.lower()
            password = request.params['password']
            if 'rememberbox' in request.params:
                headers = remember(request, login, max_age='31536000000')
            else:
                headers = remember(request, login)
            usercheck = DBSession.query(Channel).filter_by(usralias=login_lower)\
                        .first()
            if usercheck:
                verified = sha256_crypt.verify(password, usercheck.password)
                if verified:
                    return HTTPFound(location = came_from,
                                     headers = headers)
                    
            message = 'login or password invalid'
        return {'message':message, 'currenturl':currenturl,
                'came_from':came_from, 'url':url, 'login':login,
                'password':password, 'logged_in':logged_in, 'now':now}
    except DBAPIError:
        raise Exception()

#Logout view    
@view_config(route_name='logout')
@view_config(route_name='logoutb')
def logout(request):
    try:
        headers = forget(request)
        return HTTPFound(location = request.route_url('home'),
                         headers = headers)
    except DBAPIError:
        raise Exception()
  
#Pandrastream upload view    
@view_config(route_name='panda', permission='view')
def authorize_upload(request):
                params = json.loads(request.POST['payload'])
                upload = panda.post("/videos/upload.json", {
                  "file_name": params['filename'],
                  "file_size": params['filesize'],
                  "profiles": "h264",
                })
                
                auth = {"upload_url": json.loads(upload)["location"]}
                return Response(json.dumps(auth))

#Generic page view - used for most static pages.
@view_config(route_name='privacy', renderer='atv:templates/privacy.pt',
             permission='view')
@view_config(route_name='terms', renderer='atv:templates/terms.pt',
             permission='view')
@view_config(route_name='blog', renderer='atv:templates/blog.pt',
             permission='view')
@view_config(route_name='copyright', renderer='atv:templates/copyright.pt',
             permission='view')
@view_config(route_name='privacyb', renderer='atv:templates/privacy.pt',
             permission='view')
@view_config(route_name='termsb', renderer='atv:templates/terms.pt', 
             permission='view')
@view_config(route_name='blogb', renderer='atv:templates/blog.pt', 
             permission='view')
@view_config(route_name='copyrightb', renderer='atv:templates/copyright.pt', 
             permission='view')
@view_config(route_name='denied', renderer='atv:templates/denied.pt', 
             permission='view')
def generic_view(request):
    try:
        logged_in = authenticated_userid(request)
        now = int(round(time.time()/60/60))
        if logged_in != None:
            logged_in_alias = logged_in.lower()
        else:
            logged_in_alias = ""
        referrer = request.url
        currenturl= '/'
        came_from = request.params.get('came_from', referrer)
        return {'logged_in':logged_in, 'came_from':came_from,
                'currenturl':currenturl, 'logged_in_alias':logged_in_alias,
                'now':now}
    except DBAPIError:
        raise Exception()

#Youtube and video upload view
@view_config(route_name='answer', permission='view')
def answer(request):
    try:
        logged_in = authenticated_userid(request)
        errormsg=''
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            if request.method == 'POST':
                    akarma = 1
                    unixage = int(round(time.time()/60/60)) 
                    answeredby = request.params['answerer']
                    channel = request.params['answering']
                    channel = channel.lower()
                    questionalias = request.params['questionalias']
                    question = request.params['question']
                    type = request.params['type']
                    if type == "embed":
                        vidurl = request.params['vidurl']
                        with transaction.manager:
                             answer = Answer(akarma = akarma,
                                             answeredby = answeredby,
                                             questiontext = question,
                                             question = questionalias,
                                             embedcode = vidurl, 
                                             channel = channel, 
                                             unixage = unixage)
                             
                             DBSession.add(answer)
                             answerStatus(questionalias, True)
                             akarmaStatus(logged_in_alias, 'up')
                    elif type == "upload":
                        vidurl = request.params['vidurl']
                        vidurl2 = "videos/" + vidurl + "/encodings.json"
                        videopath = panda.get(vidurl2)
                        videopath = videopath[8:40]
                        print videopath
                        videopath = "http://video.answer.tv/" + videopath + ".mp4"
                        with transaction.manager:
                             answer = Answer(akarma = akarma,
                                             answeredby = answeredby, 
                                             questiontext = question, 
                                             question = questionalias, 
                                             embedcode = videopath, 
                                             channel = channel, 
                                             unixage = unixage)
                             
                             DBSession.add(answer)
                             answerStatus(questionalias, True)
                             akarmaStatus(logged_in_alias, 'up')
                    else:
                        pass

    except DBAPIError:
        raise Exception()

@view_config(route_name='delete', permission='view')
def delete(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            if request.method == 'POST':
                    alias = request.params['alias']
                    questiondata = DBSession.query(Question).filter_by\
                                   (alias = alias).first()
                                   
                    askedby = questiondata.askedbyalias
                    answeredby = questiondata.askedtoalias
                    qkarma = questiondata.qkarma
                    if logged_in_alias == askedby:
                        with transaction.manager:
                            DBSession.delete(questiondata)
                            userdata = DBSession.query(Channel).filter_by\
                                       (usralias = askedby).first()
                                      
                            userdata.qkarma = userdata.qkarma - qkarma
                            transaction.commit()
                    elif logged_in_alias == answeredby:
                        with transaction.manager:
                            DBSession.delete(questiondata)
                            userdata = DBSession.query(Channel).filter_by\
                                       (usralias = answeredby).first()
                                      
                            userdata.qkarma = userdata.qkarma - qkarma
                            transaction.commit()
                            
    except DBAPIError:
        raise Exception()

#Delete answer view
@view_config(route_name='deleteanswer', permission='view')
def deleteanswer(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            if request.method == 'POST':
                    alias = request.params['question']
                    alias = slugify(alias)
                    answerdata = DBSession.query(Answer).filter_by\
                                (question = alias)\
                                .filter_by(channel = logged_in_alias).first()
                    with transaction.manager:
                        DBSession.delete(answerdata)
                        userdata = DBSession.query(Channel).\
                                    filter_by(usralias = logged_in_alias).first()
                                       
                        userdata.akarma = userdata.akarma - 1
                        questiondata = DBSession.query(Question)\
                                       .filter_by(alias = alias)\
                                       .filter_by(askedtoalias = logged_in_alias).first()
                                           
                        questiondata.answered = False
                        transaction.commit()
                            
    except DBAPIError:
        raise Exception()

#Change answered status of question in database (question answered / unanswered)
def answerStatus(alias, state):
    questiondata = DBSession.query(Question).filter_by(alias = alias).first()
    questiondata.answered = state
    DBSession.add(questiondata)

def akarmaStatus(alias, state):
    channeldata = DBSession.query(Channel).filter_by(usralias = alias).first()
    if state == 'up':
        channeldata.akarma =channeldata.akarma + 1
        DBSession.add(channeldata)
    elif state == 'down':
        channeldata.akarma = channeldata.akarma - 1
        DBSession.add(channeldata)
    else:
        pass
    
# Admin view. Works for Sebastian's login only
@view_config(route_name='adminb', renderer='atv:templates/admin.pt',
             permission='view')    
@view_config(route_name='admin', renderer='atv:templates/admin.pt',
             permission='view')
def admin_view(request):
    try:
        logged_in = authenticated_userid(request)
        now = int(round(time.time()/60/60))
        if logged_in == None:
            return HTTPFound(location = request.route_url('home'))
        if logged_in.lower() != "sebastian":
            return HTTPFound(location = request.route_url('home')) 
        logged_in_alias = logged_in.lower()
        nochannels = DBSession.query(Channel).count()
        noquestions = DBSession.query(Question).count()
        noanswers = DBSession.query(Answer).count()
        latestusers= DBSession.query(Channel).order_by(sa.desc(Channel.created)).limit(20)
        referrer = request.url
        currenturl= '/'
        came_from = request.params.get('came_from', referrer)
        if request.method == 'POST':
                question = request.params['question']
                questiontext = request.params['questiontext']
                channel = request.params['channel']
                answer = request.params['answer']
                fake_user_list = ["PrinceKingPhillip","Rebekah","DaveEwin","DropDeader","Kn0wledge","AmyLou","Phil",
                                  "TaylorSmith","GertrudeStein","HarryPotter","Craig","Jessica","Rebel3","OfficialMe",
                                  "Dan","Joe","Peter","SarahC","AndyW","KateL","Robots","Lead4dead","Amys","Charity",
                                  "Zoe","Jake","Milo","David","Chrisw","Dandy","babellincoln","CapR","WhackAttack",
                                  "PrimalMusk","FPhil","Urish","Babbit_B","Woodrail","The_Sullster","Insectarr","Portis",
                                  "JohnJJames","McSom","NicolasJohnson","Beer-Duff","Pinhead","ME_ME_YOU","Whiteops",
                                  "Lisa","Manny","Trisha","Daniel"]
                questionmain = question
                questiontext = questiontext
                questionmain = questionmain.replace('"', "'")
                questiontext = questiontext.replace('"', "'")
                askedto = channel
                askedtoname = channel
                questionmainlower = questionmain.lower()
                questionmainslug = slugify(questionmainlower)
                logged_in = random.choice(fake_user_list)
                logged_in_alias = logged_in.lower()
                already_asked = DBSession.query(Question).filter_by(alias = questionmainslug).first()
                if not already_asked:
                    qkarma= randint(2,20)
                    askedby = logged_in
                    askedbyalias = logged_in.lower()
                    askedtoalias = askedto.lower()
                    alias= slugify(questionmain) 
                    message = ""
                    askedbyname = logged_in
                    questionasker = askedbyalias + "--" + alias
                    unixage = int(round(time.time()/60/60)) 
                    views = 1
                    with transaction.manager:
                        question = Question(questionmain=questionmain,
                                            questionasker=logged_in_alias + "--" + alias,
                                            askedtoname=askedtoname,
                                            questiontext=questiontext,
                                            askedbyname=logged_in,
                                            qkarma=qkarma,
                                            askedby=logged_in,
                                            askedbyalias=logged_in_alias,
                                            askedto=askedto,
                                            askedtoalias=askedtoalias,
                                            alias=alias,
                                            unixage=unixage,
                                            views=views,)
                        DBSession.add(question)
                    akarma = 1
                    unixage = int(round(time.time()/60/60)) 
                    answeredby = askedto
                    channel = logged_in
                    channel = channel.lower()
                    questionalias = alias
                    question = questionmain
                    vidurl = answer
                    with transaction.manager:
                        answer = Answer(akarma=akarma,
                                        answeredby=answeredby,
                                        questiontext=question,
                                        question=questionalias,
                                        embedcode=vidurl,
                                        channel=channel,
                                        unixage=unixage)
                             
                        DBSession.add(answer)
                        answerStatus(questionalias, True)
                        akarmaStatus(askedtoalias, 'up')
                else:
                    pass         
        else:     
            return {'logged_in':logged_in,
                    'came_from':came_from, 
                    'currenturl':currenturl, 
                    'now':now, 
                    'logged_in_alias':logged_in_alias, 
                    'nochannels':nochannels, 
                    'noquestions':noquestions, 
                    'noanswers':noanswers, 
                    'latestusers':latestusers}
    except DBAPIError:
        raise Exception()

@view_config(route_name='contact', renderer='atv:templates/contact.pt', permission='view')
@view_config(route_name='contactb', renderer='atv:templates/contact.pt', permission='view')
def contact_view(request):
    try:
        logged_in = authenticated_userid(request)
        status = ""
        now = int(round(time.time()/60/60))
        senderblock = ''
        emailblock=''
        messageblock = ''
        if logged_in != None:
            logged_in_alias = logged_in.lower()
        else:
            logged_in_alias = ""
        referrer = request.url
        currenturl= '/'
        came_from = request.params.get('came_from', referrer)
        if request.method == 'POST':
            recaptcha_client = RecaptchaClient('6LeTyuESAAAAANmGDXW0C-gXFi7ka3oV8APjVIlH',
                                               '6LeTyuESAAAAAKNb8BOZDofUeJGm5FXxcwg0ua5l')
            
            challenge = request.params['recaptcha_challenge_field']
            responser = request.params['recaptcha_response_field']
            ip = request.client_addr
            is_solution_correct = recaptcha_client.is_solution_correct(responser,
                                                                       challenge,
                                                                       ip)
            if is_solution_correct:
                sender = request.params['sender']
                email = request.params['email']
                message = request.params['message']
                if not sender:
                    status = "Cannot send. Please ensure all field are filled in correctly."
                if not email:
                    status = "Cannot send. Please ensure all field are filled in correctly."
                if not message:
                    status = "Cannot send. Please ensure all field are filled in correctly."     
                else:
                    mailer.contactForm(sender, email, message)
                    status = """Thank you. Your message has been sent and if
                             required we will respond shortly."""
            else:
                status = 'Incorrect ReCAPCHA - please try again.'
                senderblock = request.params['sender']
                emailblock = request.params['email']
                messageblock = request.params['message']     
        return {'logged_in':logged_in,
                'came_from':came_from, 
                'now':now, 
                'currenturl':currenturl, 
                'logged_in_alias':logged_in_alias, 
                'status':status, 
                'senderblock':senderblock, 
                'emailblock':emailblock, 
                'messageblock':messageblock}
        
    except DBAPIError:
        raise Exception()
    
    
    
@view_config(route_name='verifyreset', renderer='atv:templates/verifyreset.pt',
             permission='view')
def reset_code(request):
    try:    
        login_url = request.route_url('login')
        referrer = request.url
        logged_in = authenticated_userid(request)
        currenturl = '/'
        came_from = request.params.get('came_from', referrer)
        headers= ''
        status = ''
        if logged_in:
            logged_in_alias = logged_in.lower()
        else:
            logged_in_alias = ""
        code = request.matchdict.get('code', None)
        if code is None:
            return HTTPFound(location = request.route_url('home'))
        else:
            match = DBSession.query(TempPassword).filter_by(hashcode=code).first()
            if match is None:
                return HTTPFound(location = request.route_url('home'))
            if 'form.submitted' in request.params:
                newPassword = request.params['password']
                HashNewPassword = sha256_crypt.encrypt(newPassword)
                with transaction.manager:
                    email = match.emailalias
                    DBSession.delete(match)
                    user = DBSession.query(Channel).filter_by(email=email).first()
                    user.password=HashNewPassword
                    DBSession.add(user)
                return HTTPFound(location = request.route_url('login'))
            return{'code':code, 
                   'came_from':came_from, 
                   'logged_in':logged_in, 
                   'logged_in_alias':logged_in_alias,
                   'status': status}
                    
    except DBAPIError:
        raise Exception()
    
#Reset password view    
@view_config(route_name='reset', renderer='atv:templates/reset.pt', 
             permission='view')
@view_config(route_name='resetb', renderer='atv:templates/reset.pt',
             permission='view')
def reset_view(request):
    try:
        login_url = request.route_url('login')
        referrer = request.url
        logged_in = authenticated_userid(request)
        logged_in_alias = ''
        now = int(round(time.time()/60/60))
        currenturl = '/'
        if logged_in:
            logged_in_alias = logged_in.lower()
        if referrer == login_url:
            referrer = '/' # never use the login form itself as came_from
        came_from = request.params.get('came_from', referrer)
        url = request.application_url + '/login',
        headers= ''
        status = ''
        email = ''
        emaillower = ''
        def reset_generator(size=6, chars=string.ascii_uppercase + string.digits):
            return ''.join(random.choice(chars) for x in range(size))
        if 'form.submitted' in request.params:
            email = request.params['email']
            emaillower = email.lower()
            emailExists = DBSession.query(Channel).filter_by(email=emaillower).first()
            tempEmailExists = DBSession.query(TempPassword).filter_by(emailalias=emaillower).first()
            if not emailExists:
                status = "Sorry, there is no account registered with that email address."
            elif ' ' in email:
                status = "Email invalid. Please enter a correct email address."
            
            elif tempEmailExists:
                    status = """Please note that you have already requested a
                             password reset within the last 24 hours. If you
                            have not received the email, please check your spam
                            / junk folder."""
            else:
                resetUsr = emailExists.usralias 
                resetRand = reset_generator(25)
                resetAddress = resetUsr + resetRand
                unixage = int(round(time.time()/60/60))
                with transaction.manager:
                            temp_password = TempPassword(
                                                        emailalias = emaillower,
                                                        hashcode = resetAddress,
                                                        unixage = unixage,
                                                        )
                            DBSession.add(temp_password)
                mailer.resetPassword(emaillower, resetAddress) 
                status = """Thank you, instructions have been sent to your email
                         address on how to reset your password. If you have not
                         received the email within 5 minutes, 
                please check your spam / junk folder."""
                
        return {'status':status,
                'currenturl':currenturl, 
                'came_from':came_from, 
                'url':url, 
                'now':now, 
                'logged_in':logged_in, 
                'email':emaillower, 
                'logged_in_alias':logged_in_alias}
        
    except DBAPIError:
        raise Exception()
    
#Reset email view    
@view_config(route_name='ereset', renderer='atv:templates/ereset.pt',
             permission='view')
@view_config(route_name='eresetb', renderer='atv:templates/ereset.pt', 
             permission='view')
def ereset_view(request):
    try:
        login_url = request.route_url('login')
        referrer = request.url
        now = int(round(time.time()/60/60))
        logged_in = authenticated_userid(request)
        logged_in_alias = logged_in.lower()
        currenturl = '/'
        if not logged_in:
            return HTTPFound(location = request.route_url('home'))
        if referrer == login_url:
            referrer = '/' # never use the login form itself as came_from
        came_from = request.params.get('came_from', referrer)
        url = request.application_url + '/login',
        headers= ''
        status = ''
        email = ''
        emaillower = ''
        UsrEmail = DBSession.query(Channel).filter_by(usralias=logged_in_alias).first()
        currentEmail = UsrEmail.email
        def reset_generator(size=6, chars=string.ascii_uppercase + string.digits):
            return ''.join(random.choice(chars) for x in range(size))
        if 'form.submitted' in request.params:
            email = request.params['email']
            emaillower = email.lower()
            tempEmailExists = DBSession.query(TempEmail).filter_by(oldemail= UsrEmail.email).first()
            EmailExists = DBSession.query(Channel).filter_by(email=email).first()
            if ' ' in email:
                status = "Email invalid. Please enter a correct email address."
            
            elif tempEmailExists:
                status = """Please note that you have already requested a email
                         change within the last 24 hours. If you have not
                         received the email, 
                please check your spam / junk folder."""
            
            elif EmailExists and EmailExists != UsrEmail:
                status = """There is already another account registered under this
                         email address. Please select a different email address
                         and try again."""
                
            elif currentEmail == emaillower:
                status = "You are already registered under this email address."
                
            else:
                resetUsr = UsrEmail.usralias
                resetRand = reset_generator(25)
                resetEmail = resetUsr + resetRand
                unixage = int(round(time.time()/60/60))
                with transaction.manager:
                            temp_email = TempEmail(
                                                   oldemail = UsrEmail.email,
                                                   emailalias = emaillower, 
                                                   hashcode = resetEmail,
                                                   unixage = unixage
                                                   )
                            DBSession.add(temp_email)
                mailer.resetEmail(emaillower, resetEmail) 
                status = """Thank you, a confirmation link has been sent to
                         this new email address. If you have not received the
                         email within 5 minutes, 
                please check your spam / junk folder."""

        return {'status':status,
                'currenturl':currenturl,
                'now':now, 
                'came_from':came_from, 
                'url':url, 
                'logged_in':logged_in, 
                'email':currentEmail, 
                'logged_in_alias':logged_in_alias}
        
    except DBAPIError:
        raise Exception()

#Signup view
@view_config(route_name='signup', renderer='atv:templates/signup.pt', permission='view')
@view_config(route_name='signupb', renderer='atv:templates/signup.pt', permission='view')
def signup_view(request):
    try:
        login_url = request.route_url('login')
        referrer = request.url
        logged_in = authenticated_userid(request)
        currenturl = '/'
        if logged_in:
            return HTTPFound(location = request.route_url('home'))
        if referrer == login_url:
            referrer = '/' # never use the login form itself as came_from
        came_from = request.params.get('came_from', referrer)
        url = request.application_url + '/login',
        headers= ''
        status = ''
        login = ''
        passwordraw = ''
        email = ''
        emaillower = ''
        
        def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
            return ''.join(random.choice(chars) for x in range(size))
        
        if 'form.submitted' in request.params:
            login = request.params['login']
            loginlower = login.lower()
            nolist = [
                      "admin", "top","latest","rising","hot","ask","answer",
                      "answer","answere","answeru","answerr","blog","copyright",
                      "terms","privacy","contact","signup","login","reset",
                      "ereset","verify","following","followunfollow","2x4b32cp",
                      "search","vote","stream"
                      ]
            passwordraw = request.params['password']
            email = request.params['email']
            emaillower = email.lower()
            status = ''
            userExists = DBSession.query(Channel).filter_by(usralias=loginlower).first()
            emailExists = DBSession.query(Channel).filter_by(email=emaillower).first()
            TempUserExists = DBSession.query(TempChannel).filter_by(useralias=loginlower).first()
            TempEmailExists = DBSession.query(TempChannel).filter_by(email=emaillower).first()

            if not login:
                status = "Username invalid. Please enter a username that is at least 6 characters and has no white spaces."   
            elif loginlower in nolist:
                status = "Sorry, that there is already an account registered with that username. Please Select another"
            elif TempUserExists:
                status = "Username already exists. Please select another"
            elif userExists:
                status = "Sorry, that there is already an account registered with that username. Please select another"
            elif emailExists:
                status = "Sorry, that there is already an account registered with that email address. Please select another"
            elif TempEmailExists:
                status = "Sorry, that there is already an account registered with that email address. Please select another."
            elif not passwordraw:
                status = "Password invalid. Please try again."
            elif not email:
                status = "Email address invalid, please try again."
            elif ' ' in login:
                status = "Username invalid. Please enter a username that is at least 6 characters and has no white spaces."
            elif ' ' in passwordraw:
                status = "Password invalid. Please enter a password that is at least 6 characters and has no white spaces."
            elif ' ' in email:
                status = "Email invalid. Please enter a correct email address."
            elif len(login) < 6:
                status = "Username invalid. Please enter a username that is at least 6 characters and has no white spaces."
            elif len(passwordraw) < 6:
                status = "Password invalid. Please enter a username that is at least 6 characters and has no white spaces." 
            else:
                with transaction.manager:
                            verify = login + id_generator(25)
                            password = sha256_crypt.encrypt(passwordraw)
                            unixage = int(round(time.time()/60/60))
                            temp_account = TempChannel(login = login,
                                                       password = password, 
                                                       email = email, 
                                                       verify = verify, 
                                                       useralias = loginlower, 
                                                       unixage=unixage)
                            
                            DBSession.add(temp_account)
                            mailer.signUp(email, verify)
                            return HTTPFound(location = request.route_url('verify')) 
                            
        return {'status':status, 
                'currenturl':currenturl, 
                'came_from':came_from, 
                'url':url, 
                'login':login, 
                'password':passwordraw, 
                'logged_in':logged_in, 
                'email':emaillower}
        
    except DBAPIError:
        raise Exception()

#Verify signup code / email link    
@view_config(route_name='verify', renderer='atv:templates/verify.pt',
             permission='view')
@view_config(route_name='verifyb', renderer='atv:templates/verify.pt', 
             permission='view')
def verify_view(request):
    logged_in = authenticated_userid(request)
    if logged_in:
        return HTTPFound(location = request.route_url('home'))
    else:
        logged_in_alias = ""
        referrer = request.url
        currenturl= '/'
        came_from = request.params.get('came_from', referrer)
    return {'logged_in':logged_in, 'came_from':came_from,
            'currenturl':currenturl, 'logged_in_alias':logged_in_alias}

#verify email code / email link
@view_config(route_name='verifyemail', permission='view')
def verify_email(request):
    #try:
        logged_in = authenticated_userid(request)
        if logged_in:
            return HTTPFound(location = request.route_url('home'))
        else:
            code = request.matchdict.get('code', None)
            if code is None:
                return HTTPFound(location = request.route_url('home'))
            else:
                match = DBSession.query(TempChannel).filter_by(verify=code).first()
                if match is None:
                    return HTTPFound(location = request.route_url('home'))
                else:
                    username = match.login
                    name = username
                    password = match.password
                    email = match.email
                    usralias = username.lower()
                    url = 'answer.tv/' + usralias
                    following = " finance  help  mediation  signlanguage  relationships  dogs  gardening  martialarts  woodoworking  entrepreneurs  math  diving  cplusplus  wordpress  computers  learngerman  learnfrench  learnspanish  learnitalian  java  health  beauty  london  drink  cooking  gaming  knitting  diy  python  "
                    unixage = int(round(time.time()/60/60))
                    with transaction.manager:
                        old_temp = match
                        profileimg = old_temp.login + ".png"
                        DBSession.delete(old_temp)
                        new_user = Channel(username=username, name=name,
                                           password=password, email=email,
                                           usralias=usralias,
                                           following=following,
                                           url=url
                                           )
                        DBSession.add(new_user)   
                    imagepath = media.createpics(profileimg)   
                    with transaction.manager:
                        new_images = Images(usralias=usralias, profilepic=imagepath,
                                            backgroundpic=imagepath)
                        DBSession.add(new_images)
                    newUserQuestions(username)
                    return HTTPFound(location=request.route_url('login'))
        return{}
    #except DBAPIError:
        #raise Exception()

#Channel (profile page) view    
@view_config(route_name='channel', renderer='atv:templates/channel.pt', 
             permission='view')
@view_config(route_name='channelb', renderer='atv:templates/channel.pt', 
             permission='view')
def channelProfile_view(request):
    try:
        channel = request.matchdict.get('channel', None)
        now = int(round(time.time()/60/60))
        mychannel = ''
        if channel is None:
            raise HTTPNotFound()
        else:
            channellower = channel.lower()
            channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == channellower).first()
            if channelname is None:
                raise HTTPNotFound()
            currenturl= request.url
            logged_in = authenticated_userid(request)
            if logged_in != None:
                logged_in_alias = logged_in.lower()
                logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
                try:
                    follow_list = logged_in_details.following.split()
                except:
                    follow_list = ""
                notifications = notify(logged_in_details.notifications)
                if channelname.Channel.usralias in follow_list:
                    is_following = True
                else:
                    is_following = False
                if channelname.Channel.usralias == logged_in_alias:
                    mychannel = True
                else:
                    mychannel = False 
            else:
                logged_in_alias = "" # Workaround - look at a better solution.
                is_following = False 
                notifications = ""
            linehighlighter = "hot"
            canView = security.canView(loggedin = logged_in_alias, 
                                       permission =channelname.Channel.privView, 
                                       channelFollowing = channelname.Channel.following, 
                                       username = channelname.Channel.usralias)
            
            if canView == False:
                return HTTPFound(location = request.route_url('denied'))
            canAsk =  security.canView(loggedin = logged_in_alias, 
                                       permission =channelname.Channel.privAsk, 
                                       channelFollowing = channelname.Channel.following, 
                                       username = channelname.Channel.usralias)
            
            page = int(request.params.get('page', 1)) 
            askedtoalias = channelname.Channel.usralias
            questionlist = Question.get_hot(request, askedtoalias, 
                                            logged_in_alias, page)
            
            return {'channelname':channelname, 
                    'canAsk':canAsk, 
                    'questionlist':questionlist, 
                    'now':now, 
                    'logged_in':logged_in, 
                    'logged_in_alias':logged_in_alias, 
                    'currenturl':currenturl, 
                    'is_following':is_following, 
                    "linehighlighter":linehighlighter, 
                    'notifications':notifications, 
                    'mychannel':mychannel}
    except DBAPIError:
        raise Exception()

#Channel latest view
@view_config(route_name='chanlatest', renderer='atv:templates/channel.pt', permission='view')
@view_config(route_name='chanlatestb', renderer='atv:templates/channel.pt', permission='view')
def chanLatest_view(request):
    try:
        channel = request.matchdict.get('channel', None)
        now = int(round(time.time()/60/60))
        mychannel = ''
        if channel == None:
            raise HTTPNotFound()
        channellower = channel.lower()
        channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == channellower).first()
        if channelname is None:
                raise HTTPNotFound()
        currenturl= request.url
        logged_in = authenticated_userid(request)
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
            try:
                follow_list = logged_in_details.following.split()
            except:
                follow_list = ""
            notifications = notify(logged_in_details.notifications)
            if channelname.Channel.usralias in follow_list:
                is_following = True
            else:
                is_following = False 
            if channelname.Channel.usralias == logged_in_alias:
                mychannel = True
            else:
                mychannel = False 
        else:
            logged_in_alias = "" # Workaround - look at a better solution.
            logged_in_details = ''
            is_following = False 
            notifications = ""
        linehighlighter = "latest"
        canView = security.canView(loggedin = logged_in_alias, 
                                   permission =channelname.Channel.privView, 
                                   channelFollowing = channelname.Channel.following, 
                                   username = channelname.Channel.usralias)
        if canView == False:
            return HTTPFound(location = request.route_url('denied'))
        canAsk =  security.canView(loggedin = logged_in_alias,
                                   permission =channelname.Channel.privAsk, 
                                   channelFollowing = channelname.Channel.following, 
                                   username = channelname.Channel.usralias)
        
        page = int(request.params.get('page', 1))
        askedtoalias = channelname.Channel.usralias
        questionlist = Question.get_latest(request, askedtoalias, 
                                           logged_in_alias, page)
        
        return {'channelname':channelname,
                'canAsk':canAsk, 
                'now':now, 
                'questionlist':questionlist, 
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias, 
                'currenturl':currenturl, 
                'is_following':is_following, 
                "linehighlighter":linehighlighter, 
                'notifications':notifications, 
                'mychannel':mychannel}
        
        
    except DBAPIError:
        raise Exception()

#Channel rising view
@view_config(route_name='chanrising', renderer='atv:templates/channel.pt',
            permission='view')
@view_config(route_name='chanrisingb', renderer='atv:templates/channel.pt', 
             permission='view')
def chanRising_view(request):
    try:
        channel = request.matchdict.get('channel', None)
        now = int(round(time.time()/60/60))
        mychannel = ''
        if channel == None:
            raise HTTPNotFound()
        channellower = channel.lower()
        channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == channellower).first()
        if channelname is None:
                raise HTTPNotFound()
        currenturl= request.url
        logged_in = authenticated_userid(request)
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
            try:
                follow_list = logged_in_details.following.split()
            except:
                follow_list = ""
            notifications = notify(logged_in_details.notifications)
            if channelname.Channel.usralias in follow_list:
                is_following = True
            else:
                is_following = False
            if channelname.Channel.usralias == logged_in_alias:
                    mychannel = True
            else:
                mychannel = False  
        else:
            logged_in_alias = "" # Workaround - look at a better solution.
            logged_in_details = ''
            is_following = False 
            notifications = ""
        linehighlighter = "rising"
        canView = security.canView(loggedin = logged_in_alias,
                                   permission =channelname.Channel.privView, 
                                   channelFollowing = channelname.Channel.following, 
                                   username = channelname.Channel.usralias)
        
        if canView == False:
            return HTTPFound(location = request.route_url('denied'))
        canAsk =  security.canView(loggedin = logged_in_alias, 
                                   permission =channelname.Channel.privAsk, 
                                   channelFollowing = channelname.Channel.following, 
                                   username = channelname.Channel.usralias)
        
        page = int(request.params.get('page', 1))
        askedtoalias = channelname.Channel.usralias
        questionlist = Question.get_rising(request, askedtoalias, 
                                           logged_in_alias, page)
        
        return {'channelname':channelname, 
                'canAsk':canAsk, 
                'now':now, 
                'questionlist':questionlist, 
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias, 
                'currenturl':currenturl, 
                'is_following':is_following, 
                "linehighlighter":linehighlighter, 
                'notifications':notifications, 
                'mychannel':mychannel}
        
    except DBAPIError:
        raise Exception()


#Explore view
@view_config(route_name='explore', renderer='atv:templates/explore.pt',
            permission='view')
@view_config(route_name='exploreb', renderer='atv:templates/explore.pt', 
             permission='view')
def explore_view(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
        else:
            logged_in_alias = "" 
        page = int(request.params.get('page', 1)) 
        trendinglist = Question.get_explore_trending(request,
                                        logged_in_alias, page)
        latestlist = Question.get_explore_latest(request,
                                        logged_in_alias, page)
        ourpicklist = Question.get_explore_ourpicks(request,
                                        logged_in_alias, page)
        latestchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc(Channel.created)).limit(20)
        
        hotchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc((Channel.akarma * 10) + Channel.qkarma)).limit(20)
        
        return {
                'trendinglist':trendinglist,
                'latestlist':latestlist,
                'ourpicklist':ourpicklist,
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias,
                'latestchannels':latestchannels,
                'hotchannels':hotchannels,  
                }
    except DBAPIError:
        raise Exception()


#Explore Trending view
@view_config(route_name='exploretrending', renderer='atv:templates/explore2.pt',
            permission='view')
@view_config(route_name='exploretrendingb', renderer='atv:templates/explore2.pt', 
             permission='view')
def explore_trending_view(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
        else:
            logged_in_alias = "" 
        page = int(request.params.get('page', 1)) 
        questionlist = Question.get_explore_trending100(request,
                                        logged_in_alias, page)
        latestchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc(Channel.created)).limit(20)
        headerline="Trending - Top 100"
        hotchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc((Channel.akarma * 10) + Channel.qkarma)).limit(20)
        return {
                'questionlist':questionlist,
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias,
                'latestchannels':latestchannels,
                'hotchannels':hotchannels,  
                'headerline':headerline,
                }
    except DBAPIError:
        raise Exception()

#Explore Latest view
@view_config(route_name='explorelatest', renderer='atv:templates/explore2.pt',
            permission='view')
@view_config(route_name='explorelatestb', renderer='atv:templates/explore2.pt', 
             permission='view')
def explore_latest_view(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
        else:
            logged_in_alias = "" 
        page = int(request.params.get('page', 1)) 
        questionlist = Question.get_explore_latest100(request,
                                        logged_in_alias, page)
        latestchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc(Channel.created)).limit(20)
        headerline="Latest - Top 100"
        hotchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc((Channel.akarma * 10) + Channel.qkarma)).limit(20)
        return {
                'questionlist':questionlist,
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias,
                'latestchannels':latestchannels,
                'hotchannels':hotchannels,  
                'headerline':headerline,
                }
    except DBAPIError:
        raise Exception()
    
    
    
#Explore Ourpicks view
@view_config(route_name='exploreourpicks', renderer='atv:templates/explore2.pt',
            permission='view')
@view_config(route_name='exploreourpicksb', renderer='atv:templates/explore2.pt', 
             permission='view')
def explore_ourpicks_view(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
        else:
            logged_in_alias = "" 
        page = int(request.params.get('page', 1)) 
        questionlist = Question.get_explore_ourpicks100(request,
                                        logged_in_alias, page)
        latestchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc(Channel.created)).limit(20)
        headerline="Our Picks - Top 100"
        hotchannels = DBSession.query(Channel, Images).outerjoin(Images, Images.usralias == Channel.usralias).order_by(sa.desc((Channel.akarma * 10) + Channel.qkarma)).limit(20)
        return {
                'questionlist':questionlist,
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias,
                'latestchannels':latestchannels,
                'hotchannels':hotchannels,  
                'headerline':headerline,
                }
    except DBAPIError:
        raise Exception()


#Following view
@view_config(route_name='following', renderer='atv:templates/following.pt',
             permission='view')
@view_config(route_name='followingb', renderer='atv:templates/following.pt', 
             permission='view')
def following_view(request):
    try:
        channel = request.matchdict.get('channel', None)
        now = int(round(time.time()/60/60))
        currenturl= request.url
        if channel == None:
            raise HTTPNotFound()
        channellower = channel.lower()
        logged_in = authenticated_userid(request)
        channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == channellower).first()
        if channelname is None:
                raise HTTPNotFound()
        if logged_in != None:
            logged_in_alias = logged_in.lower()
            follow_auth = channelname.Channel.usralias
            if logged_in_alias == follow_auth:
                own_page = True
            else:
                own_page = False
        else:
            logged_in_alias = "" # TO DO Workaround - look at a better solution.
            own_page = False   
        following_list = channelname.Channel.following
        try:
            following_list = following_list.split()
        except:
            following_list = ""
        following_list = sorted(following_list, key=lambda s: s.lower())
        followingdata = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias.in_(following_list)).all()
        notifications = notify(channelname.Channel.notifications)

        page = int(request.params.get('page', 1))
        page_url = PageURL_WebOb(request)
        Mfollowing_list = Page(followingdata, page, url=page_url, items_per_page=60)
        
        return {'channelname':channelname, 
                'logged_in':logged_in, 
                'now':now, 
                'logged_in_alias':logged_in_alias, 
                'currenturl':currenturl, 
                'Mfollowing_list':Mfollowing_list, 
                'own_page':own_page, 
                'notifications':notifications}
        
    except DBAPIError:
        raise Exception()

#Follow / unfollow channels function 
@view_config(route_name='followunfollow', request_method='POST', xhr=True, permission='view')
def followunfollow(request):
    try:
        logged_in = authenticated_userid(request)
        logged_in = logged_in.lower()
        if logged_in:
            following= ''
            followunfollow = ''
            following = request.params['following']
            following = following.lower()
            followunfollow = request.params['followunfollow']
            followunfollow = followunfollow.lower() 
            if followunfollow == 'follow':
                listing = DBSession.query(Channel).filter_by(usralias=logged_in).one()
                if listing.following == None:
                    listing.following = " " + following + " "
                else:
                    listing.following = listing.following + " " + following + " "
                transaction.commit()
                plus_one_follow = DBSession.query(Channel).filter_by(usralias=following).one()
                plus_one_follow.subscribers = plus_one_follow.subscribers + 1
                transaction.commit()  
            if followunfollow == 'unfollow':
                listing = DBSession.query(Channel).filter_by(usralias=logged_in).one()
                following_list = listing.following
                remove_user = " " + following + " " 
                following_list = following_list.replace(remove_user, "")
                listing.following = following_list
                transaction.commit()
                minus_one_follow = DBSession.query(Channel).filter_by(usralias=following).one()
                minus_one_follow.subscribers = minus_one_follow.subscribers - 1 
                transaction.commit()
            return {}
        if not logged_in:
            return HTTPFound(location = request.route_url('home'))    
    except DBAPIError:
        raise Exception()



@view_config(route_name='vote', permission='view')
def vote(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in:
            if request.method == 'POST':
                id = request.params['id']
                upvote = request.params['upvote']
                downvote = request.params['downvote']
                id = id.lower()
                id = id[1:]
                upvote = upvote.lower()
                downvote = downvote.lower()
                logged_in = logged_in.lower()
                id2 = logged_in + "--" + id
                voteData = DBSession.query(Qvote).filter_by(questionasker = id2).first()
                if voteData == None:
                    step = karma_vote_step(upvote, downvote, previousUpvote = False,
                                           previousDownvote = False)
                    questionasker = logged_in + "--" + id
                    with transaction.manager:
                        voteData = Qvote(userid = logged_in, 
                                         questionasker = questionasker, 
                                         questionid = id, 
                                         upvote = upvote, downvote = downvote)
                        DBSession.add(voteData) 
                    update_question_qkarma(logged_in, id, step)
                    update_channel_qkarma(logged_in, step)
                else:
                    step = karma_vote_step(upvote, downvote, 
                                           previousUpvote = voteData.upvote, 
                                           previousDownvote = voteData.downvote)
                    
                    with transaction.manager:
                        voteData.userid = logged_in
                        voteData.questionid = id
                        voteData.upvote = upvote
                        voteData.downvote = downvote
                        DBSession.add(voteData)
                        
                    update_question_qkarma(logged_in, id, step)
                    update_channel_qkarma(logged_in, step)
            else:
                pass         
    except DBAPIError:
        raise Exception()
    
def karma_vote_step(upvote, downvote, previousUpvote, previousDownvote):
    #Start at null
    step =0
    #Accoutn for current vote (up or down 1 vote)
    if upvote == 'true':
        step = 1
    elif downvote == 'true':
        step = -1
    #factor in previous vote on same question (does another vote need to be removed)
    if previousUpvote == 1:
        step += -1
    elif previousDownvote == 1:
        step += +1
        
    print upvote *1000
    print downvote * 1000
    print previousUpvote * 1000
    print previousDownvote * 1000
    return step

def update_question_qkarma(user, questionid, step):
    question = DBSession.query(Question).filter_by(alias = questionid).first()
    with transaction.manager:
            question.qkarma += + step
            question.questionasker = user + "--" + questionid
            DBSession.add(question)
        
def update_channel_qkarma(channelid, step):
    channel = DBSession.query(Channel).filter_by(usralias = channelid).first()
    with transaction.manager:
        channel.qkarma += + step
        DBSession.add(channel)

#Delete notifications function
@view_config(route_name='deletenotification', request_method='POST', xhr=True, 
             permission='view')
def deleteNotification(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in:
            notification= ''
            action = ''
            notification = request.params['notification']
            if notification == "Welcome to answer.tv! Your profile is looking a little empty. Click the cog icon in the top right hand corner to add your info.":
                remover = "1"
            if notification == "We have added a few people to your following list to help get you started.":
                remover = "2"
            if notification == "notification3":
                remover = "3"
            if notification == "notification4":
                remover = "4"
            if notification == "notification5":
                remover = "5"
            action = request.params['action']
            if action == 'delete':
                listing = DBSession.query(Channel).filter_by(username=logged_in).first()
                notification_list = listing.notifications
                remove_notification = remover
                notification_list = notification_list.replace(remove_notification, "")
                listing.notifications = notification_list
                transaction.commit()
            return {}
        if not logged_in:
            return HTTPFound(location = request.route_url('home'))    
    except DBAPIError:
        raise Exception()
    
@view_config(route_name='question', renderer='atv:templates/question.pt', permission='view')
@view_config(route_name='questionb', renderer='atv:templates/question.pt', permission='view')
def question_view(request):
    try:
        #check for url
        channel = request.matchdict.get('channel', None)
        if channel == None:
            raise HTTPNotFound()
        question = request.matchdict.get('question', None)
        if question == None:
            raise HTTPNotFound()
        #grab channel info
        channellower = channel.lower()
        channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == channellower).first()
        if channelname == None:
            raise HTTPNotFound()
        logged_in = authenticated_userid(request)
        is_following=''
        if logged_in:
            logged_in_alias = logged_in.lower()
            notifications = notify(channelname.Channel.notifications)          
            canAsk =  security.canView(loggedin = logged_in_alias, 
                                       permission =channelname.Channel.privAsk, 
                                       channelFollowing = channelname.Channel.following, 
                                       username = channelname.Channel.usralias)
            
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
            try:
                follow_list = logged_in_details.following.split()
            except:
                follow_list = ""
            if channelname.Channel.usralias in follow_list:
                is_following = True
            else:
                is_following = False 
            if channelname.Channel.usralias == logged_in_alias:
                    mychannel = True
            else:
                    mychannel = False 
        else:
            logged_in_alias = ''
            notifications = ''
            canAsk = ''
        now = int(round(time.time()/60/60))
        #grab question info
        questionlower = question.lower()
        questionname = DBSession.query(Question, Qvote, Images).outerjoin(Images, Images.usralias == Question.askedbyalias).outerjoin(Qvote, and_(Question.questionasker==Qvote.questionasker, Qvote.userid == logged_in_alias)).filter(Question.alias == questionlower).first()
        if questionname is None:
            raise HTTPNotFound()
        questionmatch = questionname.Question.questionmain
        if questionname == None:
            raise HTTPNotFound()
        questionname.Question.views += + 1
        with transaction.manager:
            votecount = DBSession.query(Question).filter(Question.alias == questionlower).first()
            votecount.views += + 1
            transaction.commit()
        #commerize viewcount
        views = questionname.Question.views
        views = '{:20,.0f}'.format(views)
        #Grab 'more questions...' info
        now = int(round(time.time()/60/60)) + 1
        gravity = 1.8
        askedtoalias = channelname.Channel.usralias
        questionlist = DBSession.query(Question, Qvote, Images).outerjoin(Images, Images.usralias == Question.askedbyalias).outerjoin(Qvote, and_(Question.questionasker==Qvote.questionasker, Qvote.userid == logged_in_alias)).filter\
                      (Question.askedtoalias == channellower).filter(Question.questionmain\
                      != questionmatch).order_by(sa.desc((Question.qkarma -1) /\
                      func.pow((now - Question.unixage), gravity))).limit(5)
        #grab answer info
        answerlist = DBSession.query(Answer).filter_by(question = question).first()
        if answerlist is None:
            answerlist = False
        mychannel=''
        currenturl= request.url
        page = int(request.params.get('page', 1)) 
        channel = channelname.Channel.username
        if channelname.Channel.usralias == logged_in_alias:
            mychannel = True
        else:
            mychannel = False
            
        return {'channelname':channelname, 
                'canAsk':canAsk, 
                'now':now, 
                'questionlist':questionlist, 
                'logged_in':logged_in, 
                'mychannel':mychannel, 
                'answerlist':answerlist, 
                'currenturl':currenturl, 
                'logged_in_alias':logged_in_alias, 
                'questionname':questionname, 
                'is_following':is_following, 
                'notifications':notifications,
                'views':views,
                }
        
    except DBAPIError:
        raise HTTPNotFound()

#Stream hot view
@view_config(route_name='stream', renderer='atv:templates/stream.pt', permission='view')
@view_config(route_name='streamb', renderer='atv:templates/stream.pt', permission='view')
def stream_view(request):
    try:
        logged_in = authenticated_userid(request)
        now = int(round(time.time()/60/60))
        if logged_in:
            linehighlighter = "hot"
            headers = logged_in
            channellower = logged_in.lower()
            askedtoalias = channellower
            logged_in_alias = logged_in.lower()
            channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == logged_in_alias).first()
            canAsk = True
            logged_in_details = channelname
            followinglist = channelname.Channel.following
            try:
                follow_list = logged_in_details.Channel.following.split()
            except:
                follow_list= ""
            notifications = notify(logged_in_details.Channel.notifications)
            if channelname.Channel.usralias in follow_list:
                is_following = True
            else:
                is_following = False
            notifications = notify(logged_in_details.Channel.notifications)
            if channelname.Channel.usralias == logged_in_alias:
                    mychannel = True
            else:
                    mychannel = False 
            notifications = notify(channelname.Channel.notifications)
            page = int(request.params.get('page', 1)) 
            questionlist = Question.stream_hot(request, followinglist, logged_in_alias, page)
            
            return {'channelname':channelname, 
                    'canAsk':canAsk, 
                    'now':now, 
                    'logged_in_details':logged_in_details, 
                    'is_following':is_following, 
                    'headers':headers, 
                    'questionlist':questionlist, 
                    'logged_in':logged_in, 
                    'logged_in_alias':logged_in_alias, 
                    "linehighlighter":linehighlighter, 
                    'notifications':notifications}
    
        else:
            return HTTPFound(location = request.route_url('home'))   
    except DBAPIError:
        raise Exception()

#Stream latest view
@view_config(route_name='streamlatest', renderer='atv:templates/stream.pt', 
             permission='view')
@view_config(route_name='streamlatestb', renderer='atv:templates/stream.pt', 
             permission='view')
def streamlatest_view(request):
    try:
        logged_in = authenticated_userid(request)
        now = int(round(time.time()/60/60))
        if logged_in:
            linehighlighter = "latest"
            headers = logged_in
            channellower = logged_in.lower()
            askedtoalias = channellower
            logged_in_alias = logged_in.lower()
            channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == logged_in_alias).first()
            canAsk =  True
            logged_in_details = channelname
            followinglist = channelname.Channel.following
            try:
                follow_list = logged_in_details.Channel.following.split()
            except:
                follow_list = ""
            notifications = notify(logged_in_details.Channel.notifications)
            if channelname.Channel.usralias in follow_list:
                is_following = True
            else:
                is_following = False
            notifications = notify(logged_in_details.Channel.notifications)
            if channelname.Channel.usralias == logged_in_alias:
                    mychannel = True
            else:
                    mychannel = False 
            notifications = notify(channelname.Channel.notifications)
            page = int(request.params.get('page', 1)) 
            questionlist = Question.stream_latest(request, followinglist, logged_in_alias, page)
            
            return {'channelname':channelname, 
                    'canAsk':canAsk,
                    'now':now, 'canAsk':canAsk, 
                    'logged_in_details':logged_in_details, 
                    'is_following':is_following, 
                    'headers':headers, 
                    'questionlist':questionlist, 
                    'logged_in':logged_in, 
                    'logged_in_alias':logged_in_alias, 
                    "linehighlighter":linehighlighter, 
                    'notifications':notifications}
    
        else:
            return HTTPFound(location = request.route_url('home'))   
    except DBAPIError:
        raise Exception()

#Stream top view
@view_config(route_name='streamtop', renderer='atv:templates/stream.pt', 
             permission='view')
@view_config(route_name='streamtopb', renderer='atv:templates/stream.pt', 
             permission='view')
def streamtop_view(request):
    try:
        logged_in = authenticated_userid(request)
        now = int(round(time.time()/60/60))
        if logged_in:
            linehighlighter = "rising"
            headers = logged_in
            channellower = logged_in.lower()
            askedtoalias = channellower
            logged_in_alias = logged_in.lower()
            channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == logged_in_alias).first()
            canAsk = True
            logged_in_details = channelname
            followinglist = channelname.Channel.following
            try:
                follow_list = logged_in_details.Channel.following.split()
            except:
                follow_list = ""
            notifications = notify(logged_in_details.Channel.notifications)
            if channelname.Channel.usralias in follow_list:
                is_following = True
            else:
                is_following = False
            notifications = notify(logged_in_details.Channel.notifications)
            if channelname.Channel.usralias == logged_in_alias:
                    mychannel = True
            else:
                    mychannel = False 
            notifications = notify(channelname.Channel.notifications)
            page = int(request.params.get('page', 1)) 
            questionlist = Question.stream_top(request, followinglist, logged_in_alias, page)
            
            return {'channelname':channelname, 
                    'canAsk':canAsk, 
                    'now':now, 
                    'logged_in_details':logged_in_details, 
                    'is_following':is_following, 
                    'headers':headers, 
                    'questionlist':questionlist, 
                    'logged_in':logged_in, 
                    'logged_in_alias':logged_in_alias, 
                    "linehighlighter":linehighlighter, 
                    'notifications':notifications}
    
        else:
            return HTTPFound(location = request.route_url('home'))   
    except DBAPIError:
        raise Exception()

#Edit page view    
@view_config(route_name='edit', renderer='atv:templates/edit.pt', permission='view')
@view_config(route_name='editb', renderer='atv:templates/editb.pt', permission='view')
def edit_view(request):
    try:
        logged_in = authenticated_userid(request)
        logged_in_alias = logged_in.lower()
        if logged_in:
            channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == logged_in_alias).first()
            now = int(round(time.time()/60/60))
            profileError = ''
            nameError = ''
            locationError = ''
            websiteError = ''
            descError = ''
            emailError = ''
            passwordError = ''
            custombkgError = ''
            headers = logged_in
            notifications = notify(channelname.Channel.notifications)
            if 'form.submitted' in request.params:
                name = request.params['name']
                location = request.params['location']
                website = request.params['website']
                description = request.params['bio']
                background = request.params['background']
                privacyAsk = request.params['privAsk']
                privacyView = request.params['privView']
                try:
                    Profilepic = request.params['picupload'].file
                    verifyImg = media.verifyFile(Profilepic)
                    if verifyImg == "True":
                        oldname = channelname.Images.profilepic
                        newname = media.image_name_generator(35) + ".png"
                        profileError = media.uploadImg(Profilepic, oldname, newname)
                        with transaction.manager:
                            channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == logged_in_alias).first()
                            channelname.Images.profilepic = newname
                            transaction.commit()
                    else:
                        profileError = verifyImg
                        return {'logged_in':logged_in, 'now':now, 
                                'logged_in_alias':logged_in_alias, 
                                'notifications':notifications, 
                                'channelname':channelname, 
                                'profileError': profileError, 
                                'custombkgError':custombkgError, 
                                'nameError':nameError, 
                                'locationError':locationError, 
                                'websiteError':websiteError, 
                                'descError':descError, 
                                'emailError':emailError, 
                                'passwordError':passwordError
                                }
                except:
                    pass
                try:
                    Backgroundpic = request.params['backgroundUpload'].file
                    verifyImg = media.verifyBkgFile(Backgroundpic)
                    if verifyImg == "True":
                        oldname = channelname.Images.profilepic
                        newname = media.image_name_generator(35) + ".png"
                        custombkgError = media.uploadBkgImg(Backgroundpic, oldname, newname)  
                        with transaction.manager:
                            channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == logged_in_alias).first()
                            channelname.Images.backgroundpic = newname
                            transaction.commit()                  
                    else:
                        custombkgError = verifyImg
                        return {'logged_in':logged_in, 
                                'now':now, 
                                'logged_in_alias':logged_in_alias, 
                                'notifications':notifications, 
                                'channelname':channelname, 
                                'profileError': profileError, 
                                'custombkgError':custombkgError, 
                                'nameError':nameError, 
                                'locationError':locationError, 
                                'websiteError':websiteError, 
                                'descError':descError, 
                                'emailError':emailError, 
                                'passwordError':passwordError}
                except:
                    with transaction.manager:
                        ProfEdit = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == logged_in_alias).first()
                        ProfEdit.Images.backgroundpic = background  
                with transaction.manager:
                    ProfEdit = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == logged_in_alias).first()
                    ProfEdit.Channel.name = name
                    ProfEdit.Channel.location = location
                    ProfEdit.Channel.url = website
                    ProfEdit.Channel.description = description
                    ProfEdit.Channel.privAsk = privacyAsk
                    ProfEdit.Channel.privView = privacyView
                    transaction.commit()  
                return HTTPFound(location = request.route_url('edit')) 
            
            return {'logged_in':logged_in, 
                    'now':now, 
                    'logged_in_alias':logged_in_alias, 
                    'notifications':notifications, 
                    'channelname':channelname, 
                    'profileError': profileError, 
                    'custombkgError':custombkgError, 
                    'nameError':nameError, 
                    'locationError':locationError, 
                    'websiteError':websiteError, 
                    'descError':descError, 
                    'emailError':emailError, 
                    'passwordError':passwordError}
        else:
            return HTTPFound(location = request.route_url('home'))   
    except DBAPIError:
        raise Exception()

#COmment hisotry view
@view_config(route_name='history', renderer='atv:templates/history.pt', 
             permission='view')
@view_config(route_name='historyb', renderer='atv:templates/history.pt', 
             permission='view')
def history_view(request):
    try:
        logged_in = authenticated_userid(request)
        canAsk= False
        now = int(round(time.time()/60/60))
        channel = request.matchdict.get('channel', None)
        channellower = channel.lower()
        channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == channellower).first()
        if channelname is None:
                raise HTTPNotFound()
        currenturl="/"
        if logged_in:
            askedtoalias = channellower
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
            try:
                follow_list = logged_in_details.following.split()
            except:
                follow_list = ""
            notifications = notify(logged_in_details.notifications)
            canAsk =  security.canView(loggedin = logged_in_alias, 
                                       permission =channelname.Channel.privAsk, 
                                       channelFollowing = channelname.Channel.following, 
                                       username = channelname.Channel.usralias)
            
            if channelname.Channel.usralias in follow_list:
                is_following = True
            else:
                is_following = False
            notifications = notify(logged_in_details.notifications)
            if channelname.Channel.usralias == logged_in_alias:
                    mychannel = True
            else:
                    mychannel = False 
        else:
            logged_in_alias = ''
            notifications = ''
            mychannel= False
            is_following = False 
        linehighlighter = "questions"    
        page = int(request.params.get('page', 1)) 
        questionlist = Question.get_history(request, channellower, logged_in_alias, page)
        
        return {'channelname':channelname, 
                'now':now, 
                'canAsk':canAsk, 
                'is_following':is_following, 
                'mychannel':mychannel, 
                'questionlist':questionlist, 
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias, 
                'currenturl':currenturl, "linehighlighter":linehighlighter, 
                'notifications':notifications}
       
    except DBAPIError:
        raise Exception()

#Comment answer history view
@view_config(route_name='a_history', renderer='atv:templates/history.pt', 
             permission='view')
@view_config(route_name='a_historyb', renderer='atv:templates/history.pt', 
             permission='view')
def ahistory_view(request):
    try:
        logged_in = authenticated_userid(request)
        canAsk = False
        now = int(round(time.time()/60/60))
        channel = request.matchdict.get('channel', None)
        channellower = channel.lower()
        channelname = DBSession.query(Channel, Images).outerjoin(Images, Channel.usralias == Images.usralias).filter(Channel.usralias == channellower).first()
        if channelname is None:
                raise HTTPNotFound()
        currenturl="/"
        if logged_in:
            askedtoalias = channellower
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
            canAsk =  security.canView(loggedin = logged_in_alias,
                                       permission =channelname.Channel.privAsk, 
                                       channelFollowing = channelname.Channel.following, 
                                       username = channelname.Channel.usralias)
            
            try:
                follow_list = logged_in_details.following.split()
            except:
                follow_list = ""
            notifications = notify(logged_in_details.notifications)
            if channelname.Channel.usralias in follow_list:
                is_following = True
            else:
                is_following = False
            notifications = notify(logged_in_details.notifications)
            if channelname.Channel.usralias == logged_in_alias:
                    mychannel = True
            else:
                    mychannel = False 
        else:
            logged_in_alias = ''
            notifications = ''
            mychannel= False
            is_following = False 
        linehighlighter = "answers"    
        page = int(request.params.get('page', 1)) 
        questionlist = Question.get_ahistory(request, channellower, logged_in_alias, page)
        
        return {'channelname':channelname, 
                'now':now, 
                'canAsk':canAsk, 
                'is_following':is_following, 
                'mychannel':mychannel, 
                'questionlist':questionlist, 
                'logged_in':logged_in, 
                'logged_in_alias':logged_in_alias, 
                'currenturl':currenturl, 
                "linehighlighter":linehighlighter, 
                'notifications':notifications
                }
       
    except DBAPIError:
        raise Exception()
    
#Ask question view
@view_config(route_name='ask', permission='view')
def ask_question(request):
    try:
        logged_in = authenticated_userid(request)
        if logged_in:
            if request.method == 'POST':
                questionmain = request.params['question']
                questiontext = request.params['questiontext']
                questionmain = questionmain.replace('"', "'")
                questiontext = questiontext.replace('"', "'")
                askedto = request.params['askedto']
                askedtoname = request.params['askedtoname']
                questionmainlower = questionmain.lower()
                questionmainslug = slugify(questionmainlower)
                logged_in_alias = logged_in.lower()
                logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
                already_asked = DBSession.query(Question).filter_by(alias = questionmainslug).first()
                if not already_asked:
                    qkarma= 0
                    askedby = logged_in
                    askedbyalias = logged_in.lower()
                    askedtoalias = askedto.lower()
                    alias= slugify(questionmain) 
                    message = ""
                    askedbyname = logged_in_details.name
                    questionasker = askedbyalias + "--" + alias
                    unixage = int(round(time.time()/60/60)) 
                    views = 1
                    with transaction.manager:
                        question = Question(questionmain = questionmain, 
                                            questionasker = questionasker, 
                                            askedtoname = askedtoname, 
                                            questiontext = questiontext, 
                                            askedbyname = askedbyname, 
                                            qkarma = qkarma, 
                                            askedby = askedby, 
                                            askedbyalias = askedbyalias, 
                                            askedto = askedto, 
                                            askedtoalias = askedtoalias, 
                                            alias = alias, 
                                            unixage = unixage,
                                            views = views,)
                        DBSession.add(question)
                else:
                    pass         
    except DBAPIError:
        raise Exception()

#Search view
@view_config(route_name='search', renderer='atv:templates/search.pt', 
             permission='view')
@view_config(route_name='searchb', renderer='atv:templates/search.pt', 
             permission='view')
def search_question(request):
    try:
        logged_in = authenticated_userid(request)
        now = int(round(time.time()/60/60))
        currenturl ="/"
        if logged_in:
            logged_in_alias = logged_in.lower()
            logged_in_details = DBSession.query(Channel).filter_by(usralias =logged_in_alias).first()
            notifications = notify(logged_in_details.notifications)
        else:
            logged_in_alias = ''
            notifications = ''
        if request.method == 'POST':
            searchterm = request.params['searchterm']
            page = int(request.params.get('page', 1)) 
            questionlist = Question.get_search(request, searchterm, logged_in_alias, page)
            results = False 
            if questionlist is None:
                results = True
                
            return {'questionlist':questionlist, 
                    'now':now, 
                    'logged_in':logged_in, 
                    'logged_in_alias':logged_in_alias, 
                    'currenturl':currenturl, 
                    'searchterm':searchterm, 
                    'results':results, 
                    'notifications':notifications}   
        else:
            return HTTPFound(location = request.route_url('home'))       
    except DBAPIError:
        raise Exception()     
    
#Create starter questions for new user accounts
def newUserQuestions(username):
    questionbank = [
                     "What is something everyone should carry around 'just in case'?",
                     "What is the most 'grandma phrase' you can say?",
                     "What's the coolest thing you can buy for under $25?",
                     "What is the most BS sounding, true fact that you know?",
                     "What would you do every day if you could?",
                     "What are some simple things that you do to make food go from 'ok' to 'delicious'?",
                     "What is the laziest thing you've ever done?",
                     "Which book changed your life after you read it, and how?",
                     "What gets weirder and weirder the more you think about it?",
                     "What is the coolest thing I can take to a party to improve the night?",
                     "What would your brutally honest dating profile say?",
                     "What did you realize too late?",
                     "What is something people do that they think is helpful, but really isn't?",
                     "What is a story you have been dying to tell?",
                     "What TV or movie cliche drives you insane?",
                     "What DID live up to its hype?",
                     "What misconception would you like to clear up?",
                     "What is the best toast you know for drinking?",
                     "What is the creepiest 'glitch in the matrix' you've experienced?",
                     "If you had $2.5 billion to spend, what would you spend it on?",
                     "What is your quietest act of rebellion?",
                     "What do you hope happens in the next 5 years?",
                     "What is something you did totally wrong for most of your life?",
                     "Is there a film you refuse to watch?",
                     "Which fictional character do you have an irrational level of hate towards?",
                     ]
    
    i = 0
    while i < 5:
        question = random.choice(questionbank)
        alias = slugify(question)
        questionasker = username + '--' + alias
        questiontext=''
        askedbyname = 'Sebastian'
        askedby = 'Sebastian'
        askedbyalias = 'sebastian'
        qkarma= 0
        views = 0
        askedtoalias = username.lower()
        unixage = int(round(time.time()/60/60))
        already_asked = DBSession.query(Question).filter_by(alias = alias).first()
        if not already_asked:
            with transaction.manager:
                question = Question(
                                    questionmain = question,
                                    alias = alias, 
                                    questionasker = questionasker, 
                                    askedtoname = username, 
                                    questiontext = questiontext, 
                                    askedbyname = askedbyname, 
                                    qkarma = qkarma, 
                                    askedby = askedby, 
                                    askedbyalias = askedbyalias, 
                                    askedto = username, 
                                    askedtoalias = askedtoalias,
                                    unixage = unixage,
                                    views = views,
                                    )
                DBSession.add(question)
                i = i + 1
        else:
            i = i + 1

conn_err_msg = """Answer.tv encountered an error. Please try again in a few
               moments."""
