import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#Email server settings
smtp_server = 'email-smtp.eu-west-1.amazonaws.com'
smtp_username = 'AKIAID2MYX7XYWL7TKSA'
smtp_password = 'Alv3cd3HeejmJqItsKe9JGPx150YJswnmz9xjc42Wz/U'
smtp_port = '25'
smtp_do_tls = True
    
# /Contact contact form mailer
def contactForm(sender, email, message):
    toaddrs  = 'sebastian@incerto.net'
    msg = "From: team@answer.tv " + message
    #Change according to your settings
    server.set_debuglevel(10)
    server.tls()
    server.login(smtp_username, smtp_password)
    server.sendmail(sender, toaddrs, msg)
    server.quit()



#Signup email
def signUp(email, verify):
    msg = MIMEMultipart('alternative')

    msg['Subject'] = "Answer.tv registration" 
    msg['From']    = 'registration@answer.tv' # Your from name and email address
    msg['To']      = email

    text = '''Thank you for signing up to answer.tv! To complete your
           registration, simply click on the link below to activate your
           account. If you cannot click on the link please copy and paste into
           your web browser. Please note that this link will expire within 24
           hours.\n http://www.answer.tv/verify/''' + verify + '''\nIf you
           believe you have received this email in error, please contact us at
           answer.tv/contact.\n Regards \n The answer.tv team\n'''
    
    part1 = MIMEText(text, 'plain')

    html = '''<p>Thank you for signing up to answer.tv! To complete your 
           registration, simply click on the link below to activate your
           account. If you cannot click on the link please copy and paste into
           your web browser. Please note that this link will expire within 24
           hours.</p>''' + "<p><a href='http://www.answer.tv/verify/" + verify\
           + "'>http://www.answer.tv/verify/" + verify + "</a></p>" + """<p>If
           you believe that you have received this email in error, please
           <a href="http://answer.tv/conatact">contact us</a>.</p><p>Regards</p><p>The answer.tv
           team</p>"""
    part2 = MIMEText(html, 'html')
    
    username = 'USR'
    password = 'PASSWORD'

    msg.attach(part1)
    msg.attach(part2)

    #Change according to your settings
    server = smtplib.SMTP(host=smtp_server, port=smtp_port, timeout=10)
    server.set_debuglevel(10)
    server.starttls()
    server.ehlo()
    server.login(smtp_username, smtp_password)
    server.sendmail(msg['From'], msg['To'], msg.as_string())
    server.quit()


#Reset password email
def resetPassword(email, resetcode):
    msg = MIMEMultipart('alternative')

    msg['Subject'] = "Answer.tv reset password request" 
    msg['From']    = 'registration@answer.tv' # Your from name and email address
    msg['To']      = email

    text = '''You have requested to reset your answer.tv password. Click on the
           link below to reset your password. If you cannot click on the link,
           please copy and paste the address into your web browser. Please note
           that this link will expire within 24 hours.\n http://www.answer.tv/
           reset/''' + resetcode + """\nIf you believe you have received this
           email in error, or you have not requested a password reset, please
           contact us at answer.tv/contact.\n Regards \n The answer.tv team\n"""
    
    part1 = MIMEText(text, 'plain')

    html = '''<p>You have requested to reset your answer.tv password. Click on
           the link below to reset your password. If you cannot click on the
           link, please copy and paste the address into your web browser.
           Please note that this link will expire within 24 hours.</p>''' + """
           <p><a href='http://www.answer.tv/reset/""" + resetcode + """'>
           http://www.answer.tv/reset/""" + resetcode + "</a></p>" + """<p>If
           you believe that you have received this email in error, or you have
           not requested a password reset, please <a href="http://answer.tv/conatact">contact us</a>.
           </p><p>Regards</p><p>The answer.tv team</p>"""
    part2 = MIMEText(html, 'html')

    username = 'USR'
    password = 'PASSWORD'

    msg.attach(part1)
    msg.attach(part2)

    #Change according to your settings
    server = smtplib.SMTP(host=smtp_server, port=smtp_port, timeout=10)
    server.set_debuglevel(10)
    server.starttls()
    server.ehlo()
    server.login(smtp_username, smtp_password)
    server.sendmail(msg['From'], msg['To'], msg.as_string())
    server.quit()
    
    
#Reset email password    
def resetEmail(email, resetcode):
    msg = MIMEMultipart('alternative')

    msg['Subject'] = "Answer.tv email change request" 
    msg['From']    = 'registration@answer.tv' # Your from name and email address
    msg['To']      = email

    text = '''You have requested to change your answer.tv email address. Click
           on the link below to reset your email address. If you cannot click on
           the link, please copy and paste the address into your web browser.
           Please note that this link will expire within 24 hours.\n
           http://www.answer.tv/ereset/''' + resetcode + """\nIf you believe
           you have received this email in error, or you have not requested an
           email change please contact us at answer.tv/contact.\n Regards \n
           The answer.tv team\n"""
    
    part1 = MIMEText(text, 'plain')

    html = '''<p>You have requested to change your answer.tv email address.
           Click on the link below to reset your email address. If you cannot
           click on the link, please copy and paste the address into your web
           browser. Please note that this link will expire within 24 hours.</p>
           ''' + "<p><a href='http://www.answer.tv/ereset/" + resetcode + """'>
           http://www.answer.tv/ereset/""" + resetcode + "</a></p>" + """<p>If
           you believe that you have received this email in error, or you have
           not requested a email change, <a href="http://answer.tv/conatact">contact us</a>.
           </p><p>Regards</p><p>The answer.tv team</p>"""
           
    part2 = MIMEText(html, 'html')

    username = 'USR'
    password = 'PASSWORD'

    msg.attach(part1)
    msg.attach(part2)

    #Change according to your settings
    server = smtplib.SMTP(host=smtp_server, port=smtp_port, timeout=10)
    server.set_debuglevel(10)
    server.starttls()
    server.ehlo()
    server.login(smtp_username, smtp_password)
    server.sendmail(msg['From'], msg['To'], msg.as_string())
    server.quit()
